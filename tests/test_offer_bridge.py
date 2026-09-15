import json
import os

from taximetro.offer_bridge import read_last_offer, reset_last_seen


def _write(path, detected_at_ms, texts):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"package": "sinet.startup.inDriver", "detected_at_ms": detected_at_ms, "texts": texts}, fh)


def test_missing_file_returns_none(tmp_path):
    reset_last_seen()
    path = os.path.join(tmp_path, "last_offer.json")
    assert read_last_offer(path) is None


def test_reads_a_fresh_offer(tmp_path):
    reset_last_seen()
    path = os.path.join(tmp_path, "last_offer.json")
    _write(path, 1000, ["R$ 10,00", "3 km"])
    data = read_last_offer(path)
    assert data is not None
    assert data["texts"] == ["R$ 10,00", "3 km"]


def test_does_not_return_the_same_offer_twice(tmp_path):
    reset_last_seen()
    path = os.path.join(tmp_path, "last_offer.json")
    _write(path, 1000, ["R$ 10,00", "3 km"])
    assert read_last_offer(path) is not None
    assert read_last_offer(path) is None


def test_returns_only_when_newer_than_last_seen(tmp_path):
    reset_last_seen()
    path = os.path.join(tmp_path, "last_offer.json")
    _write(path, 1000, ["R$ 10,00", "3 km"])
    read_last_offer(path)
    _write(path, 2000, ["R$ 20,00", "5 km"])
    data = read_last_offer(path)
    assert data["texts"] == ["R$ 20,00", "5 km"]
