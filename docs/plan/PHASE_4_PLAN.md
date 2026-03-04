# Phase 4 Sub-Plan: Dungeon Gates

## Goal

Gates spawn (system or player-discovered), generate yield paid from treasury to shareholders, decay in stability over time, and eventually collapse. First real economic faucet (yield) and sink (discovery cost).

---

### Step 1 — Models (`gate.py`, update `gate_shares` into same or separate file)

| File                 | Contents                                                                                                                                                                                                                                                 |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `models/gate.py`     | `GateRank` enum (E, D, C, B, A, S, S_PLUS)                                                                                                                                                                                                               |
|                      | `GateStatus` enum (OFFERING, ACTIVE, UNSTABLE, COLLAPSED)                                                                                                                                                                                                |
|                      | `DiscoveryType` enum (SYSTEM, PLAYER)                                                                                                                                                                                                                    |
|                      | `GateRankProfile` — one row per rank. PK = rank. Fields: `stability_init`, `volatility`, `yield_min_micro`, `yield_max_micro`, `total_shares`, `lifespan_min`, `lifespan_max`, `collapse_threshold`, `discovery_cost_micro`, `spawn_weight`              |
|                      | `Gate` — UUID PK, `rank` FK, `stability` DECIMAL, `volatility` DECIMAL, `base_yield_micro` BIGINT, `total_shares` INT, `status` enum, `spawned_at_tick` INT, `collapsed_at_tick` INT NULL, `discovery_type` enum, `discoverer_id` UUID NULL FK → players |
|                      | `GateShare` — composite PK (`gate_id`, `player_id`), `quantity` INT CHECK >= 0                                                                                                                                                                           |
| `models/__init__.py` | Add imports for `GateRankProfile`, `Gate`, `GateShare`                                                                                                                                                                                                   |

**Note**: System-held shares use a convention — the system account UUID from `system_accounts` is used as `player_id` in `gate_shares` for shares not yet sold. This avoids a separate holder type column.

---

### Step 2 — Migration + Seed Data

```

make migration msg="add gates gate_rank_profiles gate_shares"
make migrate

```

Seed `gate_rank_profiles` via a data migration (or startup hook like treasury seeding). Default values:

| Rank   | stability_init | volatility | yield_min_micro | yield_max_micro | total_shares | lifespan_min | lifespan_max | collapse_threshold | discovery_cost_micro | spawn_weight |
| ------ | -------------- | ---------- | --------------- | --------------- | ------------ | ------------ | ------------ | ------------------ | -------------------- | ------------ |
| E      | 100            | 0.05       | 1,000           | 5,000           | 100          | 200          | 400          | 20                 | 100,000              | 40           |
| D      | 95             | 0.08       | 3,000           | 10,000          | 80           | 180          | 360          | 22                 | 250,000              | 25           |
| C      | 90             | 0.12       | 8,000           | 25,000          | 60           | 150          | 300          | 25                 | 500,000              | 18           |
| B      | 85             | 0.15       | 20,000          | 60,000          | 50           | 120          | 250          | 28                 | 1,000,000            | 10           |
| A      | 80             | 0.20       | 50,000          | 150,000         | 40           | 100          | 200          | 30                 | 2,500,000            | 5            |
| S      | 75             | 0.25       | 120,000         | 400,000         | 30           | 80           | 160          | 35                 | 5,000,000            | 2            |
| S_PLUS | 70             | 0.30       | 300,000         | 1,000,000       | 20           | 60           | 120          | 40                 | 10,000,000           | 1            |

All `_micro` values are in micro-units. Yields are per-tick amounts for the whole gate (split across shareholders).

---

### Step 3 — Config Updates

Add to `config.py`:

- `system_spawn_probability: float = 0.15` — chance per tick of a system-spawned gate
- `gate_offering_ticks: int = 60` — ticks a gate stays in OFFERING before transitioning to ACTIVE
- `gate_base_decay_rate: float = 0.1` — base stability decay per tick (scaled by rank volatility)

---

### Step 4 — Gate Lifecycle Service (`services/gate_lifecycle.py`)

Core functions called from the tick pipeline:

**`system_spawn_gate(session, tick_number, rng, treasury_id)`**

- Roll `rng.random()` against `system_spawn_probability`
- If triggered: weighted random rank selection using `spawn_weight`
- Create gate with randomized params within rank profile ranges:
  - `stability` = profile `stability_init`
  - `volatility` = profile `volatility` \* `rng.uniform(0.8, 1.2)`
  - `base_yield_micro` = `rng.randint(yield_min, yield_max)`
  - `total_shares` = profile `total_shares`
  - `status` = OFFERING
  - `discovery_type` = SYSTEM
