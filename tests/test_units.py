"""Tests for units of measure, currency, and unit conversion."""

from __future__ import annotations

import pytest

from engine.errors import EvalError
from engine.evaluator import Environment, evaluate_line
from engine.values import Quantity


def _eval(line: str) -> object:
    return evaluate_line(line, Environment())


def test_quantity_literal() -> None:
    result = _eval("5 km")
    assert isinstance(result, Quantity)
    assert result.dimension == "length"
    assert result.magnitude == pytest.approx(5000)


def test_same_dimension_addition_converts() -> None:
    result = _eval("5 km + 200 m")
    assert isinstance(result, Quantity)
    assert result.magnitude == pytest.approx(5200)
    assert result.unit == "km"  # follows the left operand's unit


def test_mismatched_dimension_addition_raises() -> None:
    with pytest.raises(EvalError):
        _eval("5 km + 200 g")


def test_quantity_scaled_by_plain_number() -> None:
    result = _eval("2 * 3 kg")
    assert isinstance(result, Quantity)
    assert result.magnitude == pytest.approx(6000)


def test_quantity_divided_by_same_dimension_is_plain_ratio() -> None:
    result = _eval("10 km / 2 km")
    assert result == pytest.approx(5)


def test_currency_symbol_prefix() -> None:
    result = _eval("$5 + $3")
    assert isinstance(result, Quantity)
    assert result.dimension == "currency"
    assert result.magnitude == pytest.approx(8)


def test_currency_code_suffix() -> None:
    result = _eval("5 USD")
    assert isinstance(result, Quantity)
    assert result.dimension == "currency"


def test_convert_with_in_keyword() -> None:
    result = _eval("1 km in m")
    assert isinstance(result, Quantity)
    assert result.unit == "m"
    assert result.magnitude == pytest.approx(1000)


def test_convert_with_as_keyword() -> None:
    result = _eval("3 as USD")
    assert isinstance(result, Quantity)
    assert result.dimension == "currency"
    assert result.magnitude == pytest.approx(3)


def test_convert_mismatched_dimension_raises() -> None:
    with pytest.raises(EvalError):
        _eval("5 km in kg")


def test_percent_of_a_quantity() -> None:
    result = _eval("20% of 5 km")
    assert isinstance(result, Quantity)
    assert result.magnitude == pytest.approx(1000)
