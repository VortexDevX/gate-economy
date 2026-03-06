# Phase 8 Sub-Plan: Events, News & Real-time

## Goal

Stochastic world events that shake the economy, a news system that narrates major happenings (collapses, large trades, events), and a WebSocket real-time feed that pushes tick updates to connected clients. Events are deterministic (tick RNG), wealth-agnostic, and conservation-safe.

---

## Economic Flows Introduced

| Flow   | Mechanism        | Direction         | Entry Type      |
| ------ | ---------------- | ----------------- | --------------- |
| Faucet | Yield Boom bonus | Treasury → Player | `YIELD_PAYMENT` |

All other event effects (stability changes, extra spawns) modify gate state without currency movement. Conservation invariant unchanged.

---

## Step 1 — Config

### Config Additions (`config.py`)

| Parameter                          | Default   | Purpose                                 |
| ---------------------------------- | --------- | --------------------------------------- |
| `event_probability`                | 0.10      | 10% chance of event per tick            |
| `event_stability_surge_min`        | 5.0       | Min stability gain                      |
| `event_stability_surge_max`        | 15.0      | Max stability gain                      |
| `event_stability_crisis_min`       | 5.0       | Min stability loss                      |
| `event_stability_crisis_max`       | 15.0      | Max stability loss                      |
| `event_market_shock_min`           | 2.0       | Min stability loss per gate             |
| `event_market_shock_max`           | 5.0       | Max stability loss per gate             |
| `event_yield_boom_min_multiplier`  | 2.0       | Min bonus yield multiplier              |
| `event_yield_boom_max_multiplier`  | 4.0       | Max bonus yield multiplier              |
| `event_discovery_surge_min`        | 1         | Min extra gates spawned                 |
| `event_discovery_surge_max`        | 3         | Max extra gates spawned                 |
| `news_large_trade_threshold_micro` | 1_000_000 | Trades above this generate news (1 cur) |

---

## Step 2 — Models + Migration

### `models/event.py` (🆕 new file)

```python
class EventType(str, enum.Enum):
    STABILITY_SURGE = "STABILITY_SURGE"
    STABILITY_CRISIS = "STABILITY_CRISIS"
    YIELD_BOOM = "YIELD_BOOM"
    MARKET_SHOCK = "MARKET_SHOCK"
    DISCOVERY_SURGE = "DISCOVERY_SURGE"

class Event(Base):
    __tablename__ = "events"
    id: UUID PK default uuid4
    event_type: EventType NOT NULL
    tick_id: INT FK→ticks NOT NULL
    target_id: UUID nullable  # gate_id for targeted events, NULL for global
    payload: JSONB nullable   # {stability_change: 12, multiplier: 2.5, gates_spawned: 2}
    created_at: TIMESTAMPTZ NOT NULL
```

### `models/news.py` (🆕 new file)

```python
class NewsCategory(str, enum.Enum):
    GATE = "GATE"
    MARKET = "MARKET"
    GUILD = "GUILD"
    WORLD = "WORLD"

class NewsImportance(int, enum.Enum):  # or just use int field
    MINOR = 1       # E/D gate spawn
    NOTABLE = 2     # C/B gate spawn, small events
    IMPORTANT = 3   # A gate spawn, guild events
    MAJOR = 4       # S/S+ spawn, gate collapse, most events
    CRITICAL = 5    # Market shock, S+ collapse

class News(Base):
    __tablename__ = "news"
    id: UUID PK default uuid4
    tick_id: INT FK→ticks NOT NULL
    headline: VARCHAR(200) NOT NULL
    body: TEXT nullable
    category: NewsCategory NOT NULL
    importance: INT NOT NULL default 1  # 1-5
    related_entity_type: VARCHAR(50) nullable  # 'gate', 'guild'
    related_entity_id: UUID nullable
    created_at: TIMESTAMPTZ NOT NULL
```

### Migration

- Create `eventtype` enum
- Create `newscategory` enum
- Create `events` table
- Create `news` table

### `models/__init__.py`

Register `Event` and `News` models.

---

## Step 3 — Event Engine (`services/event_engine.py`, 🆕 new file)

