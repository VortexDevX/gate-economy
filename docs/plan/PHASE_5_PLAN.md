# Phase 5 Sub-Plan: Market System

## Goal

Order book for gate shares (guild shares in Phase 6). Orders matched each tick via price-time priority. Progressive fees as a wealth sink. Escrow model prevents over-commitment. Initial Share Offering (ISO) sells treasury-held gate shares during OFFERING period. All trade execution is atomic — currency, shares, fees, and ledger entries in a single transaction.

---

## Economic Flows Introduced

| Flow        | Mechanism        | Direction         | Entry Type            |
| ----------- | ---------------- | ----------------- | --------------------- |
| **Neutral** | Trade settlement | Player ↔ Player   | `TRADE_SETTLEMENT`    |
| **Sink**    | Trade fees       | Player → Treasury | `TRADE_FEE`           |
| **Lock**    | Buy escrow       | Player → Treasury | `ESCROW_LOCK`         |
| **Unlock**  | Escrow release   | Treasury → Player | `ESCROW_RELEASE`      |
| **Sink**    | ISO proceeds     | Player → Treasury | `ESCROW_LOCK` (stays) |

---

## Step 1 — Models

### New Enums

| Enum          | Values                                   |
| ------------- | ---------------------------------------- |
| `AssetType`   | `GATE_SHARE`, `GUILD_SHARE`              |
| `OrderSide`   | `BUY`, `SELL`                            |
| `OrderStatus` | `OPEN`, `PARTIAL`, `FILLED`, `CANCELLED` |

### Update Existing Enum

Add to `EntryType`: `ESCROW_LOCK`, `ESCROW_RELEASE`

### New Tables

```
orders
  id                UUID PK DEFAULT uuid4
  player_id         UUID NOT NULL          -- plain UUID, no FK (can be treasury for ISO)
  asset_type        AssetType NOT NULL
  asset_id          UUID NOT NULL
  side              OrderSide NOT NULL
  quantity          INT NOT NULL CHECK (> 0)
  price_limit_micro BIGINT NOT NULL CHECK (> 0)
  filled_quantity   INT NOT NULL DEFAULT 0
  escrow_micro      BIGINT NOT NULL DEFAULT 0   -- remaining escrow (BUY only)
  status            OrderStatus NOT NULL DEFAULT 'OPEN'
  created_at_tick   INT NOT NULL
  updated_at_tick   INT NULL
  is_system         BOOLEAN NOT NULL DEFAULT FALSE  -- TRUE for ISO orders

trades
  id                UUID PK DEFAULT uuid4
  buy_order_id      UUID FK → orders NOT NULL
  sell_order_id     UUID FK → orders NOT NULL
  asset_type        AssetType NOT NULL
  asset_id          UUID NOT NULL
  quantity          INT NOT NULL
  price_micro       BIGINT NOT NULL
  buyer_fee_micro   BIGINT NOT NULL
  seller_fee_micro  BIGINT NOT NULL
  tick_id           INT FK → ticks NOT NULL
  created_at        TIMESTAMPTZ DEFAULT now()

market_prices
  asset_type        AssetType NOT NULL
  asset_id          UUID NOT NULL
  last_price_micro  BIGINT NULL
  best_bid_micro    BIGINT NULL
  best_ask_micro    BIGINT NULL
  volume_24h_micro  BIGINT NOT NULL DEFAULT 0
  updated_at_tick   INT NOT NULL
  PRIMARY KEY (asset_type, asset_id)
```

### Model Notes

- `orders.player_id` is a **plain UUID** (no FK to players). Can hold a `players.id` or `system_accounts.id` (treasury for ISO orders). Same convention as `gate_shares`.
- `orders.is_system` flag distinguishes ISO/system orders from player orders (used to skip seller fees, skip self-transfers).
- `orders.escrow_micro` tracks the **remaining** escrow locked for BUY orders. Decremented on each fill, released on cancel/complete.
- `filled_quantity` tracks cumulative fills. `remaining = quantity - filled_quantity`.

### Files

| File                 | Contents                                                                              |
| -------------------- | ------------------------------------------------------------------------------------- |
| `models/market.py`   | `AssetType`, `OrderSide`, `OrderStatus` enums, `Order`, `Trade`, `MarketPrice` models |
| `models/__init__.py` | Register `Order`, `Trade`, `MarketPrice`                                              |
| `models/ledger.py`   | Add `ESCROW_LOCK`, `ESCROW_RELEASE` to `EntryType`                                    |

