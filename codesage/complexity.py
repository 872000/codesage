"""Cyclomatic complexity and structural metrics computed from the AST.

Complexity starts at 1 per function and each decision point adds 1:
``if``/``elif``, ``for``, ``while``, ``except`` handlers, ``assert``,
ternary ``if`` expressions, boolean ``and``/``or`` operators (each extra
operand), comprehensions, and ``match``/``case`` clauses.
"""

from __future__ import annotations

import ast

from .models import FunctionMetrics

# Decision-point node types that each add 1 to cyclomatic complexity.
_DECISION_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.ExceptHandler,
    ast.Assert,
    ast.IfExp,
)


class ComplexityVisitor(ast.NodeVisitor):
    """Walk one function body, counting decision points and nesting depth."""

    def __init__(self) -> None:
        self.complexity = 1  # every function starts with a base of 1
        self.max_nesting = 0
        self._nesting = 0

    # -- decision points -------------------------------------------------
    def _count(self) -> None:
        self.complexity += 1

    def visit_If(self, node: ast.If) -> None:
        self._count()
        self._nest(node)

    def visit_For(self, node: ast.For) -> None:
        self._count()
        self._nest(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._count()
        self._nest(node)

    def visit_While(self, node: ast.While) -> None:
        self._count()
        self._nest(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._count()
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self._count()
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self._count()
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # ``a and b and c`` adds (3 - 1) = 2 decision points.
        self.complexity += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self._count()  # each ``for`` in a comprehension
        self.complexity += len(node.ifs)  # each ``if`` filter in a comprehension
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        self._count()
        self.generic_visit(node)

    def visit_match_case(self, node: ast.match_case) -> None:
        self._count()  # each ``case`` clause is a branch
        self.generic_visit(node)

    # -- nesting ---------------------------------------------------------
    def _nest(self, node: ast.AST) -> None:
        """Track nesting depth for block-structured decision nodes."""
        self._nesting += 1
        self.max_nesting = max(self.max_nesting, self._nesting)
        self.generic_visit(node)
        self._nesting -= 1

    # Do not descend into nested function/class definitions: they are
    # analyzed separately as their own units.
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return


def analyze_function(node: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: list[str]) -> FunctionMetrics:
    """Compute metrics for a single function definition node."""
    visitor = ComplexityVisitor()
    for stmt in node.body:
        visitor.visit(stmt)

    start = node.lineno
    end = node.end_lineno or node.lineno
    # Count non-blank lines in the function's span for "long function" checks.
    line_count = sum(1 for ln in source_lines[start - 1 : end] if ln.strip())

    args = node.args
    param_count = (
        len(args.posonlyargs)
        + len(args.args)
        + len(args.kwonlyargs)
        + (1 if args.vararg else 0)
        + (1 if args.kwarg else 0)
    )

    return FunctionMetrics(
        name=node.name,
        line=start,
        end_line=end,
        complexity=visitor.complexity,
        line_count=line_count,
        max_nesting=visitor.max_nesting,
        param_count=param_count,
    )


def iter_functions(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Yield all function definitions in a module (including nested ones)."""
    return [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
