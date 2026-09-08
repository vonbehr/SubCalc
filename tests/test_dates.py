"""Tests for date literals, ``today``, and date arithmetic."""

from __future__ import annotations

import datetime

import pytest

from engine.errors import EvalError, SubCalcError
from engine.evaluator import Environment, evaluate_line
from engine.values import DateValue, Quantity


def _eval(line: str) -> object:
    return evaluate_line(line, Environment())


def test_date_literal() -> None:
    result = _eval("2024-01-01")
    assert result == DateValue(datetime.date(2024, 1, 1))


def test_invalid_date_literal_is_not_a_date() -> None:
    """An invalid calendar date (e.g. month 13) fails to parse as a date.

    So the line is silently treated as prose rather than crashing.
    """
    with pytest.raises(SubCalcError):
        _eval("2024-13-01")


def test_today() -> None:
    assert _eval("today") == DateValue(datetime.date.today())


def test_date_plus_days() -> None:
    result = _eval("2024-01-01 + 30 days")
    assert result == DateValue(datetime.date(2024, 1, 31))


def test_date_minus_days() -> None:
    result = _eval("2024-01-31 - 30 days")
    assert result == DateValue(datetime.date(2024, 1, 1))


def test_date_to_date_via_to_keyword() -> None:
    result = _eval("2024-01-01 to 2024-06-01")
    assert isinstance(result, Quantity)
    assert result.dimension == "time"
    assert result.magnitude / 86400 == pytest.approx(152)


def test_date_minus_date() -> None:
    result = _eval("2024-06-01 - 2024-01-01")
    assert isinstance(result, Quantity)
    assert result.magnitude / 86400 == pytest.approx(152)


def test_to_requires_two_dates() -> None:
    with pytest.raises(EvalError):
        _eval("5 to 10")


def test_date_plus_date_raises() -> None:
    with pytest.raises(EvalError):
        _eval("2024-01-01 + 2024-06-01")