---

## Step 2 — Migration + Config

### Migration

```bash
make migration msg="add orders trades market_prices and escrow entry types"
make migrate
```

Migration must:

1. Create `orders`, `trades`, `market_prices` tables
2. Add `ESCROW_LOCK` and `ESCROW_RELEASE` values to `entrytype` PostgreSQL enum:
   ```sql
   ALTER TYPE entrytype ADD VALUE 'ESCROW_LOCK';
   ALTER TYPE entrytype ADD VALUE 'ESCROW_RELEASE';
   ```

### Config Additions (`config.py`)

| Parameter              | Default        | Purpose                                           |
| ---------------------- | -------------- | ------------------------------------------------- |
| `base_fee_rate`        | `0.005` (0.5%) | Minimum fee rate for any trade                    |
| `progressive_fee_rate` | `0.5`          | How fast fees scale with order value              |
| `fee_scale_micro`      | `10_000_000`   | Denominator for progressive scaling (10 currency) |
| `max_fee_rate`         | `0.10` (10%)   | Hard cap on fee rate                              |
| `iso_payback_ticks`    | `100`          | Used to calculate ISO price per share             |

### Fee Progression Examples

Using the formula: `fee_rate = base + (value / scale) * progressive_rate`, capped at `max_rate`:

| Trade Value (micro) | Trade Value (currency) | Fee Rate  | Fee (micro) |
| ------------------- | ---------------------- | --------- | ----------- |
| 100,000             | 0.1                    | 1.0%      | 1,000       |
| 1,000,000           | 1.0                    | 5.5%      | 55,000      |
| 5,000,000           | 5.0                    | 10% (cap) | 500,000     |
| 10,000,000          | 10.0                   | 10% (cap) | 1,000,000   |

---

## Step 3 — Fee Calculator (`services/fee_calculator.py`)

Standalone module, no DB dependencies. Pure functions.

```python
def calculate_fee(trade_value_micro: int) -> int:
    """Progressive fee for a given trade value. Returns fee in micro-units."""
    fee_rate = BASE_FEE_RATE + (trade_value_micro / FEE_SCALE) * PROGRESSIVE_RATE
    fee_rate = min(fee_rate, MAX_FEE_RATE)
    return int(trade_value_micro * fee_rate)

def calculate_max_fee(max_trade_value_micro: int) -> int:
    """Maximum possible fee — used for escrow calculation."""
    return calculate_fee(max_trade_value_micro)

def calculate_escrow(quantity: int, price_limit_micro: int) -> tuple[int, int]:
    """Calculate total escrow needed for a BUY order.
    Returns (total_escrow, max_fee)."""
    max_cost = quantity * price_limit_micro
    max_fee = calculate_max_fee(max_cost)
    return max_cost + max_fee, max_fee
```

---

## Step 4 — Order Matching Service (`services/order_matching.py`)

The core market engine. All functions operate within the tick's DB transaction.

### ISO Price Calculation

```python
def calculate_iso_price(profile: GateRankProfile) -> int:
    """Derive ISO price per share from rank profile."""
    avg_yield = (profile.yield_min_micro + profile.yield_max_micro) // 2
    return avg_yield * ISO_PAYBACK_TICKS // (2 * profile.total_shares)
    # Correction: should be total gate yield / total shares * payback
    # iso_price = avg_yield * ISO_PAYBACK_TICKS // profile.total_shares
```

Wait — `avg_yield` is the total gate yield per tick. Per-share yield = `avg_yield / total_shares`. ISO price per share = per-share yield \* payback ticks.

```python
iso_price_per_share = (yield_min + yield_max) * iso_payback_ticks // (2 * total_shares)
```

| Rank   | Avg Yield | Shares | ISO Price/Share |
| ------ | --------- | ------ | --------------- |
| E      | 3,000     | 100    | 1,500           |
| D      | 6,500     | 80     | 4,062           |
| C      | 16,500    | 60     | 13,750          |
| B      | 40,000    | 50     | 40,000          |
| A      | 100,000   | 40     | 125,000         |
| S      | 260,000   | 30     | 433,333         |
| S_PLUS | 650,000   | 20     | 1,625,000       |

