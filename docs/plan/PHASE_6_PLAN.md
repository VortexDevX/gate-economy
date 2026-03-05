# Phase 6 Sub-Plan: Guilds

## Goal

Player-created economic organizations with shares, dividends, maintenance costs, and market-tradable equity. Guilds can hold gate shares, earn yield into their treasury, distribute dividends, and face insolvency/dissolution. Guild shares trade on the same market system as gate shares.

---

## Economic Flows Introduced

| Flow        | Mechanism            | Direction         | Entry Type          |
| ----------- | -------------------- | ----------------- | ------------------- |
| **Sink**    | Guild creation fee   | Player → Treasury | `GUILD_CREATION`    |
| **Sink**    | Guild maintenance    | Guild → Treasury  | `GUILD_MAINTENANCE` |
| **Faucet**  | Yield to guild       | Treasury → Guild  | `YIELD_PAYMENT`     |
| **Neutral** | Guild share trades   | Player ↔ Player   | `TRADE_SETTLEMENT`  |
| **Sink**    | Guild share fees     | Player → Treasury | `TRADE_FEE`         |
| **Faucet**  | Dividends            | Guild → Players   | `DIVIDEND`          |
| **Lock**    | Guild buy escrow     | Guild → Treasury  | `ESCROW_LOCK`       |
| **Unlock**  | Guild escrow release | Treasury → Guild  | `ESCROW_RELEASE`    |
| **Neutral** | Guild ISO proceeds   | Treasury → Guild  | `TRADE_SETTLEMENT`  |

### Conservation Invariant Update

`treasury_balance + SUM(player_balances) + SUM(guild_treasuries) = INITIAL_SEED`

Guild treasuries are now part of the sum. All guild treasury movements go through `TransferService`.

---

## Step 1 — Models

### New Enums

| Enum             | Values                             |
| ---------------- | ---------------------------------- |
| `GuildStatus`    | `ACTIVE`, `INSOLVENT`, `DISSOLVED` |
| `GuildRole`      | `LEADER`, `OFFICER`, `MEMBER`      |
| `DividendPolicy` | `MANUAL`, `AUTO_FIXED_PCT`         |

### New Tables

```
guilds
id UUID PK DEFAULT uuid4
name VARCHAR UNIQUE NOT NULL
founder_id UUID FK → players NOT NULL
treasury_micro BIGINT NOT NULL DEFAULT 0 CHECK (>= 0)
total_shares INT NOT NULL
public_float_pct DECIMAL NOT NULL
dividend_policy DividendPolicy NOT NULL
auto_dividend_pct DECIMAL NULL
status GuildStatus NOT NULL DEFAULT 'ACTIVE'
created_at_tick INT NOT NULL
maintenance_cost_micro BIGINT NOT NULL
missed_maintenance_ticks INT NOT NULL DEFAULT 0
insolvent_ticks INT NOT NULL DEFAULT 0

guild_members
guild_id UUID FK → guilds
player_id UUID FK → players
role GuildRole NOT NULL
joined_at_tick INT NOT NULL
PRIMARY KEY (guild_id, player_id)

guild_shares
guild_id UUID FK → guilds
player_id UUID (plain, NO FK — can hold guild.id for ISO float)
quantity INT NOT NULL CHECK (>= 0)
PRIMARY KEY (guild_id, player_id)

guild_gate_holdings
guild_id UUID FK → guilds
gate_id UUID FK → gates
quantity INT NOT NULL CHECK (>= 0)
PRIMARY KEY (guild_id, gate_id)
```

### Modified Tables

```
orders

guild_id UUID NULL -- if set, order acts on behalf of this guild
```

### Model Notes

- `guilds.treasury_micro` is the guild's own balance, separate from system treasury and player balances.
- `guilds.missed_maintenance_ticks` counts consecutive ticks where maintenance couldn't be fully paid. Resets to 0 when paid.
- `guilds.insolvent_ticks` counts consecutive ticks in INSOLVENT status. Resets to 0 on recovery.
- `guild_shares.player_id` is a **plain UUID** (no FK). Can hold guild's own ID for ISO float shares (same convention as gate_shares holding treasury UUID).
- `guild_gate_holdings` tracks gate shares owned by guilds, separate from `gate_shares` (which tracks player/treasury holdings).
- `Order.guild_id` when set marks the order as a guild order — escrow/settlement uses guild treasury, shares go to/from guild tables.

