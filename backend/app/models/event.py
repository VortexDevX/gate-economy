import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EventType(str, enum.Enum):
    MANA_SURGE = "MANA_SURGE"
    INSTABILITY_WAVE = "INSTABILITY_WAVE"
    ECONOMIC_BOOM = "ECONOMIC_BOOM"
    REGULATION_CRACKDOWN = "REGULATION_CRACKDOWN"
    GATE_RESONANCE = "GATE_RESONANCE"
    MARKET_PANIC = "MARKET_PANIC"
    TREASURE_DISCOVERY = "TREASURE_DISCOVERY"
    MANA_DROUGHT = "MANA_DROUGHT"
    STABILITY_SURGE = "STABILITY_SURGE"
    STABILITY_CRISIS = "STABILITY_CRISIS"
    YIELD_BOOM = "YIELD_BOOM"
    MARKET_SHOCK = "MARKET_SHOCK"
    DISCOVERY_SURGE = "DISCOVERY_SURGE"


class EventSeverity(str, enum.Enum):
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"
    CATASTROPHIC = "CATASTROPHIC"


class EventTargetType(str, enum.Enum):
    GLOBAL = "GLOBAL"
    GATE = "GATE"
    GUILD = "GUILD"
    MARKET = "MARKET"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="eventtype"), nullable=False
    )
    severity: Mapped[EventSeverity] = mapped_column(
        Enum(EventSeverity, name="eventseverity"),
        nullable=False,
        default=EventSeverity.MINOR,
        server_default=EventSeverity.MINOR.value,
    )
    target_type: Mapped[EventTargetType | None] = mapped_column(
        Enum(EventTargetType, name="eventtargettype"),
        nullable=True,
    )
    tick_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    effects: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    duration_ticks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at_tick: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
