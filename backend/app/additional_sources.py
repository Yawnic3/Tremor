import csv
import hashlib
import io
import os
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

from backend.app.models import Event, EventType, region_for


def firms(payload: str) -> list[Event]:
    reader = csv.DictReader(io.StringIO(payload))
    if not reader.fieldnames or not {"latitude", "longitude", "acq_date", "acq_time"} <= set(
        reader.fieldnames
    ):
        raise ValueError("Invalid FIRMS CSV response")
    rows = list(reader)
    result = []
    for row in rows:
        lat, lon = float(row["latitude"]), float(row["longitude"])
        when = datetime.strptime(row["acq_date"] + row["acq_time"].zfill(4), "%Y-%m-%d%H%M").replace(
            tzinfo=timezone.utc
        )
        key = f"{lat}:{lon}:{when.isoformat()}:{row.get('satellite', '')}:{row.get('instrument', '')}"
        result.append(
            Event.model_validate(
                dict(
                    id="firms:" + hashlib.sha256(key.encode()).hexdigest()[:24],
                    title="Satellite thermal anomaly",
                    type="fire",
                    lat=lat,
                    lon=lon,
                    start=when,
                    severity=2,
                    source="NASA FIRMS",
                    url="https://firms.modaps.eosdis.nasa.gov/map/",
                    region=region_for(lat, lon),
                    raw=row,
                    description="Thermal hotspot detection, not a confirmed wildfire perimeter or damage assessment. "
                    "Severity 2 is an unknown-impact display default; confidence/FRP retained in raw data.",
                )
            )
        )
    return result


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value and value.startswith(("https://", "http://")):
                    self.urls.append(value)


def gdelt(payload: dict[str, Any], fetched_at: datetime, kind: EventType = "protest") -> list[Event]:
    if not isinstance(payload.get("features"), list):
        raise ValueError("Invalid GDELT GeoJSON response")
    result = []
    for feature in payload.get("features", []):
        if feature["geometry"]["type"] != "Point":
            continue
        lon, lat = feature["geometry"]["coordinates"][:2]
        properties = feature.get("properties", {})
        parser = Links()
        parser.feed(properties.get("html", ""))
        key = f"{lat}:{lon}:{kind}:{fetched_at.date()}"
        result.append(
            Event.model_validate(
                dict(
                    id="gdelt:" + hashlib.sha256(key.encode()).hexdigest()[:24],
                    title=f"News mention · {kind} · {properties.get('name', 'approximate location')}",
                    type=kind,
                    lat=lat,
                    lon=lon,
                    start=fetched_at,
                    severity=1,
                    source="GDELT news mention",
                    url=parser.urls[0] if parser.urls else "https://www.gdeltproject.org/",
                    region=region_for(lat, lon),
                    raw=feature,
                    description="Unverified geocoded news mention. Timestamp is retrieval time, NOT incident time. "
                    "Type is the search query, not a verified classification. Excluded from event studies. "
                    "Geocoding and news coverage may be wrong; verify the source article.",
                )
            )
        )
    return result


def firms_url() -> str:
    key = os.getenv("FIRMS_MAP_KEY")
    if not key:
        raise ValueError("FIRMS_MAP_KEY required")
    return f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_NOAA20_NRT/-125,24,-66,50/1"