### Files

| File                 | Contents                                                                                                            |
| -------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `models/guild.py`    | `GuildStatus`, `GuildRole`, `DividendPolicy` enums, `Guild`, `GuildMember`, `GuildShare`, `GuildGateHolding` models |
| `models/market.py`   | Add `guild_id` field to `Order`                                                                                     |
| `models/__init__.py` | Register `Guild`, `GuildMember`, `GuildShare`, `GuildGateHolding`                                                   |

---

## Step 2 — Migration + Config

### Migration

```bash
make migration msg="add guilds guild_members guild_shares guild_gate_holdings and order guild_id"
make migrate

```

### Migration must:

1. Create `guildstatus`, `guildrole`, `dividendpolicy` enums
2. Create `guilds`, `guild_members`, `guild_shares`, `guild_gate_holdings` tables
3. Add `guild_id` column to orders:

```sql
ALTER TABLE orders ADD COLUMN guild_id UUID NULL;
```

### Config Additions (config.py)

| Parameter                      | Default    | Purpose                                        |
| ------------------------------ | ---------- | ---------------------------------------------- |
| `guild_creation_cost_micro`    | 50_000_000 | Cost to create a guild (50 currency)           |
| `guild_total_shares`           | 1000       | Default shares issued per guild                |
| `guild_max_float_pct`          | 0.49       | Max public float (founder keeps majority)      |
| `guild_base_maintenance_micro` | 100_000    | Base per-tick maintenance cost (0.1 currency)  |
| `guild_maintenance_scale`      | 0.001      | Scale factor on total gate holding value       |
| `guild_insolvency_threshold`   | 3          | Consecutive missed maintenance → INSOLVENT     |
| `guild_dissolution_threshold`  | 10         | Consecutive insolvent ticks → DISSOLVED        |
| `guild_liquidation_discount`   | 0.50       | Liquidation price = market price × this factor |

---

## Step 3 — TransferService GUILD Support

### Update `services/transfer.py`:

### Add GUILD case to `_load_and_lock()`:

```py
if account_type == AccountEntityType.GUILD:
    from app.models.guild import Guild
    stmt = (
        select(Guild)
        .where(Guild.id == account_id)
        .with_for_update()
    )
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()
    if account is None:
        raise ValueError(f"Guild {account_id} not found")
    return account
```

**Important**: Guild model uses `treasury_micro` not balance_micro. The `_load_and_lock` returns the ORM object, and `transfer()` accesses .`balance_micro`. Two options:

- (A) Add a `balance_micro` property to Guild that maps to `treasury_micro`
- (B) Make `transfer()` aware of the field name difference

Option A is cleaner — add to Guild model:

```py
@property
def balance_micro(self) -> int:
    return self.treasury_micro

@balance_micro.setter
def balance_micro(self, value: int) -> None:
    self.treasury_micro = value
```

This lets TransferService work without modification beyond the `_load_and_lock` addition.

---

## Step 4 — Guild Manager Service (`services/guild_manager.py`)

#### `process_create_guild(session, intent, tick_number, tick_id, treasury_id)`

1. Parse payload: `{name, public_float_pct, dividend_policy, auto_dividend_pct}`
2. Validate:
   - Name unique (query guilds)
   - `public_float_pct` in `[0, guild_max_float_pct]`
   - Player has balance >= `guild_creation_cost_micro`
   - If `AUTO_FIXED_PCT`: `auto_dividend_pct > 0` and `<= 1.0`
3. `transfer(PLAYER → TREASURY, creation_cost, GUILD_CREATION)`
4. Calculate `maintenance_cost = guild_base_maintenance_micro`
5. Create Guild record (`status=ACTIVE`, `treasury_micro=0`, `total_shares=guild_total_shares`)
6. Create GuildMember (`player_id=intent.player_id`, `role=LEADER`)
7. Calculate shares:
   - `founder_shares = total_shares - int(total_shares * public_float_pct)`
   - `float_shares = total_shares - founder_shares`
