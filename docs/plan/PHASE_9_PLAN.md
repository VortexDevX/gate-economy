# Phase 9 Sub-Plan: Anti-Exploit & Balance

## Goal

Implement economic friction mechanisms that prevent permanent dominance, hoarding, and monopolistic control. Four mechanisms: portfolio maintenance (ongoing cost for holding shares), concentration penalties (extra cost for dominant positions), liquidity decay (cost for holding illiquid assets), and float caps (hard limit on ownership percentage). All are conservation-safe sinks (Player → Treasury).

---

## Economic Flows Introduced

| Flow | Mechanism             | Direction         | Entry Type              |
| ---- | --------------------- | ----------------- | ----------------------- |
| Sink | Portfolio maintenance | Player → Treasury | `PORTFOLIO_MAINTENANCE` |
| Sink | Concentration penalty | Player → Treasury | `CONCENTRATION_PENALTY` |
| Sink | Liquidity decay       | Player → Treasury | `LIQUIDITY_DECAY`       |

All three EntryType values already exist in the Python enum. Migration needed only if they're missing from the PostgreSQL enum.

Float caps are a validation check — no currency movement.

---

## Step 1 — Config

### Config Additions (`config.py`)

| Parameter                        | Default | Purpose                                                      |
| -------------------------------- | ------- | ------------------------------------------------------------ |
| `portfolio_maintenance_rate`     | 0.0001  | 0.01% of holding value per tick                              |
| `concentration_threshold_pct`    | 0.30    | Penalty kicks in above 30% ownership                         |
| `concentration_penalty_rate`     | 0.001   | 0.1% of holding value per tick at threshold                  |
| `liquidity_decay_inactive_ticks` | 200     | Gate considered illiquid after this many ticks without trade |
| `liquidity_decay_rate`           | 0.0005  | 0.05% of holding value per tick when illiquid                |
| `max_player_ownership_pct`       | 0.50    | Max 50% of any gate's total shares per player                |

---

## Step 2 — Migration (Conditional)

Check if `PORTFOLIO_MAINTENANCE`, `CONCENTRATION_PENALTY`, and `LIQUIDITY_DECAY` exist in the PostgreSQL `entrytype` enum. If not, create a migration:

```sql
ALTER TYPE entrytype ADD VALUE IF NOT EXISTS 'PORTFOLIO_MAINTENANCE';
ALTER TYPE entrytype ADD VALUE IF NOT EXISTS 'CONCENTRATION_PENALTY';
ALTER TYPE entrytype ADD VALUE IF NOT EXISTS 'LIQUIDITY_DECAY';
```

If they already exist (added in the original P2 migration), skip this step.

---

## Step 3 — Anti-Exploit Service (`services/anti_exploit.py`, 🆕 new file)

### Helper: `_share_value_micro(gate, market_price) → int`

```python
def _share_value_micro(gate, market_price):
    """Per-share value: market price if available, else fundamental estimate."""
    if market_price and market_price.last_price_micro:
        return market_price.last_price_micro
    # Fallback: fundamental value based on current yield capacity
    return int(
        gate.base_yield_micro * (gate.stability / 100.0)
        * settings.iso_payback_ticks
    ) // gate.total_shares
```

### `_portfolio_maintenance(session, tick_number, tick_id, treasury_id)`

Charges a small per-tick fee on all player gate share holdings.

```python
1. Query all GateShare rows where:
   - player_id != treasury_id
   - quantity > 0
   - joined with Gate where status IN (ACTIVE, UNSTABLE)

2. Batch-load MarketPrice for all GATE_SHARE assets

3. For each holding:
   - value = _share_value_micro(gate, market_price) * quantity
   - cost = int(value * settings.portfolio_maintenance_rate)
   - if cost <= 0: skip
   - Try transfer(PLAYER → TREASURY, cost, PORTFOLIO_MAINTENANCE)
   - On InsufficientBalance: charge e.available if > 0
```

### `_concentration_penalties(session, tick_number, tick_id, treasury_id)`

Extra cost when a player holds a dominant position (> threshold) in any gate.