### Functions

**`create_iso_orders(session, tick_number, treasury_id)`**

- For each OFFERING gate that has NO open system SELL order:
  - Calculate ISO price from rank profile
  - Get treasury's share quantity for this gate
  - If quantity > 0: create Order (is_system=True, player_id=treasury_id, side=SELL, price_limit=iso_price, quantity=shares)
  - Create/update MarketPrice entry with best_ask = iso_price

**`cancel_collapsed_gate_orders(session, tick_number, treasury_id)`**

- For each COLLAPSED gate:
  - Find all OPEN/PARTIAL orders for that gate
  - Cancel each:
    - If BUY: release escrow via `transfer(TREASURY → BUYER, escrow_micro, ESCROW_RELEASE)`
    - Set status = CANCELLED, updated_at_tick = tick_number

**`process_place_order(session, intent, tick_number, tick_id, treasury_id)`**

- Parse payload: `{asset_type, asset_id, side, quantity, price_limit_micro}`
- Validate:
  - Asset exists and is not COLLAPSED
  - quantity > 0, price_limit_micro > 0
  - If BUY: calculate escrow, verify player has balance
  - If SELL: verify player has available shares (quantity - open sell order remaining)
- If BUY:
  - `transfer(PLAYER → TREASURY, escrow, ESCROW_LOCK)`
  - Create Order with escrow_micro = escrow
- If SELL:
  - Create Order with escrow_micro = 0
- On validation failure: REJECT intent with reason

**`process_cancel_order(session, intent, tick_number, tick_id, treasury_id)`**

- Parse payload: `{order_id}`
- Find order, verify:
  - Exists
  - Belongs to intent.player_id
  - Status is OPEN or PARTIAL
- If BUY and escrow_micro > 0:
  - `transfer(TREASURY → PLAYER, escrow_micro, ESCROW_RELEASE)`
- Set order.status = CANCELLED, updated_at_tick = tick_number
- On validation failure: REJECT intent with reason

**`match_orders(session, tick_number, tick_id, treasury_id)`**

- Get list of distinct (asset_type, asset_id) pairs with OPEN/PARTIAL orders
- For each asset:

  ```
  buy_orders  = SELECT WHERE asset + side=BUY + status IN (OPEN, PARTIAL)
                ORDER BY price_limit DESC, created_at_tick ASC
  sell_orders = SELECT WHERE asset + side=SELL + status IN (OPEN, PARTIAL)
                ORDER BY price_limit ASC, created_at_tick ASC

  while buy_orders and sell_orders:
      best_buy = buy_orders[0]
      best_sell = sell_orders[0]

      if best_buy.price_limit_micro < best_sell.price_limit_micro:
          break  # no match

      trade_price = best_sell.price_limit_micro  # maker price
      trade_qty = min(best_buy.remaining, best_sell.remaining)

      execute_trade(session, best_buy, best_sell, trade_qty, trade_price, tick_id, treasury_id)

      # Update/remove filled orders from working lists
  ```

**`execute_trade(session, buy_order, sell_order, trade_qty, trade_price, tick_id, treasury_id)`**

Core atomic execution:

```
trade_value = trade_qty * trade_price
buyer_fee = calculate_fee(trade_value)
seller_fee = calculate_fee(trade_value)
is_iso = sell_order.is_system

# ── Currency settlement ──
if not is_iso:
    # Normal P2P: pay seller from escrowed funds
    transfer(TREASURY → SELLER, trade_value, TRADE_SETTLEMENT, tick_id)
    # Seller pays fee
    transfer(SELLER → TREASURY, seller_fee, TRADE_FEE, tick_id)
    # Buyer fee: already in treasury as part of escrow — record on trade only
else:
    # ISO: seller IS treasury, skip self-transfers
    # Buyer's escrow is already in treasury — that IS the payment
    # No seller fee for system
    seller_fee = 0

# ── Share transfer ──
# Seller: decrement shares
seller_share = SELECT gate_shares WHERE gate_id AND player_id=seller FOR UPDATE
seller_share.quantity -= trade_qty

# Buyer: upsert shares
INSERT gate_shares (gate_id, player_id, quantity=trade_qty)
ON CONFLICT (gate_id, player_id) DO UPDATE SET quantity = quantity + trade_qty

# ── Update orders ──
consumed_escrow = trade_value + buyer_fee
buy_order.escrow_micro -= consumed_escrow
buy_order.filled_quantity += trade_qty
buy_order.updated_at_tick = tick_number
buy_order.status = FILLED if fully filled else PARTIAL

sell_order.filled_quantity += trade_qty
sell_order.updated_at_tick = tick_number
sell_order.status = FILLED if fully filled else PARTIAL

# ── Release excess escrow if order fully filled ──
if buy_order.status == FILLED and buy_order.escrow_micro > 0:
    transfer(TREASURY → BUYER, buy_order.escrow_micro, ESCROW_RELEASE, tick_id)
    buy_order.escrow_micro = 0

# ── Record trade ──
INSERT trade (buy_order_id, sell_order_id, asset_type, asset_id,
              quantity=trade_qty, price_micro=trade_price,
              buyer_fee_micro=buyer_fee, seller_fee_micro=seller_fee,
              tick_id)
```

