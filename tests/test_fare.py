from datetime import datetime

from taximetro.fare import RATE_MAX, RATE_MIN, resolve_rate


def dt(year=2026, month=9, day=1, hour=12, minute=0):
    return datetime(year, month, day, hour, minute)


def test_weekday_commercial_hours():
    # 2026-09-01 e uma terca-feira, 10h
    assert resolve_rate(dt(day=1, hour=10)) == 2.00


def test_weekday_night():
    # 22h de terca-feira
    assert resolve_rate(dt(day=1, hour=22)) == 3.00


def test_weekday_early_morning_is_night():
    assert resolve_rate(dt(day=1, hour=5)) == 3.00


def test_weekend_default():
    # 2026-09-05 e um sabado
    assert resolve_rate(dt(day=5, hour=14)) == 3.50


def test_weekend_festa_custom_rate():
    assert resolve_rate(dt(day=5, hour=23), festa=True, festa_rate=4.20) == 4.20


def test_weekend_festa_clamps_to_bounds():
    assert resolve_rate(dt(day=5, hour=23), festa=True, festa_rate=10.0) == RATE_MAX
    assert resolve_rate(dt(day=5, hour=23), festa=True, festa_rate=0.5) == RATE_MIN


def test_festa_ignored_on_weekdays():
    assert resolve_rate(dt(day=1, hour=10), festa=True, festa_rate=4.99) == 2.00
