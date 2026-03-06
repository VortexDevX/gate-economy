import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NewsCategory(str, enum.Enum):
    GATE = "GATE"
    MARKET = "MARKET"
    GUILD = "GUILD"
    WORLD = "WORLD"


class News(Base):
    __tablename__ = "news"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tick_id: Mapped[int] = mapped_column(Integer, nullable=False)
    headline: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[NewsCategory] = mapped_column(
        Enum(NewsCategory, name="newscategory"), nullable=False
    )
    importance: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    related_entity_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )