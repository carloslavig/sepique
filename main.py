"""Taxímetro - MVP.

Tela única: inicia/finaliza corrida, rastreia km via GPS e calcula o valor
em tempo real conforme a tarifa do momento (dia da semana / horário), com
opção de marcar "festa" nos fins de semana para escolher a tarifa manualmente.
"""
import os
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import platform

from taximetro.distance import MAX_PLAUSIBLE_STEP_KM, haversine_km
from taximetro.fare import RATE_MAX, RATE_MIN, RATE_WEEKEND_DEFAULT, is_weekend, resolve_rate

try:
    from plyer import gps
except Exception:
    gps = None

KV = """
<Taximetro>:
    orientation: "vertical"
    padding: dp(24)
    spacing: dp(16)

    Label:
        text: "Se Pique"
        font_size: "28sp"
        size_hint_y: None
        height: dp(48)

    Label:
        text: root.status_text
        font_size: "16sp"
        size_hint_y: None
        height: dp(28)

    Label:
        text: "[b]R$ {{:.2f}}[/b]".format(root.fare)
        markup: True
        font_size: "56sp"
        size_hint_y: None
        height: dp(80)

    Label:
        text: "{{:.2f}} km   R$ {{:.2f}}/km".format(root.distance_km, root.rate_per_km)
        font_size: "18sp"
        size_hint_y: None
        height: dp(28)

    BoxLayout:
        size_hint_y: None
        height: dp(48)
        spacing: dp(12)
        disabled: root.running or not root.is_weekend_now

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
        height: dp(48)
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

    Button:
        text: "Iniciar corrida" if not root.running else "Finalizar corrida"
        font_size: "20sp"
        size_hint_y: None
        height: dp(64)
        on_release: root.toggle_ride()
""".format(rate_min=RATE_MIN, rate_max=RATE_MAX)

Builder.load_string(KV)


class Taximetro(BoxLayout):
    status_text = StringProperty("Pronto para iniciar")
    running = BooleanProperty(False)
    festa = BooleanProperty(False)
    festa_rate = NumericProperty(RATE_WEEKEND_DEFAULT)
    rate_per_km = NumericProperty(0.0)
    distance_km = NumericProperty(0.0)
    fare = NumericProperty(0.0)
    is_weekend_now = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_lat = None
        self._last_lon = None
        self.is_weekend_now = is_weekend(datetime.now())
        Clock.schedule_interval(self._refresh_weekend_flag, 60)

    def _refresh_weekend_flag(self, dt):
        self.is_weekend_now = is_weekend(datetime.now())
        if not self.is_weekend_now:
            self.festa = False

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
        self.distance_km = 0.0
        self.fare = 0.0
        self.rate_per_km = resolve_rate(
            datetime.now(), festa=self.festa, festa_rate=self.festa_rate
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
                self.fare = self.distance_km * self.rate_per_km
        self._last_lat = lat
        self._last_lon = lon


class TaximetroApp(App):
    def build(self):
        self._request_android_permissions()
        return Taximetro()

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