**`finalize_iso_transitions(session, tick_number, treasury_id)`**

- For each OFFERING gate:
  - Check if treasury holds 0 shares (all sold)
  - If yes: set gate.status = ACTIVE, cancel remaining ISO orders (if any)
  - Log transition

**`update_market_prices(session, tick_number)`**

- For each asset that had orders or trades this tick:
  - Compute last_price from most recent trade
  - Compute best_bid from highest OPEN/PARTIAL BUY order
  - Compute best_ask from lowest OPEN/PARTIAL SELL order
  - Compute volume_24h from trades in last 17,280 ticks (or configurable window)
  - UPSERT into market_prices

---

## Step 5 — Wire into Tick Pipeline

Update `simulation/tick.py`:

### Updated Pipeline Order

```
1.  Determine tick_number
2.  Derive seed + create RNG
3.  Insert tick record
4.  Load treasury_id
5.  Collect QUEUED intents
6.  Process intents:
    - DISCOVER_GATE → gate_lifecycle.process_discover_intent()
    - PLACE_ORDER   → order_matching.process_place_order()      ← NEW
    - CANCEL_ORDER  → order_matching.process_cancel_order()     ← NEW
7.  Advance gates (spawn, lifecycle, yield)
8.  Create ISO orders for OFFERING gates                        ← NEW
9.  Cancel orders for COLLAPSED gates                           ← NEW
10. Match orders                                                ← NEW
11. Finalize ISO transitions (all shares sold → ACTIVE)         ← NEW
12. Update market prices                                        ← NEW
13. Roll events (Phase 8+)
14. Anti-exploit maintenance (Phase 9+)
15. Mark remaining PROCESSING intents as EXECUTED
16. Compute state_hash
17. Finalize tick record
```

### Key: ISO orders are created AFTER gate lifecycle, BEFORE matching

This ensures newly spawned gates get ISO orders in the same tick they appear. Matching then processes them immediately.

### Key: Collapsed gate orders cancelled BEFORE matching

This prevents matching against dead assets and releases escrowed funds promptly.

---

## Step 6 — Schemas (`schemas/market.py`)

| Schema                | Fields                                                                                                                                          |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `OrderResponse`       | id, player_id, asset_type, asset_id, side, quantity, price_limit_micro, filled_quantity, escrow_micro, status, created_at_tick, updated_at_tick |
| `OrderListResponse`   | orders: list[OrderResponse], total: int                                                                                                         |
| `TradeResponse`       | id, buy_order_id, sell_order_id, asset_type, asset_id, quantity, price_micro, buyer_fee_micro, seller_fee_micro, tick_id                        |
| `TradeListResponse`   | trades: list[TradeResponse], total: int                                                                                                         |
| `MarketPriceResponse` | asset_type, asset_id, last_price_micro, best_bid_micro, best_ask_micro, volume_24h_micro, updated_at_tick                                       |
| `OrderBookEntry`      | price_micro: int, total_quantity: int, order_count: int                                                                                         |
| `OrderBookResponse`   | bids: list[OrderBookEntry], asks: list[OrderBookEntry]                                                                                          |

---

## Step 7 — API Routes (`api/market.py`, `api/orders.py`)

