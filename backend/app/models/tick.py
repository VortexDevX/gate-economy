from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Tick(Base):
    __tablename__ = "ticks"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    tick_number: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False
    )
    seed: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    intent_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    state_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )