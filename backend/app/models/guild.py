"""Guild models — organizations with shares, dividends, and gate holdings."""

import enum
import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GuildStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INSOLVENT = "INSOLVENT"
    DISSOLVED = "DISSOLVED"


class GuildRole(str, enum.Enum):
    LEADER = "LEADER"
    OFFICER = "OFFICER"
    MEMBER = "MEMBER"


class DividendPolicy(str, enum.Enum):
    MANUAL = "MANUAL"
    AUTO_FIXED_PCT = "AUTO_FIXED_PCT"


class Guild(Base):
    __tablename__ = "guilds"
    __table_args__ = (
        CheckConstraint("treasury_micro >= 0", name="ck_guild_treasury_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    founder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=False
    )
    treasury_micro: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    total_shares: Mapped[int] = mapped_column(Integer, nullable=False)
    public_float_pct: Mapped[float] = mapped_column(Numeric, nullable=False)
    dividend_policy: Mapped[DividendPolicy] = mapped_column(
        Enum(DividendPolicy, name="dividendpolicy"), nullable=False
    )
    auto_dividend_pct: Mapped[float | None] = mapped_column(
        Numeric, nullable=True
    )
    status: Mapped[GuildStatus] = mapped_column(
        Enum(GuildStatus, name="guildstatus"),
        nullable=False,
        default=GuildStatus.ACTIVE,
    )
    created_at_tick: Mapped[int] = mapped_column(Integer, nullable=False)
    maintenance_cost_micro: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    missed_maintenance_ticks: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    insolvent_ticks: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    @property
    def balance_micro(self) -> int:
        return self.treasury_micro

    @balance_micro.setter
    def balance_micro(self, value: int) -> None:
        self.treasury_micro = value


class GuildMember(Base):
    __tablename__ = "guild_members"

    guild_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("guilds.id"), primary_key=True
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), primary_key=True
    )
    role: Mapped[GuildRole] = mapped_column(
        Enum(GuildRole, name="guildrole"), nullable=False
    )
    joined_at_tick: Mapped[int] = mapped_column(Integer, nullable=False)


class GuildShare(Base):
    __tablename__ = "guild_shares"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_guild_share_quantity_nonneg"),
    )

    guild_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("guilds.id"), primary_key=True
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True  # NO FK — can hold guild.id
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)


class GuildGateHolding(Base):
    __tablename__ = "guild_gate_holdings"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_guild_gate_holding_nonneg"),
    )

    guild_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("guilds.id"), primary_key=True
    )
    gate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gates.id"), primary_key=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)