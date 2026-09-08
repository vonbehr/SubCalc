# SubCalc

A Sublime Text 4 package for live, per-line calculation in plain-text notes.

Write a `.calc` file mixing prose and math; every line that evaluates to a number shows its result
inline as you type. Lines that aren't calculations are left alone.

## Example

```
Grocery budget
rent = 1200                                      ⟶ 1200
groceries = 350                                  ⟶ 350
rent + groceries          // total fixed costs   ⟶ 1550
line4 - 10%                                      ⟶ 1395
20% of 1550                                      ⟶ 310
```

More worked examples -- unit conversion, currency, dates, an invoice --
live in [`examples/`](examples).

## Syntax

- **Arithmetic**: `+ - * / ^ ( )`, standard precedence. `2(3 + 4)` and `3x`
  (a number directly, with no space, against a parenthesis or a variable)
  are implicit multiplication.
- **Numbers**: thousands separators (`1,234` or `1_234`), and scientific
  notation (`1e6`, `2.5e-3`).
- **Variables**: `name = expression`, referenced by name on later lines.
  Variables are only visible on lines *after* their assignment — no forward
  references, matching how a spreadsheet or notes app reads top to bottom.
- **Line references**: `line1`, `line2`, … refer to an earlier line's
  result. A reference to a blank, prose, or failed line has no result.
- **Labels**: tag any line's result with `#name` (`rent + groceries #housing`),
  then refer to it later as `#name` — unlike a variable, a label doesn't
  change what the line displays, and it survives lines being reordered
  since it's not positional like `lineN`.
- **Percentages**:
  - `20%` alone is a fraction: `0.2`.
  - `A + 20%` / `A - 20%` means "20 percent of A": `40 - 20%` is `32`.
  - `A * 20%` / `A / 20%` treats `20%` as a plain fraction.
  - `20% of A` is always `(20/100) * A`.
- **Functions**: `sqrt`, `abs`, `round` (1 or 2 args), `floor`, `ceil`,
  `min`, `max` (2+ args), e.g. `round(sqrt(2), 4)`.
- **Constants**: `pi`, `e` — shadowed if you assign a variable of the same
  name.
- **Aggregates**: a line containing only `total` (or `sum`) adds up every
  plain number above it back to the last blank line (or the top of the
  file); `average` does the same but divides by the count. Used inside a
  larger expression, these three words are ordinary (undefined) variable
  names instead — the aggregate only fires on a line by itself.
- **Units of measure**: attach a unit to a number (`5 km`, `3 kg`, `2 hours`)
  and arithmetic between same-dimension quantities converts automatically:
  `5 km + 200 m` is `5.2 km`. Convert or tag explicitly with `in`/`as`:
  `5 km in miles`, `3 as USD`. Supported dimensions are length, mass, time,
  and currency (`$`, `€`, `£`, `¥`, or a 3-letter code like `USD`) — currency
  rates are a small static table, not fetched live.
- **Dates**: `2024-01-01` is a date literal, `today` is the current date.
  `date + N days`/`weeks` (and `- `) shift a date; `start to end` (or
  `end - start`) is the difference in days.
- **Comments**: `// ...` to end of line.
- Any line that doesn't parse as a calculation (plain prose) simply shows no
  result — it's never treated as an error. A line that looks like an
  *attempted* calculation (it has an operator, a keyword, or a reference)
  but fails gets a red squiggle with the error message instead, so a typo
  in a real formula doesn't just silently vanish. This is a best-effort
  heuristic, not the engine's actual behavior — see
  `engine/heuristics.py`.

## Commands

Available from the command palette (and `Edit > SubCalc` in the menu):

- **SubCalc: New Calculation** — opens a new `.calc`-syntax view.
- **SubCalc: Copy All Results** / **Copy Last Result** — copies the
  buffer's computed results to the clipboard.
- **SubCalc: Toggle Results** — hides or shows inline result phantoms for
  the current view.

Hovering a variable, `#label`, or `lineN` shows a popup with its current
value, and they're all offered as autocomplete suggestions, alongside
function and keyword names. Selecting more than one line's worth of text
shows that selection's total and average in the status bar.

## Installing locally (not yet on Package Control)

Symlink this repo into Sublime Text's Packages directory.

**macOS**

```sh
ln -s "$(pwd)" "$HOME/Library/Application Support/Sublime Text/Packages/SubCalc"
```

**Windows**

Find your Packages directory via Sublime Text's **Preferences > Browse Packages…**
(typically `%APPDATA%\Sublime Text\Packages`), then create the symlink from a
PowerShell prompt running as Administrator:

```powershell
New-Item -ItemType SymbolicLink `
    -Path "$env:APPDATA\Sublime Text\Packages\SubCalc" `
    -Target "C:\path\to\this\repo"
```

Alternatively, from an Administrator Command Prompt:

```bat
mklink /D "%APPDATA%\Sublime Text\Packages\SubCalc" "C:\path\to\this\repo"
```

A symlink is required (rather than a plain copy) so that Sublime Text picks
up further changes to this repo without reinstalling.

Then, in Sublime Text, open the command palette and run
**SubCalc: New Calculation** (or create/open any file with a `.calc`
extension).

Settings (`Calc.sublime-settings`, accessible via
**Preferences > Package Settings**) let you tune the decimal precision,
thousands-separator grouping, result prefix, rounding mode
(`half_even`/`half_up`/`floor`/`ceil`), and debounce delay.

## Development

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for dev setup (tests, lint, type
checks, pre-commit) and style guidelines, and
[`ROADMAP.md`](ROADMAP.md) for planned work.

The calculation engine (`engine/`) is pure Python with no dependency on
Sublime's `sublime`/`sublime_plugin` modules, so it's fully testable outside
the editor:

```sh
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/pytest
```

Only `SubCalc.py` (the editor-integration layer) requires manual testing
inside Sublime Text, since the `sublime` module only exists there.
