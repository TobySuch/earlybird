# Contributing to Earlybird

## Development setup

```bash
git clone https://github.com/TobySuch/earlybird.git
cd earlybird
cp .env.example .env   # fill in SECRET_KEY + at least GMAIL_CLIENT_ID/SECRET + one LLM key
make install           # Python deps (uv) + frontend deps (bun) + pre-commit hook
make db-init           # create/migrate the SQLite database
make dev               # start server with hot reload + Tailwind watch
```

Tests use an in-memory SQLite database and mock external APIs — no live credentials needed to run them:

```bash
make test   # run pytest
make lint   # auto-fix with ruff (check + format)
```

## Commit messages

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>
```

Common types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `style`, `ci`.

Examples:
- `feat(pipeline): add Gmail OAuth2 fetch in ingest.py`
- `fix(scheduler): read cron expression from DB config on startup`
- `test(api): add status endpoint integration tests`

The pre-commit hook and CI will reject commits that don't conform.

## Pull requests

- Open a PR against `main`.
- Include tests for any new or changed logic — see `tests/` which mirrors the `app/` layout.
- Keep PRs focused; one logical change per PR.
