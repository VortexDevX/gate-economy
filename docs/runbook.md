# Dungeon Gate Economy — Operator Runbook

## Prerequisites

- Docker Desktop with Compose v2
- Node.js 20+ and npm for the frontend
- a local `.env` copied from `.env.example`

## Services

| Service | Local address |
| --- | --- |
| Exchange UI | `http://localhost:5173` |
| FastAPI | `http://localhost:8000` |
| PostgreSQL | `127.0.0.1:5433` |
| Redis | `127.0.0.1:6380` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |

## Start

```powershell
Copy-Item .env.example .env
# Replace example secrets before continuing.
docker compose up -d --build
docker compose exec api alembic upgrade head

Set-Location frontend
npm install
npm run dev
```

The frontend is intentionally run through Vite during development; it proxies
API and WebSocket traffic to the API container.

## Health

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready
Invoke-RestMethod http://localhost:8000/simulation/status
docker compose ps
```

## Database migrations

```powershell
docker compose exec api alembic current
docker compose exec api alembic history
docker compose exec api alembic upgrade head
docker compose exec api alembic revision --autogenerate -m "describe change"
```

For a migration on a busy local simulation, stop only the worker, migrate, and
restart it:

```powershell
docker compose stop worker
docker compose exec api alembic upgrade head
docker compose start worker
```

## Database browser (Prisma Studio)

SQLAlchemy models and Alembic migrations remain the schema source of truth.
Prisma Studio can be used as a local browser without adding Prisma to the app:

```powershell
$urlLine = Get-Content .env | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
$containerUrl = ($urlLine -split '=', 2)[1].Trim().Trim('"').Trim("'")
$studioUrl = $containerUrl -replace '^postgresql\+asyncpg://', 'postgresql://' -replace '@postgres:5432/', '@127.0.0.1:5433/'
npx --yes prisma@latest studio --url="$studioUrl" --port 5555
```

Open `http://localhost:5555`. Keep `SEED_AI_PLAYERS_ON_STARTUP=false` for a
user-free baseline; set it to `true` and restart the API only when the three AI
liquidity accounts are wanted.

## Tests

The backend test guard must reject the development database. Create and migrate
an isolated database once:

```powershell
docker compose exec postgres createdb -U dge dungeon_gate_test
docker compose exec api sh -lc 'export DATABASE_URL="${DATABASE_URL%/*}/dungeon_gate_test"; alembic upgrade head'
```

Run all verification:

```powershell
docker compose exec api sh -lc 'export TEST_DATABASE_URL="${DATABASE_URL%/*}/dungeon_gate_test"; pytest -q'
docker compose exec api ruff check app tests
docker compose exec api mypy app

Set-Location frontend
npm run typecheck
npm run build
```

## Logs

```powershell
docker compose logs --tail 200 api
docker compose logs --tail 200 worker
docker compose logs -f worker
```

Cycle completion and duration are emitted by the worker. Repeated cycle times
above `SIMULATION_TICK_INTERVAL` are a performance failure, even if the worker
continues to make progress.

## Admin controls

These calls require an admin access token:

```powershell
$headers = @{ Authorization = "Bearer <ADMIN_ACCESS_TOKEN>" }
Invoke-RestMethod -Method Post http://localhost:8000/admin/simulation/pause -Headers $headers
Invoke-RestMethod -Method Post http://localhost:8000/admin/simulation/resume -Headers $headers
Invoke-RestMethod http://localhost:8000/admin/audit/conservation -Headers $headers
```

The conservation response should report `PASS` with a zero delta.

## Observability

- FastAPI metrics: `GET /metrics`
- Prometheus scrapes the API container every five seconds.
- Grafana credentials come from `GF_SECURITY_ADMIN_USER` and
  `GRAFANA_ADMIN_PASSWORD`; do not rely on default passwords.

## Stop and recover

```powershell
docker compose down
docker compose up -d
```

Do not add `--volumes` unless permanent local database deletion is intentional.
