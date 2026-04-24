"""Tests for make_cron_trigger's correct day-of-week mapping, and run_retention."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Config, Episode, NewsSource, Run
from app.scheduler import make_cron_trigger, run_retention


def _fire_dates(cron: str, count: int = 7, start: datetime | None = None) -> list[str]:
    """Return the weekday names of the next *count* fire times."""
    trigger = make_cron_trigger(cron)
    if start is None:
        # Monday 2026-04-13 00:00 UTC
        start = datetime(2026, 4, 13, 0, 0, tzinfo=timezone.utc)
    current = start
    days = []
    for _ in range(count):
        next_time = trigger.get_next_fire_time(None, current)
        if next_time is None:
            break
        days.append(next_time.strftime("%A"))
        current = next_time.replace(second=1)
    return days


def test_weekdays_numeric_range():
    """0 6 * * 1-5 must fire Monday through Friday, never Saturday or Sunday."""
    days = _fire_dates("0 6 * * 1-5", count=10)
    assert "Saturday" not in days
    assert "Sunday" not in days
    assert days[:5] == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def test_weekdays_comma_list():
    days = _fire_dates("0 6 * * 1,2,3,4,5", count=10)
    assert "Saturday" not in days
    assert "Sunday" not in days


def test_sunday_zero():
    """Day 0 in crontab means Sunday."""
    days = _fire_dates("0 6 * * 0", count=3)
    assert all(d == "Sunday" for d in days)


def test_sunday_seven():
    """Day 7 in crontab is also Sunday."""
    days = _fire_dates("0 6 * * 7", count=3)
    assert all(d == "Sunday" for d in days)


def test_every_day_wildcard():
    days = _fire_dates("0 6 * * *", count=7)
    assert len(set(days)) == 7  # all 7 distinct weekdays appear


def test_named_days_passthrough():
    """Named days (mon-fri) should work too."""
    days = _fire_dates("0 6 * * mon-fri", count=10)
    assert "Saturday" not in days
    assert "Sunday" not in days


def test_invalid_field_count():
    with pytest.raises(ValueError, match="5 cron fields"):
        make_cron_trigger("0 6 * *")


# ── run_retention ─────────────────────────────────────────────────────────────


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _set_config(db, key: str, value: str) -> None:
    db.add(Config(key=key, value=value))
    db.commit()


def _make_run_and_episode(db, age_days: int, audio_path: str | None = None) -> Episode:
    """Insert a Run + Episode created `age_days` ago."""
    created = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=age_days)
    run = Run(started_at=created, status="success")
    db.add(run)
    db.commit()
    source = NewsSource(run_id=run.id, title="T", source_type="gmail", source_name="S")
    db.add(source)
    episode = Episode(run_id=run.id, created_at=created, audio_path=audio_path)
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode


def _patch_session(db_session):
    """Return a context manager that patches SessionLocal to return db_session."""
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=db_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    # run_retention calls SessionLocal() directly (not as context manager)
    return patch("app.scheduler.SessionLocal", return_value=db_session)


def test_retention_no_op_when_disabled(db_session):
    _set_config(db_session, "retention.enabled", "false")
    _make_run_and_episode(db_session, age_days=60)

    with _patch_session(db_session):
        run_retention()

    assert db_session.query(Episode).count() == 1


def test_retention_skips_recent_episodes(db_session):
    _set_config(db_session, "retention.enabled", "true")
    _set_config(db_session, "retention.max_days", "30")
    _make_run_and_episode(db_session, age_days=5)

    with _patch_session(db_session):
        run_retention()

    assert db_session.query(Episode).count() == 1


def test_retention_deletes_old_episode_run_and_sources(db_session):
    _set_config(db_session, "retention.enabled", "true")
    _set_config(db_session, "retention.max_days", "30")
    _make_run_and_episode(db_session, age_days=45)

    with _patch_session(db_session):
        run_retention()

    assert db_session.query(Episode).count() == 0
    assert db_session.query(NewsSource).count() == 0
    assert db_session.query(Run).count() == 0


def test_retention_deletes_audio_file(db_session, tmp_path):
    _set_config(db_session, "retention.enabled", "true")
    _set_config(db_session, "retention.max_days", "30")
    audio = tmp_path / "episode_1.mp3"
    audio.write_bytes(b"fake-mp3")
    _make_run_and_episode(db_session, age_days=45, audio_path=str(audio))

    with _patch_session(db_session):
        run_retention()

    assert not audio.exists()
    assert db_session.query(Episode).count() == 0


def test_retention_handles_missing_audio_gracefully(db_session, tmp_path):
    _set_config(db_session, "retention.enabled", "true")
    _set_config(db_session, "retention.max_days", "30")
    missing = str(tmp_path / "nonexistent.mp3")
    _make_run_and_episode(db_session, age_days=45, audio_path=missing)

    with _patch_session(db_session):
        run_retention()  # must not raise

    assert db_session.query(Episode).count() == 0