```python
1. Query same GateShare holdings as above

2. For each holding:
   - ownership_pct = quantity / gate.total_shares
   - if ownership_pct <= settings.concentration_threshold_pct: skip
   - excess_pct = ownership_pct - settings.concentration_threshold_pct
   - value = _share_value_micro(gate, market_price) * quantity
   - penalty = int(value * settings.concentration_penalty_rate * (excess_pct / 0.10))
   - if penalty <= 0: skip
   - Try transfer(PLAYER → TREASURY, penalty, CONCENTRATION_PENALTY)
   - On InsufficientBalance: charge e.available if > 0
```

Penalty scales linearly: for every 10% above threshold, multiplier increases by 1×.

### `_liquidity_decay(session, tick_number, tick_id, treasury_id)`

Cost for holding shares in gates with no recent trading activity.

```python
1. Query all GateShare holdings (same as portfolio maintenance)

2. For each holding:
   - Look up MarketPrice for this gate
   - if no market_price or market_price.updated_at_tick is None: skip
   - inactive_ticks = tick_number - market_price.updated_at_tick
   - if inactive_ticks < settings.liquidity_decay_inactive_ticks: skip
   - value = _share_value_micro(gate, market_price) * quantity
   - cost = int(value * settings.liquidity_decay_rate)
   - if cost <= 0: skip
   - Try transfer(PLAYER → TREASURY, cost, LIQUIDITY_DECAY)
   - On InsufficientBalance: charge e.available if > 0
```

### `run_anti_exploit_maintenance(session, tick_number, tick_id, treasury_id)`

Orchestrator that runs all three mechanisms in order.

```python
async def run_anti_exploit_maintenance(session, tick_number, tick_id, treasury_id):
    await _portfolio_maintenance(session, tick_number, tick_id, treasury_id)
    await _concentration_penalties(session, tick_number, tick_id, treasury_id)
    await _liquidity_decay(session, tick_number, tick_id, treasury_id)
```

---

## Step 4 — Float Cap Validation

### Modify `process_place_order` in `order_matching.py`

Add a float cap check for BUY orders on GATE_SHARE assets:

```python
# After validating asset exists and before creating the order:
if payload["side"] == "BUY" and payload["asset_type"] == "GATE_SHARE":
    # Load current holding
    share_result = await session.execute(
        select(GateShare).where(
            GateShare.gate_id == asset_id,
            GateShare.player_id == intent.player_id,
        )
    )
    current_share = share_result.scalar_one_or_none()
    current_qty = current_share.quantity if current_share else 0

    gate_result = await session.execute(
        select(Gate.total_shares).where(Gate.id == asset_id)
    )
    total_shares = gate_result.scalar_one()

    max_allowed = int(total_shares * settings.max_player_ownership_pct)
    if current_qty + payload["quantity"] > max_allowed:
        intent.status = IntentStatus.REJECTED
        intent.reject_reason = (
            f"Would exceed ownership cap: "
            f"{current_qty}+{payload['quantity']} > {max_allowed} "
            f"({settings.max_player_ownership_pct:.0%} of {total_shares})"
        )
        return
```

This check applies to human players only. AI orders (created directly, not via intents) are not affected — they trade in small quantities.

---

## Step 5 — Pipeline Wiring

### Update `simulation/tick.py`

Replace `_anti_exploit_maintenance` no-op:

```python
from app.services.anti_exploit import run_anti_exploit_maintenance
```

Step 14 becomes:

```python
# 14. Anti-exploit maintenance
await run_anti_exploit_maintenance(session, tick_number, tick.id, treasury_id)
```

Remove the `_anti_exploit_maintenance` no-op function.

---

## Step 6 — Tests

### `test_anti_exploit.py` (🆕 new file)

#### Portfolio Maintenance

| Test                                                | Assertion                                    |
| --------------------------------------------------- | -------------------------------------------- |
| Charges maintenance on player holdings              | Player balance decreases, treasury increases |
| Skips OFFERING and COLLAPSED gates                  | No charge for non-active/unstable gates      |
| Skips treasury-held shares                          | Treasury doesn't charge itself               |
| Charges available balance when cost exceeds balance | Player drained to 0, no error                |
| No charge when player has no holdings               | Balances unchanged                           |

#### Concentration Penalty

| Test                                  | Assertion                           |
| ------------------------------------- | ----------------------------------- |
| Charges penalty above threshold       | Player charged when ownership > 30% |
| No penalty below threshold            | No charge when ownership ≤ 30%      |
| Penalty scales with excess percentage | Higher ownership → higher penalty   |

#### Liquidity Decay

