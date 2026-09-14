"""Cálculo de distância entre coordenadas GPS (fórmula de haversine)."""
from math import atan2, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088

# Acima disso entre duas leituras consecutivas, tratamos como salto de GPS
# (erro de sinal) e ignoramos a leitura ao invés de somar à corrida.
MAX_PLAUSIBLE_STEP_KM = 0.5


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * atan2(sqrt(a), sqrt(1 - a))
