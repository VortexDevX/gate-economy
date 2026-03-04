import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AccountEntityType(str, enum.Enum):
    PLAYER = "PLAYER"
    SYSTEM = "SYSTEM"
    GUILD = "GUILD"


class EntryType(str, enum.Enum):
    STARTING_GRANT = "STARTING_GRANT"
    YIELD_PAYMENT = "YIELD_PAYMENT"
    TRADE_SETTLEMENT = "TRADE_SETTLEMENT"
    TRADE_FEE = "TRADE_FEE"
    GATE_DISCOVERY = "GATE_DISCOVERY"
    GUILD_CREATION = "GUILD_CREATION"
    GUILD_MAINTENANCE = "GUILD_MAINTENANCE"
    PORTFOLIO_MAINTENANCE = "PORTFOLIO_MAINTENANCE"
    CONCENTRATION_PENALTY = "CONCENTRATION_PENALTY"
    LIQUIDITY_DECAY = "LIQUIDITY_DECAY"
    DIVIDEND = "DIVIDEND"
    AI_BUDGET = "AI_BUDGET"
    ADMIN_ADJUSTMENT = "ADMIN_ADJUSTMENT"
    ESCROW_LOCK = "ESCROW_LOCK"
    ESCROW_RELEASE = "ESCROW_RELEASE"


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount_micro > 0", name="ck_ledger_amount_positive"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    tick_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    debit_type: Mapped[AccountEntityType] = mapped_column(
        Enum(AccountEntityType, name="accountentitytype"),
        nullable=False,
    )
    debit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    credit_type: Mapped[AccountEntityType] = mapped_column(
        Enum(AccountEntityType, name="accountentitytype", create_type=False),
        nullable=False,
    )
    credit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    amount_micro: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    entry_type: Mapped[EntryType] = mapped_column(
        Enum(EntryType, name="entrytype"),
        nullable=False,
    )
    memo: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )