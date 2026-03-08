# Dungeon Gate Economy — Architecture

## System Overview

Dungeon Gate Economy is a simulation-first, closed-loop market game.
All world state mutations are executed by one authoritative simulation worker in deterministic ticks.

## Core Invariant

```
treasury_balance + SUM(player_balances) + SUM(guild_treasuries) = INITIAL_SEED
```

The invariant is:
- checked by tests and admin audit endpoint
- enforced at runtime each tick
- if violated, tick commit is aborted and worker sets simulation pause flag

## Core Stack

| Layer | Technology |
| --- | --- |
| API | FastAPI (async) |
| DB | PostgreSQL 15 + SQLAlchemy 2 async + Alembic |
| Cache / Coordination | Redis 7 |
| Simulation | Celery worker + beat |
| Metrics | Prometheus + Grafana |
| Load Harness | k6 scripts in `infra/k6` |

## High-Level Data Flow

1. Player submits action intent via API (`/intents`).
2. Intent is persisted as `QUEUED`.
3. Worker wakes every tick interval, checks pause flag, acquires Redis simulation lock.
4. Worker executes full tick pipeline in one DB transaction.
5. Tick commits atomically or rolls back fully.
6. After commit, worker publishes realtime summary to Redis pub/sub.
7. API websocket layer relays pub/sub messages to connected clients.

## Tick Pipeline (Current)

1. Determine `tick_number`
2. Derive deterministic seed and create `TickRNG`
3. Insert tick row
4. Load treasury + runtime tunables from `simulation_parameters`
5. Collect QUEUED intents -> PROCESSING
6. Process intents
7. Advance gates + yield
8. Guild lifecycle + AI traders
9. ISO/order maintenance + matching + market prices
10. Events + news generation
11. Anti-exploit maintenance
12. Leaderboard + season maintenance
13. Hard invariant check (abort on failure)
14. Finalize intents + state hash + tick completion
15. Commit
16. Publish realtime summary

## Determinism and Replay

- Seed chain: `seed_n = SHA256(seed_{n-1} || tick_number)` truncated to 64-bit.
- All stochastic behavior uses tick-scoped RNG.
- State hash includes major economy/state dimensions (balances, market/order activity, guild/season state).
- Replay tests verify deterministic outcomes.

## Real-time and Observability

- WebSocket endpoints:
  - `WS /ws` (public)
  - `WS /ws/feed?token=<access_jwt>` (authenticated)
- Realtime payload currently publishes `tick_update` + compact news payload.
- `/metrics` exports business metrics for Prometheus scrape.
- Grafana dashboard and Prometheus config are provisioned under `infra/`.

## Current Backend Scope

Completed backend phases:
- Phase 1 through Phase 11

Frontend work is planned in:
- `docs/plan/FRONTEND_PLAN.md`

For current schema, APIs, config, and conventions:
- use `docs/CONTEXT.md` as authoritative current-state reference.
