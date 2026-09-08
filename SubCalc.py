"""Sublime Text integration: live inline results for .calc files."""

from __future__ import annotations

import sublime
import sublime_plugin

from .engine import currency_rates
from .engine.evaluator import LineOutcome, evaluate_buffer_with_env
from .engine.formatting import format_number, format_value
from .engine.heuristics import looks_like_calculation
from .engine.values import Value

_SYNTAX_PATH = "Packages/SubCalc/Calc.sublime-syntax"
_RESULT_SCOPE = "comment.line.double-slash.calc"
_ERROR_SCOPE = "invalid.illegal.calc"
_RESULT_PHANTOM_KEY = "subcalc_results"
_ERROR_PHANTOM_KEY = "subcalc_errors"
_ERROR_REGION_KEY = "subcalc_error_regions"
_STATUS_KEY = "subcalc_selection"
_SETTINGS_FILE = "Calc.sublime-settings"
_HIDDEN_SETTING = "subcalc_hidden"

_FUNCTION_NAMES = ("sqrt", "abs", "round", "floor", "ceil", "min", "max")
_KEYWORD_NAMES = ("total", "sum", "average", "today", "now", "of", "in", "as", "to", "pi", "e")

#: Live listener instances, keyed by view id, so commands (copy, toggle) can
#: reach the listener for the view they were run on without a global scan.
_listeners: dict[int, SubcalcListener] = {}

#: Guards against scheduling more than one background currency-rate fetch
#: at a time (e.g. several Calc views going stale together).
_currency_refresh_in_flight = False


def _display_settings() -> tuple[int, bool, str]:
    """Reads the decimal-places/thousands-separator/rounding-mode settings.

    Returns:
        A ``(decimal_places, thousands_separator, rounding_mode)`` tuple.
    """
    settings = sublime.load_settings(_SETTINGS_FILE)
    return (
        settings.get("decimal_places", 6),
        settings.get("thousands_separator", True),
        settings.get("rounding_mode", "half_even"),
    )


def _currency_settings() -> tuple[bool, str, float]:
    """Reads the live-currency-rate settings.

    Returns:
        A ``(enabled, api_url, cache_minutes)`` tuple.
    """
    settings = sublime.load_settings(_SETTINGS_FILE)
    return (
        settings.get("currency_live_rates", False),
        settings.get("currency_api_url", currency_rates.DEFAULT_API_URL),
        settings.get("currency_cache_minutes", 60),
    )


def _buffer_lines(view: sublime.View) -> list[str]:
    """Reads every line of ``view`` as plain text, without trailing newlines."""
    return [view.substr(region) for region in view.lines(sublime.Region(0, view.size()))]


def _perform_currency_refresh(api_url: str, announce: bool) -> None:
    """Fetches live currency rates and refreshes open Calc views on success.

    Makes a blocking network request, so this must only be called from a
    background thread (e.g. via ``sublime.set_timeout_async``).

    Args:
        api_url: The rates endpoint to fetch.
        announce: Whether to show a status-bar message with the outcome --
            on for an explicit user-triggered refresh, off for the
            automatic background one, which should stay unobtrusive.
    """
    success = currency_rates.refresh(api_url)
    if success:
        for listener in list(_listeners.values()):
            listener.refresh()
        if announce:
            sublime.status_message("SubCalc: currency rates updated")
    elif announce:
        error = currency_rates.last_error() or "unknown error"
        sublime.status_message(f"SubCalc: currency rate fetch failed ({error})")


def _maybe_refresh_currency_rates() -> None:
    """Kicks off a background currency-rate fetch if due, at most one at a time."""
    global _currency_refresh_in_flight
    enabled, api_url, cache_minutes = _currency_settings()
    if not enabled or _currency_refresh_in_flight:
        return
    if not currency_rates.is_stale(cache_minutes):
        return

    def _run() -> None:
        global _currency_refresh_in_flight
        try:
            _perform_currency_refresh(api_url, announce=False)
        finally:
            _currency_refresh_in_flight = False

    _currency_refresh_in_flight = True
    sublime.set_timeout_async(_run, 0)


