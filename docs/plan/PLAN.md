# DUNGEON GATE ECONOMY — BUILD PLAN

## Economic Model Summary (locked in)

| Flow        | Direction          | Examples                                                                                                                            |
| ----------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Faucet**  | Treasury → Players | Yield payments, starting balance                                                                                                    |
| **Sink**    | Players → Treasury | Trade fees, gate discovery cost, guild creation, guild maintenance, portfolio maintenance, concentration penalties, liquidity decay |
| **Neutral** | Player ↔ Player    | Share trades (minus fee)                                                                                                            |

**Hard invariant**: `treasury_balance + SUM(all_player_balances) + SUM(all_guild_treasuries) = INITIAL_SEED`  
Verified automatically. If it ever breaks, simulation halts.

---

## Project Structure (established in Phase 1, grows over all phases)

```
dungeon-gate-economy/
├── docker-compose.yml
├── Makefile
├── .github/workflows/ci.yml
├── backend/
│   ├── alembic/
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory
│   │   ├── config.py                # Pydantic Settings
│   │   ├── database.py              # async engine, session
│   │   ├── models/                  # SQLAlchemy models
│   │   │   ├── player.py
│   │   │   ├── ledger.py
│   │   │   ├── treasury.py
│   │   │   ├── gate.py
│   │   │   ├── market.py
│   │   │   ├── guild.py
│   │   │   ├── tick.py
│   │   │   ├── event.py
│   │   │   ├── news.py
│   │   │   ├── season.py
│   │   │   └── ai_trader.py
│   │   ├── schemas/                 # Pydantic request/response
│   │   ├── api/                     # FastAPI routers
│   │   │   ├── auth.py
│   │   │   ├── players.py
│   │   │   ├── gates.py
│   │   │   ├── market.py
│   │   │   ├── guilds.py
│   │   │   ├── intents.py
│   │   │   ├── news.py
│   │   │   ├── leaderboard.py
│   │   │   ├── admin.py
│   │   │   └── ws.py
│   │   ├── services/                # Business logic
│   │   │   ├── transfer.py
│   │   │   ├── auth.py
│   │   │   ├── gate_lifecycle.py
│   │   │   ├── order_matching.py
│   │   │   ├── guild_manager.py
│   │   │   ├── ai_trader.py
│   │   │   ├── event_engine.py
│   │   │   ├── news_generator.py
│   │   │   ├── leaderboard.py
│   │   │   └── anti_exploit.py
│   │   ├── simulation/
│   │   │   ├── worker.py            # Celery app
│   │   │   ├── tick.py              # Tick pipeline
│   │   │   ├── rng.py               # Deterministic RNG
│   │   │   └── lock.py             # Redis leadership lock
│   │   └── core/
│   │       ├── auth.py              # JWT + Argon2 utils
│   │       ├── deps.py              # FastAPI dependencies
│   │       └── constants.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_transfer.py
│   │   ├── test_auth.py
│   │   ├── test_tick.py
│   │   ├── test_gates.py
│   │   ├── test_market.py
│   │   ├── test_guilds.py
│   │   ├── test_conservation.py
│   │   ├── test_replay.py
│   │   └── test_anti_exploit.py
│   └── requirements.txt
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── ws/
│   │   └── App.tsx
│   └── tailwind.config.js
├── infra/
│   ├── prometheus.yml
│   ├── grafana/
│   └── k6/
└── docs/
    ├── architecture.md
    └── runbook.md
```

---

## PHASE 1: Foundation & Infrastructure

**Goal**: Bootable dev environment — database, cache, API skeleton, CI pipeline.

**Deliverables**:
| Item | Detail |
|---|---|
| Docker Compose | Postgres 15, Redis 7, `api` service, `worker` service (Celery placeholder) |
| FastAPI skeleton | App factory, CORS, exception handlers |
| Database | SQLAlchemy async engine + session factory, Alembic init |
| Config | `config.py` via Pydantic Settings, `.env` file |
| Logging | Structured JSON to stdout |
| CI | GitHub Actions: `ruff`, `mypy`, `pytest`, Docker build |
| Makefile | `make up`, `make down`, `make migrate`, `make test`, `make lint` |

**API Endpoints**:
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Returns 200 |
| `GET` | `/ready` | Checks DB + Redis connectivity |

**Acceptance Criteria**:

- `docker compose up` boots all services, API responds on port 8000
- `make test` runs (even if 0 tests)
- CI green on push

**Depends on**: Nothing

---

## PHASE 2: Identity, Wallet & Ledger

**Goal**: Players register, log in, receive a starting balance from treasury. All money movement is atomic and auditable.

**Database Tables**:

```
players
  id              UUID PK
  username        VARCHAR UNIQUE NOT NULL
  email           VARCHAR UNIQUE NOT NULL
  password_hash   VARCHAR NOT NULL
  balance_micro   BIGINT NOT NULL DEFAULT 0  CHECK (balance_micro >= 0)
  is_ai           BOOLEAN DEFAULT FALSE
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ

system_accounts
  id              UUID PK
  account_type    ENUM('TREASURY')  UNIQUE
  balance_micro   BIGINT NOT NULL  CHECK (balance_micro >= 0)
  created_at      TIMESTAMPTZ

ledger_entries
  id              BIGSERIAL PK
  tick_id         INT NULL FK → ticks
  debit_type      ENUM('PLAYER','SYSTEM','GUILD')
  debit_id        UUID
  credit_type     ENUM('PLAYER','SYSTEM','GUILD')
  credit_id       UUID
  amount_micro    BIGINT NOT NULL  CHECK (amount_micro > 0)
  entry_type      ENUM(see below)
  memo            TEXT
  created_at      TIMESTAMPTZ DEFAULT now()
```

`entry_type` values: `STARTING_GRANT`, `YIELD_PAYMENT`, `TRADE_SETTLEMENT`, `TRADE_FEE`, `GATE_DISCOVERY`, `GUILD_CREATION`, `GUILD_MAINTENANCE`, `PORTFOLIO_MAINTENANCE`, `CONCENTRATION_PENALTY`, `LIQUIDITY_DECAY`, `DIVIDEND`, `AI_BUDGET`, `ADMIN_ADJUSTMENT`

**No UPDATE or DELETE** on `ledger_entries`. Enforced by application convention (no ORM update methods exposed) and optionally a DB trigger.

**Key Service — `TransferService.transfer()`**:

```
Within a single DB transaction:
1. SELECT FOR UPDATE source account
2. Assert source.balance_micro >= amount
3. Debit source (UPDATE balance_micro -= amount)
4. Credit destination (UPDATE balance_micro += amount)
5. INSERT ledger_entry
6. Commit
On any failure → rollback, raise
```

**Treasury Seeding**: Alembic data migration or startup hook inserts treasury with `INITIAL_SEED` (configurable, e.g., 100 billion micro-units = 100,000 currency).

**API Endpoints**:
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/auth/register` | Create account, grant starting balance from treasury |
| `POST` | `/auth/login` | Returns JWT access + refresh tokens |
| `POST` | `/auth/refresh` | New access token |
| `GET` | `/players/me` | Profile + balance |
| `GET` | `/players/me/ledger` | Paginated personal ledger |

**Auth Details**:

- Argon2id password hashing
- JWT access token: 15 min expiry
- JWT refresh token: 7 day expiry
- Auth dependency extracts player from token, injects into route

**Acceptance Criteria**:

- Registration → player gets starting balance, treasury debited by same amount
- Double registration (same email/username) rejected
- Login returns valid tokens, protected routes work
- `transfer()` with insufficient balance → rollback, no state change
- **Conservation test**: after N registrations, `treasury + SUM(player balances) = INITIAL_SEED`
- Ledger is append-only (test that no UPDATE/DELETE path exists in service layer)

**Depends on**: Phase 1

---

## PHASE 3: Simulation Engine Core

**Goal**: Single Celery worker runs deterministic ticks at 5s intervals. Leadership lock guarantees single-writer. Intent queue bridges API → simulation.

**Database Tables**:

```
ticks
  id              SERIAL PK
  tick_number     INT UNIQUE NOT NULL
  seed            BIGINT NOT NULL
  started_at      TIMESTAMPTZ
  completed_at    TIMESTAMPTZ
  intent_count    INT
  state_hash      VARCHAR(64)

intents
  id              UUID PK
  player_id       UUID FK → players
  intent_type     ENUM('DISCOVER_GATE','PLACE_ORDER','CANCEL_ORDER',
                       'CREATE_GUILD','GUILD_DIVIDEND','GUILD_INVEST')
  payload         JSONB NOT NULL
  status          ENUM('QUEUED','PROCESSING','EXECUTED','REJECTED')
  reject_reason   TEXT NULL
  created_at      TIMESTAMPTZ
  processed_tick  INT NULL FK → ticks
```

**Leadership Lock** (`simulation/lock.py`):

- `Redis SETNX` with key `sim:leader`, value = worker ID, TTL = 4s
- Before each tick: acquire lock. If failed, skip (another worker is running).
- After tick: delete lock.
- Prevents two workers from ever mutating state concurrently.

**Deterministic RNG** (`simulation/rng.py`):

- `TickRNG` class wrapping `random.Random`
- Seed derivation: `seed_n = hash(seed_{n-1} || tick_number)` using SHA-256 truncated to 64-bit int
- Initial seed from config
- All stochastic decisions in a tick **must** use this instance. No `import random` anywhere else.

**Tick Pipeline** (`simulation/tick.py`):

```python
async def execute_tick(tick_number: int, previous_seed: int):
    # 1. Acquire lock
    # 2. Compute seed, create TickRNG
    # 3. Insert tick record (started_at = now)
    # 4. Collect QUEUED intents → mark PROCESSING
    # 5. ---- Phase 4+: Process intents by type ----
    # 6. ---- Phase 4+: Advance gates ----
    # 7. ---- Phase 5+: Match orders ----
    # 8. ---- Phase 8+: Roll events ----
    # 9. ---- Phase 9+: Anti-exploit maintenance ----
    # 10. Mark intents EXECUTED/REJECTED
    # 11. Compute state_hash (hash of key balances + gate states)
    # 12. Update tick record (completed_at, state_hash)
    # 13. Release lock
    # 14. ---- Phase 8+: Publish to Redis pub/sub ----
```

Steps 5–9 are **no-ops** initially — just empty hooks that later phases fill in.

**Celery Setup**:

- `celery_app` with Redis broker
- Celery Beat schedule: `run_tick` every 5 seconds
- Worker concurrency = 1 (single thread for simulation)

**API Endpoints**:
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/intents` | Submit intent (validated by type, stored as QUEUED) |
| `GET` | `/simulation/status` | Current tick number, last completed tick, simulation running? |

**Acceptance Criteria**:

- Ticks advance every ~5s
- Only one tick runs at a time (test: start two workers, only one produces ticks)
- Intents submitted via API appear in next tick's collection
- Replaying tick N with same seed + same intents produces same `state_hash`
- Tick records are sequential with no gaps

**Depends on**: Phase 1, Phase 2

---

## PHASE 4: Dungeon Gates

**Goal**: Gates spawn, generate yield (paid from treasury), decay in stability, and collapse. Players can discover gates (currency sink).

**Database Tables**:

```
gate_rank_profiles
  rank            ENUM('E','D','C','B','A','S','S_PLUS') PK
  stability_init  DECIMAL           -- starting stability (0-100)
  volatility      DECIMAL           -- how erratic decay is
  yield_min_micro BIGINT            -- min base yield per tick
  yield_max_micro BIGINT            -- max base yield per tick
  total_shares    INT               -- shares issued per gate of this rank
  lifespan_min    INT               -- min ticks before decay pressure
  lifespan_max    INT               -- max ticks
  collapse_threshold DECIMAL        -- stability below this → UNSTABLE
  discovery_cost_micro BIGINT       -- player cost to discover this rank
  spawn_weight    INT               -- relative spawn probability

gates
  id              UUID PK
  rank            ENUM FK
  stability       DECIMAL NOT NULL
  volatility      DECIMAL NOT NULL
  base_yield_micro BIGINT NOT NULL
  total_shares    INT NOT NULL
  status          ENUM('OFFERING','ACTIVE','UNSTABLE','COLLAPSED')
  spawned_at_tick INT NOT NULL
  collapsed_at_tick INT NULL
  discovery_type  ENUM('SYSTEM','PLAYER')
  discoverer_id   UUID NULL FK → players

gate_shares
  gate_id         UUID FK → gates
  player_id       UUID FK → players
  quantity        INT NOT NULL CHECK (quantity >= 0)
  PRIMARY KEY (gate_id, player_id)
```

**Simulation Logic added to tick pipeline**:

**Step: System Spawn**

- Each tick: roll RNG against `system_spawn_probability` (configurable, e.g., 0.15 = ~3 gates/minute).
- If triggered: select rank via weighted distribution (`spawn_weight`), create gate with randomized params within rank profile ranges.
- Gate starts in `OFFERING` status. System creates gate_shares entry for SYSTEM account with full share count.

**Step: Process DISCOVER_GATE intents**

- Validate player has funds ≥ discovery cost for requested rank (or min rank)
- Transfer cost: player → treasury
- Roll rank: base rank = requested minimum, RNG chance to upgrade (higher spend, higher chance — but never guaranteed)
- Create gate, same as system spawn
- Gate `discoverer_id` = player

**Step: Gate Lifecycle (per ACTIVE/UNSTABLE gate)**

```
age = current_tick - spawned_at_tick
decay_rate = base_decay(rank) * (1 + volatility * rng.gauss(0, 0.3))
gate.stability -= decay_rate
if gate.stability < collapse_threshold AND status == ACTIVE:
    gate.status = UNSTABLE
if status == UNSTABLE:
    collapse_prob = (collapse_threshold - stability) / collapse_threshold
    if rng.random() < collapse_prob:
        gate.status = COLLAPSED
        gate.collapsed_at_tick = current_tick
```

**Step: Yield Distribution (per ACTIVE gate)**

```
effective_yield = base_yield_micro * (stability / 100.0)
total_shares_outstanding = SUM(gate_shares.quantity) for this gate
if total_shares_outstanding == 0 or effective_yield <= 0:
    skip
if treasury.balance_micro < effective_yield:
    effective_yield = treasury.balance_micro  # cap at available
for each shareholder:
    payout = effective_yield * (holder.quantity / total_shares_outstanding)
    transfer(TREASURY → holder, payout, YIELD_PAYMENT)
```

**API Endpoints**:
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/gates` | List gates (filter by status, rank) |
| `GET` | `/gates/{id}` | Gate detail (stats, shareholders summary) |
| `POST` | `/intents` | `type=DISCOVER_GATE`, payload: `{min_rank: "C"}` |

**Acceptance Criteria**:

- System spawns gates over time (run 100 ticks, count gates > 0)
- Player discovery deducts cost, creates gate
- Stability decays over ticks
- Gates transition ACTIVE → UNSTABLE → COLLAPSED
- Yield paid from treasury to shareholders
- No yield when treasury empty (graceful degradation)
- Conservation invariant holds

**Depends on**: Phase 3, Phase 2

---

## PHASE 5: Market System

**Goal**: Order book for gate shares (and later guild shares). Matched each tick. Price formation. Progressive fees.

**Database Tables**:

```
orders
  id              UUID PK
  player_id       UUID FK
  asset_type      ENUM('GATE_SHARE','GUILD_SHARE')
  asset_id        UUID NOT NULL
  side            ENUM('BUY','SELL')
  quantity        INT NOT NULL
  price_limit_micro BIGINT NOT NULL
  filled_quantity INT NOT NULL DEFAULT 0
  status          ENUM('OPEN','PARTIAL','FILLED','CANCELLED')
  created_at_tick INT
  updated_at_tick INT

trades
  id              UUID PK
  buy_order_id    UUID FK → orders
  sell_order_id   UUID FK → orders
  asset_type      ENUM
  asset_id        UUID
  quantity        INT
  price_micro     BIGINT
  buyer_fee_micro BIGINT
  seller_fee_micro BIGINT
  tick_id         INT FK → ticks

market_prices
  asset_type      ENUM
  asset_id        UUID
  last_price_micro BIGINT
  best_bid_micro  BIGINT NULL
  best_ask_micro  BIGINT NULL
  volume_24h_micro BIGINT DEFAULT 0
  updated_at_tick INT
  PRIMARY KEY (asset_type, asset_id)
```

**Initial Share Offering (ISO)**:

- When gate status = `OFFERING`, system places a SELL order for all shares at an initial price derived from rank profile.
- Once all shares sold (or after N ticks), gate transitions to `ACTIVE`.
- ISO proceeds go to treasury (sink).

**Intent Processing**:

- `PLACE_ORDER` intent → validate:
  - If BUY: player has balance ≥ `quantity * price_limit + estimated_fee` (escrow reserved)
  - If SELL: player owns ≥ quantity of the asset
  - Asset exists and is not COLLAPSED
- Create order record with status OPEN
- `CANCEL_ORDER` intent → mark order CANCELLED, release any escrowed funds

**Order Matching (per asset, per tick)**:

```
buy_orders  = sorted by price DESC, then created_at_tick ASC
sell_orders = sorted by price ASC,  then created_at_tick ASC

while buy_orders and sell_orders:
    best_buy = buy_orders[0]
    best_sell = sell_orders[0]
    if best_buy.price_limit_micro < best_sell.price_limit_micro:
        break  # no match
    trade_price = best_sell.price_limit_micro  # price-taker pays maker's price
    trade_qty = min(best_buy.remaining, best_sell.remaining)

    fee_buyer = calculate_fee(trade_qty * trade_price, buyer)
    fee_seller = calculate_fee(trade_qty * trade_price, seller)

    # Atomic execution:
    transfer(buyer → seller, trade_qty * trade_price, TRADE_SETTLEMENT)
    transfer(buyer → treasury, fee_buyer, TRADE_FEE)
    transfer(seller → treasury, fee_seller, TRADE_FEE)
    move_shares(seller → buyer, asset, trade_qty)

    record trade
    update order fill quantities and statuses
```

**Progressive Fee Formula**:

```
fee_rate = BASE_FEE_RATE + (order_value / FEE_SCALE) * PROGRESSIVE_RATE
fee_rate = min(fee_rate, MAX_FEE_RATE)
fee = order_value * fee_rate
```

All parameters in `simulation_parameters` table (Phase 11 formalizes, but seed defaults now).

**Escrow Model** (important for correctness):

- When a BUY order is placed, the maximum cost (`quantity * price_limit + max_fee`) is **escrowed** — deducted from player balance and held.
- On fill: actual cost deducted from escrow, remainder returned.
- On cancel: full escrow returned.
- This prevents over-spending between order placement and execution.
- Ledger entries: `ESCROW_LOCK`, `ESCROW_RELEASE`, `TRADE_SETTLEMENT`, `TRADE_FEE`

**API Endpoints**:
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/intents` | `type=PLACE_ORDER`, payload: `{asset_type, asset_id, side, quantity, price_limit}` |
| `POST` | `/intents` | `type=CANCEL_ORDER`, payload: `{order_id}` |
| `GET` | `/orders/me` | My open/recent orders |
| `GET` | `/market/{asset_type}/{asset_id}` | Price, bid/ask, depth |
| `GET` | `/market/{asset_type}/{asset_id}/book` | Order book (aggregated by price level) |
| `GET` | `/market/{asset_type}/{asset_id}/trades` | Recent trades |

**Acceptance Criteria**:

- ISO sells shares, proceeds to treasury
- Buy/sell orders match correctly (price-time priority)
- Trades execute atomically (currency + shares + fees + ledger)
- Escrow prevents over-commitment
- Cancel returns escrowed funds
- Progressive fees increase with order size
- Cannot buy shares of a COLLAPSED gate
- Cannot sell shares you don't own
- Conservation invariant holds

**Depends on**: Phase 4 (gates + shares exist)

---

## PHASE 6: Guilds

**Goal**: Player-created economic organizations with shares, dividends, operational costs, and market-tradable equity.

**Database Tables**:

```
guilds
  id                  UUID PK
  name                VARCHAR UNIQUE NOT NULL
  founder_id          UUID FK → players
  treasury_micro      BIGINT NOT NULL DEFAULT 0  CHECK (>= 0)
  total_shares        INT NOT NULL
  public_float_pct    DECIMAL NOT NULL           -- e.g., 0.30 = 30%
  dividend_policy     ENUM('MANUAL','AUTO_FIXED_PCT')
  auto_dividend_pct   DECIMAL NULL               -- if AUTO, % of treasury distributed per tick
  status              ENUM('ACTIVE','INSOLVENT','DISSOLVED')
  created_at_tick     INT
  maintenance_cost_micro BIGINT NOT NULL          -- per-tick cost

guild_members
  guild_id            UUID FK
  player_id           UUID FK
  role                ENUM('LEADER','OFFICER','MEMBER')
  joined_at_tick      INT
  PRIMARY KEY (guild_id, player_id)

guild_shares
  guild_id            UUID FK
  player_id           UUID FK
  quantity            INT NOT NULL CHECK (>= 0)
  PRIMARY KEY (guild_id, player_id)

guild_gate_holdings
  guild_id            UUID FK
  gate_id             UUID FK
  quantity            INT NOT NULL CHECK (>= 0)
  PRIMARY KEY (guild_id, gate_id)
```

**Guild Lifecycle**:

| Action          | Mechanics                                                                                                                                                                  |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Creation**    | Player pays creation fee → treasury. Gets all shares. Public float % auto-listed as ISO on market.                                                                         |
| **Revenue**     | Guild can hold gate shares (bought via leader intent). Yield from those shares → guild treasury (not player).                                                              |
| **Dividends**   | Manual: leader triggers. Auto: each tick, X% of guild treasury distributed to guild shareholders pro-rata via ledger.                                                      |
| **Maintenance** | Each tick: `maintenance_cost` debited from guild treasury → system treasury. Cost = `base + (total_assets * scale_factor)`.                                                |
| **Insolvency**  | If guild treasury can't cover maintenance for 3 consecutive ticks → status = INSOLVENT. Yield reduced 50%.                                                                 |
| **Dissolution** | If INSOLVENT for 10 consecutive ticks → DISSOLVED. Gate holdings sold at market price (or liquidated to treasury at discount). Proceeds distributed to guild shareholders. |

**Guild Share Trading**: Same market system, `asset_type = GUILD_SHARE`. Identical matching.

**API Endpoints**:
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/intents` | `type=CREATE_GUILD`, payload: `{name, public_float_pct, dividend_policy, ...}` |
| `GET` | `/guilds` | List guilds |
| `GET` | `/guilds/{id}` | Guild detail (treasury, members, holdings) |
| `POST` | `/intents` | `type=GUILD_DIVIDEND`, payload: `{guild_id}` (leader only) |
| `POST` | `/intents` | `type=GUILD_INVEST`, payload: `{guild_id, gate_id, quantity, price}` (leader buys gate shares for guild) |

**Acceptance Criteria**:

- Guild creation deducts fee, issues shares
- Public float shares appear on market
- Guild receives yield from its gate holdings
- Dividends distribute guild treasury to shareholders
- Maintenance costs deducted each tick
- Insolvency and dissolution mechanics trigger correctly
- Conservation invariant holds (guild treasuries included in sum)

**Depends on**: Phase 5

---

## PHASE 7: AI Traders

**Goal**: Treasury-backed bot accounts that provide liquidity and apply market pressure.

**Database Tables**:

```
ai_traders
  id              UUID PK
  player_id       UUID FK → players (is_ai = true)
  strategy        ENUM('MARKET_MAKER','VALUE_INVESTOR','NOISE_TRADER')
  parameters      JSONB           -- strategy-specific config
  budget_micro    BIGINT NOT NULL  -- max treasury allocation
  active          BOOLEAN DEFAULT TRUE
```

**Strategies**:

| Strategy           | Behavior                                                                                                                                       |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Market Maker**   | For each active asset: place BUY at `fair_value - spread` and SELL at `fair_value + spread`. Cancel and reprice each tick. Provides liquidity. |
| **Value Investor** | Compute yield-to-price ratio for gates. Buy undervalued (high ratio), sell overvalued (low ratio). Slow, large positions. Hold for N ticks.    |
| **Noise Trader**   | Random small buy/sell orders at ±random% from last price. Creates volume and price noise.                                                      |

**Budget Management**:

- Each AI trader has a budget sourced from treasury.
- On creation: `transfer(TREASURY → AI_player, budget, AI_BUDGET)`
- Periodic rebalance: if AI player balance drifts too far from target, adjust via transfer.
- AI profits/losses flow naturally through the market — no special treatment.

**Integration into Tick Pipeline**:

- After intent collection, before order matching:
  - `AITraderService.generate_intents(tick_rng)` → evaluates each active AI trader → creates intents
  - These intents are added to the current tick's intent batch
  - Processed identically to player intents

**Acceptance Criteria**:

- AI traders place orders every tick
- Orders match against player (and other AI) orders
- Market has visible bid-ask spreads on active assets
- AI traders respect budget limits
- AI accounts flagged `is_ai` (excluded from leaderboards, Phase 10)
- Conservation invariant holds

**Depends on**: Phase 5 (market system)

---

## PHASE 8: Events, News & Real-time

**Goal**: Stochastic events affect the world. News system narrates events. WebSocket delivers updates to players.

**Database Tables**:

```
events
  id              UUID PK
  tick_id         INT FK → ticks
  event_type      VARCHAR NOT NULL
  severity        ENUM('MINOR','MODERATE','MAJOR','CATASTROPHIC')
  target_type     ENUM('GLOBAL','GATE','GUILD','MARKET') NULL
  target_id       UUID NULL
  effects         JSONB
  duration_ticks  INT NULL         -- NULL = permanent
  expires_at_tick INT NULL
  created_at      TIMESTAMPTZ

