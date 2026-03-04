import uuid

from pydantic import BaseModel


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