class SubcalcListener(sublime_plugin.ViewEventListener):
    """Recomputes and displays inline results for views using Calc syntax."""

    def __init__(self, view: sublime.View) -> None:
        """Initializes phantom sets, caches, and the edit-generation counter.

        Args:
            view: The view this listener instance is attached to.
        """
        super().__init__(view)
        self._result_phantoms = sublime.PhantomSet(view, _RESULT_PHANTOM_KEY)
        self._error_phantoms = sublime.PhantomSet(view, _ERROR_PHANTOM_KEY)
        self._generation = 0
        self._outcomes: list[LineOutcome] = []
        self._variables: dict[str, Value] = {}
        self._labels: dict[str, Value] = {}
        _listeners[view.id()] = self

    @classmethod
    def is_applicable(cls, settings: sublime.Settings) -> bool:
        """Restricts this listener to views using the Calc syntax.

        Args:
            settings: The candidate view's settings.

        Returns:
            True if the view's syntax is Calc.sublime-syntax.
        """
        return settings.get("syntax") == _SYNTAX_PATH

    def on_load_async(self) -> None:
        """Computes initial results when a .calc file is opened."""
        self._schedule_update()

    def on_modified_async(self) -> None:
        """Schedules a debounced recompute after every edit."""
        self._schedule_update()

    def on_pre_close(self) -> None:
        """Drops this listener from the registry when its view closes."""
        _listeners.pop(self.view.id(), None)

    def _schedule_update(self) -> None:
        self._generation += 1
        generation = self._generation
        settings = sublime.load_settings(_SETTINGS_FILE)
        debounce_ms = settings.get("debounce_ms", 150)
        sublime.set_timeout_async(lambda: self._update(generation), debounce_ms)

    def refresh(self) -> None:
        """Forces an immediate (non-debounced) recompute and redraw."""
        self._generation += 1
        self._update(self._generation)

    def _update(self, generation: int) -> None:
        """Recomputes results and redraws phantoms, unless superseded.

        Args:
            generation: The edit-generation this update was scheduled for.
        """
        if generation != self._generation:
            return
        view = self.view

        line_regions = view.lines(sublime.Region(0, view.size()))
        lines = [view.substr(region) for region in line_regions]
        self._outcomes, env = evaluate_buffer_with_env(lines)
        self._variables = env.variables
        self._labels = env.labels
        _maybe_refresh_currency_rates()

        if view.settings().get(_HIDDEN_SETTING, False):
            self._result_phantoms.update([])
            self._error_phantoms.update([])
            view.erase_regions(_ERROR_REGION_KEY)
            return

        settings = sublime.load_settings(_SETTINGS_FILE)
        prefix = settings.get("result_prefix", "  ⟶ ")
        decimal_places, thousands_separator, rounding_mode = _display_settings()
        result_color = view.style_for_scope(_RESULT_SCOPE)["foreground"]
        error_color = view.style_for_scope(_ERROR_SCOPE)["foreground"]

        result_phantoms = []
        error_phantoms = []
        error_regions = []
        for region, line_text, outcome in zip(line_regions, lines, self._outcomes):
            end_point = sublime.Region(region.end(), region.end())
            if outcome.value is not None:
                text = format_value(
                    outcome.value, decimal_places, thousands_separator, rounding_mode
                )
                html = (
                    f'<body style="margin:0"><span style="color:{result_color}">'
                    f"{prefix}{text}</span></body>"
                )
                result_phantoms.append(
                    sublime.Phantom(end_point, html, sublime.PhantomLayout.INLINE)
                )
            elif outcome.error is not None and looks_like_calculation(line_text):
                html = (
                    f'<body style="margin:0"><span style="color:{error_color}">'
                    f"  ⚠ {outcome.error}</span></body>"
                )
                error_phantoms.append(
                    sublime.Phantom(end_point, html, sublime.PhantomLayout.INLINE)
                )
                error_regions.append(region)

        self._result_phantoms.update(result_phantoms)
        self._error_phantoms.update(error_phantoms)
        if error_regions:
            view.add_regions(
                _ERROR_REGION_KEY,
                error_regions,
                scope=_ERROR_SCOPE,
                flags=sublime.DRAW_NO_FILL | sublime.DRAW_SQUIGGLY_UNDERLINE,
            )
        else:
            view.erase_regions(_ERROR_REGION_KEY)

    def on_hover(self, point: int, hover_zone: int) -> None:
        """Shows a popup with a variable/label/line's current value on hover.

        Args:
            point: The buffer offset the mouse is hovering over.
            hover_zone: Which part of the view is being hovered; only plain
                text hovers (not the gutter or a phantom) are handled.
        """
        if hover_zone != sublime.HOVER_TEXT:
            return
        view = self.view
        word_region = view.word(point)
        word = view.substr(word_region)
        if not word or not word[0].isalpha():
            return

        name = None
        value = None
        if word in self._variables:
            name, value = word, self._variables[word]
        elif word_region.begin() > 0 and view.substr(word_region.begin() - 1) == "#":
            if word in self._labels:
                name, value = f"#{word}", self._labels[word]
        else:
            lowered = word.lower()
            suffix = lowered[4:]
            if lowered.startswith("line") and suffix.isdigit():
                index = int(suffix) - 1
                if 0 <= index < len(self._outcomes):
                    line_value = self._outcomes[index].value
                    if line_value is not None:
                        name, value = word, line_value

        if name is None or value is None:
            return
        decimal_places, thousands_separator, rounding_mode = _display_settings()
        text = format_value(value, decimal_places, thousands_separator, rounding_mode)
        view.show_popup(f"<b>{name}</b> = {text}", location=point, max_width=400)

    def on_query_completions(
        self, prefix: str, locations: list[int]
    ) -> sublime.CompletionList:
        """Offers completions for known variables, labels, lines, and keywords.

        Args:
            prefix: The word being completed (unused; Sublime filters by it).
            locations: The buffer offsets completions were requested at
                (unused; every completion is offered regardless of position).

        Returns:
            The available completions for this view's current buffer state.
        """
        items = []
        for name in sorted(self._variables):
            items.append(sublime.CompletionItem(name, kind=sublime.KIND_VARIABLE))
        for name in sorted(self._labels):
            items.append(sublime.CompletionItem(f"#{name}", kind=sublime.KIND_VARIABLE))
        for index in range(1, len(self._outcomes) + 1):
            items.append(sublime.CompletionItem(f"line{index}", kind=sublime.KIND_VARIABLE))
        for name in _FUNCTION_NAMES:
            items.append(
                sublime.CompletionItem(
                    name, trigger=f"{name}(", completion=f"{name}(", kind=sublime.KIND_FUNCTION
                )
            )
        for name in _KEYWORD_NAMES:
            items.append(sublime.CompletionItem(name, kind=sublime.KIND_KEYWORD))
        return sublime.CompletionList(items)

    def on_selection_modified_async(self) -> None:
        """Shows the sum/average of the selected lines' results in the status bar."""
        view = self.view
        selections = [sel for sel in view.sel() if not sel.empty()]
        if not selections or not self._outcomes:
            view.erase_status(_STATUS_KEY)
            return

        rows: set[int] = set()
        for sel in selections:
            start_row = view.rowcol(sel.begin())[0]
            end_row = view.rowcol(sel.end())[0]
            rows.update(range(start_row, end_row + 1))

        values = [
            self._outcomes[row].value
            for row in sorted(rows)
            if row < len(self._outcomes) and isinstance(self._outcomes[row].value, float)
        ]
        if not values:
            view.erase_status(_STATUS_KEY)
            return

        decimal_places, thousands_separator, rounding_mode = _display_settings()
        total = sum(values)
        average = total / len(values)
        display = (decimal_places, thousands_separator, rounding_mode)
        total_text = format_number(total, *display)
        average_text = format_number(average, *display)
        view.set_status(
            _STATUS_KEY,
            f"SubCalc: Σ {total_text}  ⌀ {average_text} ({len(values)} line(s))",
        )


