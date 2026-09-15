"""Persistência local do histórico de corridas (SQLite)."""
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from typing import List, NamedTuple, Optional


class Ride(NamedTuple):
    id: int
    started_at: str
    customer_name: str
    customer_phone: str
    distance_km: float
    rate_per_km: float
    fare: float


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            customer_name TEXT NOT NULL DEFAULT '',
            customer_phone TEXT NOT NULL DEFAULT '',
            distance_km REAL NOT NULL,
            rate_per_km REAL NOT NULL,
            fare REAL NOT NULL
        )
        """
    )
    return conn


def save_ride(
    db_path: str,
    customer_name: str,
    customer_phone: str,
    distance_km: float,
    rate_per_km: float,
    fare: float,
    started_at: Optional[datetime] = None,
) -> None:
    started_at = started_at or datetime.now()
    with closing(_connect(db_path)) as conn:
        conn.execute(
            "INSERT INTO rides (started_at, customer_name, customer_phone, "
            "distance_km, rate_per_km, fare) VALUES (?, ?, ?, ?, ?, ?)",
            (
                started_at.strftime("%d/%m/%Y %H:%M"),
                customer_name.strip(),
                customer_phone.strip(),
                distance_km,
                rate_per_km,
                fare,
            ),
        )
        conn.commit()


def list_rides(db_path: str) -> List[Ride]:
    if not os.path.exists(db_path):
        return []
    with closing(_connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT id, started_at, customer_name, customer_phone, "
            "distance_km, rate_per_km, fare FROM rides ORDER BY id DESC"
        ).fetchall()
    return [Ride(*row) for row in rows]
