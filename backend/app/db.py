import os
import sqlite3
from pathlib import Path

from backend.app.models import Event


def connect() -> sqlite3.Connection:
    path = Path(os.getenv('EVENTMAP_DB', 'data/runtime/eventmap.db'))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY, lat REAL, lon REAL, start TEXT, payload TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS events_space ON events(lat, lon);
        CREATE INDEX IF NOT EXISTS events_time ON events(start);
        CREATE TABLE IF NOT EXISTS runs (
            source TEXT PRIMARY KEY, fetched_at TEXT, count INTEGER, error TEXT);
    ''')
    return conn


def save_events(events: list[Event]) -> int:
    with connect() as conn:
        conn.executemany('INSERT OR REPLACE INTO events VALUES (?,?,?,?,?)', [
            (e.id, e.lat, e.lon, e.start.isoformat(), e.model_dump_json()) for e in events
        ])
    return len(events)


def list_events(bbox: tuple[float, float, float, float] | None = None) -> list[Event]:
    with connect() as conn:
        if bbox:
            west, south, east, north = bbox
            rows = conn.execute('SELECT payload FROM events WHERE lat BETWEEN ? AND ? '
                                'AND lon BETWEEN ? AND ? ORDER BY start DESC',
                                (south, north, west, east)).fetchall()
        else:
            rows = conn.execute('SELECT payload FROM events ORDER BY start DESC').fetchall()
    return [Event.model_validate_json(row['payload']) for row in rows]
