// --- Auth ---

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string | null;
  token_type: string;
}

// --- Player ---

export interface PlayerResponse {
  id: string;
  username: string;
  balance_micro: number;
  is_ai: boolean;
  role: string;
  created_at: string;
}

export interface LedgerEntryResponse {
  id: number;
  tick_id: number | null;
  debit_type: string;
  debit_id: string;
  credit_type: string;
  credit_id: string;
  amount_micro: number;
  entry_type: string;
  memo: string | null;
  created_at: string;
}

export interface PaginatedLedger {
  items: LedgerEntryResponse[];
  total: number;
  page: number;
  size: number;
}

// --- Simulation ---

export interface SimulationStatus {
  current_tick: number;
  last_completed_at: string | null;
  is_running: boolean;
  is_paused: boolean;
  treasury_balance: number;
}

// --- Gates ---

export interface GateResponse {
  id: string;
  rank: string;
  stability: number;
  volatility: number;
  base_yield_micro: number;
  total_shares: number;
  status: string;
  spawned_at_tick: number;
  collapsed_at_tick: number | null;
  discovery_type: string;
  discoverer_id: string | null;
}

export interface ShareholderInfo {
  player_id: string;
  quantity: number;
  percentage: number;
}

export interface GateDetailResponse extends GateResponse {
  shareholders: ShareholderInfo[];
}

export interface GateListResponse {
  gates: GateResponse[];
  total: number;
}

export interface GateRankProfileResponse {
  rank: string;
  stability_init: number;
  volatility: number;
  yield_min_micro: number;
  yield_max_micro: number;
  total_shares: number;
  lifespan_min: number;
  lifespan_max: number;
  collapse_threshold: number;
  discovery_cost_micro: number;
  spawn_weight: number;
}

// --- Guilds ---

export interface GuildResponse {
  id: string;
  name: string;
  founder_id: string;
  treasury_micro: number;
  total_shares: number;
  public_float_pct: number;
  dividend_policy: string;
  auto_dividend_pct: number | null;
  status: string;
  created_at_tick: number;
  maintenance_cost_micro: number;
}

export interface GuildMemberResponse {
  player_id: string;
  role: string;
  joined_at_tick: number;
}

export interface GuildGateHoldingResponse {
  gate_id: string;
  quantity: number;
}

export interface GuildDetailResponse extends GuildResponse {
  members: GuildMemberResponse[];
  gate_holdings: GuildGateHoldingResponse[];
  shareholder_count: number;
}

export interface GuildListResponse {
  guilds: GuildResponse[];
  total: number;
}

// --- Market ---

export interface MarketPriceResponse {
  asset_type: string;
  asset_id: string;
  last_price_micro: number | null;
  best_bid_micro: number | null;
  best_ask_micro: number | null;
  volume_24h_micro: number;
  updated_at_tick: number;
}

export interface OrderBookEntry {
  price_micro: number;
  total_quantity: number;
  order_count: number;
}

export interface OrderBookResponse {
  bids: OrderBookEntry[];
  asks: OrderBookEntry[];
}

export interface TradeResponse {
  id: string;
  buy_order_id: string;
  sell_order_id: string;
  asset_type: string;
  asset_id: string;
  quantity: number;
  price_micro: number;
  buyer_fee_micro: number;
  seller_fee_micro: number;
  tick_id: number;
}

export interface TradeListResponse {
  trades: TradeResponse[];
  total: number;
}

// --- Orders ---

export interface OrderResponse {
  id: string;
  player_id: string;
  asset_type: string;
  asset_id: string;
  side: string;
  quantity: number;
  price_limit_micro: number;
  filled_quantity: number;
  escrow_micro: number;
  status: string;
  created_at_tick: number;
  updated_at_tick: number | null;
}

export interface OrderListResponse {
  orders: OrderResponse[];
  total: number;
}

// --- Intents ---

export interface IntentCreate {
  intent_type: string;
  payload: Record<string, unknown>;
}

export interface IntentResponse {
  id: string;
  intent_type: string;
  status: string;
  reject_reason: string | null;
  created_at: string;
  processed_tick: number | null;
}

export interface IntentListResponse {
  items: IntentResponse[];
  total: number;
}

// --- News ---

export interface NewsResponse {
  id: string;
  tick_id: number;
  headline: string;
  body: string | null;
  category: string;
  importance: number;
  related_entity_type: string | null;
  related_entity_id: string | null;
  created_at: string;
}

export interface NewsListResponse {
  items: NewsResponse[];
  total: number;
  limit: number;
  offset: number;
}

// --- Events ---

export interface EventResponse {
  id: string;
  tick_id: number;
  event_type: string;
  severity: string;
  target_type: string | null;
  target_id: string | null;
  effects: Record<string, unknown> | null;
  duration_ticks: number | null;
  expires_at_tick: number | null;
  payload: Record<string, unknown> | null;
  created_at: string;
}

export interface EventListResponse {
  items: EventResponse[];
  total: number;
  limit: number;
  offset: number;
}

// --- Leaderboard & Seasons ---

export interface LeaderboardEntryResponse {
  rank: number;
  player_id: string;
  username: string;
  score_micro: number;
  net_worth_micro: number;
  balance_micro: number;
  portfolio_micro: number;
}

export interface LeaderboardResponse {
  entries: LeaderboardEntryResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface MyRankResponse {
  rank: number | null;
  player_id: string;
  score_micro: number;
  net_worth_micro: number;
  balance_micro: number;
  portfolio_micro: number;
  last_active_tick: number;
  updated_at_tick: number;
}

export interface SeasonResponse {
  id: number;
  season_number: number;
  start_tick: number;
  end_tick: number | null;
  status: string;
}

export interface SeasonResultResponse {
  season_id: number;
  player_id: string;
  username: string;
  final_rank: number;
  final_score_micro: number;
  final_net_worth_micro: number;
}

// --- Generic ---

export interface ApiError {
  detail: string;
}

// --- Admin ---

export interface SimulationControlResponse {
  status: string;
  message: string;
}

export interface ParameterResponse {
  key: string;
  value: string;
  value_type: string;
  description: string | null;
  updated_at: string;
  updated_by: string | null;
}

export interface ParameterUpdateRequest {
  value: string;
}

export interface TreasuryLedgerEntry {
  id: number;
  tick_id: number | null;
  debit_type: string;
  debit_id: string;
  credit_type: string;
  credit_id: string;
  amount_micro: number;
  entry_type: string;
  memo: string | null;
  created_at: string;
}

export interface TreasuryResponse {
  treasury_id: string;
  balance_micro: number;
  recent_entries: TreasuryLedgerEntry[];
}

export interface ConservationAuditResponse {
  status: "PASS" | "FAIL";
  treasury_balance_micro: number;
  player_sum_micro: number;
  guild_sum_micro: number;
  total_micro: number;
  expected_micro: number;
  delta_micro: number;
}

export interface EventTriggerRequest {
  event_type: string;
}

export interface EventTriggerResponse {
  event_id: string;
  event_type: string;
  tick_id: number | null;
  message: string;
}

export interface AdminLedgerEntry {
  id: number;
  tick_id: number | null;
  debit_type: string;
  debit_id: string;
  credit_type: string;
  credit_id: string;
  amount_micro: number;
  entry_type: string;
  memo: string | null;
  created_at: string;
}

export interface SeasonActionRequest {
  action: "create" | "end";
}

export interface SeasonActionResponse {
  season_id: number;
  season_number: number;
  action: "create" | "end";
  message: string;
}
