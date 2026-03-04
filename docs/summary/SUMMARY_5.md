# Phase 5 — Complete ✓

## Summary of What We Built

### Database Tables

| Table             | Purpose                        | Key Constraints                                                 |
| ----------------- | ------------------------------ | --------------------------------------------------------------- |
| **orders**        | Buy/sell orders for assets     | UUID PK, quantity > 0, price > 0, filled ≥ 0, escrow ≥ 0        |
| **trades**        | Executed trade records         | UUID PK, links buy + sell orders, records price/quantity/fees   |
| **market_prices** | Current market state per asset | Composite PK (asset_type, asset_id), tracks last/bid/ask/volume |

### Enums Created

| Enum          | Values                                   |
| ------------- | ---------------------------------------- |
| `AssetType`   | `GATE_SHARE`, `GUILD_SHARE`              |
| `OrderSide`   | `BUY`, `SELL`                            |
| `OrderStatus` | `OPEN`, `PARTIAL`, `FILLED`, `CANCELLED` |

### Enums Extended

| Enum        | New Values                      |
| ----------- | ------------------------------- |
| `EntryType` | `ESCROW_LOCK`, `ESCROW_RELEASE` |

### Services

| Service            | Method / Function                | Purpose                                                                                |
| ------------------ | -------------------------------- | -------------------------------------------------------------------------------------- |
| **fee_calculator** | `calculate_fee()`                | Progressive fee: `rate = base + (value/scale) * progressive`, capped at max (10%)      |
| **fee_calculator** | `calculate_max_fee()`            | Max possible fee for a trade value — used for escrow                                   |
| **fee_calculator** | `calculate_escrow()`             | Total escrow = max_cost + max_fee, returns tuple                                       |
| **order_matching** | `calculate_iso_price()`          | ISO price per share = avg_yield × payback_ticks / total_shares                         |
| **order_matching** | `create_iso_orders()`            | System SELL orders for OFFERING gates that lack one                                    |
| **order_matching** | `finalize_iso_transitions()`     | OFFERING → ACTIVE when treasury holds 0 shares                                         |
| **order_matching** | `cancel_collapsed_gate_orders()` | Cancel all open orders for COLLAPSED gates, release BUY escrow                         |
| **order_matching** | `process_place_order()`          | Validate + create order from PLACE_ORDER intent (escrow for BUY, share check for SELL) |
| **order_matching** | `process_cancel_order()`         | Cancel order from CANCEL_ORDER intent, release escrow if BUY                           |
| **order_matching** | `match_orders()`                 | Price-time priority matching across all assets with open orders                        |
| **order_matching** | `_execute_trade()`               | Atomic: currency settlement + share transfer + fee collection + trade record           |
| **order_matching** | `update_market_prices()`         | Refresh last_price, best_bid, best_ask, volume for traded/ordered assets               |

### Tick Pipeline — Updated

| Step | Action                                   | Status                           |
| ---- | ---------------------------------------- | -------------------------------- |
| 1    | Determine tick_number                    | ✅ Active (Phase 3)              |
| 2    | Derive seed + create RNG                 | ✅ Active (Phase 3)              |
| 3    | Insert tick record                       | ✅ Active (Phase 3)              |
| 4    | Load treasury_id                         | ✅ Active (Phase 4)              |
| 5    | Collect QUEUED intents                   | ✅ Active (Phase 3)              |
| 6    | Process intents by type                  | ✅ DISCOVER_GATE (P4)            |
|      |                                          | ✅ **PLACE_ORDER (P5)**          |
|      |                                          | ✅ **CANCEL_ORDER (P5)**         |
| 7    | System gate spawn + lifecycle + yield    | ✅ Active (Phase 4)              |
| 8    | **Create ISO orders for OFFERING gates** | ✅ **NEW (Phase 5)**             |
| 9    | **Cancel orders for COLLAPSED gates**    | ✅ **NEW (Phase 5)**             |
| 10   | **Match orders**                         | ✅ **NEW (Phase 5)**             |
| 11   | **Finalize ISO transitions**             | ✅ **NEW (Phase 5)**             |
| 12   | **Update market prices**                 | ✅ **NEW (Phase 5)**             |
| 13   | Roll events                              | ⬜ No-op (Phase 8+)              |
| 14   | Anti-exploit maintenance                 | ⬜ No-op (Phase 9+)              |
| 15   | Mark PROCESSING intents → EXECUTED       | ✅ Active (Phase 3)              |
| 16   | Compute state_hash                       | ✅ **Extended with market data** |
| 17   | Finalize tick record                     | ✅ Active (Phase 3)              |

