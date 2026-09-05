#!/usr/bin/env python3
"""Is the margin crop WIDE ENOUGH, or is it clipped by the page edge?

Separating class (b) — "a label is printed and the crop misses it" — from class
(a) — "no label is printed" — starts with a question that needs no eyes: does
the crop `staff_labels_vision.margin_strip` cuts actually reach the left edge of
the PAGE? The crop is

    x0 = max(0, x_ref - MARGIN_SPACINGS * spacing)

so when `x_ref - 30*spacing` is already negative, x0 is 0 and the reader is
looking at every pixel there is to the left of the staves. A widened crop cannot
help such a system, and a label it missed is either not printed or unreadable —
never mis-cropped.

⚠️ A NARROW CROP IS A SYMPTOM AS OFTEN AS A CAUSE. `x_ref` is the median staff
`x_start`, so on a page that prints NO margin labels the music simply begins
nearer the page edge and the crop comes out narrow *because* there is nothing
there. Do not read "narrow crop" as "crop bug" — read `edge_clipped`.

Also dumps a CONTROL image per system: the same band of the page taken from
x = 0 with no margin cap at all, so the (a)/(b) call can be settled by eye
against the widest possible evidence.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

WORKS = REPO / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"
DPI = 600


def main() -> int:
    from PIL import Image, ImageDraw
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr.staff_labels_vision import MARGIN_SPACINGS, OVERLAP_SPACINGS, _spacing
    from tools.library.score_library import library_root

    lib = Path(library_root())
    works = json.loads(WORKS.read_text())
    out = HERE / "controls"
    out.mkdir(exist_ok=True)
    rows = []

    for row in works["rows"]:
        rid = row["row_id"]
        pdf = lib / row["edition"]["catalog_path"]
        page = render_page(pdf, row["page"]["pdf_page_index"], dpi=DPI)
        pws = detect_staves(page)
        h, w = page.binary.shape
        by_sys: dict[int, list] = {}
        for s in sorted(pws.staves, key=lambda s: s.top_y):
            by_sys.setdefault(s.system_index, []).append(s)
        for sysi, staves in sorted(by_sys.items()):
            spacing = _spacing(staves)
            xs = sorted(s.x_start for s in staves)
            x_ref = xs[len(xs) // 2]
            want = x_ref - MARGIN_SPACINGS * spacing
            x0 = max(0, int(want))
            x1 = min(w, int(x_ref + OVERLAP_SPACINGS * spacing))
            y0 = max(0, min(s.top_y for s in staves) - int(2 * spacing))
            y1 = min(h, max(s.bottom_y for s in staves) + int(2 * spacing))
            rows.append({
                "row_id": rid, "system": sysi, "page_w": int(w),
                "spacing": round(float(spacing), 1),
                "x_start_min": int(xs[0]), "x_start_median": int(x_ref),
                "x_start_max": int(xs[-1]),
                "margin_wanted_px": round(float(MARGIN_SPACINGS * spacing), 1),
                "margin_available_px": int(x_ref),
                "x0": x0, "x1": x1, "crop_w": x1 - x0,
                "edge_clipped": want < 0,
                "headroom_px": int(x_ref - MARGIN_SPACINGS * spacing),
            })
            # control: everything from the page's left edge, ticks per staff
            ctrl = Image.fromarray(page.rgb[y0:y1, 0:x1]).convert("RGB")
            d = ImageDraw.Draw(ctrl)
            for i, s in enumerate(staves):
                cy = int((s.top_y + s.bottom_y) / 2) - y0
                d.line([0, cy, 24, cy], fill=(255, 0, 0), width=4)
                d.text((28, cy - 6), str(i), fill=(255, 0, 0))
            d.line([x0, 0, x0, ctrl.height], fill=(0, 0, 255), width=3)
            sc = 1400 / max(ctrl.width, ctrl.height)
            if sc < 1.0:
                ctrl = ctrl.resize((max(1, int(ctrl.width * sc)),
                                   max(1, int(ctrl.height * sc))), Image.LANCZOS)
            ctrl.save(out / f"{rid}-sys{sysi}-control.png")

    (HERE / "crop-geometry.json").write_text(json.dumps(rows, indent=1))
    print(f"{'row':38} {'sys':>3} {'space':>6} {'x_ref':>6} {'want':>7} "
          f"{'crop_w':>7} {'headroom':>9}  clipped")
    for r in rows:
        print(f"{r['row_id']:38} {r['system']:>3} {r['spacing']:>6} "
              f"{r['x_start_median']:>6} {r['margin_wanted_px']:>7} "
              f"{r['crop_w']:>7} {r['headroom_px']:>9}  "
              f"{'YES' if r['edge_clipped'] else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
