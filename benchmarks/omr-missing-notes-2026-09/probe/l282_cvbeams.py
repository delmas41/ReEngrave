#!/usr/bin/env python3
"""l282_cvbeams: for every one of Sean's truth beams on Brahms 317803 pdf 0 (fully labeled cells), what did the
classical-CV beam reader do with the ink? Prepares the page as the gather does (`pipeline.prepare_pages`) and, in
every cell holding a truth beam, runs the SAME `line_detection.detect_stems` and `detect_beams`, reporting

  * the beam-shaped OPENED COMPONENT over the truth beam (`detect_beams`'s own horizontal opening, on the
    staff-erased raster): found / not, its size in staff spaces;
  * whether `detect_beams` EMITTED it (>= 2 anchoring stems END at it), and how many stems anchored it;
  * the vertical-run candidates (`detect_stems`' `candidates_out`) that stand at the component's two ends and
    why each was refused (`too_wide`: the stem fused with the stack of heads on it; `too_tall`; ...).

So a beam the CV reader never emitted is told apart by cause: no component (the opening lost it), a component
with fewer than two anchors (the STEMS were refused), or emitted. ROADMAP 2.82. A reading probe.

    python3 l282_cvbeams.py [--page 0] [--json out.json]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402

from l281_tiles import PDFS  # noqa: E402
from l281_truth import Truth  # noqa: E402
from tools.omr import line_detection as LD  # noqa: E402
from tools.omr.hand_truth import score as S  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    T = Truth()
    full = S.Scope(T.full)
    truth_beams = [b for b in T.beams if full.holds(b.rect)]
    from tools.omr.staged.pipeline import prepare_pages
    (pws, cells), = prepare_pages(PDFS["brahms"], [a.page])
    rows = []
    cache = {}
    for b in truth_beams:
        cx, cy = (b.rect[0] + b.rect[2]) / 2, (b.rect[1] + b.rect[3]) / 2
        cell = None
        for c in cells:
            bb = getattr(c, "bbox_page_px", None)
            if bb and bb[0] <= cx <= bb[2] and bb[1] <= cy <= bb[3]:
                # the cell whose own (unpadded) rectangle holds the beam's centre is the one the beam is read in
                cell = c
                break
        if cell is None:
            rows.append({"truth_id": b.id, "status": "no cell"})
            continue
        key = id(cell)
        if key not in cache:
            sp = LD._staff_line_spacing(cell)
            cand = []
            stems = LD.detect_stems(cell, candidates_out=cand)
            beams = LD.detect_beams(cell, stems=stems, rescue_tall=True)
            src = cell.image_no_staff if getattr(cell, "image_no_staff", None) is not None else cell.image
            ink = LD._binary_ink(src)
            kw = max(3, int(round(sp * 1.5)))
            opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (kw, 1)))
            n, lab, st, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
            cache[key] = (sp, cand, stems, beams, st, n)
        sp, cand, stems, beams, st, n = cache[key]
        up = cell.upscale_factor
        bb = cell.bbox_page_px
        tb = [(b.rect[0] - bb[0]) * up, (b.rect[1] - bb[1]) * up, (b.rect[2] - bb[0]) * up, (b.rect[3] - bb[1]) * up]
        # the opened component(s) overlapping the truth beam
        comps = []
        for i in range(1, n):
            x, y, w, h, ar = [int(v) for v in st[i]]
            ox = min(x + w, tb[2]) - max(x, tb[0])
            oy = min(y + h, tb[3]) - max(y, tb[1])
            if ox > 0 and oy > 0:
                comps.append({"x": x, "y": y, "w": w, "h": h, "area": ar, "w_sp": round(w / sp, 2),
                              "h_sp": round(h / sp, 2), "overlap_x_of_truth": round(ox / max(1, tb[2] - tb[0]), 2)})
        emitted = [bm for bm in beams if min(bm.x_canonical + bm.width_canonical, tb[2]) - max(bm.x_canonical, tb[0]) > 0
                   and min(bm.y_canonical + bm.height_canonical, tb[3]) - max(bm.y_canonical, tb[1]) > 0]
        # candidates standing within 1.5 spaces of the truth beam's two ends
        near = []
        for v in cand:
            vx = v.x + v.w / 2.0
            if (abs(vx - tb[0]) <= 1.5 * sp or abs(vx - tb[2]) <= 1.5 * sp
                    or (tb[0] < vx < tb[2])) and v.y <= tb[3] + 1.0 * sp and v.y + v.h >= tb[1] - 1.0 * sp:
                near.append({"x": v.x, "w": v.w, "h": v.h, "h_sp": round(v.h / sp, 1), "outcome": v.outcome})
        status = ("emitted" if emitted else
                  ("component, not emitted (too few anchoring stems)" if comps else "no beam-shaped component"))
        rows.append({"truth_id": b.id, "status": status, "components": comps, "emitted": len(emitted),
                     "stems_in_cell": len(stems), "near_runs": near})
    c = collections.Counter(r["status"] for r in rows)
    print(f"truth beams in fully labeled cells of pdf page {a.page}: {len(rows)}")
    for k, v in c.items():
        print(f"   {v:3d}  {k}")
    print("\nper truth beam that the CV reader did NOT emit:")
    for r in rows:
        if r["status"] == "emitted":
            continue
        oc = collections.Counter(n["outcome"] for n in r.get("near_runs", []))
        print(f"  {r['truth_id']:8s} {r['status']}; components {[(c_['w_sp'], c_['h_sp']) for c_ in r.get('components', [])]}"
              f"; stems accepted in the cell {r.get('stems_in_cell')}; vertical runs near its ends/body: {dict(oc)}")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