8. Create GuildShare (`guild_id`, `player_id=intent.player_id`, `quantity=founder_shares`)
9. If `float_shares > 0`:
   - Create GuildShare (`guild_id`, `player_id=guild.id`, `quantity=float_shares`)
   - (ISO order created in the ISO step of tick pipeline)

#### `process_guild_dividend(session, intent, tick_number, tick_id, treasury_id)`

1. Parse payload: `{guild_id, gate_id, quantity, price_limit_micro}`
2. Validate:
   - Guild exists and is ACTIVE
   - `intent.player_id` is LEADER (or OFFICER) of guild
   - Gate exists and is not COLLAPSED
   - `quantity > 0`, `price > 0`
   - `Guild treasury >= escrow (quantity * price + max_fee)`
3. Escrow: `transfer(GUILD → TREASURY, escrow, ESCROW_LOCK)`
4. Create Order:
   - `player_id = guild.id` (plain UUID)
   - `guild_id = guild.id`
   - `asset_type = GATE_SHARE`
   - `side = BUY`
   - `escrow_micro = escrow`
   - `created_at_tick = tick_number`

#### `guild_maintenance(session, tick_number, tick_id, treasury_id)`

Called each tick for all ACTIVE and INSOLVENT guilds:

```py
for each guild with status in (ACTIVE, INSOLVENT):
    # Calculate maintenance
    # Base cost + scaled cost on guild gate holdings value
    gate_value = SUM(holding.quantity * market_price(gate_id)) for each gate holding
    cost = guild_base_maintenance_micro + int(gate_value * guild_maintenance_scale)
    guild.maintenance_cost_micro = cost  # update for display

    if guild.treasury_micro >= cost:
        transfer(GUILD → TREASURY, cost, GUILD_MAINTENANCE, tick_id)
        guild.missed_maintenance_ticks = 0
        if guild.status == GuildStatus.INSOLVENT:
            guild.insolvent_ticks = 0
            guild.status = GuildStatus.ACTIVE  # recovery
    else:
        # Pay what's available
        if guild.treasury_micro > 0:
            transfer(GUILD → TREASURY, guild.treasury_micro, GUILD_MAINTENANCE, tick_id)
        guild.missed_maintenance_ticks += 1

    # Insolvency check
    if guild.missed_maintenance_ticks >= guild_insolvency_threshold:
        if guild.status == GuildStatus.ACTIVE:
            guild.status = GuildStatus.INSOLVENT
            guild.insolvent_ticks = 0

    if guild.status == GuildStatus.INSOLVENT:
        guild.insolvent_ticks += 1
        if guild.insolvent_ticks >= guild_dissolution_threshold:
            await _dissolve_guild(session, guild, tick_number, tick_id, treasury_id)
```

#### `auto_dividends(session, tick_number, tick_id)`

Called each tick:

```py
for each ACTIVE guild with dividend_policy == AUTO_FIXED_PCT:
    if guild.treasury_micro <= 0:
        continue
    amount = int(guild.treasury_micro * guild.auto_dividend_pct)
    if amount <= 0:
        continue
    distribute same as manual dividend
```

#### `_dissolve_guild(session, guild, tick_number, tick_id, treasury_id)`

1. Set `guild.status = DISSOLVED`

2. Liquidate gate holdings:

   ```py
   for each guild_gate_holding:
       market_price = get last_price for this gate (or 0 if unknown)
       liquidation_value = holding.quantity * market_price * guild_liquidation_discount
       if liquidation_value > 0:
           transfer(TREASURY → GUILD, liquidation_value, TRADE_SETTLEMENT, tick_id)
       holding.quantity = 0
   ```

3. Distribute guild treasury to shareholders pro-rata:

   ```py
   total = guild.treasury_micro
   shareholders = guild_shares WHERE player_id != guild.id AND quantity > 0
   total_shares = SUM(shareholders.quantity)
   for each shareholder:
       payout = total * (shareholder.quantity / total_shares)
       if payout > 0:
           transfer(GUILD → PLAYER, payout, DIVIDEND, tick_id)
   # Remainder (from integer division) stays — should be near 0
   ```

