"""Tests for engine.evaluator, including buffer-level tolerant evaluation."""

from __future__ import annotations

import pytest

from engine.errors import EvalError
from engine.evaluator import Environment, evaluate_buffer, evaluate_line


def _eval(line: str, env: Environment | None = None) -> float | None:
    return evaluate_line(line, env if env is not None else Environment())


def test_basic_arithmetic() -> None:
    """Standard operator precedence and grouping evaluate correctly."""
    assert _eval("1 + 2 * 3") == 7
    assert _eval("(1 + 2) * 3") == 9
    assert _eval("2^3^2") == 512


def test_division_by_zero_raises() -> None:
    """Dividing by zero raises EvalError rather than a Python exception."""
    with pytest.raises(EvalError):
        _eval("1 / 0")


# -- Percent semantics -------------------------------------------------
# See the plan's percent-semantics table: bare N% is a fraction, A +/- N% is
# "N percent of A", A * N% or A / N% treats N% as a plain fraction, and
# "N% of A" always means (N/100) * A.


def test_bare_percent_is_a_fraction() -> None:
    assert _eval("20%") == pytest.approx(0.2)


def test_percent_added_is_percent_of_left_operand() -> None:
    assert _eval("40 + 20%") == pytest.approx(48)


def test_percent_subtracted_is_percent_of_left_operand() -> None:
    assert _eval("40 - 20%") == pytest.approx(32)


def test_percent_multiplied_is_a_plain_fraction() -> None:
    assert _eval("40 * 20%") == pytest.approx(8)


def test_percent_divided_is_a_plain_fraction() -> None:
    assert _eval("40 / 20%") == pytest.approx(200)


def test_percent_of_keyword() -> None:
    assert _eval("20% of 40") == pytest.approx(8)


def test_percent_of_then_addition_uses_resolved_value() -> None:
    """'20% of 40 + 5' resolves the percent-of first, then adds normally."""
    assert _eval("20% of 40 + 5") == pytest.approx(13)


# -- Variables -----------------------------------------------------------


def test_variable_assignment_and_reference() -> None:
    env = Environment()
    assert _eval("discount = 10%", env) == pytest.approx(0.1)
    assert _eval("100 - 100 * discount", env) == pytest.approx(90)


def test_unknown_variable_raises() -> None:
    with pytest.raises(EvalError):
        _eval("total * 2")


def test_variable_only_visible_after_its_assignment_line() -> None:
    """No forward references: a variable must be assigned on an earlier line."""
    results = evaluate_buffer(["x + 1", "x = 5"])
    assert results == [None, 5]


# -- Line references -------------------------------------------------------


def test_line_reference_reads_earlier_result() -> None:
    results = evaluate_buffer(["10 + 5", "line1 * 2"])
    assert results == [15, 30]


def test_line_reference_to_blank_line_fails_silently_in_buffer() -> None:
    results = evaluate_buffer(["some notes", "line1 + 1"])
    assert results == [None, None]


def test_line_reference_to_future_line_fails() -> None:
    with pytest.raises(EvalError):
        _eval("line2 + 1")  # line 2 has not been evaluated yet in a fresh env


# -- Buffer-level tolerance -------------------------------------------------


def test_prose_lines_produce_no_result() -> None:
    results = evaluate_buffer(
        [
            "Grocery budget",
            "// fixed costs",
            "rent = 1200",
            "rent + 300",
            "",
            "thanks for reading",
        ]
    )
    assert results == [None, None, 1200, 1500, None, None]


def test_complex_result_from_exponentiation_is_reported_as_eval_error() -> None:
    """Python's ** silently promotes negative-base fractional powers to complex."""
    with pytest.raises(EvalError):
        _eval("(-1) ^ 0.5")


def test_zero_to_negative_power_is_eval_error() -> None:
    with pytest.raises(EvalError):
        _eval("0 ^ -1")
