import os
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.app.db import connect, save_events
from backend.app.models import Event, region_for

USGS_URL = 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson'
NWS_URL = 'https://api.weather.gov/alerts/active'


def usgs(payload: dict[str, Any]) -> list[Event]:
    result = []
    for item in payload.get('features', []):
        p = item['properties']
        lon, lat = item['geometry']['coordinates'][:2]
        magnitude = p.get('mag') or 0
        result.append(Event(id='usgs:' + item['id'], title=p.get('title', 'Earthquake'), type='earthquake',
                            lat=lat, lon=lon, start=datetime.fromtimestamp(p['time']/1000, timezone.utc),
                            severity=max(1, min(5, int(magnitude)-1)), source='USGS', url=p['url'],
                            region=region_for(lat, lon), description=f'Magnitude {magnitude}.', raw=item))
    return result


def nws(payload: dict[str, Any]) -> list[Event]:
    result = []
    for item in payload.get('features', []):
        geometry = item.get('geometry')
        if not geometry or geometry['type'] not in ('Polygon', 'MultiPolygon'):
            continue  # NWS zone-only alerts have no defensible point location.
        ring = geometry['coordinates'][0] if geometry['type'] == 'Polygon' else geometry['coordinates'][0][0]
        points = ring[:-1] if ring[0] == ring[-1] else ring
        lon = sum(p[0] for p in points)/len(points)
        lat = sum(p[1] for p in points)/len(points)
        p = item['properties']
        result.append(Event(id='nws:' + item['id'], title=p['event'], type='severe_weather', lat=lat, lon=lon,
                            start=p.get('onset') or p['sent'], end=p.get('ends') or p.get('expires'),
                            severity={'Extreme': 5, 'Severe': 4, 'Moderate': 3, 'Minor': 2}.get(p['severity'], 1),
                            source='NWS', url=p.get('@id') or item['id'], region=region_for(lat, lon),
                            description=p.get('description', '') + '\nApproximate polygon vertex centroid; '
                            'not a hazard footprint. Zone-only alerts omitted.', raw=item))
    return result


def request(url: str, params: dict[str, str] | None = None) -> httpx.Response:
    with httpx.Client(timeout=30, follow_redirects=True, headers={
        'User-Agent': os.getenv('EVENTMAP_USER_AGENT', 'EventMap-local-research'),
        'Accept': 'application/geo+json,application/json,text/csv',
    }) as client:
        response = client.get(url, params=params)
        response.raise_for_status()  # 429 is recorded; no aggressive automatic retry.
        return response


def ingest(source: str, force: bool = False) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    with connect() as conn:
        previous = conn.execute('SELECT * FROM runs WHERE source=?', (source,)).fetchone()
    if previous and not force and (now - datetime.fromisoformat(previous['fetched_at'])).total_seconds() < 900:
        return {'source': source, 'cached': True, 'count': previous['count'], 'error': previous['error']}
    try:
        if source == 'usgs':
            events = usgs(request(USGS_URL).json())
        elif source == 'nws':
            events = nws(request(NWS_URL).json())
        else:
            raise ValueError('Unknown source')
        count = save_events(events)
        error = None
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        count, error = 0, 'Upstream fetch or normalization failed; cached events retained. Retry after 15 minutes.'
    with connect() as conn:
        conn.execute('INSERT OR REPLACE INTO runs VALUES (?,?,?,?)', (source, now.isoformat(), count, error))
    return {'source': source, 'cached': False, 'count': count, 'error': error}
