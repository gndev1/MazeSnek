
from __future__ import annotations

import ast
import operator as op
import re
from typing import Any


_ALLOWED_BIN_OPS: dict[type[Any], Any] = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.FloorDiv: op.floordiv,
}

_ALLOWED_UNARY_OPS: dict[type[Any], Any] = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}


def _php_int_div(left: int, right: int) -> int:
    if right == 0:
        raise ValueError("Division by zero")

    quotient = abs(left) // abs(right)
    if (left < 0) ^ (right < 0):
        return -quotient
    return quotient


def _php_mod(left: int, right: int) -> int:
    if right == 0:
        raise ValueError("Modulo by zero")
    return left - _php_int_div(left, right) * right


def _normalize_text(expr: str) -> str:
    expr = expr.strip()
    expr = expr.replace("^", "**")
    expr = expr.replace("−", "-").replace("–", "-").replace("—", "-")
    expr = re.sub(r"\s+", " ", expr)
    return expr


def _eval_ast(node: ast.AST, variables: dict[str, int]) -> int:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, int):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value!r}")

    if isinstance(node, ast.Num):
        if isinstance(node.n, int):
            return node.n
        raise ValueError(f"Unsupported number: {node.n!r}")

    if isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        raise ValueError(f"Unknown variable: {node.id}")

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id != "abs":
            raise ValueError("Only abs() calls are supported")
        if len(node.args) != 1:
            raise ValueError("abs() requires exactly one argument")
        return abs(_eval_ast(node.args[0], variables))

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BIN_OPS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")

        left = _eval_ast(node.left, variables)
        right = _eval_ast(node.right, variables)

        if op_type is ast.Add:
            return left + right
        if op_type is ast.Sub:
            return left - right
        if op_type is ast.Mult:
            return left * right
        if op_type is ast.Mod:
            return _php_mod(left, right)
        if op_type is ast.Pow:
            if right < 0:
                raise ValueError("Negative exponent not supported")
            return left ** right
        if op_type is ast.FloorDiv:
            return _php_int_div(left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARY_OPS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")

        operand = _eval_ast(node.operand, variables)
        if op_type is ast.UAdd:
            return operand
        if op_type is ast.USub:
            return -operand

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def _safe_eval_int(expr: str, variables: dict[str, int] | None = None) -> int:
    variables = variables or {}
    normalized = _normalize_text(expr)
    if not normalized:
        raise ValueError("Expression text was empty")

    allowed = r"[A-Za-z0-9_\+\-\*\/%\(\)\s,]+"
    if not re.fullmatch(allowed, normalized):
        raise ValueError(f"Expression contains unsupported characters: {normalized!r}")

    tree = ast.parse(normalized, mode="eval")
    return _eval_ast(tree.body, variables)


def _extract_variable_definitions(text: str) -> tuple[dict[str, int], str]:
    variables: dict[str, int] = {}

    let_pattern = re.compile(
        r"Let\s+([A-Z])\s*=\s*(.+?)\.",
        flags=re.IGNORECASE | re.DOTALL,
    )

    consumed_until = 0
    for match in let_pattern.finditer(text):
        name = match.group(1).upper()
        expr = match.group(2).strip()
        variables[name] = _safe_eval_int(expr, variables)
        consumed_until = match.end()

    remaining = text[consumed_until:].strip() if consumed_until else text.strip()
    return variables, remaining


def _solve_old_clause_format(text: str, variables: dict[str, int]) -> str | None:
    clauses = re.findall(
        r"Clause\s+\d+:\s*multiply\s+(.+?)\s+by\s+(-?\d+)\.",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not clauses:
        return None

    total = 0
    for expr, multiplier_text in clauses:
        total += _safe_eval_int(expr, variables) * int(multiplier_text)

    final_adjustment = re.search(
        r"Final adjustment:\s*(add|subtract)\s+(-?\d+)\.",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if final_adjustment:
        verb, amount_text = final_adjustment.groups()
        amount = int(amount_text)
        if verb.lower() == "add":
            total += amount
        else:
            total -= amount

    return str(total)


def _solve_structured_parts(text: str, variables: dict[str, int]) -> str | None:
    if "Part " not in text:
        return None

    part_pattern = re.compile(
        r"Part\s+(\d+):\s*(.*?)(?=(?:Part\s+\d+:)|(?:Respond with)|\Z)",
        flags=re.IGNORECASE | re.DOTALL,
    )

    clause_pattern = re.compile(
        r"Clause\s+\d+:\s*take\s+(.+?)\s*\*\s*(-?\d+)\s*-\s*(-?\d+)\.",
        flags=re.IGNORECASE | re.DOTALL,
    )

    final_adjustment_pattern = re.compile(
        r"Final adjustment:\s*add\s+(-?\d+)\.",
        flags=re.IGNORECASE | re.DOTALL,
    )

    part_values: list[int] = []

    for part_match in part_pattern.finditer(text):
        part_number = int(part_match.group(1))
        part_body = part_match.group(2)

        total = 0
        clause_count = 0

        for clause_match in clause_pattern.finditer(part_body):
            clause_count += 1
            expr = clause_match.group(1).strip()
            weight = int(clause_match.group(2))
            modifier = int(clause_match.group(3))

            base_value = _safe_eval_int(expr, variables)
            clause_value = (base_value * weight) - modifier
            total += clause_value

        if clause_count == 0:
            raise ValueError(f"No recognizable clauses found in Part {part_number}")

        final_adjustment = final_adjustment_pattern.search(part_body)
        if final_adjustment:
            total += int(final_adjustment.group(1))

        part_values.append(total)

    if not part_values:
        return None

    if len(part_values) == 1:
        return str(part_values[0])

    return ",".join(str(value) for value in part_values)


def solve_equation(equation: str) -> str:
    equation = equation.strip()
    if not equation:
        raise ValueError("Equation text was empty")

    variables, remaining = _extract_variable_definitions(equation)

    solved = _solve_structured_parts(remaining, variables)
    if solved is not None:
        return solved

    solved = _solve_old_clause_format(remaining, variables)
    if solved is not None:
        return solved

    return str(_safe_eval_int(remaining, variables))
