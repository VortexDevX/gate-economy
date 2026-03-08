# PHASE 8 PLAN: Events, News & Real-time

## Goal
Add stochastic world events, narrative news output, and real-time delivery to clients using WebSocket.

## Canonical Scope (Aligned with `docs/plan/PLAN.md`)

### Data Model
- `events`
  - `id`, `tick_id`, `event_type`, `severity`, `target_type`, `target_id`, `effects`, `duration_ticks`, `expires_at_tick`, `created_at`
- `news_items`
  - `id`, `tick_id`, `headline`, `body`, `category`, `importance`, `related_type`, `related_id`, `created_at`

### Event Types
- `MANA_SURGE`
- `INSTABILITY_WAVE`
- `ECONOMIC_BOOM`
- `REGULATION_CRACKDOWN`
- `GATE_RESONANCE`
- `MARKET_PANIC`
- `TREASURE_DISCOVERY`
- `MANA_DROUGHT`

### Tick Pipeline Integration
1. Roll event trigger using `event_probability`.
2. Select event by weighted draw.
3. Apply event effects to world state.
4. Persist event row.
5. Generate `news_items` rows for events + major market/world changes.
6. Revert temporary effects when `expires_at_tick` is reached.

### APIs
- `GET /news`
- `GET /events`
- `WS /ws/feed`

### Real-time Transport
- Worker publishes tick updates to Redis pub/sub.
- API websocket layer fans out messages to connected authenticated clients.
- Message types include `tick_summary`, `news`, `prices`, and player-specific portfolio deltas.

## Acceptance Criteria
- Events occur stochastically and deterministically under fixed seed replay.
- Event effects are visible and reversible when temporary.
- News is generated for key events and large trades.
- `/events` and `/news` return paginated/filterable results.
- `WS /ws/feed` delivers updates within target latency.
- No wealth-targeting in event selection.

## Implementation Notes (Current Repo)
- WebSocket supports `WS /ws/feed` with JWT query token.
- `GET /events` exists and is tested.
- Canonical table names/fields are now present (`news_items`, extended `events` fields).
- Legacy event/news types are still kept for backward compatibility with existing services/tests.
- Realtime payload is currently `tick_update` + compact news summary; richer per-player deltas can be added later without backend schema changes.
