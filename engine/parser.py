"""Recursive-descent parser producing an AST from a :mod:`tokenizer` stream.

Grammar (lowest to highest precedence)::

    line       := (IDENT "=" conversion | conversion) ("#" IDENT)?
                | keyword_line
    keyword_line := ("total" | "sum" | "average")   -- the entire line
    conversion := to_expr (("in" | "as") unit_name)?
    to_expr    := additive ("to" additive)?
    additive   := multiplicative (("+" | "-") multiplicative)*
    multiplicative := of_term (("*" | "/") of_term | implicit_factor)*
    of_term    := percent (IDENT("of") percent)?
    percent    := power ("%")*
    power      := unary ("^" power)?
    unary      := "-" unary | primary
    primary    := NUMBER unit_name? | DATE | TIME | CURRENCY NUMBER | "#" IDENT
                | IDENT "(" (additive ("," additive)*)? ")"
                | IDENT | "(" additive ")"
    unit_name  := IDENT | CURRENCY   -- a unit word (e.g. "km") or a currency
                                        symbol (e.g. "€"), pre- or postfix

``of`` is only consumed as the "of" keyword when the left-hand side is a
percentage; otherwise it is left for the caller, which then fails to find a
combining operator and raises :class:`ParseError` -- the intended outcome for
ordinary prose lines that happen to contain the word "of". ``in``/``as``/
``to`` behave the same way: they are keywords only where the grammar above
expects them, and otherwise ordinary identifiers.

An implicit multiplication factor is a ``(`` (e.g. ``2(3 + 4)``) or, right
after a bare number, an immediately adjacent identifier that isn't a
reserved word or a function call (e.g. ``3x``) -- adjacency is required so
that ordinary prose like "5 apples" is left alone.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Union

from . import dates, units
from .errors import ParseError
from .tokenizer import Token, tokenize

_LINE_REF_PREFIX = "line"
_FUNCTIONS = frozenset({"sqrt", "abs", "round", "floor", "ceil", "min", "max"})
_AGGREGATE_KEYWORDS = frozenset({"total", "sum", "average"})
_RESERVED_WORDS = _FUNCTIONS | _AGGREGATE_KEYWORDS | {"of", "in", "as", "to", "today", "now"}


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
class LabelRef:
    """A reference to a labeled line's result, e.g. ``#subtotal``."""

    name: str


@dataclass(frozen=True)
class Today:
    """The ``today`` keyword, evaluating to the current date."""


@dataclass(frozen=True)
class Now:
    """The ``now`` keyword, evaluating to the current time of day."""


@dataclass(frozen=True)
class DateLiteral:
    """A date literal (ISO, dotted, or German -- see :mod:`engine.dates`)."""

    date: datetime.date


@dataclass(frozen=True)
class TimeLiteral:
    """A ``HH:MM`` or ``HH:MM:SS`` time-of-day literal."""

    time: datetime.time


@dataclass(frozen=True)
class Percent:
    """A value suffixed with ``%``, e.g. the ``20%`` in ``20% of 40``."""

    expr: Node


@dataclass(frozen=True)
class PercentOf:
    """A resolved ``N% of A`` expression."""

    percent: Node
    target: Node


@dataclass(frozen=True)
class Quantity:
    """A number literal tagged with a unit or currency, e.g. ``5 km``."""

    value: Node
    unit: str


@dataclass(frozen=True)
class ConvertTo:
    """An ``expr in unit`` / ``expr as unit`` conversion."""

    expr: Node
    unit: str


@dataclass(frozen=True)
class DateRange:
    """A ``start to end`` date difference."""

    start: Node
    end: Node


@dataclass(frozen=True)
class FunctionCall:
    """A call to one of the built-in functions, e.g. ``sqrt(16)``."""

    name: str
    args: list[Node]


@dataclass(frozen=True)
class Aggregate:
    """A bare ``total`` / ``sum`` / ``average`` line summarizing a block."""

    kind: str


@dataclass(frozen=True)
class BinOp:
    """A binary arithmetic operation."""

    op: str
    left: Node
    right: Node


