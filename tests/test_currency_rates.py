"""Tests for engine.currency_rates. Network calls are always mocked."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from engine import currency_rates


class _FakeResponse:
    """A minimal stand-in for the object ``urlopen`` returns."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def _fake_urlopen(payload: object) -> _FakeResponse:
    return _FakeResponse(json.dumps(payload).encode("utf-8"))


def test_refresh_success_populates_cache() -> None:
    payload = {"amount": 1.0, "base": "USD", "rates": {"EUR": 0.9, "GBP": 0.8}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        assert currency_rates.refresh() is True
    assert currency_rates.get_live_rate("EUR") == pytest.approx(0.9)
    assert currency_rates.get_live_rate("GBP") == pytest.approx(0.8)
    assert currency_rates.last_error() is None


def test_refresh_adds_usd_as_the_base() -> None:
    """The API omits the base currency from 'rates'; USD=1.0 is added."""
    payload = {"rates": {"EUR": 0.9}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        currency_rates.refresh()
    assert currency_rates.get_live_rate("USD") == pytest.approx(1.0)


def test_get_live_rate_is_case_insensitive() -> None:
    payload = {"rates": {"EUR": 0.9}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        currency_rates.refresh()
    assert currency_rates.get_live_rate("eur") == pytest.approx(0.9)


def test_unfetched_rate_is_none() -> None:
    assert currency_rates.get_live_rate("EUR") is None


def test_network_failure_is_caught() -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("no network")):
        assert currency_rates.refresh() is False
    assert currency_rates.last_error() is not None
    assert currency_rates.get_live_rate("EUR") is None


def test_malformed_json_is_caught() -> None:
    with patch("urllib.request.urlopen", return_value=_FakeResponse(b"not json")):
        assert currency_rates.refresh() is False
    assert currency_rates.last_error() is not None


def test_unexpected_shape_is_caught() -> None:
    with patch("urllib.request.urlopen", return_value=_fake_urlopen({"no_rates_key": True})):
        assert currency_rates.refresh() is False


def test_failed_refresh_does_not_clear_existing_cache() -> None:
    payload = {"rates": {"EUR": 0.9}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        currency_rates.refresh()
    with patch("urllib.request.urlopen", side_effect=OSError("timed out")):
        currency_rates.refresh()
    assert currency_rates.get_live_rate("EUR") == pytest.approx(0.9)


def test_is_stale_when_never_fetched() -> None:
    assert currency_rates.is_stale(60) is True


def test_is_stale_false_right_after_a_fetch() -> None:
    payload = {"rates": {"EUR": 0.9}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        currency_rates.refresh()
    assert currency_rates.is_stale(60) is False


def test_reset_clears_cache_and_error() -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("boom")):
        currency_rates.refresh()
    assert currency_rates.last_error() is not None
    currency_rates.reset()
    assert currency_rates.last_error() is None
    assert currency_rates.is_stale(60) is True
