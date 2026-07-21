# Dungeon Gate Economy — Product Rescue

Date: 2026-07-18

## Verdict

The project already had a serious deterministic economy: gates, yields, order
matching, guilds, AI traders, events, seasons, conservation checks, and operator
controls. It felt small and dull because most of that depth was hidden behind
anonymous UUIDs, generic CRUD screens, delayed intents with weak feedback, and
read APIs that forced the client to reconstruct game state.

The rescue direction is **Arcane Exchange**: an occult commodities exchange,
not an admin dashboard. The player should be able to answer four questions in
seconds:

1. What is moving?
2. What does it yield?
3. How close is it to collapse?
4. What can I do before the next cycle?

## Root Causes

| Priority | Finding | Player impact | Rescue |
| --- | --- | --- | --- |
| P0 | AI traders cancelled and recreated quotes across every gate each tick; matching and market snapshots repeated per asset; state hashing serialized all historical orders and trades. | A configured five-second cycle took tens of seconds as history grew. Actions felt inert and the world felt dead. | Bounded rotating AI coverage, set-wise matching and pricing, bounded state hashing, and hot-path indexes. |
| P0 | There was no portfolio or market overview read model. | The frontend could not show net worth, exposure, yield, risk, or a useful scanner without many requests and client-side guesses. | Added authoritative portfolio, market scanner, per-cycle price history, and exact order preview projections. |
| P1 | New guilds paid their entire founding cost to the system and faced maintenance immediately with an empty treasury. Player discoveries paid a fee while giving the finder no allocation. | Two headline progression actions were economically irrational. | Seed guild operating capital with the founding payment, add lifecycle grace, and allocate a configurable finder share on discovery while preserving conservation. |
| P1 | Intent payloads were untyped JSON accepted at the API boundary. | A malformed action could survive until the simulation tick and poison or reject work late. | Validate every intent type with discriminated Pydantic payload models; malformed actions now fail with 422 before queueing. |
| P1 | Authentication stored a stale player snapshot and logout left cached private queries alive. | Balances and roles could look wrong after actions or between accounts. | Sync `/players/me` into auth state and clear the query cache on logout. |
| P1 | The interface used anonymous entities, a route launcher, flat cards, and generic blue SaaS styling. | The product looked like a developer console instead of a trading game. | Added deterministic gate names/tickers, exchange navigation, dense market hierarchy, a Gate Pulse risk/yield module, and responsive order-book interactions. |
| P2 | UI copy exposed database tick IDs and assumed a fixed six-second cycle. The order ticket estimated fees locally and capped quantity from visible asks. | Chronology, cost, and legal order size could be wrong. | Expose logical cycle numbers, remove fixed timing claims, and use the server's exact escrow/fee/share preview. |

## Recovered Core Loop

```text
SCAN                         COMMIT
yield + price + spread       exact fee + escrow
stability + collapse risk -> buy / sell / discover
        ^                         |
        |                         v
REACT                        RESOLVE
rebalance / exit / compound  next deterministic cycle
guild / season goals         fill / yield / event / collapse
```

The **Gate Pulse** is the visual anchor for that loop. It combines status,
stability, collapse threshold, effective yield, share yield, mark, spread, and
recent per-cycle price action. Risk is no longer a decorative badge separated
from the trade decision.

## Backend Changes

### Player-facing projections

- `GET /players/me/portfolio`
  - cash and reserved cash
  - gate and guild market value
  - net worth
  - projected yield per cycle
  - unstable exposure
  - marked positions with bid/ask, ownership, and risk bands
- `GET /market/overview`
  - comparable gate instruments
  - deterministic ticker and lore name
  - mark, yield rate, spread, volume, stability distance, and risk band
  - filtering, ranking, and bounded pagination
- `GET /market/{asset_type}/{asset_id}/history`
  - logical-cycle OHLC, average price, volume, and trade count
- `POST /market/order-preview`
  - authoritative gross, fee, escrow, spendable cash, sellable shares, and
    rejection reason without mutating state

### Simulation hardening

- Every intent payload is validated before it enters the queue.
- AI quote refresh rotates across a deterministic bounded gate batch.
- Order matching locks open books once and applies stable price-time-ID order.
- Market snapshots aggregate bids, asks, last trades, and volume set-wise.
- State hashes retain current economic state and aggregate historical trade
  count without serializing all closed order and trade rows every cycle.
