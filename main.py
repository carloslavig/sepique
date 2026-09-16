"""Taxímetro - MVP.

Tela do taxímetro: inicia/finaliza corrida, rastreia km via GPS e calcula o
valor em tempo real conforme a tarifa do momento (dia da semana / horário),
com opção de marcar "festa" para escolher a tarifa manualmente (vale só nos
fins de semana), campos opcionais de nome/telefone do cliente, e uma taxa de
espera quando o carro fica parado no trânsito. Cada corrida finalizada é
salva num histórico local, acessível pelo menu no canto superior esquerdo.
"""
import os
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import (
    BooleanProperty,
    ListProperty,
    NumericProperty,
    StringProperty,
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.utils import platform

from taximetro.distance import MAX_PLAUSIBLE_STEP_KM, haversine_km
from taximetro.fare import (
    FLAG_DROP,
    RATE_MAX,
    RATE_MIN,
    RATE_WEEKEND_DEFAULT,
    WaitingFeeTracker,
    is_weekend,
    resolve_rate,
)
from taximetro.offer import evaluate_offer, parse_offer_texts
from taximetro.offer_bridge import read_last_offer
from taximetro.storage import list_rides, save_ride

try:
    from plyer import gps
except Exception:
    gps = None

# Paleta escura, estilo app de corrida (Uber/99/Urbano Norte).
BG = "0.055, 0.06, 0.075, 1"
CARD_BG = "0.11, 0.115, 0.14, 1"
INPUT_BG = "0.16, 0.165, 0.2, 1"
ACCENT = "0.05, 0.85, 0.55, 1"
ACCENT_DIM = "0.05, 0.85, 0.55, 0.16"
DANGER = "0.95, 0.30, 0.38, 1"
TEXT_PRIMARY = "1, 1, 1, 1"
TEXT_SECONDARY = "0.66, 0.68, 0.74, 1"
TEXT_MUTED = "0.46, 0.48, 0.54, 1"
BORDER = "0.2, 0.21, 0.26, 1"
BUTTON_TEXT_BLUE = "0.35, 0.65, 1, 1"

KV = """
<TopBar@BoxLayout>:
    menu_callback: None
    title_text: ""
    size_hint_y: None
    height: dp(52)
    spacing: dp(10)
    padding: [0, dp(4)]

    IconButton:
        text: "="
        size_hint_x: None
        width: dp(44)
        on_release: root.menu_callback() if root.menu_callback else None

    Label:
        text: root.title_text
        font_size: "20sp"
        bold: True
        color: __TEXT_PRIMARY__
        halign: "left"
        valign: "middle"
        text_size: self.size

<IconButton@ButtonBehavior+BoxLayout>:
    text: ""
    canvas.before:
        Color:
            rgba: __CARD_BG__
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [12]

    Label:
        text: root.text
        font_size: "20sp"
        bold: True
        color: __TEXT_PRIMARY__

<Card@BoxLayout>:
    orientation: "vertical"
    padding: dp(18)
    spacing: dp(6)
    canvas.before:
        Color:
            rgba: __CARD_BG__
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [18]

<FieldRow@BoxLayout>:
    size_hint_y: None
    height: dp(46)
    canvas.before:
        Color:
            rgba: __INPUT_BG__
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [12]

<StyledInput@TextInput>:
    background_normal: ""
    background_active: ""
    background_color: 0, 0, 0, 0
    foreground_color: __TEXT_PRIMARY__
    hint_text_color: __TEXT_MUTED__
    cursor_color: __ACCENT__
    padding: [dp(14), dp(12)]
    multiline: False

<PillButton@ButtonBehavior+BoxLayout>:
    text: ""
    bg_color: __ACCENT__
    canvas.before:
        Color:
            rgba: self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [16]

    Label:
        text: root.text
        bold: True
        font_size: "19sp"
        color: __BUTTON_TEXT_BLUE__

<RideCard@BoxLayout>:
    orientation: "vertical"
    size_hint_y: None
    height: dp(84)
    padding: dp(14)
    spacing: dp(4)
    canvas.before:
        Color:
            rgba: __CARD_BG__
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [14]

<MainScreen>:
    name: "main"
    canvas.before:
        Color:
            rgba: __BG__
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        orientation: "vertical"
        padding: [dp(20), dp(12)]
        spacing: dp(10)

        TopBar:
            title_text: "Se Pique"
            menu_callback: root.open_menu

        ScrollView:
            do_scroll_x: False

            BoxLayout:
                orientation: "vertical"
                spacing: dp(16)
                padding: [0, dp(6)]
                size_hint_y: None
                height: self.minimum_height

                Card:
                    size_hint_y: None
                    height: dp(192)

                    Label:
                        text: root.status_text
                        font_size: "14sp"
                        color: __TEXT_SECONDARY__
                        size_hint_y: None
                        height: dp(20)
                        halign: "left"
                        text_size: self.size

                    Label:
                        text: "R$ {:.2f}".format(root.fare)
                        bold: True
                        font_size: "48sp"
                        color: __TEXT_PRIMARY__
                        size_hint_y: None
                        height: dp(60)
                        halign: "left"
                        text_size: self.size

                    Label:
                        text: "{:.2f} km  ({:.0f} m)   -   R$ {:.2f}/km".format(root.distance_km, root.distance_km * 1000, root.rate_per_km)
                        font_size: "13sp"
                        color: __TEXT_SECONDARY__
                        size_hint_y: None
                        height: dp(20)
                        halign: "left"
                        text_size: self.size

                    Label:
                        text: "+ R$ {:.2f} de espera (parado no transito)".format(root.waiting_fee)
                        font_size: "12sp"
                        color: __ACCENT__
                        size_hint_y: None
                        height: dp(18) if root.waiting_fee > 0 else 0
                        opacity: 1 if root.waiting_fee > 0 else 0
                        halign: "left"
                        text_size: self.size

                    Label:
                        text: "GPS recebeu: {} sinal(is)  -  {}".format(root.gps_fix_count, root.last_fix_info)
                        font_size: "11sp"
                        color: __TEXT_MUTED__
                        size_hint_y: None
                        height: dp(16)
                        halign: "left"
                        text_size: self.size

                Card:
                    size_hint_y: None
                    height: dp(120)

                    Label:
                        text: "Cliente (opcional)"
                        font_size: "12sp"
                        color: __TEXT_MUTED__
                        size_hint_y: None
                        height: dp(16)
                        halign: "left"
                        text_size: self.size

                    FieldRow:
                        StyledInput:
                            id: name_input
                            hint_text: "Nome"
                            disabled: root.running
                            on_text: root.customer_name = self.text

                    FieldRow:
                        StyledInput:
                            id: phone_input
                            hint_text: "Telefone"
                            disabled: root.running
                            on_text: root.customer_phone = self.text

                Card:
                    size_hint_y: None
                    height: dp(108) if root.festa else dp(60)
                    disabled: root.running

                    BoxLayout:
                        size_hint_y: None
                        height: dp(28)

                        Label:
                            text: "Festa (fim de semana): escolher valor"
                            font_size: "14sp"
                            color: __TEXT_PRIMARY__
                            halign: "left"
                            text_size: self.size

                        Switch:
                            size_hint_x: None
                            width: dp(58)
                            active: root.festa
                            on_active: root.set_festa(self.active)

                    BoxLayout:
                        size_hint_y: None
                        height: dp(36) if root.festa else 0
                        opacity: 1 if root.festa else 0
                        spacing: dp(12)
                        disabled: not root.festa

                        Label:
                            text: "R$ {:.2f}/km".format(root.festa_rate)
                            color: __TEXT_SECONDARY__
                            size_hint_x: None
                            width: dp(84)

                        Slider:
                            id: festa_slider
                            min: __RATE_MIN__
                            max: __RATE_MAX__
                            step: 0.10
                            value: root.festa_rate
                            cursor_size: dp(20), dp(20)
                            on_value: root.set_festa_rate(self.value)

                PillButton:
                    text: "Iniciar corrida" if not root.running else "Finalizar corrida"
                    bg_color: __DANGER__ if root.running else __ACCENT__
                    size_hint_y: None
                    height: dp(58)
                    on_release: root.toggle_ride()

<OfferScreen>:
    name: "offer"
    canvas.before:
        Color:
            rgba: __BG__
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        orientation: "vertical"
        padding: [dp(20), dp(12)]
        spacing: dp(10)

        TopBar:
            title_text: "Vale a corrida?"
            menu_callback: root.go_back

        ScrollView:
            do_scroll_x: False

            BoxLayout:
                orientation: "vertical"
                spacing: dp(16)
                padding: [0, dp(6)]
                size_hint_y: None
                height: self.minimum_height

                Card:
                    size_hint_y: None
                    height: dp(84)

                    Label:
                        text: "Deteccao automatica (Urbano Norte, inDriver, PopMove)"
                        font_size: "12sp"
                        color: __TEXT_MUTED__
                        halign: "left"
                        text_size: self.size
                        size_hint_y: None
                        height: dp(16)

                    Label:
                        text: root.autodetect_status_text
                        font_size: "13sp"
                        color: __TEXT_SECONDARY__
                        halign: "left"
                        text_size: self.size
                        size_hint_y: None
                        height: dp(20)

                    PillButton:
                        text: "Ativar nas configuracoes do Android"
                        bg_color: __CARD_BG__
                        size_hint_y: None
                        height: dp(36)
                        on_release: root.open_accessibility_settings()

                Card:
                    size_hint_y: None
                    height: dp(230)

                    Label:
                        text: "Distancia ate o passageiro (km)"
                        font_size: "12sp"
                        color: __TEXT_MUTED__
                        size_hint_y: None
                        height: dp(16)
                        halign: "left"
                        text_size: self.size

                    FieldRow:
                        StyledInput:
                            id: pickup_input
                            hint_text: "0.0"
                            input_filter: "float"

                    Label:
                        text: "Distancia da corrida (km)"
                        font_size: "12sp"
                        color: __TEXT_MUTED__
                        size_hint_y: None
                        height: dp(16)
                        halign: "left"
                        text_size: self.size

                    FieldRow:
                        StyledInput:
                            id: ride_input
                            hint_text: "0.0"
                            input_filter: "float"

                    Label:
                        text: "Valor oferecido (R$)"
                        font_size: "12sp"
                        color: __TEXT_MUTED__
                        size_hint_y: None
                        height: dp(16)
                        halign: "left"
                        text_size: self.size

                    FieldRow:
                        StyledInput:
                            id: value_input
                            hint_text: "0.0"
                            input_filter: "float"

                PillButton:
                    text: "Analisar"
                    bg_color: __ACCENT__
                    size_hint_y: None
                    height: dp(54)
                    on_release: root.analyze()

                Card:
                    size_hint_y: None
                    height: dp(90) if root.result_text else 0
                    opacity: 1 if root.result_text else 0

                    Label:
                        text: root.result_text
                        bold: True
                        font_size: "26sp"
                        color: root.result_color
                        size_hint_y: None
                        height: dp(34)
                        halign: "left"
                        text_size: self.size

                    Label:
                        text: root.result_detail
                        font_size: "13sp"
                        color: __TEXT_SECONDARY__
                        size_hint_y: None
                        height: dp(20)
                        halign: "left"
                        text_size: self.size

<HistoryScreen>:
    name: "history"
    canvas.before:
        Color:
            rgba: __BG__
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        orientation: "vertical"
        padding: dp(20)
        spacing: dp(16)

        TopBar:
            title_text: "Historico de corridas"
            menu_callback: root.go_back

        ScrollView:
            BoxLayout:
                id: history_list
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(10)
"""

for _token, _value in {
    "__BG__": BG,
    "__CARD_BG__": CARD_BG,
    "__INPUT_BG__": INPUT_BG,
    "__ACCENT__": ACCENT,
    "__ACCENT_DIM__": ACCENT_DIM,
    "__DANGER__": DANGER,
    "__TEXT_PRIMARY__": TEXT_PRIMARY,
    "__TEXT_SECONDARY__": TEXT_SECONDARY,
    "__TEXT_MUTED__": TEXT_MUTED,
    "__BORDER__": BORDER,
    "__BUTTON_TEXT_BLUE__": BUTTON_TEXT_BLUE,
    "__RATE_MIN__": str(RATE_MIN),
    "__RATE_MAX__": str(RATE_MAX),
}.items():
    KV = KV.replace(_token, _value)

Window.clearcolor = tuple(float(x) for x in BG.split(","))
Builder.load_string(KV)


class MainScreen(Screen):
    status_text = StringProperty("Pronto para iniciar")
    running = BooleanProperty(False)
    festa = BooleanProperty(False)
    festa_rate = NumericProperty(RATE_WEEKEND_DEFAULT)
    rate_per_km = NumericProperty(0.0)
    distance_km = NumericProperty(0.0)
    fare = NumericProperty(0.0)
    waiting_fee = NumericProperty(0.0)
    customer_name = StringProperty("")
    customer_phone = StringProperty("")
    gps_fix_count = NumericProperty(0)
    last_fix_info = StringProperty("nenhum sinal de GPS recebido ainda")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_lat = None
        self._last_lon = None
        self._waiting_tracker = None
        self._waiting_event = None

    def open_menu(self):
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        offer_btn = Factory.PillButton(
            text="Vale a corrida?", size_hint_y=None, height=48
        )
        history_btn = Factory.PillButton(
            text="Historico de corridas", size_hint_y=None, height=48
        )
        popup = Popup(
            title="Menu", content=content, size_hint=(0.8, 0.5), auto_dismiss=True
        )

        def go_offer(*_args):
            popup.dismiss()
            self.manager.current = "offer"

        def go_history(*_args):
            popup.dismiss()
            self.manager.current = "history"

        offer_btn.bind(on_release=go_offer)
        history_btn.bind(on_release=go_history)
        content.add_widget(offer_btn)
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
        self.waiting_fee = 0.0
        self.gps_fix_count = 0
        self.last_fix_info = "nenhum sinal de GPS recebido ainda"
        self._waiting_tracker = WaitingFeeTracker()
        self.rate_per_km = resolve_rate(
            self._started_at, festa=self.festa, festa_rate=self.festa_rate
        )
        self._recompute_fare()
        self.running = True
        self.status_text = "Corrida em andamento..."
        self._waiting_event = Clock.schedule_interval(self._on_waiting_tick, 60)
        self._start_gps()

    def _start_gps(self):
        if gps is None:
            self.status_text = "GPS nao disponivel (plyer ausente)"
            return
        if platform == "android" and not self._has_location_permission():
            self.status_text = "Sem permissao de localizacao - solicitando..."
            self._request_location_permission()
            return
        self._begin_gps_tracking()

    def _has_location_permission(self):
        try:
            from android.permissions import Permission, check_permission

            return check_permission(Permission.ACCESS_FINE_LOCATION) or check_permission(
                Permission.ACCESS_COARSE_LOCATION
            )
        except Exception:
            return True

    def _request_location_permission(self):
        try:
            from android.permissions import Permission, request_permissions

            request_permissions(
                [Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION],
                self._on_permission_result,
            )
        except Exception:
            self.status_text = "Nao foi possivel solicitar permissao de localizacao"

    def _on_permission_result(self, _permissions, grants):
        if not any(grants):
            self.status_text = "Permissao de localizacao negada"
            return
        if not self.running:
            return
        self._begin_gps_tracking()

    def _begin_gps_tracking(self):
        try:
            gps.configure(on_location=self._on_location, on_status=self._on_status)
            gps.start(minTime=1000, minDistance=5)
            self.status_text = "Corrida em andamento..."
        except Exception as exc:
            self.status_text = "Erro ao iniciar GPS: {}".format(exc)

    def _stop_ride(self):
        self.running = False
        self.status_text = "Corrida finalizada"
        if self._waiting_event is not None:
            self._waiting_event.cancel()
            self._waiting_event = None
        if gps is not None:
            try:
                gps.stop()
            except Exception:
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

    def _recompute_fare(self):
        self.fare = FLAG_DROP + self.distance_km * self.rate_per_km + self.waiting_fee

    def _on_waiting_tick(self, _dt):
        if self._waiting_tracker is None:
            return
        self.waiting_fee = self._waiting_tracker.tick_minute(self.distance_km)
        self._recompute_fare()

    def _on_status(self, stype, status):
        if stype == "provider-disabled":
            self.status_text = "Localizacao desligada no celular"
        elif stype == "provider-enabled" and self.running:
            self.status_text = "Corrida em andamento..."

    def _on_location(self, **kwargs):
        # O plyer entrega esse callback na thread do Android (Looper que
        # passamos pro requestLocationUpdates), nao na thread do Kivy.
        # Agendar com Clock.schedule_once garante que a mudanca de estado
        # (e o redesenho da tela) rode na thread certa.
        Clock.schedule_once(lambda _dt, kw=kwargs: self._apply_location(**kw), 0)

    def _apply_location(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        accuracy = kwargs.get("accuracy")
        self.gps_fix_count += 1
        self.last_fix_info = "lat={:.5f} lon={:.5f} precisao={}m".format(
            lat if lat is not None else 0.0,
            lon if lon is not None else 0.0,
            "{:.0f}".format(accuracy) if accuracy is not None else "?",
        )
        if lat is None or lon is None:
            return
        if self._last_lat is not None:
            step_km = haversine_km(self._last_lat, self._last_lon, lat, lon)
            if step_km <= MAX_PLAUSIBLE_STEP_KM:
                self.distance_km += step_km
                self._recompute_fare()
        self._last_lat = lat
        self._last_lon = lon


class OfferScreen(Screen):
    result_text = StringProperty("")
    result_detail = StringProperty("")
    result_color = ListProperty([float(x) for x in TEXT_PRIMARY.split(",")])
    autodetect_status_text = StringProperty(
        "Desligada. Ative nas configuracoes e volte pra essa tela."
    )

    def go_back(self):
        Clock.unschedule(self._poll_offer)
        self.manager.current = "main"

    def on_pre_enter(self):
        Clock.schedule_interval(self._poll_offer, 2)

    def on_leave(self):
        Clock.unschedule(self._poll_offer)

    def analyze(self):
        pickup = self._read_float(self.ids.pickup_input.text)
        ride = self._read_float(self.ids.ride_input.text)
        value = self._read_float(self.ids.value_input.text)
        ev = evaluate_offer(pickup, ride, value)
        if ev.worth_it:
            self.result_text = "VALE A PENA"
            self.result_color = [float(x) for x in ACCENT.split(",")]
        else:
            self.result_text = "NAO VALE A PENA"
            self.result_color = [float(x) for x in DANGER.split(",")]
        self.result_detail = "{total:.2f} km no total  ->  R$ {rate:.2f}/km".format(
            total=ev.total_km, rate=ev.rate_per_km
        )

    @staticmethod
    def _read_float(text):
        try:
            return float((text or "0").replace(",", "."))
        except ValueError:
            return 0.0

    def open_accessibility_settings(self):
        if platform != "android":
            self.autodetect_status_text = "So funciona no celular (Android)."
            return
        try:
            from jnius import autoclass

            Intent = autoclass("android.content.Intent")
            Settings = autoclass("android.provider.Settings")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
            PythonActivity.mActivity.startActivity(intent)
            self.autodetect_status_text = (
                "Procure 'Se Pique' na lista e ative. Depois volte pra essa tela."
            )
        except Exception:
            self.autodetect_status_text = "Nao consegui abrir as configuracoes."

    def _poll_offer(self, _dt):
        data = read_last_offer()
        if not data:
            return
        parsed = parse_offer_texts(data.get("texts", []))
        if not parsed:
            return
        self.ids.pickup_input.text = "{:.2f}".format(parsed["pickup_km"])
        self.ids.ride_input.text = "{:.2f}".format(parsed["ride_km"])
        self.ids.value_input.text = "{:.2f}".format(parsed["offered_value"])
        self.autodetect_status_text = "Pedido detectado agora ({}).".format(
            data.get("package", "?")
        )
        self.analyze()


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
            empty = Factory.Card(size_hint_y=None, height=60)
            empty.add_widget(
                Factory.Label(
                    text="Nenhuma corrida registrada ainda.",
                    color=[float(x) for x in TEXT_SECONDARY.split(",")],
                )
            )
            container.add_widget(empty)
            return
        for ride in rides:
            who = ride.customer_name or "Sem nome"
            if ride.customer_phone:
                who += "  -  " + ride.customer_phone
            card = Factory.RideCard()
            card.add_widget(
                Factory.Label(
                    text="[b]{date}[/b]  -  {who}".format(date=ride.started_at, who=who),
                    markup=True,
                    color=[float(x) for x in TEXT_PRIMARY.split(",")],
                    font_size="14sp",
                    halign="left",
                    valign="middle",
                    text_size=(Window.width - dp(72), None),
                    size_hint_y=None,
                    height=22,
                )
            )
            card.add_widget(
                Factory.Label(
                    text=(
                        "{km:.2f} km ({m:.0f} m) x R$ {rate:.2f}/km  ->  "
                        "[b]R$ {fare:.2f}[/b]"
                    ).format(
                        km=ride.distance_km,
                        m=ride.distance_km * 1000,
                        rate=ride.rate_per_km,
                        fare=ride.fare,
                    ),
                    markup=True,
                    color=[float(x) for x in TEXT_SECONDARY.split(",")],
                    font_size="13sp",
                    halign="left",
                    valign="middle",
                    text_size=(Window.width - dp(72), None),
                    size_hint_y=None,
                    height=22,
                )
            )
            container.add_widget(card)


class TaximetroApp(App):
    def build(self):
        self._request_android_permissions()
        sm = ScreenManager()
        sm.add_widget(MainScreen())
        sm.add_widget(OfferScreen())
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
