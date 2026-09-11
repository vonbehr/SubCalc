"""Lexer that turns a single line of ``.calc`` source into a token stream."""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import dates
from .errors import TokenizeError

#: The symbol that separates function-call arguments (e.g. ``round(pi, 2)``),
#: keyed by decimal_separator. When "," is the decimal point it can no
#: longer double as an argument separator, so ";" takes over instead (the
#: same convention spreadsheets use for locales with a comma decimal point).
ARG_SEPARATORS = {".": ",", ",": ";"}

#: The NUMBER pattern, keyed by decimal_separator. Whichever of "," and "."
#: isn't the decimal point may still optionally group the integer part
#: (e.g. "1,234.5" or "1.234,5"); "_" always may, regardless of separator.
_NUMBER_PATTERNS = {
    ".": r"\d[\d_]*(?:,\d[\d_]*)*(?:\.\d+)?(?:[eE][+-]?\d+)?",
    ",": r"\d[\d_]*(?:\.\d[\d_]*)*(?:,\d+)?(?:[eE][+-]?\d+)?",
}


def _build_token_re(decimal_separator: str) -> re.Pattern[str]:
    token_spec = [
        ("DATE", dates.TOKEN_PATTERN),
        ("TIME", r"\d{1,2}:\d{2}(?::\d{2})?"),
        ("NUMBER", _NUMBER_PATTERNS[decimal_separator]),
        ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
        # "," and ";" are both always recognized as operators, regardless of
        # decimal_separator, so an ordinary prose comma (or, in a
        # comma-decimal line, a semicolon) never fails to tokenize -- only
        # the one named in ARG_SEPARATORS is meaningful to the parser as a
        # function-argument separator; the other is simply an inert OP
        # token that fails to parse in context, same as any stray symbol.
        ("OP", r"[+\-*/^()=%#,;$€£¥]"),
        ("WHITESPACE", r"[ \t]+"),
        ("MISMATCH", r"."),
    ]
    return re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in token_spec))


_TOKEN_RE_BY_SEPARATOR = {sep: _build_token_re(sep) for sep in _NUMBER_PATTERNS}


@dataclass(frozen=True)
class Token:
    """A single lexical token.

    Attributes:
        type: One of ``"NUMBER"``, ``"DATE"``, ``"TIME"``, ``"IDENT"``,
            ``"OP"``, or ``"EOF"``.
        value: The raw source text the token was matched from.
        pos: The zero-based column offset the token starts at, used for
            error messages.
    """

    type: str
    value: str
    pos: int


def tokenize(line: str, decimal_separator: str = ".") -> list[Token]:
    """Tokenizes one line of source, ignoring any trailing ``//`` comment.

    Args:
        line: A single line of ``.calc`` source, without its trailing newline.
        decimal_separator: The symbol that acts as the decimal point in
            NUMBER literals, ``"."`` (the default) or ``","``. This also
            determines which symbol separates function-call arguments; see
            :data:`ARG_SEPARATORS`.

    Returns:
        The tokens found in the line, followed by a terminating ``EOF``
        token. A blank or comment-only line yields just the ``EOF`` token.

    Raises:
        TokenizeError: If the line contains a character that does not match
            any known token, such as an unsupported symbol.
        ValueError: If ``decimal_separator`` is not ``"."`` or ``","``.
    """
    token_re = _TOKEN_RE_BY_SEPARATOR.get(decimal_separator)
    if token_re is None:
        raise ValueError(f"Unknown decimal separator: {decimal_separator!r}")

    comment_start = line.find("//")
    code = line if comment_start == -1 else line[:comment_start]

    tokens: list[Token] = []
    for match in token_re.finditer(code):
        kind = match.lastgroup
        assert kind is not None  # every alternative above is a named group
        if kind == "WHITESPACE":
            continue
        if kind == "MISMATCH":
            raise TokenizeError(
                f"Unexpected character {match.group()!r} at position {match.start()}"
            )
        tokens.append(Token(kind, match.group(), match.start()))

    tokens.append(Token("EOF", "", len(code)))
    return tokens
