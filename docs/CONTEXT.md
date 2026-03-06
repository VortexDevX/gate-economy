# DGE — Build Context

> **Usage**: Paste this into every new AI chat after the system prompt.
> Then paste the current phase's subplan (e.g., `docs/plan/PHASE_9_PLAN.md`).
> That's it — two documents total.

---

## Phase Status

| #   | Phase                       | Status  | Tests | Cumulative Tests |
| --- | --------------------------- | ------- | ----- | ---------------- |
| 1   | Foundation & Infrastructure | ✅ Done | 2     | 2                |
| 2   | Identity, Wallet & Ledger   | ✅ Done | 17    | 19               |
| 3   | Simulation Engine Core      | ✅ Done | 24    | 43               |
| 4   | Dungeon Gates               | ✅ Done | 19    | 62               |
| 5   | Market System               | ✅ Done | 28    | 90               |
| 6   | Guilds                      | ✅ Done | 19    | 109              |
| 7   | AI Traders                  | ✅ Done | 20    | 129              |
| 8   | Events, News & Real-time    | ✅ Done | 19    | 148              |
| 9   | Anti-Exploit & Balance      | 🔲 NEXT | —     | —                |
| 10  | Leaderboards & Seasons      | 🔲      | —     | —                |
| 11  | Admin & Observability       | 🔲      | —     | —                |
| 12  | Frontend                    | 🔲      | —     | —                |
| 13  | Hardening & Launch Prep     | 🔲      | —     | —                |

**Baseline: 148 tests passing**

---

## Economic Model

**Hard invariant** (verified every tick — violation halts simulation):

```
treasury_balance + SUM(player_balances) + SUM(guild_treasuries) = INITIAL_SEED
```

| Flow    | Direction         | Active Examples                                               |
| ------- | ----------------- | ------------------------------------------------------------- |
| Faucet  | Treasury → Player | Yield payments, starting grant, AI budget, yield boom bonus   |
| Faucet  | Treasury → Guild  | Yield to guild gate holdings, yield boom to guild holdings    |
| Faucet  | Guild → Players   | Dividends (manual + auto)                                     |
| Sink    | Player → Treasury | Trade fees, gate discovery cost, ISO proceeds, guild creation |
| Sink    | Guild → Treasury  | Guild maintenance                                             |
| Lock    | Player → Treasury | Buy order escrow, AI buy escrow                               |
| Lock    | Guild → Treasury  | Guild invest escrow                                           |
| Unlock  | Treasury → Player | Escrow release (cancel/fill excess), AI escrow release        |
| Unlock  | Treasury → Guild  | Guild escrow release                                          |
| Neutral | Player ↔ Player   | Share trades (minus fees to treasury)                         |
| Neutral | Treasury → Guild  | Guild ISO proceeds                                            |

**Future sinks** (not yet active): portfolio maintenance, concentration penalties, liquidity decay.

---

## Database Schema (Cumulative)

### players

`id` UUID PK · `username` VARCHAR UQ · `email` VARCHAR UQ · `password_hash` VARCHAR · `balance_micro` BIGINT ≥0 · `is_ai` BOOL default FALSE · `created_at`/`updated_at` TZ

### system_accounts

`id` UUID PK · `account_type` ENUM('TREASURY') UQ · `balance_micro` BIGINT ≥0 · `created_at` TZ

### ledger_entries _(append-only — no UPDATE/DELETE)_

`id` BIGSERIAL PK · `tick_id` INT NULL FK→ticks · `debit_type`/`credit_type` ENUM('PLAYER','SYSTEM','GUILD') · `debit_id`/`credit_id` UUID · `amount_micro` BIGINT >0 · `entry_type` EntryType · `memo` TEXT · `created_at` TZ

**EntryType enum**: STARTING_GRANT, YIELD_PAYMENT, TRADE_SETTLEMENT, TRADE_FEE, GATE_DISCOVERY, GUILD_CREATION, GUILD_MAINTENANCE, PORTFOLIO_MAINTENANCE, CONCENTRATION_PENALTY, LIQUIDITY_DECAY, DIVIDEND, AI_BUDGET, ADMIN_ADJUSTMENT, ESCROW_LOCK, ESCROW_RELEASE

### ticks

`id` SERIAL PK · `tick_number` INT UQ · `seed` BIGINT · `started_at`/`completed_at` TZ · `intent_count` INT · `state_hash` VARCHAR(64)

### intents

