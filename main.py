"""Taxímetro - MVP.

Tela do taxímetro: inicia/finaliza corrida, rastreia km via GPS e calcula o
valor em tempo real conforme a tarifa do momento (dia da semana / horário),
com opção de marcar "festa" para escolher a tarifa manualmente (vale só nos
fins de semana) e campos opcionais de nome/telefone do cliente. Cada corrida
finalizada é salva num histórico local, acessível pelo menu no canto
superior esquerdo.
"""
import os
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.utils import platform

from taximetro.distance import MAX_PLAUSIBLE_STEP_KM, haversine_km
from taximetro.fare import (
    FLAG_DROP,
    RATE_MAX,
    RATE_MIN,
    RATE_WEEKEND_DEFAULT,
    is_weekend,
    resolve_rate,
)
from taximetro.storage import list_rides, save_ride

try:
    from plyer import gps
except Exception:
    gps = None

KV = """
<TopBar@BoxLayout>:
    menu_callback: None
    title_text: ""
    size_hint_y: None
    height: dp(48)
    spacing: dp(8)

    Button:
        text: "="
        font_size: "22sp"
        size_hint_x: None
        width: dp(48)
        on_release: root.menu_callback() if root.menu_callback else None

    Label:
        text: root.title_text
        font_size: "22sp"
        halign: "left"
        valign: "middle"
        text_size: self.size

<MainScreen>:
    name: "main"

    BoxLayout:
        orientation: "vertical"
        padding: dp(24)
        spacing: dp(14)

        TopBar:
            title_text: "Se Pique"
            menu_callback: root.open_menu

        Label:
            text: root.status_text
            font_size: "16sp"
            size_hint_y: None
            height: dp(24)

        Label:
            text: "[b]R$ {{:.2f}}[/b]".format(root.fare)
            markup: True
            font_size: "52sp"
            size_hint_y: None
            height: dp(72)

        Label:
            text: "{{:.2f}} km   R$ {{:.2f}}/km  (+ R$ {{:.2f}} bandeirada)".format(root.distance_km, root.rate_per_km, {flag_drop})
            font_size: "14sp"
            size_hint_y: None
            height: dp(22)

        TextInput:
            id: name_input
            hint_text: "Nome do cliente (opcional)"
            multiline: False
            size_hint_y: None
            height: dp(44)
            disabled: root.running
            on_text: root.customer_name = self.text

        TextInput:
            id: phone_input
            hint_text: "Telefone (opcional)"
            multiline: False
            size_hint_y: None
            height: dp(44)
            disabled: root.running
            on_text: root.customer_phone = self.text

        BoxLayout:
            size_hint_y: None
            height: dp(44)
            spacing: dp(12)
            disabled: root.running

            CheckBox:
                id: festa_check
                size_hint_x: None
                width: dp(48)
                active: root.festa
                on_active: root.set_festa(self.active)

            Label:
                text: "Festa (fim de semana): escolher valor"
                font_size: "14sp"

        BoxLayout:
            size_hint_y: None
            height: dp(44)
            spacing: dp(12)
            disabled: not root.festa or root.running

            Label:
                text: "R$ {{:.2f}}/km".format(root.festa_rate)
                size_hint_x: None
                width: dp(90)

            Slider:
                id: festa_slider
                min: {rate_min}
                max: {rate_max}
                step: 0.10
                value: root.festa_rate
                on_value: root.set_festa_rate(self.value)

        Widget:

        Button:
            text: "Iniciar corrida" if not root.running else "Finalizar corrida"
            font_size: "20sp"
            size_hint_y: None
            height: dp(60)
            on_release: root.toggle_ride()

<HistoryScreen>:
    name: "history"

    BoxLayout:
        orientation: "vertical"
        padding: dp(24)
        spacing: dp(14)

        TopBar:
            title_text: "Historico de corridas"
            menu_callback: root.go_back

        ScrollView:
            BoxLayout:
                id: history_list
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)
""".format(rate_min=RATE_MIN, rate_max=RATE_MAX, flag_drop=FLAG_DROP)

Builder.load_string(KV)


