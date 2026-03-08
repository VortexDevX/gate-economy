# Frontend Plan (Post-Backend-Completion)

## Goal

Build a production-ready React frontend that matches the **current backend contracts** and does not require backend-breaking changes later.

---

## Source of Truth

1. `docs/plan/PLAN.md` (Phase 12 intent)
2. Actual backend API/schemas in `backend/app/api/*` and `backend/app/schemas/*`
3. `docs/CONTEXT.md` for current-state conventions

If any conflict exists, use the current backend contract and update docs.

---

## Locked Backend Contracts (Must Match UI)

### Auth
- `POST /auth/register` returns **PlayerResponse** (not tokens)
- `POST /auth/login` returns `access_token`, `refresh_token`, `token_type`
- `POST /auth/refresh` takes `{ "refresh_token": "..." }` and returns new access token

### Player
- `GET /players/me` returns role-aware profile (`role` now present)
- `GET /players/me/ledger` uses page/size style pagination

### Market + Lists
- Mixed pagination styles exist:
  - `limit/offset`: `/news`, `/events`, `/orders/me`, `/market/*/trades`, `/gates`, `/guilds`
  - `page/page_size`: `/leaderboard`, `/seasons`, `/players/me/ledger`

### Realtime
- WS endpoints:
  - public: `WS /ws`
  - authenticated: `WS /ws/feed?token=<access>`
- Current WS payload is `tick_update` with tick number + compact news list.
- Prices/portfolio/leaderboard are refreshed via API after tick events.

### Admin
- Admin endpoints are available and role-protected (`ADMIN`).

---

## Stack (Approved)

- React 18 + TypeScript + Vite
- TailwindCSS
- React Router
- Axios client
- React Query (`@tanstack/react-query`) for server state
- Zustand for minimal app state (auth/session + WS connection state)

---

## Delivery Milestones

## M1 — App Foundation + Auth
- Scaffold frontend app
- Axios client with auth header + refresh interceptor
- Auth store/context (login/logout/refresh bootstrap)
- Public/protected routes
- Pages: Login, Register, Dashboard shell

Acceptance:
- Register then login flow works end-to-end
- Token refresh works on 401 without page crash

## M2 — Core Read Views
- Dashboard: simulation status + player balance + quick cards
- Gates list/detail
- Profile + ledger table
- News + events pages

Acceptance:
- All pages load from real APIs with loading/error/empty states

## M3 — Trading UX
- Market detail (price, order book, trades)
- Order form (BUY/SELL intent submission)
- My orders page + cancel intent action
- Currency/percent formatting utilities

Acceptance:
- Place/cancel intents from UI successfully
- Order status updates visible after subsequent ticks

## M4 — Guild UX
- Guild list/detail
- Create guild intent form
- Guild actions (dividend/invest) for leaders
- Guild share trading entrypoints to market page

Acceptance:
- Guild lifecycle actions can be executed from UI through intents

## M5 — Leaderboard + Seasons + Admin
- Leaderboard pages and season result browsing
- `/leaderboard/me` card and row highlighting
- Admin-only section:
  - pause/resume
  - parameters list/edit
  - treasury view
  - conservation audit
  - ledger browser
  - event trigger
  - season create/end

Acceptance:
- Non-admin blocked from admin routes
- Admin operations reflected in UI with clear status feedback

## M6 — Realtime + Polish
- WS manager with reconnect/backoff
- On `tick_update`, invalidate React Query caches selectively:
  - simulation status
  - news/events
  - market data for open views
  - player profile/orders
- Responsive layout polish + accessibility pass

Acceptance:
- UI updates within 1 tick without manual refresh
- Stable behavior under disconnect/reconnect

---

## Cross-Cutting Rules

- All state-changing gameplay actions go through `/intents`
- Use micro-unit conversion helpers consistently
- Never hardcode enum labels; use API values
- Keep endpoint wrappers typed and centralized under `src/api`
- Avoid optimistic economic state writes; prefer “pending intent” UX

---

## Suggested Structure

```
frontend/
  src/
    api/
    app/
    components/
    features/
      auth/
      dashboard/
      gates/
      market/
      guilds/
      news/
      leaderboard/
      admin/
    hooks/
    stores/
    utils/
    routes/
```

---

## Definition of Done (Frontend)

- All player-facing Phase 12 flows from `PLAN.md` are reachable via UI
- Admin panel supports current Phase 11 backend APIs
- No contract mismatch with backend schemas/routes
- Mobile/tablet/desktop layouts usable
- No critical console/network errors in standard flows
