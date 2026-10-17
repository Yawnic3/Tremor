import httpx
from typing import Any
import pytest
from fastapi.testclient import TestClient

from backend.app.cli import seed
from backend.app.db import list_events, save_events
from backend.app.ingestion import ingest, nws, usgs
from backend.app.main import app


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    monkeypatch.setenv("TREMOR_DB", str(tmp_path / "test.db"))


def test_seed_idempotent_and_filters():
    seed()
    seed()
    assert len(list_events()) == 56
    client = TestClient(app)
    result = client.get("/api/events?type=fire&severity=4&start=2026-09-01").json()
    assert len(result) == 1
    assert result[0]["synthetic"]
    assert client.get("/api/events?demo=false").json() == []
    assert client.get("/api/events?bbox=bad").status_code == 422
    assert client.get("/api/events?start=2026-10-01&end=2026-01-01").status_code == 422


def test_usgs_normalization():
    payload = {
        "features": [
            {
                "id": "abc",
                "geometry": {"coordinates": [-122, 38, 10]},
                "properties": {
                    "time": 1700000000000,
                    "mag": 6.2,
                    "url": "https://earthquake.usgs.gov/earthquakes/eventpage/abc",
                },
            }
        ]
    }
    events = usgs(payload)
    save_events(events)
    save_events(events)
    assert len(list_events()) == 1
    assert events[0].severity == 5 and events[0].region == "US West"


def test_nws_polygon_and_missing_geometry():
    feature: dict[str, Any] = {"id": "https://api.weather.gov/alerts/abc", "geometry": None, "properties": {}}
    assert nws({"features": [feature]}) == []
    feature["geometry"] = {
        "type": "Polygon",
        "coordinates": [[[-96, 29], [-94, 29], [-94, 31], [-96, 31], [-96, 29]]],
    }
    feature["properties"] = {"event": "Flood Warning", "sent": "2026-09-01T12:00:00Z", "severity": "Severe"}
    event = nws({"features": [feature]})[0]
    assert event.lat == 30 and event.lon == -95 and event.severity == 4


def test_failed_source_backoff(monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("backend.app.ingestion.request", fail)
    assert ingest("usgs")["error"]
    assert ingest("usgs")["cached"]
