# Phase 3 Sub-Plan: Simulation Engine Core

## Goal

Single Celery worker runs deterministic ticks at 5s intervals. Leadership lock guarantees single-writer. Intent queue bridges API → simulation. All future tick phases are empty hooks.

---

### Step 1 — Models (`tick.py`, `intent.py`)

| File                 | Contents                                                                                                                                                                                 |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `models/tick.py`     | `Tick` — SERIAL PK, `tick_number` (UNIQUE), `seed` BIGINT, `started_at`, `completed_at`, `intent_count`, `state_hash` VARCHAR(64)                                                        |
| `models/intent.py`   | `Intent` — UUID PK, `player_id` FK, `intent_type` ENUM, `payload` JSONB, `status` ENUM(QUEUED/PROCESSING/EXECUTED/REJECTED), `reject_reason`, `created_at`, `processed_tick` FK nullable |
| `models/__init__.py` | Add imports for both                                                                                                                                                                     |

Enums: `IntentType` (DISCOVER_GATE, PLACE_ORDER, CANCEL_ORDER, CREATE_GUILD, GUILD_DIVIDEND, GUILD_INVEST), `IntentStatus`.

---

### Step 2 — Migration

```
make migration msg="add ticks and intents"
make migrate
```

---

### Step 3 — Deterministic RNG (`simulation/rng.py`)

- `TickRNG` class wrapping `random.Random`
- `derive_seed(previous_seed, tick_number) → int` using SHA-256 truncated to 64-bit
- Constructor takes seed, exposes standard methods (random, gauss, uniform, choice, randint)
- Initial seed from `settings` (add `simulation_initial_seed` to config)
- **No `import random` anywhere else in the codebase** — enforced by convention

---

### Step 4 — Leadership Lock (`simulation/lock.py`)

- `SimulationLock` class using Redis
- `acquire(worker_id) → bool`: `SETNX sim:leader <worker_id>` with TTL=4s
- `release(worker_id)`: delete key only if value matches (Lua script for atomicity)
- Prevents two workers from running ticks concurrently

---

### Step 5 — State Hash Utility

- Function `compute_state_hash(session) → str`
- Hashes: treasury balance + sum of player balances
- SHA-256 hex digest truncated to 64 chars
- Later phases add gate states, market prices — but for now just balances
- Used for replay verification

---

### Step 6 — Tick Pipeline (`simulation/tick.py`)

Core function:

```
async def execute_tick(previous_seed: int, db_factory, redis_client) → Tick:
    1. Determine tick_number (last tick + 1, or 1 if first)
    2. Derive seed from previous_seed + tick_number
    3. Create TickRNG
    4. Insert tick record (started_at = now)
    5. Collect QUEUED intents → mark PROCESSING
    6. [NO-OP] Process intents by type (Phase 4+)
    7. [NO-OP] Advance gates (Phase 4+)
    8. [NO-OP] Match orders (Phase 5+)
    9. [NO-OP] Roll events (Phase 8+)
    10. [NO-OP] Anti-exploit maintenance (Phase 9+)
    11. Mark intents EXECUTED (none rejected yet)
    12. Compute state_hash
    13. Update tick record (completed_at, intent_count, state_hash)
    14. Return tick
```

Each no-op is a clearly named empty async function that later phases fill in. Pipeline is a single DB transaction for state mutations.

---

### Step 7 — Celery Worker (`simulation/worker.py`)

- `celery_app` with Redis broker from settings
- Single task `run_tick`:
  1. Acquire leadership lock
  2. If acquired: call `execute_tick`
  3. Release lock
  4. If not acquired: skip (log and return)
- Celery Beat config: `run_tick` every 5 seconds
- Worker concurrency = 1

---

### Step 8 — Config Updates

Add to `config.py`:

- `simulation_initial_seed: int = 42`
- `simulation_tick_interval: int = 5`
- `celery_broker_url: str` (defaults to `redis_url`)

---

### Step 9 — Intent Schema + Simulation Schema

| Schema             | Fields                                                                  |
| ------------------ | ----------------------------------------------------------------------- |
| `IntentCreate`     | `intent_type` enum, `payload` dict (validated per type in later phases) |
| `IntentResponse`   | id, intent_type, status, reject_reason, created_at, processed_tick      |
| `SimulationStatus` | current_tick, last_completed_at, is_running (bool), treasury_balance    |

---

### Step 10 — API Routes

| File                | Endpoints                                                                     |
| ------------------- | ----------------------------------------------------------------------------- |
| `api/intents.py`    | `POST /intents` (auth required) — validate type, store as QUEUED              |
| `api/simulation.py` | `GET /simulation/status` — current tick number, last completed, running state |

---

### Step 11 — Wire Everything

- Add `intents_router` and `simulation_router` to `main.py`
- Update `docker-compose.yml`: replace worker placeholder with actual Celery worker + beat
- Add Celery-related entries to `.env` if needed

---

### Step 12 — Tests

| Test File             | Cases                                                                                                                                                                                           |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_rng.py`         | Same seed → same sequence. Different seeds → different sequences. `derive_seed` is deterministic.                                                                                               |
| `test_tick.py`        | Execute 1 tick → tick record created with correct number/seed/hash. Execute 3 ticks → sequential numbering. Intents collected and marked PROCESSING→EXECUTED. State hash matches recomputation. |
| `test_replay.py`      | Run 5 ticks with fixed seed → record hashes. Run 5 ticks again with same seed → identical hashes.                                                                                               |
| `test_lock.py`        | Acquire succeeds first time. Second acquire fails. Release + re-acquire works.                                                                                                                  |
| `test_intents_api.py` | Submit intent → 201, appears as QUEUED. Submit without auth → 401/403. Invalid type → 422.                                                                                                      |

---

## Execution Order

```
Step 1:   models              → 3 files (tick, intent, __init__)
Step 2:   migration           → commands only
Step 3:   simulation/rng.py   → 1 file
Step 4:   simulation/lock.py  → 1 file
Step 5:   state hash util     → 1 file (inside simulation/ or core/)
Step 6:   simulation/tick.py  → 1 file
Step 7:   simulation/worker.py → 1 file
Step 8:   config.py           → modify
Step 9:   schemas              → 2 files
Step 10:  api routes           → 2 files
Step 11:  wire + docker        → modify main.py + docker-compose.yml
Step 12:  tests                → 5 files
```

**Total: ~12 new files, ~4 modified files.**

---

## Key Design Decisions

| Decision                                                     | Rationale                                                          |
| ------------------------------------------------------------ | ------------------------------------------------------------------ |
| NullPool in tests stays                                      | Proven to work in Phase 2, no reason to change                     |
| Tick pipeline is one function with hook calls                | Easy to extend in Phase 4+ without restructuring                   |
| Celery beat for scheduling, not `while True` loop            | Standard, restart-safe, observable                                 |
| Worker concurrency=1                                         | Single-writer invariant — leadership lock is backup safety         |
| State hash covers only balances for now                      | Minimal but extendable. Each phase adds its state to the hash      |
| Intents validated loosely now, strictly per-type in Phase 4+ | Avoids building intent processors that have nothing to process yet |
