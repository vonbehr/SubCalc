# Contributing

## Dev setup

The calculation engine (`engine/`) is pure Python with no dependency on
Sublime's `sublime`/`sublime_plugin` modules, so it's fully testable outside
the editor:

```sh
python3 -m venv .venv
.venv/bin/pip install pytest ruff mypy pre-commit
```

Run the test suite:

```sh
.venv/bin/pytest
```

Lint and type-check (both run in CI; `engine/` and `tests/` must also pass
`ruff format --check`):

```sh
.venv/bin/ruff check engine tests SubCalc.py
.venv/bin/ruff format engine tests SubCalc.py
.venv/bin/mypy
```

Install the git hook so these run automatically on every commit:

```sh
.venv/bin/pre-commit install
```

`SubCalc.py` (the editor-integration layer) requires manual testing inside
Sublime Text, since the `sublime` module only exists there -- see
"Installing locally" in the README to symlink this repo into your Packages
directory, then use `examples/*.calc` as a quick smoke test.

## Style

This project follows [PEP 8](https://peps.python.org/pep-0008/) and the
[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
(the latter takes precedence where they conflict). Every function needs
type hints and a Google-style docstring; `ruff`'s `D` (pydocstyle) rules
enforce the docstring format in CI.

The engine's runtime type aliases use `typing.Union` rather than `X | Y`
(e.g. `engine/values.py`, `engine/parser.py`'s `Node`), even though the rest
of the codebase uses `from __future__ import annotations` and modern
annotation syntax freely. That's deliberate: Sublime Text 4's default
plugin host is Python 3.3, and this package opts into the newer 3.8 host
via `.python-version` -- but a *runtime-evaluated* `X | Y` still needs
3.10+. Annotations are fine either way since they're never evaluated at
import time; only genuine runtime expressions need the older form.

## Pull requests

- Add or update tests for any engine behavior change -- `tests/` mirrors
  `engine/` module by module.
- Keep `ROADMAP.md` in sync: check off items you finish, and add new ones
  you find worth doing.
- A bug fix doesn't need surrounding cleanup, and a new feature doesn't
  need speculative generality beyond what it uses today.
