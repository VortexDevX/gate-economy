# Phase 7 Summary — AI Traders

**Status:** ✅ Complete
**Tests added:** 20
**Cumulative tests:** 129

---

## What Was Built

Treasury-funded AI trading bots that provide market liquidity, price discovery, and volume through three automated strategies. AI bots are regular players (`is_ai=True`) that create orders directly in the tick pipeline (not via intents) and use the same escrow/transfer system as human players.

---

## Deliverables

### Step 1 — Config Additions (`config.py`)

9 new settings controlling AI behavior:

| Parameter                        | Default       | Purpose                        |
| -------------------------------- | ------------- | ------------------------------ |
| `ai_market_maker_budget_micro`   | 2,000,000,000 | MM starting funds (2,000 curr) |
| `ai_value_investor_budget_micro` | 1,000,000,000 | VI starting funds (1,000 curr) |
| `ai_noise_trader_budget_micro`   | 500,000,000   | NT starting funds (500 curr)   |
| `ai_mm_spread`                   | 0.05          | MM bid/ask spread (5%)         |
| `ai_mm_order_qty`                | 5             | Shares per MM order            |
| `ai_vi_buy_discount`             | 0.30          | Buy when price < fair × 0.7    |
| `ai_vi_sell_premium`             | 0.30          | Sell when price > fair × 1.3   |
| `ai_noise_activity`              | 0.40          | Probability NT acts per tick   |
| `ai_noise_max_qty`               | 3             | Max shares per noise trade     |

### Step 2 — AI Player Seeding (`main.py`)

- Added `seed_ai_players()` to application lifespan (runs after `seed_gate_rank_profiles()`).
- Creates 3 AI players idempotently:
  - `ai_market_maker` — 2,000 currency budget
  - `ai_value_investor` — 1,000 currency budget
  - `ai_noise_trader` — 500 currency budget
- `password_hash = "!ai-no-login"` — never matches Argon2, AI cannot authenticate via API.
- Budgets funded from treasury via `TransferService` with `AI_BUDGET` entry type — conservation maintained.

### Step 2b — RNG Addition (`simulation/rng.py`)

- Added `shuffle(seq)` method to `TickRNG` (deterministic in-place shuffle via `random.Random.shuffle`).
- Required by Market Maker to randomize gate processing order.

### Step 3 — AI Trading Service (`services/ai_traders.py`) — 🆕 New File

**Helpers:**

| Function                  | Purpose                                                     |
| ------------------------- | ----------------------------------------------------------- |
| `_cancel_ai_orders()`     | Cancel all OPEN/PARTIAL orders for an AI, release escrow    |
| `_get_available_shares()` | Held shares minus committed to open sell orders             |
| `_place_ai_buy()`         | Place BUY with escrow lock, returns False if broke          |
| `_place_ai_sell()`        | Place SELL after checking available shares                  |
| `_get_reference_price()`  | Fallback chain: last_price → best_ask → ISO estimate → None |

**Strategies:**

| Strategy           | Behavior                                                                                                                                                                                                                   |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Market Maker**   | Cancel-and-replace each tick. Places BUY at `ref × 0.95` and SELL at `ref × 1.05` on every tradeable gate (OFFERING/ACTIVE/UNSTABLE). Sells only if holding shares. Gates shuffled via RNG.                                |
| **Value Investor** | Estimates fair value via DCF: `(base_yield × stability% × remaining_ticks) / total_shares`. Buys when `market_price < fair × 0.7`, sells when `market_price > fair × 1.3`. Max 10% of balance per gate. Only ACTIVE gates. |
| **Noise Trader**   | Acts with 40% probability per tick. Picks random ACTIVE gate with a market price. Random BUY/SELL, random quantity (1–3), price jittered ±10% around last_price. Sells only if holding.                                    |

**Orchestrator:**

`run_ai_traders()` — loads all `is_ai=True` players with `FOR UPDATE`, runs each strategy by username. Returns immediately if no AI players exist.

### Step 4 — Pipeline Wiring (`simulation/tick.py`)

