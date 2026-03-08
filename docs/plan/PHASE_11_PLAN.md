# Phase 11 Sub-Plan: Admin & Observability

## Goal

Deliver operator controls and observability exactly as defined in `docs/plan/PLAN.md` Phase 11:

- Admin API for tuning and intervention
- Prometheus metrics exposure
- Grafana dashboards
- k6 load-test harness

---

## Source of Truth

This sub-plan is intentionally aligned to `PLAN.md` Phase 11.
If any wording here conflicts with `PLAN.md`, follow `PLAN.md`.

---

## Economic Flows Introduced

No new baseline economy flow types are introduced in Phase 11.

- Existing ledger flow used: `ADMIN_ADJUSTMENT` (already present in `EntryType`)
- Any manual balance intervention must use `transfer()` and ledger entries
- Conservation invariant remains mandatory

---

## Step 1 — Data Model + Migration

### Add `simulation_parameters` table

```sql
simulation_parameters
  key             VARCHAR PK
  value           VARCHAR NOT NULL
  value_type      ENUM('INT','FLOAT','BOOL','STRING')
  description     TEXT
  updated_at      TIMESTAMPTZ
  updated_by      UUID NULL FK → players
```

### Player admin authorization model

- Admin API is protected by player role: `role = ADMIN`
- Ensure player role support exists in model/migration path used by your codebase
- Keep this additive (no gameplay schema regression)

### Seed behavior

- Seed `simulation_parameters` with all tunable runtime parameters
- Simulation reads these at tick start
- Use Redis cache/invalidation if implemented, but DB remains source of truth

---

## Step 2 — Admin Auth Dependency

Create `core/admin.py` (or equivalent dependency module):

```python
async def require_admin(current_player = Depends(get_current_player)):
    if current_player.role != PlayerRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_player
```

Notes:

- No API-key auth in Phase 11
- Reuse existing player auth/JWT path

---

## Step 3 — Admin Parameter Service

Create `services/admin.py` with parameter operations backed by `simulation_parameters`.

### Required operations

1. `list_parameters(session)`:
   - return all parameter rows with typed values
1. `update_parameter(session, key, raw_value, updated_by)`:
   - reject unknown key
   - type-cast by `value_type`
   - persist value, `updated_at`, `updated_by`
1. Runtime propagation:
   - parameter updates reflected within at most one tick

### Guardrails

- Whitelist only gameplay/runtime tunables
- Never expose DB/JWT/infra secrets as runtime-tunable

---

## Step 4 — Simulation Control Service

Implement pause/resume and admin intervention endpoints behavior.

### Pause/Resume mechanism

- Redis pause flag key: `simulation:paused`
- Pause: set flag
- Resume: clear flag
- Worker checks pause flag each cycle and skips tick while paused

### Conservation audit

- Add explicit admin audit operation returning pass/fail + computed totals
- Output should include treasury, player sum, guild sum, expected `INITIAL_SEED`, delta

### Manual event + season intervention

- Support admin-triggered event endpoint (`/admin/events/trigger`)
- Support admin season control endpoint (`/admin/seasons`) per main plan

---

## Step 5 — Admin API Router

Create `api/admin.py` and register in `main.py`.

### Endpoints (must match `PLAN.md`)

| Method | Path                        | Purpose                                  |
| ------ | --------------------------- | ---------------------------------------- |
| POST   | `/admin/simulation/pause`   | Pause tick loop                          |
| POST   | `/admin/simulation/resume`  | Resume tick loop                         |
| GET    | `/admin/parameters`         | List all parameters                      |
| PATCH  | `/admin/parameters/{key}`   | Update one parameter                     |
| POST   | `/admin/events/trigger`     | Manually trigger event                   |
| GET    | `/admin/treasury`           | Treasury balance + recent flows          |
| GET    | `/admin/audit/conservation` | Run conservation audit, return PASS/FAIL |
| GET    | `/admin/ledger`             | Query ledger with filters                |
| POST   | `/admin/seasons`            | Create/end season                        |

### Auth

- All admin endpoints require authenticated ADMIN player via dependency

---

## Step 6 — Worker Update

Update `simulation/worker.py`:

- Check `simulation:paused` before lock/tick execution
- If paused, log skip and return
- Preserve existing lock safety and error handling

---

## Step 7 — Metrics (`/metrics`)

Expose Prometheus metrics and ensure names/types match `PLAN.md`.

| Metric                       | Type      |
| ---------------------------- | --------- |
| `dge_tick_duration_seconds`  | histogram |
| `dge_tick_number`            | gauge     |
| `dge_intent_queue_depth`     | gauge     |
| `dge_active_players_total`   | gauge     |
| `dge_treasury_balance_micro` | gauge     |
| `dge_trade_volume_micro`     | counter   |
| `dge_active_gates_total`     | gauge     |
| `dge_ws_connections`         | gauge     |
| `dge_order_book_depth`       | gauge     |
| `dge_events_fired_total`     | counter   |

Implementation notes:

- HTTP instrumentation can use `prometheus-fastapi-instrumentator`
- Business metrics may be DB-backed or event-updated, but endpoint output must include the required metric names

---

## Step 8 — Grafana + Prometheus Infra

### Prometheus

- Ensure scrape target includes API `/metrics`
- Keep scrape interval suitable for 5s tick cadence

### Grafana

- Provision dashboard JSON via Docker volume mount
- Include panels covering simulation health, economy, throughput, and latency

---

## Step 9 — k6 Load Tests

Create scripts matching `PLAN.md`:

| Script              | Scenario                                              |
| ------------------- | ----------------------------------------------------- |
| `auth_load.js`      | 1,000 concurrent registrations + logins               |
| `order_storm.js`    | 500 concurrent users placing orders every tick        |
| `ws_connections.js` | 1,000 WebSocket connections, measure delivery latency |
| `mixed_workload.js` | 60% read, 30% orders, 10% discovery                   |

Targets:

- p99 API < 500ms
- p99 WS delivery < 1s

---

## Step 10 — Tests

Create `tests/test_admin.py` (and related metric/integration tests).

### Required test groups

1. Admin auth/authorization:
   - non-admin blocked
   - admin allowed
1. Parameter API:
   - list parameters
   - update parameter success
   - invalid key/type rejected
1. Simulation control:
   - pause/resume behavior
   - worker skip while paused
1. Conservation audit:
   - endpoint returns PASS on healthy state
   - returns FAIL when state is intentionally perturbed (if test harness allows)
1. Treasury and ledger admin views:
   - filters/pagination correctness
1. Events and seasons admin intervention:
   - trigger and season controls behave as expected
1. Metrics:
   - `/metrics` exposed and includes required names

---

## Execution Order

1. Migration + model updates (`simulation_parameters`, role support)
1. Admin auth dependency
1. Admin service layer (parameters, treasury/audit/ledger helpers, intervention helpers)
1. Admin router endpoints
1. Worker pause-flag integration
1. Metrics exposure
1. Prometheus/Grafana wiring
1. k6 scripts
1. Tests

---

## Dependencies

- All prior phases
- Existing auth and transfer services
- Tick worker + lock + Redis
- Ledger/trade/gate/guild/season data paths

---

## Acceptance Criteria (Phase 11)

- Admin can pause/resume simulation via API
- Parameter changes reflected within 1 tick
- Conservation audit endpoint returns PASS/FAIL
- Prometheus endpoint returns required metrics
- Grafana dashboard renders
- k6 runs at target concurrency and latency thresholds from `PLAN.md`
