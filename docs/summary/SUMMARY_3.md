# Phase 3 — Complete ✓

## Summary of What We Built

### Database Tables

| Table       | Purpose                         | Key Constraints                                                     |
| ----------- | ------------------------------- | ------------------------------------------------------------------- |
| **ticks**   | One row per simulation tick     | `tick_number` UNIQUE, tracks seed, timing, state_hash for replay    |
| **intents** | Player action queue (API → sim) | UUID PK, FK to players + ticks, JSONB payload, status state machine |

### Enums Created

| Enum           | Values                                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------ |
| `IntentType`   | `DISCOVER_GATE`, `PLACE_ORDER`, `CANCEL_ORDER`, `CREATE_GUILD`, `GUILD_DIVIDEND`, `GUILD_INVEST` |
| `IntentStatus` | `QUEUED`, `PROCESSING`, `EXECUTED`, `REJECTED`                                                   |

### Simulation Components

| Component          | File                       | Purpose                                                                                         |
| ------------------ | -------------------------- | ----------------------------------------------------------------------------------------------- |
| **TickRNG**        | `simulation/rng.py`        | Deterministic RNG wrapping `random.Random`. Seed derived via SHA-256 from previous seed + tick. |
| **SimulationLock** | `simulation/lock.py`       | Redis SETNX lock with 4s TTL + Lua-script atomic release. Guarantees single-writer.             |
| **State Hash**     | `simulation/state_hash.py` | SHA-256 of treasury + all player balances (ordered by ID). Used for replay verification.        |
| **Tick Pipeline**  | `simulation/tick.py`       | Core `execute_tick()` — collects intents, runs hooks, computes hash, commits atomically.        |
| **Celery Worker**  | `simulation/worker.py`     | Celery app with beat schedule (5s). Acquires lock → runs tick → releases lock. Concurrency=1.   |

### Tick Pipeline Steps

| Step | Action                    | Status              |
| ---- | ------------------------- | ------------------- |
| 1    | Determine tick_number     | ✅ Active           |
| 2    | Derive deterministic seed | ✅ Active           |
| 3    | Create TickRNG            | ✅ Active           |
| 4    | Insert tick record        | ✅ Active           |
| 5    | Collect QUEUED intents    | ✅ Active           |
| 6    | Process intents by type   | ⬜ No-op (Phase 4+) |
| 7    | Advance gates             | ⬜ No-op (Phase 4+) |
| 8    | Match orders              | ⬜ No-op (Phase 5+) |
| 9    | Roll events               | ⬜ No-op (Phase 8+) |
| 10   | Anti-exploit maintenance  | ⬜ No-op (Phase 9+) |
| 11   | Mark intents EXECUTED     | ✅ Active           |
| 12   | Compute state_hash        | ✅ Active           |
| 13   | Finalize tick record      | ✅ Active           |

### API Endpoints (Cumulative)

| Method | Path                 | Auth | Phase | Purpose                                |
| ------ | -------------------- | ---- | ----- | -------------------------------------- |
| `GET`  | `/health`            | No   | 1     | Health check                           |
| `GET`  | `/ready`             | No   | 1     | DB + Redis connectivity                |
| `POST` | `/auth/register`     | No   | 2     | Create account, grant starting balance |
| `POST` | `/auth/login`        | No   | 2     | Returns access + refresh tokens        |
| `POST` | `/auth/refresh`      | No   | 2     | New access token from refresh token    |
| `GET`  | `/players/me`        | Yes  | 2     | Profile + balance                      |
| `GET`  | `/players/me/ledger` | Yes  | 2     | Paginated personal ledger              |
| `POST` | `/intents`           | Yes  | 3     | Submit intent (stored as QUEUED)       |
| `GET`  | `/simulation/status` | No   | 3     | Current tick, running state, treasury  |

### Config Additions (Phase 3)

| Parameter                  | Value                  | Purpose                           |
| -------------------------- | ---------------------- | --------------------------------- |
| `simulation_initial_seed`  | `42`                   | Starting seed for RNG chain       |
| `simulation_tick_interval` | `5` (seconds)          | Wall-clock interval between ticks |
| `celery_broker_url`        | `redis://redis:6379/0` | Celery broker                     |

### Docker Compose Changes

| Service    | Before (Phase 2)             | After (Phase 3)                                                        |
| ---------- | ---------------------------- | ---------------------------------------------------------------------- |
| **worker** | `sleep infinity` placeholder | `celery -A app.simulation.worker:celery_app worker -B --concurrency=1` |

### Testing

