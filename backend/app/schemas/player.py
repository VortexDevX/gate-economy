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
