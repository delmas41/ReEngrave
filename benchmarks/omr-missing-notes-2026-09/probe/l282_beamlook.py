#!/usr/bin/env python3
"""l282_beamlook: for named truth beams of Sean's page (Brahms 317803 pdf 0), every stroke of the
record that overlaps one, with its ink reading, and a crop at the gather's own 600 dpi: the truth
beam in GREEN, CV strokes in BLUE, detector strokes in RED (one thin outline each), the cell's five
page staff lines as thin yellow ticks at the left edge. ROADMAP 2.82. A reading probe.

    python3 l282_beamlook.py --ext ext.json --ids q82,q883,b4189 --out DIR
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from l281_truth import Truth  # noqa: E402
from l282_truthbeams import area, inter  # noqa: E402
from tools.omr.hand_truth import score as S  # noqa: E402

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
       "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")


def strokes_page(ext, page=0):
    out = []
    for ck, ss in ext["strokes"].items():
        p = ck.split("/")
        if int(p[1]) != page:
            continue
        calib = ext["calib"].get(ck)
        if not calib:
            continue
        x0, y0, up = calib[:3]
        for sid, s in ss.items():
            bx, by, bw, bh = s["box"][:4]
            pb = (x0 + bx / up, y0 + by / up, x0 + (bx + bw) / up, y0 + (by + bh) / up)
            out.append({"id": sid, "cell": ck, "reader": s["reader"], "pb": pb, "ink": ext["ink"].get(sid),
                        "ab": ext["ink_abs"].get(sid), "up": up})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", required=True)
    ap.add_argument("--ids", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pad", type=float, default=4.0, help="spaces around the truth beam")
    a = ap.parse_args()
    ext = json.load(open(a.ext))
    T = Truth()
    sp = T.space
    strokes = strokes_page(ext)
    bands = S.staff_bands(T.page)
    from tools.omr.preprocessing import render_page
    img = render_page(PDF, 0, dpi=600).rgb
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    byid = {i.id: i for i in T.beams}
    for tid in a.ids.split(","):
        it = byid[tid]
        r = it.rect
        print(f"== truth beam {tid} rect {[round(v) for v in r]} ({r[2]-r[0]:.0f} x {r[3]-r[1]:.0f} px; space {sp:.1f})")
        near = []
        for s in strokes:
            ia = inter(s["pb"], r)
            if ia <= 0:
                continue
            near.append((ia / area(r), s))
        near.sort(key=lambda t: -t[0])
        for frac, s in near:
            i = s["ink"] or {}
            pb = s["pb"]
            print(f"   {s['id']:12s} {s['reader']:9s} cell {s['cell']} box {[round(v) for v in pb]} "
                  f"({pb[2]-pb[0]:.0f}x{pb[3]-pb[1]:.0f}) covers {frac:.2f} of truth | ratio={i.get('thickness_ratio')} "
                  f"thick={i.get('thickness_px')} line={i.get('line_px')} sag={i.get('sagitta_spaces')} "
                  f"ends={[e.get('found') for e in (i.get('end_stems') or [])]} band={i.get('band')} "
                  f"{('ABSTAINED ' + str(s['ab'])) if s['ab'] else ''}")
        pad = a.pad * sp
        X0, Y0, X1, Y1 = int(r[0] - pad), int(r[1] - pad * 1.6), int(r[2] + pad), int(r[3] + pad * 1.6)
        crop = img[max(0, Y0):Y1, max(0, X0):X1].copy()
        ox, oy = max(0, X0), max(0, Y0)
        f = 1.0
        for frac, s in near:
            pb = s["pb"]
            col = (255, 0, 0) if s["reader"] == "detector" else (0, 90, 255)
            cv2.rectangle(crop, (int(pb[0] - ox), int(pb[1] - oy)), (int(pb[2] - ox), int(pb[3] - oy)), col, 1)
        cv2.rectangle(crop, (int(r[0] - ox), int(r[1] - oy)), (int(r[2] - ox), int(r[3] - oy)), (0, 170, 0), 1)
        for b in bands:
            if b.rect[0] <= (r[0] + r[2]) / 2 <= b.rect[2]:
                for ly in b.lines:
                    if Y0 <= ly <= Y1:
                        cv2.line(crop, (0, int(ly - oy)), (8, int(ly - oy)), (255, 200, 0), 2)
                        cv2.line(crop, (crop.shape[1] - 9, int(ly - oy)), (crop.shape[1] - 1, int(ly - oy)),
                                 (255, 200, 0), 2)
        cv2.imwrite(str(out / f"{tid}.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
        print(f"   -> {out / (tid + '.png')}")


if __name__ == "__main__":
    main()
