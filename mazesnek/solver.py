from __future__ import annotations

import ast
import operator as op
import re
from fractions import Fraction
from typing import Any


_ALLOWED_BIN_OPS: dict[type[Any], Any] = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

_ALLOWED_UNARY_OPS: dict[type[Any], Any] = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}


def _eval_ast(node: ast.AST) -> Fraction:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, int):
            return Fraction(node.value)
        if isinstance(node.value, float):
            return Fraction(str(node.value))
        raise ValueError(f"Unsupported constant: {node.value!r}")

    if isinstance(node, ast.Num):
        if isinstance(node.n, int):
            return Fraction(node.n)
        if isinstance(node.n, float):
            return Fraction(str(node.n))
        raise ValueError(f"Unsupported number: {node.n!r}")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BIN_OPS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")

        left = _eval_ast(node.left)
        right = _eval_ast(node.right)

        if op_type is ast.Add:
            return left + right
        if op_type is ast.Sub:
            return left - right
        if op_type is ast.Mult:
            return left * right
        if op_type is ast.Div:
            return left / right
        if op_type is ast.FloorDiv:
            return Fraction(left.numerator // left.denominator // (right.numerator // right.denominator))
        if op_type is ast.Mod:
            if left.denominator != 1 or right.denominator != 1:
                raise ValueError("Modulo requires integer operands")
            return Fraction(left.numerator % right.numerator)
        if op_type is ast.Pow:
            if right.denominator != 1:
                raise ValueError("Exponent must be an integer")
            exponent = right.numerator
            if exponent >= 0:
                return left ** exponent
            return Fraction(1, 1) / (left ** abs(exponent))

        raise ValueError(f"Unsupported operator: {op_type.__name__}")

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARY_OPS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")

        operand = _eval_ast(node.operand)

        if op_type is ast.UAdd:
            return operand
        if op_type is ast.USub:
            return -operand

        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def _safe_eval_math(expr: str) -> Fraction:
    cleaned = expr.replace("^", "**")
    cleaned = re.sub(r"[^0-9\+\-\*\/\%\(\)\.\s]", "", cleaned)
    cleaned = " ".join(cleaned.split())

    if not cleaned:
        raise ValueError("Expression became empty after cleaning")

    tree = ast.parse(cleaned, mode="eval")
    return _eval_ast(tree.body)


def _solve_clause_style_equation(text: str) -> Fraction | None:
    if "Clause" not in text and "Final adjustment" not in text:
        return None

    total = Fraction(0, 1)

    clauses = re.findall(
        r"Clause\s+\d+:\s*multiply\s+(.*?)\s+by\s+(-?\d+)\.",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not clauses:
        return None

    for expr, multiplier_text in clauses:
        expr_value = _safe_eval_math(expr)
        multiplier = Fraction(int(multiplier_text))
        total += expr_value * multiplier

    final_adjustment = re.search(
        r"Final adjustment:\s*(add|subtract)\s+(-?\d+)\.",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if final_adjustment:
        verb, amount_text = final_adjustment.groups()
        amount = Fraction(int(amount_text))
        if verb.lower() == "add":
            total += amount
        else:
            total -= amount

    return total


def _fraction_to_output(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return str(float(value))


def solve_equation(equation: str) -> str:
    equation = equation.strip()

    clause_value = _solve_clause_style_equation(equation)
    if clause_value is not None:
        return _fraction_to_output(clause_value)

    basic_value = _safe_eval_math(equation)
    return _fraction_to_output(basic_value)