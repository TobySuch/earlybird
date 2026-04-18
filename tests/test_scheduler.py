"""Tests for make_cron_trigger's correct day-of-week mapping."""

from datetime import datetime, timezone

import pytest

from app.scheduler import make_cron_trigger


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