| Method | Path                                     | Auth | Purpose                                                                                  |
| ------ | ---------------------------------------- | ---- | ---------------------------------------------------------------------------------------- |
| `POST` | `/intents`                               | Yes  | `type=PLACE_ORDER`, payload: `{asset_type, asset_id, side, quantity, price_limit_micro}` |
| `POST` | `/intents`                               | Yes  | `type=CANCEL_ORDER`, payload: `{order_id}`                                               |
| `GET`  | `/orders/me`                             | Yes  | My open/recent orders (paginated)                                                        |
| `GET`  | `/market/{asset_type}/{asset_id}`        | No   | Price, bid/ask, volume                                                                   |
| `GET`  | `/market/{asset_type}/{asset_id}/book`   | No   | Order book aggregated by price level                                                     |
| `GET`  | `/market/{asset_type}/{asset_id}/trades` | No   | Recent trades (paginated)                                                                |

---

## Step 8 — Update State Hash

Extend `compute_state_hash` to include:

- Count of open orders
- Total escrow locked in open BUY orders
- Total trade count

This ensures replay verification catches market state divergence.

---

## Step 9 — Tests

### `test_fee_calculator.py`

| Test                   | Assertion                                   |
| ---------------------- | ------------------------------------------- |
| Small trade fee        | Fee at base rate (~0.5%)                    |
| Medium trade fee       | Fee scales progressively                    |
| Large trade fee capped | Fee rate hits MAX_FEE_RATE (10%)            |
| Zero value             | Returns 0 fee                               |
| Escrow calculation     | escrow = max_cost + max_fee, values correct |

### `test_market.py` (simulation-level)

| Test                                       | Assertion                                                          |
| ------------------------------------------ | ------------------------------------------------------------------ |
| Place BUY order escrows funds              | Player balance reduced by escrow, order created with escrow_micro  |
| Place SELL order validates shares          | Order created, no escrow, player shares unchanged                  |
| SELL order rejected: insufficient shares   | Intent REJECTED, no order created                                  |
| SELL order rejected: double-sell           | Two sells exceeding available shares → second rejected             |
| BUY order rejected: insufficient balance   | Intent REJECTED, no order created, balance unchanged               |
| Cancel BUY order releases escrow           | Player balance restored, order CANCELLED                           |
| Cancel SELL order                          | Order CANCELLED, no balance change                                 |
| Cancel wrong player's order                | Intent REJECTED                                                    |
| Basic match: one buy + one sell            | Trade created, shares moved, currency settled, fees charged        |
| Price-time priority                        | Earlier order at same price matches first                          |
| Partial fill                               | Buy order partially filled, status = PARTIAL, escrow updated       |
| Multiple fills in one tick                 | Multiple trades, all correct                                       |
| Trade price = seller's limit (maker price) | Buyer may pay less than limit                                      |
| Excess escrow released on full fill        | Remaining escrow returned to buyer after all fills                 |
| Cannot trade COLLAPSED gate shares         | Orders cancelled, escrow released                                  |
| ISO: system sells OFFERING shares          | ISO order created, shares sold to buyer, proceeds in treasury      |
| ISO: all shares sold → gate ACTIVE         | Gate transitions when treasury has 0 shares                        |
| ISO: no seller fee                         | seller_fee_micro = 0 on ISO trades                                 |
| ISO: unsold shares stay with treasury      | Gate goes ACTIVE after offering period, remaining shares untouched |
| Conservation after trading                 | `treasury + players = INITIAL_SEED` after N ticks of trading       |

### `test_market_api.py`

| Test                           | Assertion                                            |
| ------------------------------ | ---------------------------------------------------- |
| GET /orders/me (empty)         | Returns empty list, 200                              |
| GET /orders/me (with orders)   | Returns player's orders only                         |
| GET /market/{type}/{id}        | Returns price data                                   |
| GET /market/{type}/{id}/book   | Returns aggregated order book (bids + asks)          |
| GET /market/{type}/{id}/trades | Returns recent trades                                |
| Invalid asset_type             | 422                                                  |
| Nonexistent asset_id           | 200 with empty/null data (not 404 — no trades is OK) |

---

## Execution Order

```
Step 1:   Models + enums           → market.py, update ledger.py + __init__.py
Step 2:   Migration + config       → migration, update config.py
Step 3:   Fee calculator           → services/fee_calculator.py
Step 4:   Order matching service   → services/order_matching.py (largest file)
Step 5:   Wire tick pipeline       → modify simulation/tick.py
Step 6:   Schemas                  → schemas/market.py
Step 7:   API routes               → api/market.py, api/orders.py, update main.py
Step 8:   State hash               → modify simulation/state_hash.py
Step 9:   Tests                    → test_fee_calculator.py, test_market.py, test_market_api.py
```

