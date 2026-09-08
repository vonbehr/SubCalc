"""Recursive-descent parser producing an AST from a :mod:`tokenizer` stream.

Grammar (lowest to highest precedence)::

    line       := (IDENT "=" additive) | additive
    additive   := multiplicative (("+" | "-") multiplicative)*
    multiplicative := of_term (("*" | "/") of_term)*
    of_term    := percent (IDENT("of") percent)?
    percent    := power ("%")*
    power      := unary ("^" power)?
    unary      := "-" unary | primary
    primary    := NUMBER | IDENT | "(" additive ")"

``of`` is only consumed as the "of" keyword when the left-hand side is a
percentage; otherwise it is left for the caller, which then fails to find a
combining operator and raises :class:`ParseError` -- the intended outcome for
ordinary prose lines that happen to contain the word "of".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .errors import ParseError
from .tokenizer import Token, tokenize


@dataclass(frozen=True)
class Number:
    """A literal numeric value."""

    value: float


@dataclass(frozen=True)
class Var:
    """A reference to a user-defined variable."""

    name: str


@dataclass(frozen=True)
class LineRef:
    """A reference to another line's result, e.g. ``line3``."""

    line_number: int


@dataclass(frozen=True)
class Percent:
    """A value suffixed with ``%``, e.g. the ``20%`` in ``20% of 40``."""

    expr: "Node"


@dataclass(frozen=True)
class PercentOf:
    """A resolved ``N% of A`` expression."""

    percent: "Node"
    target: "Node"


@dataclass(frozen=True)
class BinOp:
    """A binary arithmetic operation."""

    op: str
    left: "Node"
    right: "Node"


@dataclass(frozen=True)
class Unary:
    """A unary operation, currently only negation."""

    op: str
    expr: "Node"


@dataclass(frozen=True)
class Assign:
    """A variable assignment, e.g. ``discount = 10%``."""

    name: str
    expr: "Node"


Node = Union[Number, Var, LineRef, Percent, PercentOf, BinOp, Unary, Assign]

_LINE_REF_PREFIX = "line"


class _Parser:
    """Stateful recursive-descent parser over a fixed token list."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _at_op(self, value: str) -> bool:
        token = self._peek()
        return token.type == "OP" and token.value == value

    def _at_keyword(self, keyword: str) -> bool:
        token = self._peek()
        return token.type == "IDENT" and token.value.lower() == keyword

    def parse_line(self) -> Node:
        if (
            self._peek().type == "IDENT"
            and self._tokens[self._pos + 1].type == "OP"
            and self._tokens[self._pos + 1].value == "="
            and not self._is_line_ref(self._peek().value)
        ):
            name = self._advance().value
            self._advance()  # consume "="
            expr = self._parse_additive()
            self._expect_eof()
            return Assign(name, expr)

        expr = self._parse_additive()
        self._expect_eof()
        return expr

    def _expect_eof(self) -> None:
        token = self._peek()
        if token.type != "EOF":
            raise ParseError(f"Unexpected token {token.value!r} at position {token.pos}")

    def _parse_additive(self) -> Node:
        left = self._parse_multiplicative()
        while self._at_op("+") or self._at_op("-"):
            op = self._advance().value
            right = self._parse_multiplicative()
            left = BinOp(op, left, right)
        return left

    def _parse_multiplicative(self) -> Node:
        left = self._parse_of_term()
        while self._at_op("*") or self._at_op("/"):
            op = self._advance().value
            right = self._parse_of_term()
            left = BinOp(op, left, right)
        return left

    def _parse_of_term(self) -> Node:
        left = self._parse_percent()
        if isinstance(left, Percent) and self._at_keyword("of"):
            self._advance()  # consume "of"
            target = self._parse_percent()
            return PercentOf(left.expr, target)
        return left

    def _parse_percent(self) -> Node:
        node = self._parse_power()
        while self._at_op("%"):
            self._advance()
            node = Percent(node)
        return node

    def _parse_power(self) -> Node:
        base = self._parse_unary()
        if self._at_op("^"):
            self._advance()
            exponent = self._parse_power()  # right-associative
            return BinOp("^", base, exponent)
        return base

    def _parse_unary(self) -> Node:
        if self._at_op("-"):
            self._advance()
            return Unary("-", self._parse_unary())
        return self._parse_primary()

    def _parse_primary(self) -> Node:
        token = self._peek()

        if token.type == "NUMBER":
            self._advance()
            return Number(float(token.value.replace(",", "").replace("_", "")))

        if token.type == "IDENT":
            self._advance()
            line_number = self._is_line_ref(token.value)
            if line_number is not None:
                return LineRef(line_number)
            return Var(token.value)

        if token.type == "OP" and token.value == "(":
            self._advance()
            expr = self._parse_additive()
            if not self._at_op(")"):
                raise ParseError(f"Expected ')' at position {self._peek().pos}")
            self._advance()
            return expr

        raise ParseError(f"Unexpected token {token.value!r} at position {token.pos}")

    @staticmethod
    def _is_line_ref(identifier: str) -> int | None:
        lowered = identifier.lower()
        if not lowered.startswith(_LINE_REF_PREFIX):
            return None
        suffix = lowered[len(_LINE_REF_PREFIX):]
        if suffix.isdigit() and suffix:
            return int(suffix)
        return None


def parse(tokens: list[Token]) -> Node:
    """Parses a full token stream for one line into an AST.

    Args:
        tokens: The token stream produced by :func:`engine.tokenizer.tokenize`,
            including the terminating ``EOF`` token.

    Returns:
        The root AST node for the line -- an :class:`Assign` for assignment
        lines, otherwise the parsed expression.

    Raises:
        ParseError: If the tokens do not form a valid expression or
            assignment, or if trailing tokens remain after a valid one.
    """
    return _Parser(tokens).parse_line()


def parse_line(line: str) -> Node:
    """Convenience wrapper that tokenizes and parses a raw source line.

    Args:
        line: A single line of ``.calc`` source.

    Returns:
        The root AST node for the line, as returned by :func:`parse`.

    Raises:
        TokenizeError: If the line cannot be tokenized.
        ParseError: If the tokens do not form a valid expression or
            assignment.
    """
    return parse(tokenize(line))
