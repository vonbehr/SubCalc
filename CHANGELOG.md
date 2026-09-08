# Changelog

All notable changes to this project are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Built-in functions: `sqrt`, `abs`, `round`, `floor`, `ceil`, `min`, `max`.
- Constants `pi` and `e`.
- Scientific notation, both as input (`1e6`, `2.5e-3`) and as output for
  very large or very small results.
- Implicit multiplication: `2(3 + 4)` and `3x`.
- `total` / `sum` / `average` aggregate lines, summarizing the block since
  the last blank line.
- Units of measure with conversion (length, mass, time) and a static
  currency-conversion table, e.g. `5 km + 200 m`, `3 kg in lb`, `$5 + $3`.
- `expr in unit` / `expr as unit` conversion and tagging, including
  postfix currency symbols (`500$`) and a currency symbol as the
  conversion target (`500$ in €`), not just prefix (`$500`) or a 3-letter
  code (`500 USD`).
- Optional live currency rates: `"currency_live_rates": true` fetches
  real exchange rates from Frankfurter in the background (off by
  default; never blocks typing; falls back to the static table when
  disabled, unfetched, or offline), plus a `currency_api_url` override
  and a `currency_cache_minutes` refresh interval. A new **SubCalc:
  Refresh Currency Rates** command fetches immediately regardless of the
  setting.
- Date literals (`2024-01-01`), `today`, date + duration arithmetic, and
  `start to end` date differences.
- Alternate date formats: dotted day.month.year with a 2- or 4-digit year
  (`05.07.2026`, `5.7.2026`, `5.7.26`), and German day. Month year with a
  full or abbreviated month name (`5. Juni 2026`).
- Time-of-day literals (`14:30`, `14:30:15`), `now`, and time arithmetic
  (`+`/`-` a duration, wrapping past midnight; `to` or `-` between two
  times for a signed duration in hours) -- the same duration/quantity
  machinery as dates, applied to a clock time instead of a calendar date.
- Named line labels (`#name`), referenced later as `#name`, as an
  alternative to positional `lineN` references.
- Configurable rounding mode (`half_even`, `half_up`, `floor`, `ceil`).
- An inline error indicator for lines that look like an attempted
  calculation but fail to evaluate.
- A hover popup showing a variable's, label's, or line's current value.
- Autocomplete for variables, labels, line references, functions, and
  keywords.
- Commands to copy all results or just the last result to the clipboard.
- A status-bar total/average for the currently selected lines.
- A per-view command to toggle result phantoms on/off.
- Richer syntax highlighting and a bundled color-scheme overlay.
- Windows install instructions in the README.
- CI (GitHub Actions) running the test suite and ruff/mypy on every push
  and pull request; a pre-commit config for the same checks locally.
- `CONTRIBUTING.md`, `CHANGELOG.md`, `ROADMAP.md`, and an `examples/`
  gallery of sample `.calc` files.

### Fixed

- The inline error indicator no longer flags ordinary sentences that
  happen to contain a date, a clock time, or a hyphenated word ("Meeting
  on 2026-07-05...", "Call John at 15:00...", "Flight check-in") --
  these were false positives from the DATE/TIME token and the `-`
  operator being treated as unconditional signals.

## [1.0.0] - 2026-09-08

### Added

- Initial release: live inline per-line calculation for `.calc` files.
- Arithmetic (`+ - * / ^ ()`), variables, `lineN` references, and the
  percent semantics described in the README.
- `SubCalc: New Calculation` command and `.calc` syntax highlighting.
