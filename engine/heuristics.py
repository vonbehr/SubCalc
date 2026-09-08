"""Best-effort heuristic for telling an attempted calculation from prose.

Used only to decide whether a line that failed to evaluate deserves an
inline error indicator in the editor -- never by the engine itself, which
already treats every failure identically (no result). Getting this
heuristic exactly right is impossible in general (natural language and
calculator syntax overlap too much), so it deliberately errs conservative:
a bare number next to ordinary words ("5 apples") is not flagged, but any
operator, keyword, or line/label reference is.
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


def looks_like_calculation(line: str) -> bool:
    """Checks whether a line contains a signal suggesting a calculation.

    A line is flagged if it was likely meant as a calculation, rather than
    ordinary prose.

    Args:
        line: A single line of ``.calc`` source.

    Returns:
        True if the line contains an operator, a reserved keyword, a
        line/label reference, a date literal, or an unparseable character.
    """
    comment_start = line.find("//")
    code = line if comment_start == -1 else line[:comment_start]
    if not code.strip():
        return False

    try:
        tokens = tokenize(code)
    except TokenizeError:
        return True

    for index, token in enumerate(tokens):
        if token.type == "DATE":
            return True
        if token.type == "OP" and token.value == "#":
            # "#" only signals a label *reference* (e.g. "#subtotal") when
            # followed by a name; "#482" is far more often prose (an issue,
            # PR, or room number) than a broken label.
            next_token = tokens[index + 1] if index + 1 < len(tokens) else None
            if next_token is not None and next_token.type == "IDENT":
                return True
            continue
        if token.type == "OP" and token.value in _OPERATOR_VALUES:
            return True
        if token.type == "IDENT":
            lowered = token.value.lower()
            if lowered in _KEYWORDS or lowered in _REFERENCE_WORDS:
                return True
            suffix = lowered[len(_LINE_REF_PREFIX) :]
            if lowered.startswith(_LINE_REF_PREFIX) and suffix.isdigit() and suffix:
                return True
    return False
