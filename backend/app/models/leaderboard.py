import enum
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SeasonStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class PlayerNetWorth(Base):
    __tablename__ = "player_net_worth"

    player_id: Mapped[UUID] = mapped_column(
        ForeignKey("players.id"), primary_key=True
    )
    net_worth_micro: Mapped[int] = mapped_column(BigInteger, default=0)
    score_micro: Mapped[int] = mapped_column(BigInteger, default=0)
    balance_micro: Mapped[int] = mapped_column(BigInteger, default=0)
    portfolio_micro: Mapped[int] = mapped_column(BigInteger, default=0)
    last_active_tick: Mapped[int] = mapped_column(Integer, default=0)
    updated_at_tick: Mapped[int] = mapped_column(Integer, default=0)


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    season_number: Mapped[int] = mapped_column(Integer, unique=True)
    start_tick: Mapped[int] = mapped_column(Integer)
    end_tick: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[SeasonStatus] = mapped_column(
        Enum(SeasonStatus, name="seasonstatus"),
        default=SeasonStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class SeasonResult(Base):
    __tablename__ = "season_results"

    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id"), primary_key=True
    )
    player_id: Mapped[UUID] = mapped_column(
        ForeignKey("players.id"), primary_key=True
    )
    final_rank: Mapped[int] = mapped_column(Integer)
    final_score_micro: Mapped[int] = mapped_column(BigInteger)
    final_net_worth_micro: Mapped[int] = mapped_column(BigInteger)