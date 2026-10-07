"""The mechanism, measured. The through-the-head test (`ledger_grid.head_middle_rung_evidence`) asks for a
line at the used box's middle row, within MIDDLE_ROW_TOL_SPACES (0.15 sp = ~2.4 px). For each Litolff p3
far head whose verdict differs between raster A (scorers') and B (gather): slide the probe row from -9 to
+9 px around the row the reader actually used and print where the evidence is True. If True only on a
window of a few px and the used row is inside it in one raster and outside it in the other, the
read flips on 2 px of registration, not on the raster."""
from __future__ import annotations
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import numpy as np
import frame_drop_arms as F
import edge_census as ec
from tools.omr.annotate import ledger_grid as lg

SEAN = {"glyph/3/0/0/6/2": [-6]}


def used_box(fp, h, lines_g):
    lines = F.FH.frame_lines_for_head(fp.gray, lines_g, h["box"])
    sp = (max(lines) - min(lines)) / 4.0
    hh = dict(subject=h["subject"], box=tuple(h["box"]),
              kind="hollow" if F.FH.head_kind(h["cls"]) == "hollow" else "filled")
    st = fp._standard_box(hh, lines, sp)
    return (tuple(st["box"]) if st["pass"] else tuple(h["box"])), sp, st["pass"]


def evidence_window(fp, box, sp, others, mid):
    on = []
    for d in range(-9, 10):
        ev = lg.head_middle_rung_evidence(fp.gray, box, sp, others, mid + d)
        if ev:
            on.append(d)
    return on


if __name__ == "__main__":
    L = F.load()
    shp = L["D"]["shapes"][F.PAGE]
    shape = dict(width_sp=shp["width_sp"], height_sp=shp["height_sp"], tilt_deg=shp["tilt_deg"])
    sk = lambda s: "staff/" + "/".join(s.split("/")[1:4])
    far = [h for h in L["D"]["far"] if h["page"] == F.PAGE]
    pages = {}
    for name, gray in (("A", L["gray_A"]), ("B", L["gray_B"])):
        fp = F.FH.FarHeadPage(gray, L["heads"], L["page_boxes"], L["staff_lines"])
        fp.adopt(shape, "scorer")
        pages[name] = fp
    print("evidence(True) at probe row = used mid row + d, d in -9..9; the reader itself probes d=0 (tolerance +-2.4 px each side)")
    for h in far:
        out = {}
        for name, fp in pages.items():
            gl = L["staff_lines"][sk(h["subject"])]
            box, sp, passed = used_box(fp, h, gl)
            others = lg.exclusion_boxes_for(h["subject"], box, fp.nh, fp.acc, drop_same_ink_other_staff=True)
            mid = (box[1] + box[3]) / 2.0
            with lg.exclusion_rules(connected=True, own_box=None, one_sided=True):
                ev = evidence_window(fp, box, sp, others, mid)
            r = fp.read(h["subject"], h["box"], h["cls"], gl)
            out[name] = dict(ev=ev, pos=r["pos"], v=ec.verdict(r["pos"], SEAN.get(h["subject"], h["truth"])),
                             mid=mid, std=passed)
        if out["A"]["v"] == out["B"]["v"]:
            continue
        print(f"\n{h['subject']} ref {h['truth']}")
        for k in "AB":
            o = out[k]
            window = (f"{min(o['ev'])}..{max(o['ev'])}" if o["ev"] else "none in +-9")
            print(f"  {k}: read {o['pos']} ({o['v']}), box={'standard' if o['std'] else 'detector'}, "
                  f"evidence True for d in [{window}]  (reader probes d=0 -> {'True' if 0 in o['ev'] else 'False'})")
