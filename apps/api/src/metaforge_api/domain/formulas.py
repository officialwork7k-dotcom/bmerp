"""Safe formula evaluation for computed fields (e.g. `qty * unitPrice`,
`ROUND(balance, 2)`, `balance > 0`, `IF(qty > 10, price * 0.9, price)`).

Restricted-AST evaluator — no `eval()`, no attribute access, no arbitrary
calls. v2 adds comparisons/boolean logic/ternary (for conditional formulas
like an "is_overdue" flag) and a small whitelisted function set (for
rounding and clamping money fields) on top of v1's + - * /. Still pure
arithmetic/logic over the row's own fields — aggregate-over-children values
are computed separately (see repository.build_aggregate_update_sql) and
only enter a formula as an already-materialized field on the row, same as
any other field.
"""

from __future__ import annotations

import ast
import operator

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_ALLOWED_CMPOPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}
# Each takes already-evaluated numeric args, so no AST access of its own.
_ALLOWED_FUNCS = {
    "ROUND": lambda *args: round(args[0], int(args[1]) if len(args) > 1 else 0),
    "ABS": lambda *args: abs(args[0]),
    "MIN": lambda *args: min(args),
    "MAX": lambda *args: max(args),
}


class FormulaError(ValueError):
    pass


def evaluate_formula(expression: str, values: dict[str, object]) -> float | bool:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"invalid formula syntax: {expression!r}") from exc
    return _eval_node(tree.body, values)


def _eval_node(node: ast.AST, values: dict[str, object]) -> float | bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name):
        raw = values.get(node.id, 0) or 0
        try:
            return float(raw)
        except (TypeError, ValueError):
            raise FormulaError(f"field {node.id!r} is not numeric") from None
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left = _eval_node(node.left, values)
        right = _eval_node(node.right, values)
        if isinstance(node.op, ast.Div) and right == 0:
            return 0.0
        return _ALLOWED_BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        return _ALLOWED_UNARYOPS[type(node.op)](_eval_node(node.operand, values))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _truthy(_eval_node(node.operand, values))
    if isinstance(node, ast.Compare):
        # `a < b < c` chains: every pairwise comparison must hold, same as
        # Python's own chained-comparison semantics.
        left = _eval_node(node.left, values)
        for op, comparator in zip(node.ops, node.comparators):
            if type(op) not in _ALLOWED_CMPOPS:
                raise FormulaError(f"unsupported comparison: {ast.dump(op)}")
            right = _eval_node(comparator, values)
            if not _ALLOWED_CMPOPS[type(op)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.BoolOp):
        results = [_truthy(_eval_node(v, values)) for v in node.values]
        return all(results) if isinstance(node.op, ast.And) else any(results)
    if isinstance(node, ast.IfExp):
        # Python ternary: `<then> if <cond> else <else>` — the natural
        # spelling for a conditional formula ("IF" is expressed this way
        # rather than as a pseudo-function, since ast.parse already gives
        # us a real ternary node for free).
        test = _truthy(_eval_node(node.test, values))
        return _eval_node(node.body if test else node.orelse, values)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_FUNCS:
        if node.keywords:
            raise FormulaError(f"keyword arguments are not supported: {node.func.id}")
        args = [_eval_node(a, values) for a in node.args]
        return _ALLOWED_FUNCS[node.func.id](*args)
    raise FormulaError(f"unsupported expression element: {ast.dump(node)}")


def _truthy(value: float | bool) -> bool:
    return bool(value)
