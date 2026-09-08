"""Best-effort heuristic for telling an attempted calculation from prose.

Used only to decide whether a line that failed to evaluate deserves an
inline error indicator in the editor -- never by the engine itself, which
already treats every failure identically (no result). Getting this
heuristic exactly right is impossible in general (natural language and
calculator syntax overlap too much), so it deliberately errs conservative:
a bare number next to ordinary words ("5 apples") is not flagged, but any
operator, keyword, or line/label reference is.

A date or time literal is a weaker signal than an operator: on its own
("2026-07-05", to catch a typo'd date) it counts, but a date or time
embedded among ordinary prose words ("Meeting on 2026-07-05 at the
office", "Call John at 15:00") does not, since that combination is far
more often a sentence than a broken calculation.

A "-" flanked by letters on both sides with no space ("check-in",
"well-being", "T-shirt") is treated as an English compound word, not a
minus sign -- real subtraction is written with at least one space
("rent - 100") or beside a digit ("-5"), essentially always. The one
trade-off is a tightly-written variable subtraction like "a-b" now reads
as prose too; that shape is rare enough next to how common hyphenated
words are that it's the right default.
"""

from __future__ import annotations

from .errors import TokenizeError
from .tokenizer import tokenize

_OPERATOR_VALUES = frozenset("+-*/^%=")
_KEYWORDS = frozenset({"of", "in", "as", "to"})
_REFERENCE_WORDS = frozenset(
    {
        "pi",
        "e",
        "today",
        "now",
        "total",
        "sum",
        "average",
        "sqrt",
        "abs",
        "round",
        "floor",
        "ceil",
        "min",
        "max",
    }
)
_LINE_REF_PREFIX = "line"


def _is_word_hyphen(code: str, pos: int) -> bool:
    """Checks whether the ``-`` at ``pos`` is a compound-word hyphen.

    Args:
        code: The line's code (comment already stripped).
        pos: The zero-based offset of the ``-`` character within ``code``.

    Returns:
        True if the characters immediately before and after are both
        letters with no space, the shape of a word like "check-in" rather
        than a minus sign.
    """
    before = code[pos - 1] if pos > 0 else ""
    after = code[pos + 1] if pos + 1 < len(code) else ""
    return before.isalpha() and after.isalpha()


def looks_like_calculation(line: str) -> bool:
    """Checks whether a line contains a signal suggesting a calculation.

    A line is flagged if it was likely meant as a calculation, rather than
    ordinary prose.

    Args:
        line: A single line of ``.calc`` source.

    Returns:
        True if the line contains an operator, a reserved keyword, a
        line/label reference, an unparseable character, or an isolated
        date/time literal (one with no other ordinary word on the line).
    """
    comment_start = line.find("//")
    code = line if comment_start == -1 else line[:comment_start]
    if not code.strip():
        return False

    try:
        tokens = tokenize(code)
    except TokenizeError:
        return True

    has_date_or_time = False
    has_stray_word = False
    for index, token in enumerate(tokens):
        if token.type in ("DATE", "TIME"):
            has_date_or_time = True
            continue
        if token.type == "OP" and token.value == "#":
            # "#" only signals a label *reference* (e.g. "#subtotal") when
            # followed by a name; "#482" is far more often prose (an issue,
            # PR, or room number) than a broken label.
            next_token = tokens[index + 1] if index + 1 < len(tokens) else None
            if next_token is not None and next_token.type == "IDENT":
                return True
            continue
        if token.type == "OP" and token.value == "-" and _is_word_hyphen(code, token.pos):
            continue
        if token.type == "OP" and token.value in _OPERATOR_VALUES:
            return True
        if token.type == "IDENT":
            lowered = token.value.lower()
            if lowered in _KEYWORDS or lowered in _REFERENCE_WORDS:
                continue
            suffix = lowered[len(_LINE_REF_PREFIX) :]
            if lowered.startswith(_LINE_REF_PREFIX) and suffix.isdigit() and suffix:
                continue
            has_stray_word = True

    return has_date_or_time and not has_stray_word