- Alembic adds partial/open-book and recent-history indexes for the actual hot
  queries.
- News, events, and trades expose the simulation's logical cycle number.

## Frontend Changes

- Exchange dashboard replaces the route launcher with account exposure,
  projected yield, market breadth, actionable movers, and a compact news tape.
- Gate scanner compares yield, risk, price, spread, volume, status, and rank.
- Gate detail becomes a trading workstation with Gate Pulse, history, book,
  prints, and the exact order ticket in one decision surface.
- Navigation is grouped around Exchange, Operations, Guilds, Intelligence, and
  account actions.
- Anonymous gate UUIDs are presented as stable exchange tickers and lore names;
  IDs remain available only as secondary identity.
- Order-book rows support keyboard selection; mobile and reduced-motion states
  are explicit.

## Architecture Boundary

The simulation remains the source of truth. The frontend does not calculate
fees, ownership availability, collapse risk, or portfolio value independently.
Write actions still enter the deterministic intent queue; read models are
immediate projections over authoritative tables.

This keeps the economic invariant intact:

```text
system treasury + player balances + guild treasuries = initial seed
```

Escrow is a custody transfer to the treasury and remains part of player net
worth in the portfolio projection.

## Remaining Work, Ranked

1. **P1 — intent receipts:** expose a typed result envelope containing created
   entity IDs, fills, transfers, and rejection detail so every queued action can
   close its feedback loop without polling broad collections.
2. **P1 — durable performance budget:** record cycle phase timings and database
   row counts, then fail an operator smoke check when p95 cycle time exceeds the
   configured interval.
3. **P1 — onboarding:** give a new account a guided first discovery/trade and
   explain yield, collapse, escrow, and the one-cycle action delay in context.
4. **P2 — richer charts:** replace the compact CSS/SVG history with accessible
   candlesticks, volume, time-range selection, and event annotations once the
   core loop has real player telemetry.
5. **P2 — liquidity policy:** tune AI batch size, quote age, and activity against
   concurrent-player load rather than increasing synthetic order volume.
6. **P2 — guild strategy:** surface treasury runway, gate holdings, dividend
   history, and governance decisions as one guild operating screen.
7. **P3 — world identity:** persist authored names, regions, modifiers, and gate
   visual families when narrative content becomes production scope. The current
   deterministic identity layer is intentionally storage-free.

## Verification Gates

Before a release:

```powershell
# Backend static checks (inside backend container or backend virtualenv)
ruff check app tests
mypy app

# Dedicated test database only
$env:DATABASE_URL = "postgresql+asyncpg://.../dungeon_gate_test" # Alembic
alembic upgrade head
$env:TEST_DATABASE_URL = $env:DATABASE_URL                       # pytest
pytest -q

# Frontend
cd frontend
npm run typecheck
npm run build

# Development/production database
$env:DATABASE_URL = "postgresql+asyncpg://.../dungeon_gate"
alembic upgrade head
```

Never point the test suite at the development database. Its safety guard is
expected to reject that configuration.

### Rescue verification record

Completed 2026-07-18:

- backend full suite: **229 passed**
- post-browser/final focused backend suite: **79 passed**
- Ruff: **clean**
- MyPy: **clean across 72 source files**
- frontend TypeScript and production build: **passed**
- test and development databases: **Alembic `a91d7c4e2b10` (head)**
- live browser smoke: dashboard, active-first scanner, gate workstation, order
  ticket, navigation, authentication, and console; **no console errors**
- live simulation: cycles continued through T1033. Final clean eight-cycle
  sample was **1.62–2.85 seconds, median 2.17 seconds**, with an empty Celery
  queue. Event-heavy/host-load bursts reached **7.30 seconds**, still far below
  the previous 23–39-second empty cycles but proving the remaining p95
  performance-budget item is real
- live conservation total after cycles: **100,000,000,000 micro-units**

Live startup also exposed a pre-existing local treasury baseline drift of
`+189,344` micro-units. Account balances otherwise reconciled exactly against
ledger flows. The treasury was conditionally reduced by that exact amount,
restoring the configured seed before unpausing; the correction is reversible by
adding the same amount back.
