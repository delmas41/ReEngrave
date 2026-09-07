"""Tall crops with the DETECTED ROW MARKED, for hand-adjudicating a census hit.

`cut_crops.py` centres a crop on the rule, which is unreadable when the answer
is "which of the horizontal lines in this picture is the one it found". This
draws a marker in the margin at the detected y and shows enough context above
and below to see what the rule sits between.

    python3 cut_adjudication_crops.py --work mozart--symphony-25 --work bizet...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.preprocessing import render_page                    # noqa: E402
from tools.library.score_library import library_root               # noqa: E402

HERE = Path(__file__).parent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", default="census.json")
    ap.add_argument("--work", action="append", default=[])
    ap.add_argument("--out-dir", default="crops-adjudication")
    ap.add_argument("--pad-spaces", type=float, default=14.0)
    ap.add_argument("--x-span", type=int, default=1500,
                    help="page px of width to show, from the rule's x_start")
    args = ap.parse_args(argv)

    doc = json.loads((HERE / args.census).read_text())
    rows = [r for r in doc["rows"] if r.get("n_one")]
    if args.work:
        rows = [r for r in rows if r["work_id"] in set(args.work)]
    out = HERE / args.out_dir
    out.mkdir(exist_ok=True)
    root = library_root()

    for r in rows:
        page = render_page(str(root / r["path"]), r["page"], dpi=600)
        rgb = page.rgb
        for e in r["one_line"]:
            sp = float(e.get("spacing") or 20.0)
            pad = int(round(args.pad_spaces * sp))
            y0, y1 = max(0, e["y"] - pad), min(rgb.shape[0], e["y"] + pad)
            x0 = max(0, e["x_start"] - 40)
            x1 = min(rgb.shape[1], x0 + args.x_span)
            crop = rgb[y0:y1, x0:x1].copy()
            if crop.size == 0:
                continue
            # Mark the detected row: two red ticks in the margins, and a dotted
            # red overlay ON the row so it can be picked out of the staff lines
            # around it without hiding the ink.
            yy = e["y"] - y0
            if 0 <= yy < crop.shape[0]:
                crop[max(0, yy - 1):yy + 2, 0:34] = (255, 0, 0)
                crop[max(0, yy - 1):yy + 2, -34:] = (255, 0, 0)
                crop[yy:yy + 1, 40::14] = (255, 0, 0)
            sc = 1400 / crop.shape[1]
            crop = cv2.resize(crop, (1400, max(1, int(crop.shape[0] * sc))),
                              interpolation=cv2.INTER_AREA)
            slug = f"{r['work_id']}__p{r['page']}__s{e['staff_index']}.png"
            cv2.imwrite(str(out / slug), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
            print(" ", slug, f"(y={e['y']}, spacing={sp:.0f}, "
                             f"{r['n_five']} five-line staves on the page)",
                  flush=True)
    print("\nwrote to", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
