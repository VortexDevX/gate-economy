import enum
import uuid

from sqlalchemy import BigInteger, CheckConstraint, Enum, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class GateRank(str, enum.Enum):
    E = "E"
    D = "D"
    C = "C"
    B = "B"
    A = "A"
    S = "S"
    S_PLUS = "S_PLUS"


class GateStatus(str, enum.Enum):
    OFFERING = "OFFERING"
    ACTIVE = "ACTIVE"
    UNSTABLE = "UNSTABLE"
    COLLAPSED = "COLLAPSED"


class DiscoveryType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    PLAYER = "PLAYER"


class GateRankProfile(Base):
    """One row per rank — defines baseline parameters for gate spawning."""

    __tablename__ = "gate_rank_profiles"

    rank: Mapped[GateRank] = mapped_column(
        Enum(GateRank, name="gaterank"),
        primary_key=True,
    )
    stability_init: Mapped[float] = mapped_column(Float, nullable=False)
    volatility: Mapped[float] = mapped_column(Float, nullable=False)
    yield_min_micro: Mapped[int] = mapped_column(BigInteger, nullable=False)
    yield_max_micro: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_shares: Mapped[int] = mapped_column(Integer, nullable=False)
    lifespan_min: Mapped[int] = mapped_column(Integer, nullable=False)
    lifespan_max: Mapped[int] = mapped_column(Integer, nullable=False)
    collapse_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    discovery_cost_micro: Mapped[int] = mapped_column(BigInteger, nullable=False)
    spawn_weight: Mapped[int] = mapped_column(Integer, nullable=False)


class Gate(TimestampMixin, Base):
    """A dungeon gate instance — spawned by system or discovered by player."""

    __tablename__ = "gates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rank: Mapped[GateRank] = mapped_column(
        Enum(GateRank, name="gaterank", create_type=False),
        ForeignKey("gate_rank_profiles.rank"),
        nullable=False,
    )
    stability: Mapped[float] = mapped_column(Float, nullable=False)
    volatility: Mapped[float] = mapped_column(Float, nullable=False)
    base_yield_micro: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_shares: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[GateStatus] = mapped_column(
        Enum(GateStatus, name="gatestatus"),
        nullable=False,
    )
    spawned_at_tick: Mapped[int] = mapped_column(Integer, nullable=False)
    collapsed_at_tick: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discovery_type: Mapped[DiscoveryType] = mapped_column(
        Enum(DiscoveryType, name="discoverytype"),
        nullable=False,
    )
    discoverer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=True
    )


class GateShare(Base):
    """Fractional ownership of a gate.

    player_id is a plain UUID with NO FK to players.
    It may hold a players.id OR a system_accounts.id (treasury holds
    unsold shares). Integrity enforced at application level —
    rows are only created by gate_lifecycle and market matching engine.
    """

    __tablename__ = "gate_shares"
    __table_args__ = (
        CheckConstraint(
            "quantity >= 0", name="ck_gate_shares_quantity_non_negative"
        ),
    )

    gate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gates.id"), primary_key=True
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)