# Roadmap

Ideas for SubCalc beyond the current v1 feature set, grouped by area. Check
items off as they land; feel free to reorder or drop ones that turn out not
to be worth it.

## Language / calculation engine

- [x] Built-in functions: `sqrt`, `abs`, `round`, `floor`, `ceil`, `min`, `max`
- [x] Constants: `pi`, `e`
- [x] Scientific notation input/output (`1e6`, `2.5e-3`)
<!-- - [ ] Hex/binary/octal integer literals (`0xFF`, `0b1010`) -->
- [x] Implicit multiplication (`2(3 + 4)`, `3x`)
- [x] Aggregate keywords over a block of lines (`total`, `sum`, `average`)
- [x] Units of measure with conversion (length, weight, time, …)
- [x] Currency literals and conversion (static table, or fetched rates)
- [x] Date/time arithmetic (`today + 30 days`, `2024-01-01 to 2024-06-01`)
- [x] Per-line result formatting overrides (e.g. force a `$` or `kg` suffix)
- [x] Configurable rounding modes (banker's rounding, etc.)
- [x] Named line labels (`#subtotal`) as an alternative to positional
      `lineN` references, so reordering lines doesn't break references

## Sublime Text integration

- [x] Inline error indicator for lines that look like a calculation but fail
      to evaluate, instead of silently showing no result
- [x] Hover popup showing intermediate steps or a referenced variable's value
- [x] Autocomplete for variable names and `lineN` references
- [x] Command to copy all results, or just the last result, to the clipboard
- [x] Status bar total/average for the currently selected lines
- [x] Richer syntax highlighting (distinct scopes for operators, numbers,
      variables, percentages) and a bundled color scheme
- [x] Per-view toggle to hide/show result phantoms
<!-- - [ ] Snippets for common patterns (budgets, unit conversions, etc.) -->
- [x] Package icon/thumbnail for Package Control listing

## Tooling / infrastructure

- [x] CI (GitHub Actions) running `pytest` on every push and PR
- [x] Lint/type-check in CI (`ruff`, `mypy`) to enforce the PEP 8 / Google
      style guide requirements from `CLAUDE.md`
- [x] Pre-commit hooks for the above
- [x] `CHANGELOG.md` with version history
<!-- - [ ] Submit to Package Control once the package feels stable -->

## Documentation

- [x] `CONTRIBUTING.md` with dev setup and PR expectations
- [x] Gallery of example `.calc` files (budget, unit conversion, invoice, …)
- [x] README section per feature as each one ships
