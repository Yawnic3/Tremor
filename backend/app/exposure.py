import csv
import math
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl

from backend.app.models import Event

RADII = {'earthquake': 150, 'fire': 50, 'severe_weather': 300, 'strike': 75,
         'port_closure': 120, 'protest': 30}


class Facility(BaseModel):
    id: str
    ticker: str
    name: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    type: str = 'headquarters'
    weight: float | None = Field(None, ge=0, le=1)
    source: HttpUrl
    confidence: str
    quality_note: str
    verified: str | None


class Company(BaseModel):
    ticker: str
    name: str
    sector: str
    facilities: list[Facility]


class Exposure(BaseModel):
    ticker: str
    name: str
    score: float
    strength: str
    why: str
    distance_km: float
    radius_km: float
    facilities: list[Facility]


def companies() -> list[Company]:
    with (Path(__file__).resolve().parents[2] / 'data' / 'companies.csv').open(encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    return [Company(ticker=r['ticker'], name=r['name'], sector=r['sector'], facilities=[Facility(
        id=r['ticker'] + ':hq', ticker=r['ticker'], name=r['city'] + ' headquarters (approximate)',
        lat=float(r['lat']), lon=float(r['lon']), weight=None, source=HttpUrl(r['source']), confidence=r['confidence'],
        verified=r['verified'] or None, quality_note=(
            'City-level coordinate unless independently checked. Corporate source link is a review lead; '
            'unverified records require manual validation. HQ proximity is a weak operational exposure proxy. '
            'Asset/revenue weight unknown; matching uses a conservative 0.2 proxy weight.'))]) for r in rows]


def distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    a, b = math.radians(lat1), math.radians(lat2)
    h = math.sin((b-a)/2)**2 + math.cos(a)*math.cos(b)*math.sin(math.radians(lon2-lon1)/2)**2
    return 6371 * 2 * math.asin(math.sqrt(min(1, h)))


def match(event: Event, radius: float | None = None) -> list[Exposure]:
    radius = radius or RADII[event.type]
    output = []
    for company in companies():
        facilities = [f for f in company.facilities
                      if abs(f.lat-event.lat) <= radius/110 and distance(event.lat, event.lon, f.lat, f.lon) <= radius]
        if not facilities:
            continue
        nearest = min(distance(event.lat, event.lon, f.lat, f.lon) for f in facilities)
        score = min(1.0, sum((f.weight if f.weight is not None else 0.2) *
                            (1-distance(event.lat, event.lon, f.lat, f.lon)/radius) for f in facilities))
        output.append(Exposure(ticker=company.ticker, name=company.name, score=round(score, 4),
                               strength='High' if score >= .6 else 'Moderate' if score >= .3 else 'Low',
                               distance_km=round(nearest, 1), radius_km=radius, facilities=facilities,
                               why=f'{len(facilities)} headquarters within {radius:g} km; nearest {nearest:.1f} km. '
                               'Proximity only; unknown asset weight uses 0.2. No confirmed disruption.'))
    return sorted(output, key=lambda e: (-e.score, e.ticker))