4. Cancel all open orders with `guild_id = guild.id`:
   - Release escrow: `transfer(TREASURY → GUILD, escrow, ESCROW_RELEASE)`
   - Release any remaining guild treasury as final sweep:

   ```py
   if guild.treasury_micro > 0:
       transfer(GUILD → TREASURY, guild.treasury_micro, GUILD_MAINTENANCE, tick_id)
   ```

5. Cancel all open GUILD_SHARE orders for this guild's shares:
   - Release buyer escrows: `transfer(TREASURY → PLAYER, escrow, ESCROW_RELEASE)`

---

## Step 5 — Update Yield Distribution

### Modify `services/gate_lifecycle.py` → `distribute_yield()`:

### Currently queries `gate_shares` only. Must also query `guild_gate_holdings`:

```py
# After getting player shareholders from gate_shares:

# Guild shareholders
result = await session.execute(
    select(GuildGateHolding).where(
        GuildGateHolding.gate_id == gate.id,
        GuildGateHolding.quantity > 0,
    )
)
guild_holders = result.scalars().all()

# Total shares = player shares + guild shares (exclude treasury as before)
total_shares = player_total + sum(gh.quantity for gh in guild_holders)

# Pay guilds
for gh in guild_holders:
    payout = effective_yield * gh.quantity // total_shares
    if payout > 0:
        transfer(TREASURY → GUILD(gh.guild_id), payout, YIELD_PAYMENT, tick_id)
```

### Important: INSOLVENT guilds receive 50% yield (per plan). Apply multiplier:

```py
if guild.status == GuildStatus.INSOLVENT:
    payout = payout // 2  # 50% yield penalty
```

---

## Step 6 — Update Order Matching

### Modifications to `services/order_matching.py`:

### `_validate_asset()` — add GUILD_SHARE support:

```py
if asset_type == AssetType.GUILD_SHARE:
    result = await session.execute(select(Guild).where(Guild.id == asset_id))
    guild = result.scalar_one_or_none()
    if guild is None:
        return "Guild not found"
    if guild.status == GuildStatus.DISSOLVED:
        return "Guild is dissolved"
    return None
```

### `_get_available_shares()` — add GUILD_SHARE + guild order support:

```py
if asset_type == AssetType.GUILD_SHARE:
    result = await session.execute(
        select(GuildShare.quantity).where(
            GuildShare.guild_id == asset_id, GuildShare.player_id == player_id,
        )
    )
    owned = result.scalar_one_or_none() or 0
```

For guild orders (guild_id set, buying gate shares), available shares come from `guild_gate_holdings` — but guilds only BUY gate shares (not sell), so this case only applies to the quantity validation check, which is handled in `process_guild_invest`.

`_execute_trade()` — extend for GUILD_SHARE and guild orders:

### The core changes:

```py
# Determine seller/buyer entity types
sell_is_guild = sell_order.guild_id is not None
buy_is_guild = buy_order.guild_id is not None

# Currency settlement
if sell_is_guild:
    # Guild ISO or guild selling — pay guild treasury
    transfer(TREASURY → GUILD(sell_order.guild_id), trade_value, TRADE_SETTLEMENT)
    seller_fee = 0  # no fee for guild ISO
elif not is_iso:
    # Normal P2P
    transfer(TREASURY → PLAYER(sell_order.player_id), trade_value, TRADE_SETTLEMENT)
    transfer(PLAYER → TREASURY, seller_fee, TRADE_FEE)

# Share transfer — depends on asset_type AND guild involvement
if asset_type == AssetType.GATE_SHARE:
    # Seller shares
    if sell_is_guild:
        # guild_gate_holdings (shouldn't happen in P6 — guilds don't sell gate shares)
        # But handle defensively
        decrement guild_gate_holdings
    else:
        decrement gate_shares (existing logic)

    # Buyer shares
    if buy_is_guild:
        upsert guild_gate_holdings
    else:
        upsert gate_shares (existing logic)

elif asset_type == AssetType.GUILD_SHARE:
    # Both use guild_shares table, keyed by (guild_id=asset_id, player_id)
    decrement guild_shares WHERE guild_id=asset_id AND player_id=seller
    upsert guild_shares WHERE guild_id=asset_id AND player_id=buyer

# Escrow release on full fill
if buy_is_guild and buy_order.escrow_micro > 0:
    transfer(TREASURY → GUILD, escrow, ESCROW_RELEASE)
else:
    transfer(TREASURY → PLAYER, escrow, ESCROW_RELEASE)  # existing logic
```

