# Phase 7 Sub-Plan: AI Traders

## Goal

Treasury-funded AI players that provide market liquidity, price discovery, and trading volume through three automated strategies: Market Maker, Value Investor, and Noise Trader. AI bots are regular players (`is_ai=True`) that trade through the same order/escrow system as human players, but make decisions directly in the tick pipeline rather than via intents.

---

## Economic Flows Introduced

| Flow    | Mechanism         | Direction            | Entry Type                       |
| ------- | ----------------- | -------------------- | -------------------------------- |
| Faucet  | AI budget         | Treasury → AI Player | `AI_BUDGET`                      |
| Lock    | AI buy escrow     | AI Player → Treasury | `ESCROW_LOCK`                    |
| Unlock  | AI escrow release | Treasury → AI Player | `ESCROW_RELEASE`                 |
| Neutral | AI trades         | AI ↔ Any Player      | `TRADE_SETTLEMENT` + `TRADE_FEE` |

Conservation invariant unchanged — AI players are regular players in `SUM(player_balances)`.

---

## Step 1 — Config

### Config Additions (`config.py`)

| Parameter                        | Default       | Purpose                            |
| -------------------------------- | ------------- | ---------------------------------- |
| `ai_market_maker_budget_micro`   | 2,000,000,000 | MM starting funds (2,000 currency) |
| `ai_value_investor_budget_micro` | 1,000,000,000 | VI starting funds (1,000 currency) |
| `ai_noise_trader_budget_micro`   | 500,000,000   | NT starting funds (500 currency)   |
| `ai_mm_spread`                   | 0.05          | MM bid/ask spread (5%)             |
| `ai_mm_order_qty`                | 5             | Shares per MM order                |
| `ai_vi_buy_discount`             | 0.30          | Buy when price < fair × (1−this)   |
| `ai_vi_sell_premium`             | 0.30          | Sell when price > fair × (1+this)  |
| `ai_noise_activity`              | 0.40          | Probability of NT acting per tick  |
| `ai_noise_max_qty`               | 3             | Max shares per noise trade         |

---

## Step 2 — AI Player Seeding

### Update `main.py` lifespan — add `seed_ai_players()` after `seed_gate_rank_profiles()`:

```python
AI_BOTS = [
    ("ai_market_maker", "ai_mm@system.internal", settings.ai_market_maker_budget_micro),
    ("ai_value_investor", "ai_vi@system.internal", settings.ai_value_investor_budget_micro),
    ("ai_noise_trader", "ai_nt@system.internal", settings.ai_noise_trader_budget_micro),
]

async def seed_ai_players():
    for username, email, budget in AI_BOTS:
        # Check if player with this username exists
        if exists: skip
        # Create Player(username, email, is_ai=True, balance=0, password_hash="!ai-no-login")
        # transfer(SYSTEM → PLAYER, budget, AI_BUDGET, memo=f"AI budget: {username}")
```

Idempotent — skips if player with that username already exists.

### Notes

- `password_hash = "!ai-no-login"` — will never match Argon2 verification.
- AI players are created once at startup. If deleted by test cleanup, they don't respawn mid-test.
- Budget comes from treasury → conservation maintained.

---

## Step 3 — AI Trading Service (`services/ai_traders.py`)

### Core Utilities

#### `_cancel_ai_orders(session, player_id, tick_number, tick_id, treasury_id)`

```python
# Select all OPEN/PARTIAL orders for this AI player
# For each:
#   if BUY and escrow > 0: transfer(SYSTEM → PLAYER, escrow, ESCROW_RELEASE)
#   order.status = CANCELLED
#   order.updated_at_tick = tick_number
```

#### `_place_ai_buy(session, player_id, asset_type, asset_id, qty, price, tick_number, tick_id, treasury_id) → bool`

```python
escrow = qty * price + calculate_fee(qty * price)
# Check player balance >= escrow
if insufficient: return False
transfer(PLAYER → SYSTEM, escrow, ESCROW_LOCK, tick_id)
session.add(Order(
    player_id=player_id, asset_type=asset_type, asset_id=asset_id,
    side=BUY, quantity=qty, price_limit_micro=price,
    escrow_micro=escrow, created_at_tick=tick_number,
))
return True
```

#### `_place_ai_sell(session, player_id, asset_type, asset_id, qty, price, tick_number, tick_id, treasury_id) → bool`

```python
available = _get_available_shares(session, player_id, asset_type, asset_id)
if available < qty: return False
session.add(Order(
    player_id=player_id, asset_type=asset_type, asset_id=asset_id,
    side=SELL, quantity=qty, price_limit_micro=price,
    created_at_tick=tick_number,
))
return True
```

### `_get_reference_price(session, asset_type, asset_id, gate)` → `int | None`

```python
# 1. Try last_price from MarketPrice
# 2. Else try best_ask from MarketPrice (catches ISO price)
# 3. Else if gate is OFFERING, estimate from rank profile (ISO price formula)
# 4. Else return None (skip this asset)
```

