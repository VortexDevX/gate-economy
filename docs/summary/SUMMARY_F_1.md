## What the problem is

You currently have **two different backend issues**, and they interact in a way that makes the frontend look broken.

---

### 1. The simulation is not actually running anymore

This is the main issue.

From the worker logs:

- Tick **8** completed successfully
- Tick **9** completed successfully
- On the next real tick, the worker logged:

`tick_halted_invariant_violation`

That means the backend’s **money conservation invariant** failed.

Your hard invariant is:

```text
treasury_balance + SUM(player_balances) + SUM(guild_treasuries) = INITIAL_SEED
```

So after some operation inside the tick pipeline, total money no longer matched the original seeded amount.

When that happens, the worker is designed to do this:

- catch `InvariantViolationError`
- set Redis key:

```text
simulation:paused = 1
```

- stop advancing the world

That is exactly what happened.

After that, Beat still schedules tasks every 5 seconds, but each task exits immediately because it sees the pause flag. That’s why later tasks show runtimes like:

- `0.005s`
- `0.007s`

Those are **skip ticks**, not real simulation ticks.

---

### 2. Why the dashboard says “Stopped”

Because `/simulation/status` checks whether a tick completed recently.

Your API reported:

```json
{
  "current_tick": 9,
  "last_completed_at": "2026-03-08T10:54:30.425702Z",
  "is_running": false,
  "treasury_balance": 96490079767
}
```

That means:

- the **last completed tick** is still 9
- no new real tick has completed since then
- once enough wall-clock time passed, the API correctly marked simulation as `false`

So the dashboard is not wrong. It is accurately reflecting that the worker halted itself.

---

### 3. Why your orders don’t appear

Because the frontend only submits **intents**, not final outcomes.

When you place an order, the UI sends:

- `PLACE_ORDER` intent

That intent sits in the queue until the **next simulation tick** processes it.

But right now:

- simulation is paused
- queued intents are not being processed
- so no actual order record gets created from them

So the frontend behavior is:

- correct
- but blocked by the backend halt

---

### 4. The metrics endpoint is also broken, but that is separate

This error:

```text
TypeError: unsupported operand type(s) for +=: 'float' and 'decimal.Decimal'
```

comes from `/metrics`, specifically this line:

```python
dge_trade_volume_micro.inc(trade_volume_total - _last_trade_volume_total)
```

`trade_volume_total` is coming from SQL `SUM(...)`, which PostgreSQL/SQLAlchemy may return as a `Decimal`.

But Prometheus counters expect a `float`.

So `/metrics` is crashing due to a **type mismatch**.

Important:

- this does **not** appear to be the cause of the simulation halt
- it is a separate API bug
- but it adds noise to logs

---

## What likely caused the invariant violation

Based on the logs, the failure happened right after:

- a new gate was created
- an ISO order was created for that gate

Specifically:

- tick 10-ish path:
  - `gate_created`
  - `iso_order_created`
  - then immediately:
  - `tick_halted_invariant_violation`

That strongly suggests the bug is somewhere in one of these money/share flows:

- **gate spawn + ISO setup**
- **ISO escrow / settlement**
- **trade matching for ISO orders**
- **share issuance / treasury-side order logic**

Most likely categories:

1. **Money counted twice**
   - e.g. treasury receives ISO proceeds in state and also through ledger/escrow path

2. **Money created or lost during escrow**
   - e.g. escrow lock/release/settlement path not netting correctly

3. **ISO special-case logic incorrect**
   - because ISO seller is treasury/system, and those flows are easy to mishandle

4. **Invariant check bug**
   - less likely, but still possible if the runtime audit excludes/includes something incorrectly

I can’t say which one exactly without inspecting:

- `simulation/tick.py`
- `services/order_matching.py`
- `services/gate_lifecycle.py`

---

# SUMMARY of what we did in this instance

## 1. Loaded full project context

You gave me:

- full backend phase status through Phase 11
- canonical schema
- tick pipeline
- API inventory
- config values
- conventions and patterns
- folder structure
- master `PLAN.md`
- `FRONTEND_PLAN.md`

I absorbed all of it and aligned to the current backend truth.

---

## 2. Started Phase 12 frontend implementation

We began with **M1 — App Foundation + Auth**.

### Files/config scaffolded

We created the frontend foundation:

- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/tsconfig.json`
- `frontend/tailwind.config.js`
- `frontend/postcss.config.js`
- `frontend/index.html`
- `frontend/src/vite-env.d.ts`
- `frontend/src/index.css`
- `frontend/src/main.tsx`

### Core frontend stack wired

Using the approved stack:

- React 18
- TypeScript
- Vite
- TailwindCSS
- React Router
- Axios
- React Query
- Zustand

### Auth layer implemented

We added:

- typed auth/player API contracts
- Axios client
- token storage
- auth header injection
- refresh-token interceptor
- Zustand auth store

### M1 pages/components built

We implemented:

- Login page
- Register page
- Dashboard shell
- Protected route
- Auth bootstrap flow
- App layout and routing
- Makefile frontend commands

You tested it and confirmed it worked.

---

## 3. Implemented M2 — Core Read Views

After requesting backend contracts for gates/news/events/simulation, we added:

### API wrappers and hooks

- gates API
- news API
- events API
- simulation status API
- player ledger API
- React Query hooks for all of the above

### Shared utilities/components

- formatting helpers
- loading spinner
- error alert
- empty state
- pagination
- badge/status components

### Read pages

We built:

- Dashboard with:
  - simulation status
  - treasury display
  - latest news preview
- Gates list page
- Gate detail page
- Profile page with ledger
- News page
- Events page
- Navigation/sidebar updates
- Route registration for all pages

You tested and confirmed M2 worked.

---

## 4. Implemented M3 — Trading UX

After requesting market/order/intent backend files, we added:

### Market/order API layer

- market price API
- order book API
- trades API
- my orders API
- intent submission API

### React Query hooks

- market price
- order book
- trades
- my orders
- submit intent mutation

### Trading UI

We built:

- `OrderBook`
- `TradeHistory`
- `OrderForm`
- `OrdersPage`

### Gate detail upgraded

The gate detail page now includes:

- market stats
- order book
- trade history
- buy/sell order form

### Dashboard/order updates

We also updated:

- dashboard active orders preview
- sidebar with Orders page
- routes for `/orders`

---

## 5. Fixed SPA refresh/navigation proxy bug

You reported that refreshing certain pages showed raw backend JSON instead of the React app.

Example:

- `/gates`
- `/gates/{id}`

Cause:

- Vite proxy was forwarding browser navigation requests to backend endpoints

Fix:

- updated `frontend/vite.config.ts`
- added HTML request bypass logic so:
  - browser navigation gets `index.html`
  - API XHR/fetch still proxies to backend

That solved the “raw JSON on refresh” issue.

---

## 6. Improved order visibility behavior

You reported that newly submitted orders didn’t show up on Orders page/dashboard.

We diagnosed:

- frontend submits **intents**
- actual orders appear only after next simulation tick
- queries were not refetching appropriately

Fixes we made:

- added polling/refetch intervals for:
  - orders
  - simulation status
  - gates
  - market data
- added delayed invalidation after successful intent submission
- updated order form messaging to clarify:
  - order is queued
  - it appears after next tick

This frontend change was correct, but then we discovered the deeper backend simulation halt.

---

## 7. Diagnosed simulation halt

You reported:

- dashboard shows simulation as stopped
- orders never process

We investigated and found:

### Pause flag existed

Redis had:

```text
simulation:paused = "1"
```

We cleared it.

### Worker still stopped shortly after

After restarting worker and checking logs, we found:

- simulation resumed briefly
- ticks 8 and 9 completed
- next tick hit `tick_halted_invariant_violation`
- worker re-set the pause flag
- all later ticks became fast skips

Conclusion:

- the real root problem is a **backend conservation invariant failure**

---

## 8. Diagnosed metrics bug

You also shared API logs showing `/metrics` crashing with:

```text
TypeError: unsupported operand type(s) for +=: 'float' and 'decimal.Decimal'
```

We identified:

- SQL aggregate values are returning `Decimal`
- Prometheus client expects `float`

I provided a patch for:

- `backend/app/api/metrics.py`

to cast those values before using `.inc()` / `.set()`.

---

# Current status right now

## Frontend

Frontend is in a strong state through most of:

- M1 complete
- M2 complete
- M3 mostly complete

UI pieces are working structurally.

## Blocker

The current blocker is backend-side:

- simulation halts itself due to invariant violation
- once halted, intents never process
- therefore trading UX cannot function end-to-end
