# Phase 4 — Complete ✓

## Summary of What We Built

### Database Tables

| Table                  | Purpose                            | Key Constraints                                        |
| ---------------------- | ---------------------------------- | ------------------------------------------------------ |
| **gate_rank_profiles** | One row per rank — baseline params | PK = rank enum, defines stability/yield/cost/shares    |
| **gates**              | Dungeon gate instances             | UUID PK, FK to rank profile, FK to discoverer (player) |
| **gate_shares**        | Fractional gate ownership          | Composite PK (gate_id, player_id), `quantity >= 0`     |

### Enums Created

| Enum            | Values                                        |
| --------------- | --------------------------------------------- |
| `GateRank`      | `E`, `D`, `C`, `B`, `A`, `S`, `S_PLUS`        |
| `GateStatus`    | `OFFERING`, `ACTIVE`, `UNSTABLE`, `COLLAPSED` |
| `DiscoveryType` | `SYSTEM`, `PLAYER`                            |

### Gate Rank Profiles (Seed Data)

| Rank   | stability_init | volatility | yield_min | yield_max | shares | collapse_threshold | discovery_cost | spawn_weight |
| ------ | -------------- | ---------- | --------- | --------- | ------ | ------------------ | -------------- | ------------ |
| E      | 100            | 0.05       | 1,000     | 5,000     | 100    | 20                 | 100,000        | 40           |
| D      | 95             | 0.08       | 3,000     | 10,000    | 80     | 22                 | 250,000        | 25           |
| C      | 90             | 0.12       | 8,000     | 25,000    | 60     | 25                 | 500,000        | 18           |
| B      | 85             | 0.15       | 20,000    | 60,000    | 50     | 28                 | 1,000,000      | 10           |
| A      | 80             | 0.20       | 50,000    | 150,000   | 40     | 30                 | 2,500,000      | 5            |
| S      | 75             | 0.25       | 120,000   | 400,000   | 30     | 35                 | 5,000,000      | 2            |
| S_PLUS | 70             | 0.30       | 300,000   | 1,000,000 | 20     | 40                 | 10,000,000     | 1            |

### Services

| Service           | Method                      | Purpose                                                                                  |
| ----------------- | --------------------------- | ---------------------------------------------------------------------------------------- |
| **GateLifecycle** | `system_spawn_gate()`       | Roll RNG → weighted rank selection → create gate in OFFERING → assign shares to treasury |
| **GateLifecycle** | `process_discover_intent()` | Validate funds → transfer cost → roll rank upgrade → create gate                         |
| **GateLifecycle** | `advance_gate_lifecycle()`  | OFFERING→ACTIVE transition, stability decay, ACTIVE→UNSTABLE→COLLAPSED transitions       |
| **GateLifecycle** | `distribute_yield()`        | Pro-rata yield from treasury to shareholders, skipping treasury-held shares              |

### Tick Pipeline — Now Active

| Step | Action                    | Status                         |
| ---- | ------------------------- | ------------------------------ |
| 1    | Determine tick_number     | ✅ Active (Phase 3)            |
| 2    | Derive deterministic seed | ✅ Active (Phase 3)            |
| 3    | Create TickRNG            | ✅ Active (Phase 3)            |
| 4    | Insert tick record        | ✅ Active (Phase 3)            |
| 5    | Collect QUEUED intents    | ✅ Active (Phase 3)            |
| 6    | Process intents by type   | ✅ **DISCOVER_GATE active**    |
| 7    | Advance gates             | ✅ **Spawn + decay + yield**   |
| 8    | Match orders              | ⬜ No-op (Phase 5+)            |
| 9    | Roll events               | ⬜ No-op (Phase 8+)            |
| 10   | Anti-exploit maintenance  | ⬜ No-op (Phase 9+)            |
| 11   | Mark intents EXECUTED     | ✅ Active (preserves REJECTED) |
| 12   | Compute state_hash        | ✅ **Extended with gate data** |
| 13   | Finalize tick record      | ✅ Active (Phase 3)            |

### Config Additions