### Event Type Weights

| Event Type       | Weight | Target    | Effect                                  |
| ---------------- | ------ | --------- | --------------------------------------- |
| STABILITY_SURGE  | 25     | 1 gate    | +5 to +15 stability (capped at init)    |
| STABILITY_CRISIS | 25     | 1 gate    | -5 to -15 stability (floor at 0)        |
| YIELD_BOOM       | 20     | 1 gate    | Bonus yield distribution (2x-4x normal) |
| MARKET_SHOCK     | 15     | All gates | -2 to -5 stability each                 |
| DISCOVERY_SURGE  | 15     | Global    | Spawn 1-3 extra system gates            |

### `roll_events(session, tick_number, tick_id, rng, treasury_id) → list[Event]`

```python
1. if rng.random() >= settings.event_probability: return []

2. Choose event_type via rng.choices(types, weights)

3. Dispatch to handler:
     STABILITY_SURGE  → _handle_stability_surge(session, tick_id, rng)
     STABILITY_CRISIS → _handle_stability_crisis(session, tick_id, rng)
     YIELD_BOOM       → _handle_yield_boom(session, tick_id, rng, treasury_id)
     MARKET_SHOCK     → _handle_market_shock(session, tick_id, rng)
     DISCOVERY_SURGE  → _handle_discovery_surge(session, tick_number, tick_id, rng, treasury_id)

4. Handler returns Event record (or None if no valid target)
5. Return list of events (0 or 1 for now, list for future multi-event support)
```

### Event Handlers

#### `_handle_stability_surge(session, tick_id, rng) → Event | None`

```python
# Query ACTIVE/UNSTABLE gates
# If none: return None
# Pick random gate via rng.choice
# change = rng.uniform(surge_min, surge_max)
# Load rank profile for cap
# gate.stability = min(gate.stability + change, profile.stability_init)
# Create + return Event(STABILITY_SURGE, target_id=gate.id, payload={change, new_stability})
```

#### `_handle_stability_crisis(session, tick_id, rng) → Event | None`

```python
# Query ACTIVE gates (not already UNSTABLE — make it dramatic)
# If none: return None
# Pick random gate
# change = rng.uniform(crisis_min, crisis_max)
# gate.stability = max(gate.stability - change, 0)
# Create + return Event(STABILITY_CRISIS, target_id=gate.id, payload={change, new_stability})
```

#### `_handle_yield_boom(session, tick_id, rng, treasury_id) → Event | None`

```python
# Query ACTIVE gates
# If none: return None
# Pick random gate
# multiplier = rng.uniform(yield_boom_min, yield_boom_max)
# bonus_yield = int(gate.base_yield_micro * (gate.stability / 100.0) * multiplier)
# Distribute pro-rata to shareholders (skip treasury-held, skip guild-held shares)
#   - For each gate_share holder:
#       share_yield = (bonus_yield * share.quantity) // gate.total_shares
#       if share_yield > 0:
#           Determine if holder is player or guild (check guild_gate_holdings)
#           transfer(TREASURY → holder, share_yield, YIELD_PAYMENT)
# Create + return Event(YIELD_BOOM, target_id=gate.id, payload={multiplier, bonus_yield})
```

Note: Yield boom reuses `YIELD_PAYMENT` entry type with descriptive memo. No new enum value needed.

#### `_handle_market_shock(session, tick_id, rng) → Event | None`

```python
# Query all ACTIVE/UNSTABLE gates
# If none: return None
# change = rng.uniform(shock_min, shock_max)
# For each gate:
#     gate.stability = max(gate.stability - change, 0)
# Create + return Event(MARKET_SHOCK, target_id=None, payload={change, affected_count})
```

#### `_handle_discovery_surge(session, tick_number, tick_id, rng, treasury_id) → Event | None`

```python
# count = rng.randint(discovery_surge_min, discovery_surge_max)
# For i in range(count):
#     spawn_gate(session, tick_number, tick_id, rng, treasury_id)  # force spawn
# Create + return Event(DISCOVERY_SURGE, target_id=None, payload={count})
```

### Gate Lifecycle Refactor (minor)