`id` UUID PK · `player_id` UUID FK→players · `intent_type` IntentType · `payload` JSONB · `status` IntentStatus · `reject_reason` TEXT NULL · `created_at` TZ · `processed_tick` INT NULL FK→ticks

**IntentType**: DISCOVER_GATE, PLACE_ORDER, CANCEL_ORDER, CREATE_GUILD, GUILD_DIVIDEND, GUILD_INVEST
**IntentStatus**: QUEUED, PROCESSING, EXECUTED, REJECTED

### gate_rank_profiles

`rank` GateRank PK · `stability_init` DECIMAL · `volatility` DECIMAL · `yield_min_micro`/`yield_max_micro` BIGINT · `total_shares` INT · `lifespan_min`/`lifespan_max` INT · `collapse_threshold` DECIMAL · `discovery_cost_micro` BIGINT · `spawn_weight` INT

**Seed data:**

| Rank | stab | vol  | yield_min | yield_max | shares | collapse_thresh | disc_cost  | weight |
| ---- | ---- | ---- | --------- | --------- | ------ | --------------- | ---------- | ------ |
| E    | 100  | 0.05 | 1,000     | 5,000     | 100    | 20              | 100,000    | 40     |
| D    | 95   | 0.08 | 3,000     | 10,000    | 80     | 22              | 250,000    | 25     |
| C    | 90   | 0.12 | 8,000     | 25,000    | 60     | 25              | 500,000    | 18     |
| B    | 85   | 0.15 | 20,000    | 60,000    | 50     | 28              | 1,000,000  | 10     |
| A    | 80   | 0.20 | 50,000    | 150,000   | 40     | 30              | 2,500,000  | 5      |
| S    | 75   | 0.25 | 120,000   | 400,000   | 30     | 35              | 5,000,000  | 2      |
| S+   | 70   | 0.30 | 300,000   | 1,000,000 | 20     | 40              | 10,000,000 | 1      |

### gates

`id` UUID PK · `rank` GateRank FK · `stability` DECIMAL · `volatility` DECIMAL · `base_yield_micro` BIGINT · `total_shares` INT · `status` GateStatus · `spawned_at_tick` INT · `collapsed_at_tick` INT NULL · `discovery_type` DiscoveryType · `discoverer_id` UUID NULL FK→players

**GateStatus**: OFFERING, ACTIVE, UNSTABLE, COLLAPSED
**DiscoveryType**: SYSTEM, PLAYER

### gate_shares

`gate_id` UUID FK→gates · `player_id` UUID _(plain, NO FK — can hold treasury UUID)_ · `quantity` INT ≥0 · PK: (gate_id, player_id)

### guilds

`id` UUID PK · `name` VARCHAR UQ · `founder_id` UUID FK→players · `treasury_micro` BIGINT ≥0 · `total_shares` INT · `public_float_pct` DECIMAL · `dividend_policy` DividendPolicy · `auto_dividend_pct` DECIMAL NULL · `status` GuildStatus default ACTIVE · `created_at_tick` INT · `maintenance_cost_micro` BIGINT · `missed_maintenance_ticks` INT default 0 · `insolvent_ticks` INT default 0

**GuildStatus**: ACTIVE, INSOLVENT, DISSOLVED
**DividendPolicy**: MANUAL, AUTO_FIXED_PCT

Property: `balance_micro` ↔ `treasury_micro` (property alias for TransferService compatibility)

### guild_members

`guild_id` UUID FK→guilds · `player_id` UUID FK→players · `role` GuildRole · `joined_at_tick` INT · PK: (guild_id, player_id)

**GuildRole**: LEADER, OFFICER, MEMBER

### guild_shares

`guild_id` UUID FK→guilds · `player_id` UUID _(plain, NO FK — can hold guild.id for ISO float)_ · `quantity` INT ≥0 · PK: (guild_id, player_id)

### guild_gate_holdings

`guild_id` UUID FK→guilds · `gate_id` UUID FK→gates · `quantity` INT ≥0 · PK: (guild_id, gate_id)

### orders

`id` UUID PK · `player_id` UUID _(plain, NO FK — can hold treasury/guild UUID)_ · `guild_id` UUID NULL _(marks guild orders)_ · `asset_type` AssetType · `asset_id` UUID · `side` OrderSide · `quantity` INT >0 · `price_limit_micro` BIGINT >0 · `filled_quantity` INT ≥0 default 0 · `escrow_micro` BIGINT ≥0 default 0 · `status` OrderStatus default OPEN · `created_at_tick` INT · `updated_at_tick` INT NULL · `is_system` BOOL default FALSE