| Parameter                  | Value  | Purpose                                       |
| -------------------------- | ------ | --------------------------------------------- |
| `system_spawn_probability` | `0.15` | Chance per tick of system gate spawn (~3/min) |
| `gate_offering_ticks`      | `60`   | Ticks in OFFERING before transitioning ACTIVE |
| `gate_base_decay_rate`     | `0.1`  | Base stability decay per tick                 |

### API Endpoints (Cumulative)

| Method | Path                   | Auth | Phase | Purpose                                      |
| ------ | ---------------------- | ---- | ----- | -------------------------------------------- |
| `GET`  | `/health`              | No   | 1     | Health check                                 |
| `GET`  | `/ready`               | No   | 1     | DB + Redis connectivity                      |
| `POST` | `/auth/register`       | No   | 2     | Create account, grant starting balance       |
| `POST` | `/auth/login`          | No   | 2     | Returns access + refresh tokens              |
| `POST` | `/auth/refresh`        | No   | 2     | New access token from refresh token          |
| `GET`  | `/players/me`          | Yes  | 2     | Profile + balance                            |
| `GET`  | `/players/me/ledger`   | Yes  | 2     | Paginated personal ledger                    |
| `POST` | `/intents`             | Yes  | 3     | Submit intent (DISCOVER_GATE now processed)  |
| `GET`  | `/simulation/status`   | No   | 3     | Current tick, running state                  |
| `GET`  | `/gates`               | No   | **4** | List gates (filter: status, rank, paginated) |
| `GET`  | `/gates/{id}`          | No   | **4** | Gate detail + shareholder breakdown          |
| `GET`  | `/gates/rank-profiles` | No   | **4** | All 7 rank profiles (reference data)         |

### State Hash — Extended

Now covers:

- Treasury balance
- Individual player balances (ordered by ID)
- Gate counts per status
- Sum of all gate stabilities (truncated to int)
- Total shares held across all gates

### Testing

| Test File              | Tests  | Covers                                                                             |
| ---------------------- | ------ | ---------------------------------------------------------------------------------- |
| `test_health.py`       | 2      | Health + ready endpoints                                                           |
| `test_transfer.py`     | 4      | Successful transfer, insufficient balance, zero/negative amount                    |
| `test_auth.py`         | 12     | Register, login, refresh, token validation, protected routes                       |
| `test_conservation.py` | 1      | Treasury + players = INITIAL_SEED                                                  |
| `test_rng.py`          | 8      | Deterministic seeding, sequence reproducibility                                    |
| `test_lock.py`         | 5      | Acquire, double acquire, release + reacquire, wrong-worker release                 |
| `test_tick.py`         | 4      | Single tick, sequential numbering, intent collection, state hash consistency       |
| `test_replay.py`       | 2      | 5-tick replay identical (now cleans gates too), different seed → different results |
| `test_intents_api.py`  | 5      | Submit → QUEUED, all types, no auth, invalid type, missing payload                 |
| `test_gates.py`        | 12     | System spawn, player discovery, lifecycle decay/collapse, yield, conservation      |
| `test_gates_api.py`    | 7      | List gates, filters, detail + shareholders, rank profiles, 404                     |
| **Total**              | **62** | **(62 confirmed passing, 31.30s)**                                                 |

### Key Design Decisions

| Decision                                      | Rationale                                                                          |
| --------------------------------------------- | ---------------------------------------------------------------------------------- |
| Treasury UUID as shareholder in `gate_shares` | Plain UUID, no FK to players. Reuses table. System is just another holder.         |
| Skip treasury shares in yield distribution    | No self-payment. Avoids deadlock on same row. Economically identical.              |
| Integer division for pro-rata yield           | Avoids float rounding. Remainder stays in treasury. Conservative & invariant-safe. |
| OFFERING gates don't yield                    | Shares not distributed yet — prevents free yield to treasury                       |
| UNSTABLE gates don't yield                    | Economic signal — instability hurts returns, incentivizes selling                  |
| Decay rate clamped ≥ 0                        | Prevents free stability gains from Gaussian noise                                  |
| Rank upgrade probabilistic (15% per tier)     | Never guaranteed S+ from paying E-rank cost                                        |
| Seed rank profiles via startup hook           | Idempotent, same pattern as treasury seeding                                       |
| Autouse test fixture for DB reset             | Guarantees test isolation — treasury restored to INITIAL_SEED before every test    |
| Gate data in state hash                       | Catches gate state divergence in replay verification                               |
| Yield capped at treasury balance              | Graceful degradation — economy slows rather than breaking                          |

