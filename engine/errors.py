"""Exception types shared across the calculation engine."""


class SubCalcError(Exception):
    """Base class for all errors raised by the calculation engine.

    Callers that walk a buffer line by line (see
    :func:`engine.evaluator.evaluate_buffer`) catch this base class to treat a
    failing line as ordinary prose rather than a broken calculation.
    """


class TokenizeError(SubCalcError):
    """Raised when a line contains a character the tokenizer cannot classify."""


class ParseError(SubCalcError):
    """Raised when a token stream does not match the expression grammar."""


class EvalError(SubCalcError):
    """Raised when a syntactically valid expression cannot be evaluated.

    Examples include references to unknown variables, references to lines
    that produced no result, and division by zero.
    """