---

### Market Maker Strategy

#### `run_market_maker(session, player, tick_number, tick_id, treasury_id, rng)`

```python
1. await _cancel_ai_orders(session, player.id, tick_number, tick_id, treasury_id)
   # Reload balance after escrow releases
   await session.refresh(player)

2. Query all gates with status in (OFFERING, ACTIVE, UNSTABLE)

3. Shuffle gate list using rng (deterministic order)

4. For each gate:
     ref_price = _get_reference_price(...)
     if ref_price is None: continue

     buy_price = int(ref_price * (1 - settings.ai_mm_spread))
     sell_price = int(ref_price * (1 + settings.ai_mm_spread))
     qty = settings.ai_mm_order_qty

     if buy_price > 0 and qty > 0:
         _place_ai_buy(session, player.id, GATE_SHARE, gate.id, qty, buy_price, ...)

     # Sell only if holding shares
     holding = query GateShare where gate_id=gate.id and player_id=player.id
     if holding and holding.quantity > 0:
         sell_qty = min(qty, holding.quantity)
         _place_ai_sell(session, player.id, GATE_SHARE, gate.id, sell_qty, sell_price, ...)
```

### Value Investor Strategy

#### `run_value_investor(session, player, tick_number, tick_id, treasury_id, rng)`

```python
1. await _cancel_ai_orders(session, player.id, tick_number, tick_id, treasury_id)
   await session.refresh(player)

2. Query all ACTIVE gates + their rank profiles

3. For each gate:
     # Estimate fair value per share
     profile = rank_profiles[gate.rank]
     remaining_stability = max(gate.stability - profile.collapse_threshold, 0)
     estimated_remaining_ticks = remaining_stability / settings.gate_base_decay_rate
     if estimated_remaining_ticks <= 0: continue

     total_remaining_yield = int(gate.base_yield_micro * (gate.stability / 100.0) * estimated_remaining_ticks)
     fair_value = total_remaining_yield // gate.total_shares
     if fair_value <= 0: continue

     ref_price = _get_reference_price(...)
     if ref_price is None: continue

     # BUY undervalued
     buy_threshold = int(fair_value * (1 - settings.ai_vi_buy_discount))
     if ref_price <= buy_threshold:
         max_spend = player.balance_micro // 10  # max 10% of balance per gate
         if max_spend > 0 and ref_price > 0:
             qty = min(max_spend // ref_price, settings.ai_mm_order_qty)
             if qty > 0:
                 _place_ai_buy(..., qty, ref_price, ...)

     # SELL overvalued
     sell_threshold = int(fair_value * (1 + settings.ai_vi_sell_premium))
     if ref_price >= sell_threshold:
         holding = query GateShare
         if holding and holding.quantity > 0:
             _place_ai_sell(..., holding.quantity, ref_price, ...)
```

### Noise Trader Strategy

#### `run_noise_trader(session, player, tick_number, tick_id, treasury_id, rng)`

```python
1. await _cancel_ai_orders(session, player.id, tick_number, tick_id, treasury_id)
   await session.refresh(player)

2. if rng.random() >= settings.ai_noise_activity: return  # skip this tick

3. Query all ACTIVE gates with market prices (last_price not null)
   if none: return

4. gate = rng.choice(gates)
   ref_price = market_price.last_price_micro

5. side = BUY if rng.random() < 0.5 else SELL
   qty = rng.randint(1, settings.ai_noise_max_qty)
   price_factor = rng.uniform(0.90, 1.10)
   price = max(1, int(ref_price * price_factor))

6. if side == BUY:
       _place_ai_buy(..., qty, price, ...)
   else:
       # Only sell if holding shares
       holding = query GateShare
       if holding and holding.quantity > 0:
           sell_qty = min(qty, holding.quantity)
           _place_ai_sell(..., sell_qty, price, ...)
```

### AI Runner

#### `run_ai_traders(session, tick_number, tick_id, treasury_id, rng)`

```python
result = await session.execute(
    select(Player).where(Player.is_ai == True).with_for_update()
)
ai_players = {p.username: p for p in result.scalars().all()}

if not ai_players:
    return  # no AI players, nothing to do

if "ai_market_maker" in ai_players:
    await run_market_maker(session, ai_players["ai_market_maker"],
                           tick_number, tick_id, treasury_id, rng)

if "ai_value_investor" in ai_players:
    await run_value_investor(session, ai_players["ai_value_investor"],
                             tick_number, tick_id, treasury_id, rng)

if "ai_noise_trader" in ai_players:
    await run_noise_trader(session, ai_players["ai_noise_trader"],
                           tick_number, tick_id, treasury_id, rng)
```

---

## Step 4 — Pipeline Wiring

### Update `simulation/tick.py`:

```python
from app.services.ai_traders import run_ai_traders
```