| Test File              | Tests  | Covers                                                                                   |
| ---------------------- | ------ | ---------------------------------------------------------------------------------------- |
| `test_health.py`       | 2      | Health + ready endpoints                                                                 |
| `test_transfer.py`     | 4      | Successful transfer, insufficient balance, zero/negative amount                          |
| `test_auth.py`         | 12     | Register, login, refresh, token validation, protected routes                             |
| `test_conservation.py` | 1      | Treasury + players = INITIAL_SEED after 5 registrations                                  |
| `test_rng.py`          | 8      | Deterministic seeding, sequence reproducibility, all RNG methods                         |
| `test_lock.py`         | 5      | Acquire, double acquire, release + reacquire, wrong-worker release, expired release      |
| `test_tick.py`         | 4      | Single tick, sequential numbering, intent collection, state hash consistency             |
| `test_replay.py`       | 2      | 5-tick replay identical, different seed → different results                              |
| `test_intents_api.py`  | 5      | Submit → QUEUED, all types accepted, no auth rejected, invalid type 422, missing payload |
| **Total**              | **43** |                                                                                          |

### Postman Collection

- `docs/postman/DungeonGateEconomy.postman_collection.json`
- Covers all endpoints through Phase 3
- Auto-sets tokens on login for authenticated requests
- All 17 Postman tests passing

### Key Design Decisions

| Decision                         | Rationale                                                                               |
| -------------------------------- | --------------------------------------------------------------------------------------- |
| NullPool per tick in worker      | `asyncio.run()` creates new event loop per task — persistent pools bind to wrong loop   |
| Celery Beat embedded (`-B`)      | Single process for scheduling + execution. Simple for dev.                              |
| Lua script for lock release      | Prevents releasing another worker's lock after TTL expiry                               |
| State hash covers balances only  | Minimal but deterministic. Extended in future phases with gates, market state           |
| Intents validated loosely        | Per-type payload validation added in Phase 4+ when processors exist                     |
| All tick mutations in one commit | Atomic — entire tick succeeds or nothing changes                                        |
| `pause_simulation` test fixture  | Holds Redis lock during tests to prevent worker interference with tick-level assertions |

### Files Created or Modified (Phase 3)

```

backend/app/
├── config.py ← MODIFIED: +simulation +celery settings
├── main.py ← MODIFIED: +intents +simulation routers
├── models/
│ ├── **init**.py ← MODIFIED: registered Tick + Intent
│ ├── tick.py ← NEW
│ └── intent.py ← NEW
├── schemas/
│ ├── intent.py ← NEW
│ └── simulation.py ← NEW
├── api/
│ ├── intents.py ← NEW
│ └── simulation.py ← NEW
├── simulation/
│ ├── **init**.py ← EXISTS (empty)
│ ├── rng.py ← NEW
│ ├── lock.py ← NEW
│ ├── state_hash.py ← NEW
│ ├── tick.py ← NEW
│ └── worker.py ← NEW
backend/tests/
├── conftest.py ← MODIFIED: +session_factory +redis +pause +test_player
├── test_rng.py ← NEW
├── test_lock.py ← NEW
├── test_tick.py ← NEW
├── test_replay.py ← NEW
└── test_intents_api.py ← NEW

docker-compose.yml ← MODIFIED: worker runs Celery
alembic/versions/
└── <hash>\_add_ticks_and_intents.py ← NEW: migration

docs/
├── postman/
│ └── DungeonGateEconomy.postman_collection.json ← NEW
└── summary/
└── SUMMARY_3.md ← NEW

```

### Economic Invariant Status

```

✅ treasury_balance + SUM(player_balances) = INITIAL_SEED
Holds — Phase 3 adds no faucets or sinks.
Ticks run continuously without disturbing balances.
State hash verifies balance integrity every tick.
No guild treasuries yet (Phase 6).

```

### Architecture Checkpoint

```

Phase 1 ✅ — Foundation & Infrastructure
Phase 2 ✅ — Identity, Wallet & Ledger
Phase 3 ✅ — Simulation Engine Core
Phase 4 ⬜ — Dungeon Gates ← NEXT

```

---

**Phase 3 acceptance criteria — all met:**

- ✅ Ticks advance every ~5s
- ✅ Only one tick runs at a time (leadership lock verified)
- ✅ Intents submitted via API appear in next tick's collection
- ✅ Replaying tick N with same seed + same intents produces same state_hash
- ✅ Tick records are sequential with no gaps
- ✅ 43 tests passing (8 RNG + 5 lock + 4 tick + 2 replay + 5 intent API + 19 prior)
- ✅ All Postman tests passing
