import argparse
import json
import sys
import httpx
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from pydantic import HttpUrl

from backend.app.db import save_events
from backend.app.ingestion import ingest
from backend.app.models import Event, EventType, region_for
from backend.app.prices import import_csv, refresh
from backend.app.exposure import companies
from backend.app.backfill import backfill


def seed() -> None:
    records: list[tuple[EventType, str, float, float, int]] = [
        ("earthquake", "Seismic activity near the Bay Area", 37.5, -122.1, 4),
        ("fire", "Wildfire scenario · Southern California", 34.1, -118.3, 4),
        ("severe_weather", "Gulf Coast storm scenario", 29.76, -95.37, 5),
        ("port_closure", "Port disruption scenario · New York", 40.68, -74.1, 3),
        ("strike", "Industrial action scenario · Detroit", 42.33, -83.05, 3),
        ("protest", "Demonstration scenario · Seattle", 47.6, -122.33, 2),
        ("severe_weather", "Flooding scenario · Atlanta", 33.75, -84.39, 3),
        ("fire", "Fire scenario · Phoenix", 33.45, -112.07, 2),
    ]
    events = [
        Event(
            id=f"demo:{i}",
            title=title,
            type=kind,
            lat=lat,
            lon=lon,
            start=datetime(2026, 9, 15 + i, 12, tzinfo=timezone.utc),
            severity=severity,
            source="Illustrative scenario",
            url=HttpUrl("https://www.ready.gov/"),
            region=region_for(lat, lon),
            description="Fictional event for demonstrating geographic exposure. Not an observed incident.",
            synthetic=True,
        )
        for i, (kind, title, lat, lon, severity) in enumerate(records)
    ]
    save_events(events)
    historical = []
    for event in events:
        for j in range(1, 7):
            historical.append(
                event.model_copy(
                    update={
                        "id": f"{event.id}:history:{j}",
                        "title": event.title + " · historical illustration",
                        "start": event.start - timedelta(days=60 * j),
                    }
                )
            )
    save_events(historical)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tremor data operations")
    parser.add_argument("command", choices=["seed", "ingest", "fetch-prices", "import-prices", "backfill"])
    parser.add_argument("--source", choices=["usgs", "nws", "firms", "gdelt", "all"], default="all")
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--ticker", default="SPY")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--provenance", default="user supplied; source unspecified")
    args = parser.parse_args()
    if args.command == "seed":
        seed()
        print("Illustrative events seeded (idempotent).")
    elif args.command == "backfill":
        if not args.start or not args.end:
            parser.error("--start and --end required (ISO dates)")
        print(f"Backfilled {backfill(args.start, args.end)} earthquakes.")
    elif args.command == "ingest":
        failed = False
        for source in ["usgs", "nws"] if args.source == "all" else [args.source]:
            result = ingest(source)
            print(json.dumps(result))
            failed = failed or bool(result.get("error"))
        if failed:
            raise SystemExit(1)
    else:
        ticker = args.ticker.upper()
        if ticker not in {"SPY", *(c.ticker for c in companies())}:
            parser.error("Ticker must be SPY or a curated company")
        if args.command == "import-prices":
            if not args.file:
                parser.error("--file required (date,adjusted_close CSV)")
            series = import_csv(ticker, args.file, args.provenance)
        else:
            series = refresh(ticker)
        print(f"{series.ticker}: {len(series.prices)} rows; {series.provider}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, httpx.HTTPError):
        print(
            "Data operation failed. Check inputs, .env, provider quota and source availability. "
            "Existing cached data retained.",
            file=sys.stderr,
        )
        raise SystemExit(1)
