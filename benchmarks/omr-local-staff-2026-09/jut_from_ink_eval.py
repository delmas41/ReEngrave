"""lane-jut-from-ink (2026-10-04): the far-head reader with the jut measured from the head's INK edge
(`ledger_grid._jut_from_head_ink`) instead of the detector box edge. CORRECT FRAME ONLY: the gather's
deskewed raster (arm B of frame_drop_arms) with the record's boxes. Read-only on the shared records.

  python3 jut_from_ink_eval.py            # tally old vs new, Litolff p3 and Brahms p1
  python3 jut_from_ink_eval.py shift      # box shifted by -2..+2 px in x and y, old vs new
"""
from __future__ import annotations
import os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import frame_drop_arms as F
import edge_census as ec
from tools.omr.annotate import far_head_reader as FH

SEAN = {"glyph/3/0/0/6/2": [-6]}   # Sean's -6 (the 2.44c reference says -4)


def prepare(doc, page):
    F.DOC, F.PAGE = doc, page
    L = F.load()
    shp = L["D"]["shapes"][page]
    shape = dict(width_sp=shp["width_sp"], height_sp=shp["height_sp"], tilt_deg=shp["tilt_deg"])
    fp = FH.FarHeadPage(L["gray_B"], L["heads"], L["page_boxes"], L["staff_lines"])
    fp.adopt(shape, "scorer")
    far = [h for h in L["D"]["far"] if h["page"] == page]
    return L, fp, far


def run(L, fp, far, mode, dx=0, dy=0, sean=True):
    FH.EXCLUSION_RULES["jut_from_ink"] = (mode == "ink")
    sk = lambda s: "staff/" + "/".join(s.split("/")[1:4])
    out = {}
    for h in far:
        b = h["box"]
        sb = (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy)
        r = fp.read(h["subject"], sb, h["cls"], L["staff_lines"][sk(h["subject"])])
        truth = SEAN.get(h["subject"], h["truth"]) if sean else h["truth"]
        out[h["subject"]] = (ec.verdict(r["pos"], truth), r["pos"], r["reason"])
    return out


def tal(res):
    return ec.tally([v[0] for v in res.values()])


if __name__ == "__main__":
    for doc, page in (("beethoven5-litolff", 3), ("brahms1-breitkopf", 1)):
        L, fp, far = prepare(doc, page)
        print("==", doc, "p%d" % page, "n_far", len(far), "shape", fp.shape_source)
        old, new = run(L, fp, far, "box"), run(L, fp, far, "ink")
        print("box edge:", tal(old), "| ink edge:", tal(new))
        for s in old:
            if old[s][0] != new[s][0] or old[s][1] != new[s][1]:
                print("  ", s, "truth", [h for h in far if h["subject"] == s][0]["truth"],
                      "old", old[s][:2], "new", new[s][:2])
        if len(sys.argv) > 1 and sys.argv[1] == "shift":
            print("right heads under a box shift; rows dy, cols dx=-2..+2")
            for mode in ("box", "ink"):
                tot = []
                for dy in (-2, -1, 0, 1, 2):
                    row = [tal(run(L, fp, far, mode, dx, dy))["right"] for dx in (-2, -1, 0, 1, 2)]
                    tot += row
                    print(" ", mode, "dy=%+d" % dy, row)
                print("  ", mode, "min/max over 25 shifts:", min(tot), max(tot))
