"""Tests for app/app_config.py — YAML config loading and auto-generation."""

import yaml

import app.app_config as app_config_module
from app.app_config import DEFAULTS, _deep_merge, _reset_cache, load_app_config


def test_generates_config_file_when_absent(tmp_path):
    config_path = tmp_path / "config.yml"
    assert not config_path.exists()

    result = load_app_config(config_path)

    assert config_path.exists()
    assert result == DEFAULTS


def test_generated_file_is_valid_yaml(tmp_path):
    config_path = tmp_path / "config.yml"
    load_app_config(config_path)

    with config_path.open() as fh:
        parsed = yaml.safe_load(fh)

    assert parsed["gmail"]["label"] == DEFAULTS["gmail"]["label"]


def test_loads_existing_config(tmp_path):
    config_path = tmp_path / "config.yml"
    config_path.write_text("gmail:\n  label: MyLabel\n  processed_label: done\n")

    result = load_app_config(config_path)

    assert result["gmail"]["label"] == "MyLabel"
    assert result["gmail"]["processed_label"] == "done"


def test_missing_keys_filled_from_defaults(tmp_path):
    """A user config that only overrides some keys should still get default values for others."""
    config_path = tmp_path / "config.yml"
    # Only override the label, leave processed_label and schedule absent
    config_path.write_text("gmail:\n  label: Custom\n")

    result = load_app_config(config_path)

    assert result["gmail"]["label"] == "Custom"
    assert result["gmail"]["processed_label"] == DEFAULTS["gmail"]["processed_label"]
    assert result["schedule"]["cron"] == DEFAULTS["schedule"]["cron"]


def test_get_app_config_caches_result(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yml"
    monkeypatch.setattr(app_config_module, "CONFIG_PATH", config_path)
    _reset_cache()

    first = app_config_module.get_app_config()
    second = app_config_module.get_app_config()

    assert first is second  # same object — cache hit


def test_deep_merge_nested():
    base = {"a": {"x": 1, "y": 2}, "b": 3}
    override = {"a": {"y": 99, "z": 0}, "c": 4}
    merged = _deep_merge(base, override)

    assert merged == {"a": {"x": 1, "y": 99, "z": 0}, "b": 3, "c": 4}


def test_empty_config_file_returns_defaults(tmp_path):
    config_path = tmp_path / "config.yml"
    config_path.write_text("")  # empty file → yaml.safe_load returns None

    result = load_app_config(config_path)

    assert result == DEFAULTS
