# Dungeon Gate Economy

An occult market game where unstable dungeon gates are income-producing,
tradable assets. Players scan yield and collapse risk, place orders into a real
price-time book, collect cycle income, discover new gates, and build guild
treasuries inside a deterministic closed economy.

The interface direction is **Arcane Exchange**: dense enough to trade from,
legible enough to learn, and tied directly to simulation truth.

## What is playable

- deterministic simulation cycles with reproducible state hashes
- gate discovery, stability decay, yield, collapse, and share ownership
- limit orders, escrow, price-time matching, fees, trade prints, and history
- player portfolio with marked value, projected yield, and unstable exposure
- sortable gate scanner with price, spread, volume, yield, and risk
- guild creation, shares, investments, maintenance, insolvency, and dividends
- AI liquidity, world events, news, seasons, leaderboards, and WebSocket updates
- admin parameters, conservation audit, metrics, Prometheus, and Grafana

The product diagnosis and prioritized roadmap live in
[`docs/PRODUCT_RESCUE.md`](docs/PRODUCT_RESCUE.md).

## Stack

| Layer | Technology |
| --- | --- |
| Simulation/API | Python 3.11, FastAPI, Pydantic, SQLAlchemy async |
| Persistence | PostgreSQL 15, Alembic |
| Cycle worker | Celery, Redis |
| Client | React 18, TypeScript, Vite, TanStack Query, Zustand |
| Operations | Docker Compose, Prometheus, Grafana |

## Run locally

Prerequisites: Docker Desktop, Node.js 20+, and npm.

```powershell
Copy-Item .env.example .env
# Replace the example passwords and JWT secret in .env.

docker compose up -d --build postgres redis api worker prometheus grafana
docker compose exec api alembic upgrade head

Set-Location frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies API and
WebSocket traffic to [http://localhost:8000](http://localhost:8000).

Useful endpoints:

- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- API health: [http://localhost:8000/health](http://localhost:8000/health)
- simulation status: [http://localhost:8000/simulation/status](http://localhost:8000/simulation/status)
- Prometheus: [http://localhost:9090](http://localhost:9090)
- Grafana: [http://localhost:3000](http://localhost:3000)

## Verify

Create a dedicated test database once. Tests intentionally refuse to run
against the development database.

```powershell
docker compose exec postgres createdb -U dge dungeon_gate_test
docker compose exec api sh -lc 'export DATABASE_URL="${DATABASE_URL%/*}/dungeon_gate_test"; alembic upgrade head'
docker compose exec api sh -lc 'export TEST_DATABASE_URL="${DATABASE_URL%/*}/dungeon_gate_test"; pytest -q'
docker compose exec api ruff check app tests
docker compose exec api mypy app

Set-Location frontend
npm run typecheck
npm run build
```

If the test database already exists, the `createdb` command can be skipped.

## Architecture

```text
React exchange UI
  |-- immediate reads --> FastAPI read models --> PostgreSQL
  |-- queued writes ----> typed intents --------> deterministic cycle
  |                                               |-- gate lifecycle
  |                                               |-- guild lifecycle
  |                                               |-- AI quotes
  |                                               |-- matching/settlement
  |                                               |-- events/news/audits
  `-- live updates <----- WebSocket / Redis <----- cycle commit
```

The backend is authoritative for fees, escrow, holdings, risk, portfolio value,
and all economic transfers. The client previews these values; it does not invent
its own economy rules.

Hard monetary invariant:

```text
system treasury + player balances + guild treasuries = initial seed
```

## Project map

```text
backend/app/api/          HTTP and WebSocket routes
backend/app/services/     economy and player-facing projections
backend/app/simulation/   deterministic cycle orchestration
backend/app/models/       SQLAlchemy state
backend/alembic/          schema migrations
backend/tests/            simulation, API, security, and invariant tests
frontend/src/features/    exchange and game screens
frontend/src/hooks/       server-state query layer
docs/                     architecture, rescue audit, plans, and runbook
infra/                    monitoring and load-test assets
```

## Operator cautions

- Run Alembic before starting a newly pulled worker revision.
- Never use the development database as `TEST_DATABASE_URL`.
- Pause the worker before high-impact database maintenance.
- Use the admin conservation endpoint after economy-rule changes.
- Treat `.env` as local secret material; commit only `.env.example`.
