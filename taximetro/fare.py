"""Regras de precificação do taxímetro."""
from datetime import datetime, time
from typing import Optional

RATE_MIN = 2.00
RATE_MAX = 5.00

FLAG_DROP = 12.00  # bandeirada: valor inicial da corrida, antes de rodar km

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


# Taxa de espera: se o carro não andar pelo menos WAITING_MIN_KM a cada
# WAITING_CHECK_INTERVAL_MIN minutos (trânsito parado, sinal etc.), soma
# WAITING_FEE_PER_MINUTE a cada minuto adicional que ficar devendo essa
# distância, até que ela seja cumprida (aí o ciclo de checagem reinicia).
WAITING_CHECK_INTERVAL_MIN = 3
WAITING_MIN_KM = 1.0
WAITING_FEE_PER_MINUTE = 0.60


class WaitingFeeTracker:
    """Acumula a taxa de espera minuto a minuto ao longo de uma corrida."""

    def __init__(self) -> None:
        self.extra_fee = 0.0
        self._checkpoint_km = 0.0
        self._minutes_since_checkpoint = 0

    def tick_minute(self, total_distance_km: float) -> float:
        """Chamar uma vez por minuto decorrido de corrida.

        Retorna o valor acumulado de taxa de espera (R$) até agora.
        """
        self._minutes_since_checkpoint += 1
        if self._minutes_since_checkpoint < WAITING_CHECK_INTERVAL_MIN:
            return self.extra_fee

        covered = total_distance_km - self._checkpoint_km
        if covered < WAITING_MIN_KM:
            self.extra_fee += WAITING_FEE_PER_MINUTE
        else:
            self._checkpoint_km = total_distance_km
            self._minutes_since_checkpoint = 0
        return self.extra_fee
