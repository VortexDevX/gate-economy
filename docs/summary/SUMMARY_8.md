# Phase 8 Summary: Events, News & Real-time

**Tests before:** 129 · **Tests added:** 19 · **Tests after:** 148

---

## What Was Built

### 1. Stochastic Event Engine (`services/event_engine.py`)

A per-tick random event system that introduces unpredictable economic shocks. Each tick has a configurable probability (default 10%) of firing exactly one event, chosen by weighted random selection:

| Event Type       | Weight | Target        | Effect                                     |
| ---------------- | ------ | ------------- | ------------------------------------------ |
| STABILITY_SURGE  | 25     | 1 random gate | +5 to +15 stability (capped at rank init)  |
| STABILITY_CRISIS | 25     | 1 ACTIVE gate | -5 to -15 stability (floored at 0)         |
| YIELD_BOOM       | 20     | 1 ACTIVE gate | Bonus yield (2×–4× normal) paid to holders |
| MARKET_SHOCK     | 15     | All gates     | -2 to -5 stability to every gate           |
| DISCOVERY_SURGE  | 15     | Global        | Spawn 1–3 extra system gates               |

Events are deterministic (use tick RNG), wealth-agnostic (random target selection), and conservation-safe (YIELD_BOOM is the only one that moves currency, via existing YIELD_PAYMENT flow).

### 2. Gate Lifecycle Refactor (`services/gate_lifecycle.py`)

Extracted `spawn_gate()` from `system_spawn_gate()` — an unconditional gate spawn function reusable by both the regular system spawner and DISCOVERY_SURGE events. `system_spawn_gate()` now delegates to it after the probability check.

### 3. News Generator (`services/news_generator.py`)

Post-hoc scanner that creates human-readable news items each tick by examining:

- **Events** → headline + importance based on event type
- **Gate spawns** → importance scaled by rank (E=1 → S+=5)
- **Gate collapses** → importance ≥ 3
- **Large trades** → value ≥ 1 currency (configurable threshold)

News is informational only — no game state side effects.

### 4. Real-time Publishing (`services/realtime.py`)

Fire-and-forget Redis pub/sub publisher. After each tick commits, a JSON payload with tick number and news headlines is pushed to the `dge:realtime` channel. Failure is logged but doesn't block the tick.

### 5. WebSocket Endpoint (`api/ws.py`)

`/ws` — accepts WebSocket connections and bridges Redis pub/sub messages to the client. Each connected client receives every tick update in real time. No authentication required (read-only public feed).

### 6. News API (`api/news.py`)

`GET /news` — paginated news feed (newest first) with filters:

- `category` (GATE, MARKET, GUILD, WORLD)
- `min_importance` (1–5)
- `limit` / `offset` pagination

---

## New Files

| File                         | Type                           |
| ---------------------------- | ------------------------------ |
| `models/event.py`            | Event model + EventType enum   |
| `models/news.py`             | News model + NewsCategory enum |
| `services/event_engine.py`   | Event rolling + 5 handlers     |
| `services/news_generator.py` | Tick news scanner              |
| `services/realtime.py`       | Redis pub/sub publisher        |
| `api/ws.py`                  | WebSocket endpoint             |
| `api/news.py`                | News REST API                  |
| `schemas/news.py`            | News response schemas          |
| `tests/test_events.py`       | 9 event engine tests           |
| `tests/test_news.py`         | 8 news + API tests             |
| `tests/test_ws.py`           | 2 realtime tests               |

## Modified Files

| File                         | Change                                                  |
| ---------------------------- | ------------------------------------------------------- |
| `config.py`                  | 11 new event/news config params                         |
| `models/__init__.py`         | Registered Event + News                                 |
| `services/gate_lifecycle.py` | Extracted `spawn_gate()`                                |
| `simulation/tick.py`         | Wired steps 13 + 13b + 18, removed `_roll_events` no-op |
| `main.py`                    | Registered news + ws routers                            |
| `tests/conftest.py`          | Added Event + News cleanup                              |

## Migration

One migration: `add_events_and_news` — creates `events` table, `news` table, `eventtype` enum, `newscategory` enum.

---

## Tick Pipeline (Updated)

Steps 13, 13b, and 18 are now active:

```
13.  Roll events ✅ P8
13b. Generate news ✅ P8
14.  Anti-exploit maintenance 🔲 P9
...
18.  Publish realtime update (after commit) ✅ P8
```

---

## Config Added

| Parameter                             | Default    | Purpose               |
| ------------------------------------- | ---------- | --------------------- |
| `event_probability`                   | 0.10       | Event chance per tick |
| `event_stability_surge_min/max`       | 5.0 / 15.0 | Surge range           |
| `event_stability_crisis_min/max`      | 5.0 / 15.0 | Crisis range          |
| `event_market_shock_min/max`          | 2.0 / 5.0  | Shock range           |
| `event_yield_boom_min/max_multiplier` | 2.0 / 4.0  | Boom multiplier       |
| `event_discovery_surge_min/max`       | 1 / 3      | Extra gates           |
| `news_large_trade_threshold_micro`    | 1,000,000  | Trade news cutoff     |

---

## Key Design Decisions

- **One event per tick max** — predictable frequency, list structure supports future expansion
- **Events roll after order matching (step 13)** — don't interfere with current tick's trading; effects hit next tick
- **YIELD_BOOM reuses YIELD_PAYMENT** entry type — it IS yield, just bonus; no new ledger enum needed
- **News is post-hoc, not inline** — no modifications to existing services, clean separation
- **WebSocket is unauthenticated** — public read-only feed, no state mutation
- **Publish is fire-and-forget after commit** — tick integrity is never compromised by Redis failures
- **Events ignore player wealth** — random gate targeting is anti-whale by design
