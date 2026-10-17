import argparse
import json
from datetime import datetime, timezone
from pydantic import HttpUrl

from backend.app.db import save_events
from backend.app.ingestion import ingest
from backend.app.models import Event, EventType, region_for


def seed() -> None:
    records: list[tuple[EventType, str, float, float, int]] = [
        ('earthquake', 'Seismic activity near the Bay Area', 37.5, -122.1, 4),
        ('fire', 'Wildfire scenario · Southern California', 34.1, -118.3, 4),
        ('severe_weather', 'Gulf Coast storm scenario', 29.76, -95.37, 5),
        ('port_closure', 'Port disruption scenario · New York', 40.68, -74.1, 3),
        ('strike', 'Industrial action scenario · Detroit', 42.33, -83.05, 3),
        ('protest', 'Demonstration scenario · Seattle', 47.6, -122.33, 2),
        ('severe_weather', 'Flooding scenario · Atlanta', 33.75, -84.39, 3),
        ('fire', 'Fire scenario · Phoenix', 33.45, -112.07, 2),
    ]
    events = [Event(id=f'demo:{i}', title=title, type=kind, lat=lat, lon=lon,
                    start=datetime(2026, 9, 15+i, 12, tzinfo=timezone.utc), severity=severity,
                    source='Illustrative scenario', url=HttpUrl('https://www.ready.gov/'), region=region_for(lat, lon),
                    description='Fictional event for demonstrating geographic exposure. Not an observed incident.',
                    synthetic=True) for i, (kind, title, lat, lon, severity) in enumerate(records)]
    save_events(events)


def main() -> None:
    parser = argparse.ArgumentParser(description='EventMap data operations')
    parser.add_argument('command', choices=['seed', 'ingest'])
    parser.add_argument('--source', choices=['usgs', 'nws', 'all'], default='all')
    args = parser.parse_args()
    if args.command == 'seed':
        seed()
        print('Illustrative events seeded (idempotent).')
    else:
        for source in (['usgs', 'nws'] if args.source == 'all' else [args.source]):
            print(json.dumps(ingest(source)))


if __name__ == '__main__':
    main()
