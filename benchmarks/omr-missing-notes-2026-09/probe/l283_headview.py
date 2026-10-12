#!/usr/bin/env python3
"""l283_headview: print crops (the red bracket on the head, nothing else of ours) of given head keys out of a record, side by side,
with the tip rows of the head's stem printed (value / abstention reason and the measures) from the base and the arm record, so a
CHANGED head can be looked at against the print. ROADMAP 2.83 probe.

    python3 l283_headview.py --pdf brahms|litolff --arm arm.record.json [--base base.record.json] --out m.png key [key ...]
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from l281_tiles import PDFS, cut  # noqa: E402
from l283_tiles import head_info  # noqa: E402
from l283_truth_score import tip_state  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def tip_rows(run, key):
    g = run.glyphs[key]
    hs = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
    sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
    out = []
    if hs is None or hs["outcome"] != "decided":
        return ["no decided stem"]
    for o in run.obs_at(g.cell_key, Q.STEM_TIP_INK):
        d = o.get("detail") or {}
        if d.get("stem_row_id") == hs["value"]:
            out.append((d["end"], "flag" if o["value"] else "none", {k: d.get(k) for k in ("out", "arm", "t_first", "right", "hooks", "hooks_reason")}))
    for s, k, a in run.rows_at(g.cell_key):
        if k == "abstention" and a["quantity"] == Q.STEM_TIP_INK and (a.get("detail") or {}).get("stem_row_id") == hs["value"]:
            d = a.get("detail") or {}
            out.append((d.get("end"), "abstained:" + a["reason"] + ":" + str(d.get("why")), {k: d.get(k) for k in ("out", "arm", "t_first", "area", "left_area")}))
    return [("direction", sd["value"] if sd and sd["outcome"] == "decided" else None)] + sorted(out, key=str)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--base", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("keys", nargs="+")
    a = ap.parse_args()
    from tools.omr.preprocessing import render_page
    arm = RD.load_run(a.arm)
    base = RD.load_run(a.base) if a.base else None
    tiles = []
    for key in a.keys:
        box, sp, stem, page = head_info(arm, key)
        img = render_page(PDFS[a.pdf], page, dpi=600).rgb
        crop, _w = cut(img, box, sp, stem)
        tiles.append(crop)
        for tag, run in (("base", base), ("arm", arm)):
            if run is None:
                continue
            v = run.standing(key, Q.DURATION, "ADJUDICATE")
            print(key, tag, v["outcome"] if v else None, v.get("reason") if v else None, tip_rows(run, key))
    H = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, 8, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles]
    cv2.imwrite(a.out, cv2.cvtColor(np.concatenate(tiles, axis=1), cv2.COLOR_RGB2BGR))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