Extract `_create_gate(session, tick_number, tick_id, rng, treasury_id, rank_profiles)` from `system_spawn_gate()` so both the system spawner and DISCOVERY_SURGE can create gates without the probability check.

```python
# In gate_lifecycle.py:
async def spawn_gate(session, tick_number, tick_id, rng, treasury_id) -> Gate:
    """Unconditionally spawn one system gate. Used by system_spawn and events."""
    # (existing rank selection + gate creation logic, extracted)

async def system_spawn_gate(session, tick_number, tick_id, rng, treasury_id):
    """Probabilistic system spawn — calls spawn_gate if RNG passes."""
    if rng.random() >= settings.system_spawn_probability:
        return None
    return await spawn_gate(session, tick_number, tick_id, rng, treasury_id)
```

---

## Step 4 — News Service (`services/news_generator.py`, 🆕 new file)

### `generate_tick_news(session, tick_number, tick_id, events) → list[News]`

Scans for notable activity this tick and creates News rows.

```python
news_items = []

# 1. News from events
for event in events:
    news_items.append(_news_from_event(event, tick_id))

# 2. Gate spawns this tick
spawned_gates = query gates WHERE spawned_at_tick = tick_number
for gate in spawned_gates:
    # Skip if already covered by DISCOVERY_SURGE event news
    news_items.append(News(
        tick_id=tick_id,
        headline=f"A Rank-{gate.rank.value} Gate has appeared!",
        category=GATE,
        importance=_rank_importance(gate.rank),  # E=1, D=1, C=2, B=2, A=3, S=4, S+=5
        related_entity_type="gate",
        related_entity_id=gate.id,
    ))

# 3. Gate collapses this tick
collapsed_gates = query gates WHERE collapsed_at_tick = tick_number
for gate in collapsed_gates:
    news_items.append(News(
        tick_id=tick_id,
        headline=f"Rank-{gate.rank.value} Gate has collapsed!",
        body="All shares are now worthless. Orders have been cancelled.",
        category=GATE,
        importance=max(3, _rank_importance(gate.rank)),
        related_entity_type="gate",
        related_entity_id=gate.id,
    ))

# 4. Large trades this tick
large_trades = query trades WHERE tick_id = tick.id
    AND (quantity * price_micro) >= settings.news_large_trade_threshold_micro
for trade in large_trades:
    value = trade.quantity * trade.price_micro
    news_items.append(News(
        tick_id=tick_id,
        headline=f"Large trade: {trade.quantity} shares at {trade.price_micro} per share",
        category=MARKET,
        importance=2,
        related_entity_type="trade",
        related_entity_id=trade.id,
    ))

session.add_all(news_items)
return news_items
```

### `_news_from_event(event, tick_id) → News`

Maps each event type to a headline and importance:

| Event Type       | Headline Template                                      | Importance |
| ---------------- | ------------------------------------------------------ | ---------- |
| STABILITY_SURGE  | "Stability surge! Gate {rank} reinforced (+{change})"  | 3          |
| STABILITY_CRISIS | "Crisis! Gate {rank} destabilized (-{change})"         | 3          |
| YIELD_BOOM       | "Yield boom! Gate {rank} produces {mult}× bonus yield" | 3          |
| MARKET_SHOCK     | "Market shock! {count} gates destabilized"             | 4          |
| DISCOVERY_SURGE  | "Discovery surge! {count} new gates appeared"          | 3          |

### `_rank_importance(rank) → int`

```python
E/D → 1, C/B → 2, A → 3, S → 4, S+ → 5
```

---

## Step 5 — Realtime (`services/realtime.py`, 🆕 new file)

### `publish_tick_update(tick_number, news_items)`

```python
async def publish_tick_update(tick_number: int, news_items: list) -> None:
    """Publish tick summary to Redis pub/sub for WebSocket clients."""
    from redis.asyncio import Redis

    payload = {
        "type": "tick_update",
        "tick_number": tick_number,
        "news": [
            {
                "id": str(n.id),
                "headline": n.headline,
                "category": n.category.value,
                "importance": n.importance,
            }
            for n in news_items
        ],
    }

    try:
        r = Redis.from_url(settings.redis_url)
        await r.publish("dge:realtime", json.dumps(payload))
        await r.aclose()
    except Exception:
        logger.warning("realtime_publish_failed", tick_number=tick_number)
```