@dataclass(frozen=True)
class Unary:
    """A unary operation, currently only negation."""

    op: str
    expr: Node


@dataclass(frozen=True)
class Assign:
    """A variable assignment, e.g. ``discount = 10%``."""

    name: str
    expr: Node


@dataclass(frozen=True)
class Labeled:
    """A line whose result is also tagged with a ``#name`` label."""

    expr: Node
    name: str


Node = Union[
    Number,
    Var,
    LineRef,
    LabelRef,
    Today,
    Now,
    DateLiteral,
    TimeLiteral,
    Percent,
    PercentOf,
    Quantity,
    ConvertTo,
    DateRange,
    FunctionCall,
    Aggregate,
    BinOp,
    Unary,
    Assign,
    Labeled,
]


class _Parser:
    """Stateful recursive-descent parser over a fixed token list."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _peek_next(self) -> Token:
        return self._tokens[self._pos + 1]

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
        if self._is_bare_keyword_line():
            kind = self._advance().value.lower()
            self._expect_eof()
            return Aggregate(kind)

        if self._is_assignment_start():
            name = self._advance().value
            self._advance()  # consume "="
            expr = self._parse_conversion()
            node: Node = Assign(name, expr)
        else:
            node = self._parse_conversion()

        node = self._maybe_attach_label(node)
        self._expect_eof()
        return node

    def _is_bare_keyword_line(self) -> bool:
        token = self._peek()
        if token.type != "IDENT" or token.value.lower() not in _AGGREGATE_KEYWORDS:
            return False
        return self._peek_next().type == "EOF"

    def _is_assignment_start(self) -> bool:
        return (
            self._peek().type == "IDENT"
            and self._peek_next().type == "OP"
            and self._peek_next().value == "="
            and not self._is_line_ref(self._peek().value)
        )

    def _maybe_attach_label(self, node: Node) -> Node:
        if not self._at_op("#"):
            return node
        self._advance()
        label_token = self._peek()
        if label_token.type != "IDENT":
            raise ParseError(f"Expected a label name at position {label_token.pos}")
        self._advance()
        return Labeled(node, label_token.value)

    def _expect_eof(self) -> None:
        token = self._peek()
        if token.type != "EOF":
            raise ParseError(f"Unexpected token {token.value!r} at position {token.pos}")

    def _parse_conversion(self) -> Node:
        left = self._parse_to()
        if self._at_keyword("in") or self._at_keyword("as"):
            self._advance()
            unit = self._expect_unit_name()
            return ConvertTo(left, unit)
        return left

    def _expect_unit_name(self) -> str:
        token = self._peek()
        if token.type == "IDENT" or (
            token.type == "OP" and token.value in units.CURRENCY_SYMBOLS
        ):
            self._advance()
            return token.value
        raise ParseError(f"Expected a unit name at position {token.pos}")

    def _parse_to(self) -> Node:
        left = self._parse_additive()
        if self._at_keyword("to"):
            self._advance()
            right = self._parse_additive()
            return DateRange(left, right)
        return left

    def _parse_additive(self) -> Node:
        left = self._parse_multiplicative()
        while self._at_op("+") or self._at_op("-"):
            op = self._advance().value
            right = self._parse_multiplicative()
            left = BinOp(op, left, right)
        return left

    def _parse_multiplicative(self) -> Node:
        left = self._parse_of_term()
        while True:
            if self._at_op("*") or self._at_op("/"):
                op = self._advance().value
                right = self._parse_of_term()
                left = BinOp(op, left, right)
                continue
            if self._at_implicit_factor(left):
                right = self._parse_of_term()
                left = BinOp("*", left, right)
                continue
            break
        return left

    def _at_implicit_factor(self, left: Node) -> bool:
        token = self._peek()
        if token.type == "OP" and token.value == "(":
            return True
        if (
            token.type == "IDENT"
            and token.value.lower() not in _RESERVED_WORDS
            and isinstance(left, Number)
        ):
            prev = self._tokens[self._pos - 1]
            adjacent = prev.pos + len(prev.value) == token.pos
            is_call = self._peek_next().type == "OP" and self._peek_next().value == "("
            return adjacent and not is_call
        return False

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
            return self._maybe_attach_unit(Number(_parse_number_literal(token.value)))

        if token.type == "DATE":
            self._advance()
            return DateLiteral(_parse_date_literal(token.value))

        if token.type == "TIME":
            self._advance()
            return TimeLiteral(_parse_time_literal(token.value))

        if token.type == "OP" and token.value in units.CURRENCY_SYMBOLS:
            self._advance()
            number_token = self._peek()
            if number_token.type != "NUMBER":
                raise ParseError(
                    f"Expected a number after {token.value!r} at position {number_token.pos}"
                )
            self._advance()
            return Quantity(Number(_parse_number_literal(number_token.value)), token.value)

        if token.type == "OP" and token.value == "#":
            self._advance()
            label_token = self._peek()
            if label_token.type != "IDENT":
                raise ParseError(f"Expected a label name at position {label_token.pos}")
            self._advance()
            return LabelRef(label_token.value)

        if token.type == "IDENT":
            self._advance()
            lowered = token.value.lower()
            if lowered == "today":
                return Today()
            if lowered == "now":
                return Now()
            line_number = self._is_line_ref(token.value)
            if line_number is not None:
                return LineRef(line_number)
            if lowered in _FUNCTIONS and self._at_op("("):
                return self._parse_function_call(lowered)
            return Var(token.value)

        if token.type == "OP" and token.value == "(":
            self._advance()
            expr = self._parse_additive()
            if not self._at_op(")"):
                raise ParseError(f"Expected ')' at position {self._peek().pos}")
            self._advance()
            return expr

        raise ParseError(f"Unexpected token {token.value!r} at position {token.pos}")

    def _maybe_attach_unit(self, node: Number) -> Node:
        token = self._peek()
        if token.type == "IDENT" and units.lookup_unit(token.value) is not None:
            self._advance()
            return Quantity(node, token.value)
        if token.type == "OP" and token.value in units.CURRENCY_SYMBOLS:
            self._advance()
            return Quantity(node, token.value)
        return node

    def _parse_function_call(self, name: str) -> Node:
        self._advance()  # consume "("
        args: list[Node] = []
        if not self._at_op(")"):
            args.append(self._parse_additive())
            while self._at_op(","):
                self._advance()
                args.append(self._parse_additive())
        if not self._at_op(")"):
            raise ParseError(f"Expected ')' at position {self._peek().pos}")
        self._advance()
        return FunctionCall(name, args)

    @staticmethod
    def _is_line_ref(identifier: str) -> int | None:
        lowered = identifier.lower()
        if not lowered.startswith(_LINE_REF_PREFIX):
            return None
        suffix = lowered[len(_LINE_REF_PREFIX) :]
        if suffix.isdigit() and suffix:
            return int(suffix)
        return None


def _parse_number_literal(text: str) -> float:
    """Converts a NUMBER token's raw text into a float.

    Args:
        text: The token's raw source text, e.g. ``"1,000_000.5"`` or
            ``"2.5e-3"``.

    Returns:
        The parsed value.
    """
    return float(text.replace(",", "").replace("_", ""))


def _parse_date_literal(text: str) -> datetime.date:
    """Converts a DATE token's raw text into a :class:`datetime.date`.

    Args:
        text: The token's raw source text, in any format
            :func:`engine.dates.parse_date` accepts.

    Returns:
        The parsed date.

    Raises:
        ParseError: If the text is not a valid calendar date.
    """
    try:
        return dates.parse_date(text)
    except ValueError as exc:
        raise ParseError(f"Invalid date {text!r}: {exc}") from exc


def _parse_time_literal(text: str) -> datetime.time:
    """Converts a TIME token's raw text into a :class:`datetime.time`.

    Args:
        text: The token's raw ``HH:MM`` or ``HH:MM:SS`` source text.

    Returns:
        The parsed time of day.

    Raises:
        ParseError: If the text is not a valid time of day (e.g. hour 25).
    """
    try:
        return datetime.time.fromisoformat(text)
    except ValueError as exc:
        raise ParseError(f"Invalid time {text!r}: {exc}") from exc


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
