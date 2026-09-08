"""Evaluates parsed lines against a running variable/line-result environment."""

from __future__ import annotations

import datetime
import math
from dataclasses import dataclass, field
from typing import Callable

from . import units
from .errors import EvalError, SubCalcError
from .parser import (
    Aggregate,
    Assign,
    BinOp,
    ConvertTo,
    DateLiteral,
    DateRange,
    FunctionCall,
    Labeled,
    LabelRef,
    LineRef,
    Node,
    Now,
    Number,
    Percent,
    PercentOf,
    TimeLiteral,
    Today,
    Unary,
    Var,
    parse_line,
)
from .parser import Quantity as QuantityLiteral
from .values import DateValue, Quantity, TimeValue, Value

_CONSTANTS: dict[str, float] = {"pi": math.pi, "e": math.e}

_DAY_SECONDS = 86400.0
_SECONDS_PER_DAY = 86400


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
        labels: Values assigned via a trailing ``#name`` label, keyed by
            label name. Like variables, only visible on later lines.
        block_start: The index into ``line_results`` where the current
            aggregate block began -- resets after every blank line, so
            ``total``/``sum``/``average`` only summarize the lines since
            the last blank line (or the start of the buffer).
    """

    variables: dict[str, Value] = field(default_factory=dict)
    line_results: list[Value | None] = field(default_factory=list)
    labels: dict[str, Value] = field(default_factory=dict)
    block_start: int = 0


def eval_node(node: Node, env: Environment) -> Value:
    """Recursively evaluates an AST node.

    Args:
        node: The AST node to evaluate, as produced by
            :func:`engine.parser.parse`.
        env: The current variable and line-result state.

    Returns:
        The node's value: a plain number, a unit-tagged :class:`Quantity`,
        or a :class:`DateValue`.

    Raises:
        EvalError: If the node references an unknown variable, label, or
            line, combines incompatible types (e.g. adding a length to a
            mass), or performs an invalid operation such as division by
            zero.
    """
    if isinstance(node, Number):
        return node.value

    if isinstance(node, Var):
        if node.name in env.variables:
            return env.variables[node.name]
        constant = _CONSTANTS.get(node.name.lower())
        if constant is not None:
            return constant
        raise EvalError(f"Unknown variable: {node.name}")

    if isinstance(node, LineRef):
        index = node.line_number - 1
        if index < 0 or index >= len(env.line_results):
            raise EvalError(f"line{node.line_number} has not been evaluated yet")
        value = env.line_results[index]
        if value is None:
            raise EvalError(f"line{node.line_number} has no result")
        return value

    if isinstance(node, LabelRef):
        try:
            return env.labels[node.name]
        except KeyError:
            raise EvalError(f"Unknown label: #{node.name}") from None

    if isinstance(node, Today):
        return DateValue(datetime.date.today())

    if isinstance(node, Now):
        return TimeValue(datetime.datetime.now().time())

    if isinstance(node, DateLiteral):
        return DateValue(node.date)

    if isinstance(node, TimeLiteral):
        return TimeValue(node.time)

    if isinstance(node, Unary):
        return _eval_unary(node, env)

    if isinstance(node, Percent):
        return _scale(eval_node(node.expr, env), 0.01)

    if isinstance(node, PercentOf):
        return _eval_percent_of(node, env)

    if isinstance(node, QuantityLiteral):
        return _eval_quantity_literal(node, env)

    if isinstance(node, ConvertTo):
        return _eval_convert_to(node, env)

    if isinstance(node, DateRange):
        return _eval_range(node, env)

    if isinstance(node, FunctionCall):
        return _eval_function_call(node, env)

    if isinstance(node, Aggregate):
        return _eval_aggregate(node, env)

    if isinstance(node, BinOp):
        return _eval_binop(node, env)

    raise EvalError(f"Cannot evaluate node of type {type(node).__name__}")


def _eval_unary(node: Unary, env: Environment) -> Value:
    value = eval_node(node.expr, env)
    if node.op != "-":
        return value
    if isinstance(value, float):
        return -value
    if isinstance(value, Quantity):
        return Quantity(-value.magnitude, value.dimension, value.unit)
    raise EvalError(f"Cannot negate a {_type_name(value)}")


def _scale(value: Value, factor: float) -> Value:
    """Multiplies a value's magnitude by ``factor``, preserving its unit."""
    if isinstance(value, float):
        return value * factor
    if isinstance(value, Quantity):
        return Quantity(value.magnitude * factor, value.dimension, value.unit)
    raise EvalError(f"Cannot take a percentage of a {_type_name(value)}")


