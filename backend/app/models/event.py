import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EventType(str, enum.Enum):
    STABILITY_SURGE = "STABILITY_SURGE"
    STABILITY_CRISIS = "STABILITY_CRISIS"
    YIELD_BOOM = "YIELD_BOOM"
    MARKET_SHOCK = "MARKET_SHOCK"
    DISCOVERY_SURGE = "DISCOVERY_SURGE"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="eventtype"), nullable=False
    )
    tick_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )