"""Core data structures for CodeSage findings and reports."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Finding:
    """A single review finding."""

    rule_id: str
    severity: str  # "info" | "warning" | "critical"
    file: str
    line: int
    message: str
    suggestion: str

    def sort_key(self) -> tuple:
        order = {"critical": 0, "warning": 1, "info": 2}
        return (order.get(self.severity, 3), self.file, self.line, self.rule_id)


@dataclass
class FunctionMetrics:
    """Metrics computed for a single function."""

    name: str
    line: int
    end_line: int
    complexity: int
    line_count: int
    max_nesting: int
    param_count: int


@dataclass
class FileReport:
    """Full report for one analyzed file."""

    file: str
    line_count: int
    functions: list[FunctionMetrics] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    total_complexity: int = 0
    error: str | None = None

    def sorted_findings(self) -> list[Finding]:
        return sorted(self.findings, key=lambda f: f.sort_key())

    def counts(self) -> dict[str, int]:
        tally = {"critical": 0, "warning": 0, "info": 0}
        for finding in self.findings:
            if finding.severity in tally:
                tally[finding.severity] += 1
        return tally