**AssetType**: GATE_SHARE, GUILD_SHARE
**OrderSide**: BUY, SELL
**OrderStatus**: OPEN, PARTIAL, FILLED, CANCELLED

Property: `remaining = quantity - filled_quantity`

### trades

`id` UUID PK · `buy_order_id` UUID · `sell_order_id` UUID · `asset_type` AssetType · `asset_id` UUID · `quantity` INT · `price_micro` BIGINT · `buyer_fee_micro` BIGINT · `seller_fee_micro` BIGINT · `tick_id` INT FK→ticks · `created_at` TZ

### market_prices

PK: (`asset_type`, `asset_id`) · `last_price_micro` BIGINT NULL · `best_bid_micro` BIGINT NULL · `best_ask_micro` BIGINT NULL · `volume_24h_micro` BIGINT default 0 · `updated_at_tick` INT

### events

`id` UUID PK · `event_type` EventType · `tick_id` INT · `target_id` UUID NULL · `payload` JSONB NULL · `created_at` TZ

**EventType**: STABILITY_SURGE, STABILITY_CRISIS, YIELD_BOOM, MARKET_SHOCK, DISCOVERY_SURGE

### news

`id` UUID PK · `tick_id` INT · `headline` VARCHAR(200) · `body` TEXT NULL · `category` NewsCategory · `importance` INT default 1 · `related_entity_type` VARCHAR(50) NULL · `related_entity_id` UUID NULL · `created_at` TZ

**NewsCategory**: GATE, MARKET, GUILD, WORLD

---

## Tick Pipeline (Current State)

```
1.  Determine tick_number ✅ P3
2.  Derive seed + create TickRNG ✅ P3
3.  Insert tick record ✅ P3
4.  Load treasury_id ✅ P4
5.  Collect QUEUED intents → mark PROCESSING ✅ P3
6.  Process intents by type:
    DISCOVER_GATE ✅ P4
    PLACE_ORDER ✅ P5
    CANCEL_ORDER ✅ P5
    CREATE_GUILD ✅ P6
    GUILD_DIVIDEND ✅ P6
    GUILD_INVEST ✅ P6
7.  System gate spawn + lifecycle + yield ✅ P4 (yield extended P6 for guild holdings)
7b. Guild lifecycle (maintenance, insolvency, auto-dividends) ✅ P6
7c. AI traders (cancel old orders, run strategies) ✅ P7
8.  Create ISO orders for OFFERING gates + guild shares ✅ P5 (extended P6)
9.  Cancel orders for COLLAPSED gates + DISSOLVED guilds ✅ P5 (extended P6)
10. Match orders ✅ P5 (extended P6 for GUILD_SHARE + guild orders)
11. Finalize ISO transitions ✅ P5
12. Update market prices ✅ P5
13. Roll events ✅ P8
13b. Generate news ✅ P8
14. Anti-exploit maintenance 🔲 P9
15. Mark PROCESSING intents → EXECUTED ✅ P3
16. Compute state_hash ✅ P3 (extended P4, P5, P6)
17. Finalize tick record ✅ P3
18. Publish realtime update (after commit) ✅ P8
```

---

## API Endpoints (Cumulative)

| Method | Path                                   | Auth | Phase | Purpose                    |
| ------ | -------------------------------------- | ---- | ----- | -------------------------- |
| GET    | /health                                | No   | 1     | Health check               |
| GET    | /ready                                 | No   | 1     | DB + Redis connectivity    |
| POST   | /auth/register                         | No   | 2     | Create account + grant     |
| POST   | /auth/login                            | No   | 2     | JWT access + refresh       |
| POST   | /auth/refresh                          | No   | 2     | New access token           |
| GET    | /players/me                            | Yes  | 2     | Profile + balance          |
| GET    | /players/me/ledger                     | Yes  | 2     | Paginated ledger           |
| POST   | /intents                               | Yes  | 3     | Submit intent              |
| GET    | /simulation/status                     | No   | 3     | Tick number, state         |
| GET    | /gates                                 | No   | 4     | List gates (filter/page)   |
| GET    | /gates/{id}                            | No   | 4     | Gate detail + shareholders |
| GET    | /gates/rank-profiles                   | No   | 4     | Rank reference data        |
| GET    | /orders/me                             | Yes  | 5     | My orders (paginated)      |
| GET    | /market/{asset_type}/{asset_id}        | No   | 5     | Price, bid/ask, volume     |
| GET    | /market/{asset_type}/{asset_id}/book   | No   | 5     | Aggregated order book      |
| GET    | /market/{asset_type}/{asset_id}/trades | No   | 5     | Recent trades (paginated)  |
| GET    | /guilds                                | No   | 6     | List guilds (filter/page)  |
| GET    | /guilds/{id}                           | No   | 6     | Guild detail + members     |
| GET    | /news                                  | No   | 8     | Paginated news feed        |
| WS     | /ws                                    | No   | 8     | Real-time tick updates     |

