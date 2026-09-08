"""Static unit-of-measure and currency conversion tables.

Every table maps a unit name or symbol to the factor that converts one of
that unit into the dimension's base unit (meters, grams, seconds, or US
dollars). Currency lookups prefer a live rate from
:mod:`engine.currency_rates` when one has been fetched (opt-in, see that
module), falling back to the static, approximate snapshot below.
"""

from __future__ import annotations

from . import currency_rates

_LENGTH_M: dict[str, float] = {
    "mm": 0.001,
    "millimeter": 0.001,
    "millimeters": 0.001,
    "millimetre": 0.001,
    "millimetres": 0.001,
    "cm": 0.01,
    "centimeter": 0.01,
    "centimeters": 0.01,
    "centimetre": 0.01,
    "centimetres": 0.01,
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "metre": 1.0,
    "metres": 1.0,
    "km": 1000.0,
    "kilometer": 1000.0,
    "kilometers": 1000.0,
    "kilometre": 1000.0,
    "kilometres": 1000.0,
    "in": 0.0254,
    "inch": 0.0254,
    "inches": 0.0254,
    "ft": 0.3048,
    "foot": 0.3048,
    "feet": 0.3048,
    "yd": 0.9144,
    "yard": 0.9144,
    "yards": 0.9144,
    "mi": 1609.344,
    "mile": 1609.344,
    "miles": 1609.344,
}

_MASS_G: dict[str, float] = {
    "mg": 0.001,
    "milligram": 0.001,
    "milligrams": 0.001,
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "kg": 1000.0,
    "kilogram": 1000.0,
    "kilograms": 1000.0,
    "lb": 453.592,
    "lbs": 453.592,
    "pound": 453.592,
    "pounds": 453.592,
    "oz": 28.3495,
    "ounce": 28.3495,
    "ounces": 28.3495,
}

_TIME_S: dict[str, float] = {
    "s": 1.0,
    "sec": 1.0,
    "secs": 1.0,
    "second": 1.0,
    "seconds": 1.0,
    "min": 60.0,
    "mins": 60.0,
    "minute": 60.0,
    "minutes": 60.0,
    "h": 3600.0,
    "hr": 3600.0,
    "hrs": 3600.0,
    "hour": 3600.0,
    "hours": 3600.0,
    "day": 86400.0,
    "days": 86400.0,
    "week": 604800.0,
    "weeks": 604800.0,
}

# Static, approximate rates relative to USD -- the fallback when no live
# rate has been fetched (see the module docstring).
_CURRENCY_CODES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.0,
    "CHF": 0.88,
    "CAD": 1.36,
    "AUD": 1.52,
}

#: Symbols that may prefix a number directly, e.g. ``$5``, mapped to the
#: ISO code a live rate would be keyed by.
_CURRENCY_SYMBOL_CODES: dict[str, str] = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
CURRENCY_SYMBOLS = frozenset(_CURRENCY_SYMBOL_CODES)

_DIMENSIONS: dict[str, dict[str, float]] = {
    "length": _LENGTH_M,
    "mass": _MASS_G,
    "time": _TIME_S,
}


def _lookup_currency(name: str) -> tuple[str, float] | None:
    code = _CURRENCY_SYMBOL_CODES.get(name)
    if code is None:
        code = name.upper()
        if code not in _CURRENCY_CODES:
            return None
    live_rate = currency_rates.get_live_rate(code)
    factor = live_rate if live_rate is not None else _CURRENCY_CODES[code]
    return "currency", factor


def lookup_unit(name: str) -> tuple[str, float] | None:
    """Looks up a unit by name or symbol.

    Args:
        name: The raw unit token as written by the user, e.g. ``"km"``,
            ``"USD"``, or ``"$"``.

    Returns:
        A ``(dimension, factor)`` pair, where ``factor`` converts one of
        this unit into the dimension's base unit, or ``None`` if ``name``
        is not a recognized unit or currency.
    """
    key = name.lower()
    for dimension, table in _DIMENSIONS.items():
        factor = table.get(key)
        if factor is not None:
            return dimension, factor
    return _lookup_currency(name)


def unit_factor(name: str) -> float:
    """Returns the base-unit conversion factor for a known unit.

    Args:
        name: A unit name or symbol previously validated by
            :func:`lookup_unit`.

    Returns:
        The factor that converts one of ``name`` into its dimension's base
        unit.

    Raises:
        ValueError: If ``name`` is not a recognized unit or currency.
    """
    info = lookup_unit(name)
    if info is None:
        raise ValueError(f"Unknown unit: {name}")
    return info[1]
