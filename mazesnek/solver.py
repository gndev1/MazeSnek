from __future__ import annotations

import ast
import operator as op
import re
from typing import Any

_ALLOWED_BINOPS: dict[type[Any], Any] = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

_ALLOWED_UNARYOPS: dict[type[Any], Any] = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("Unsupported constant in expression")

    if isinstance(node, ast.Num):
        return float(node.n)

    if isinstance(node, ast.BinOp):
        fn = _ALLOWED_BINOPS.get(type(node.op))
        if fn is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return float(fn(_eval(node.left), _eval(node.right)))

    if isinstance(node, ast.UnaryOp):
        fn = _ALLOWED_UNARYOPS.get(type(node.op))
        if fn is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return float(fn(_eval(node.operand)))

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def clean_expression(expr: str) -> str:
    cleaned = expr.strip()
    cleaned = cleaned.replace("^", "**")
    cleaned = cleaned.replace("×", "*")
    cleaned = cleaned.replace("÷", "/")
    cleaned = re.sub(r"[^0-9\+\-\*\/\%\(\)\.\s]", "", cleaned)
    return cleaned


def solve_expression(expr: str) -> str:
    cleaned = clean_expression(expr)
    if not cleaned:
        raise ValueError(f"Expression became empty after cleaning: {expr!r}")
    tree = ast.parse(cleaned, mode="eval")
    value = _eval(tree.body)
    if value.is_integer():
        return str(int(value))
    return str(value)