### `create_iso_orders()` — extend for guild share ISOs:

```py
# After gate ISOs:
# Guild share ISOs
result = await session.execute(
    select(Guild).where(Guild.status == GuildStatus.ACTIVE)
)
for guild in result.scalars().all():
    # Check if guild holds its own shares (ISO float)
    result2 = await session.execute(
        select(GuildShare.quantity).where(
            GuildShare.guild_id == guild.id,
            GuildShare.player_id == guild.id,
        )
    )
    self_held = result2.scalar_one_or_none() or 0
    if self_held <= 0:
        continue

    # Check if ISO order already exists
    exists = await session.execute(
        select(Order.id).where(
            Order.asset_type == AssetType.GUILD_SHARE,
            Order.asset_id == guild.id,
            Order.guild_id == guild.id,
            Order.side == OrderSide.SELL,
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIAL]),
        ).limit(1)
    )
    if exists.scalar_one_or_none() is not None:
        continue

    # ISO price = creation_cost / total_shares
    iso_price = settings.guild_creation_cost_micro // guild.total_shares

    session.add(Order(
        player_id=guild.id,
        guild_id=guild.id,
        asset_type=AssetType.GUILD_SHARE,
        asset_id=guild.id,
        side=OrderSide.SELL,
        quantity=self_held,
        price_limit_micro=iso_price,
        created_at_tick=tick_number,
    ))
```

### `cancel_collapsed_gate_orders()` → rename to `cancel_dead_asset_orders()`:

```py
# Existing: cancel orders for collapsed gates
# New: cancel orders for dissolved guilds
result = await session.execute(
    select(Guild.id).where(Guild.status == GuildStatus.DISSOLVED)
)
dissolved_ids = [r[0] for r in result.all()]
if dissolved_ids:
    # Cancel GUILD_SHARE orders for dissolved guilds
    # Cancel guild BUY orders (guild_id = dissolved guild)
    # Release escrows
```

---

## Step 7 — Wire into Tick Pipeline

Update `simulation/tick.py`:

### Updated `_process_intents()`:

```py
elif intent.intent_type == IntentType.CREATE_GUILD:
    await process_create_guild(session, intent, tick_number, tick_id, treasury_id)
elif intent.intent_type == IntentType.GUILD_DIVIDEND:
    await process_guild_dividend(session, intent, tick_number, tick_id, treasury_id)
elif intent.intent_type == IntentType.GUILD_INVEST:
    await process_guild_invest(session, intent, tick_number, tick_id, treasury_id)
```

### New `_guild_lifecycle()` step:

```py
async def _guild_lifecycle(session, tick_number, tick_id, rng, treasury_id):
    await guild_maintenance(session, tick_number, tick_id, treasury_id)
    await auto_dividends(session, tick_number, tick_id)
```

### Updated pipeline order:

6.  Process intents (+ CREATE_GUILD, GUILD_DIVIDEND, GUILD_INVEST)
7.  Advance gates (spawn, lifecycle, yield — now includes guild gate holdings)
    7b. Guild lifecycle (maintenance, insolvency, auto-dividends, dissolution) ← NEW
8.  Create ISO orders (gates + guild shares) ← EXTENDED
9.  Cancel orders for COLLAPSED gates + DISSOLVED guilds ← EXTENDED
10. Match orders
11. Finalize ISO transitions (gates only — guilds have no status change)
12. Update market prices

---

## Step 8 — State Hash + Conservation

### State Hash Extension

Add to `compute_state_hash`:

