# Dungeon Gate Economy UI Redesign

**Direction:** Realm Sanctum (visual v2)

**Date:** 2026-07-22

**Scope:** Player-facing information architecture, interaction language, visual system, and state handling

## Visual V2 — Realm Sanctum

The first implementation improved clarity but still looked like a themed web
dashboard: repeated rectangular panels, a permanent text sidebar, small labels,
and no strong fantasy-world focal point. Visual v2 keeps the verified economy
flow while replacing that presentation.

- A project-owned cinematic gate environment anchors login and the Sanctum.
- The desktop shell is now a top game HUD plus compact tool rail; mobile uses a
  five-action dock and full-screen navigation drawer.
- The home screen is an in-world sanctum with one active mission, real portfolio
  state, and four large actions around the gate—not a grid of equal widgets.
- Cyan rift light, indigo stone, violet magic, and small amber coin accents
  replace the flat obsidian-and-brass treatment.
- Decorative Cinzel is restricted to display text. Oxanium, Rajdhani, and
  JetBrains Mono keep controls and economy data readable.
- The art lives at `frontend/public/assets/gate-sanctum-v2.webp`; code-native
  overlays, focus states, responsive layouts, and reduced-motion behavior remain
  functional without inventing combat stats, levels, or equipment systems.

## Product Position

Dungeon Gate Economy is an occult market game, not a generic finance dashboard
and not a dungeon-combat RPG. The player discovers temporary income-producing
gates, owns and trades their shares, earns yield while they remain active, and
tries to exit before instability turns into collapse.

The redesign presents that existing simulation as **The Obsidian Exchange**: a
fantasy command hall where every screen helps the player answer four questions:

1. What should I do now?
2. What will resolve on the next world cycle?
3. What is earning coin for me?
4. What is in danger of collapsing?

The interface may call the player a hunter, scout, founder, or trader, but those
are thematic roles. It must not imply combat, equipment, character levels,
raids, or other systems that the backend does not implement.

## Evidence-Backed Diagnosis

The simulation already contains the useful game: deterministic cycles, gate
discovery, finder shares, gate yield and collapse, a limit-order market, guild
treasuries, events, news, and seasonal rankings. The earlier interface obscured
that game for several concrete reasons.

- The main loop was split across nine similarly weighted navigation entries.
  Discovery looked like a separate application instead of the opening action
  in the gate-ownership loop.
- Screens led with market and database language: intents, ticks, UUIDs, raw
  event keys, float percentages, and ledger rows. The player had to infer why
  any of it mattered.
- A successful API response only means that an action was queued. The actual
  mutation occurs in the simulation pipeline on a later world cycle. Weak
  queued-action feedback made correct behavior feel broken.
- New accounts were sent to a dense exchange dashboard without a first
  objective, even though the natural starting move is an inexpensive E-rank
  expedition.
- Late-game guild creation was presented beside first-session actions despite
  costing `¤50` while a player starts with `¤10`.
- The portfolio projection existed, but the Profile page emphasized account
  metadata and raw ledger entries instead of ownership, income, and danger.
- Empty screens did not consistently distinguish a new player, an empty filter,
  a paused simulation, a stopped worker, and a genuine request failure.
- At audit time, the freshly reset local world had human accounts but no ticks,
  gates, orders, guilds, seasons, or AI liquidity, and its worker was stopped.
  In that condition every command remains queued indefinitely. Visual polish
  cannot make a dormant simulation feel playable.

The authoritative action sequence is visible in
[`backend/app/simulation/tick.py`](../backend/app/simulation/tick.py): queued
intents are processed first, followed by gate and guild lifecycles, ISO orders,
matching, prices, events, news, maintenance, and rankings.

## Actual Gameplay Flow

```text
CREATE ACCOUNT
    |
    | receive ¤10 starting coin
    v
COMMAND CHAMBER
    |
    | recommended first move: E-rank expedition (¤0.10)
    v
LAUNCH EXPEDITION
    |
    | DISCOVER_GATE command enters Action Queue
    v
NEXT WORLD CYCLE
    |
    +---- rejected --------------------> explain reason + recover
    |
    `---- discovered gate
             |
             | player receives 10% finder stake
             v
          OFFERING
             |
             | initial shares trade, or offering window expires
             v
           ACTIVE <---------------------------+
             |                                |
             | share yield paid each cycle    | buy / sell / rebalance
             | stability decays               |
             v                                |
          UNSTABLE                            |
             |                                |
             | no normal yield                |
             | growing collapse probability   |
             v                                |
          COLLAPSED --------------------------+
             |
             | shares lose value; orders close
             v
      GROW NET WORTH / SEASON SCORE
             |
             | later milestone: ¤50
             v
         FOUND A GUILD
             |
             | invest treasury, maintain solvency,
             | trade guild shares, distribute dividends
             `------------------------------------------>
```

The player-visible resources are deliberately small in number:

| Resource | Meaning |
| --- | --- |
| Coin `¤` | Spendable player cash. One displayed coin is one million stored micro-units. |
| Locked coin | Cash reserved by open buy orders. It remains part of net worth but cannot be spent twice. |
| Gate shares | Ownership that can earn yield while the gate is ACTIVE and can be traded until collapse. |
| Guild shares | Ownership in a guild and its dividend economy. |
| Stability | Gate safety. Rank-specific collapse thresholds matter more than a generic color. |
| Yield / cycle | Projected income from active gate positions. |
| Net worth | Cash, locked cash, and marked gate/guild positions. |
| Season score | Net-worth-based ranking with inactivity decay. It is not XP. |

## Five Player Areas

The routes remain small and composable, but the player should understand them
as five areas rather than a collection of CRUD pages.

### 1. Command Chamber

**Primary route:** `/dashboard`  
**Purpose:** Answer “what should I do now?” and provide one safe return point
after every action.

The chamber contains:

- one state-driven objective with one primary CTA;
- world state and current cycle;
- cash, locked coin, net worth, yield/cycle, and dangerous exposure;
- current gate positions and the most urgent risk;
- pending commands and open orders;
- a compact world dispatch;
- first-session quest progress.

Objective priority is deterministic:

```text
world halted
  > dangerous owned gate
  > pending command
  > no gate position
  > active position / growth objective
```

This prevents a page full of equally loud widgets from competing with the next
move. The implemented shell and objective language live in
[`Layout.tsx`](../frontend/src/components/Layout.tsx) and
[`DashboardPage.tsx`](../frontend/src/features/dashboard/DashboardPage.tsx).

### 2. Gate Atlas and Expeditions

**Routes:** `/discover`, `/gates`, `/gates/:gateId`  
**Purpose:** Discover gates, compare opportunities, understand lifecycle risk,
and make a buy/hold/sell decision.

The expedition desk presents rank selection as a two-step contract:

1. choose the minimum acceptable rank;
2. review cost, possible yield, starting stability, finder stake, affordability,
   world state, and the next-cycle delay before launching.

The Gate Atlas separates lifecycle states—OFFERING, ACTIVE, UNSTABLE, and
COLLAPSED—and compares mark price, yield, stability buffer, risk, spread, and
volume. A filter with no matches is not the same as a world with no gates.

The gate chamber is a decision workstation. Its order of importance is:

1. identity, rank, lifecycle status, and rank-specific collapse line;
2. the player’s stake, marked value, and projected yield;
3. visible risk and price history;
4. order book and exact server preview;
5. recent trades and secondary ownership detail.

### 3. Hunter Chronicle and Action Queue

**Routes:** `/profile`, `/orders`  
**Purpose:** Explain what the player owns, where coin moved, what is pending,
and whether a command actually succeeded.

The Chronicle is the inventory/portfolio surface, not merely an account page.
It prioritizes positions, ownership percentage, yield, marked value, collapse
buffer, liquid cash, and locked cash. The accounting ledger is secondary proof.

The Action Queue translates backend intent states into player language:

| Backend state | Player meaning |
| --- | --- |
| `QUEUED` | Command accepted; waiting for a world cycle. |
| `PROCESSING` | The world engine is resolving the command. |
| `EXECUTED` | Command completed; show the concrete result when available. |
| `REJECTED` | Nothing changed; show the reason and a recovery action. |
| Order `OPEN` | Placed on the market; locked coin or shares remain committed. |
| Order `PARTIAL` | Some shares traded; the remainder is still open. |
| Order `FILLED` | The complete quantity traded. |
| Order `CANCELLED` | Remaining escrow/shares are released. |

“Command accepted” must never be written as though discovery, purchase, or
guild creation has already happened.

### 4. Guild Hall

**Routes:** `/guilds`, `/guilds/create`, `/guilds/:guildId`  
**Purpose:** Present guilds as a later economic strategy layer.

The Hall supports two different users:

- an investor browsing and trading guild shares;
- a guild leader managing treasury, gate investments, maintenance, and
  dividends.

Guild founding is visibly a `¤50` milestone, not the recommended first action.
The create contract explains public float, founder ownership, retained treasury
capital, dividend policy, maintenance, and next-cycle resolution in plain
language. A leader chooses a named gate from the Atlas; no primary interaction
should require copying a raw gate UUID.

The UI must not offer join, invite, raid, voting, or member-management flows
until corresponding backend actions exist.

### 5. World and Season

**Routes:** `/news`, `/events`, `/leaderboard`  
**Purpose:** Turn simulation output into actionable context and long-term goals.

World Dispatches answer “what changed?” Active Omens answer “what is affecting
my assets?” The Season Crown answers “how am I progressing relative to other
players?” They are related context views rather than three unrelated databases.

Every gate- or guild-targeted item should link to the affected entity. Raw event
payload keys are secondary diagnostics; the primary sentence explains the
player impact, such as reduced stability, bonus yield, or newly spawned gates.

An active season correctly has no final-result rows. “No live season,”
“unranked,” “rankings not updated yet,” and “no completed season” are distinct
states.

The field manual at `/guide` supports all five areas. Account controls and the
admin console are utilities, not additional player areas.

## State Design

### Global States

| State | Required treatment |
| --- | --- |
| Auth bootstrap | Branded shell skeleton; do not flash the login screen. |
| World live | Show current cycle and a restrained live pulse. |
| Simulation paused | Persistent banner explaining that commands can be prepared but not resolved. |
| Worker stopped/stale | Treat as “world halted,” not merely “feed offline.” Never imply that a queued command will resolve soon. |
| Realtime disconnected | Explain that polling continues; do not mark the entire world halted solely from WebSocket state. |
| Partial API failure | Keep successful panels usable and put retry controls inside the failed panel. |
| Authentication expired | Preserve the intended destination, clear private cache, and return to login safely. |

### Area State Matrix

| Area | Loading | Empty / first-time | Error / special state |
| --- | --- | --- | --- |
| Command Chamber | Skeletons matching objective, stats, positions, and feed geometry | Guided first expedition; never a blank dashboard | World-halted objective, section-local retries, dangerous-position override |
| Expedition desk | Rank-card and contract skeletons | No profiles means configuration is incomplete, not “nothing found” | Unaffordable rank, dormant world, submission rejection, persistent queued receipt |
| Gate Atlas | Stable card/table skeletons | Distinguish no gates in the world from no filter matches | Reset filters, retry request, stale-market note |
| Gate chamber | Hero, position, chart, book, and ticket skeletons | Separate no position, no bids, no asks, and no trades | 404, OFFERING education, UNSTABLE warning, COLLAPSED memorial state, preview rejection |
| Chronicle | Position and summary skeletons | No holdings with Expedition and Atlas CTAs | Portfolio error independent from ledger error |
| Action Queue | Timeline skeletons | Explain next-cycle commands and link to a first expedition | Queued too long, processing, rejected with recovery, partial fill, cancellation pending |
| Guild Hall | Guild-card skeletons | No guilds in world versus no guild position | Founder locked by insufficient coin, non-leader view, INSOLVENT warning, DISSOLVED final state |
| World | Dispatch/omen skeletons | No cycles yet versus no matching filter | Linkable target, human-readable impact, local retry |
| Season | Podium/table skeleton | No season, unranked player, or no completed results | Ranking update cadence and inactivity state explained |

