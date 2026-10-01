"""Markdown and self-contained HTML report renderers."""

from __future__ import annotations

import html
from datetime import datetime

from .models import FileReport

_SEVERITY_EMOJI = {"critical": "🔴", "warning": "🟡", "info": "🔵"}


def _summary(reports: list[FileReport]) -> dict[str, int]:
    tally = {"critical": 0, "warning": 0, "info": 0}
    for report in reports:
        for severity, count in report.counts().items():
            tally[severity] += count
    return tally


def render_markdown(reports: list[FileReport]) -> str:
    """Render a Markdown review report."""
    tally = _summary(reports)
    lines: list[str] = [
        "# CodeSage Review Report",
        "",
        f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
        "## Summary",
        "",
        f"- Files analyzed: **{len(reports)}**",
        f"- 🔴 Critical: **{tally['critical']}**",
        f"- 🟡 Warnings: **{tally['warning']}**",
        f"- 🔵 Info: **{tally['info']}**",
        "",
    ]

    for report in reports:
        lines.append(f"## `{report.file}`")
        lines.append("")
        if report.error:
            lines.append(f"> ⚠️ {report.error}")
            lines.append("")
            continue
        lines.append(
            f"{report.line_count} lines · {len(report.functions)} functions · "
            f"total complexity {report.total_complexity}"
        )
        lines.append("")
        findings = report.sorted_findings()
        if not findings:
            lines.append("✅ No findings — clean!")
            lines.append("")
            continue
        lines.append("| Severity | Rule | Line | Message | Suggestion |")
        lines.append("| --- | --- | --- | --- | --- |")
        for f in findings:
            lines.append(
                f"| {_SEVERITY_EMOJI.get(f.severity, '')} {f.severity} "
                f"| `{f.rule_id}` | {f.line} | {f.message} | {f.suggestion} |"
            )
        lines.append("")
    return "\n".join(lines)


_HTML_CSS = """
body { font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
       max-width: 1000px; margin: 2rem auto; padding: 0 1.5rem; color: #24292f;
       background: #f6f8fa; }
h1, h2 { color: #1f2328; }
.card { background: #fff; border: 1px solid #d0d7de; border-radius: 8px;
        padding: 1rem 1.5rem; margin-bottom: 1.5rem; }
.badges span { display: inline-block; margin-right: .75rem; font-weight: 600;
                padding: .25rem .75rem; border-radius: 999px; font-size: .85rem; }
.critical { background: #ffebe9; color: #a40e26; }
.warning { background: #fff8c5; color: #7d4e00; }
.info { background: #ddf4ff; color: #0550ae; }
table { width: 100%; border-collapse: collapse; font-size: .9rem; }
th, td { text-align: left; padding: .5rem .6rem; border-bottom: 1px solid #d0d7de; }
th { background: #f6f8fa; }
.sev { font-weight: 700; white-space: nowrap; }
.clean { color: #1a7f37; font-weight: 600; }
code { background: #eaeef2; padding: .1rem .35rem; border-radius: 4px; }
.meta { color: #57606a; font-size: .9rem; }
"""


def render_html(reports: list[FileReport]) -> str:
    """Render a self-contained HTML review report (inline CSS, no assets)."""
    tally = _summary(reports)
    esc = html.escape

    parts: list[str] = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>CodeSage Review Report</title>",
        f"<style>{_HTML_CSS}</style></head><body>",
        "<h1>🔎 CodeSage Review Report</h1>",
        f"<p class='meta'>Generated {esc(datetime.now().strftime('%Y-%m-%d %H:%M'))} · "
        f"{len(reports)} file(s) analyzed</p>",
        "<div class='card badges'>",
        f"<span class='critical'>🔴 {tally['critical']} critical</span>",
        f"<span class='warning'>🟡 {tally['warning']} warnings</span>",
        f"<span class='info'>🔵 {tally['info']} info</span>",
        "</div>",
    ]

    for report in reports:
        parts.append("<div class='card'>")
        parts.append(f"<h2><code>{esc(report.file)}</code></h2>")
        if report.error:
            parts.append(f"<p>⚠️ {esc(report.error)}</p></div>")
            continue
        parts.append(
            f"<p class='meta'>{report.line_count} lines · {len(report.functions)} "
            f"functions · total complexity {report.total_complexity}</p>"
        )
        findings = report.sorted_findings()
        if not findings:
            parts.append("<p class='clean'>✅ No findings — clean!</p></div>")
            continue
        parts.append(
            "<table><tr><th>Severity</th><th>Rule</th><th>Line</th>"
            "<th>Message</th><th>Suggestion</th></tr>"
        )
        for f in findings:
            emoji = _SEVERITY_EMOJI.get(f.severity, "")
            parts.append(
                f"<tr><td class='sev {f.severity}'>{emoji} {f.severity}</td>"
                f"<td><code>{esc(f.rule_id)}</code></td><td>{f.line}</td>"
                f"<td>{esc(f.message)}</td><td>{esc(f.suggestion)}</td></tr>"
            )
        parts.append("</table></div>")

    parts.append(
        "<p class='meta'>Generated by "
        "<a href='https://github.com/872000/codesage'>CodeSage</a> — "
        "static-analysis code reviewer.</p></body></html>"
    )
    return "\n".join(parts)
