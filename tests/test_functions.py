"""Tests for built-in functions and constants."""

from __future__ import annotations

import math

import pytest

from engine.errors import EvalError
from engine.evaluator import Environment, evaluate_line


def _eval(line: str) -> float | None:
    return evaluate_line(line, Environment())


def test_sqrt() -> None:
    assert _eval("sqrt(16)") == pytest.approx(4)


def test_sqrt_of_negative_raises() -> None:
    with pytest.raises(EvalError):
        _eval("sqrt(-1)")


def test_abs() -> None:
    assert _eval("abs(-5)") == pytest.approx(5)


def test_round_default_zero_digits() -> None:
    assert _eval("round(3.7)") == pytest.approx(4)


def test_round_with_digits() -> None:
    assert _eval("round(3.14159, 2)") == pytest.approx(3.14)


def test_floor_and_ceil() -> None:
    assert _eval("floor(3.7)") == pytest.approx(3)
    assert _eval("ceil(3.2)") == pytest.approx(4)


def test_min_and_max_variadic() -> None:
    assert _eval("min(4, 1, 9)") == pytest.approx(1)
    assert _eval("max(4, 1, 9)") == pytest.approx(9)


def test_function_wrong_arity_raises() -> None:
    with pytest.raises(EvalError):
        _eval("sqrt(4, 9)")


def test_function_composition() -> None:
    assert _eval("sqrt(abs(-16))") == pytest.approx(4)


def test_constant_pi() -> None:
    assert _eval("pi") == pytest.approx(math.pi)


def test_constant_e() -> None:
    assert _eval("2 * e") == pytest.approx(2 * math.e)


def test_constant_shadowed_by_assignment() -> None:
    env = Environment()
    assert evaluate_line("e = 5", env) == pytest.approx(5)
    assert evaluate_line("e * 2", env) == pytest.approx(10)