### Config Additions

| Parameter              | Default        | Purpose                                           |
| ---------------------- | -------------- | ------------------------------------------------- |
| `base_fee_rate`        | `0.005` (0.5%) | Minimum fee rate for any trade                    |
| `progressive_fee_rate` | `0.5`          | How fast fees scale with order value              |
| `fee_scale_micro`      | `10_000_000`   | Denominator for progressive scaling (10 currency) |
| `max_fee_rate`         | `0.10` (10%)   | Hard cap on fee rate                              |
| `iso_payback_ticks`    | `100`          | Used to calculate ISO price per share             |

### Fee Progression Examples

| Trade Value (micro) | Trade Value (currency) | Fee Rate  | Fee (micro) |
| ------------------- | ---------------------- | --------- | ----------- |
| 100,000             | 0.1                    | 1.0%      | 1,000       |
| 1,000,000           | 1.0                    | 5.5%      | 55,000      |
| 5,000,000           | 5.0                    | 10% (cap) | 500,000     |
| 10,000,000          | 10.0                   | 10% (cap) | 1,000,000   |

### ISO Prices Per Rank

| Rank   | Avg Yield | Shares | ISO Price/Share |
| ------ | --------- | ------ | --------------- |
| E      | 3,000     | 100    | 1,500           |
| D      | 6,500     | 80     | 4,062           |
| C      | 16,500    | 60     | 13,750          |
| B      | 40,000    | 50     | 40,000          |
| A      | 100,000   | 40     | 125,000         |
| S      | 260,000   | 30     | 433,333         |
| S_PLUS | 650,000   | 20     | 1,625,000       |

### API Endpoints (Cumulative)

| Method | Path                                     | Auth | Phase | Purpose                                |
| ------ | ---------------------------------------- | ---- | ----- | -------------------------------------- |
| `GET`  | `/health`                                | No   | 1     | Health check                           |
| `GET`  | `/ready`                                 | No   | 1     | DB + Redis connectivity                |
| `POST` | `/auth/register`                         | No   | 2     | Create account, grant starting balance |
| `POST` | `/auth/login`                            | No   | 2     | Returns access + refresh tokens        |
| `POST` | `/auth/refresh`                          | No   | 2     | New access token from refresh token    |
| `GET`  | `/players/me`                            | Yes  | 2     | Profile + balance                      |
| `GET`  | `/players/me/ledger`                     | Yes  | 2     | Paginated personal ledger              |
| `POST` | `/intents`                               | Yes  | 3     | Submit intent                          |
| `GET`  | `/simulation/status`                     | No   | 3     | Current tick, running state            |
| `GET`  | `/gates`                                 | No   | 4     | List gates (filter/page)               |
| `GET`  | `/gates/{id}`                            | No   | 4     | Gate detail + shareholders             |
| `GET`  | `/gates/rank-profiles`                   | No   | 4     | Rank reference data                    |
| `GET`  | `/orders/me`                             | Yes  | **5** | My open/recent orders (paginated)      |
| `GET`  | `/market/{asset_type}/{asset_id}`        | No   | **5** | Price, bid/ask, volume                 |
| `GET`  | `/market/{asset_type}/{asset_id}/book`   | No   | **5** | Aggregated order book                  |
| `GET`  | `/market/{asset_type}/{asset_id}/trades` | No   | **5** | Recent trades (paginated)              |

### State Hash — Extended

Now covers:

- Treasury balance
- Individual player balances (ordered by ID)
- Gate counts per status
- Sum of all gate stabilities (truncated to int)
- Total shares held across all gates
- **Open order count**
- **Total escrow locked in open BUY orders**
- **Total trade count**

