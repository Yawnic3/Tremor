import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from pydantic import HttpUrl

from backend.app.db import save_events
from backend.app.ingestion import ingest
from backend.app.models import Event, EventType, region_for
from backend.app.prices import import_csv, refresh
from backend.app.exposure import companies


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
    parser = argparse.ArgumentParser(description='Tremor data operations')
    parser.add_argument('command', choices=['seed', 'ingest', 'fetch-prices', 'import-prices'])
    parser.add_argument('--source', choices=['usgs', 'nws', 'all'], default='all')
    parser.add_argument('--ticker', default='SPY')
    parser.add_argument('--file', type=Path)
    parser.add_argument('--provenance', default='user supplied; source unspecified')
    args = parser.parse_args()
    if args.command == 'seed':
        seed()
        print('Illustrative events seeded (idempotent).')
    elif args.command == 'ingest':
        for source in (['usgs', 'nws'] if args.source == 'all' else [args.source]):
            print(json.dumps(ingest(source)))
    else:
        ticker = args.ticker.upper()
        if ticker not in {'SPY', *(c.ticker for c in companies())}:
            parser.error('Ticker must be SPY or a curated company')
        if args.command == 'import-prices':
            if not args.file:
                parser.error('--file required (date,adjusted_close CSV)')
            series = import_csv(ticker, args.file, args.provenance)
        else:
            series = refresh(ticker)
        print(f'{series.ticker}: {len(series.prices)} rows; {series.provider}')


if __name__ == '__main__':
    main()

