"""Guild API schemas."""

import uuid

from pydantic import BaseModel


class GuildGateHoldingOut(BaseModel):
    gate_id: uuid.UUID
    quantity: int


class GuildMemberOut(BaseModel):
    player_id: uuid.UUID
    role: str
    joined_at_tick: int


class GuildResponse(BaseModel):
    id: uuid.UUID
    name: str
    founder_id: uuid.UUID
    treasury_micro: int
    total_shares: int
    public_float_pct: float
    dividend_policy: str
    auto_dividend_pct: float | None
    status: str
    created_at_tick: int
    maintenance_cost_micro: int

    model_config = {"from_attributes": True}


class GuildDetailResponse(GuildResponse):
    members: list[GuildMemberOut]
    gate_holdings: list[GuildGateHoldingOut]
    shareholder_count: int


class GuildListResponse(BaseModel):
    guilds: list[GuildResponse]
    total: int