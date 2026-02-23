.PHONY: up down build logs test lint migrate migration shell reset

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f

test:
	docker compose exec api pytest -v

lint:
	docker compose exec api ruff check app/ tests/
	docker compose exec api mypy app/ --ignore-missing-imports

migrate:
	docker compose exec api alembic upgrade head

migration:
	docker compose exec api alembic revision --autogenerate -m "$(msg)"

shell:
	docker compose exec api bash

reset:
	docker compose down -v
	docker compose up -d