"""Tests for time-of-day literals, ``now``, and time arithmetic."""

from __future__ import annotations

import datetime

import pytest

from engine.errors import EvalError, SubCalcError
from engine.evaluator import Environment, evaluate_line
from engine.values import Quantity, TimeValue


def _eval(line: str) -> object:
    return evaluate_line(line, Environment())


def test_time_literal_hh_mm() -> None:
    assert _eval("14:30") == TimeValue(datetime.time(14, 30))


def test_time_literal_hh_mm_ss() -> None:
    assert _eval("14:30:15") == TimeValue(datetime.time(14, 30, 15))


def test_invalid_time_literal_raises() -> None:
    with pytest.raises(SubCalcError):
        _eval("25:99")


def test_now() -> None:
    result = _eval("now")
    assert isinstance(result, TimeValue)
    # Sanity check only -- can't assert an exact value against a live clock.
    assert 0 <= result.time.hour <= 23


def test_time_plus_minutes() -> None:
    result = _eval("14:30 + 90 min")
    assert result == TimeValue(datetime.time(16, 0))


def test_time_minus_minutes() -> None:
    result = _eval("14:30 - 90 min")
    assert result == TimeValue(datetime.time(13, 0))


def test_time_addition_wraps_past_midnight() -> None:
    result = _eval("23:30 + 90 min")
    assert result == TimeValue(datetime.time(1, 0))


def test_time_subtraction_wraps_before_midnight() -> None:
    result = _eval("00:30 - 1 hour")
    assert result == TimeValue(datetime.time(23, 30))


def test_time_minus_time_is_a_duration() -> None:
    result = _eval("16:00 - 14:30")
    assert isinstance(result, Quantity)
    assert result.dimension == "time"
    assert result.unit == "hours"
    assert result.magnitude / 3600 == pytest.approx(1.5)


def test_time_to_time_via_to_keyword() -> None:
    result = _eval("14:30 to 16:00")
    assert isinstance(result, Quantity)
    assert result.magnitude / 3600 == pytest.approx(1.5)


def test_short_time_difference_displays_in_minutes() -> None:
    """A sub-hour gap reads as '10 minutes', not '0.166667 hours'."""
    result = _eval("07:05 to 07:15")
    assert isinstance(result, Quantity)
    assert result.unit == "minutes"
    assert result.magnitude / 60 == pytest.approx(10)


def test_time_difference_can_be_negative() -> None:
    """Unlike addition, subtraction/'to' does not wrap.

    An earlier end time yields a negative duration, matching
    date-difference semantics.
    """
    result = _eval("14:00 to 12:00")
    assert isinstance(result, Quantity)
    assert result.magnitude / 3600 == pytest.approx(-2)


def test_to_requires_two_times_or_two_dates() -> None:
    with pytest.raises(EvalError):
        _eval("14:30 to 2024-01-01")


def test_time_plus_time_raises() -> None:
    with pytest.raises(EvalError):
        _eval("14:30 + 15:00")