def _eval_percent_of(node: PercentOf, env: Environment) -> Value:
    percent_value = eval_node(node.percent, env)
    if not isinstance(percent_value, float):
        raise EvalError("A percentage must be a plain number")
    target = eval_node(node.target, env)
    return _scale(target, percent_value / 100)


def _eval_quantity_literal(node: QuantityLiteral, env: Environment) -> Value:
    magnitude = eval_node(node.value, env)
    if not isinstance(magnitude, float):
        raise EvalError("Only a plain number can carry a unit")
    info = units.lookup_unit(node.unit)
    if info is None:
        raise EvalError(f"Unknown unit: {node.unit}")
    dimension, factor = info
    return Quantity(magnitude * factor, dimension, node.unit)


def _eval_convert_to(node: ConvertTo, env: Environment) -> Value:
    value = eval_node(node.expr, env)
    info = units.lookup_unit(node.unit)
    if info is None:
        raise EvalError(f"Unknown unit: {node.unit}")
    dimension, factor = info
    if isinstance(value, float):
        return Quantity(value * factor, dimension, node.unit)
    if isinstance(value, Quantity):
        if value.dimension != dimension:
            raise EvalError(f"Cannot convert {value.dimension} to {dimension}")
        return Quantity(value.magnitude, dimension, node.unit)
    raise EvalError(f"Cannot convert a {_type_name(value)} to a unit")


def _time_seconds(value: datetime.time) -> float:
    return value.hour * 3600 + value.minute * 60 + value.second


def _time_diff_unit(seconds: float) -> str:
    """Picks a readable display unit for a time-of-day difference.

    Args:
        seconds: The signed difference, in seconds.

    Returns:
        ``"minutes"`` for a difference under an hour, else ``"hours"`` --
        e.g. a 10-minute gap reads as "10 minutes", not "0.166667 hours".
    """
    return "hours" if abs(seconds) >= 3600 else "minutes"


def _eval_range(node: DateRange, env: Environment) -> Value:
    start = eval_node(node.start, env)
    end = eval_node(node.end, env)
    if isinstance(start, DateValue) and isinstance(end, DateValue):
        days = (end.date - start.date).days
        return Quantity(days * _DAY_SECONDS, "time", "days")
    if isinstance(start, TimeValue) and isinstance(end, TimeValue):
        seconds = _time_seconds(end.time) - _time_seconds(start.time)
        return Quantity(seconds, "time", _time_diff_unit(seconds))
    raise EvalError("'to' requires two dates or two times of day")


def _eval_aggregate(node: Aggregate, env: Environment) -> Value:
    block = [v for v in env.line_results[env.block_start :] if isinstance(v, float)]
    if node.kind == "average":
        if not block:
            raise EvalError("average of an empty block")
        return sum(block) / len(block)
    return float(sum(block))


def _eval_function_call(node: FunctionCall, env: Environment) -> Value:
    args: list[float] = []
    for arg_node in node.args:
        value = eval_node(arg_node, env)
        if not isinstance(value, float):
            raise EvalError(f"{node.name}() only accepts plain numbers")
        args.append(value)
    return _call_function(node.name, args)


def _check_arity(name: str, args: list[float], minimum: int, maximum: int | None) -> None:
    if len(args) < minimum or (maximum is not None and len(args) > maximum):
        raise EvalError(f"{name}() got an unexpected number of arguments")


def _call_function(name: str, args: list[float]) -> float:
    if name == "sqrt":
        _check_arity(name, args, 1, 1)
        if args[0] < 0:
            raise EvalError("sqrt of a negative number")
        return math.sqrt(args[0])
    if name == "abs":
        _check_arity(name, args, 1, 1)
        return abs(args[0])
    if name == "round":
        _check_arity(name, args, 1, 2)
        digits = int(args[1]) if len(args) == 2 else 0
        return float(round(args[0], digits))
    if name == "floor":
        _check_arity(name, args, 1, 1)
        return float(math.floor(args[0]))
    if name == "ceil":
        _check_arity(name, args, 1, 1)
        return float(math.ceil(args[0]))
    if name == "min":
        _check_arity(name, args, 1, None)
        return min(args)
    if name == "max":
        _check_arity(name, args, 1, None)
        return max(args)
    raise EvalError(f"Unknown function: {name}")


def _type_name(value: Value) -> str:
    if isinstance(value, Quantity):
        return value.dimension
    if isinstance(value, DateValue):
        return "date"
    if isinstance(value, TimeValue):
        return "time of day"
    return "number"


