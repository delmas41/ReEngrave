"""lane-frame-drop-investigation (2026-10-04): the far-head reader (the product's
`far_head_reader.FarHeadPage`) on the SAME 44 Litolff far heads, in two rasters:
  A  the benchmark scorers' raster (fitz render, UNDESKEWED)
  B  the gather's raster (`render_page(...).rgb`, deskewed)
boxes and staff lines always come from the record (the gather's frame).
"""
from __future__ import annotations
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import numpy as np, cv2
import score_standard_box as sb, truth_set_2_44c as ts
import score_head_template as sht
import edge_census as ec
from frame import render_page_matching_gather
from tools.omr.annotate import far_head_reader as FH
from tools.omr.staged.record import Q

import os
DOC = os.environ.get("FD_DOC", "beethoven5-litolff")
PAGE = int(os.environ.get("FD_PAGE", "3"))


def load():
    D = sb.build(DOC)
    rec = D["rec"]
    cfg = ts.DOCS[DOC]
    pi = render_page_matching_gather(cfg["pdf"], PAGE, 600)
    gray_B = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2GRAY)
    gray_A = D["pages"].get(PAGE)
    glyphs = sht._page_glyph_boxes(rec)[PAGE]
    cls_of = {s: c for (s, c, b) in glyphs}
    heads, staff_lines = [], {}
    for sub, box in D["nh"][PAGE]:
        sk = "staff/" + "/".join(sub.split("/")[1:4])
        lr = rec.obs(Q.STAFF_LINES, sk)
        o = rec.obs(Q.NOTEHEAD_STAFF_POSITION, sub)
        if not lr or not o:
            continue
        gl = [float(y) for y in lr[-1]["value"]]
        staff_lines[sk] = gl
        heads.append(dict(subject=sub, box=box, pos=int(o[-1]["detail"]["rounded"]),
                          cls=cls_of.get(sub, "noteheadBlackOnLine"), score=1.0, global_lines=gl))
    return dict(D=D, rec=rec, gray_A=gray_A, gray_B=gray_B, pi=pi, heads=heads,
                staff_lines=staff_lines, page_boxes=glyphs)


def make_page(L, gray):
    return FH.FarHeadPage(gray, L["heads"], L["page_boxes"], L["staff_lines"])


def read_all(L, fp):
    out = {}
    for h in L["D"]["far"]:
        if h["page"] != PAGE:
            continue
        parts = h["subject"].split("/")
        sk = "staff/" + "/".join(parts[1:4])
        r = fp.read(h["subject"], h["box"], h["cls"], L["staff_lines"][sk])
        out[h["subject"]] = dict(r, v=ec.verdict(r["pos"], h["truth"]), truth=h["truth"])
    return out


def tally(res):
    return ec.tally([r["v"] for r in res.values()])


if __name__ == "__main__":
    L = load()
    print("skew correction deg", L["pi"].skew_correction_deg)
    fa, fb = make_page(L, L["gray_A"]), make_page(L, L["gray_B"])
    print("A page shape", fa.shape_source, fa.shape, "n_on", fa.n_on_line, "thick", fa.thickness)
    print("B page shape", fb.shape_source, fb.shape, "n_on", fb.n_on_line, "thick", fb.thickness)
    shp = L["D"]["shapes"][PAGE]
    print("scorer shape p3", shp)
    shape = dict(width_sp=shp["width_sp"], height_sp=shp["height_sp"], tilt_deg=shp["tilt_deg"])
    fa.adopt(shape, "scorer"); fb.adopt(shape, "scorer")
    ra, rb = read_all(L, fa), read_all(L, fb)
    print("A", tally(ra), "B", tally(rb))
    for s in ra:
        if ra[s]["v"] != rb[s]["v"] or ra[s]["pos"] != rb[s]["pos"]:
            print(s, "ref", ra[s]["truth"], "A", ra[s]["pos"], ra[s]["v"], ra[s]["box_source"], "|", "B", rb[s]["pos"], rb[s]["v"], rb[s]["box_source"])
