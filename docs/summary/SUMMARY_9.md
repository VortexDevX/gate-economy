# Phase 9 Summary: Anti-Exploit & Balance

**Status:** ✅ Complete
**Tests added:** 17
**Cumulative tests:** 165

---

## What Was Built

Four economic friction mechanisms that prevent permanent dominance, hoarding, and monopolistic control in the closed-loop economy.

### 1. Portfolio Maintenance (Sink)

A small per-tick fee charged on all player gate share holdings in ACTIVE or UNSTABLE gates.

- **Rate:** 0.01% of holding value per tick (`portfolio_maintenance_rate = 0.0001`)
- **Flow:** Player → Treasury (`PORTFOLIO_MAINTENANCE` ledger entry)
- **Valuation:** Market price if available, fundamental estimate fallback
- **Skips:** Treasury-held shares, OFFERING/COLLAPSED gates, zero-cost rounds
- **Partial charge:** If player can't afford full cost, drains available balance to 0

### 2. Concentration Penalty (Sink)

Extra cost when a player holds a dominant position (>30%) in any single gate.

- **Threshold:** 30% ownership (`concentration_threshold_pct = 0.30`)
- **Rate:** 0.1% of holding value per tick, scaled linearly per 10% excess (`concentration_penalty_rate = 0.001`)
- **Flow:** Player → Treasury (`CONCENTRATION_PENALTY` ledger entry)
- **Scaling:** At 40% ownership (10% excess), multiplier = 1×. At 50% (20% excess), multiplier = 2×.
- **Partial charge:** Same drain-to-zero behavior as portfolio maintenance

### 3. Liquidity Decay (Sink)

Cost for holding shares in gates with no recent trading activity.

- **Inactive threshold:** 200 ticks without a trade (`liquidity_decay_inactive_ticks = 200`)
- **Rate:** 0.05% of holding value per tick (`liquidity_decay_rate = 0.0005`)
- **Flow:** Player → Treasury (`LIQUIDITY_DECAY` ledger entry)
- **Skips:** Gates with no market price history, recently traded gates
- **Partial charge:** Same drain-to-zero behavior

### 4. Float Cap (Validation)

Hard limit preventing any single player from owning more than 50% of a gate's total shares.

- **Cap:** 50% (`max_player_ownership_pct = 0.50`)
- **Enforcement:** BUY orders rejected at intent processing time
- **Scope:** GATE_SHARE only — GUILD_SHARE not capped
- **Exemptions:** OFFERING gates (ISO distribution must be unrestricted), AI direct orders
- **No currency movement** — pure validation check

---

## Files Changed

| File                                     | Action     | Purpose                                                        |
| ---------------------------------------- | ---------- | -------------------------------------------------------------- |
| `backend/app/config.py`                  | ✏️ Updated | 6 new anti-exploit config parameters                           |
| `backend/app/services/anti_exploit.py`   | 🆕 Created | Portfolio, concentration, liquidity decay mechanisms           |
| `backend/app/services/order_matching.py` | ✏️ Updated | Float cap validation in `process_place_order`                  |
| `backend/app/simulation/tick.py`         | ✏️ Updated | Wired `run_anti_exploit_maintenance` at step 14, removed no-op |
| `backend/tests/test_anti_exploit.py`     | 🆕 Created | 17 tests for all mechanisms                                    |
| `backend/tests/test_market.py`           | ✏️ Updated | Fixed typo, disabled anti-exploit rates in autouse fixture     |
| `backend/tests/conftest.py`              | ✏️ Updated | Global `_disable_anti_exploit` autouse fixture                 |
| `backend/tests/test_events.py`           | ✏️ Updated | Added `pause_simulation` to fix race condition                 |
| `backend/tests/test_ai_traders.py`       | ✏️ Updated | Added `pause_simulation` to fix race condition                 |

---

## Config Parameters Added