### Testing

| Test File                | Tests  | Covers                                                                               |
| ------------------------ | ------ | ------------------------------------------------------------------------------------ |
| `test_health.py`         | 2      | Health + ready endpoints                                                             |
| `test_transfer.py`       | 4      | Successful transfer, insufficient balance, zero/negative amount                      |
| `test_auth.py`           | 12     | Register, login, refresh, token validation, protected routes                         |
| `test_conservation.py`   | 1      | Treasury + players = INITIAL_SEED after registrations                                |
| `test_rng.py`            | 8      | Deterministic seeding, sequence reproducibility                                      |
| `test_lock.py`           | 5      | Acquire, double acquire, release + reacquire, wrong-worker release                   |
| `test_tick.py`           | 4      | Single tick, sequential numbering, intent collection, state hash consistency         |
| `test_replay.py`         | 2      | 5-tick replay identical, different seed → different results                          |
| `test_intents_api.py`    | 5      | Submit → QUEUED, all types, no auth, invalid type, missing payload                   |
| `test_gates.py`          | 12     | System spawn, player discovery, lifecycle, yield, conservation                       |
| `test_gates_api.py`      | 7      | List gates, filters, detail + shareholders, rank profiles, 404                       |
| `test_fee_calculator.py` | 6      | Small/medium/large fees, cap, zero, escrow calculation                               |
| `test_market.py`         | 15     | Order placement, cancellation, matching, partial fills, ISO, collapsed, conservation |
| `test_market_api.py`     | 7      | /orders/me, /market price, book, trades, 422 validation                              |
| **Total**                | **90** | **(90 passed)**                                                                      |

### Escrow Model

| Step             | Direction                                               | Entry Type         |
| ---------------- | ------------------------------------------------------- | ------------------ |
| Place BUY order  | Player → Treasury (lock)                                | `ESCROW_LOCK`      |
| Trade fills      | Escrow consumed in treasury — seller paid from treasury | `TRADE_SETTLEMENT` |
| Buyer fee        | Consumed from escrow (stays in treasury, no transfer)   | —                  |
| Seller fee       | Seller → Treasury                                       | `TRADE_FEE`        |
| Full fill excess | Treasury → Player                                       | `ESCROW_RELEASE`   |
| Cancel BUY order | Treasury → Player                                       | `ESCROW_RELEASE`   |
| ISO trade        | No settlement (treasury is seller — escrow IS payment)  | —                  |

### Key Design Decisions

| Decision                                    | Rationale                                                                                            |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Treasury as escrow holder                   | Conservation invariant holds naturally. Escrow is `transfer(PLAYER → TREASURY)`. Clean ledger trail. |
| Skip self-transfers for ISO                 | Seller = treasury, escrow already in treasury. No-op settlement avoids deadlock.                     |
| `is_system` flag on orders                  | Clean ISO detection. Skip seller fee, skip self-transfer.                                            |
| `orders.player_id` plain UUID (no FK)       | Same convention as `gate_shares`. Treasury can be a seller.                                          |
| Price-time priority matching                | Standard, fair, deterministic. Seller's limit price used (maker gets their price).                   |
| Fee calculated per-trade (not per-order)    | Partial fills at different prices get accurate fees. Conservative for escrow.                        |
| Escrow uses max possible fee                | Ensures buyer always has enough. Excess released on fill/cancel.                                     |
| Available shares = owned − open sell orders | No schema change. Calculated within tick transaction (safe from races).                              |
| ISO orders created after gate lifecycle     | New gates get ISO orders in same tick they spawn.                                                    |
| Collapsed gate orders auto-cancelled        | Prevents stale orders, releases locked escrow promptly.                                              |
| Market prices updated after matching        | Reflects current state. UPSERT pattern handles first-trade and updates.                              |
| No seller fee on ISO                        | System selling to bootstrap — fee would be treasury → treasury.                                      |

### Issues Encountered & Resolved

