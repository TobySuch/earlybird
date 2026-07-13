---
name: verify
description: How to run and drive earlybird for end-to-end verification without Gmail or real LLM keys.
---

# Verifying earlybird changes

## Launch against a scratch DB

```bash
SCRATCH=$(mktemp -d)
DATABASE_URL="sqlite:///$SCRATCH/verify.db" uv run alembic upgrade head
# create a login user (auth routes live under /auth/*)
DATABASE_URL="sqlite:///$SCRATCH/verify.db" uv run python -c "
from sqlalchemy.orm import Session
from app.database import engine
from app.models import User
from app.auth import hash_password
with Session(engine) as db:
    db.add(User(username='preview', password_hash=hash_password('preview'))); db.commit()"
DATABASE_URL="sqlite:///$SCRATCH/verify.db" OPENAI_API_KEY=fake uv run uvicorn app.main:app --port 18080
```

Login: `curl -c cookies.txt -X POST http://127.0.0.1:18080/auth/login -d "username=preview&password=preview"` (NOT `/login` — 404). Settings POST redirects 303 to `/settings?saved=1`; missing form fields silently reset to CONFIG_DEFAULTS, so pass every field you care about.

## Faking the LLM

Set `llm.provider=openai` and `llm.openai_base_url` (or the per-role `llm.reporter.*` / `llm.editor.*` keys) to a local fake OpenAI-compatible server that answers `POST /v1/chat/completions`. Route canned responses by system-prompt content: reporter prompts contain "reporter on a podcast production team", editor rundown "editor-in-chief", assembly "writing the final", digest "expert newsletter editor", headlines "podcast episode summarizer". Log the request `model` field to verify per-role routing.

## Driving the pipeline without Gmail

Full runs (`POST /api/run/trigger`) need Gmail OAuth. To exercise process/publish only, seed `Run` + `NewsSource` rows in the scratch DB and call `process.run(db, run)` — the exact call `scheduler.execute_pipeline` makes. Episodes render at `/` (dashboard) and `/episodes/{id}`.
