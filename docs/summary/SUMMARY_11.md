# Phase 11 Summary: Admin & Observability

> Update (2026-03-08, post Phase 8–10 parity pass):
> Full backend suite baseline moved from 209 to 210 tests.
> Metrics implementation now uses histogram/counter types where specified.

**Status**: ✅ Complete
**Tests added**: 20 (189 → 209)
**Date completed**: 2026-03-08

---

## What Was Built

### 1. Data Model + Migration

- **`PlayerRole` enum** (`PLAYER`, `ADMIN`) added to `Player` model with `server_default='PLAYER'`
- **`SimulationParameter` table** — key-value store for runtime-tunable gameplay parameters
  - `key` (PK), `value`, `value_type` (INT/FLOAT/BOOL/STRING), `description`, `updated_at`, `updated_by` (FK → players)
- **`ParamValueType` enum** — types for parameter value casting
- Migration: `2e9f2d2c75d9` — required manual `sa.Enum.create()` before `add_column` (Convention #4)

### 2. Admin Auth Dependency

- **`core/admin.py`** — `require_admin` dependency + `AdminPlayer` type alias
- Reuses existing JWT auth flow; checks `player.role == PlayerRole.ADMIN`
- Returns 403 for non-admin players

### 3. Admin Service Layer (`services/admin.py`)

- **Tunable parameter registry** — 42 gameplay parameters whitelisted for runtime tuning
  - Covers gates, fees, guilds, AI traders, events, anti-exploit, leaderboard, seasons
  - Never exposes DB/JWT/infra secrets
- **`seed_parameters()`** — idempotent seeding from current `settings` values
- **`list_parameters()`** / **`update_parameter()`** — CRUD with type casting and validation
- **`load_parameters_into_settings()`** — loads DB values into in-memory settings singleton (called each tick)
- **`run_conservation_audit()`** — computes treasury + player_sum + guild_sum vs INITIAL_SEED, returns PASS/FAIL
- **`get_treasury_info()`** — treasury balance + recent ledger entries involving treasury
- **`PAUSE_KEY`** — Redis key `simulation:paused` used by worker and admin endpoints

### 4. Parameter Seeding in Lifespan

- **`seed_simulation_parameters()`** added to `main.py` lifespan — runs after AI player seeding
- Idempotent: only creates rows for keys not already present

### 5. Admin API Router (`api/admin.py`) — 9 Endpoints

| Method | Path                        | Purpose                                                    |
| ------ | --------------------------- | ---------------------------------------------------------- |
| POST   | `/admin/simulation/pause`   | Set Redis pause flag                                       |
| POST   | `/admin/simulation/resume`  | Clear Redis pause flag                                     |
| GET    | `/admin/parameters`         | List all tunable parameters                                |
| PATCH  | `/admin/parameters/{key}`   | Update parameter value (type-validated)                    |
| POST   | `/admin/events/trigger`     | Manually fire an event                                     |
| GET    | `/admin/treasury`           | Treasury balance + recent flows                            |
| GET    | `/admin/audit/conservation` | Conservation invariant check → PASS/FAIL                   |
| GET    | `/admin/ledger`             | Query ledger with filters (entry_type, player_id, tick_id) |
| POST   | `/admin/seasons`            | Create or end a season                                     |

All endpoints require authenticated ADMIN player.

### 6. Worker Pause Integration

- **`simulation/worker.py`** — checks `simulation:paused` Redis key before acquiring lock
- If paused, logs skip and returns immediately — no tick executed
- Preserves existing lock safety and error handling

### 7. Tick Parameter Loading

- **`simulation/tick.py`** step 4b — calls `load_parameters_into_settings()` at tick start
- Admin parameter changes reflected within at most 1 tick

### 8. Prometheus Metrics (`api/metrics.py`)

`/metrics` endpoint exposes 10 business metrics via `prometheus-client`:

| Metric                       | Type  | Source                |
| ---------------------------- | ----- | --------------------- |
| `dge_tick_number`            | gauge | Latest tick           |
| `dge_tick_duration_seconds`  | histogram | Tick duration observations |
| `dge_intent_queue_depth`     | gauge | Queued intents count  |
| `dge_active_players_total`   | gauge | Human player count    |
| `dge_treasury_balance_micro` | gauge | Treasury balance      |
| `dge_trade_volume_micro`     | counter | Total trade volume    |
| `dge_active_gates_total`     | gauge | Non-collapsed gates   |
| `dge_ws_connections`         | gauge | WebSocket connections |
| `dge_order_book_depth`       | gauge | Open/partial orders   |
| `dge_events_fired_total`     | counter | Total events          |

- DB-backed snapshot on each scrape (no in-process counters to drift)
- Uses isolated `CollectorRegistry` to avoid default collector pollution

### 9. Prometheus + Grafana Infrastructure

- **`infra/prometheus.yml`** — 5s scrape interval matching tick cadence
- **Grafana provisioning** — auto-configured datasource + dashboard provider
- **`dge-overview.json` dashboard** — 11 panels:
  - Stat panels: tick number, tick duration, treasury, active players, active gates, WS connections
  - Time series: intent queue, trade volume, order book depth, events fired, tick duration over time
- **`docker-compose.yml`** — added `prometheus` (port 9090) and `grafana` (port 3000) services
  - Grafana: anonymous viewer access enabled, admin/admin default credentials

### 10. k6 Load Test Scripts

| Script              | Scenario                                        | Target            |
| ------------------- | ----------------------------------------------- | ----------------- |
| `auth_load.js`      | Ramp to 1,000 VUs registering + logging in      | p99 < 500ms       |
| `order_storm.js`    | 500 VUs placing order intents every 5s          | p99 < 500ms       |
| `ws_connections.js` | Ramp to 1,000 WebSocket connections             | p99 delivery < 1s |
| `mixed_workload.js` | 60% reads, 30% orders, 10% discovery at 500 VUs | p99 < 500ms       |

All scripts support `BASE_URL` / `WS_URL` env vars for targeting different environments.

---

## Schemas Added

- `ParameterResponse`, `ParameterUpdate`
- `ConservationAuditResponse`
- `TreasuryResponse`, `TreasuryLedgerEntry`
- `EventTriggerRequest`, `EventTriggerResponse`
- `SeasonActionRequest`, `SeasonActionResponse`
- `SimulationControlResponse`
- `AdminLedgerEntry`

---

## Files Created

| File                                                    | Type             |
| ------------------------------------------------------- | ---------------- |
| `backend/app/models/admin.py`                           | Model            |
| `backend/app/core/admin.py`                             | Auth dependency  |
| `backend/app/services/admin.py`                         | Service          |
| `backend/app/schemas/admin.py`                          | Schemas          |
| `backend/app/api/admin.py`                              | Router           |
| `backend/app/api/metrics.py`                            | Metrics endpoint |
| `backend/tests/test_admin.py`                           | Tests            |
| `infra/grafana/provisioning/datasources/datasource.yml` | Grafana config   |
| `infra/grafana/provisioning/dashboards/dashboard.yml`   | Grafana config   |
| `infra/grafana/dashboards/dge-overview.json`            | Dashboard        |
| `infra/k6/auth_load.js`                                 | Load test        |
| `infra/k6/order_storm.js`                               | Load test        |
| `infra/k6/ws_connections.js`                            | Load test        |
| `infra/k6/mixed_workload.js`                            | Load test        |
| `backend/alembic/versions/2e9f2d2c75d9_*.py`            | Migration        |

## Files Modified

| File                               | Change                                                |
| ---------------------------------- | ----------------------------------------------------- |
| `backend/app/models/player.py`     | Added `PlayerRole` enum + `role` column               |
| `backend/app/models/__init__.py`   | Registered `SimulationParameter`                      |
| `backend/app/main.py`              | Added admin router, metrics router, parameter seeding |
| `backend/app/simulation/worker.py` | Pause flag check before tick                          |
| `backend/app/simulation/tick.py`   | Parameter loading at step 4b                          |
| `backend/tests/conftest.py`        | Added `SimulationParameter` to cleanup                |
| `infra/prometheus.yml`             | Reduced scrape interval to 5s                         |
| `docker-compose.yml`               | Added prometheus + grafana services                   |

---

## Design Decisions

1. **DB-backed metrics** — gauges refreshed on each Prometheus scrape rather than in-process counters. Slightly higher scrape cost but zero drift risk and works across multiple API processes.

2. **Short-lived Redis for pause/resume** — admin endpoints create and dispose their own Redis connections instead of using the shared pool. Avoids event loop binding issues in test environments.

3. **Parameter propagation via tick** — rather than Redis pub/sub invalidation, worker loads all parameters from DB at tick start. Simpler, guaranteed consistency, at most 1 tick delay.

4. **No new ledger entry types** — admin-triggered events use existing `Event` model. Manual balance adjustments would use existing `ADMIN_ADJUSTMENT` entry type (already in enum).

5. **42 tunable parameters** — comprehensive whitelist of gameplay tunables. Infrastructure settings (DB URL, JWT secret, Redis URL) are explicitly excluded.

---

## Conventions Established

### 17. Admin Patterns

- Admin endpoints use `AdminPlayer` dependency (reuses JWT auth + role check).
- No API-key auth — admin is a player role, not a separate auth mechanism.
- Parameter updates apply to in-memory settings immediately (same process) and persist to DB.
- Worker picks up DB-persisted parameters at next tick start via `load_parameters_into_settings()`.
- Pause/resume uses Redis key `simulation:paused` — worker checks before lock acquisition.
- Conservation audit is read-only — does not halt or correct, just reports PASS/FAIL + delta.

---

## Test Coverage

20 new tests in `test_admin.py`:

| Group              | Count | Tests                                                      |
| ------------------ | ----- | ---------------------------------------------------------- |
| Auth/Authorization | 2     | non-admin blocked, unauthenticated blocked                 |
| Simulation Control | 2     | pause, resume                                              |
| Parameters         | 4     | list, update success, invalid key, invalid value           |
| Conservation Audit | 2     | pass (healthy), fail (perturbed)                           |
| Treasury & Ledger  | 4     | treasury view, ledger view, filter by type, invalid filter |
| Events             | 2     | trigger success, invalid type                              |
| Seasons            | 3     | create, create conflict, end no active                     |
| Metrics            | 1     | all 10 metric names present                                |

**Total: 210 tests passing (current baseline)**

---

## Economic Impact

- No new currency flows introduced
- Conservation invariant now has an explicit admin audit endpoint
- Parameter tuning allows live economy balancing without code deploy
- Pause/resume enables safe maintenance windows
