"""Generate assets/cli_demo.png — a programmatic "screenshot" of the
CodeSage CLI reviewing the bundled samples, drawn with PIL (no browser)."""

from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont

from codesage.analyzer import analyze_path  # noqa: E402

OUT = ROOT / "assets" / "cli_demo.png"

W, H = 1180, 660
BG = (13, 17, 23)          # GitHub dark
FG = (230, 237, 243)
DIM = (139, 148, 158)
GREEN = (63, 185, 80)
RED = (248, 81, 73)
YELLOW = (210, 153, 34)
BLUE = (88, 166, 255)
CYAN = (57, 211, 199)

lines: list[tuple[str, tuple[int, int, int]]] = [
    ("$ python -m codesage review samples/", FG),
    ("", FG),
    ("================ samples/clean.py ================", DIM),
    ("  25 lines · 3 functions · total complexity 5", FG),
    ("  [OK] No findings — clean!", GREEN),
    ("", FG),
    ("================ samples/smelly.py ================", DIM),
    ("  122 lines · 5 functions · total complexity 31", FG),
    ("  [CRITICAL] samples/smelly.py:11 (high-complexity)", RED),
    ("      Function 'calculate_discount' has cyclomatic complexity 11.", FG),
    ("      hint: Split it into smaller functions, one per branch of logic.", DIM),
    ("  [CRITICAL] samples/smelly.py:35 (high-complexity)", RED),
    ("      Function 'process_orders' has cyclomatic complexity 12.", FG),
    ("  [WARNING ] samples/smelly.py:11 (too-many-params)", YELLOW),
    ("      Function 'calculate_discount' takes 7 parameters (limit 5).", FG),
    ("  [WARNING ] samples/smelly.py:35 (long-function)", YELLOW),
    ("      Function 'process_orders' is 47 lines long (limit 40).", FG),
    ("  [WARNING ] samples/smelly.py:84 (deep-nesting)", YELLOW),
    ("      Function 'nested_check' nests 5 levels deep (limit 4).", FG),
    ("  [WARNING ] samples/smelly.py:110 (duplicate-block)", YELLOW),
    ("      Block of 5 statements duplicates code at line 98.", FG),
    ("  [INFO    ] samples/smelly.py:15 (magic-number)", BLUE),
    ("      Magic number 0.05 used directly in code.", FG),
    ("      ... and 16 more info findings", DIM),
    ("", FG),
    ("2 file(s): 2 critical · 5 warnings · 17 info", CYAN),
]

# Real metrics for the header line are pulled from the analyzer at build time.
from codesage.analyzer import analyze_path  # noqa: E402

reports = analyze_path(ROOT / "samples")
smelly = next(r for r in reports if r.file.endswith("smelly.py"))
lines[7] = (
    f"  {smelly.line_count} lines · {len(smelly.functions)} functions "
    f"· total complexity {smelly.total_complexity}",
    FG,
)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

# Window chrome.
draw.rounded_rectangle([0, 0, W, H], radius=18, fill=BG,
                       outline=(48, 54, 61), width=2)
for i, color in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
    x = 28 + i * 26
    draw.ellipse([x, 18, x + 14, 32], fill=color)
draw.text((110, 16), "parth — codesage — zsh", font=load_font(16), fill=DIM)

font = load_font(19)
y = 62
for text, color in lines:
    draw.text((28, y), text, font=font, fill=color)
    y += 26

img.save(OUT)
print(f"wrote {OUT}")
