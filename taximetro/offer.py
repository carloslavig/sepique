"""Avalia se um pedido de corrida de outro app (Urbano Norte, inDriver,
PopMove...) compensa aceitar.

Considera a distância até o passageiro (deslocamento até buscar) somada à
distância da corrida em si: o valor oferecido precisa cobrir pelo menos
RATE_MIN por km rodado no total, não só na corrida.
"""
import re
from typing import List, NamedTuple, Optional

from .fare import RATE_MIN


class OfferEvaluation(NamedTuple):
    pickup_km: float
    ride_km: float
    total_km: float
    offered_value: float
    rate_per_km: float
    worth_it: bool


def evaluate_offer(
    pickup_km: float,
    ride_km: float,
    offered_value: float,
    min_rate_per_km: float = RATE_MIN,
) -> OfferEvaluation:
    """Decide se um pedido de corrida compensa aceitar."""
    total_km = max(0.0, pickup_km) + max(0.0, ride_km)
    if total_km <= 0:
        rate_per_km = 0.0
    else:
        rate_per_km = offered_value / total_km
    return OfferEvaluation(
        pickup_km=pickup_km,
        ride_km=ride_km,
        total_km=total_km,
        offered_value=offered_value,
        rate_per_km=rate_per_km,
        worth_it=total_km > 0 and rate_per_km >= min_rate_per_km,
    )


_CURRENCY_RE = re.compile(r"R\$\s*([\d]{1,3}(?:\.\d{3})*(?:,\d{1,2})?|\d+(?:,\d{1,2})?)")
_KM_RE = re.compile(r"([\d]+(?:[.,]\d+)?)\s*km", re.IGNORECASE)


def _to_float(raw: str) -> float:
    # "1.234,56" (milhar+decimal BR) ou "3,5" (decimal BR) ou "3.5" (decimal US)
    raw = raw.strip()
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    return float(raw)


def parse_offer_texts(
    texts: List[str],
) -> Optional[dict]:
    """Extrai valor oferecido e distâncias a partir dos textos da tela de
    outro app (capturados via serviço de acessibilidade).

    Heurística: pega o primeiro valor "R$" encontrado como valor oferecido;
    se houver 2+ distâncias em km, assume que a menor é até o passageiro e a
    maior é a da corrida; se houver só 1, trata como distância da corrida
    (pickup = 0). Retorna None se não achar valor nem distância nenhuma.
    Pensado para ser ajustado depois de ver telas reais dos apps.
    """
    joined = " | ".join(texts)

    money_matches = [_to_float(m) for m in _CURRENCY_RE.findall(joined)]
    km_matches = [_to_float(m) for m in _KM_RE.findall(joined)]

    if not money_matches and not km_matches:
        return None

    offered_value = money_matches[0] if money_matches else 0.0

    if len(km_matches) >= 2:
        ordered = sorted(km_matches[:2])
        pickup_km, ride_km = ordered[0], ordered[1]
    elif len(km_matches) == 1:
        pickup_km, ride_km = 0.0, km_matches[0]
    else:
        pickup_km, ride_km = 0.0, 0.0

    return {
        "offered_value": offered_value,
        "pickup_km": pickup_km,
        "ride_km": ride_km,
    }
