"""Evaluates parsed lines against a running variable/line-result environment."""

from __future__ import annotations

from dataclasses import dataclass, field

from .errors import EvalError, SubCalcError
from .parser import (
    Assign,
    BinOp,
    LineRef,
    Node,
    Number,
    Percent,
    PercentOf,
    Unary,
    Var,
    parse_line,
)


@dataclass
class Environment:
    """Running state threaded through the evaluation of a buffer.

    Attributes:
        variables: Values assigned so far, keyed by variable name. Lookups
            only ever see assignments from earlier lines, matching the
            top-to-bottom, no-forward-references behavior of Soulver and
            NotesCalculator.
        line_results: The result of each line evaluated so far, in order,
            with ``None`` for lines that produced no result (blank, prose,
            or a failed calculation). Used to resolve ``lineN`` references.
    """

    variables: dict[str, float] = field(default_factory=dict)
    line_results: list[float | None] = field(default_factory=list)


def eval_node(node: Node, env: Environment) -> float:
    """Recursively evaluates an AST node.

    Args:
        node: The AST node to evaluate, as produced by
            :func:`engine.parser.parse`.
        env: The current variable and line-result state.

    Returns:
        The numeric value of the node.

    Raises:
        EvalError: If the node references an unknown variable, an invalid
            or unresolved line, or performs an invalid operation such as
            division by zero.
    """
    if isinstance(node, Number):
        return node.value

    if isinstance(node, Var):
        try:
            return env.variables[node.name]
        except KeyError:
            raise EvalError(f"Unknown variable: {node.name}") from None

    if isinstance(node, LineRef):
        index = node.line_number - 1
        if index < 0 or index >= len(env.line_results):
            raise EvalError(f"line{node.line_number} has not been evaluated yet")
        value = env.line_results[index]
        if value is None:
            raise EvalError(f"line{node.line_number} has no result")
        return value

    if isinstance(node, Unary):
        value = eval_node(node.expr, env)
        return -value if node.op == "-" else value

    if isinstance(node, Percent):
        return eval_node(node.expr, env) / 100

    if isinstance(node, PercentOf):
        percent = eval_node(node.percent, env) / 100
        target = eval_node(node.target, env)
        return percent * target

    if isinstance(node, BinOp):
        return _eval_binop(node, env)

    raise EvalError(f"Cannot evaluate node of type {type(node).__name__}")


def _eval_binop(node: BinOp, env: Environment) -> float:
    """Evaluates a binary operation, applying percent-of-left-operand rules.

    ``A + N%`` and ``A - N%`` treat the percentage as "N percent of A" (e.g.
    ``40 - 20%`` is ``32``), so those two cases evaluate the left operand
    once and derive the percentage from it rather than evaluating the
    right-hand :class:`Percent` node generically.
    """
    if node.op in ("+", "-") and isinstance(node.right, Percent):
        left = eval_node(node.left, env)
        fraction = eval_node(node.right.expr, env) / 100
        delta = left * fraction
        return left + delta if node.op == "+" else left - delta

    left = eval_node(node.left, env)
    right = eval_node(node.right, env)

    if node.op == "+":
        return left + right
    if node.op == "-":
        return left - right
    if node.op == "*":
        return left * right
    if node.op == "/":
        if right == 0:
            raise EvalError("Division by zero")
        return left / right
    if node.op == "^":
        try:
            result = left**right
        except (OverflowError, ValueError, ZeroDivisionError) as exc:
            raise EvalError(f"Invalid exponentiation: {exc}") from exc
        if isinstance(result, complex):
            # E.g. (-1) ** 0.5: Python's ** promotes negative-base fractional
            # powers to complex instead of raising; we have no complex display.
            raise EvalError("Exponentiation produced a complex result")
        return result

    raise EvalError(f"Unknown operator: {node.op}")


def evaluate_line(line: str, env: Environment) -> float | None:
    """Evaluates a single line, updating ``env`` with any assignment made.

    Args:
        line: A single line of ``.calc`` source.
        env: The environment to evaluate against and, for assignment lines,
            update in place.

    Returns:
        The line's numeric result, or ``None`` if the line is blank or
        comment-only.

    Raises:
        SubCalcError: If the line cannot be tokenized, parsed, or evaluated
            (see :mod:`engine.errors`). Callers processing a whole buffer
            should catch this to treat the line as ordinary prose.
    """
    node = parse_line(line)
    if isinstance(node, Assign):
        value = eval_node(node.expr, env)
        env.variables[node.name] = value
        return value
    return eval_node(node, env)


def evaluate_buffer(lines: list[str]) -> list[float | None]:
    """Evaluates every line of a buffer in order, top to bottom.

    Lines that are blank, prose, or fail to evaluate for any reason are
    silently treated as having no result -- this tolerance is what lets the
    engine coexist with free-form notes in the same file.

    Args:
        lines: The buffer's lines, in order, without trailing newlines.

    Returns:
        One result per input line, ``None`` where the line had no result.
    """
    env = Environment()
    results: list[float | None] = []
    for line in lines:
        try:
            value = evaluate_line(line, env)
        except SubCalcError:
            value = None
        results.append(value)
        env.line_results.append(value)
    return results
