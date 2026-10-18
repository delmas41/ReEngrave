"""ROADMAP 2.164 -- static scan of a night record (streamed): every notehead-classed box at a bar's left edge
(`head_oval.LEFT_EDGE_SPACES`) with an arc box in the PREVIOUS cell of its staff ending at that cell's right edge
(`notehead_precision.ARC_CUT_AT_BARLINE_SPACES`) and overlapping its rows -- the rule's domain before the oval test --
then `head_oval.oval_width` on the page raster for each, and the stored `notehead_is_not_a_notehead` verdict.
Writes OUT.json {doc, hits: [...]}, the injection source for `replay_2_164.py`.
usage: scan_2_164.py RECORD.json DOC OUT.json"""
import collections
import json
import sys

import ijson

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged import head_oval as HO  # noqa: E402
from tools.omr.staged.adjudicators import notehead_precision as NP  # noqa: E402

PDFS = {"litolff": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                    "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"),
        "brahms": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                   "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")}
REC, DOC, OUT = sys.argv[1:4]
heads, cells, space, nn = {}, {}, {}, {}
arcs = collections.defaultdict(list)
with open(REC, "rb") as fh:
    for o in ijson.items(fh, "record.observations.item", use_float=True):
        s, q = o["subject"], o["quantity"]
        if q == "cell_box":
            cells[s] = o["value"]
        elif q == "cell_ink_pieces":
            space[s] = (o.get("detail") or {}).get("staff_space_page_px")
        elif q == "glyph_box" and (o.get("detail") or {}).get("category") == "notehead":
            heads[s] = (o["value"][0], o["detail"].get("bbox_page_px"))
        elif q == "arc_box":
            arcs["cell/" + "/".join(s.split("/")[1:5])].append((s, o["value"], (o.get("detail") or {}).get("bbox_page_px")))
print("heads", len(heads), "cells", len(cells), flush=True)
with open(REC, "rb") as fh:
    for v in ijson.items(fh, "record.verdicts.item", use_float=True):
        if v["quantity"] == "notehead_is_not_a_notehead" and v["subject"] in heads:
            nn[v["subject"]] = (v.get("value"), v.get("reason"))
hits = []
for g, (cls, b) in heads.items():
    p = g.split("/")
    c = "cell/" + "/".join(p[1:5])
    cb, sp = cells.get(c), space.get(c)
    if not b or not cb or not sp or not HO.box_at_left_edge(b, cb, sp):
        continue
    if int(p[4]) < 1:
        continue
    prev = "cell/%s/%s/%s/%d" % (p[1], p[2], p[3], int(p[4]) - 1)
    pb = cells.get(prev)
    if not pb:
        continue
    lo, hi = b[1] - NP.ARC_TAIL_ROW_SLACK_SPACES * sp, b[3] + NP.ARC_TAIL_ROW_SLACK_SPACES * sp
    best = None
    for a, kind, ab in arcs.get(prev, ()):
        if not ab:
            continue
        te = (pb[2] - ab[2]) / sp
        if abs(te) > NP.ARC_CUT_AT_BARLINE_SPACES or ab[3] < lo or ab[1] > hi:
            continue
        if best is None or abs(te) < abs(best[2]):
            best = (a, kind, te)
    if best:
        hits.append(dict(glyph=g, cls=cls, box=b, sp=sp, cell_box=cb, arc=best[0], kind=best[1],
                         arc_end_to_barline_sp=round(best[2], 3), left_gap_sp=round((b[0] - cb[0]) / sp, 3),
                         stored=nn.get(g)))
hits.sort(key=lambda h: [int(x) for x in h["glyph"].split("/")[1:]])
cur = img = None
for h in hits:
    pg = int(h["glyph"].split("/")[1])
    if cur != pg:
        img = render_page(PDFS[DOC], pg, dpi=600).binary
        cur = pg
    h["oval"] = HO.oval_width(img, h["box"], h["sp"])
json.dump(dict(doc=DOC, hits=hits), open(OUT, "w"), indent=0)
st = collections.Counter((h["stored"] or (None, None))[1] for h in hits)
low = [h for h in hits if h["oval"] and h["oval"]["oval_width_sp"] < NP.ARC_TAIL_OVAL_MAX_SPACES]
print(DOC, "domain", len(hits), dict(st), "| oval below cut", len(low),
      "| of those standing as heads", sum(1 for h in low if (h["stored"] or (None,))[0] is False))