---

## Config Values

| Parameter                          | Value                                                 | Phase | Notes                   |
| ---------------------------------- | ----------------------------------------------------- | ----- | ----------------------- |
| DB URL                             | `...asyncpg://dge:dge_dev@postgres:5432/dungeon_gate` | 1     | Docker internal         |
| Redis URL                          | `redis://redis:6379/0`                                | 1     |                         |
| INITIAL_SEED                       | 100,000,000,000 micro                                 | 2     | 100,000 currency        |
| STARTING_BALANCE                   | 10,000,000 micro                                      | 2     | 10 currency             |
| JWT access expiry                  | 15 min                                                | 2     |                         |
| JWT refresh expiry                 | 7 days                                                | 2     |                         |
| simulation_initial_seed            | 42                                                    | 3     | RNG chain start         |
| simulation_tick_interval           | 5s                                                    | 3     |                         |
| system_spawn_probability           | 0.15                                                  | 4     | ~3 gates/min            |
| gate_offering_ticks                | 60                                                    | 4     | OFFERING duration       |
| gate_base_decay_rate               | 0.1                                                   | 4     | Stability decay/tick    |
| base_fee_rate                      | 0.005 (0.5%)                                          | 5     | Minimum trade fee rate  |
| progressive_fee_rate               | 0.5                                                   | 5     | Fee scaling factor      |
| fee_scale_micro                    | 10,000,000                                            | 5     | Progressive denominator |
| max_fee_rate                       | 0.10 (10%)                                            | 5     | Hard cap on fee rate    |
| iso_payback_ticks                  | 100                                                   | 5     | ISO price derivation    |
| guild_creation_cost_micro          | 50,000,000                                            | 6     | 50 currency             |
| guild_total_shares                 | 1,000                                                 | 6     | Shares per guild        |
| guild_max_float_pct                | 0.49                                                  | 6     | Max public float        |
| guild_base_maintenance_micro       | 100,000                                               | 6     | 0.1 currency/tick       |
| guild_maintenance_scale            | 0.001                                                 | 6     | Scale on gate value     |
| guild_insolvency_threshold         | 3                                                     | 6     | Missed → INSOLVENT      |
| guild_dissolution_threshold        | 10                                                    | 6     | Insolvent → DISSOLVED   |
| guild_liquidation_discount         | 0.50                                                  | 6     | Liquidation at 50%      |
| ai_market_maker_budget_micro       | 2,000,000,000                                         | 7     | 2,000 currency          |
| ai_value_investor_budget_micro     | 1,000,000,000                                         | 7     | 1,000 currency          |
| ai_noise_trader_budget_micro       | 500,000,000                                           | 7     | 500 currency            |
| ai_mm_spread                       | 0.05                                                  | 7     | 5% bid/ask spread       |
| ai_mm_order_qty                    | 5                                                     | 7     | Shares per MM order     |
| ai_vi_buy_discount                 | 0.30                                                  | 7     | Buy below fair × 0.7    |
| ai_vi_sell_premium                 | 0.30                                                  | 7     | Sell above fair × 1.3   |
| ai_noise_activity                  | 0.40                                                  | 7     | NT action probability   |
| ai_noise_max_qty                   | 3                                                     | 7     | Max shares per NT trade |
| event_probability                  | 0.10                                                  | 8     | Event chance per tick   |
| event_stability_surge_min/max      | 5.0 / 15.0                                            | 8     | Surge stability range   |
| event_stability_crisis_min/max     | 5.0 / 15.0                                            | 8     | Crisis stability range  |
| event_market_shock_min/max         | 2.0 / 5.0                                             | 8     | Shock stability range   |
| event_yield_boom_min/max_mult      | 2.0 / 4.0                                             | 8     | Boom yield multiplier   |
| event_discovery_surge_min/max      | 1 / 3                                                 | 8     | Extra gates spawned     |
| news_large_trade_threshold_micro   | 1,000,000                                             | 8     | Trade news cutoff       |

