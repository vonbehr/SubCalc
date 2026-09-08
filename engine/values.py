"""Runtime value types produced by evaluation, beyond plain numbers."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class Quantity:
    """A numeric magnitude tagged with a unit of measure or currency.

    Attributes:
        magnitude: The value expressed in the dimension's base unit (e.g.
            meters for length, grams for mass, seconds for time, US dollars
            for currency), so that same-dimension quantities can be combined
            without repeated conversion.
        dimension: The physical dimension, e.g. ``"length"``, ``"mass"``,
            ``"time"``, or ``"currency"``.
        unit: The unit to display the magnitude in, e.g. ``"km"`` -- the
            unit the value was most recently expressed or converted to.
    """

    magnitude: float
    dimension: str
    unit: str


@dataclass(frozen=True)
class DateValue:
    """A calendar date, produced by a date literal or ``today``."""

    date: datetime.date


@dataclass(frozen=True)
class TimeValue:
    """A time of day, produced by a time literal (``14:30``) or ``now``."""

    time: datetime.time


Value = Union[float, Quantity, DateValue, TimeValue]