New step in pipeline between guild lifecycle and ISO creation:

```
7b. Guild lifecycle (maintenance, insolvency, auto-dividends)
7c. AI trader step (cancel old orders, run strategies)  ← NEW
8.  Create ISO orders
9.  Cancel dead asset orders
10. Match orders (AI orders matched alongside player orders)
```

```python
# 7c. AI traders
await run_ai_traders(session, tick_number, tick.id, treasury_id, rng)
```

### Why before ISO creation?

AI market makers can place buy orders on OFFERING gates. Those orders match against ISO sell orders created in step 8. This gives AI first access to new ISO shares alongside players.

### Why before matching?

AI orders created in step 7c are matched in step 10 alongside all other orders. Same-tick execution — no delay disadvantage.

---

## Step 5 — Tests

### `test_ai_traders.py` (simulation-level)

| Test                                    | Assertion                                                    |
| --------------------------------------- | ------------------------------------------------------------ |
| AI seeding creates 3 players            | 3 players with `is_ai=True`, correct usernames               |
| AI seeding is idempotent                | Running twice doesn't duplicate                              |
| AI seeding funds from treasury          | Balances correct, conservation holds                         |
| MM places buy order for priced gate     | BUY order exists at spread below last_price                  |
| MM places sell when holding shares      | SELL order exists at spread above last_price                 |
| MM cancels old orders on new tick       | Previous tick's orders cancelled, escrow released            |
| MM skips gate without price             | No orders for unpriced gates                                 |
| VI buys undervalued gate                | BUY order when market_price < fair_value \* 0.7              |
| VI skips fairly-priced gate             | No order when price near fair_value                          |
| VI sells overvalued gate                | SELL order when price > fair_value \* 1.3 and holding shares |
| NT places random order                  | Order created with valid params                              |
| NT skips with probability               | No order when RNG says skip (controlled seed)                |
| AI does nothing without tradeable gates | No orders when no active/offering gates                      |
| AI buy fails when balance exhausted     | No buy order, no crash                                       |
| AI orders matched via standard matching | Trades execute, balances update correctly                    |
| Conservation after AI trading           | treasury + players + guilds = INITIAL_SEED                   |

### Estimated: ~16 tests

---

## Execution Order

```
Step 1:  Config additions                → config.py (edit)
Step 2:  AI player seeding              → main.py (edit)
Step 3:  AI trading service             → services/ai_traders.py (new, largest file)
Step 4:  Pipeline wiring                → simulation/tick.py (edit)
Step 5:  Tests                          → tests/test_ai_traders.py (new)
```

### Estimated: ~2 new files, ~3 modified files, ~16 new tests.

---

## Key Design Decisions

| Decision                                     | Rationale                                                          |
| -------------------------------------------- | ------------------------------------------------------------------ |
| AI creates orders directly (not via intents) | Same-tick execution, AI is part of simulation engine not a UI user |
| AI uses same escrow/transfer system          | Fully auditable, same money safety guarantees                      |
| Cancel-and-replace each tick                 | Simple, no stale order management complexity                       |
| AI only trades GATE_SHARE                    | Simpler scope, GUILD_SHARE can be added later                      |
| One-time budget funding                      | Simple, natural consequence if AI goes broke                       |
| AI players marked `is_ai=True`               | Clean identification using existing field                          |
| AI step before ISO + matching                | AI orders placed in same tick get matched immediately              |
| Reference price fallback chain               | last_price → best_ask → ISO estimate → skip                        |
| Strategies use tick RNG                      | Deterministic replay guaranteed                                    |
| `password_hash = "!ai-no-login"`             | Never matches Argon2 — AI cannot authenticate via API              |

---

## Edge Cases

| Edge Case                            | Expected Behavior                                              |
| ------------------------------------ | -------------------------------------------------------------- |
| No active/offering gates             | AI does nothing, returns early                                 |
| AI balance exhausted                 | No buy orders placed, no crash                                 |
| AI holds no shares of a gate         | No sell orders for that gate                                   |
| Gate collapses while AI holds shares | Shares worthless (same as players), orders cancelled in step 9 |
| All ISO shares bought by AI          | Normal — AI and players compete equally                        |
| AI orders match each other           | Valid — two AI bots can trade                                  |
| No AI players in DB (test cleanup)   | AI step returns immediately, no effect                         |
| AI sells more than available         | `_place_ai_sell` checks available, rejects                     |
| MM + VI both want same gate          | Both place orders, matched by price-time priority              |
| Very high volatility gate            | VI fair value estimate may be inaccurate — by design           |

---

## Dependencies

- Phase 2: Player accounts, TransferService, `is_ai` field
- Phase 4: Gates, gate_shares, rank profiles, gate lifecycle
- Phase 5: Market system (orders, matching, escrow, market prices)
- Phase 6: Guild model (for state hash — no direct AI-guild interaction in P7)
