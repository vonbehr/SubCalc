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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
