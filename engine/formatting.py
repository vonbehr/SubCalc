"""Formats evaluated values for display as inline phantoms."""

from __future__ import annotations

import decimal

from . import units
from .values import DateValue, Quantity, TimeValue, Value

_SCIENTIFIC_HIGH = 1e15
_SCIENTIFIC_LOW = 1e-6

_ROUNDING_MODES = {
    "half_up": decimal.ROUND_HALF_UP,
    "floor": decimal.ROUND_FLOOR,
    "ceil": decimal.ROUND_CEILING,
}


def _round(value: float, decimal_places: int, rounding_mode: str) -> float:
    """Rounds ``value`` to ``decimal_places`` using the requested mode.

    Args:
        value: The number to round.
        decimal_places: How many digits to keep after the decimal point.
        rounding_mode: One of ``"half_even"`` (Python's built-in
            round-half-to-even, the default), ``"half_up"``, ``"floor"``, or
            ``"ceil"``.

    Returns:
        The rounded value.

    Raises:
        ValueError: If ``rounding_mode`` is not recognized.
    """
    if rounding_mode == "half_even":
        return round(value, decimal_places)
    mode = _ROUNDING_MODES.get(rounding_mode)
    if mode is None:
        raise ValueError(f"Unknown rounding mode: {rounding_mode}")
    quantum = decimal.Decimal(1).scaleb(-decimal_places)
    rounded = decimal.Decimal(str(value)).quantize(quantum, rounding=mode)
    return float(rounded)


def _format_scientific(value: float, decimal_places: int) -> str:
    mantissa_places = max(decimal_places, 2)
    text = f"{value:.{mantissa_places}e}"
    mantissa, exponent = text.split("e")
    mantissa = mantissa.rstrip("0").rstrip(".")
    exponent_value = int(exponent)
    sign = "+" if exponent_value >= 0 else "-"
    return f"{mantissa}e{sign}{abs(exponent_value):02d}"


def format_number(
    value: float,
    decimal_places: int = 6,
    thousands_separator: bool = True,
    rounding_mode: str = "half_even",
) -> str:
    """Formats a number for display, trimming insignificant trailing zeros.

    Args:
        value: The number to format.
        decimal_places: The maximum number of digits shown after the decimal
            point. Trailing zeros beyond the value's actual precision are
            trimmed, so an integer result never shows a decimal point.
        thousands_separator: Whether to group the integer part with commas.
        rounding_mode: One of ``"half_even"``, ``"half_up"``, ``"floor"``, or
            ``"ceil"``; see :func:`_round`.

    Returns:
        The formatted string, e.g. ``"1,234.5"``, ``"42"``, or ``"6.02e+23"``
        for magnitudes at or beyond 1e15, or below 1e-6.
    """
    if value != 0 and (abs(value) >= _SCIENTIFIC_HIGH or abs(value) < _SCIENTIFIC_LOW):
        return _format_scientific(value, decimal_places)

    rounded = _round(value, decimal_places, rounding_mode)
    if rounded == 0:
        rounded = 0.0  # normalizes -0.0 to 0.0

    separator = "," if thousands_separator else ""

    if rounded == int(rounded):
        return f"{int(rounded):{separator}}"

    text = f"{rounded:{separator}.{decimal_places}f}"
    return text.rstrip("0").rstrip(".")


def format_value(
    value: Value,
    decimal_places: int = 6,
    thousands_separator: bool = True,
    rounding_mode: str = "half_even",
) -> str:
    """Formats any evaluated value -- a number, quantity, or date.

    Args:
        value: The value to format, as produced by
            :func:`engine.evaluator.eval_node`.
        decimal_places: See :func:`format_number`.
        thousands_separator: See :func:`format_number`.
        rounding_mode: See :func:`format_number`.

    Returns:
        The formatted string, e.g. ``"1,234.5"``, ``"5.2 km"``,
        ``"2024-06-01"``, or ``"14:30"``.
    """
    if isinstance(value, Quantity):
        display = value.magnitude / units.unit_factor(value.unit)
        number = format_number(display, decimal_places, thousands_separator, rounding_mode)
        return f"{number} {value.unit}"
    if isinstance(value, DateValue):
        return value.date.isoformat()
    if isinstance(value, TimeValue):
        pattern = "%H:%M" if value.time.second == 0 else "%H:%M:%S"
        return value.time.strftime(pattern)
    return format_number(value, decimal_places, thousands_separator, rounding_mode)