<!-- PHASE_CONFIG: Add new config params here after each phase -->

---

## Folder Structure

```
dungeon-gate-economy/
├── .github/workflows/ci.yml
├── backend/
│   ├── alembic/versions/              # 6 migrations
│   ├── app/
│   │   ├── api/                       # auth, gates, guilds, health, intents, market, news, orders, players, simulation, ws
│   │   ├── core/                      # auth (JWT/Argon2), deps (get_db, get_redis, get_current_player)
│   │   ├── models/                    # base, event, gate, guild, intent, ledger, market, news, player, tick, treasury
│   │   ├── schemas/                   # auth, gate, guild, intent, market, news, player, simulation
│   │   ├── services/                  # ai_traders, auth, event_engine, fee_calculator, gate_lifecycle, guild_manager, news_generator, order_matching, realtime, transfer
│   │   ├── simulation/               # lock, rng, state_hash, tick, worker
│   │   ├── config.py, database.py, main.py
│   ├── tests/                         # 20 test files, 148 tests
│   ├── Dockerfile, alembic.ini, pyproject.toml, requirements.txt
├── docs/
│   ├── plan/                          # PLAN.md + PHASE_X_PLAN.md files
│   ├── postman/                       # Postman collection
│   ├── summary/                       # SUMMARY_1-8.md
│   ├── CONTEXT.md                     # ← THIS FILE
│   ├── architecture.md, runbook.md
├── frontend/src/                      # .gitkeep only
├── infra/                             # prometheus.yml, grafana/, k6/
├── .env.example, Makefile, docker-compose.yml
```

<!-- FOLDER: Update after significant structural changes -->

---

## Conventions & Critical Patterns

### 1. Test Infrastructure

- **Autouse fixture `_clean_state`** wipes ALL data and resets treasury to INITIAL_SEED before every test. Never assume leftover state.
- **NullPool engines** per test fixture — avoids asyncio event loop binding issues.
- **`pause_simulation`** fixture holds Redis lock to prevent Celery worker from running ticks during tests.
- **`funded_player_id`** fixture creates a player with `starting_balance_micro` properly debited from treasury — use for tests needing a player with funds.
- **`test_player_id`** fixture creates a player with 0 balance — use when funds are not needed.

### 2. Treasury-as-Holder

- `gate_shares.player_id` and `orders.player_id` have **NO FK to players** — treasury UUID sits there directly.
- `guild_shares.player_id` has **NO FK** — guild's own UUID sits there for ISO float.
- Use same pattern for any table where treasury or guild participates as an entity.
- Yield distribution **skips treasury-held shares** (no self-payment).
- Dividend distribution **skips guild-held shares** (no self-payment).
- ISO trades skip self-transfers (treasury is both seller and escrow holder).

### 3. Settings Mutation in Tests

- Tests modify `settings.*` directly (e.g., `settings.system_spawn_probability = 0.0`) and restore via `try/finally` or autouse fixtures.
- Works because Settings is a module-level singleton.

### 4. Enum Evolution in Migrations

- Adding values to PostgreSQL enums requires manual `ALTER TYPE ... ADD VALUE IF NOT EXISTS` in the migration.
- **Alembic autogenerate does NOT handle this** — always check and edit migration SQL.

### 5. Intent Processing

- `_process_intents()` in `tick.py` routes by IntentType, takes `treasury_id` and `tick_id` params.
- Step 15 preserves REJECTED status — only PROCESSING intents become EXECUTED.

### 6. Money Rules

- All currency as BIGINT micro-units (1 currency = 1,000,000 micro).
- Integer division for pro-rata calculations (remainder stays in treasury/guild).
- No negative balances ever — deduct what's available, floor at zero.
- Every balance change through `TransferService.transfer()` with ledger entry.

### 7. State Hash

- SHA-256 of: treasury balance + player balances (ordered by ID) + gate counts per status + total stability (truncated) + total shares held + open order count + total escrow in BUY orders + total trade count + guild treasury sum + guild counts per status.
- Extended each phase with new state dimensions.

### 8. Escrow Model

