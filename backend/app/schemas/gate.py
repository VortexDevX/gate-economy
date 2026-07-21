"""Gate-related request/response schemas."""

import uuid
from typing import Self

from pydantic import BaseModel, model_validator

from app.services.instrument_identity import gate_display_name, gate_ticker


class GateResponse(BaseModel):
    """Single gate summary — used in list views."""

    id: uuid.UUID
    rank: str
    stability: float
    volatility: float
    base_yield_micro: int
    total_shares: int
    status: str
    spawned_at_tick: int
    collapsed_at_tick: int | None
    discovery_type: str
    discoverer_id: uuid.UUID | None
    ticker: str = ""
    display_name: str = ""
    effective_yield_micro: int = 0
    yield_per_share_micro: int = 0

    @model_validator(mode="after")
    def derive_market_identity(self) -> Self:
        self.ticker = gate_ticker(self.id, self.rank)
        self.display_name = gate_display_name(self.id)
        self.effective_yield_micro = (
            int(self.base_yield_micro * (self.stability / 100.0))
            if self.status == "ACTIVE"
            else 0
        )
        self.yield_per_share_micro = (
            self.effective_yield_micro // self.total_shares
            if self.total_shares > 0
            else 0
        )
        return self

    model_config = {"from_attributes": True}


class ShareholderInfo(BaseModel):
    """One shareholder's stake in a gate."""

    player_id: uuid.UUID
    quantity: int
    percentage: float


class GateDetailResponse(GateResponse):
    """Gate detail — includes shareholder breakdown."""

    shareholders: list[ShareholderInfo]


class GateListResponse(BaseModel):
    """Paginated gate list."""

    gates: list[GateResponse]
    total: int


class GateRankProfileResponse(BaseModel):
    """Reference data for one rank tier."""

    rank: str
    stability_init: float
    volatility: float
    yield_min_micro: int
    yield_max_micro: int
    total_shares: int
    lifespan_min: int
    lifespan_max: int
    collapse_threshold: float
    discovery_cost_micro: int
    spawn_weight: int

    model_config = {"from_attributes": True}