news_items
  id              UUID PK
  tick_id         INT FK
  headline        TEXT NOT NULL
  body            TEXT
  category        ENUM('EVENT','MARKET','GATE','GUILD','LEADERBOARD')
  importance      ENUM('LOW','MEDIUM','HIGH','BREAKING')
  related_type    VARCHAR NULL
  related_id      UUID NULL
  created_at      TIMESTAMPTZ
```

**Event Types**:

| Event                  | Severity     | Target         | Effect                       |
| ---------------------- | ------------ | -------------- | ---------------------------- |
| `MANA_SURGE`           | MINOR        | Single gate    | +stability                   |
| `INSTABILITY_WAVE`     | MODERATE     | Multiple gates | −stability                   |
| `ECONOMIC_BOOM`        | MAJOR        | Global         | All yields ×1.5 for N ticks  |
| `REGULATION_CRACKDOWN` | MODERATE     | Global         | Fees ×2 for N ticks          |
| `GATE_RESONANCE`       | MAJOR        | Global         | Bonus high-rank gate spawn   |
| `MARKET_PANIC`         | MAJOR        | Market         | AI traders sell aggressively |
| `TREASURE_DISCOVERY`   | MINOR        | Single gate    | One-time bonus yield payout  |
| `MANA_DROUGHT`         | CATASTROPHIC | Global         | All yields ×0.5 for N ticks  |

**Event Processing (tick pipeline)**:

1. Roll `rng.random()` against `event_probability` (e.g., 0.05 per tick = ~1 event/minute average)
2. If triggered: select type via weighted draw, determine target randomly (wealth-agnostic)
3. Apply effects: modify gate/market parameters, insert modifiers
4. Temporary effects tracked by `expires_at_tick`, reverted when tick reaches expiry

**News Generation**:

- Template-based: each event type has headline/body templates with variable interpolation
- Auto-generated for: events, gate collapses, large trades (>threshold), leaderboard changes
- Stored in `news_items` table

**WebSocket** (`api/ws.py`):

- Endpoint: `WS /ws/feed?token=<jwt>`
- On connect: authenticate JWT, add to connection pool
- Simulation tick completion → publish to Redis channel `sim:tick_results`
- WebSocket handler subscribes to Redis, fans out to connected clients:
  - `tick_summary` — tick number, timestamp
  - `news` — new news items
  - `prices` — updated market prices
  - `portfolio` — per-player balance/holding changes (filtered per connection)
- Client receives JSON messages with `type` field for routing

**API Endpoints**:
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/news` | Paginated news feed |
| `GET` | `/events` | Recent events (with filters) |
| `WS` | `/ws/feed` | Real-time feed |

**Acceptance Criteria**:

- Events trigger stochastically (run 200 ticks, at least some events fire)
- Event effects visible in state (e.g., stability changed)
- Temporary effects revert after expiry
- News generated for events and major trades
- WebSocket delivers messages within 1s of tick completion
- Events don't target players by wealth

**Depends on**: Phase 4 (gates to affect), Phase 5 (market prices), Phase 3 (tick pipeline)

---

## PHASE 9: Anti-Exploit & Economic Balance

**Goal**: Implement economic friction that prevents permanent dominance and infinite-value strategies.

**Mechanisms** (added to tick pipeline as "maintenance phase"):

| Mechanism                           | Rule                                                                                                           | Sink destination                    |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| **Ownership Concentration Penalty** | Yield reduced for shares exceeding ownership thresholds: >25% = full yield, >50% = 80%, >75% = 60%, >90% = 30% | Uncollected yield stays in treasury |
| **Liquidity Decay**                 | Shares held without any trade for >N ticks: small per-tick cost per share debited from player                  | Player → Treasury                   |
| **Float Control Cap**               | Max single-player ownership per asset: 80%. Orders exceeding cap rejected at matching time.                    | N/A (prevention)                    |
| **Portfolio Maintenance**           | Net worth > threshold: `cost = base * ((net_worth - threshold) / threshold)^1.5` per tick                      | Player → Treasury                   |
| **Progressive Fees**                | Already implemented in Phase 5 — tuning pass here                                                              | Player → Treasury                   |

**Implementation Notes**:

