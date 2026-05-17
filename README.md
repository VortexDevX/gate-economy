<div align="center">

# Dungeon Gate Economy

### Simulation-first closed-loop economy where dungeon gates become tradable assets

<p>
  <img src="https://img.shields.io/badge/FastAPI-111827?style=for-the-badge" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Python-111827?style=for-the-badge" alt="Python" />
  <img src="https://img.shields.io/badge/React-111827?style=for-the-badge" alt="React" />
  <img src="https://img.shields.io/badge/Simulation-111827?style=for-the-badge" alt="Simulation" />
  <img src="https://img.shields.io/badge/Market%20Engine-111827?style=for-the-badge" alt="Market Engine" />
  <img src="https://img.shields.io/badge/PostgreSQL-111827?style=for-the-badge" alt="PostgreSQL" />
</p>
<p>
  <a href="https://github.com/VortexDevX/gate-economy"><img src="https://img.shields.io/badge/GitHub%20Repo-111827?style=for-the-badge" alt="GitHub Repo" /></a>
</p>

</div>

---

## Overview

Dungeon Gate Economy models a player-driven market around dungeon gates, deterministic ticks, player intents, matching, guild economics, AI traders, and anti-exploit monitoring. The cleanup keeps simulation logic and conservation assumptions intact.

<table>
<tr>
<td width="25%"><strong>Status</strong></td>
<td>Simulation and frontend/backend app in progress</td>
</tr>
<tr>
<td><strong>Stack</strong></td>
<td>FastAPI, SQLAlchemy, Alembic, Pydantic, React/Vite, TypeScript, market simulation services</td>
</tr>
<tr>
<td><strong>Built for</strong></td>
<td>Developers exploring game economy simulation and deterministic market systems</td>
</tr>
</table>

## Highlights

- Closed-loop monetary and market simulation concepts
- Intent APIs, order matching, metrics, and admin-style surfaces
- Python backend plus Vite/React frontend layout
- Migrations left behaviorally untouched
- Screenshot placeholder folder added

## Feature Map

<table>
<tr>
<td width="50%" valign="top">

### Economy Core

Gates, shares, intents, orders, ticks, guilds, and market events.

</td>
<td width="50%" valign="top">

### Backend

FastAPI service with schemas, services, tests, and Alembic migrations.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### Frontend

React/Vite app for interacting with the simulation surface.

</td>
<td width="50%" valign="top">

### Invariants

Conservation and market assumptions should be changed only with tests.

</td>
</tr>
</table>

## Quick Start

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

cd ../frontend
npm install
npm run dev
```

## Project Structure

- backend/ - FastAPI simulation API
- backend/app/ - schemas, services, simulation modules
- frontend/ - Vite/React interface
- docs/ - architecture, runbook, screenshots

## Screenshots

Use `docs/screenshots/` for real screenshots when the simulation UI is ready.

## Notes

- Simulation logic and conservation invariants were not changed.
- Migrations were not behaviorally modified.
- Do not run database migrations as part of README cleanup.

---

<div align="center">

<strong>Clean docs. Clear setup. No fake screenshots.</strong>

</div>
