"""Smell detectors that turn metrics into severity-ranked findings."""

from __future__ import annotations

import ast
import hashlib

from .models import Finding, FunctionMetrics


class Config:
    """Tunable thresholds for every rule."""

    def __init__(
        self,
        max_function_lines: int = 40,
        critical_function_lines: int = 80,
        max_nesting: int = 4,
        critical_nesting: int = 6,
        max_params: int = 5,
        max_complexity_warn: int = 6,
        max_complexity_critical: int = 10,
        max_file_lines: int = 500,
        critical_file_lines: int = 1000,
        duplicate_window: int = 5,
    ) -> None:
        self.max_function_lines = max_function_lines
        self.critical_function_lines = critical_function_lines
        self.max_nesting = max_nesting
        self.critical_nesting = critical_nesting
        self.max_params = max_params
        self.max_complexity_warn = max_complexity_warn
        self.max_complexity_critical = max_complexity_critical
        self.max_file_lines = max_file_lines
        self.critical_file_lines = critical_file_lines
        self.duplicate_window = duplicate_window


# ---------------------------------------------------------------------------
# Function-level rules
# ---------------------------------------------------------------------------

def check_complexity(metrics: FunctionMetrics, file: str, cfg: Config) -> list[Finding]:
    findings: list[Finding] = []
    c = metrics.complexity
    if c >= cfg.max_complexity_critical:
        findings.append(
            Finding(
                rule_id="high-complexity",
                severity="critical",
                file=file,
                line=metrics.line,
                message=f"Function '{metrics.name}' has cyclomatic complexity {c} "
                f"(threshold {cfg.max_complexity_critical}).",
                suggestion="Split it into smaller functions, one per branch of logic.",
            )
        )
    elif c >= cfg.max_complexity_warn:
        findings.append(
            Finding(
                rule_id="high-complexity",
                severity="warning",
                file=file,
                line=metrics.line,
                message=f"Function '{metrics.name}' has cyclomatic complexity {c} "
                f"(warning at {cfg.max_complexity_warn}).",
                suggestion="Consider extracting helper functions to reduce branching.",
            )
        )
    return findings


def check_long_function(metrics: FunctionMetrics, file: str, cfg: Config) -> list[Finding]:
    findings: list[Finding] = []
    n = metrics.line_count
    if n > cfg.critical_function_lines:
        severity = "critical"
    elif n > cfg.max_function_lines:
        severity = "warning"
    else:
        return findings
    findings.append(
        Finding(
            rule_id="long-function",
            severity=severity,
            file=file,
            line=metrics.line,
            message=f"Function '{metrics.name}' is {n} lines long (limit {cfg.max_function_lines}).",
            suggestion="Break it into smaller, single-purpose functions.",
        )
    )
    return findings


def check_deep_nesting(metrics: FunctionMetrics, file: str, cfg: Config) -> list[Finding]:
    findings: list[Finding] = []
    d = metrics.max_nesting
    if d > cfg.critical_nesting:
        severity = "critical"
    elif d > cfg.max_nesting:
        severity = "warning"
    else:
        return findings
    findings.append(
        Finding(
            rule_id="deep-nesting",
            severity=severity,
            file=file,
            line=metrics.line,
            message=f"Function '{metrics.name}' nests {d} levels deep (limit {cfg.max_nesting}).",
            suggestion="Use early returns or guard clauses to flatten the nesting.",
        )
    )
    return findings


def check_too_many_params(metrics: FunctionMetrics, file: str, cfg: Config) -> list[Finding]:
    if metrics.param_count <= cfg.max_params:
        return []
    return [
        Finding(
            rule_id="too-many-params",
            severity="warning",
            file=file,
            line=metrics.line,
            message=f"Function '{metrics.name}' takes {metrics.param_count} parameters "
            f"(limit {cfg.max_params}).",
            suggestion="Group related parameters into a dataclass or config object.",
        )
    ]


# ---------------------------------------------------------------------------
# Magic numbers
# ---------------------------------------------------------------------------

# Numbers that are fine to appear literally (identity values, indices, steps).
_MAGIC_ALLOWLIST = {0, 1, -1, 2, 100}


