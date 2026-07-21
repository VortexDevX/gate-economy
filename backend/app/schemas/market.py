import uuid

from pydantic import BaseModel, PositiveInt

from app.models.market import AssetType, OrderSide


class OrderResponse(BaseModel):
    id: uuid.UUID
    player_id: uuid.UUID
    asset_type: str
    asset_id: uuid.UUID
    side: str
    quantity: int
    price_limit_micro: int
    filled_quantity: int
    escrow_micro: int
    status: str
    created_at_tick: int
    updated_at_tick: int | None = None

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int


class TradeResponse(BaseModel):
    id: uuid.UUID
    buy_order_id: uuid.UUID
    sell_order_id: uuid.UUID
    asset_type: str
    asset_id: uuid.UUID
    quantity: int
    price_micro: int
    buyer_fee_micro: int
    seller_fee_micro: int
    tick_id: int
    tick_number: int | None = None

    model_config = {"from_attributes": True}


class TradeListResponse(BaseModel):
    trades: list[TradeResponse]
    total: int


class MarketPriceResponse(BaseModel):
    asset_type: str
    asset_id: uuid.UUID
    last_price_micro: int | None = None
    best_bid_micro: int | None = None
    best_ask_micro: int | None = None
    volume_24h_micro: int = 0
    updated_at_tick: int = 0

    model_config = {"from_attributes": True}


class OrderBookEntry(BaseModel):
    price_micro: int
    total_quantity: int
    order_count: int


class OrderBookResponse(BaseModel):
    bids: list[OrderBookEntry]
    asks: list[OrderBookEntry]


class OrderPreviewRequest(BaseModel):
    asset_type: AssetType
    asset_id: uuid.UUID
    side: OrderSide
    quantity: PositiveInt
    price_limit_micro: PositiveInt


class OrderPreviewResponse(BaseModel):
    gross_value_micro: int
    estimated_fee_micro: int
    fee_rate_bps: int
    required_escrow_micro: int
    available_cash_micro: int
    available_shares: int
    can_submit: bool
    reason: str | None = None


class MarketAssetResponse(BaseModel):
    asset_id: uuid.UUID
    ticker: str
    display_name: str
    rank: str
    status: str
    stability: float
    collapse_threshold: float
    distance_to_instability: float
    risk_band: str
    total_shares: int
    base_yield_micro: int
    effective_yield_micro: int
    yield_per_share_micro: int
    mark_price_micro: int
    yield_rate_bps_per_tick: int | None
    last_price_micro: int | None
    best_bid_micro: int | None
    best_ask_micro: int | None
    spread_bps: int | None
    volume_24h_micro: int
    updated_at_tick: int
    spawned_at_tick: int
    discovery_type: str


class MarketOverviewResponse(BaseModel):
    items: list[MarketAssetResponse]
    total: int
    active_count: int
    offering_count: int
    unstable_count: int
    collapsed_count: int


class MarketHistoryPoint(BaseModel):
    tick_number: int
    open_micro: int
    high_micro: int
    low_micro: int
    close_micro: int
    average_price_micro: int
    volume_quantity: int
    volume_micro: int
    trade_count: int


class MarketHistoryResponse(BaseModel):
    asset_type: str
    asset_id: uuid.UUID
    points: list[MarketHistoryPoint]
