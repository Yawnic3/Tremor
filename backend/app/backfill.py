from datetime import date

from backend.app.db import save_events
from backend.app.ingestion import request, usgs


def backfill(start: date, end: date) -> int:
    if not 0 < (end - start).days <= 31:
        raise ValueError("Backfill requires 1–31 days per request; end is exclusive.")
    payload = request(
        "https://earthquake.usgs.gov/fdsnws/event/1/query",
        {
            "format": "geojson",
            "starttime": start.isoformat(),
            "endtime": end.isoformat(),
            "minmagnitude": "4",
            "limit": "20000",
            "orderby": "time-asc",
            "minlatitude": "24",
            "maxlatitude": "50",
            "minlongitude": "-125",
            "maxlongitude": "-66",
        },
    ).json()
    if len(payload.get("features", [])) >= 20000:
        raise ValueError("Upstream record cap reached; split the requested interval.")
    return save_events([e for e in usgs(payload) if start <= e.start.date() < end])
