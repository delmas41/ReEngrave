#!/usr/bin/env python3
"""Native-resolution margin strips for named staves, stacked into one image.

The (a)-vs-(b) call — "is a label printed here at all?" — is a question about
ink on the page, and the only honest way to answer it is to look at the page at
the resolution the reader was given. This dumps the FULL left margin (from
x = 0, no `MARGIN_SPACINGS` cap) beside each named staff, at 600 dpi, so a
missing label cannot be an artifact of the crop or of a downscale.

    python3 zoom_margin.py <row_id> <system_index> <pos,pos,...> <out.png>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

WORKS = REPO / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"


def main() -> int:
    from PIL import Image, ImageDraw
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.library.score_library import library_root

    rid, sysi = sys.argv[1], int(sys.argv[2])
    positions = [int(x) for x in sys.argv[3].split(",")]
    outp = sys.argv[4]

    lib = Path(library_root())
    works = json.loads(WORKS.read_text())
    row = [x for x in works["rows"] if x["row_id"] == rid][0]
    page = render_page(lib / row["edition"]["catalog_path"],
                       row["page"]["pdf_page_index"], dpi=600)
    pws = detect_staves(page)
    by_sys: dict[int, list] = {}
    for s in sorted(pws.staves, key=lambda s: s.top_y):
        by_sys.setdefault(s.system_index, []).append(s)
    staves = by_sys[sysi]

    heights = sorted(s.bottom_y - s.top_y for s in staves)
    spacing = heights[len(heights) // 2] / 4.0
    xs = sorted(s.x_start for s in staves)
    x1 = int(xs[len(xs) // 2] + 2 * spacing)

    tiles = []
    for i in positions:
        s = staves[i]
        y0 = max(0, int(s.top_y - 3 * spacing))
        y1 = min(page.rgb.shape[0], int(s.bottom_y + 3 * spacing))
        t = Image.fromarray(page.rgb[y0:y1, 0:x1]).convert("RGB")
        d = ImageDraw.Draw(t)
        d.text((4, 4), f"pos {i}", fill=(255, 0, 0))
        tiles.append(t)
    W = max(t.width for t in tiles)
    H = sum(t.height + 12 for t in tiles)
    canvas = Image.new("RGB", (W, H), (180, 180, 255))
    y = 0
    for t in tiles:
        canvas.paste(t, (0, y))
        y += t.height + 12
    canvas.save(outp)
    print(outp, canvas.size, "x1", x1, "spacing", round(spacing, 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
