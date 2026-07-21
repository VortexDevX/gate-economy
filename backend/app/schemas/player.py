import uuid
from datetime import datetime

from pydantic import BaseModel


class PlayerResponse(BaseModel):
    id: uuid.UUID
    username: str
    balance_micro: int
    is_ai: bool
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LedgerEntryResponse(BaseModel):
    id: int
    tick_id: int | None
    debit_type: str
    debit_id: uuid.UUID
    credit_type: str
    credit_id: uuid.UUID
    amount_micro: int
    entry_type: str
    memo: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedLedger(BaseModel):
    items: list[LedgerEntryResponse]
    total: int
    page: int
    size: int


class GatePositionResponse(BaseModel):
    gate_id: uuid.UUID
    ticker: str
    display_name: str
    rank: str
    status: str
    quantity: int
    total_shares: int
    ownership_pct: float
    stability: float
    collapse_threshold: float
    base_yield_micro: int
    effective_yield_micro: int
    projected_yield_micro: int
    mark_price_micro: int
    market_value_micro: int
    best_bid_micro: int | None
    best_ask_micro: int | None
    volume_24h_micro: int
    risk_band: str


class GuildPositionResponse(BaseModel):
    guild_id: uuid.UUID
    name: str
    status: str
    quantity: int
    total_shares: int
    ownership_pct: float
    treasury_micro: int
    mark_price_micro: int
    market_value_micro: int
    best_bid_micro: int | None
    best_ask_micro: int | None
    volume_24h_micro: int


class PortfolioResponse(BaseModel):
    as_of_tick: int
    cash_balance_micro: int
    reserved_cash_micro: int
    gate_value_micro: int
    guild_value_micro: int
    portfolio_value_micro: int
    net_worth_micro: int
    projected_yield_per_tick_micro: int
    unstable_exposure_micro: int
    gate_positions: list[GatePositionResponse]
    guild_positions: list[GuildPositionResponse]