```py
# Guild treasury sum
result = await session.execute(
    select(func.coalesce(func.sum(Guild.treasury_micro), 0))
)
guild_treasury_total = result.scalar_one()

# Guild count per status
result = await session.execute(
    select(Guild.status, func.count(Guild.id)).group_by(Guild.status)
)
guild_status_counts = {s.value: c for s, c in result.all()}

parts.append(f"guild_treasury:{guild_treasury_total}")
for status_name in sorted(guild_status_counts.keys()):
    parts.append(f"guilds:{status_name}:{guild_status_counts[status_name]}")
```

### Conservation Invariant

```
treasury + SUM(player_balances) + SUM(guild_treasuries) = INITIAL_SEED
```

Update `test_conservation.py` to include guild treasuries in the sum.

---

## Step 9 — Schemas (`schemas/guild.py`)

| Schema                | Fields                                                                                                         |
| --------------------- | -------------------------------------------------------------------------------------------------------------- |
| `GuildResponse`       | id, name, founder_id, treasury_micro, total_shares, public_float_pct, dividend_policy, status, created_at_tick |
| `GuildDetailResponse` | GuildResponse + members, gate_holdings (list of {gate_id, quantity}), shareholder_count                        |
| `GuildListResponse`   | guilds: list[GuildResponse], total: int                                                                        |

---

## Step 10 — API Routes

### Update `api/guilds.py` (new file) + `main.py`:

| Method | Path           | Auth | Purpose                                                                                      |
| ------ | -------------- | ---- | -------------------------------------------------------------------------------------------- |
| `GET`  | `/guilds`      | No   | List guilds (filter by status, paginated)                                                    |
| `GET`  | `/guilds/{id}` | No   | Guild detail (treasury, members, holdings, shareholder count)                                |
| `POST` | `/intents`     | Yes  | `type=CREATE_GUILD`, payload: `{name, public_float_pct, dividend_policy, auto_dividend_pct}` |
| `POST` | `/intents`     | Yes  | `type=GUILD_DIVIDEND`, payload: `{guild_id, amount_micro?}`                                  |
| `POST` | `/intents`     | Yes  | `type=GUILD_INVEST`, payload: `{guild_id, gate_id, quantity, price_limit_micro}`             |

---

## Step 11 — Tests

### `test_guild_manager.py` (simulation-level)

| Test                                    | Assertion                                                     |
| --------------------------------------- | ------------------------------------------------------------- |
| Guild creation deducts fee              | Player balance reduced, guild created, shares issued          |
| Guild creation — name unique            | Second guild with same name → REJECTED                        |
| Guild creation — insufficient balance   | REJECTED, no guild created                                    |
| Float shares held by guild              | Guild self-held shares = total \* float_pct                   |
| Guild share ISO created                 | ISO sell order exists for guild float shares                  |
| Guild share ISO matches                 | Buyer gets guild shares, proceeds to guild treasury           |
| Manual dividend distributes             | Guild treasury reduced, shareholders receive pro-rata         |
| Manual dividend — not leader            | REJECTED                                                      |
| Auto dividend each tick                 | Treasury decreases by pct, shareholders receive               |
| Guild invest creates order              | BUY order with guild_id set, escrow from guild treasury       |
| Guild invest — gate shares delivered    | Trade fills, shares in guild_gate_holdings                    |
| Guild receives yield from gate holdings | Yield paid to guild treasury (not to player)                  |
| Insolvent guild — yield penalty         | Insolvent guild receives 50% yield                            |
| Maintenance deducted each tick          | Guild treasury reduced by maintenance cost                    |
| Maintenance — insufficient funds        | Pay what's available, increment missed_maintenance_ticks      |
| Insolvency after 3 missed               | Guild status → INSOLVENT                                      |
| Recovery from insolvency                | Maintenance paid → back to ACTIVE, counters reset             |
| Dissolution after 10 insolvent          | Status → DISSOLVED, holdings liquidated, proceeds distributed |
| Dissolved guild orders cancelled        | Open orders cancelled, escrow released                        |
| Conservation after guild operations     | treasury + players + guilds = INITIAL_SEED                    |

### `test_guild_api.py` (API-level)

