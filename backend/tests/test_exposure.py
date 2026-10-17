import pytest
from fastapi.testclient import TestClient
from backend.app.cli import seed
from backend.app.exposure import companies, distance, match
from backend.app.main import app, event_detail


def test_dataset():
    dataset = companies()
    assert len(dataset) == 50
    assert len({c.ticker for c in dataset}) == 50
    assert all(f.source and f.quality_note and f.weight is None for c in dataset for f in c.facilities)


def test_distance():
    assert distance(0, 0, 0, 0) == 0
    assert distance(0, 0, 0, 1) == pytest.approx(111.195, rel=1e-4)
    assert distance(0, 179.5, 0, -179.5) == pytest.approx(111.195, rel=1e-4)


def test_ranking(tmp_path, monkeypatch):
    monkeypatch.setenv("TREMOR_DB", str(tmp_path / "test.db"))
    seed()
    result = match(event_detail("demo:0"))
    assert any(e.ticker == "AAPL" for e in result)
    assert result == sorted(result, key=lambda e: (-e.score, e.ticker))
    assert not match(event_detail("demo:0"), 1)
    client = TestClient(app)
    assert client.get("/api/events/demo:0/exposure?radius_km=0").status_code == 422
    assert client.get("/api/events/missing/exposure").status_code == 404
