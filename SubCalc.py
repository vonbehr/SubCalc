"""Sublime Text integration: live inline results for .calc files."""

from __future__ import annotations

import sublime
import sublime_plugin

from .engine.evaluator import evaluate_buffer
from .engine.formatting import format_number

_SYNTAX_PATH = "Packages/SubCalc/Calc.sublime-syntax"
_COMMENT_SCOPE = "comment.line.double-slash.calc"
_PHANTOM_KEY = "subcalc_results"
_SETTINGS_FILE = "Calc.sublime-settings"


class SubcalcListener(sublime_plugin.ViewEventListener):
    """Recomputes and displays inline results for views using Calc syntax."""

    def __init__(self, view: sublime.View) -> None:
        """Initializes the phantom set and edit-generation counter.

        Args:
            view: The view this listener instance is attached to.
        """
        super().__init__(view)
        self._phantom_set = sublime.PhantomSet(view, _PHANTOM_KEY)
        self._generation = 0

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

    def _schedule_update(self) -> None:
        self._generation += 1
        generation = self._generation
        settings = sublime.load_settings(_SETTINGS_FILE)
        debounce_ms = settings.get("debounce_ms", 150)
        sublime.set_timeout_async(lambda: self._update(generation), debounce_ms)

    def _update(self, generation: int) -> None:
        """Recomputes and redraws phantoms, unless a newer edit supersedes this run.

        Args:
            generation: The edit-generation this update was scheduled for.
        """
        if generation != self._generation:
            return
        view = self.view
        settings = sublime.load_settings(_SETTINGS_FILE)

        line_regions = view.lines(sublime.Region(0, view.size()))
        lines = [view.substr(region) for region in line_regions]
        results = evaluate_buffer(lines)

        prefix = settings.get("result_prefix", "  ⟶ ")
        decimal_places = settings.get("decimal_places", 6)
        thousands_separator = settings.get("thousands_separator", True)
        color = view.style_for_scope(_COMMENT_SCOPE)["foreground"]

        phantoms = []
        for region, result in zip(line_regions, results):
            if result is None:
                continue
            text = format_number(result, decimal_places, thousands_separator)
            end_point = sublime.Region(region.end(), region.end())
            html = (
                f'<body style="margin:0"><span style="color:{color}">'
                f"{prefix}{text}</span></body>"
            )
            phantoms.append(
                sublime.Phantom(end_point, html, sublime.PhantomLayout.INLINE)
            )
        self._phantom_set.update(phantoms)


class SubcalcNewCommand(sublime_plugin.WindowCommand):
    """Opens a new, ready-to-type view using the Calc syntax."""

    def run(self) -> None:
        """Creates the view and assigns Calc syntax before any text is typed."""
        view = self.window.new_file()
        view.assign_syntax(_SYNTAX_PATH)
        view.set_name("Untitled.calc")
