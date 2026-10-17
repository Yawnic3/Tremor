import os
import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path

from backend.app.models import Event


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = Path(os.getenv("TREMOR_DB", "data/runtime/tremor.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY, lat REAL, lon REAL, start TEXT, payload TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS events_space ON events(lat, lon);
        CREATE INDEX IF NOT EXISTS events_time ON events(start);
        CREATE TABLE IF NOT EXISTS runs (
            source TEXT PRIMARY KEY, fetched_at TEXT, count INTEGER, error TEXT);
    """)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def save_events(events: list[Event]) -> int:
    with connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO events VALUES (?,?,?,?,?)",
            [(e.id, e.lat, e.lon, e.start.isoformat(), e.model_dump_json()) for e in events],
        )
    return len(events)


def list_events(bbox: tuple[float, float, float, float] | None = None) -> list[Event]:
    with connect() as conn:
        if bbox:
            west, south, east, north = bbox
            rows = conn.execute(
                "SELECT payload FROM events WHERE lat BETWEEN ? AND ? "
                "AND lon BETWEEN ? AND ? ORDER BY start DESC",
                (south, north, west, east),
            ).fetchall()
        else:
            rows = conn.execute("SELECT payload FROM events ORDER BY start DESC").fetchall()
    return [Event.model_validate_json(row["payload"]) for row in rows]