Loading skeletons preserve the final layout and hierarchy. A full-page spinner
is reserved for protected-route bootstrap or a route whose identity cannot yet
be known. Empty states always answer why the area is empty and give the next
valid action. Error states never erase already loaded economic information.

## Obsidian Exchange Art Direction

### Mood

The exchange combines an occult guild archive, a cartographer’s gate atlas, and
a high-stakes trading hall. It is dark, mineral, tactile, and legible. Fantasy
comes from sigils, rank crests, illuminated borders, gate-state language, and
world-cycle behavior—not ornamental clutter or invented combat imagery.

Avoid:

- generic blue SaaS cards;
- stock candlestick-dashboard templates;
- excessive glass blur, gradients, or pill badges;
- anonymous UUIDs as visual identity;
- decorative charts that are not backed by trades;
- fantasy illustrations that promise combat or exploration gameplay that does
  not exist.

### Palette

| Role | Dark theme | Light theme | Meaning |
| --- | --- | --- | --- |
| Void / canvas | `#020405`, `#08100e` | `#eaf0ee`, `#f7fbf9` | Obsidian chamber or pale mineral vellum |
| Surface | `#0d1513`, `#151d1b` | `#f7fbf9`, `#edf5f2` | Panels and contracts |
| Exchange gold | `#ffe16d` | `#a16900` | Primary action, coin, selected contract |
| Aether cyan | `#00dce5` | `#006f78` | Live world, discovery, market information |
| Stable green | `#38c172` | `#0f7a4f` | Income, completion, healthy stability |
| Warning amber | `#f1b347` | `#a16900` | Offering, watch state, pending risk |
| Collapse red | `#f16858` | `#b33a34` | Rejection, critical risk, collapse |
| Guild violet | restrained accent | restrained accent | Guild-specific ownership and strategy |

Risk color never replaces text, status, or a numeric threshold.

### Typography

- **Libre Caslon Text:** screen titles, contract titles, and important lore
  sentences.
- **Alegreya Sans:** navigation, explanations, labels, controls, and body copy.
- **JetBrains Mono:** coin, prices, quantities, tick numbers, and identifiers.

Large serif titles establish game identity; plain sans-serif explanation keeps
the rules understandable. Monospace is for exact data, not whole paragraphs.

### Geometry and Texture

- Use compact, hard-edged panels with an approximately `8px` radius.
- Fine mineral borders and two restrained corner marks make a panel feel like
  an exchange plate or field contract.
- Selected and dangerous states use a border/accent shift before adding glow.
- Rank crests and the gate sigil are stable visual identifiers.
- Background grids and grain remain subtle enough that tables and forms retain
  high contrast.
- Icons come from one line-icon family and support labels; they do not replace
  unfamiliar game terms.

### Motion

Motion communicates state:

- a slow pulse for a live world feed;
- a brief resolving animation for a queued command;
- stability and exposure bars transitioning when new cycle data arrives;
- a restrained receipt entrance after an action.

Do not continuously animate every panel. Respect `prefers-reduced-motion`, and
ensure no action depends on animation to be understood.

### Responsive Behavior

- Desktop uses a persistent command sidebar and top resource strip.
- Mobile uses a four-item bottom dock plus a labeled navigation drawer.
- Dense market tables become decision cards or horizontally scroll only when
  column comparison remains essential.
- Primary controls remain at least `44px` high and do not depend on hover.
- The world-halted state, action receipt, balance, and current objective remain
  visible on narrow screens.

## Reusable UI Primitives

The implementation centralizes game presentation in
[`GameUI.tsx`](../frontend/src/components/game/GameUI.tsx).