| Test                             | Assertion                                   |
| -------------------------------- | ------------------------------------------- |
| Charges decay on illiquid gate   | Player charged when gate inactive > N ticks |
| No decay on recently traded gate | No charge when recent trade exists          |
| No decay when no market price    | Skip gates with no price history            |

#### Float Caps

| Test                             | Assertion                   |
| -------------------------------- | --------------------------- |
| Buy order rejected exceeding cap | Intent REJECTED with reason |
| Buy order accepted within cap    | Order created successfully  |
| Sell orders not affected by cap  | Sell always allowed         |
| Cap only applies to GATE_SHARE   | GUILD_SHARE buy not capped  |

#### Integration

| Test                                 | Assertion                                  |
| ------------------------------------ | ------------------------------------------ |
| Conservation holds after maintenance | treasury + players + guilds = INITIAL_SEED |
| Full tick with anti-exploit runs     | execute_tick completes without error       |

### Estimated: ~17 tests

---

## Execution Order

```
Step 1:  Config additions                     → config.py (edit)
Step 2:  Migration (conditional)              → migration (new, if needed)
Step 3:  Anti-exploit service                 → services/anti_exploit.py (new)
Step 4:  Float cap validation                 → services/order_matching.py (edit)
Step 5:  Pipeline wiring                      → simulation/tick.py (edit)
Step 6:  Tests                                → tests/test_anti_exploit.py (new)
```

### Estimated: ~1 new file, ~3 modified files, ~17 new tests

---

## Key Design Decisions

| Decision                                        | Rationale                                                                        |
| ----------------------------------------------- | -------------------------------------------------------------------------------- |
| Player-only maintenance (not guilds)            | Guilds already pay guild_maintenance that scales with holdings                   |
| Market price with fundamental fallback          | Market-driven when possible, safe fallback for untraded gates                    |
| Charge min(cost, balance) on insufficient funds | Prevents "keep balance at 0" exploit to dodge fees                               |
| Float cap at intent time, not match time        | Simpler, conservative check; prevents worst-case accumulation                    |
| Float cap ignores AI orders                     | AI trades small quantities; adding checks would complicate direct-order path     |
| Sequential mechanism execution                  | Portfolio → concentration → decay; each sees current balance after prior charges |
| No news for maintenance charges                 | Routine costs, not newsworthy; avoids news spam                                  |
| Concentration penalty scales linearly per 10%   | Simple, predictable, easy to reason about                                        |
| OFFERING and COLLAPSED gates exempt             | OFFERING has no yield yet; COLLAPSED is worthless                                |

---

## Edge Cases

| Edge Case                              | Expected Behavior                                                                                |
| -------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Player with 0 balance                  | All charges skipped (nothing to deduct)                                                          |
| Holding value rounds to 0 cost         | Charge skipped (cost <= 0 check)                                                                 |
| Player at exactly threshold (30%)      | No concentration penalty (> not >=)                                                              |
| Gate with no market price, no trades   | Use fundamental value fallback for portfolio/concentration; skip liquidity decay                 |
| Player holds shares of UNSTABLE gate   | Maintenance charged (UNSTABLE gates still have value)                                            |
| Player tries to buy exactly at cap     | Allowed (current + qty == max_allowed is fine via > check... actually need <= max_allowed check) |
| Multiple holdings charged in same tick | Each charge sees updated balance from prior charges                                              |
| AI player holdings                     | Subject to portfolio/concentration/decay same as humans                                          |
| Float cap on guild orders              | Not applied (guild orders don't go through PLACE_ORDER intent)                                   |
| Treasury-held ISO shares               | Skipped (treasury != player)                                                                     |

---

## Dependencies

- Phase 2: Transfer service, ledger entry types
- Phase 4: Gates, gate shares, gate lifecycle
- Phase 5: Market system (market prices for valuation, order placement for float cap)
- Phase 6: Guilds (excluded from player-only maintenance)

---

## Guidelines for Responses

1. **Small changes:** If a file only needs a minor update, just tell me _what_ to change and _where_.

2. **Label every file output:** Always specify whether the file is being:
   - 🆕 **Created** (new file)
   - ✏️ **Updated** (partial change)
   - 🔁 **Replaced** (full rewrite)

3. **Go step by step:**
   - If a step involves **fewer than 2 files**, combine it with the next.
   - Aim for **2–3 steps** at a time.

4. **No overthinking:** Don't spiral into deep analysis.