- BUY orders: escrow = `quantity × price_limit + max_fee` locked via `transfer(PLAYER → TREASURY, ESCROW_LOCK)`.
- Guild BUY orders: escrow locked via `transfer(GUILD → TREASURY, ESCROW_LOCK)`.
- On fill: trade_value + buyer_fee consumed from escrow (stays in treasury). Seller paid via `transfer(TREASURY → SELLER, TRADE_SETTLEMENT)`.
- On full fill: excess escrow released via `transfer(TREASURY → PLAYER/GUILD, ESCROW_RELEASE)`.
- On cancel: full remaining escrow released.
- ISO: no settlement transfer needed — escrow IS the payment (treasury is seller).
- Guild ISO: proceeds go to guild treasury via `transfer(TREASURY → GUILD, TRADE_SETTLEMENT)`.

### 9. Delivery Style

- Step-by-step, max 2-3 files per message.
- Always full filepath: `backend/app/...` not `app/...`.
- For small updates to existing files, describe edits inline rather than replacing entire file.
- User creates files manually, runs `make test` after each batch, reports results.

### 10. Docker Ports

- Host ports remapped: Postgres **5433**, Redis **6380** (local services occupy defaults).
- Worker: `celery -A app.simulation.worker:celery_app worker -B --concurrency=1`

### 11. Files to Request Before Coding a New Phase

Before writing any code for a new phase, ask the user for the current versions of files you'll need to modify. At minimum:

- `simulation/tick.py` (pipeline wiring)
- `models/__init__.py` (model registration)
- `main.py` (router registration)
- Any model files being extended (e.g., `ledger.py` for new enum values)
- `tests/conftest.py` (if new fixtures needed)
- `simulation/state_hash.py` (if extending)

### 12. Guild Patterns

- Guild `balance_micro` property maps to `treasury_micro` — lets TransferService work without modification.
- `guild_id` on Order (nullable) explicitly marks guild orders — escrow/settlement uses guild treasury.
- Guild ISO price = `guild_creation_cost_micro // guild_total_shares`.
- No seller fee on guild ISO (same as gate ISO — bootstrap selling).
- Maintenance cost = `base + int(gate_value * scale)` — scales with power.
- Insolvency after N consecutive missed maintenance ticks → 50% yield penalty.
- Dissolution: liquidate holdings at discount → distribute to shareholders → cancel orders → sweep remainder.

### 13. AI Trader Patterns

- AI bots are regular players with `is_ai=True` and `password_hash="!ai-no-login"`.
- AI creates orders directly in tick pipeline step 7c (not via intents).
- Cancel-and-replace pattern: all OPEN/PARTIAL orders cancelled each tick, escrow released, new orders placed.
- AI uses same escrow/transfer system as human players — fully auditable.
- Strategies use tick RNG for deterministic replay.
- AI only trades GATE_SHARE (GUILD_SHARE deferred).
- AI budgets are one-time treasury funding — if AI goes broke, it stops trading naturally.

### 14. Event & News Patterns

- Events roll in step 13 (after order matching) — effects hit next tick's trading.
- At most 1 event per tick; list structure supports future multi-event expansion.
- YIELD_BOOM reuses `YIELD_PAYMENT` entry type — no new ledger enum needed.
- `spawn_gate()` extracted from `system_spawn_gate()` for reuse by DISCOVERY_SURGE.
- News is post-hoc scan — no modifications to existing services.
- Realtime publish is fire-and-forget after commit — tick integrity never compromised.
- WebSocket `/ws` is unauthenticated public read-only feed via Redis pub/sub bridge.

<!-- CONVENTIONS: Add new patterns discovered during implementation -->

---

## Upcoming Phases (Brief)

| Phase  | One-line Summary                                                            |
| ------ | --------------------------------------------------------------------------- |
| **9**  | Concentration penalties, liquidity decay, portfolio maintenance, float caps |
| **10** | Net worth leaderboards with decay, seasonal resets                          |
| **11** | Admin API, tunable parameters, Prometheus/Grafana, k6 load tests            |
| **12** | React frontend (all player-facing features)                                 |
| **13** | Replay tests, conservation soak, fuzz, security audit, load test, docs      |

---

## How to Update This File

After completing each phase:

1. ✅ **Phase Status** — check off completed, update test counts, mark next
2. 📋 **Database Schema** — add any new tables/columns
3. 🔌 **Tick Pipeline** — update step status markers
4. 🌐 **API Endpoints** — add new rows
5. ⚙️ **Config Values** — add new parameters
6. 📁 **Folder Structure** — update if significant new dirs/files
7. 📝 **Conventions** — add any new patterns discovered
8. 🗑️ **Upcoming Phases** — remove completed phase from the table