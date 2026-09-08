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

## Syntax (v1)

- **Arithmetic**: `+ - * / ^ ( )`, standard precedence.
- **Variables**: `name = expression`, referenced by name on later lines.
  Variables are only visible on lines *after* their assignment — no forward
  references, matching how a spreadsheet or notes app reads top to bottom.
- **Line references**: `line1`, `line2`, … refer to an earlier line's
  result. A reference to a blank, prose, or failed line has no result.
- **Percentages**:
  - `20%` alone is a fraction: `0.2`.
  - `A + 20%` / `A - 20%` means "20 percent of A": `40 - 20%` is `32`.
  - `A * 20%` / `A / 20%` treats `20%` as a plain fraction.
  - `20% of A` is always `(20/100) * A`.
- **Comments**: `// ...` to end of line.
- Any line that doesn't parse as a calculation (plain prose) simply shows no
  result — it's never treated as an error.

Units, currency conversion, and date math are intentionally out of scope for
v1; the engine and integration pattern are built to extend to those later.

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
thousands-separator grouping, result prefix, and debounce delay.

## Development

The calculation engine (`engine/`) is pure Python with no dependency on
Sublime's `sublime`/`sublime_plugin` modules, so it's fully testable outside
the editor:

```sh
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/pytest
```

Only `SubCalc.py` (the editor-integration layer) requires manual testing
inside Sublime Text, since the `sublime` module only exists there.
