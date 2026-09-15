from taximetro.offer import evaluate_offer, parse_offer_texts


def test_worth_it_when_rate_meets_minimum():
    ev = evaluate_offer(pickup_km=1.0, ride_km=4.0, offered_value=10.0)
    assert ev.total_km == 5.0
    assert ev.rate_per_km == 2.0
    assert ev.worth_it is True


def test_not_worth_it_when_below_minimum():
    ev = evaluate_offer(pickup_km=2.0, ride_km=4.0, offered_value=10.0)
    # 10 / 6 = 1.666..., abaixo de R$2/km
    assert ev.worth_it is False


def test_pickup_distance_counts_toward_total():
    # corrida boa por si so, mas a distancia ate o passageiro estraga
    close = evaluate_offer(pickup_km=0.0, ride_km=5.0, offered_value=10.0)
    far = evaluate_offer(pickup_km=5.0, ride_km=5.0, offered_value=10.0)
    assert close.worth_it is True
    assert far.worth_it is False


def test_zero_total_distance_is_never_worth_it():
    ev = evaluate_offer(pickup_km=0.0, ride_km=0.0, offered_value=10.0)
    assert ev.worth_it is False
    assert ev.rate_per_km == 0.0


def test_custom_minimum_rate():
    ev = evaluate_offer(pickup_km=0.0, ride_km=2.0, offered_value=7.0, min_rate_per_km=3.0)
    assert ev.rate_per_km == 3.5
    assert ev.worth_it is True


def test_parse_offer_texts_two_distances_and_currency():
    result = parse_offer_texts(
        ["R$ 18,50", "1,2 km ate voce", "5,4 km de viagem", "Aceitar"]
    )
    assert result == {"offered_value": 18.50, "pickup_km": 1.2, "ride_km": 5.4}


def test_parse_offer_texts_single_distance_treated_as_ride():
    result = parse_offer_texts(["R$ 9,00", "3 km"])
    assert result == {"offered_value": 9.0, "pickup_km": 0.0, "ride_km": 3.0}


def test_parse_offer_texts_thousands_separator():
    result = parse_offer_texts(["R$ 1.234,56", "2 km"])
    assert result["offered_value"] == 1234.56


def test_parse_offer_texts_no_useful_data_returns_none():
    assert parse_offer_texts(["Ola", "Aceitar", "Recusar"]) is None
