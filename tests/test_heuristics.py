"""Tests for engine.heuristics.looks_like_calculation."""

from __future__ import annotations

from engine.heuristics import looks_like_calculation


def test_blank_line_is_not_a_calculation() -> None:
    assert looks_like_calculation("") is False


def test_comment_only_line_is_not_a_calculation() -> None:
    assert looks_like_calculation("// just a note") is False


def test_prose_without_operators_is_not_flagged() -> None:
    assert looks_like_calculation("Grocery budget") is False


def test_number_next_to_a_word_is_not_flagged() -> None:
    """A bare number in prose ('5 apples', '3pm', 'page 5') is too common.

    Flagging it would be noisy; only real calculator signals (operators,
    keywords, references) are flagged.
    """
    assert looks_like_calculation("5 apples") is False


def test_trailing_operator_is_flagged() -> None:
    assert looks_like_calculation("rent +") is True


def test_broken_arithmetic_is_flagged() -> None:
    assert looks_like_calculation("10 / 0") is True


def test_assignment_is_flagged() -> None:
    assert looks_like_calculation("rent = ") is True


def test_line_reference_is_flagged() -> None:
    assert looks_like_calculation("line1 + line2") is True


def test_label_reference_is_flagged() -> None:
    assert looks_like_calculation("#subtotal * 2") is True


def test_hash_followed_by_a_number_is_not_flagged() -> None:
    """'Invoice #482', 'Issue #17', 'Room #12' are common prose.

    '#' only signals a label reference when followed by a name, not a
    number.
    """
    assert looks_like_calculation("Invoice #482") is False


def test_unknown_character_is_flagged() -> None:
    assert looks_like_calculation("3 @ 4") is True


def test_of_keyword_is_flagged() -> None:
    assert looks_like_calculation("20% of bacon") is True
