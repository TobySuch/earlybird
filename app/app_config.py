"""YAML-based application config loader.

Non-secret settings (Gmail label, cron schedule, etc.) live in data/config.yml.
Credentials remain in environment variables via app/config.py (Settings).

On startup, load_app_config() is called once. If data/config.yml doesn't exist it is
created with DEFAULTS so users have a self-documenting starting point.
"""

from pathlib import Path

import yaml

CONFIG_PATH = Path("data/config.yml")

DEFAULTS: dict = {
    "gmail": {
        # The Gmail label whose messages will be ingested each run.
        "label": "Newsletters",
        # This label is applied to messages after they are fetched so they are
        # skipped on future runs.
        "processed_label": "earlybird-processed",
        # How many days back to look for new messages on each run.
        "lookback_days": 7,
    },
    "schedule": {
        # APScheduler cron expression for the daily pipeline run.
        "cron": "0 7 * * 1-5",
        # Set to false to disable automatic scheduled runs entirely.
        "enabled": True,
    },
}

_config: dict | None = None


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_app_config(config_path: Path = CONFIG_PATH) -> dict:
    """Load config from *config_path*, creating it from DEFAULTS if absent.

    User values are merged on top of DEFAULTS so new keys added in future
    versions appear automatically with their default values.
    """
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w") as fh:
            yaml.dump(DEFAULTS, fh, default_flow_style=False, sort_keys=False)
        return DEFAULTS.copy()

    with config_path.open() as fh:
        user_cfg = yaml.safe_load(fh) or {}

    return _deep_merge(DEFAULTS, user_cfg)


def get_app_config() -> dict:
    """Return the cached application config, loading it on first call."""
    global _config
    if _config is None:
        _config = load_app_config()
    return _config


def _reset_cache() -> None:
    """Reset the in-memory cache. Used in tests only."""
    global _config
    _config = None
