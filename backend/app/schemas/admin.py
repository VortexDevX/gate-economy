from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ParameterResponse(BaseModel):
    key: str
    value: str
    value_type: str
    description: str | None = None
    updated_at: datetime
    updated_by: UUID | None = None

    model_config = {"from_attributes": True}


class ParameterUpdate(BaseModel):
    value: str = Field(..., min_length=1, max_length=500)


class ConservationAuditResponse(BaseModel):
    status: str  # PASS or FAIL
    treasury_balance_micro: int
    player_sum_micro: int
    guild_sum_micro: int
    total_micro: int
    expected_micro: int
    delta_micro: int


class TreasuryLedgerEntry(BaseModel):
    id: int
    tick_id: int | None = None
    debit_type: str
    debit_id: UUID
    credit_type: str
    credit_id: UUID
    amount_micro: int
    entry_type: str
    memo: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TreasuryResponse(BaseModel):
    treasury_id: UUID
    balance_micro: int
    recent_entries: list[TreasuryLedgerEntry]


class EventTriggerRequest(BaseModel):
    event_type: str


class EventTriggerResponse(BaseModel):
    event_id: UUID
    event_type: str
    tick_id: int | None = None
    message: str


class SeasonActionRequest(BaseModel):
    action: str = Field(..., pattern="^(create|end)$")


class SeasonActionResponse(BaseModel):
    season_id: int
    season_number: int
    action: str
    message: str


class SimulationControlResponse(BaseModel):
    status: str
    message: str


class AdminLedgerEntry(BaseModel):
    id: int
    tick_id: int | None = None
    debit_type: str
    debit_id: UUID
    credit_type: str
    credit_id: UUID
    amount_micro: int
    entry_type: str
    memo: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}