"""Why the 'through the head' evidence fails on the gather raster: the jut test needs the head's connected ink
run to extend past the used BOX edge by THROUGH_RUNG_STUB_PROBE_SPACES (0.25 sp = ~3.9 px). Measure, per
head, the jut past each box edge at the row the reader probes (the best row within the tolerance), in A
(scorer, frames disagree), B (gather, frames agree), A2 (undeskewed, frames agree); then sweep the stub
threshold on all three to see where each arm's tally moves."""
from __future__ import annotations
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import numpy as np
import frame_drop_arms as F
import frame_drop_experiments as X
import frame_drop_probe_row as P
import edge_census as ec
from tools.omr.annotate import ledger_grid as lg

SEAN = {"glyph/3/0/0/6/2": [-6]}


def juts(gray, box, spacing, others, mid):
    """(left_jut_px, right_jut_px) of the run containing the box-x-middle column, best over the tolerance band
    rows (the reader unions the band, so use the band union exactly as it does)."""
    x0, y0, x1, y1 = box
    h, w = gray.shape
    pad = lg.RUNG_BOX_VISIBILITY_SPACES * spacing
    cx0, cx1 = max(0, int(x0 - pad)), min(w, int(x1 + pad))
    tol = lg.MIDDLE_ROW_TOL_SPACES * spacing
    wy0, wy1 = max(0, int(round(mid - tol))), min(h, int(round(mid + tol)) + 1)
    win = gray[wy0:wy1, cx0:cx1]
    thr = lg._otsu_threshold(win)
    ink = win <= thr
    if others:
        ink = lg._exclude_other_heads_ink(ink, others, cx0, wy0, spacing, gray, thr)
    cols = ink.any(axis=0)
    probe = int(round((x0 + x1) / 2.0)) - cx0
    if not cols[probe]:
        return None
    s = probe
    while s > 0 and cols[s - 1]:
        s -= 1
    e = probe
    while e < len(cols) - 1 and cols[e + 1]:
        e += 1
    e += 1
    return (x0 - cx0) - s, e - (x1 - cx0)


if __name__ == "__main__":
    L = F.load()
    shp = L["D"]["shapes"][F.PAGE]
    shape = dict(width_sp=shp["width_sp"], height_sp=shp["height_sp"], tilt_deg=shp["tilt_deg"])
    sk = lambda s: "staff/" + "/".join(s.split("/")[1:4])
    far = [h for h in L["D"]["far"] if h["page"] == F.PAGE]
    M, Mi = X.rot(L)
    heads2, pbs2, sl2, mbox, mlines = X.mapped(L, Mi)
    arms = {}
    for name, gray, hs, pb, sl, fm in (
            ("A", L["gray_A"], L["heads"], L["page_boxes"], L["staff_lines"], lambda h: (h["box"], L["staff_lines"][sk(h["subject"])])),
            ("B", L["gray_B"], L["heads"], L["page_boxes"], L["staff_lines"], lambda h: (h["box"], L["staff_lines"][sk(h["subject"])])),
            ("A2", L["gray_A"], heads2, pbs2, sl2, lambda h: (mbox(h["box"]), mlines(h["box"], L["staff_lines"][sk(h["subject"])])))):
        fp = F.FH.FarHeadPage(gray, hs, pb, sl)
        fp.adopt(shape, "scorer")
        arms[name] = (fp, fm)
    flips = ["glyph/3/0/7/3/1", "glyph/3/0/7/6/2", "glyph/3/1/0/9/0", "glyph/3/0/0/6/2", "glyph/3/0/0/7/1"]
    print("jut past the used box edge (left,right px) at the probe row; needs >= %.1f px on one side" %
          (lg.THROUGH_RUNG_STUB_PROBE_SPACES * 15.75))
    for h in far:
        if h["subject"] not in flips:
            continue
        line = h["subject"]
        for name, (fp, fm) in arms.items():
            box0, gl = fm(h)
            hh = dict(h, box=tuple(box0))
            box, sp, passed = P.used_box(fp, hh, gl)
            others = lg.exclusion_boxes_for(h["subject"], box, fp.nh, fp.acc, drop_same_ink_other_staff=True)
            with lg.exclusion_rules(connected=True, own_box=None, one_sided=True):
                j = juts(fp.gray, box, sp, others, (box[1] + box[3]) / 2.0)
            line += f" | {name}: " + ("no run" if j is None else f"L {j[0]:+.1f} R {j[1]:+.1f}") + f" box {box[2]-box[0]:.1f}px wide"
        print(line)
    print("\nstub-threshold sweep, right count vs Sean (n=41):")
    orig = lg.THROUGH_RUNG_STUB_PROBE_SPACES
    for stub in (0.25, 0.20, 0.15, 0.10, 0.05, 0.0):
        lg.THROUGH_RUNG_STUB_PROBE_SPACES = stub
        row = []
        for name, (fp, fm) in arms.items():
            vs = []
            for h in far:
                box, gl = fm(h)
                r = fp.read(h["subject"], box, h["cls"], gl)
                vs.append(ec.verdict(r["pos"], SEAN.get(h["subject"], h["truth"])))
            t = ec.tally(vs)
            row.append(f"{name} {t['right']}/{t['wrong']}/{t['abstain']}")
        print(f"stub {stub:.2f} sp ({stub*15.75:.1f} px): " + "   ".join(row))
    lg.THROUGH_RUNG_STUB_PROBE_SPACES = orig
