import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AssetType(str, enum.Enum):
    GATE_SHARE = "GATE_SHARE"
    GUILD_SHARE = "GUILD_SHARE"


class OrderSide(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, enum.Enum):
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_quantity_positive"),
        CheckConstraint("price_limit_micro > 0", name="ck_order_price_positive"),
        CheckConstraint("filled_quantity >= 0", name="ck_order_filled_nonneg"),
        CheckConstraint("escrow_micro >= 0", name="ck_order_escrow_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="assettype"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    side: Mapped[OrderSide] = mapped_column(
        Enum(OrderSide, name="orderside"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_limit_micro: Mapped[int] = mapped_column(BigInteger, nullable=False)
    filled_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    escrow_micro: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="orderstatus"),
        nullable=False,
        default=OrderStatus.OPEN,
    )
    created_at_tick: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at_tick: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    guild_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    
    @property
    def remaining(self) -> int:
        return self.quantity - self.filled_quantity


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    buy_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    sell_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="assettype", create_type=False), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_micro: Mapped[int] = mapped_column(BigInteger, nullable=False)
    buyer_fee_micro: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seller_fee_micro: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tick_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class MarketPrice(Base):
    __tablename__ = "market_prices"

    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="assettype", create_type=False),
        primary_key=True,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    last_price_micro: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    best_bid_micro: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    best_ask_micro: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    volume_24h_micro: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    updated_at_tick: Mapped[int] = mapped_column(Integer, nullable=False)