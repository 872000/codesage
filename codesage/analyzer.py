"""Orchestrates analysis: parse files, compute metrics, run smell detectors."""

from __future__ import annotations

import ast
from pathlib import Path

from .complexity import analyze_function, iter_functions
from .models import FileReport
from .smells import (
    Config,
    check_complexity,
    check_deep_nesting,
    check_long_file,
    check_long_function,
    check_magic_numbers,
    check_too_many_params,
    find_duplicate_blocks,
)


def analyze_source(source: str, file: str, cfg: Config | None = None) -> FileReport:
    """Analyze a Python source string and return a FileReport."""
    cfg = cfg or Config()
    lines = source.splitlines()
    report = FileReport(file=file, line_count=len(lines))

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        report.error = f"SyntaxError: {exc}"
        return report

    func_nodes = iter_functions(tree)
    seen_magic_lines: set[int] = set()

    for node in func_nodes:
        metrics = analyze_function(node, lines)
        report.functions.append(metrics)
        report.total_complexity += metrics.complexity
        report.findings.extend(check_complexity(metrics, file, cfg))
        report.findings.extend(check_long_function(metrics, file, cfg))
        report.findings.extend(check_deep_nesting(metrics, file, cfg))
        report.findings.extend(check_too_many_params(metrics, file, cfg))

    report.findings.extend(check_magic_numbers(tree, file, seen_magic_lines))
    report.findings.extend(find_duplicate_blocks(func_nodes, file, cfg.duplicate_window))
    report.findings.extend(check_long_file(len(lines), file, cfg))

    report.functions.sort(key=lambda m: m.complexity, reverse=True)
    return report


def analyze_file(path: str | Path, cfg: Config | None = None) -> FileReport:
    """Analyze a single Python file."""
    path = Path(path)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        report = FileReport(file=str(path), line_count=0)
        report.error = f"Could not read file: {exc}"
        return report
    return analyze_source(source, str(path), cfg)


def analyze_path(target: str | Path, cfg: Config | None = None) -> list[FileReport]:
    """Recursively analyze every ``*.py`` file under ``target``."""
    target = Path(target)
    cfg = cfg or Config()
    if target.is_file():
        files = [target]
    else:
        files = sorted(p for p in target.rglob("*.py") if "__pycache__" not in p.parts)
    return [analyze_file(p, cfg) for p in files]
