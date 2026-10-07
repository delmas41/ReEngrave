"""CONTROL (lane-farhead-per-bar-grid, 2026-10-06): the grid handed to the far-head reader equals the one gather used for the
record's in-staff positions. For 20 random in-staff heads: pos_float rebuilt from the head's page box centre and the
reconstructed per-bar grid (`(cy - top) / ((bottom - top) / 8)`) against the recorded `Q.NOTEHEAD_STAFF_POSITION` value.
CAN FAIL: the same rebuild against the RAW staff lines is printed beside it and must disagree on tilted bars.

  python3 farhead_per_bar_grid_control.py litolff 8 | brahms 10
"""
import random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import farhead_per_bar_grid_lib as GL
import farhead_note_first_oos as O
import truth_set_2_44c as ts
from frame import render_page_matching_gather
from tools.omr.staged import export as EXP
from tools.omr.staged.record import Q
from tools.omr.staged.record_io import load_record

DOCS = {"litolff": ("beethoven5-litolff", "beethoven5-litolff-mvt1-whole-20261006-night-combined.record.json"),
        "brahms": ("brahms1-breitkopf", "brahms1-breitkopf-mvt1-whole-20261006-night-combined.record.json")}


def main(which, page, n=20, seed=7):
    doc, fname = DOCS[which]
    rec = EXP.Record(load_record(O.SHARED / fname))
    cfg = ts.DOCS[doc]
    pi = render_page_matching_gather(cfg["pdf"], page, 600)
    grid_of, staves, raw, unmatched, pws, cells = GL.bar_grids(rec, page, pi)
    print(which, "page", page, "staves", len(staves), "unmatched", len(unmatched), "bars with a grid", len(grid_of))
    boxes = {}
    for o in rec.observations:
        if o["quantity"] == Q.GLYPH_BOX and o.get("value") and o["subject"].startswith(f"glyph/{page}/"):
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb and o["value"][0].startswith("notehead"):
                boxes[o["subject"]] = [float(v) for v in pb]
    cand = []
    for sub, b in boxes.items():
        po = rec.obs(Q.NOTEHEAD_STAFF_POSITION, sub)
        sy, st, ce = GL.head_cell(sub)
        if po and (sy, st, ce) in grid_of:
            pf = float(po[-1]["value"])
            if 0 <= pf <= 8:
                cand.append((sub, b, pf, grid_of[(sy, st, ce)], raw.get(f"staff/{page}/{sy}/{st}")))
    random.Random(seed).shuffle(cand)
    worst_g = worst_r = 0.0
    for sub, b, pf, g, r in cand[:n]:
        cy = (b[1] + b[3]) / 2.0
        pg = (cy - g[0]) / ((g[-1] - g[0]) / 8.0)
        pr = (cy - r[0]) / ((r[-1] - r[0]) / 8.0) if r else float("nan")
        worst_g, worst_r = max(worst_g, abs(pg - pf)), max(worst_r, abs(pr - pf))
        print(f"  {sub:22s} record {pf:7.3f}  per-bar grid {pg:7.3f} (d {pg - pf:+.3f})  raw lines {pr:7.3f} (d {pr - pf:+.3f})")
    print(f"  n={min(n, len(cand))} of {len(cand)} in-staff heads; worst |grid - record| = {worst_g:.3f} half-steps; "
          f"worst |raw - record| = {worst_r:.3f}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
