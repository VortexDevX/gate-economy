from uuid import UUID

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    player_id: UUID
    username: str
    score_micro: int
    net_worth_micro: int
    balance_micro: int
    portfolio_micro: int


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]
    total: int
    page: int
    page_size: int


class MyRankResponse(BaseModel):
    rank: int | None
    player_id: UUID
    score_micro: int
    net_worth_micro: int
    balance_micro: int
    portfolio_micro: int
    last_active_tick: int
    updated_at_tick: int


class SeasonResponse(BaseModel):
    id: int
    season_number: int
    start_tick: int
    end_tick: int | None
    status: str


class SeasonDetailResponse(SeasonResponse):
    top_players: list[LeaderboardEntry]


class SeasonResultResponse(BaseModel):
    season_id: int
    player_id: UUID
    username: str
    final_rank: int
    final_score_micro: int
    final_net_worth_micro: int
