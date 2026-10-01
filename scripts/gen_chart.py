"""Generate assets/complexity_chart.png — bar chart of per-function
cyclomatic complexity for the bundled smelly sample (real analyzer output)."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
import sys

sys.path.insert(0, str(ROOT))

from codesage.analyzer import analyze_file  # noqa: E402

OUT = ROOT / "assets" / "complexity_chart.png"

report = analyze_file(ROOT / "samples" / "smelly.py")
funcs = sorted(report.functions, key=lambda m: m.complexity, reverse=True)
names = [m.name for m in funcs]
values = [m.complexity for m in funcs]
colors = [
    "#d1242f" if v >= 10 else "#d29922" if v >= 6 else "#1a7f37" for v in values
]

fig, ax = plt.subplots(figsize=(9, 4.6))
bars = ax.barh(names, values, color=colors, edgecolor="#1f2328", height=0.55)
ax.set_xlabel("Cyclomatic complexity")
ax.set_title("CodeSage — complexity per function (samples/smelly.py)", pad=30)
ax.set_xlim(0, max(values) + 2)
ax.axvline(6, color="#d29922", linestyle="--", linewidth=1, alpha=0.8)
ax.axvline(10, color="#d1242f", linestyle="--", linewidth=1, alpha=0.8)
ax.text(6.1, -0.6, "warning ≥ 6", color="#9a6700", fontsize=9)
ax.text(10.1, -0.6, "critical ≥ 10", color="#a40e26", fontsize=9)
for bar, value in zip(bars, values):
    ax.text(value + 0.15, bar.get_y() + bar.get_height() / 2, str(value),
            va="center", fontsize=10, fontweight="bold")
ax.invert_yaxis()
fig.tight_layout()
fig.savefig(OUT, dpi=150)
print(f"wrote {OUT}")
