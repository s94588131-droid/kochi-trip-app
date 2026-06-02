from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS price_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checked_at TEXT NOT NULL,
    departure_date TEXT NOT NULL,
    return_date TEXT NOT NULL,
    guests INTEGER NOT NULL,
    baggage_plan TEXT NOT NULL,
    seat_plan TEXT NOT NULL,
    outbound_fare INTEGER NOT NULL,
    return_fare INTEGER NOT NULL,
    baggage_fee INTEGER NOT NULL,
    seat_fee INTEGER NOT NULL,
    hotel_fee INTEGER NOT NULL,
    total_price INTEGER NOT NULL,
    booking_url TEXT NOT NULL,
    hotel_url TEXT NOT NULL,
    source TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def get_database_path(default_path: str = "travel_prices.sqlite3") -> Path:
    return Path(default_path).expanduser().resolve()


def init_db(db_path: str = "travel_prices.sqlite3") -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def connect(db_path: str = "travel_prices.sqlite3") -> Iterator[sqlite3.Connection]:
    path = get_database_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def save_price_check(record: dict[str, Any], db_path: str = "travel_prices.sqlite3") -> int:
    fields = [
        "checked_at",
        "departure_date",
        "return_date",
        "guests",
        "baggage_plan",
        "seat_plan",
        "outbound_fare",
        "return_fare",
        "baggage_fee",
        "seat_fee",
        "hotel_fee",
        "total_price",
        "booking_url",
        "hotel_url",
        "source",
        "notes",
    ]
    values = [record.get(field) for field in fields]
    placeholders = ", ".join(["?"] * len(fields))
    with connect(db_path) as conn:
        cursor = conn.execute(
            f"INSERT INTO price_checks ({', '.join(fields)}) VALUES ({placeholders})",
            values,
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_price_checks(limit: int = 50, db_path: str = "travel_prices.sqlite3") -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM price_checks
            ORDER BY datetime(checked_at) DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_previous_check(
    departure_date: str,
    return_date: str,
    guests: int,
    baggage_plan: str,
    seat_plan: str,
    db_path: str = "travel_prices.sqlite3",
) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM price_checks
            WHERE departure_date = ?
              AND return_date = ?
              AND guests = ?
              AND baggage_plan = ?
              AND seat_plan = ?
            ORDER BY datetime(checked_at) DESC, id DESC
            LIMIT 1
            """,
            (departure_date, return_date, guests, baggage_plan, seat_plan),
        ).fetchone()
    return dict(row) if row else None


def get_best_check(db_path: str = "travel_prices.sqlite3") -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM price_checks
            ORDER BY total_price ASC, datetime(checked_at) DESC
            LIMIT 1
            """
        ).fetchone()
    return dict(row) if row else None


def get_rankings(limit: int = 20, db_path: str = "travel_prices.sqlite3") -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM price_checks
            ORDER BY total_price ASC, datetime(checked_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_setting(key: str, value: str | None, db_path: str = "travel_prices.sqlite3") -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        conn.commit()


def get_settings(db_path: str = "travel_prices.sqlite3") -> dict[str, str | None]:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {str(row["key"]): row["value"] for row in rows}


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()
