import os
from datetime import datetime

from taximetro.storage import list_rides, save_ride


def test_list_rides_empty_when_no_db(tmp_path):
    db_path = os.path.join(tmp_path, "rides.db")
    assert list_rides(db_path) == []


def test_save_and_list_ride(tmp_path):
    db_path = os.path.join(tmp_path, "rides.db")
    save_ride(
        db_path,
        customer_name="  Joao  ",
        customer_phone=" 11 91234-5678 ",
        distance_km=5.2,
        rate_per_km=2.0,
        fare=22.4,
        started_at=datetime(2026, 9, 15, 14, 30),
    )
    rides = list_rides(db_path)
    assert len(rides) == 1
    ride = rides[0]
    assert ride.customer_name == "Joao"
    assert ride.customer_phone == "11 91234-5678"
    assert ride.distance_km == 5.2
    assert ride.rate_per_km == 2.0
    assert ride.fare == 22.4
    assert ride.started_at == "15/09/2026 14:30"


def test_rides_ordered_most_recent_first(tmp_path):
    db_path = os.path.join(tmp_path, "rides.db")
    save_ride(db_path, "", "", 1.0, 2.0, 14.0, started_at=datetime(2026, 9, 1, 8, 0))
    save_ride(db_path, "", "", 2.0, 2.0, 16.0, started_at=datetime(2026, 9, 2, 8, 0))
    rides = list_rides(db_path)
    assert [r.distance_km for r in rides] == [2.0, 1.0]
