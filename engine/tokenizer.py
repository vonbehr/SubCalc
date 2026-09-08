"""Lexer that turns a single line of ``.calc`` source into a token stream."""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import dates
from .errors import TokenizeError

_TOKEN_SPEC = [
    ("DATE", dates.TOKEN_PATTERN),
    ("TIME", r"\d{1,2}:\d{2}(?::\d{2})?"),
    ("NUMBER", r"\d[\d_]*(?:,\d[\d_]*)*(?:\.\d+)?(?:[eE][+-]?\d+)?"),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OP", r"[+\-*/^()=%#,$€£¥]"),
    ("WHITESPACE", r"[ \t]+"),
    ("MISMATCH", r"."),
]
_TOKEN_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in _TOKEN_SPEC))


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


def tokenize(line: str) -> list[Token]:
    """Tokenizes one line of source, ignoring any trailing ``//`` comment.

    Args:
        line: A single line of ``.calc`` source, without its trailing newline.

    Returns:
        The tokens found in the line, followed by a terminating ``EOF``
        token. A blank or comment-only line yields just the ``EOF`` token.

    Raises:
        TokenizeError: If the line contains a character that does not match
            any known token, such as an unsupported symbol.
    """
    comment_start = line.find("//")
    code = line if comment_start == -1 else line[:comment_start]

    tokens: list[Token] = []
    for match in _TOKEN_RE.finditer(code):
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
