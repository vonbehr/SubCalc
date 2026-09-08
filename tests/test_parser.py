"""Tests for engine.parser."""

from __future__ import annotations

import pytest

from engine.errors import ParseError
from engine.parser import (
    Assign,
    BinOp,
    LineRef,
    Number,
    Percent,
    PercentOf,
    Var,
    parse_line,
)


def test_simple_arithmetic_precedence() -> None:
    """Multiplication binds tighter than addition."""
    node = parse_line("1 + 2 * 3")
    assert node == BinOp("+", Number(1), BinOp("*", Number(2), Number(3)))


def test_power_is_right_associative() -> None:
    """2^3^2 parses as 2^(3^2), not (2^3)^2."""
    node = parse_line("2^3^2")
    assert node == BinOp("^", Number(2), BinOp("^", Number(3), Number(2)))


def test_parentheses_override_precedence() -> None:
    """Parenthesized groups are parsed as a single sub-expression."""
    node = parse_line("(1 + 2) * 3")
    assert node == BinOp("*", BinOp("+", Number(1), Number(2)), Number(3))


def test_assignment() -> None:
    """A leading identifier followed by '=' parses as an Assign node."""
    node = parse_line("discount = 10%")
    assert node == Assign("discount", Percent(Number(10)))


def test_line_reference() -> None:
    """An identifier of the form lineN parses as a LineRef, not a Var."""
    node = parse_line("line3 + 1")
    assert node == BinOp("+", LineRef(3), Number(1))


def test_plain_identifier_is_a_variable() -> None:
    """A non-reserved identifier (not lineN, total/sum/average, ...) is a Var."""
    node = parse_line("widgets")
    assert node == Var("widgets")


def test_percent_of() -> None:
    """'N% of A' parses as a PercentOf node."""
    node = parse_line("20% of 40")
    assert node == PercentOf(Number(20), Number(40))


def test_of_without_leading_percent_is_a_parse_error() -> None:
    """'of' is only meaningful right after a percentage; otherwise invalid."""
    with pytest.raises(ParseError):
        parse_line("5 of 40")


def test_trailing_garbage_is_a_parse_error() -> None:
    """Leftover tokens after a complete expression raise ParseError."""
    with pytest.raises(ParseError):
        parse_line("1 + 2 3")


def test_unclosed_paren_is_a_parse_error() -> None:
    """A missing closing parenthesis raises ParseError."""
    with pytest.raises(ParseError):
        parse_line("(1 + 2")


def test_prose_line_is_a_parse_error() -> None:
    """Ordinary text with no operators between words fails to parse."""
    with pytest.raises(ParseError):
        parse_line("buy milk and eggs")