### WebSocket Endpoint (`api/ws.py`, 🆕 new file)

```python
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe("dge:realtime")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe("dge:realtime")
        await pubsub.aclose()
        await redis.aclose()
```

---

## Step 6 — Pipeline Wiring

### Update `simulation/tick.py`

Replace the `_roll_events` no-op with real implementation:

```python
from app.services.event_engine import roll_events
from app.services.news_generator import generate_tick_news
from app.services.realtime import publish_tick_update
```

Updated pipeline steps:

```
13. Roll events
    events = await roll_events(session, tick_number, tick.id, rng, treasury_id)

13b. Generate news
    news_items = await generate_tick_news(session, tick_number, tick.id, events)

14. Anti-exploit maintenance 🔲 P9

... (steps 15-17 unchanged)

After commit:
18. Publish realtime update (fire-and-forget)
    await publish_tick_update(tick_number, news_items)
```

Remove the `_roll_events` no-op function. Keep `_anti_exploit_maintenance` no-op.

---

## Step 7 — API Endpoints

### News API (`api/news.py`, 🆕 new file)

| Method | Path  | Auth | Purpose                       |
| ------ | ----- | ---- | ----------------------------- |
| GET    | /news | No   | Paginated news (newest first) |

#### `GET /news`

Query params:

- `limit` (int, default 20, max 100)
- `offset` (int, default 0)
- `category` (optional NewsCategory filter)
- `min_importance` (optional int, default 1)

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "tick_id": 42,
      "headline": "Market shock! 5 gates destabilized",
      "body": null,
      "category": "WORLD",
      "importance": 4,
      "related_entity_type": "gate",
      "related_entity_id": "uuid",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

### Schemas (`schemas/news.py`, 🆕 new file)

```python
class NewsResponse(BaseModel):
    id: UUID
    tick_id: int
    headline: str
    body: str | None
    category: str
    importance: int
    related_entity_type: str | None
    related_entity_id: UUID | None
    created_at: datetime

class NewsListResponse(BaseModel):
    items: list[NewsResponse]
    total: int
    limit: int
    offset: int
```

### Register in `main.py`

```python
from app.api.news import router as news_router
from app.api.ws import router as ws_router

app.include_router(news_router)
app.include_router(ws_router)
```

---

## Step 8 — Tests

### `test_events.py` (🆕 new file)

| Test                                      | Assertion                                    |
| ----------------------------------------- | -------------------------------------------- |
| Event fires when probability passes       | Event record created, probability=1.0        |
| Event skipped when probability fails      | No event record, probability=0.0             |
| Stability surge increases gate stability  | Gate stability increased, capped at init     |
| Stability crisis decreases gate stability | Gate stability decreased, floor at 0         |
| Yield boom distributes bonus to holders   | Shareholders receive yield, treasury debited |
| Market shock decreases all gate stability | All ACTIVE/UNSTABLE gates lose stability     |
| Discovery surge spawns extra gates        | 1-3 new gates appear with OFFERING status    |
| Event skipped when no valid targets       | No event when no ACTIVE gates                |
| Conservation holds after yield boom       | treasury + players + guilds = INITIAL_SEED   |

### `test_news.py` (🆕 new file)

| Test                               | Assertion                                     |
| ---------------------------------- | --------------------------------------------- |
| News generated for event           | News row with event headline exists           |
| News generated for gate collapse   | News row referencing collapsed gate           |
| News generated for gate spawn      | News row referencing spawned gate             |
| News generated for large trade     | News row when trade value ≥ threshold         |
| No news for small trade            | No news row when trade value < threshold      |
| News API returns paginated results | GET /news returns items, total, limit, offset |
| News API filters by category       | Only matching category returned               |
| News API filters by min_importance | Only importance ≥ filter returned             |

### `test_ws.py` (🆕 new file)

| Test                                | Assertion                                                 |
| ----------------------------------- | --------------------------------------------------------- |
| Publish sends to Redis channel      | Subscribe + verify message received                       |
| Full tick publishes realtime update | execute_tick → Redis channel receives tick_update message |