class MagicNumberVisitor(ast.NodeVisitor):
    """Find numeric literals that are not bound to a named constant."""

    def __init__(self) -> None:
        self.hits: list[tuple[int, str]] = []  # (line, literal text)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            if node.value not in _MAGIC_ALLOWLIST:
                self.hits.append((node.lineno, repr(node.value)))
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # ``MAX_RETRIES = 5`` — naming the number makes it a real constant.
        if all(isinstance(t, ast.Name) and t.id.isupper() for t in node.targets):
            return
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.target.id.isupper():
            return
        self.generic_visit(node)


def check_magic_numbers(tree: ast.Module, file: str, seen_lines: set[int]) -> list[Finding]:
    visitor = MagicNumberVisitor()
    visitor.visit(tree)
    findings: list[Finding] = []
    for line, literal in visitor.hits:
        if line in seen_lines:
            continue
        seen_lines.add(line)
        findings.append(
            Finding(
                rule_id="magic-number",
                severity="info",
                file=file,
                line=line,
                message=f"Magic number {literal} used directly in code.",
                suggestion=f"Bind it to a named UPPER_CASE constant, e.g. LIMIT = {literal}.",
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Duplicate code blocks (clone detection via normalized hashing)
# ---------------------------------------------------------------------------

class _Normalizer(ast.NodeTransformer):
    """Replace identifiers and literals so structurally equal code hashes equal."""

    def visit_Name(self, node: ast.Name) -> ast.AST:
        node.id = "VAR"
        return self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        node.value = "CONST"
        return self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> ast.AST:
        node.arg = "ARG"
        return self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        node.attr = "ATTR"
        return self.generic_visit(node)


def _fingerprint(stmt: ast.stmt) -> str:
    normalized = _Normalizer().visit(ast.parse(ast.unparse(stmt)).body[0])
    dump = ast.dump(normalized, annotate_fields=False, include_attributes=False)
    return hashlib.sha256(dump.encode()).hexdigest()[:16]


def find_duplicate_blocks(
    func_nodes: list[ast.FunctionDef | ast.AsyncFunctionDef],
    file: str,
    window: int,
) -> list[Finding]:
    """Sliding-window clone detection over statement sequences.

    Each function body is scanned with a window of ``window`` consecutive
    statements; windows are normalized (names/literals abstracted away) and
    hashed. Identical hashes appearing at two or more locations are reported
    as duplicated blocks.
    """
    seen: dict[str, tuple[str, int]] = {}  # hash -> (function name, line)
    findings: list[Finding] = []
    reported_func_pairs: set[tuple[str, str]] = set()

    for func in func_nodes:
        body = func.body
        if len(body) < window:
            continue
        for i in range(len(body) - window + 1):
            chunk = body[i : i + window]
            key = hashlib.sha256(
                "|".join(_fingerprint(s) for s in chunk).encode()
            ).hexdigest()[:16]
            line = chunk[0].lineno
            if key in seen:
                other_func, other_line = seen[key]
                if other_func == func.name and abs(line - other_line) < window:
                    continue  # overlapping windows inside the same function
                # One finding per function pair keeps the report readable even
                # when several overlapping windows match.
                pair = tuple(sorted((func.name, other_func)))
                if pair in reported_func_pairs:
                    continue
                reported_func_pairs.add(pair)
                findings.append(
                    Finding(
                        rule_id="duplicate-block",
                        severity="warning",
                        file=file,
                        line=line,
                        message=f"Block of {window} statements duplicates code at "
                        f"line {other_line} (in '{other_func}').",
                        suggestion="Extract the repeated block into a shared helper function.",
                    )
                )
            else:
                seen[key] = (func.name, line)
    return findings


# ---------------------------------------------------------------------------
# File-level rules
# ---------------------------------------------------------------------------

def check_long_file(line_count: int, file: str, cfg: Config) -> list[Finding]:
    if line_count > cfg.critical_file_lines:
        severity = "critical"
    elif line_count > cfg.max_file_lines:
        severity = "warning"
    else:
        return []
    return [
        Finding(
            rule_id="long-file",
            severity=severity,
            file=file,
            line=1,
            message=f"File has {line_count} lines (limit {cfg.max_file_lines}).",
            suggestion="Split the module into smaller, focused modules.",
        )
    ]