- Concentration penalty: modify yield distribution logic (Phase 4) — don't pay full yield to concentrated holders.
- Liquidity decay: track `last_trade_tick` per holding. If `current_tick - last_trade_tick > decay_threshold`, charge decay cost.
- Portfolio maintenance: compute net worth each tick (or every N ticks), charge if over threshold. Uses market prices from Phase 5.
- All costs go through `TransferService` with proper `entry_type` and ledger entries.
- If player can't afford maintenance/decay cost, deduct what's available (drain to zero, never negative).

**New field**:

```
gate_shares → add: last_trade_tick INT  (updated on any buy/sell involving this holding)
```

**Acceptance Criteria**:

- Concentrated holder receives less yield than distributed holder (same total shares)
- Shares untouched for many ticks incur costs
- Order exceeding 80% ownership cap is rejected
- High-net-worth player pays measurable maintenance
- A simulated "whale buys everything" scenario shows diminishing returns
- Conservation invariant holds after all penalties

**Depends on**: Phase 5 (market data), Phase 4 (yield distribution)

---

## PHASE 10: Leaderboards & Seasons

**Goal**: Track and rank players by net worth with seasonal resets and activity-based decay.

**Database Tables**:

```
seasons
  id              SERIAL PK
  name            VARCHAR NOT NULL
  started_at_tick INT NOT NULL
  ends_at_tick    INT NULL
  status          ENUM('ACTIVE','COMPLETED')

leaderboard_entries
  season_id       INT FK
  player_id       UUID FK
  net_worth_micro BIGINT
  score           BIGINT           -- decayed score
  rank            INT
  last_active_tick INT
  updated_at_tick INT
  PRIMARY KEY (season_id, player_id)

season_results
  season_id       INT FK
  player_id       UUID FK
  final_rank      INT
  final_score     BIGINT
  PRIMARY KEY (season_id, player_id)
```

**Net Worth Calculation**:

```
net_worth = player.balance_micro
          + SUM(gate_shares.quantity * market_prices.last_price for each gate holding)
          + SUM(guild_shares.quantity * market_prices.last_price for each guild holding)
```

Computed every 12 ticks (~1 minute).

**Score Decay**:

```
if (current_tick - last_active_tick) > inactivity_threshold:
    score *= decay_factor  (e.g., 0.995 per tick beyond threshold)
```

`last_active_tick` updated whenever player submits any intent.

**Season Lifecycle**:

- Admin creates season with duration or end tick
- During season: leaderboard updated continuously
- Season end: copy `leaderboard_entries` → `season_results`, set status COMPLETED
- New season: fresh `leaderboard_entries`, all scores start from current net worth
- **Economy persists** — only rankings reset

**Excluded**: AI trader accounts (`is_ai = true`) never appear on leaderboard.

**Rewards**: Cosmetic/title only (no currency). Prevents faucet. Titles stored as player metadata.

**API Endpoints**:
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/leaderboard` | Current season top N |
| `GET` | `/leaderboard/me` | My rank and score |
| `GET` | `/seasons` | List seasons |
| `GET` | `/seasons/{id}/results` | Final results |

**Acceptance Criteria**:

- Leaderboard reflects net worth accurately
- Inactive players decay in ranking
- AI players excluded
- Season end snapshots correctly
- No currency faucet from leaderboard
- Economy state unchanged by season transitions

**Depends on**: Phase 5 (market prices for net worth)

---

## PHASE 11: Admin & Observability

**Goal**: Admin API for tuning and intervention. Prometheus/Grafana for monitoring. Load test harness.

**Database Tables**:

```
simulation_parameters
  key             VARCHAR PK
  value           VARCHAR NOT NULL
  value_type      ENUM('INT','FLOAT','BOOL','STRING')
  description     TEXT
  updated_at      TIMESTAMPTZ
  updated_by      UUID NULL FK → players
```

Seeded with all tunable parameters (fee rates, spawn rates, yield multipliers, decay rates, thresholds, etc.). Simulation reads these at tick start (cached in Redis, invalidated on update).

**Admin API** (protected by `role = ADMIN` on player):
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/admin/simulation/pause` | Pause tick loop |
| `POST` | `/admin/simulation/resume` | Resume tick loop |
| `GET` | `/admin/parameters` | List all parameters |
| `PATCH` | `/admin/parameters/{key}` | Update parameter |
| `POST` | `/admin/events/trigger` | Manually trigger event |
| `GET` | `/admin/treasury` | Treasury balance + recent flows |
| `GET` | `/admin/audit/conservation` | Run conservation check, return result |
| `GET` | `/admin/ledger` | Query ledger (filters: type, player, tick range) |
| `POST` | `/admin/seasons` | Create/end season |

**Prometheus Metrics** (exposed at `/metrics`):

| Metric                       | Type      |
| ---------------------------- | --------- |
| `dge_tick_duration_seconds`  | histogram |
| `dge_tick_number`            | gauge     |
| `dge_intent_queue_depth`     | gauge     |
| `dge_active_players_total`   | gauge     |
| `dge_treasury_balance_micro` | gauge     |
| `dge_trade_volume_micro`     | counter   |
| `dge_active_gates_total`     | gauge     |
| `dge_ws_connections`         | gauge     |
| `dge_order_book_depth`       | gauge     |
| `dge_events_fired_total`     | counter   |

**Grafana**: Dashboard JSON provisioned via Docker volume mount.

