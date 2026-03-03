import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IntentType(str, enum.Enum):
    DISCOVER_GATE = "DISCOVER_GATE"
    PLACE_ORDER = "PLACE_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"
    CREATE_GUILD = "CREATE_GUILD"
    GUILD_DIVIDEND = "GUILD_DIVIDEND"
    GUILD_INVEST = "GUILD_INVEST"


class IntentStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"


class Intent(Base):
    __tablename__ = "intents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=False
    )
    intent_type: Mapped[IntentType] = mapped_column(
        Enum(IntentType, name="intenttype"), nullable=False
    )
    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )
    status: Mapped[IntentStatus] = mapped_column(
        Enum(IntentStatus, name="intentstatus"),
        nullable=False,
        default=IntentStatus.QUEUED,
    )
    reject_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    processed_tick: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ticks.id"), nullable=True
    )