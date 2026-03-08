from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EventResponse(BaseModel):
    id: UUID
    tick_id: int
    event_type: str
    severity: str
    target_type: str | None
    target_id: UUID | None
    effects: dict | None
    duration_ticks: int | None
    expires_at_tick: int | None
    payload: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    items: list[EventResponse]
    total: int
    limit: int
    offset: int
