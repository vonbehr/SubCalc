"""Tests for implicit multiplication: ``2(3 + 4)`` and ``3x``."""

from __future__ import annotations

from engine.evaluator import Environment, evaluate_buffer, evaluate_line


def _eval(line: str, env: Environment | None = None) -> float | None:
    return evaluate_line(line, env if env is not None else Environment())


def test_number_before_parenthesis() -> None:
    assert _eval("2(3 + 4)") == 14


def test_parenthesis_before_parenthesis() -> None:
    assert _eval("(1 + 2)(3 + 4)") == 21


def test_number_adjacent_to_variable() -> None:
    env = Environment()
    _eval("x = 5", env)
    assert _eval("3x", env) == 15


def test_space_between_number_and_word_is_not_implicit_multiplication() -> None:
    """'5 apples' stays prose rather than becoming 5 * apples.

    Adjacency is required precisely to avoid this false positive.
    """
    assert evaluate_buffer(["5 apples"]) == [None]


def test_number_adjacent_to_unassigned_variable_fails_silently_in_buffer() -> None:
    assert evaluate_buffer(["3y"]) == [None]
