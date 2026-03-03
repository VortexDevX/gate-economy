# Dungeon Gate Economy — Architecture

## System Overview

Simulation-first, market-driven game with a closed-loop economy.
Single authoritative simulation worker advances the world in discrete 5-second ticks.

## Core Invariant

```

treasury_balance + SUM(player_balances) + SUM(guild_treasuries) = INITIAL_SEED

```

Verified every tick. Violation halts simulation.

## Tech Stack

| Layer      | Technology                         |
| ---------- | ---------------------------------- |
| API        | FastAPI (async)                    |
| Database   | PostgreSQL 15 + SQLAlchemy 2 async |
| Cache/Pub  | Redis 7                            |
| Simulation | Celery + Redis broker              |
| Frontend   | React + TypeScript + Vite          |
| Infra      | Docker Compose                     |

## Data Flow

```

Player → API (submit intent) → DB (intents table, QUEUED)
↓
Celery Beat (5s) → Worker → acquire Redis lock
↓
Tick Pipeline (single DB transaction): 1. Determine tick_number 2. Derive seed (SHA-256 chain) 3. Collect QUEUED intents → PROCESSING 4. [Phase 4+] Process intents by type 5. [Phase 4+] Advance gates 6. [Phase 5+] Match orders 7. [Phase 8+] Roll events 8. [Phase 9+] Anti-exploit maintenance 9. Mark intents EXECUTED/REJECTED 10. Compute state_hash 11. Commit all mutations atomically
↓
Release lock → log tick_completed

```

## Determinism Model

- RNG chain: `seed_n = SHA256(seed_{n-1} || tick_number)` truncated to 64-bit
- Initial seed configurable (`simulation_initial_seed`, default 42)
- `TickRNG` wraps `random.Random` — no bare `import random` allowed elsewhere
- Given same initial seed + same intents → identical state hashes (verified by replay tests)

## Leadership Lock

- Redis `SETNX` with 4s TTL on key `sim:leader`
- Lua-script atomic release (compare-and-delete)
- Worker concurrency = 1 (Celery setting)
- Lock is backup safety — single worker is the primary guarantee

## Database Tables

| Table             | Phase | Purpose                         |
| ----------------- | ----- | ------------------------------- |
| `players`         | 2     | Player accounts with wallet     |
| `system_accounts` | 2     | Treasury (singleton)            |
| `ledger_entries`  | 2     | Append-only audit trail         |
| `ticks`           | 3     | One row per simulation tick     |
| `intents`         | 3     | Player action queue (API → sim) |

## API Endpoints

| Method | Path                 | Auth | Phase | Purpose                          |
| ------ | -------------------- | ---- | ----- | -------------------------------- |
| `GET`  | `/health`            | No   | 1     | Health check                     |
| `GET`  | `/ready`             | No   | 1     | DB + Redis connectivity          |
| `POST` | `/auth/register`     | No   | 2     | Create account + starting grant  |
| `POST` | `/auth/login`        | No   | 2     | JWT access + refresh tokens      |
| `POST` | `/auth/refresh`      | No   | 2     | New access token                 |
| `GET`  | `/players/me`        | Yes  | 2     | Profile + balance                |
| `GET`  | `/players/me/ledger` | Yes  | 2     | Paginated personal ledger        |
| `POST` | `/intents`           | Yes  | 3     | Submit intent (stored as QUEUED) |
| `GET`  | `/simulation/status` | No   | 3     | Current tick, running state      |

## Phase Status

- [x] Phase 1 — Foundation & Infrastructure
- [x] Phase 2 — Identity, Wallet & Ledger
- [x] Phase 3 — Simulation Engine Core
- [ ] Phase 4 — Dungeon Gates
- [ ] Phase 5 — Market System
