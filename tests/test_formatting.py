"""Tests for engine.formatting.

Covers number, quantity, date, and rounding-mode display.
"""

from __future__ import annotations

import datetime

from engine.formatting import format_number, format_value
from engine.values import DateValue, Quantity


def test_integer_has_no_decimal_point() -> None:
    assert format_number(42.0) == "42"


def test_trailing_zeros_are_trimmed() -> None:
    assert format_number(1.5000) == "1.5"


def test_thousands_separator() -> None:
    assert format_number(1234567) == "1,234,567"


def test_thousands_separator_can_be_disabled() -> None:
    assert format_number(1234567, thousands_separator=False) == "1234567"


def test_negative_zero_normalizes_to_zero() -> None:
    assert format_number(-0.0004, decimal_places=2) == "0"


def test_decimal_places_are_respected() -> None:
    assert format_number(1 / 3, decimal_places=2) == "0.33"


def test_scientific_notation_for_very_large_numbers() -> None:
    assert format_number(6.02e23) == "6.02e+23"


def test_scientific_notation_for_very_small_numbers() -> None:
    assert format_number(0.0000001, decimal_places=6) == "1e-07"


def test_rounding_mode_half_up() -> None:
    assert format_number(2.5, decimal_places=0, rounding_mode="half_up") == "3"


def test_rounding_mode_half_even_is_the_default() -> None:
    assert format_number(2.5, decimal_places=0) == "2"
    assert format_number(3.5, decimal_places=0) == "4"


def test_rounding_mode_floor() -> None:
    assert format_number(2.9, decimal_places=0, rounding_mode="floor") == "2"


def test_rounding_mode_ceil() -> None:
    assert format_number(2.1, decimal_places=0, rounding_mode="ceil") == "3"


def test_format_value_quantity() -> None:
    quantity = Quantity(magnitude=5200, dimension="length", unit="km")
    assert format_value(quantity) == "5.2 km"


def test_format_value_date() -> None:
    value = DateValue(datetime.date(2024, 6, 1))
    assert format_value(value) == "2024-06-01"


def test_format_value_plain_number() -> None:
    assert format_value(12.5) == "12.5"