- Create `GateShare` entry: `player_id = treasury_id`, `quantity = total_shares`

**`process_discover_gate(session, intent, rng, treasury_id)`**

- Validate player balance >= discovery cost for requested `min_rank`
- Transfer: player → treasury (GATE_DISCOVERY)
- Roll rank: start at `min_rank`, RNG chance to upgrade one tier (e.g., 15% per tier, cumulative check)
- Create gate same as system spawn but `discovery_type = PLAYER`, `discoverer_id = player.id`
- Create `GateShare` with shares assigned to treasury (same as system spawn — sold via market in Phase 5)

**`advance_gate_lifecycle(session, tick_number, rng)`**

- For each gate with status OFFERING:
  - If `tick_number - spawned_at_tick >= gate_offering_ticks`: transition to ACTIVE
- For each gate with status ACTIVE or UNSTABLE:

```

age = tick_number - spawned_at_tick
decay_rate = gate_base_decay_rate _ (1 + gate.volatility _ rng.gauss(0, 0.3))
decay_rate = max(decay_rate, 0) # no negative decay (no free stability)
gate.stability -= decay_rate
gate.stability = max(gate.stability, 0) # floor at 0

if gate.status == ACTIVE and gate.stability < profile.collapse_threshold:
gate.status = UNSTABLE

if gate.status == UNSTABLE:
collapse_prob = (profile.collapse_threshold - gate.stability) / profile.collapse_threshold
collapse_prob = max(collapse_prob, 0)
if rng.random() < collapse_prob:
gate.status = COLLAPSED
gate.collapsed_at_tick = tick_number

```

**`distribute_yield(session, tick_number, treasury_id)`**

- For each ACTIVE gate (not OFFERING, not UNSTABLE, not COLLAPSED):

```

effective_yield = gate.base_yield_micro \* (gate.stability / 100.0)
effective_yield = int(effective_yield) # truncate to integer micro-units

# Load all shareholders with quantity > 0

# Skip if no shareholders or effective_yield <= 0

# Cap at treasury balance

treasury = SELECT FOR UPDATE treasury
if treasury.balance_micro < effective_yield:
effective_yield = treasury.balance_micro
if effective_yield <= 0:
skip

# Distribute pro-rata

total_held = SUM(shares.quantity)
remainder = effective_yield
for each shareholder (ordered by player_id for determinism):
payout = effective_yield \* share.quantity // total_held
if payout > 0:
transfer(TREASURY → shareholder, payout, YIELD_PAYMENT, tick_id)
remainder -= payout

# Any remainder from integer division stays in treasury (implicit)

```

**Important**: Use integer division (`//`) for pro-rata to avoid floating point. Remainder stays in treasury. This is conservative and preserves the invariant.

---

### Step 5 — Wire into Tick Pipeline (`simulation/tick.py`)

Fill in the no-op hooks:

```python
async def _process_intents(session, tick_number, rng, intents):
  # Filter for DISCOVER_GATE intents
  # Call process_discover_gate for each
  # Mark rejected if insufficient funds (set reject_reason)

async def _advance_gates(session, tick_number, rng):
  # Call system_spawn_gate
  # Call advance_gate_lifecycle
  # Call distribute_yield
```

**Intent rejection**: If a DISCOVER_GATE intent fails validation (insufficient balance, invalid rank), set `intent.status = REJECTED` and `intent.reject_reason = "..."`. Do NOT raise — continue processing remaining intents.

---

### Step 6 — Schemas

| Schema                    | Fields                                                                                                                                     |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `GateResponse`            | id, rank, stability, volatility, base_yield_micro, total_shares, status, spawned_at_tick, collapsed_at_tick, discovery_type, discoverer_id |
| `GateDetailResponse`      | Same as above + shareholders summary (list of {player_id, quantity, percentage})                                                           |
| `GateListResponse`        | List of `GateResponse` with pagination (total count)                                                                                       |
| `GateRankProfileResponse` | All profile fields for reference                                                                                                           |

---

### Step 7 — API Routes (`api/gates.py`)

| Method | Path                   | Auth | Purpose                                      |
| ------ | ---------------------- | ---- | -------------------------------------------- |
| `GET`  | `/gates`               | No   | List gates (filter: status, rank, paginated) |
| `GET`  | `/gates/{id}`          | No   | Gate detail + shareholder summary            |
| `GET`  | `/gates/rank-profiles` | No   | List all rank profiles (reference data)      |

Discovery is via existing `POST /intents` with `type=DISCOVER_GATE`.

---