| Primitive | Responsibility |
| --- | --- |
| `ScreenHeader` | Eyebrow, one clear title, plain-language purpose, and optional primary action |
| `GamePanel` | Themed content surface with a restrained semantic accent |
| `PanelHeading` | Panel title, one-line explanation, and local action |
| `StatRune` | Exact value, label, supporting note, and semantic tone |
| `RankCrest` | Stable E through S+ rank identity |
| `StabilityMeter` | Stability value plus authoritative rank threshold and safety buffer |
| `GameAction` | Route-changing CTA with primary/secondary/ghost/danger hierarchy |
| `GameButton` | Mutation control using the same hierarchy |
| `GameEmpty` | Reason, consequence, and next valid route |
| `PlainTip` | Short rule explanation placed beside the decision it affects |

Shared loading, error, status, and pagination components remain structural
utilities. They should be visually adapted to the same language rather than
reimplemented per feature.

## Reusable Page Scaffolds

### Command Hub

```text
ScreenHeader
  ObjectivePanel + primary action
  ResourceStrip (4-6 StatRunes)
  MainGrid
    OwnedPositions / Opportunities
    PendingActions / WorldDispatch
  ContextualQuest
```

Use for the Command Chamber and any later role-specific headquarters.

### Atlas / Catalog

```text
ScreenHeader + create/discover action
  WorldCounts
  FilterBar
  Loading | GlobalEmpty | FilterEmpty | Results
  Pagination
```

Use for gate and guild discovery lists. Global empty and filtered empty require
different copy and actions.

### Decision Workstation

```text
IdentityHeader (name, ticker, rank, lifecycle)
  RiskAndHistoryPanel | PlayerPositionPanel
  ExactMarketStats
  OrderBook | ActionContract
  RecentActivity
  SecondaryIdentityAndOwnership
```

Use for gate and guild-share detail. The action contract stays beside the data
needed to make that decision.

### Expedition / Contract

```text
ScreenHeader
  StepOneChoiceGrid | StepTwoContractSummary
  Cost + affordability + balance after action
  Consequence + resolution timing
  Submit control
  Persistent receipt
```

Use for discovery, guild founding, and other multi-parameter irreversible or
delayed actions.

### Chronicle / Feed

```text
ScreenHeader
  SummaryStrip
  Filters or tabs
  Loading | FirstTime | FilterEmpty | Timeline/Table
  Detail disclosure
```

Use for portfolio history, action results, world dispatches, omens, and season
history.

## Interaction and Copy Rules

Every economic action must show, before submission:

- what the command does;
- the immediate cost or locked amount;
- the player’s balance or shares after submission when known;
- whether it resolves now or on a future world cycle;
- the principal risk;
- the exact reason the current command is disabled.

Use player language first and engine terminology second:

| Avoid as primary copy | Prefer |
| --- | --- |
| “Submit DISCOVER_GATE intent” | “Launch E-rank expedition” |
| “Tick #42” | “World cycle 42” |
| “Intent queued” alone | “Command accepted; waiting for the next world cycle” |
| “Insufficient balance: 100000” | “You need ¤0.10 more coin” |
| Raw asset UUID | Gate name and ticker, with short ID as secondary detail |
| `STABILITY_CRISIS: -7.25` | “Stability crisis: this gate lost 7.25 safety points” |

Do not hide exact market mechanics. Fees, escrow, price limits, quantities, and
partial fills remain visible inside the advanced portion of the decision
surface.

## Truth Rules

The frontend is a projection of the server-authoritative economy.

- Use `/players/me/portfolio` for cash, locked cash, marked value, net worth,
  projected yield, and dangerous exposure.
- Use `/market/overview` for comparable price, yield, risk, spread, and volume.
- Use `/market/order-preview` for fees, escrow, spendable cash, and sellable
  shares. Do not recreate fee rules locally.
- Use each rank’s collapse threshold. Do not infer danger from one global
  stability cutoff.
- Never fabricate market history when no trades exist.
- Never show a countdown unless the server provides reliable cadence/ETA data.
- Never call an action complete from the POST response alone; follow its queued
  intent through execution or rejection.
