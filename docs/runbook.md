# Dungeon Gate Economy — Runbook

## Prerequisites

- Docker Desktop
- `make`
- Optional local tools for convenience: `curl`, `jq`

## Services and Ports

- API: `http://localhost:8000`
- Postgres host port: `5433`
- Redis host port: `6380`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

## Start / Stop

```bash
make up
make down
```

`make up` boots API, worker, Postgres, Redis, Prometheus, Grafana.

## Health Checks

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/simulation/status
```

## Database Migrations

```bash
make migrate
make migration msg="describe change"
```

If migration order drifts, inspect:

```bash
docker compose exec api alembic current
docker compose exec api alembic history
```

## Test Commands

```bash
make test
docker compose exec api pytest -q
docker compose exec api pytest tests/test_admin.py -q
```

## Lint / Type Check

```bash
make lint
```

## Logs and Debug

```bash
make logs
docker compose logs -f api
docker compose logs -f worker
```

## Interactive Shells

```bash
make shell
docker compose exec api bash
docker compose exec api python -m pytest -q
```

## Observability

- Metrics endpoint: `GET /metrics`
- Prometheus target should include API container at 5s scrape interval.
- Grafana default credentials:
  - user: `admin`
  - pass: `admin`

## Pause / Resume Simulation (Admin API)

Requires admin JWT.

```bash
curl -X POST http://localhost:8000/admin/simulation/pause \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>"

curl -X POST http://localhost:8000/admin/simulation/resume \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>"
```

## Conservation Audit

```bash
curl http://localhost:8000/admin/audit/conservation \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>"
```

Expected response includes `status` (`PASS`/`FAIL`) and `delta_micro`.

## Load Test Harness (k6)

Scripts in `infra/k6`:
- `auth_load.js`
- `order_storm.js`
- `ws_connections.js`
- `mixed_workload.js`

Example:

```bash
docker run --rm -i --network host \
  -v ${PWD}/infra/k6:/scripts \
  grafana/k6 run /scripts/mixed_workload.js
```

## Reset

```bash
make reset
```

Use only when you want a full local rebuild (containers + volumes).
