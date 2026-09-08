"""Optional live currency-rate fetching, layered on the static table.

See :mod:`engine.units` for the static fallback table this augments.
Network access here is entirely opt-in and never happens on the hot
evaluation path: :func:`refresh` makes a single blocking HTTP request and
must only be called from a background thread -- the Sublime integration
schedules it via ``sublime.set_timeout_async`` when the user has enabled
it in settings. The engine itself has no timer, thread, or setting of its
own; it just holds whatever was last fetched.

A failed refresh (offline, DNS failure, a malformed response, ...) never
raises and never clears an existing cache, so a transient outage silently
falls back to the last known rates -- and if nothing has ever been
fetched, to :mod:`engine.units`'s static table.
"""

from __future__ import annotations

import json
import time
import urllib.request

#: Rates expressed relative to USD, matching engine.units's currency base.
DEFAULT_API_URL = "https://api.frankfurter.app/latest?from=USD"
_DEFAULT_TIMEOUT = 5.0

_live_rates: dict[str, float] = {}
_last_fetch_time: float = 0.0
_last_error: str | None = None


def get_live_rate(code: str) -> float | None:
    """Returns the cached live USD-relative rate for a currency code.

    Args:
        code: A 3-letter ISO currency code, e.g. ``"EUR"``.

    Returns:
        The cached rate, or ``None`` if it was never fetched -- callers
        should fall back to the static table in that case, not treat this
        as an error.
    """
    return _live_rates.get(code.upper())


def is_stale(cache_minutes: float) -> bool:
    """Checks whether the cache is empty or older than ``cache_minutes``.

    Args:
        cache_minutes: How long a fetched set of rates stays fresh.

    Returns:
        True if a refresh is due.
    """
    if not _live_rates:
        return True
    return (time.monotonic() - _last_fetch_time) >= cache_minutes * 60


def last_error() -> str | None:
    """The error message from the most recent failed refresh, if any."""
    return _last_error


def reset() -> None:
    """Clears the cached rates and error state, as if never fetched."""
    global _live_rates, _last_fetch_time, _last_error
    _live_rates = {}
    _last_fetch_time = 0.0
    _last_error = None


def refresh(api_url: str = DEFAULT_API_URL, timeout: float = _DEFAULT_TIMEOUT) -> bool:
    """Fetches live exchange rates and updates the in-memory cache.

    This makes a blocking network request and must only be called from a
    background thread.

    Args:
        api_url: The rates endpoint to fetch, expressed relative to USD
            (see :data:`DEFAULT_API_URL`) and returning a JSON object with
            a ``"rates"`` mapping of currency code to USD-relative rate,
            e.g. ``{"rates": {"EUR": 0.92, "GBP": 0.79}}``.
        timeout: Socket timeout, in seconds.

    Returns:
        True if the fetch succeeded and the cache was updated; False on
        any failure, in which case :func:`last_error` explains why and
        the existing cache (if any) is left untouched.
    """
    global _live_rates, _last_fetch_time, _last_error
    try:
        with urllib.request.urlopen(api_url, timeout=timeout) as response:
            payload = json.loads(response.read())
        rates = {str(code).upper(): float(rate) for code, rate in payload["rates"].items()}
        rates["USD"] = 1.0
    except Exception as exc:  # a failed background fetch must never crash the caller
        _last_error = f"{type(exc).__name__}: {exc}"
        return False

    _live_rates = rates
    _last_fetch_time = time.monotonic()
    _last_error = None
    return True
