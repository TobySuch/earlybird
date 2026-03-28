# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Earlybird is a personal newsletter aggregator and podcast generator. It reads newsletters from Gmail, uses Claude Haiku to filter and summarise stories based on user interests, produces a daily digest viewable in a web UI, and optionally generates a TTS podcast episode uploaded to Audiobookshelf or served via a private RSS feed.

## Commands

Always use Makefile targets instead of running tools directly.

```bash
make install       # install Python deps (uv) + frontend deps (bun) + pre-commit hook
make dev           # run server with hot reload + Tailwind watch mode
make test          # run pytest
make lint          # auto-fix with ruff (check + format)
make build-assets  # compile frontend assets (JS vendor copy + Tailwind CSS)
make db-init       # create/migrate SQLite tables
make docker-up     # start Docker Compose stack
make docker-down   # stop Docker Compose stack
make clean         # remove build artefacts
```

To run a single test directly:
```bash
uv run pytest tests/path/to/test_file.py::test_name
```

## Commits

All commits must use the Conventional Commits format:

```
<type>(<scope>): <short summary>
```

Common types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `style`, `ci`.

Examples:
- `feat(pipeline): add Gmail OAuth2 fetch in ingest.py`
- `fix(scheduler): read cron expression from DB config on startup`
- `test(api): add status endpoint integration tests`
- `chore(deps): add ruff and pre-commit to dev dependencies`

## Tests

Always write tests when adding or modifying logic. Place tests under `tests/` mirroring the `app/` layout (e.g. `app/pipeline/ingest.py` → `tests/pipeline/test_ingest.py`).

- Use `fastapi.testclient.TestClient` for route tests.
- Use `pytest` fixtures for DB sessions — never use the production DB.
- Test pipeline stages with fixture data rather than live Gmail/Claude/TTS calls.
- Run `make test` before committing.

## Architecture

**Stack:** Python + FastAPI backend, HTMX + AlpineJS frontend (Jinja2 templates, no build step), SQLite via SQLAlchemy, APScheduler embedded in FastAPI.

**Project layout:**
```
app/
  main.py          # FastAPI entrypoint, mounts routers, starts scheduler
  scheduler.py     # APScheduler setup; job calls pipeline in sequence
  config.py        # Settings from .env + DB config table
  models.py        # SQLAlchemy ORM models
  database.py      # Session management
  pipeline/
    ingest.py      # Gmail OAuth2 fetch, label-as-processed, store stories
    process.py     # Claude Haiku: filter by interests, summarise, write script
    publish.py     # TTS (OpenAI or ElevenLabs), ABS upload
  routers/
    ui.py          # HTMX web UI (dashboard, episodes, sources, settings, run log)
    api.py         # JSON API (trigger run, status, feed config)
templates/         # Jinja2 HTML
static/            # CSS, minimal JS
```

**Pipeline flow:** APScheduler (cron) → `ingest.py` fetches Gmail since last `runs.started_at` → stories stored in DB → `process.py` sends to Claude Haiku → episode row written → `publish.py` generates MP3 and uploads to ABS.

**Key design decisions:**
- Scheduling uses `runs.started_at` as the fetch window boundary, not wall-clock time — skipping weekends never drops stories.
- All user settings (API keys, interest profile, TTS voice, ABS URL, cron schedule) live in the `config` key/value table, editable via the Settings UI.
- The RSS podcast feed (`/feed.xml`) is disabled by default and served at a hard-to-guess URL when enabled.
- Single Docker container with SQLite and Gmail OAuth token as mounted volumes; sits behind Traefik.

**Database tables:** `runs`, `sources`, `stories`, `episodes`, `config` — see `app/models.py` for the full schema.

**LLM usage:** Claude Haiku only, invoked in `pipeline/process.py`. User provides a natural-language interest profile stored in `config` that is injected into the prompt.