| Parameter                        | Default | Purpose                                       |
| -------------------------------- | ------- | --------------------------------------------- |
| `portfolio_maintenance_rate`     | 0.0001  | 0.01% of holding value per tick               |
| `concentration_threshold_pct`    | 0.30    | Penalty above 30% ownership                   |
| `concentration_penalty_rate`     | 0.001   | 0.1% of holding value per tick at threshold   |
| `liquidity_decay_inactive_ticks` | 200     | Ticks without trade → illiquid                |
| `liquidity_decay_rate`           | 0.0005  | 0.05% of holding value per tick when illiquid |
| `max_player_ownership_pct`       | 0.50    | Max 50% of any gate's shares                  |

---

## Tick Pipeline Update

Step 14 changed from no-op to active:

```
14. Anti-exploit maintenance ✅ P9
    → _portfolio_maintenance()
    → _concentration_penalties()
    → _liquidity_decay()
```

Sequential execution ensures each mechanism sees updated balance from prior charges.

---

## Design Decisions

| Decision                                          | Rationale                                                               |
| ------------------------------------------------- | ----------------------------------------------------------------------- |
| Player-only maintenance (not guilds)              | Guilds already pay `guild_maintenance` that scales with holdings        |
| Market price with fundamental fallback            | Market-driven when possible, safe fallback for untraded gates           |
| Charge `min(cost, balance)` on insufficient funds | Prevents "keep balance at 0" exploit to dodge fees                      |
| Float cap at intent time, not match time          | Simpler, conservative; prevents worst-case accumulation                 |
| OFFERING gates exempt from float cap              | ISO is initial distribution — must allow full purchase                  |
| Float cap ignores AI orders                       | AI trades small quantities; adding checks complicates direct-order path |
| No news for maintenance charges                   | Routine costs, not newsworthy; avoids news spam                         |
| Global `_disable_anti_exploit` in conftest        | Prevents worker tick deadlocks; anti-exploit tests re-enable locally    |

---

## Test Coverage (17 tests)

### Portfolio Maintenance (5)

- Charges maintenance on player holdings
- Skips OFFERING and COLLAPSED gates
- Skips treasury-held shares
- Partial charge drains to 0 on insufficient balance
- No charge when player has no holdings

### Concentration Penalty (3)

- Charges penalty above 30% threshold
- No penalty at or below threshold
- Penalty scales with excess percentage (40% vs 50%)

### Liquidity Decay (3)

- Charges decay on illiquid gate (inactive > 200 ticks)
- No charge on recently traded gate
- No charge when no market price exists

### Float Caps (4)

- BUY order rejected when exceeding cap
- BUY order accepted at exact cap boundary
- SELL orders not affected by cap
- GUILD_SHARE BUY not subject to cap

### Integration (2)

- Conservation invariant holds after all maintenance charges
- Full tick with anti-exploit completes successfully

---

## Fixes Applied During Phase

1. **OFFERING gates exempted from float cap** — ISO buying all shares of a small gate was being rejected
2. **Anti-exploit rates disabled globally in test conftest** — worker ticks acquiring locks caused deadlocks with concurrent test sessions
3. **`pause_simulation` added to flaky tests** — `test_mm_cancels_old_orders`, `test_event_skipped_no_valid_targets` had worker race conditions
4. **Typo fix in test_market.py** — `@pytest.mark.asynciopcof` → `@pytest.mark.asyncio`

---

## Economic Impact

These mechanisms create continuous pressure against:

- **Passive hoarding** — portfolio maintenance ensures holding costs exist
- **Monopolistic control** — concentration penalty makes dominance expensive
- **Illiquid cornering** — liquidity decay punishes buying and holding without trading
- **Hard monopoly** — float cap prevents any player from owning >50% of a gate

All three sinks flow Player → Treasury, maintaining the conservation invariant:

```
treasury + Σ(player_balances) + Σ(guild_treasuries) = INITIAL_SEED
```