class MainScreen(Screen):
    status_text = StringProperty("Pronto para iniciar")
    running = BooleanProperty(False)
    festa = BooleanProperty(False)
    festa_rate = NumericProperty(RATE_WEEKEND_DEFAULT)
    rate_per_km = NumericProperty(0.0)
    distance_km = NumericProperty(0.0)
    fare = NumericProperty(0.0)
    customer_name = StringProperty("")
    customer_phone = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_lat = None
        self._last_lon = None

    def open_menu(self):
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        history_btn = Button(
            text="Historico de corridas", size_hint_y=None, height=48
        )
        popup = Popup(
            title="Menu", content=content, size_hint=(0.8, 0.4), auto_dismiss=True
        )

        def go_history(*_args):
            popup.dismiss()
            self.manager.current = "history"

        history_btn.bind(on_release=go_history)
        content.add_widget(history_btn)
        popup.open()

    def set_festa(self, active):
        self.festa = active

    def set_festa_rate(self, value):
        self.festa_rate = value

    def toggle_ride(self):
        if self.running:
            self._stop_ride()
        else:
            self._start_ride()

    def _start_ride(self):
        self._last_lat = None
        self._last_lon = None
        self._started_at = datetime.now()
        self.distance_km = 0.0
        self.fare = FLAG_DROP
        self.rate_per_km = resolve_rate(
            self._started_at, festa=self.festa, festa_rate=self.festa_rate
        )
        self.running = True
        self.status_text = "Corrida em andamento..."
        if gps is not None:
            try:
                gps.configure(on_location=self._on_location, on_status=self._on_status)
                gps.start(minTime=1000, minDistance=5)
            except NotImplementedError:
                self.status_text = "GPS nao disponivel neste dispositivo"
        else:
            self.status_text = "GPS nao disponivel (plyer ausente)"

    def _stop_ride(self):
        self.running = False
        self.status_text = "Corrida finalizada"
        if gps is not None:
            try:
                gps.stop()
            except NotImplementedError:
                pass
        app = App.get_running_app()
        save_ride(
            app.db_path,
            customer_name=self.customer_name,
            customer_phone=self.customer_phone,
            distance_km=self.distance_km,
            rate_per_km=self.rate_per_km,
            fare=self.fare,
            started_at=getattr(self, "_started_at", datetime.now()),
        )
        self.customer_name = ""
        self.customer_phone = ""
        self.ids.name_input.text = ""
        self.ids.phone_input.text = ""

    def _on_status(self, stype, status):
        pass

    def _on_location(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        if lat is None or lon is None:
            return
        if self._last_lat is not None:
            step_km = haversine_km(self._last_lat, self._last_lon, lat, lon)
            if step_km <= MAX_PLAUSIBLE_STEP_KM:
                self.distance_km += step_km
                self.fare = FLAG_DROP + self.distance_km * self.rate_per_km
        self._last_lat = lat
        self._last_lon = lon


class HistoryScreen(Screen):
    def go_back(self):
        self.manager.current = "main"

    def on_pre_enter(self):
        self._refresh()

    def _refresh(self):
        container = self.ids.history_list
        container.clear_widgets()
        app = App.get_running_app()
        rides = list_rides(app.db_path)
        if not rides:
            container.add_widget(
                Label(
                    text="Nenhuma corrida registrada ainda.",
                    size_hint_y=None,
                    height=40,
                )
            )
            return
        for ride in rides:
            who = ride.customer_name or "Sem nome"
            if ride.customer_phone:
                who += " - " + ride.customer_phone
            text = (
                "[b]{date}[/b]  -  {who}\n"
                "{km:.2f} km x R$ {rate:.2f}/km  ->  [b]R$ {fare:.2f}[/b]"
            ).format(
                date=ride.started_at,
                who=who,
                km=ride.distance_km,
                rate=ride.rate_per_km,
                fare=ride.fare,
            )
            container.add_widget(
                Label(
                    text=text,
                    markup=True,
                    size_hint_y=None,
                    height=60,
                    halign="left",
                    valign="middle",
                )
            )


class TaximetroApp(App):
    def build(self):
        self._request_android_permissions()
        sm = ScreenManager()
        sm.add_widget(MainScreen())
        sm.add_widget(HistoryScreen())
        return sm

    @property
    def db_path(self):
        return os.path.join(self.user_data_dir, "rides.db")

    def _request_android_permissions(self):
        if platform != "android":
            return
        try:
            from android.permissions import Permission, request_permissions

            request_permissions(
                [Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION]
            )
        except Exception:
            pass


if __name__ == "__main__":
    TaximetroApp().run()
