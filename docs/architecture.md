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

## Phase Status

- [x] Phase 1 — Foundation & Infrastructure
- [ ] Phase 2 — Identity, Wallet & Ledger
- [ ] Phase 3 — Simulation Engine Core
