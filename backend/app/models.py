from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

EventType = Literal["earthquake", "fire", "severe_weather", "strike", "port_closure", "protest"]


class Event(BaseModel):
    id: str
    title: str
    type: EventType
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    start: datetime
    end: datetime | None = None
    severity: int = Field(ge=1, le=5)
    source: str
    url: HttpUrl
    region: str
    description: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)
    synthetic: bool = False

    @field_validator("start", "end")
    @classmethod
    def timezone_required(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Timezone required")
        return value


def region_for(lat: float, lon: float) -> str:
    if not (24 <= lat <= 50 and -125 <= lon <= -66):
        return "Other"
    if lon < -114:
        return "US West"
    if lon < -95:
        return "US Central"
    return "US East"
