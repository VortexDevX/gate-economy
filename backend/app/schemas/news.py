from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NewsResponse(BaseModel):
    id: UUID
    tick_id: int
    headline: str
    body: str | None
    category: str
    importance: int
    related_entity_type: str | None
    related_entity_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NewsListResponse(BaseModel):
    items: list[NewsResponse]
    total: int
    limit: int
    offset: int