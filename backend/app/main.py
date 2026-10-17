from datetime import date

from fastapi import FastAPI, HTTPException, Query

from backend.app.db import list_events
from backend.app.models import Event, EventType

app = FastAPI(title="EventMap", version="0.1.0")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get('/api/events', response_model=list[Event])
def events(type: EventType | None = None, start: date | None = None, end: date | None = None,
           severity: int = Query(1, ge=1, le=5), demo: bool = True,
           bbox: str | None = None) -> list[Event]:
    bounds = None
    if start and end and start > end:
        raise HTTPException(422, 'Start must precede end')
    if bbox:
        try:
            values = tuple(float(v) for v in bbox.split(','))
            if len(values) != 4:
                raise ValueError()
            w, s, e, n = values
            if not (-180 <= w <= e <= 180 and -90 <= s <= n <= 90):
                raise ValueError()
            bounds = (w, s, e, n)
        except ValueError:
            raise HTTPException(422, 'bbox must be west,south,east,north with ordered valid coordinates')
    return [e for e in list_events(bounds) if e.synthetic == demo and (not type or e.type == type)
            and e.severity >= severity and (not start or e.start.date() >= start)
            and (not end or e.start.date() <= end)]


@app.get('/api/events/{event_id}', response_model=Event)
def event_detail(event_id: str) -> Event:
    for event in list_events():
        if event.id == event_id:
            return event
    raise HTTPException(404, 'Event not found')
