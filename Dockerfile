FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python deps (production only — no dev group)
COPY pyproject.toml .
RUN uv sync --no-dev

# Copy pre-built frontend assets (run `make build-assets` before `docker build`)
COPY static/ static/
COPY templates/ templates/
COPY app/ app/

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
