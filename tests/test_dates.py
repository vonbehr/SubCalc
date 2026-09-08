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


# -- Alternate date formats -------------------------------------------------


def test_dotted_date_zero_padded() -> None:
    assert _eval("05.07.2026") == DateValue(datetime.date(2026, 7, 5))


def test_dotted_date_unpadded() -> None:
    assert _eval("5.7.2026") == DateValue(datetime.date(2026, 7, 5))


def test_dotted_date_two_digit_year() -> None:
    assert _eval("5.7.26") == DateValue(datetime.date(2026, 7, 5))


def test_dotted_date_two_digit_year_pivots_to_1900s() -> None:
    """69-99 maps to 1969-1999, matching the POSIX/glibc %y convention."""
    assert _eval("5.7.99") == DateValue(datetime.date(1999, 7, 5))


def test_german_date_with_month_name() -> None:
    assert _eval("5. Juni 2026") == DateValue(datetime.date(2026, 6, 5))


def test_german_date_month_abbreviation() -> None:
    assert _eval("5. Jun 2026") == DateValue(datetime.date(2026, 6, 5))


def test_german_date_is_case_insensitive() -> None:
    assert _eval("5. juni 2026") == DateValue(datetime.date(2026, 6, 5))


def test_dotted_date_arithmetic() -> None:
    result = _eval("05.07.2026 + 10 days")
    assert result == DateValue(datetime.date(2026, 7, 15))


def test_invalid_dotted_date_raises() -> None:
    with pytest.raises(SubCalcError):
        _eval("32.13.2026")


def test_plain_decimal_number_is_unaffected() -> None:
    """'5.7' alone stays a plain float, not a date.

    The day.month.year pattern requires all three dotted parts.
    """
    assert _eval("5.7") == pytest.approx(5.7)
