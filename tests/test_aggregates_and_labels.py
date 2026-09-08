"""Tests for total/sum/average aggregate lines and #label references."""

from __future__ import annotations

import pytest

from engine.errors import EvalError
from engine.evaluator import Environment, evaluate_buffer, evaluate_line


def test_total_sums_the_current_block() -> None:
    results = evaluate_buffer(["10", "20", "total"])
    assert results == [10, 20, 30]


def test_sum_is_an_alias_for_total() -> None:
    results = evaluate_buffer(["10", "20", "sum"])
    assert results == [10, 20, 30]


def test_average() -> None:
    results = evaluate_buffer(["10", "20", "30", "average"])
    assert results == [10, 20, 30, 20]


def test_blank_line_resets_the_block() -> None:
    results = evaluate_buffer(["10", "20", "", "5", "total"])
    assert results == [10, 20, None, 5, 5]


def test_prose_line_does_not_reset_the_block() -> None:
    results = evaluate_buffer(["10", "notes here", "20", "total"])
    assert results == [10, None, 20, 30]


def test_average_of_empty_block_raises() -> None:
    with pytest.raises(EvalError):
        evaluate_line("average", Environment())


def test_total_used_mid_expression_is_still_a_plain_variable() -> None:
    """Only a bare, whole-line aggregate keyword is special.

    Used inside a larger expression, 'total'/'sum'/'average' is an ordinary
    (here unknown) variable, matching the pre-existing behavior.
    """
    with pytest.raises(EvalError):
        evaluate_line("total * 2", Environment())


def test_label_reference() -> None:
    results = evaluate_buffer(["rent = 1200 #base", "line1 * 2", "#base * 2"])
    assert results == [1200, 2400, 2400]


def test_label_on_a_plain_expression() -> None:
    results = evaluate_buffer(["100 + 50 #housing", "#housing / 2"])
    assert results == [150, 75]


def test_unknown_label_raises() -> None:
    with pytest.raises(EvalError):
        evaluate_line("#nope + 1", Environment())


def test_label_only_visible_after_its_line() -> None:
    results = evaluate_buffer(["#later + 1", "10 #later"])
    assert results == [None, 10]
