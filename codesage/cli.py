"""Command-line interface for CodeSage.

Usage:
    python -m codesage review <directory> [--format md|html|text] [--output FILE]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .analyzer import analyze_path
from .models import FileReport
from .reporter import render_html, render_markdown
from .smells import Config

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def _print_text_report(reports: list[FileReport]) -> None:
    for report in reports:
        print(f"\n{'=' * 72}\n{report.file}\n{'=' * 72}")
        if report.error:
            print(f"  ⚠️  {report.error}")
            continue
        print(
            f"  {report.line_count} lines · {len(report.functions)} functions "
            f"· total complexity {report.total_complexity}"
        )
        findings = report.sorted_findings()
        if not findings:
            print("  ✅ No findings — clean!")
            continue
        for f in findings:
            mark = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(f.severity, "•")
            print(f"  {mark} [{f.severity.upper():8}] {f.file}:{f.line} "
                  f"({f.rule_id}) — {f.message}")
            print(f"             💡 {f.suggestion}")


def cmd_review(args: argparse.Namespace) -> int:
    cfg = Config(
        max_function_lines=args.max_function_lines,
        max_nesting=args.max_nesting,
        max_params=args.max_params,
        max_complexity_warn=args.warn_complexity,
        max_complexity_critical=args.critical_complexity,
    )
    target = Path(args.target)
    if not target.exists():
        print(f"error: '{args.target}' does not exist", file=sys.stderr)
        return 2

    reports = analyze_path(target, cfg)
    criticals = sum(r.counts()["critical"] for r in reports)

    if args.format == "md":
        output = render_markdown(reports)
    elif args.format == "html":
        output = render_html(reports)
    else:
        output = ""
        _print_text_report(reports)

    if output and args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Report written to {args.output}")
    elif output:
        print(output)

    # Summary footer for the terminal.
    total = {"critical": 0, "warning": 0, "info": 0}
    for report in reports:
        for sev, count in report.counts().items():
            total[sev] += count
    print(
        f"\n📊 {len(reports)} file(s): "
        f"🔴 {total['critical']} critical · "
        f"🟡 {total['warning']} warnings · "
        f"🔵 {total['info']} info"
    )
    # Non-zero exit code when critical findings exist (CI-friendly).
    return 1 if criticals else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codesage",
        description="CodeSage — static-analysis code reviewer for Python.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="Review a file or directory of Python code.")
    review.add_argument("target", help="Python file or directory to analyze.")
    review.add_argument(
        "--format",
        choices=["text", "md", "html"],
        default="text",
        help="Output format (default: text).",
    )
    review.add_argument("--output", help="Write the md/html report to this file.")
    review.add_argument("--max-function-lines", type=int, default=40)
    review.add_argument("--max-nesting", type=int, default=4)
    review.add_argument("--max-params", type=int, default=5)
    review.add_argument("--warn-complexity", type=int, default=6)
    review.add_argument("--critical-complexity", type=int, default=10)
    review.set_defaults(func=cmd_review)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
