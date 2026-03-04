"""Gate-related request/response schemas."""

import uuid

from pydantic import BaseModel


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