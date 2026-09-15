from taximetro.fare import WAITING_FEE_PER_MINUTE, WaitingFeeTracker


def test_no_fee_before_3_minutes_even_if_stopped():
    t = WaitingFeeTracker()
    assert t.tick_minute(0.0) == 0.0
    assert t.tick_minute(0.0) == 0.0


def test_fee_kicks_in_at_3rd_minute_if_stopped():
    t = WaitingFeeTracker()
    t.tick_minute(0.0)
    t.tick_minute(0.0)
    assert t.tick_minute(0.0) == WAITING_FEE_PER_MINUTE


def test_fee_keeps_growing_each_minute_while_still_behind():
    t = WaitingFeeTracker()
    for _ in range(3):
        t.tick_minute(0.0)
    assert t.tick_minute(0.0) == WAITING_FEE_PER_MINUTE * 2
    assert t.tick_minute(0.0) == WAITING_FEE_PER_MINUTE * 3


def test_no_fee_when_pace_is_kept():
    t = WaitingFeeTracker()
    # 1km a cada 3 min = ritmo em dia, nunca deve cobrar
    for minute in range(1, 10):
        fee = t.tick_minute(minute * (1.0 / 3))
    assert fee == 0.0


def test_catching_up_resets_the_window():
    t = WaitingFeeTracker()
    t.tick_minute(0.0)
    t.tick_minute(0.0)
    fee = t.tick_minute(0.0)
    assert fee == WAITING_FEE_PER_MINUTE
    # anda 1km de uma vez: cumpriu a distancia, zera a janela sem cobrar mais
    fee = t.tick_minute(1.0)
    assert fee == WAITING_FEE_PER_MINUTE
    # novo ciclo de 3 min comeca agora; parado de novo nao cobra antes da hora
    fee = t.tick_minute(1.0)
    assert fee == WAITING_FEE_PER_MINUTE
    fee = t.tick_minute(1.0)
    assert fee == WAITING_FEE_PER_MINUTE
    fee = t.tick_minute(1.0)
    assert fee == WAITING_FEE_PER_MINUTE * 2