### Step 8 — Update State Hash

Extend `compute_state_hash` to include:

- Count of gates per status
- Sum of all gate stabilities (truncated to int for determinism)
- Total shares held across all gates

This ensures replay verification catches gate state divergence.

---

### Step 9 — Ledger Entry Types

Already defined in Phase 2: `GATE_DISCOVERY`, `YIELD_PAYMENT`. No new enum values needed.

Add `ESCROW_LOCK` and `ESCROW_RELEASE` to `EntryType` enum for Phase 5 readiness (optional — can defer).

---

### Step 10 — Tests

| Test File           | Cases                                                                                                                                                |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_gates.py`     | System spawn creates gate (run 20 ticks, expect at least 1 gate). Gate has correct initial stability from profile. Gate shares created for treasury. |
|                     | Player discovery: deducts cost, creates gate, correct discovery_type + discoverer_id.                                                                |
|                     | Discovery with insufficient balance → intent REJECTED, no gate created, no balance change.                                                           |
|                     | Gate lifecycle: run N ticks → stability decreases. Gate transitions ACTIVE → UNSTABLE → COLLAPSED.                                                   |
|                     | OFFERING → ACTIVE transition after `gate_offering_ticks`.                                                                                            |
|                     | Yield distribution: treasury debited, shareholders credited, amounts match pro-rata.                                                                 |
|                     | No yield for COLLAPSED gates.                                                                                                                        |
|                     | No yield when treasury is empty (graceful degradation, no error).                                                                                    |
|                     | Conservation invariant holds after spawn + discovery + yield distribution.                                                                           |
| `test_gates_api.py` | `GET /gates` returns list (empty initially, populated after ticks).                                                                                  |
|                     | `GET /gates/{id}` returns detail with shareholders.                                                                                                  |
|                     | `GET /gates/{id}` with invalid UUID → 404.                                                                                                           |
|                     | `GET /gates?status=ACTIVE` filters correctly.                                                                                                        |
|                     | `GET /gates/rank-profiles` returns all 7 profiles.                                                                                                   |

---

## Execution Order

```
Step 1:   models                    → 1 file (gate.py) + modify __init__
Step 2:   migration + seed data     → migration + seed hook/migration
Step 3:   config updates            → modify config.py
Step 4:   gate_lifecycle service    → 1 file (services/gate_lifecycle.py)
Step 5:   wire into tick pipeline   → modify simulation/tick.py
Step 6:   schemas                   → 1 file (schemas/gate.py)
Step 7:   API routes                → 1 file (api/gates.py) + modify main.py
Step 8:   update state hash         → modify simulation/state_hash.py
Step 9:   ledger entry types        → no change needed (already defined)
Step 10:  tests                     → 2 files (test_gates.py, test_gates_api.py)
```

**Total: ~5 new files, ~5 modified files.**

---

## Key Design Decisions

| Decision                                                  | Rationale                                                                          |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Treasury UUID as shareholder for unsold shares            | Reuses existing `gate_shares` table. No new column. System is just another holder. |
| Integer division for yield pro-rata                       | Avoids float rounding issues. Remainder stays in treasury. Conservative.           |
| OFFERING period before ACTIVE                             | Gives time for Phase 5 ISO to sell shares before yield starts                      |
| Decay rate can't go negative (clamped)                    | Prevents free stability gains from RNG noise                                       |
| Gates don't yield while OFFERING                          | Shares haven't been distributed yet — no free yield to treasury self-pay           |
| Gates don't yield while UNSTABLE                          | Provides economic signal — instability hurts returns (incentivizes selling)        |
| Discovery rank upgrade is probabilistic, never guaranteed | Prevents "pay more, always get S+" exploit                                         |
| Seed rank profiles via startup hook (like treasury)       | Simple, idempotent, no separate data migration needed                              |
| State hash extended with gate data                        | Catches gate state divergence in replay tests                                      |
| Yield capped at treasury balance                          | Graceful degradation — economy slows down rather than breaking                     |

---

## Economic Impact

| Flow       | Mechanism      | Direction          |
| ---------- | -------------- | ------------------ |
| **Sink**   | Gate discovery | Player → Treasury  |
| **Faucet** | Yield payments | Treasury → Players |

First phase where money actually moves through the economy beyond registration grants.
Conservation invariant expands: treasury debited by yields, credited by discovery costs.

---

## Dependencies

- Phase 2: TransferService (for discovery cost + yield payments)
- Phase 3: Tick pipeline hooks, TickRNG, intent processing framework
- Phase 5 (future): ISO mechanism will use gate shares + market system to sell OFFERING shares