def _time_from_seconds(total_seconds: float) -> datetime.time:
    """Builds a wall-clock time from a seconds offset, wrapping past 24h."""
    whole = int(round(total_seconds)) % _SECONDS_PER_DAY
    hour, remainder = divmod(whole, 3600)
    minute, second = divmod(remainder, 60)
    return datetime.time(hour, minute, second)


def _combine_quantities(
    left: Quantity, right: Quantity, op: Callable[[float, float], float]
) -> Quantity:
    if left.dimension != right.dimension:
        raise EvalError(f"Cannot combine {left.dimension} and {right.dimension}")
    return Quantity(op(left.magnitude, right.magnitude), left.dimension, left.unit)


def _add(left: Value, right: Value) -> Value:
    if isinstance(left, float) and isinstance(right, float):
        return left + right
    if isinstance(left, Quantity) and isinstance(right, Quantity):
        return _combine_quantities(left, right, lambda a, b: a + b)
    if isinstance(left, DateValue) and isinstance(right, Quantity):
        if right.dimension == "time":
            return DateValue(left.date + datetime.timedelta(seconds=right.magnitude))
    if isinstance(right, DateValue) and isinstance(left, Quantity):
        if left.dimension == "time":
            return DateValue(right.date + datetime.timedelta(seconds=left.magnitude))
    if isinstance(left, TimeValue) and isinstance(right, Quantity):
        if right.dimension == "time":
            return TimeValue(_time_from_seconds(_time_seconds(left.time) + right.magnitude))
    if isinstance(right, TimeValue) and isinstance(left, Quantity):
        if left.dimension == "time":
            return TimeValue(_time_from_seconds(_time_seconds(right.time) + left.magnitude))
    raise EvalError(f"Cannot add {_type_name(left)} and {_type_name(right)}")


def _subtract(left: Value, right: Value) -> Value:
    if isinstance(left, float) and isinstance(right, float):
        return left - right
    if isinstance(left, Quantity) and isinstance(right, Quantity):
        return _combine_quantities(left, right, lambda a, b: a - b)
    if isinstance(left, DateValue) and isinstance(right, Quantity):
        if right.dimension == "time":
            return DateValue(left.date - datetime.timedelta(seconds=right.magnitude))
    if isinstance(left, DateValue) and isinstance(right, DateValue):
        days = (left.date - right.date).days
        return Quantity(days * _DAY_SECONDS, "time", "days")
    if isinstance(left, TimeValue) and isinstance(right, Quantity):
        if right.dimension == "time":
            return TimeValue(_time_from_seconds(_time_seconds(left.time) - right.magnitude))
    if isinstance(left, TimeValue) and isinstance(right, TimeValue):
        seconds = _time_seconds(left.time) - _time_seconds(right.time)
        return Quantity(seconds, "time", _time_diff_unit(seconds))
    raise EvalError(f"Cannot subtract {_type_name(right)} from {_type_name(left)}")


def _multiply(left: Value, right: Value) -> Value:
    if isinstance(left, float) and isinstance(right, float):
        return left * right
    if isinstance(left, Quantity) and isinstance(right, float):
        return Quantity(left.magnitude * right, left.dimension, left.unit)
    if isinstance(left, float) and isinstance(right, Quantity):
        return Quantity(right.magnitude * left, right.dimension, right.unit)
    raise EvalError(f"Cannot multiply {_type_name(left)} and {_type_name(right)}")


def _divide(left: Value, right: Value) -> Value:
    if isinstance(left, float) and isinstance(right, float):
        if right == 0:
            raise EvalError("Division by zero")
        return left / right
    if isinstance(left, Quantity) and isinstance(right, float):
        if right == 0:
            raise EvalError("Division by zero")
        return Quantity(left.magnitude / right, left.dimension, left.unit)
    if isinstance(left, Quantity) and isinstance(right, Quantity):
        if right.magnitude == 0:
            raise EvalError("Division by zero")
        if left.dimension != right.dimension:
            raise EvalError(f"Cannot divide {left.dimension} by {right.dimension}")
        return left.magnitude / right.magnitude
    raise EvalError(f"Cannot divide {_type_name(left)} by {_type_name(right)}")


def _power(left: Value, right: Value) -> float:
    if not isinstance(left, float) or not isinstance(right, float):
        raise EvalError("Exponentiation requires plain numbers")
    try:
        result = left**right
    except (OverflowError, ValueError, ZeroDivisionError) as exc:
        raise EvalError(f"Invalid exponentiation: {exc}") from exc
    if isinstance(result, complex):
        # E.g. (-1) ** 0.5: Python's ** promotes negative-base fractional
        # powers to complex instead of raising; we have no complex display.
        raise EvalError("Exponentiation produced a complex result")
    return float(result)