**Estimated: ~7 new files, ~6 modified files.**

---

## Key Design Decisions

| Decision                                       | Rationale                                                                                                 |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Treasury as escrow holder                      | Maintains conservation invariant. Escrow is just `transfer(PLAYER → TREASURY)`. Ledger tracks it cleanly. |
| Skip self-transfers for ISO                    | Seller = treasury, escrow already in treasury. No-op settlement, no deadlock.                             |
| `is_system` flag on orders                     | Clean detection of ISO orders. Skip seller fee, skip self-transfer.                                       |
| `orders.player_id` plain UUID (no FK)          | Same convention as `gate_shares`. Treasury can be a seller.                                               |
| Price-time priority matching                   | Standard, fair, deterministic. Seller's limit price used (maker gets their price).                        |
| Fee calculated per-trade (not per-order)       | Partial fills at different prices get accurate fees. Conservative for escrow.                             |
| Escrow uses max possible fee                   | Ensures buyer always has enough. Excess released on fill/cancel.                                          |
| Available shares = quantity - open sell orders | No schema change. Calculated within tick transaction (safe from races).                                   |
| ISO orders created after gate lifecycle        | New gates get ISO orders in the same tick they spawn.                                                     |
| Collapsed gate orders auto-cancelled           | Prevents stale orders, releases locked escrow promptly.                                                   |
| Market prices updated after matching           | Reflects current state. UPSERT pattern handles first-trade and updates.                                   |
| ISO price = avg_yield \* payback / shares      | Economically derived. ~100 tick payback. Higher rank = higher price.                                      |
| No seller fee on ISO                           | System selling to bootstrap — fee would just be treasury → treasury.                                      |

---

## Edge Cases to Handle

| Edge Case                                       | Expected Behavior                                                  |
| ----------------------------------------------- | ------------------------------------------------------------------ |
| Buy order at price below all sells              | Order stays OPEN, no match                                         |
| Sell order at price above all buys              | Order stays OPEN, no match                                         |
| Player places buy + sell for same asset         | Both valid — player can have both sides open                       |
| Order quantity > total shares of gate           | Rejected at validation (can't buy/sell more than exist)            |
| Two players sell same gate, only one has shares | Validated at placement. Second rejected if insufficient available. |
| Gate collapses mid-tick (during lifecycle)      | Orders cancelled in cancel_collapsed step before matching          |
| Treasury depleted during escrow release         | Can't happen — escrow was already transferred to treasury          |
| All ISO shares sell in one tick                 | Gate transitions to ACTIVE in finalize_iso step same tick          |
| No open orders for any asset                    | Matching loop completes immediately, no error                      |
| Player cancels already-filled order             | Rejected — only OPEN/PARTIAL can be cancelled                      |
| Player cancels another player's order           | Rejected — ownership check                                         |
| Buyer fee > remaining escrow (shouldn't happen) | Escrow is calculated with max fee — this is prevented by design    |

---

## Conservation Invariant Update

```
treasury_balance + SUM(player_balances) = INITIAL_SEED
```

During Phase 5, escrow temporarily moves money from player → treasury. This is tracked in the ledger. The invariant holds because:

- ESCROW_LOCK: player -X, treasury +X → sum unchanged
- TRADE_SETTLEMENT: treasury -X, seller +X → sum unchanged
- TRADE_FEE: seller -X, treasury +X → sum unchanged
- ESCROW_RELEASE: treasury -X, player +X → sum unchanged
- ISO settlement: no transfer (money already in treasury) → sum unchanged

**Note**: The `SUM(escrow_micro)` across open BUY orders equals treasury's "debt" to those buyers. But since it's already in treasury balance, the invariant still holds naturally. No separate escrow tracking needed in the invariant.

---

## Dependencies

- Phase 2: TransferService (escrow + settlement)
- Phase 3: Tick pipeline, intent framework
- Phase 4: Gates, gate_shares, rank profiles, gate lifecycle
- Phase 6 (future): Guild shares use identical market system (`asset_type = GUILD_SHARE`)
