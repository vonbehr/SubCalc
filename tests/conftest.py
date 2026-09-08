"""Ensures the repo root (containing the ``engine`` package) is importable.

Sublime Text loads this package's Python files directly out of the repo, so
there is no installable distribution to add to the path -- pytest needs this
file to discover ``engine`` when run from the repo root. Living under
``tests/`` (rather than the repo root) also keeps Sublime's plugin loader --
which auto-imports every top-level ``.py`` file in a package -- from picking
this file up as a plugin.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import currency_rates  # noqa: E402 - after the sys.path insert above


@pytest.fixture(autouse=True)
def _reset_currency_rates() -> None:
    """Isolates tests from the live-rate cache, a module-level global."""
    currency_rates.reset()