**k6 Test Scripts**:
| Script | Scenario |
|---|---|
| `auth_load.js` | 1,000 concurrent registrations + logins |
| `order_storm.js` | 500 concurrent users placing orders every tick |
| `ws_connections.js` | 1,000 WebSocket connections, measure delivery latency |
| `mixed_workload.js` | Realistic mix: 60% read, 30% orders, 10% discovery |

**Acceptance Criteria**:

- Admin can pause/resume simulation via API
- Parameter changes reflected within 1 tick
- Conservation audit endpoint returns PASS/FAIL
- Prometheus endpoint returns all metrics
- Grafana dashboard renders
- k6 runs at 1,000 concurrent, p99 < 500ms for API, p99 < 1s for WS delivery

**Depends on**: All previous phases

---

## PHASE 12: Frontend

**Goal**: Functional React UI covering all player-facing features.

**Pages**:

| Page                 | Features                                                                                             |
| -------------------- | ---------------------------------------------------------------------------------------------------- |
| **Login / Register** | Forms, error handling, redirect                                                                      |
| **Dashboard**        | Balance, portfolio summary (gate shares, guild shares, values), recent ledger entries, active orders |
| **Gate Browser**     | Filterable/sortable list, rank badges, stability bars, yield indicators                              |
| **Gate Detail**      | Stats, stability chart (historical), shareholder breakdown, order book, trade history, buy/sell form |
| **Market Overview**  | All tradeable assets, prices, volume, movers                                                         |
| **Guild Browser**    | List guilds, key stats                                                                               |
| **Guild Detail**     | Treasury, members, holdings, dividend history, manage (if leader), buy/sell guild shares             |
| **Create Guild**     | Form with float/dividend config                                                                      |
| **Discovery**        | Spend currency to discover gate, rank selection, cost display                                        |
| **News Feed**        | Real-time scrolling feed, filterable by category                                                     |
| **Leaderboard**      | Season rankings table, my rank highlighted                                                           |

**Technical Decisions**:
| Concern | Approach |
|---|---|
| API client | `axios` with JWT interceptor (auto-refresh on 401) |
| Server state | React Query (`@tanstack/react-query`) |
| Local state | Zustand (minimal: auth token, WS connection status) |
| WebSocket | Custom hook with auto-reconnect, message type routing |
| Charts | Recharts (lightweight, sufficient for stability/price history) |
| Styling | TailwindCSS, dark theme default |

**Acceptance Criteria**:

- All player actions achievable through UI
- UI submits intents only (never decides outcomes)
- Real-time updates appear within 1s
- Responsive on desktop (1024px+) and tablet (768px+)
- Error states shown clearly (insufficient balance, order rejected, etc.)
- No exposed secrets in frontend bundle

**Depends on**: All API endpoints (Phases 2–11)

---

## PHASE 13: Hardening & Launch Prep

**Goal**: Prove correctness, security, and performance. Produce documentation.

**Deliverables**:

| Category                   | Item                                                                                                                                                                                                                       |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Replay Test**            | Run 500 ticks with fixed seed + scripted intents. Record all state hashes. Re-run → assert identical hashes.                                                                                                               |
| **Conservation Soak Test** | Run 5,000 ticks with AI traders + simulated players submitting random intents. Assert conservation invariant after every tick.                                                                                             |
| **Fuzz Test**              | Random intent payloads at high volume. Assert no unhandled exceptions, no invariant violations.                                                                                                                            |
| **Edge Case Tests**        | Treasury near-zero: yields degrade gracefully. All gates collapsed: system spawns new ones. 100% ownership: anti-exploit caps engage. No buy orders: sell orders sit, no crash. Concurrent cancel + fill: no double-spend. |
| **Security Audit**         | Rate limiting (FastAPI middleware). Input validation (Pydantic strict mode). SQL injection (parameterized only via ORM). JWT expiry + refresh flow. CORS lockdown. Helmet-equivalent headers.                              |
| **Load Test**              | k6: 1,000 concurrent at sustained load for 30 minutes. Pass criteria: p99 API < 500ms, p99 WS < 1s, zero conservation violations, zero 500 errors.                                                                         |
| **Documentation**          | Auto-generated OpenAPI docs. `architecture.md`: system overview, data flow, invariants. `runbook.md`: deploy, monitor, incident response, parameter tuning guide.                                                          |

**Acceptance Criteria**:

- Replay is bit-for-bit identical
- Conservation holds over 5,000 ticks under load
- No crashes or invariant violations from fuzz
- All edge cases have defined safe behavior
- Load test passes at 1,000 concurrent
- Documentation complete and reviewed

**Depends on**: Everything

---

## Phase Dependency Graph

```
P1 ──→ P2 ──→ P3 ──→ P4 ──→ P5 ──→ P6
                                │      │
                                ↓      ↓
                               P7     P8
                                │      │
                                └──┬───┘
                                   ↓
                                  P9
                                   ↓
                                  P10
                                   ↓
                                  P11
                                   ↓
                                  P12
                                   ↓
                                  P13
```

P7 and P8 can run in parallel after P5. P6 can overlap with P7/P8 since guild shares use the same market system from P5.
