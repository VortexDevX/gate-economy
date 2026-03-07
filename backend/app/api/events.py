"""Events API — paginated event feed."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.event import Event, EventType
from app.schemas.event import EventListResponse, EventResponse

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventListResponse)
async def list_events(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    event_type: EventType | None = Query(None),
) -> EventListResponse:
    """Return paginated events, newest first."""
    base = select(Event)
    count_base = select(func.count(Event.id))

    if event_type is not None:
        base = base.where(Event.event_type == event_type)
        count_base = count_base.where(Event.event_type == event_type)

    total_result = await db.execute(count_base)
    total = total_result.scalar_one()

    stmt = base.order_by(Event.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = [EventResponse.model_validate(row) for row in result.scalars().all()]

    return EventListResponse(items=items, total=total, limit=limit, offset=offset)