class SubcalcNewCommand(sublime_plugin.WindowCommand):
    """Opens a new, ready-to-type view using the Calc syntax."""

    def run(self) -> None:
        """Creates the view and assigns Calc syntax before any text is typed."""
        view = self.window.new_file()
        view.assign_syntax(_SYNTAX_PATH)
        view.set_name("Untitled.calc")


class SubcalcCopyAllResultsCommand(sublime_plugin.TextCommand):
    """Copies every line's formatted result to the clipboard, one per line."""

    def run(self, edit: sublime.Edit) -> None:
        """Recomputes the buffer and copies its non-empty results.

        Args:
            edit: Unused; this command only reads the buffer.
        """
        outcomes, _ = evaluate_buffer_with_env(_buffer_lines(self.view))
        decimal_places, thousands_separator, rounding_mode = _display_settings()
        lines = [
            format_value(outcome.value, decimal_places, thousands_separator, rounding_mode)
            for outcome in outcomes
            if outcome.value is not None
        ]
        sublime.set_clipboard("\n".join(lines))
        sublime.status_message(f"SubCalc: copied {len(lines)} result(s)")


class SubcalcCopyLastResultCommand(sublime_plugin.TextCommand):
    """Copies the buffer's last computed result to the clipboard."""

    def run(self, edit: sublime.Edit) -> None:
        """Recomputes the buffer and copies its final non-empty result.

        Args:
            edit: Unused; this command only reads the buffer.
        """
        outcomes, _ = evaluate_buffer_with_env(_buffer_lines(self.view))
        results = [outcome.value for outcome in outcomes if outcome.value is not None]
        if not results:
            sublime.status_message("SubCalc: no result to copy")
            return
        decimal_places, thousands_separator, rounding_mode = _display_settings()
        text = format_value(results[-1], decimal_places, thousands_separator, rounding_mode)
        sublime.set_clipboard(text)
        sublime.status_message(f"SubCalc: copied {text}")


class SubcalcToggleResultsCommand(sublime_plugin.TextCommand):
    """Toggles whether inline result phantoms are shown for this view."""

    def run(self, edit: sublime.Edit) -> None:
        """Flips the per-view hidden flag and forces an immediate redraw.

        Args:
            edit: Unused; this command only changes view settings.
        """
        settings = self.view.settings()
        settings.set(_HIDDEN_SETTING, not settings.get(_HIDDEN_SETTING, False))
        listener = _listeners.get(self.view.id())
        if listener is not None:
            listener.refresh()


class SubcalcRefreshCurrencyRatesCommand(sublime_plugin.WindowCommand):
    """Manually fetches live currency rates now.

    Works regardless of the ``currency_live_rates`` setting, which only
    gates the automatic background refresh.
    """

    def run(self) -> None:
        """Kicks off a background fetch and reports the outcome."""
        _, api_url, _ = _currency_settings()
        sublime.status_message("SubCalc: fetching currency rates…")
        sublime.set_timeout_async(lambda: _perform_currency_refresh(api_url, announce=True), 0)
