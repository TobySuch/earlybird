# earlybird

<img src="static/earlybird.svg" alt="Earlybird logo" width="80" height="80">

Personal newsletter aggregator and podcast generator. Fetches newsletters from Gmail, summarises stories with Claude Haiku, produces a daily digest, and optionally generates a TTS podcast episode.

## Setup

### 1. Google Cloud / Gmail API

You need a Google Cloud project with the Gmail API enabled and an OAuth2 client to let Earlybird read your inbox.

**Create the project and enable Gmail:**

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a new project (e.g. `earlybird`).
2. In the left menu go to **APIs & Services → Library**, search for **Gmail API**, and click **Enable**.

**Configure the OAuth consent screen:**

1. Go to **APIs & Services → OAuth consent screen**.
2. Choose **External** (even for personal use — Internal requires a Workspace account).
3. Fill in the required fields:
   - App name: `Earlybird`
   - User support email: your Gmail address
   - Developer contact email: your Gmail address
4. Click through **Scopes** (no extra scopes needed here — they're requested at runtime) and **Test users**.
5. On the **Test users** step, add your own Gmail address. While the app is in "Testing" mode only listed test users can authorise it.
6. Save and continue through to the summary.

**Create OAuth2 credentials:**

1. Go to **APIs & Services → Credentials** and click **+ Create Credentials → OAuth client ID**.
2. Choose **Web application** as the application type.
3. Give it a name (e.g. `Earlybird web`).
4. Under **Authorised redirect URIs** add the callback URL for your deployment:
   - Local dev: `http://localhost:8000/auth/gmail/callback`
   - Production (behind Traefik): `https://earlybird.yourdomain.com/auth/gmail/callback`
5. Click **Create**. Copy the **Client ID** and **Client secret** — you'll need them next.

### 2. Environment variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

Key variables:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Random secret for session signing. Generate with `openssl rand -hex 32`. |
| `GMAIL_CLIENT_ID` | OAuth2 Client ID from step above. |
| `GMAIL_CLIENT_SECRET` | OAuth2 Client Secret from step above. |
| `ANTHROPIC_API_KEY` | Claude API key for summarisation. |
| `OPENAI_API_KEY` | OpenAI API key for TTS (optional). |
| `ABS_URL` | Base URL of your Audiobookshelf instance (optional). |
| `ABS_API_KEY` | ABS API token (optional). |

### 3. Gmail label

Earlybird filters by a Gmail label rather than scanning your whole inbox. Create the label in Gmail first:

1. In Gmail, click **+ Create new label** (left sidebar) and name it (e.g. `Newsletters`).
2. Set up a filter (**Settings → Filters and Blocked Addresses → Create a new filter**) to automatically apply that label to incoming newsletters.

Then tell Earlybird which label to use in the **Settings** page of the web UI after first login.

### 4. Install and run

```bash
make install   # install Python deps + frontend deps + pre-commit hook
make db-init   # apply all migrations (creates DB on first run)
make dev       # run with hot reload
```

### 5. Authorise Gmail

On first run, visit `http://localhost:8000/auth/gmail` in your browser. You'll be redirected to Google's OAuth consent screen — sign in with the Gmail account you added as a test user. After approving, you'll be redirected back and the token is saved to `data/token.json`.

You only need to do this once. The token is refreshed automatically.

## Docker

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2 (`docker compose`)
- A filled-in `.env` file (see [Environment variables](#2-environment-variables) above)

### Running standalone (port 8000)

```bash
cp .env.example .env      # fill in SECRET_KEY, GMAIL_*, ANTHROPIC_API_KEY
mkdir -p data             # persisted DB, token, and audio live here
make docker-up            # builds image and starts container
```

The app is now available at `http://localhost:8000`.

### First-run setup

1. **Create your account.** On first startup the container generates a one-time pairing code. Check the logs:

   ```bash
   docker compose logs earlybird | grep "Pairing code"
   ```

   Visit `http://localhost:8000/auth/signup`, enter the code, and set your password.

2. **Authorise Gmail.** Visit `http://localhost:8000/auth/gmail`. You'll be redirected to Google's OAuth consent screen — sign in with the Gmail account you added as a test user. After approving, the token is saved to `./data/token.json` and refreshed automatically from then on.

3. **Configure settings.** Visit `http://localhost:8000/settings` to set your Gmail label, interest profile, and any optional TTS settings.

### Rebuilding after code changes

```bash
make docker-up   # always rebuilds before starting
```

## Development

```bash
make test    # run pytest
make lint    # auto-fix with ruff
```

Tests use an in-memory SQLite database and mock the Gmail API — no live credentials needed.

## Database migrations

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/). Migrations live in `migrations/versions/`.

On startup (and via `make db-init`) the app automatically runs `alembic upgrade head`, so deployments pick up new migrations without manual intervention.

### Creating a migration

After editing `app/models.py`, autogenerate a migration from the diff:

```bash
make db-migrate msg="add foo column to runs"
```

Review the generated file in `migrations/versions/` before committing — autogenerate is good but not perfect (it won't detect column renames, for example).

### Applying migrations manually

```bash
make db-upgrade    # apply all pending migrations
make db-downgrade  # roll back the last migration
```

Or use Alembic directly for more control:

```bash
uv run alembic current          # show current revision
uv run alembic history          # list all revisions
uv run alembic upgrade head     # apply all pending
uv run alembic downgrade -1     # roll back one step
uv run alembic downgrade base   # roll back everything
```

### Existing databases (pre-migration)

If you have a database created before migrations were introduced, `init_db()` detects the missing `alembic_version` table and stamps it at `head` automatically. No data is lost and no tables are recreated.