### Estimated: ~19 tests

---

## Execution Order

```
Step 1:  Config additions                     → config.py (edit)
Step 2:  Models + migration                   → models/event.py (new), models/news.py (new),
                                                 models/__init__.py (edit), migration (new)
Step 3:  Event engine                         → services/event_engine.py (new),
                                                 services/gate_lifecycle.py (edit — extract spawn_gate)
Step 4:  News service                         → services/news_generator.py (new)
Step 5:  Realtime + WebSocket                 → services/realtime.py (new), api/ws.py (new)
Step 6:  Pipeline wiring                      → simulation/tick.py (edit)
Step 7:  API + schemas                        → api/news.py (new), schemas/news.py (new),
                                                 main.py (edit)
Step 8:  Tests                                → tests/test_events.py (new),
                                                 tests/test_news.py (new),
                                                 tests/test_ws.py (new)
```

### Estimated: ~8 new files, ~4 modified files, ~19 new tests.

---

## Key Design Decisions

| Decision                                  | Rationale                                                          |
| ----------------------------------------- | ------------------------------------------------------------------ |
| Events are immediate, one-time effects    | No duration tracking complexity, consequences play out naturally   |
| Events roll in step 13 (after matching)   | Don't interfere with current tick's trading; effects hit next tick |
| YIELD_BOOM reuses `YIELD_PAYMENT` type    | It IS a yield payment, just bonus — no new enum value needed       |
| News is post-hoc scan + event-driven      | Clean, no modification to existing services                        |
| WebSocket uses Redis pub/sub bridge       | Tick runs in Celery worker, WS in FastAPI — Redis bridges them     |
| Publish is fire-and-forget after commit   | Tick succeeds even if Redis publish fails                          |
| Event probability per tick (not per gate) | At most 1 event per tick — predictable frequency                   |
| Events ignore player wealth               | Anti-whale by design — random gates affected                       |
| `spawn_gate` extracted from system_spawn  | Reusable for DISCOVERY_SURGE without probability hack              |
| Separate events + news tables             | Events have effects (state changes), news is informational only    |

---

## Edge Cases

| Edge Case                             | Expected Behavior                                          |
| ------------------------------------- | ---------------------------------------------------------- |
| No ACTIVE gates when event fires      | Event handler returns None, no event recorded              |
| Stability surge caps at init value    | Gate stability never exceeds profile.stability_init        |
| Stability crisis floors at 0          | Gate stability never goes negative                         |
| Market shock on single gate           | Still works — "all gates" is just one gate                 |
| Yield boom with treasury-held shares  | Treasury shares skipped (no self-payment)                  |
| Yield boom with guild-held shares     | Guild receives yield (same as regular yield distribution)  |
| Discovery surge with no rank profiles | Shouldn't happen (seeded at startup), but would skip       |
| Large trade exactly at threshold      | Generates news (≥ comparison)                              |
| No trades this tick                   | No trade news generated                                    |
| Redis down during publish             | Warning logged, tick still succeeds                        |
| No WebSocket clients connected        | Publish still works, message just has no subscribers       |
| Multiple events per tick              | Not currently possible (single roll), list supports future |

---

## Dependencies

- Phase 3: Tick pipeline, RNG
- Phase 4: Gates, gate lifecycle, gate shares, rank profiles
- Phase 5: Market system (trades for large trade detection)
- Phase 6: Guilds (guild gate holdings for yield boom distribution)
- Phase 7: AI traders (run before events, may trade on event-affected gates next tick)

---

## Guidelines for Responses

1. **Small changes:** If a file only needs a minor update, just tell me _what_ to change and _where_.

2. **Label every file output:** Always specify whether the file is being:
   - 🆕 **Created** (new file)
   - ✏️ **Updated** (partial change)
   - 🔁 **Replaced** (full rewrite)

3. **Go step by step:**
   - If a step involves **fewer than 2 files**, combine it with the next.
   - Aim for **2–3 steps** at a time.

4. **No overthinking:** Don't spiral into deep analysis.
