"""Tests for engine.tokenizer."""

from __future__ import annotations

import pytest

from engine.errors import TokenizeError
from engine.tokenizer import tokenize


def test_blank_line_yields_only_eof() -> None:
    """An empty line tokenizes to just the terminating EOF token."""
    tokens = tokenize("")
    assert [t.type for t in tokens] == ["EOF"]


def test_comment_only_line_yields_only_eof() -> None:
    """A line that is entirely a comment produces no code tokens."""
    tokens = tokenize("// just a note")
    assert [t.type for t in tokens] == ["EOF"]


def test_trailing_comment_is_stripped() -> None:
    """Code before a trailing comment is tokenized; the comment is dropped."""
    tokens = tokenize("1 + 2 // running total")
    assert [t.value for t in tokens] == ["1", "+", "2", ""]


def test_number_with_separators_and_decimal() -> None:
    """Thousands separators (comma or underscore) are accepted in numbers."""
    tokens = tokenize("1,000_000.5")
    assert tokens[0].type == "NUMBER"
    assert tokens[0].value == "1,000_000.5"


def test_identifiers_and_operators() -> None:
    """A typical assignment line tokenizes into the expected token types."""
    tokens = tokenize("discount = 10%")
    assert [(t.type, t.value) for t in tokens] == [
        ("IDENT", "discount"),
        ("OP", "="),
        ("NUMBER", "10"),
        ("OP", "%"),
        ("EOF", ""),
    ]


def test_unknown_character_raises() -> None:
    """A character outside the supported syntax raises TokenizeError."""
    with pytest.raises(TokenizeError):
        tokenize("3 @ 4")


def test_comma_decimal_separator() -> None:
    """With decimal_separator=",", a comma is the decimal point."""
    tokens = tokenize("100,00", decimal_separator=",")
    assert tokens[0].type == "NUMBER"
    assert tokens[0].value == "100,00"


def test_comma_decimal_separator_groups_with_dot() -> None:
    """With decimal_separator=",", a dot may still group the integer part."""
    tokens = tokenize("1.000_000,5", decimal_separator=",")
    assert tokens[0].type == "NUMBER"
    assert tokens[0].value == "1.000_000,5"


def test_comma_decimal_separator_uses_semicolon_for_arguments() -> None:
    """With decimal_separator=",", ";" (not ",") separates call arguments."""
    tokens = tokenize("round(1,5; 2)", decimal_separator=",")
    assert [(t.type, t.value) for t in tokens] == [
        ("IDENT", "round"),
        ("OP", "("),
        ("NUMBER", "1,5"),
        ("OP", ";"),
        ("NUMBER", "2"),
        ("OP", ")"),
        ("EOF", ""),
    ]


def test_prose_comma_still_tokenizes_with_comma_decimal_separator() -> None:
    """An ordinary comma in prose is still a harmless OP token, not an error."""
    tokens = tokenize("rent, utilities, and groceries", decimal_separator=",")
    assert [t.type for t in tokens if t.type != "IDENT"] == ["OP", "OP", "EOF"]


def test_unknown_decimal_separator_raises() -> None:
    with pytest.raises(ValueError):
        tokenize("1.5", decimal_separator=";")
