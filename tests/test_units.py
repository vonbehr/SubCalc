"""Tests for units of measure, currency, and unit conversion."""

from __future__ import annotations

import pytest

from engine import currency_rates, units
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


def test_currency_symbol_postfix() -> None:
    """'500$' (symbol after the number) works the same as '$500'."""
    result = _eval("500$")
    assert isinstance(result, Quantity)
    assert result.dimension == "currency"
    assert result.unit == "$"
    assert result.magnitude == pytest.approx(500)


def test_convert_with_in_keyword() -> None:
    result = _eval("1 km in m")
    assert isinstance(result, Quantity)
    assert result.unit == "m"
    assert result.magnitude == pytest.approx(1000)


def test_convert_to_a_currency_symbol() -> None:
    """The 'in'/'as' target can be a currency symbol, not just a code."""
    result = _eval("500$ in €")
    assert isinstance(result, Quantity)
    assert result.unit == "€"
    assert result.magnitude == pytest.approx(500)  # base (USD) magnitude unchanged


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


# -- Live rates (see engine.currency_rates; network calls are mocked there,
# these tests just fake a cached rate directly) --------------------------


def test_lookup_unit_prefers_a_live_rate_over_the_static_table() -> None:
    currency_rates._live_rates["EUR"] = 0.5  # deliberately not the static 0.92
    dimension, factor = units.lookup_unit("EUR")
    assert dimension == "currency"
    assert factor == pytest.approx(0.5)


def test_lookup_unit_falls_back_to_the_static_table_when_no_live_rate() -> None:
    dimension, factor = units.lookup_unit("EUR")
    assert dimension == "currency"
    assert factor == pytest.approx(0.92)


def test_currency_symbol_resolves_to_its_live_rate_too() -> None:
    """'€' and 'EUR' share one live rate, keyed by the ISO code."""
    currency_rates._live_rates["EUR"] = 0.5
    dimension, factor = units.lookup_unit("€")
    assert dimension == "currency"
    assert factor == pytest.approx(0.5)
