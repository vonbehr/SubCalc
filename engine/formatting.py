"""Formats numeric results for display as inline phantoms."""

from __future__ import annotations


def format_number(
    value: float, decimal_places: int = 6, thousands_separator: bool = True
) -> str:
    """Formats a number for display, trimming insignificant trailing zeros.

    Args:
        value: The number to format.
        decimal_places: The maximum number of digits shown after the decimal
            point. Trailing zeros beyond the value's actual precision are
            trimmed, so an integer result never shows a decimal point.
        thousands_separator: Whether to group the integer part with commas.

    Returns:
        The formatted string, e.g. ``"1,234.5"`` or ``"42"``.
    """
    rounded = round(value, decimal_places)
    if rounded == 0:
        rounded = 0.0  # normalizes -0.0 to 0.0

    separator = "," if thousands_separator else ""

    if rounded == int(rounded):
        return f"{int(rounded):{separator}}"

    text = f"{rounded:{separator}.{decimal_places}f}"
    return text.rstrip("0").rstrip(".")