- Treat OFFERING, ACTIVE, UNSTABLE, and COLLAPSED as economic states, not merely
  badge colors.
- Treat profile lifespan fields as descriptive only until the lifecycle engine
  actually enforces them.

## Remaining Backend and Product Blockers

### P0 — Playability and action trust

1. **World bootstrap and worker health**  
   A clean database plus a stopped worker produces no ticks, gates, seasons, or
   resolvable actions. The product needs an explicit bootstrap/demo policy and
   a server-reported worker heartbeat. A cosmetic empty state is not a fix.

2. **Typed action result receipts**  
   `IntentResponse` exposes type, status, rejection reason, and processed tick,
   but no original payload, created gate/guild/order ID, fills, transfers, or
   result summary. The Action Queue cannot reliably explain or deep-link an
   executed command. Add a typed result envelope per intent type.

3. **Authoritative world-cycle timing**  
   Simulation status lacks tick interval, next expected cycle, active phase,
   last worker heartbeat, and stale threshold. The UI can say live/halted from
   current evidence, but cannot offer a truthful countdown or distinguish a
   long cycle from a dead worker.

### P1 — Decision quality and first-session pacing

4. **Complete gate decision projection**  
   Gate detail should include rank-specific collapse threshold, authoritative
   risk band, offering end/remaining cycles, lifecycle explanation, and market
   identity in one response. The current non-owner detail fallback can use
   generic thresholds and disagree with the market overview.

5. **Public economy-rules projection**  
   Starting coin, finder percentage, offering duration, guild cost, fee rules,
   ownership cap, yield concentration bands, maintenance, and season cadence
   are mutable settings but are not available through a safe player-facing
   rules endpoint. Hardcoded educational copy will drift.

6. **Starter-loop delay**  
   A discovered gate starts in OFFERING and normally waits 60 cycles before
   activation unless initial inventory sells. At the nominal five-second
   cadence this is about five minutes, longer when cycles overrun. Provide an
   intentional starter-gate policy, shorter first offering, or a fully visible
   activation objective so onboarding does not stall.

7. **Fresh-world liquidity**  
   With AI seeding disabled and only one or two humans, treasury ISO asks may
   let a player buy, but there may be no credible exit bid. Define a test/demo
   liquidity policy separately from human account cleanup.

8. **Names in action and ownership read models**  
   Orders, intent history, guild members, and guild gate holdings expose raw IDs
   where the UI needs ticker, display name, username, mark, and risk. Add
   enriched read models instead of requiring client-side N+1 lookups.

### P2 — Strategic depth and content clarity

9. **Guild capability boundary**  
   There is no join/invite/member-management action despite a member model.
   Either add a deliberate guild membership loop or keep guild UX explicitly
   focused on founding, shares, treasury investment, maintenance, and dividends.

10. **Actionable world events**  
    Events should provide a normalized player-impact summary and direct entity
    links. News already carries related entity identity, but the presentation
    should use it consistently.

11. **Lifecycle lifespan truth**  
    Rank profiles expose `lifespan_min` and `lifespan_max`, while actual collapse
    is driven by stability decay and probability rather than those bounds.
    Enforce the fields, replace them with an honest projection, or stop
    presenting them as an expected lifespan.

12. **Durable onboarding progress**  
    The first quest can be inferred from positions and pending actions, but a
    server-backed tutorial/result state would survive devices and avoid
    misclassifying veteran accounts that sold all holdings.

## Acceptance Standard

The redesign is successful when a new player can sign in and, without external
documentation, explain all of the following:

- “I own temporary gate shares, not a dungeon fighter.”
- “My commands resolve on world cycles.”
- “Only active gates pay yield.”
- “Stability crossing this gate’s collapse line is dangerous.”
- “Open buy orders lock some of my coin.”
- “My next sensible action is visible on the Command Chamber.”
- “A guild is a later wealth-management milestone.”
- “If the world engine is halted, the interface tells me that actions cannot
  resolve.”

The visual test is equally simple: at a glance, the product should read as one
coherent occult economy game—not a collection of admin tables wearing fantasy
labels.
