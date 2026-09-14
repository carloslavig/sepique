from taximetro.distance import haversine_km


def test_same_point_is_zero():
    assert haversine_km(-23.5505, -46.6333, -23.5505, -46.6333) == 0.0


def test_known_distance_approx():
    # Sao Paulo (Se) -> Rio de Janeiro (Cristo Redentor), ~360km em linha reta
    d = haversine_km(-23.5505, -46.6333, -22.9519, -43.2105)
    assert 350 < d < 370
