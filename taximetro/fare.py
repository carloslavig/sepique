"""Regras de precificação do taxímetro."""
from datetime import datetime, time
from typing import Optional

RATE_MIN = 2.00
RATE_MAX = 5.00

RATE_WEEKDAY_COMMERCIAL = 2.00
RATE_WEEKDAY_NIGHT = 3.00
RATE_WEEKEND_DEFAULT = 3.50

COMMERCIAL_START = time(8, 0)
COMMERCIAL_END = time(18, 0)


def is_weekend(dt: datetime) -> bool:
    return dt.weekday() >= 5  # 5 = sábado, 6 = domingo


def is_commercial_hours(dt: datetime) -> bool:
    return COMMERCIAL_START <= dt.time() < COMMERCIAL_END


def default_rate_per_km(dt: Optional[datetime] = None) -> float:
    """Tarifa padrão por km conforme dia da semana e horário."""
    dt = dt or datetime.now()
    if is_weekend(dt):
        return RATE_WEEKEND_DEFAULT
    if is_commercial_hours(dt):
        return RATE_WEEKDAY_COMMERCIAL
    return RATE_WEEKDAY_NIGHT


def resolve_rate(
    dt: Optional[datetime] = None,
    festa: bool = False,
    festa_rate: Optional[float] = None,
) -> float:
    """Resolve a tarifa (R$/km) para a corrida.

    Em fins de semana, se `festa` estiver marcada, usa `festa_rate`
    (limitada entre RATE_MIN e RATE_MAX) no lugar do valor padrão do fim de
    semana. Fora do fim de semana, `festa` é ignorada.
    """
    dt = dt or datetime.now()
    if is_weekend(dt) and festa:
        rate = festa_rate if festa_rate is not None else RATE_WEEKEND_DEFAULT
        return max(RATE_MIN, min(RATE_MAX, rate))
    return default_rate_per_km(dt)