def _eval_binop(node: BinOp, env: Environment) -> Value:
    """Evaluates a binary operation, applying percent-of-left-operand rules.

    ``A + N%`` and ``A - N%`` treat the percentage as "N percent of A" (e.g.
    ``40 - 20%`` is ``32``), so those two cases evaluate the left operand
    once and derive the percentage from it rather than evaluating the
    right-hand :class:`Percent` node generically.
    """
    if node.op in ("+", "-") and isinstance(node.right, Percent):
        left = eval_node(node.left, env)
        if not isinstance(left, float):
            raise EvalError("A percentage adjustment requires a plain number")
        fraction_value = eval_node(node.right.expr, env)
        if not isinstance(fraction_value, float):
            raise EvalError("A percentage must be a plain number")
        delta = left * (fraction_value / 100)
        return left + delta if node.op == "+" else left - delta

    left = eval_node(node.left, env)
    right = eval_node(node.right, env)

    if node.op == "+":
        return _add(left, right)
    if node.op == "-":
        return _subtract(left, right)
    if node.op == "*":
        return _multiply(left, right)
    if node.op == "/":
        return _divide(left, right)
    if node.op == "^":
        return _power(left, right)

    raise EvalError(f"Unknown operator: {node.op}")


def evaluate_line(line: str, env: Environment) -> Value | None:
    """Evaluates a single line, updating ``env`` with any assignment or label.

    Args:
        line: A single line of ``.calc`` source.
        env: The environment to evaluate against and, for assignment or
            labeled lines, update in place.

    Returns:
        The line's result, or ``None`` if the line is blank or comment-only.

    Raises:
        SubCalcError: If the line cannot be tokenized, parsed, or evaluated
            (see :mod:`engine.errors`). Callers processing a whole buffer
            should catch this to treat the line as ordinary prose.
    """
    node = parse_line(line)
    return _eval_line_node(node, env)


def _eval_line_node(node: Node, env: Environment) -> Value | None:
    if isinstance(node, Labeled):
        value = _eval_line_node(node.expr, env)
        if value is not None:
            env.labels[node.name] = value
        return value
    if isinstance(node, Assign):
        value = eval_node(node.expr, env)
        env.variables[node.name] = value
        return value
    return eval_node(node, env)


@dataclass(frozen=True)
class LineOutcome:
    """The outcome of evaluating one buffer line.

    Attributes:
        value: The line's result, or ``None`` if it produced none.
        error: The failure message if the line looked like an attempted
            calculation but failed, otherwise ``None``.
    """

    value: Value | None
    error: str | None


def evaluate_buffer_with_env(lines: list[str]) -> tuple[list[LineOutcome], Environment]:
    """Evaluates every line of a buffer, also returning the final environment.

    Args:
        lines: The buffer's lines, in order, without trailing newlines.

    Returns:
        A ``(outcomes, environment)`` pair: one :class:`LineOutcome` per
        input line, and the :class:`Environment` after evaluating the last
        line -- useful for editor tooling that wants the buffer's current
        variables and labels (e.g. hover, autocomplete).
    """
    env = Environment()
    outcomes: list[LineOutcome] = []
    for line in lines:
        error = None
        try:
            value = evaluate_line(line, env)
        except SubCalcError as exc:
            value = None
            error = str(exc)
        outcomes.append(LineOutcome(value, error))
        env.line_results.append(value)
        if line.strip() == "":
            env.block_start = len(env.line_results)
    return outcomes, env


def evaluate_buffer_verbose(lines: list[str]) -> list[LineOutcome]:
    """Evaluates every line of a buffer, keeping each failure's error message.

    Args:
        lines: The buffer's lines, in order, without trailing newlines.

    Returns:
        One :class:`LineOutcome` per input line.
    """
    return evaluate_buffer_with_env(lines)[0]


def evaluate_buffer(lines: list[str]) -> list[Value | None]:
    """Evaluates every line of a buffer in order, top to bottom.

    Lines that are blank, prose, or fail to evaluate for any reason are
    silently treated as having no result -- this tolerance is what lets the
    engine coexist with free-form notes in the same file.

    Args:
        lines: The buffer's lines, in order, without trailing newlines.

    Returns:
        One result per input line, ``None`` where the line had no result.
    """
    return [outcome.value for outcome in evaluate_buffer_verbose(lines)]
