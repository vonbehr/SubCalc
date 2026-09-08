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
