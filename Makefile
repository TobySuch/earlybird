.PHONY: install dev test lint lint-check build-assets db-init docker-build docker-up docker-down clean

# ── Python / uv ───────────────────────────────────────────────────────────────
install:
	uv sync --all-groups
	bun install
	uv run pre-commit install

dev:
	bun run build-css && bun run dev-css & trap 'kill %1' EXIT INT; uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest

lint:
	uv run ruff check --fix .
	uv run ruff format .

lint-check:
	uv run ruff check .
	uv run ruff format --check .

# ── Frontend / bun ────────────────────────────────────────────────────────────
build-assets:
	bun run build

# ── Database ──────────────────────────────────────────────────────────────────
db-init:
	uv run python -c "from app.database import init_db; init_db()"

db-migrate:
	uv run alembic revision --autogenerate -m "$(msg)"

db-upgrade:
	uv run alembic upgrade head

db-downgrade:
	uv run alembic downgrade -1

# ── Docker ────────────────────────────────────────────────────────────────────
docker-build:
	docker compose build

docker-up: docker-build
	mkdir -p data
	docker compose up -d

docker-down:
	docker compose down

# ── Housekeeping ──────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache
	rm -f static/js/htmx.min.js static/js/alpine.min.js static/css/main.css
