# ── Stage 1: Build frontend assets ───────────────────────────────────────────
FROM oven/bun:1-slim AS frontend
WORKDIR /build

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY static/ static/
COPY templates/ templates/

RUN bun run build

# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.14-slim
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies from lock file (no dev group)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY app/ app/
COPY migrations/ migrations/
COPY alembic.ini ./
COPY templates/ templates/
COPY --from=frontend /build/static/ static/

EXPOSE 8000
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
