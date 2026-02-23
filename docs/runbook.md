# Dungeon Gate Economy — Runbook

## Prerequisites

- Docker Desktop running
- `make` installed (`choco install make` on Windows)

## Start Everything

    make up

Boots Postgres, Redis, API (port 8000), and worker.

## Verify

    curl http://localhost:8000/health
    curl http://localhost:8000/ready

## Run Migrations

    make migrate

## Create a New Migration

    make migration msg="add players table"

## Run Tests

    make test

## Lint & Type Check

    make lint

## View Logs

    make logs

## Full Reset (destroy volumes)

    make reset

## Interactive Shell (inside API container)

    make shell