New step **7c** between guild lifecycle and ISO creation:

```
7b. Guild lifecycle (maintenance, insolvency, auto-dividends)
7c. AI traders (cancel old orders, run strategies)  ← NEW
8.  Create ISO orders for OFFERING gates + guild shares
```

AI orders placed in step 7c are matched in step 10 alongside all other orders — same-tick execution.

### Step 5 — Tests (`tests/test_ai_traders.py`) — 🆕 New File

20 tests covering:

| Category        | Tests | What's Verified                                                       |
| --------------- | ----- | --------------------------------------------------------------------- |
| Seeding         | 3     | Creates 3 AI players, idempotent, funds from treasury                 |
| Reference Price | 4     | last_price preferred, best_ask fallback, ISO estimate, None           |
| Market Maker    | 4     | BUY placement, SELL when holding, cancel old orders, skip no-price    |
| Value Investor  | 3     | Buy undervalued, skip fair-priced, sell overvalued                    |
| Noise Trader    | 2     | Places random order, skips with probability                           |
| Edge Cases      | 4     | No gates → nothing, broke → no crash, conservation, AI+human matching |

---

## Economic Impact

| Flow    | Mechanism         | Direction            | Entry Type                       |
| ------- | ----------------- | -------------------- | -------------------------------- |
| Faucet  | AI budget         | Treasury → AI Player | `AI_BUDGET`                      |
| Lock    | AI buy escrow     | AI Player → Treasury | `ESCROW_LOCK`                    |
| Unlock  | AI escrow release | Treasury → AI Player | `ESCROW_RELEASE`                 |
| Neutral | AI trades         | AI ↔ Any Player      | `TRADE_SETTLEMENT` + `TRADE_FEE` |

Conservation invariant unchanged — AI players are regular entries in `SUM(player_balances)`.

---

## Key Design Decisions

| Decision                                     | Rationale                                                          |
| -------------------------------------------- | ------------------------------------------------------------------ |
| AI creates orders directly (not via intents) | Same-tick execution, AI is part of simulation engine               |
| Cancel-and-replace each tick                 | Simple, no stale order management complexity                       |
| AI only trades GATE_SHARE                    | Simpler scope, GUILD_SHARE can be added later                      |
| One-time budget funding                      | Natural consequence if AI goes broke — finite resources            |
| Strategies use tick RNG                      | Deterministic replay guaranteed                                    |
| Reference price fallback chain               | Ensures AI can trade on new gates (ISO estimate) and existing ones |
| Step 7c placement (before ISO + matching)    | AI orders placed same tick get matched immediately                 |

---

## Files Changed

| File                                 | Action  |
| ------------------------------------ | ------- |
| `backend/app/config.py`              | ✏️ Edit |
| `backend/app/main.py`                | ✏️ Edit |
| `backend/app/simulation/rng.py`      | ✏️ Edit |
| `backend/app/simulation/tick.py`     | ✏️ Edit |
| `backend/app/services/ai_traders.py` | 🆕 New  |
| `backend/tests/test_ai_traders.py`   | 🆕 New  |

---

## Tick Pipeline (Updated)

```
1.  Determine tick_number              ✅ P3
2.  Derive seed + create TickRNG       ✅ P3
3.  Insert tick record                 ✅ P3
4.  Load treasury_id                   ✅ P4
5.  Collect QUEUED intents → PROCESSING ✅ P3
6.  Process intents by type            ✅ P3-P6
7.  System gate spawn + lifecycle + yield ✅ P4
7b. Guild lifecycle                    ✅ P6
7c. AI traders                         ✅ P7
8.  Create ISO orders                  ✅ P5
9.  Cancel dead asset orders           ✅ P5
10. Match orders                       ✅ P5
11. Finalize ISO transitions           ✅ P5
12. Update market prices               ✅ P5
13. Roll events                        🔲 P8
14. Anti-exploit maintenance           🔲 P9
15. Mark intents → EXECUTED            ✅ P3
16. Compute state_hash                 ✅ P3
17. Finalize tick record               ✅ P3
```
