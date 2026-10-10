#!/usr/bin/env python3
"""l282_onestem: why was a stroke refused `one_stem` ("touches one stem") -- what stands at its two ends? For a
record cell (`--cell cell/10/1/9/7`) of a whole-movement extract (`l282_extract.py`): every stroke filed there with its ink
reading (thickness, bow, the stem the INK found at each end and, since 2.82, at each end of its thick CORE), then -- on the
page prepared as the gather prepares it -- every vertical-run candidate `detect_stems` produced that stands within
1.5 spaces of the stroke's x-range (accepted, or refused with the first refusing filter), every detector-boxed head under the
stroke, and a crop of it all. ROADMAP 2.82 (`one_stem`, Sean 2026-10-10: *"The 'doesn't touch more than one stem' is off"*).

    python3 l282_onestem.py --ext ext.json --pdf litolff --page 10 --cell cell/10/1/9/7 --head 1562.6,3460.6,1588.3,3481.2 --out x.png
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402

from l281_tiles import PDFS  # noqa: E402
from l282_stemhyp import pick_cell, to_canon  # noqa: E402
from tools.omr import line_detection as LD  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--cell", required=True)
    ap.add_argument("--head", required=True, help="x0,y0,x1,y1 page px of the head under judgement")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ext = json.load(open(a.ext))
    hb = [float(v) for v in a.head.split(",")]
    calib = ext["calib"][a.cell]
    x0, y0, up = calib[:3]
    strokes = []
    for sid, s in ext["strokes"].get(a.cell, {}).items():
        bx, by, bw, bh = s["box"][:4]
        pb = (x0 + bx / up, y0 + by / up, x0 + (bx + bw) / up, y0 + (by + bh) / up)
        strokes.append((sid, s["reader"], pb, ext["ink"].get(sid) or {}))
    from tools.omr.staged.pipeline import prepare_pages
    (pws, cells), = prepare_pages(PDFS[a.pdf], [a.page])
    c = pick_cell(cells, (hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2)
    sp = LD._staff_line_spacing(c)
    cand = []
    LD.detect_stems(c, candidates_out=cand)
    spp = sp / c.upscale_factor
    print(f"cell {a.cell}: staff space {spp:.1f} page px; head {hb}")
    heads = [h for h in ext.get("heads", {}).get(a.cell, [])]
    for sid, rd, pb, ink in strokes:
        print(f"\nstroke {sid} {rd} page box {[round(v) for v in pb]} ({(pb[2]-pb[0])/spp:.1f} x {(pb[3]-pb[1])/spp:.2f} sp)")
        print(f"   ratio {ink.get('thickness_ratio')} bow {ink.get('sagitta_spaces')} box-end stems "
              f"{[(e.get('found'), e.get('x')) for e in (ink.get('end_stems') or [])]}; core "
              f"{None if not ink.get('core') else (round(ink['core']['spaces'], 1), ink['core']['thickness_ratio'], [(e.get('found'), e.get('through'), e.get('side')) for e in ink['core']['end_stems']])}")
        cb = to_canon(c, *pb)
        near = []
        for v in cand:
            if v.x + v.w >= cb[0] - 1.5 * sp and v.x <= cb[2] + 1.5 * sp and v.y <= cb[3] + 6 * sp and v.y + v.h >= cb[1] - 6 * sp:
                near.append(v)
        for v in sorted(near, key=lambda v: v.x):
            print(f"   vertical run x {(v.x - cb[0]) / sp:+.1f} sp from the stroke's left end, {v.w / sp:.2f} sp wide, {v.h / sp:.1f} sp tall "
                  f"-> {v.outcome}")
    img = None
    from tools.omr.preprocessing import render_page
    img = render_page(PDFS[a.pdf], a.page, dpi=600).rgb
    allx = [p for _s, _r, pb, _i in strokes for p in (pb[0], pb[2])] + [hb[0], hb[2]]
    ally = [p for _s, _r, pb, _i in strokes for p in (pb[1], pb[3])] + [hb[1], hb[3]]
    X0, X1 = int(min(allx) - 3 * spp), int(max(allx) + 3 * spp)
    Y0, Y1 = int(min(ally) - 4 * spp), int(max(ally) + 4 * spp)
    crop = img[max(0, Y0):Y1, max(0, X0):X1].copy()
    ox, oy = max(0, X0), max(0, Y0)
    for sid, rd, pb, _i in strokes:
        col = (255, 0, 0) if rd == "detector" else (0, 90, 255)
        cv2.rectangle(crop, (int(pb[0] - ox), int(pb[1] - oy)), (int(pb[2] - ox), int(pb[3] - oy)), col, 1)
    cv2.rectangle(crop, (int(hb[0] - ox), int(hb[1] - oy)), (int(hb[2] - ox), int(hb[3] - oy)), (0, 170, 0), 2)
    cv2.imwrite(a.out, cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    print("->", a.out)


if __name__ == "__main__":
    main()