| Test                            | Assertion                                   |
| ------------------------------- | ------------------------------------------- |
| GET /guilds (empty)             | Returns empty list, 200                     |
| GET /guilds (with guilds)       | Returns guild list                          |
| GET /guilds/{id}                | Returns guild detail with members, holdings |
| GET /guilds/{id} nonexistent    | 404                                         |
| GUILD_SHARE on market endpoints | /market/GUILD_SHARE/{id} works              |

---

## Execution Order

```
Step 1:   Models                   → guild.py, update market.py + __init__.py
Step 2:   Migration + config       → migration, update config.py
Step 3:   TransferService update   → modify transfer.py (small)
Step 4:   Guild manager service    → services/guild_manager.py (largest file)
Step 5:   Update yield distribution → modify gate_lifecycle.py
Step 6:   Update order matching    → modify order_matching.py (significant)
Step 7:   Wire tick pipeline       → modify tick.py
Step 8:   State hash + tests       → modify state_hash.py, conftest.py
Step 9:   Schemas                  → schemas/guild.py
Step 10:  API routes               → api/guilds.py, update main.py
Step 11:  Tests                    → test_guild_manager.py, test_guild_api.py
```

### Estimated: ~4 new files, ~8 modified files, ~25 new tests.

---

## Key Design Decisions

| Decision                                            | Rationale                                                                                |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Guild holds own shares for ISO (player_id=guild.id) | Same no-FK UUID convention used everywhere. Clean separation from founder shares.        |
| Guild ISO price = creation_cost / total_shares      | No yield data at creation. Fair baseline. Market will reprice.                           |
| Guild ISO proceeds → guild treasury                 | Proper IPO model — raises capital for the guild, not the founder.                        |
| `balance_micro` property on Guild                   | Maps to `treasury_micro`, lets TransferService work without modification.                |
| Separate `guild_gate_holdings` table                | Clear separation from player gate shares. Avoids ambiguity in yield distribution.        |
| `guild_id` on Order (nullable)                      | Explicit marker for guild orders. Avoids UUID-type guessing.                             |
| No seller fee on guild ISO                          | Same pattern as gate ISO — bootstrap selling. Fee would be guild → treasury → pointless. |
| Maintenance cost = base + scaled                    | Small guilds pay base. Large guilds pay proportionally more. Anti-dominance.             |
| Insolvency → 50% yield                              | Punitive but not fatal. Gives time to recover.                                           |
| Dissolution liquidates at discount                  | Simpler than placing market sell orders. 50% discount ensures it's a penalty.            |
| Dividends skip guild-held shares                    | No self-payment. Same as treasury shares in gate yield.                                  |
| Leader-only for dividends and invest                | Simple access control. Officers can be added later.                                      |

---

## Edge Cases to Handle

| Edge Case                                    | Expected Behavior                                           |
| -------------------------------------------- | ----------------------------------------------------------- |
| Guild treasury = 0, maintenance due          | missed_maintenance_ticks incremented, no transfer           |
| Dividend with 0 treasury                     | REJECTED (or skip if auto)                                  |
| Guild invest when guild can't afford escrow  | REJECTED                                                    |
| Gate collapses while guild holds shares      | Holdings become worthless (quantity stays but gate is dead) |
| All guild shares sold in ISO                 | No transition — guild already ACTIVE                        |
| ISO partially fills                          | Remaining shares stay listed, guild keeps unsold            |
| Leader buys own guild shares                 | Valid — leader is also a shareholder                        |
| Player sells guild shares they don't own     | REJECTED at order placement                                 |
| Dissolved guild — player tries to trade      | Orders rejected (guild is dissolved)                        |
| Dissolved guild — yield from remaining gates | No yield — holdings liquidated to 0                         |
| Two guilds buy same gate shares              | Both orders valid — matched in price-time priority          |
| Guild recovers from insolvency               | Status back to ACTIVE, counters reset                       |
| Integer division remainder in dividends      | Stays in guild treasury — conservative, invariant-safe      |

---

## Dependencies

- Phase 2: TransferService (guild treasury operations)
- Phase 3: Tick pipeline, intent framework
- Phase 4: Gates, gate_shares, yield distribution
- Phase 5: Market system (guild shares use identical matching, ISO pattern)