| Issue                                        | Cause                                                                        | Fix                                                                |
| -------------------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `test_intents_collected_and_executed` failed | PLACE_ORDER no longer a no-op after wiring — incomplete payload got REJECTED | Changed test to use GUILD_INVEST (still no-op until Phase 6)       |
| Enum migration not auto-generated            | Alembic autogenerate doesn't handle `ALTER TYPE ... ADD VALUE` for PG enums  | Manual `ALTER TYPE entrytype ADD VALUE IF NOT EXISTS` in migration |

### Files Created or Modified (Phase 5)

```
backend/app/
├── config.py ← MODIFIED: +5 market fee params
├── main.py ← MODIFIED: +market_router +orders_router
├── models/
│ ├── init.py ← MODIFIED: registered Order, Trade, MarketPrice
│ ├── ledger.py ← MODIFIED: +ESCROW_LOCK, +ESCROW_RELEASE
│ └── market.py ← NEW: 3 enums + 3 models
├── schemas/
│ └── market.py ← NEW: 7 response schemas
├── api/
│ ├── market.py ← NEW: /market endpoints (price, book, trades)
│ └── orders.py ← NEW: /orders/me endpoint
├── services/
│ ├── fee_calculator.py ← NEW: pure fee + escrow functions
│ └── order_matching.py ← NEW: ISO, placement, cancellation, matching, prices
├── simulation/
│ ├── tick.py ← MODIFIED: wired 6 market steps + 2 intent types
│ └── state_hash.py ← MODIFIED: +open_orders, +total_escrow, +total_trades

backend/tests/
├── conftest.py ← MODIFIED: +market cleanup, +funded_player_id fixture
├── test_tick.py ← MODIFIED: changed no-op intent type
├── test_fee_calculator.py ← NEW: 6 tests
├── test_market.py ← NEW: 15 tests
└── test_market_api.py ← NEW: 7 tests

backend/alembic/versions/
└── 7030291f0b68_add_orders_...py ← NEW: migration (manually edited for enum values)
```

### Economic Impact — Full Market Flows Active

| Flow        | Mechanism        | Direction                                | Entry Type         |
| ----------- | ---------------- | ---------------------------------------- | ------------------ |
| **Lock**    | Buy escrow       | Player → Treasury                        | `ESCROW_LOCK`      |
| **Unlock**  | Escrow release   | Treasury → Player                        | `ESCROW_RELEASE`   |
| **Neutral** | Trade settlement | Treasury → Seller                        | `TRADE_SETTLEMENT` |
| **Sink**    | Buyer fee        | Consumed from escrow (stays in treasury) | —                  |
| **Sink**    | Seller fee       | Seller → Treasury                        | `TRADE_FEE`        |
| **Sink**    | ISO proceeds     | Buyer escrow stays in treasury           | —                  |

### Economic Invariant Status

```
✅ treasury_balance + SUM(player_balances) = INITIAL_SEED
Verified by test_conservation_after_trading with multi-tick trading scenario.
Escrow does not break invariant — money moves within same sum.
No guild treasuries yet (Phase 6).
```

### Architecture Checkpoint

```
Phase 1 ✅ — Foundation & Infrastructure
Phase 2 ✅ — Identity, Wallet & Ledger
Phase 3 ✅ — Simulation Engine Core
Phase 4 ✅ — Dungeon Gates
Phase 5 ✅ — Market System
Phase 6 ⬜ — Guilds ← NEXT
```

---

**Phase 5 acceptance criteria — all met:**

- ✅ ISO sells shares, proceeds to treasury
- ✅ Buy/sell orders match correctly (price-time priority)
- ✅ Trades execute atomically (currency + shares + fees + ledger)
- ✅ Escrow prevents over-commitment
- ✅ Cancel returns escrowed funds
- ✅ Progressive fees increase with order size
- ✅ Cannot buy shares of a COLLAPSED gate (orders cancelled)
- ✅ Cannot sell shares you don't own (rejected at placement)
- ✅ Double-sell over-commitment rejected
- ✅ Conservation invariant holds after multi-tick trading
- ✅ 90 tests passing, 0 failures
