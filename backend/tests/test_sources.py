from datetime import date, datetime, timezone
import pytest

from backend.app.additional_sources import firms, gdelt
from backend.app.backfill import backfill
from backend.app.analytics import history
from backend.app.cli import seed
from backend.app.main import event_detail


def test_firms_stable_id():
    csv = "latitude,longitude,acq_date,acq_time,satellite,instrument\n34,-118,2026-09-01,45,N20,VIIRS\n"
    a = firms(csv)
    assert a == firms(csv)
    assert a[0].start.hour == 0 and a[0].start.minute == 45
    assert a[0].type == "fire"


def test_gdelt_untrusted_html_never_rendered():
    payload = {
        "features": [
            {
                "geometry": {"type": "Point", "coordinates": [-74, 40]},
                "properties": {
                    "name": "New York",
                    "html": "<script>bad()</script>"
                    '<a href="javascript:bad()">bad</a>'
                    '<a href="https://example.com/report">report</a>',
                },
            }
        ]
    }
    result = gdelt(payload, datetime(2026, 9, 1, tzinfo=timezone.utc))[0]
    assert str(result.url) == "https://example.com/report"
    assert "NOT incident time" in result.description


def test_backfill_bounds():
    with pytest.raises(ValueError):
        backfill(date(2026, 1, 1), date(2026, 3, 1))


def test_demo_history_complete(tmp_path, monkeypatch):
    monkeypatch.setenv("TREMOR_DB", str(tmp_path / "test.db"))
    seed()
    result = history(event_detail("demo:0"))
    assert result.synthetic
    assert all(r.n_events == 6 and r.mean_car is not None for r in result.results)
