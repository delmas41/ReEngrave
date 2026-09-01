"""Render the head of EVERY staff on a page, so its clef can be read by eye.

The sweep corpora (`sweep_located_clefs.py`) render only the staves the locator
fires on, which is what they are for — they measure precision. They cannot say
whether a REJECTED staff was rejected rightly, because they contain no rejected
staves. That question needs a clef for every staff on the page, read by eye, and
this is the tool that puts them in front of you.

    python3 benchmarks/omr-clef-geometry/render_staff_heads.py \
        --pdf tools/omr/training/data/imslp/beethoven-symphony-9/pdfs/imslp-516488/score.pdf \
        --pages 20,60,120 --out-dir /tmp/heads

It prints the detected layout — systems and staves per system — which is what
the truth file records alongside the clefs, so a page whose layout Phase 1 later
reads differently can be skipped rather than silently mis-mapped.

The crop is the union of `staff.x_start` and the header window, for the reason
`sweep_located_clefs` documents: the window can end before the clef and
`x_start` can begin after it, and only the union always contains the glyph.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from tools.omr.measure_extractor import (  # noqa: E402
    detect_barlines,
    extract_measures,
    resegment_fused_measures,
)
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import header_cells_for_page  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402


def crop(rgb, staff, window, left_spaces, right_spaces, pad_spaces):
    spacing = max(1.0, staff.line_spacing_px)
    h, w = rgb.shape[:2]
    x_anchor = int(staff.x_start)
    x0 = min(window[0], x_anchor - int(left_spaces * spacing)) if window else \
        x_anchor - int(left_spaces * spacing)
    x1 = max(window[2], x_anchor + int(right_spaces * spacing)) if window else \
        x_anchor + int(right_spaces * spacing)
    y0 = int(staff.line_ys[0] - pad_spaces * spacing)
    y1 = int(staff.line_ys[-1] + pad_spaces * spacing)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        return np.full((10, 10, 3), 255, np.uint8)
    return rgb[y0:y1, x0:x1].copy()


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--pages", required=True,
                    help="comma-separated page indices")
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--per-montage", type=int, default=8)
    ap.add_argument("--left-spaces", type=float, default=6.0)
    ap.add_argument("--right-spaces", type=float, default=13.0)
    ap.add_argument("--pad-spaces", type=float, default=2.0)
    ap.add_argument("--zoom", type=float, default=1.0)
    args = ap.parse_args()

    pdf = args.pdf if args.pdf.is_absolute() else (REPO / args.pdf)
    pdf = pdf.expanduser()
    if not pdf.exists():
        print(f"no PDF at {pdf}", file=sys.stderr)
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)

    layouts = {}
    for page_index in [int(p) for p in args.pages.split(",")]:
        try:
            page = render_page(pdf, page_index, dpi=args.dpi)
            pws = detect_barlines(detect_staves(page))
            remove_staff_lines(resegment_fused_measures(pws, extract_measures(pws)))
        except Exception as exc:
            print(f"  p{page_index}: skipped ({type(exc).__name__}: {exc})")
            continue
        cells = header_cells_for_page(pws)
        staves = sorted(pws.staves, key=lambda s: s.top_y)
        if not staves:
            print(f"  p{page_index}: no staves")
            continue
        per_system: dict[int, int] = {}
        for s in staves:
            per_system[s.system_index] = per_system.get(s.system_index, 0) + 1
        layout = [per_system[k] for k in sorted(per_system)]
        layouts[page_index] = layout
        print(f"  p{page_index}: {len(staves)} staves, layout {layout}")

        tiles = []
        ordinals: dict[int, int] = {}
        for staff in staves:
            o = ordinals.get(staff.system_index, 0)
            ordinals[staff.system_index] = o + 1
            cell = cells.get(staff.staff_index)
            window = cell.bbox_page_px if cell is not None else None
            c = crop(page.rgb, staff, window, args.left_spaces,
                     args.right_spaces, args.pad_spaces)
            if args.zoom != 1.0:
                c = cv2.resize(c, None, fx=args.zoom, fy=args.zoom,
                               interpolation=cv2.INTER_CUBIC)
            lab = np.full((26, c.shape[1], 3), 255, np.uint8)
            cv2.putText(lab, f"sys{staff.system_index} ord{o}  (s{staff.staff_index})",
                        (4, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1,
                        cv2.LINE_AA)
            tiles.append(np.vstack([lab, c]))

        for k in range(0, len(tiles), args.per_montage):
            chunk = tiles[k:k + args.per_montage]
            w = max(t.shape[1] for t in chunk)
            rows = []
            for t in chunk:
                pad = np.full((t.shape[0], w - t.shape[1], 3), 255, np.uint8)
                rows.append(np.hstack([t, pad]) if pad.shape[1] else t)
                rows.append(np.full((5, w, 3), 150, np.uint8))
            out = args.out_dir / f"p{page_index}_{k // args.per_montage:02d}.png"
            cv2.imwrite(str(out), np.vstack(rows))

    (args.out_dir / "layouts.json").write_text(json.dumps(layouts, indent=1))
    print(f"\nmontages in {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
