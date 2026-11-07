"""Parse SQL-like user commands and validate literal values."""

import re
import shlex

_CONDITION_PATTERN = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*(.*?)\s*$")


def parse_literal(value):
    """Convert a quoted string, integer, or boolean to Python data."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if re.fullmatch(r"[+-]?\d+", value):
        return int(value)
    raise ValueError(f"Некорректное значение: {value}. Попробуйте снова.")


def parse_condition(expression):
    """Parse one column=value condition into a mapping."""
    match = _CONDITION_PATTERN.fullmatch(expression)
    if match is None:
        raise ValueError(f"Некорректное значение: {expression}. Попробуйте снова.")
    return {match.group(1): parse_literal(match.group(2))}


def parse_values(expression):
    """Parse comma-separated values, retaining quoted commas."""
    expression = expression.strip()
    if not expression.startswith("(") or not expression.endswith(")"):
        raise ValueError(f"Некорректное значение: {expression}. Попробуйте снова.")
    content = expression[1:-1].strip()
    if not content:
        return []
    lexer = shlex.shlex(content, posix=False, punctuation_chars=",")
    lexer.whitespace_split = True
    lexer.whitespace = " "
    tokens = list(lexer)
    values = []
    expect_value = True
    for token in tokens:
        if expect_value:
            if token == ",":
                raise ValueError("Некорректное значение: пустое поле.")
            values.append(parse_literal(token))
        elif token != ",":
            raise ValueError(f"Некорректное значение: {token}.")
        expect_value = not expect_value
    if expect_value:
        raise ValueError("Некорректное значение: пустое поле.")
    return values


def split_command(user_input):
    """Split simple commands with shlex while preserving raw CRUD values."""
    return shlex.split(user_input)
