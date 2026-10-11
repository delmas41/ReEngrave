#!/usr/bin/env python3
"""l282_core: price the 2.82 CORE reading on a whole movement WITHOUT a re-gather. Every `Q.BEAM_STROKE`
stroke of a record (`l282_extract.py`) is read again with the product's own `gather.beam_stroke_ink` on
the page raster (600 dpi, the gather's frame, `preprocessing.render_page`) at page scale, the staff-line
thickness being the record's own `line_px` for that stroke (the reader's local line; `local_line_thickness`
is patched to return it, and `line_ys` is a dummy). So the numbers below are the product reader's, off the
same ink, at page instead of canonical scale -- CONTROL: the median this reads must reproduce the record's
`thickness_ratio` (reported, with the share within 0.1 lines) or the substitution is not valid.

Outputs one JSON of `{stroke id: {median ratio, core, rescued}}` and prints, for the strokes whose median
the 2.74 cut refuses (< 1.75): how many have a core, how many stand on a stem at BOTH ends of it
(`rescued`), by reader; and for Brahms pdf 0, against Sean's truth beams.

    python3 l282_core.py --ext ext.json --pdf brahms|litolff --out core.json [--pages 0,1]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l281_tiles import PDFS  # noqa: E402
from tools.omr.staged import gather  # noqa: E402
from tools.omr.staged.adjudicators import rhythm  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", default=None)
    a = ap.parse_args()
    ext = json.load(open(a.ext))
    pages = sorted({int(ck.split("/")[1]) for ck in ext["strokes"]})
    if a.pages:
        pages = [int(x) for x in a.pages.split(",")]
    from tools.omr.preprocessing import render_page
    import cv2
    out = {}
    cur_line = {"v": None}
    gather.local_line_thickness = lambda ink, line_ys, x0, x1, space: cur_line["v"]
    diffs = []
    for p in pages:
        gray = None
        n = 0
        for ck, ss in ext["strokes"].items():
            pp = ck.split("/")
            if int(pp[1]) != p:
                continue
            calib = ext["calib"].get(ck)
            if not calib:
                continue
            x0, y0, up = calib[:3]
            space_px = 100.0 / up
            for sid, s in ss.items():
                ink = ext["ink"].get(sid)
                if not ink or not ink.get("line_px"):
                    continue
                if gray is None:
                    rgb = render_page(PDFS[a.pdf], p, dpi=600).rgb
                    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY) if rgb.ndim == 3 else rgb
                bx, by, bw, bh = s["box"][:4]
                box = (x0 + bx / up, y0 + by / up, bw / up, bh / up)
                cur_line["v"] = ink["line_px"] / up
                m = gather.beam_stroke_ink(gray, box, space_px, [0.0] * 5)
                if m is None:
                    continue
                core = m["core"]
                detail = {"thickness_ratio": m["thickness_ratio"], "core": core}
                # every detector-boxed notehead of the stroke's cell, in PAGE px (the core is page-scale here)
                heads = [(x0 + hx / up, y0 + hy / up, hw / up, hh / up)
                         for hx, hy, hw, hh in ext.get("heads", {}).get(ck, [])
                         if hw / up <= rhythm.BEAM_HEAD_BOX_MAX_SPACES * space_px]
                out[sid] = {"med": m["thickness_ratio"], "rec": ink["thickness_ratio"],
                            "core": core, "thin": rhythm.stroke_thin_by_ink(detail, heads, space_px),
                            "was_thin": ink["thickness_ratio"] is not None and ink["thickness_ratio"] < 1.75,
                            "reader": s["reader"], "page": p, "cell": ck}
                diffs.append(abs((m["thickness_ratio"] or 0) - (ink["thickness_ratio"] or 0)))
                n += 1
        print(f"page {p}: {n} strokes", flush=True)
    d = np.array(diffs)
    print(f"CONTROL page-scale median ratio vs record's: n={len(d)} median |diff| {np.median(d):.3f} lines; "
          f"within 0.1: {(d <= 0.1).mean():.3f}; within 0.3: {(d <= 0.3).mean():.3f}")
    Path(a.out).write_text(json.dumps(out, separators=(",", ":")))
    thin = [v for v in out.values() if v["was_thin"]]
    cored = [v for v in thin if v["core"]]
    # RESCUED = the median is thin on BOTH readings (the record's and this page-scale one) and the core
    # stands on two stems; a stroke whose page-scale median lands over the cut is a control mismatch,
    # reported apart, never counted as a rescue.
    resc = [v for v in thin if v["med"] is not None and v["med"] < 1.75 and not v["thin"]]
    print(f"   thin by the record but not by this page-scale re-read (control mismatch): "
          f"{sum(1 for v in thin if v['med'] is None or v['med'] >= 1.75)}")
    print(f"strokes {len(out)}; refused as too_thin by the median (rec ratio < 1.75): {len(thin)}; "
          f"with a core: {len(cored)}; RESCUED (core stands on a stem at both ends): {len(resc)}")
    for rd in ("cv_lines", "detector"):
        print(f"   {rd}: thin {sum(1 for v in thin if v['reader'] == rd)} rescued {sum(1 for v in resc if v['reader'] == rd)}")
    print("   rescued core length (spaces):", sorted(round(v['core']['spaces'], 1) for v in resc))


if __name__ == "__main__":
    main()
