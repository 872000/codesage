"""CodeSage test suite.

Run with:  python -m pytest   (or: python3 -m pytest)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from codesage.analyzer import analyze_file, analyze_source
from codesage.complexity import analyze_function
from codesage.reporter import render_html, render_markdown
from codesage.smells import Config, find_duplicate_blocks

SAMPLES = Path(__file__).resolve().parent.parent / "samples"

# A function whose cyclomatic complexity is exactly 3:
# base 1 + one `if` + one `elif`.
KNOWN_COMPLEXITY_SRC = '''
def classify_sign(x):
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    return "zero"
'''

# Base 1 + if (1) + for (1) + if (1) + and (1) + while (1) = 6.
BRANCHY_SRC = '''
def classify(n):
    if n < 0:
        return "neg"
    total = 0
    for i in range(n):
        if i % 2 == 0 and i > 3:
            total += i
    while total > 10:
        total -= 1
    return total
'''


def _metrics_for(src: str):
    tree = ast.parse(src)
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    return analyze_function(node, src.splitlines())


# ---------------------------------------------------------------------------
# Complexity
# ---------------------------------------------------------------------------

def test_complexity_of_known_function():
    """A simple if/elif chain must have complexity exactly 3."""
    assert _metrics_for(KNOWN_COMPLEXITY_SRC).complexity == 3


def test_complexity_counts_boolops_and_loops():
    """Loops, branches and boolean operators each add decision points."""
    assert _metrics_for(BRANCHY_SRC).complexity == 6


def test_complexity_of_plain_function_is_one():
    metrics = _metrics_for("def f():\n    return 1\n")
    assert metrics.complexity == 1


# ---------------------------------------------------------------------------
# Smell detectors
# ---------------------------------------------------------------------------

def test_long_function_detector_fires():
    body = "\n".join(f"    step_{i} = {i}" for i in range(60))
    report = analyze_source(f"def marathon():\n{body}\n    return 0\n", "t.py")
    rules = [f.rule_id for f in report.findings]
    assert "long-function" in rules
    finding = next(f for f in report.findings if f.rule_id == "long-function")
    assert finding.severity in ("warning", "critical")
    assert "marathon" in finding.message


def test_long_function_detector_silent_on_short_function():
    report = analyze_source("def tiny():\n    return 1\n", "t.py")
    assert not [f for f in report.findings if f.rule_id == "long-function"]


def test_duplicate_block_detector_finds_planted_duplicate():
    src = """
def first(values):
    total = 0
    count = 0
    for v in values:
        total = total + v
        count = count + 1
    average = total // max(count, 1)
    print("done")
    return total, average


def second(values):
    total = 0
    count = 0
    for v in values:
        total = total + v
        count = count + 1
    average = total // max(count, 1)
    print("done")
    return total, average
"""
    report = analyze_source(src, "t.py", Config(duplicate_window=5))
    dupes = [f for f in report.findings if f.rule_id == "duplicate-block"]
    assert dupes, "expected the planted duplicate block to be detected"
    assert any("second" in f.message or "first" in f.message for f in dupes)


def test_duplicate_block_normalization_ignores_renames():
    """Renamed variables must still match after normalization."""
    src = """
def alpha(items):
    running = 0
    n = 0
    for it in items:
        running = running + it
        n = n + 1
    mean = running // max(n, 1)
    print("done")
    return running, mean


def beta(data):
    acc = 0
    k = 0
    for d in data:
        acc = acc + d
        k = k + 1
    avg = acc // max(k, 1)
    print("done")
    return acc, avg
"""
    report = analyze_source(src, "t.py", Config(duplicate_window=5))
    assert [f for f in report.findings if f.rule_id == "duplicate-block"]


def test_duplicate_block_detector_silent_on_unique_code():
    src = """
def one(a):
    return a + 1


def two(b):
    result = b * 2
    return result - 1
"""
    report = analyze_source(src, "t.py")
    assert not [f for f in report.findings if f.rule_id == "duplicate-block"]


def test_deep_nesting_detector_fires():
    src = (
        "def deep(data):\n"
        "    for a in data:\n"
        "        if a:\n"
        "            for b in a:\n"
        "                if b:\n"
        "                    while b > 0:\n"
        "                        b = b - 1\n"
        "    return data\n"
    )
    report = analyze_source(src, "t.py", Config(max_nesting=3))
    assert [f for f in report.findings if f.rule_id == "deep-nesting"]


def test_too_many_params_detector_fires():
    report = analyze_source("def f(a, b, c, d, e, f):\n    return a\n", "t.py")
    assert [f for f in report.findings if f.rule_id == "too-many-params"]


def test_magic_number_detector_fires_but_ignores_named_constants():
    src = "LIMIT = 99\n\n\ndef f(x):\n    return x * 7\n"
    report = analyze_source(src, "t.py")
    magic = [f for f in report.findings if f.rule_id == "magic-number"]
    literals = [f.message for f in magic]
    assert any("7" in m for m in literals)
    assert not any("99" in m for m in literals), "named constant must not be flagged"


def test_high_complexity_is_critical_above_threshold():
    branches = "\n".join(f"    if x == {i}:\n        y = {i}" for i in range(12))
    report = analyze_source(f"def messy(x):\n    y = 0\n{branches}\n    return y\n", "t.py")
    crit = [f for f in report.findings
            if f.rule_id == "high-complexity" and f.severity == "critical"]
    assert crit


def test_syntax_error_is_reported_not_raised():
    report = analyze_source("def broken(:\n", "t.py")
    assert report.error is not None


# ---------------------------------------------------------------------------
# Sample files
# ---------------------------------------------------------------------------

def test_clean_sample_has_zero_criticals():
    report = analyze_file(SAMPLES / "clean.py")
    assert report.error is None
    assert report.counts()["critical"] == 0
    assert report.findings == []


def test_smelly_sample_triggers_every_major_rule():
    report = analyze_file(SAMPLES / "smelly.py")
    rules = {f.rule_id for f in report.findings}
    for expected in ("high-complexity", "long-function", "deep-nesting",
                     "duplicate-block", "magic-number", "too-many-params"):
        assert expected in rules, f"rule {expected} did not fire on smelly.py"
    assert report.counts()["critical"] >= 1


# ---------------------------------------------------------------------------
# Reporters
# ---------------------------------------------------------------------------

def test_markdown_report_contains_findings_table():
    report = analyze_file(SAMPLES / "smelly.py")
    md = render_markdown([report])
    assert "# CodeSage Review Report" in md
    assert "high-complexity" in md
    assert "Critical" in md


def test_html_report_is_self_contained():
    report = analyze_file(SAMPLES / "smelly.py")
    html_doc = render_html([report])
    assert "<!DOCTYPE html>" in html_doc
    assert "<style>" in html_doc
    assert "duplicate-block" in html_doc


def test_findings_are_severity_sorted():
    report = analyze_file(SAMPLES / "smelly.py")
    order = {"critical": 0, "warning": 1, "info": 2}
    severities = [order[f.severity] for f in report.sorted_findings()]
    assert severities == sorted(severities)
