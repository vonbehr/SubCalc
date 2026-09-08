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


def test_isolated_invalid_date_is_flagged() -> None:
    """A bare, otherwise-invalid date is worth flagging.

    It's most likely a typo, e.g. day/month swapped.
    """
    assert looks_like_calculation("2026-13-05") is True


def test_date_embedded_in_prose_is_not_flagged() -> None:
    """A date mentioned in an ordinary sentence isn't a calculation.

    Only an operator/keyword alongside it, or the date standing alone,
    counts.
    """
    assert looks_like_calculation("Meeting on 2026-07-05 at the office") is False


def test_time_embedded_in_prose_is_not_flagged() -> None:
    assert looks_like_calculation("Call John at 15:00 about the budget") is False


def test_date_with_operator_is_flagged() -> None:
    assert looks_like_calculation("2026-01-01 + 30 days") is True


def test_hyphenated_word_is_not_flagged() -> None:
    """A '-' flanked by letters with no space is a compound word.

    Not a minus sign, e.g. 'check-in'.
    """
    assert looks_like_calculation("Flight check-in") is False


def test_hyphenated_word_variants_are_not_flagged() -> None:
    assert looks_like_calculation("well-being") is False
    assert looks_like_calculation("Buy a T-shirt") is False
    assert looks_like_calculation("Keep up-to-date") is False


def test_spaced_minus_is_still_flagged() -> None:
    assert looks_like_calculation("rent - 100") is True


def test_leading_minus_before_digit_is_still_flagged() -> None:
    assert looks_like_calculation("-5 + 3") is True


def test_minus_with_space_only_before_is_still_flagged() -> None:
    """'total -typo' (space before, none after) isn't a compound word.

    Only letter-hyphen-letter with no space on either side is.
    """
    assert looks_like_calculation("total -typo") is True
