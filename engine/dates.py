"""Date-literal parsing: ISO, dotted, and German month-name formats.

Three shapes are recognized as a date:

- ISO: ``2026-07-05``
- Dotted day.month.year (the European convention): ``05.07.2026``,
  ``5.7.2026``, or with a 2-digit year, ``5.7.26``
- German day. Month year: ``5. Juni 2026``

The tokenizer embeds :data:`TOKEN_PATTERN` (a regex fragment, not compiled
on its own) to recognize any of these as a single ``DATE`` token;
:func:`parse_date` then re-parses the matched text into a
:class:`datetime.date`.
"""

from __future__ import annotations

import datetime
import re

#: German month names and common abbreviations, lowercase, mapped to their
#: calendar number.
GERMAN_MONTHS: dict[str, int] = {
    "januar": 1,
    "jan": 1,
    "februar": 2,
    "feb": 2,
    "märz": 3,
    "maerz": 3,
    "mrz": 3,
    "april": 4,
    "apr": 4,
    "mai": 5,
    "juni": 6,
    "jun": 6,
    "juli": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sept": 9,
    "sep": 9,
    "oktober": 10,
    "okt": 10,
    "november": 11,
    "nov": 11,
    "dezember": 12,
    "dez": 12,
}

# Longest name first, so e.g. "september" is tried before its "sep" prefix
# in the alternation below -- regex `|` picks the first alternative that
# matches, not the longest.
_MONTH_NAME_PATTERN = "|".join(sorted(GERMAN_MONTHS, key=len, reverse=True))

_ISO_PATTERN = r"\d{4}-\d{2}-\d{2}"
_DOTTED_PATTERN = r"\d{1,2}\.\d{1,2}\.\d{2}(?:\d{2})?"
_GERMAN_PATTERN = r"\d{1,2}\.\s*(?i:" + _MONTH_NAME_PATTERN + r")\s+\d{2,4}"

#: Regex fragment the tokenizer embeds to recognize any supported date
#: shape as a single DATE token.
TOKEN_PATTERN = f"{_ISO_PATTERN}|{_DOTTED_PATTERN}|{_GERMAN_PATTERN}"

_DOTTED_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{2}(?:\d{2})?)$")
_GERMAN_RE = re.compile(
    r"^(\d{1,2})\.\s*(" + _MONTH_NAME_PATTERN + r")\s+(\d{2,4})$", re.IGNORECASE
)


def _expand_two_digit_year(year: int) -> int:
    """Expands a 2-digit year using the POSIX/glibc ``%y`` windowing rule.

    Args:
        year: A year value; returned unchanged if already >= 100.

    Returns:
        00-68 maps to 2000-2068; 69-99 maps to 1969-1999.
    """
    if year >= 100:
        return year
    return 2000 + year if year <= 68 else 1900 + year


def parse_date(text: str) -> datetime.date:
    """Parses a DATE token's raw text into a date.

    Args:
        text: The token's raw source text, in any of the formats described
            in the module docstring.

    Returns:
        The parsed date.

    Raises:
        ValueError: If the text doesn't match a supported shape, or names
            an invalid calendar date (e.g. day 31 in a 30-day month).
    """
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        pass

    match = _DOTTED_RE.match(text)
    if match:
        day, month, year = match.groups()
        return datetime.date(_expand_two_digit_year(int(year)), int(month), int(day))

    match = _GERMAN_RE.match(text)
    if match:
        day, month_name, year = match.groups()
        month = GERMAN_MONTHS[month_name.lower()]
        return datetime.date(_expand_two_digit_year(int(year)), month, int(day))

    raise ValueError(f"Unrecognized date format: {text!r}")