### Issues Encountered & Resolved

| Issue                                          | Cause                                                                             | Fix                                                                             |
| ---------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| 18 tests failing with `InsufficientBalance`    | `test_no_yield_when_treasury_empty` drained treasury to 0, persisted across tests | Autouse `_clean_state` fixture resets treasury to INITIAL_SEED before each test |
| `test_replay` hash divergence                  | State hash now includes gate data; gates from run 1 polluted run 2                | Clean `gate_shares` + `gates` tables between replay runs                        |
| `test_intents_collected` REJECTED not EXECUTED | DISCOVER_GATE intent now actually processes; 0-balance player gets REJECTED       | Changed test to use CREATE_GUILD + PLACE_ORDER (still no-ops in Phase 4)        |
| Test isolation across shared database          | All tests hit same Postgres; committed state leaked between tests                 | Autouse fixture wipes all data + resets treasury before every test              |
| Initial run showed 55 tests                    | `test_gates_api.py` file was not created on disk                                  | Created the file, reran → 62 passed                                             |

### Files Created or Modified (Phase 4)

```
backend/app/
├── config.py                       ← MODIFIED: +gate settings (3 params)
├── main.py                         ← MODIFIED: +seed_gate_rank_profiles, +gates router
├── models/
│   ├── __init__.py                 ← MODIFIED: registered Gate, GateRankProfile, GateShare
│   └── gate.py                     ← NEW: 3 enums + 3 models
├── schemas/
│   └── gate.py                     ← NEW: response schemas
├── api/
│   └── gates.py                    ← NEW: /gates endpoints
├── services/
│   └── gate_lifecycle.py           ← NEW: spawn, discover, decay, yield
├── simulation/
│   ├── tick.py                     ← MODIFIED: wired gate processing into pipeline
│   └── state_hash.py              ← MODIFIED: extended with gate state
├── core/
│   └── deps.py                     ← MODIFIED: +DBSession, +CurrentPlayer aliases

backend/tests/
├── conftest.py                     ← MODIFIED: autouse _clean_state fixture
├── test_tick.py                    ← MODIFIED: use no-op intent types
├── test_replay.py                  ← MODIFIED: clean gates between runs
├── test_gates.py                   ← NEW: 12 tests
└── test_gates_api.py               ← NEW: 7 tests

backend/alembic/versions/
└── 0077d445e221_add_gates_...py    ← NEW: migration
```

### Economic Impact — First Real Money Movement

| Flow       | Mechanism           | Direction          | Entry Type       |
| ---------- | ------------------- | ------------------ | ---------------- |
| **Sink**   | Gate discovery cost | Player → Treasury  | `GATE_DISCOVERY` |
| **Faucet** | Yield payments      | Treasury → Players | `YIELD_PAYMENT`  |

This is the first phase where currency actively flows through the economy beyond registration grants.

### Economic Invariant Status

```
✅ treasury_balance + SUM(player_balances) = INITIAL_SEED
   Verified by test_conservation_after_gates (10 ticks with spawn + discovery + yield).
   Test isolation guaranteed by autouse fixture.
   No guild treasuries yet (Phase 6).
```

### Architecture Checkpoint

```
Phase 1 ✅ — Foundation & Infrastructure
Phase 2 ✅ — Identity, Wallet & Ledger
Phase 3 ✅ — Simulation Engine Core
Phase 4 ✅ — Dungeon Gates
Phase 5 ⬜ — Market System                    ← NEXT
```

---

**Phase 4 acceptance criteria — all met:**

- ✅ System spawns gates over time (30 ticks, at least 1 gate)
- ✅ Player discovery deducts cost, creates gate
- ✅ Stability decays over ticks
- ✅ Gates transition ACTIVE → UNSTABLE → COLLAPSED
- ✅ Yield paid from treasury to shareholders (pro-rata, integer division)
- ✅ No yield for COLLAPSED gates
- ✅ No yield when treasury empty (graceful degradation, no error)
- ✅ Conservation invariant holds after spawn + discovery + yield
- ✅ 62 tests passing, 0 failures (31.30s)
