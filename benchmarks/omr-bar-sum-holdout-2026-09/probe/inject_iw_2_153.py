"""ROADMAP 2.153 -- PROBE ONLY. The 20261014-night records carry no `interior_white` (2.148's GATHER row landed 10-16), so
a replay of main's defaults over them never exercises 2.148. This writes the row for every notehead box of a SLICE, from the
PAGE raster (`render_page(...).binary`, the same 600 dpi pixels the cell raster is cut from; `gather.head_interior_white` on
the detector's own box, bbox_page_px), into `Q.NOTEHEAD_INK.detail.interior_white`. It is NOT the production gather (that reads
the cell raster); the control is Sean's judged heads: halves must read >= 0.18, black <= 0.06 (printed).
usage: inject_iw_2_153.py SLICE.json DOC OUT.json
"""
import json
import sys

sys.path.insert(0, ".")
import numpy as np  # noqa: E402

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402

PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}
SL, DOC, OUT = sys.argv[1:4]
pdf = PDFS["brahms" if DOC.startswith("brahms") else "litolff"]
rec = json.load(open(SL))
boxes = {}
for o in rec["observations"]:
    if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("category") == "notehead":
        bb = (o["detail"] or {}).get("bbox_page_px")
        if bb:
            boxes[o["subject"]] = bb
pages = {}
n = 0
done = {}
for g, bb in boxes.items():
    pg = int(g.split("/")[1])
    if pg not in pages:
        pages[pg] = render_page(pdf, pg, dpi=600).binary
        print("page", pg, pages[pg].shape, "ink share %.3f" % float((pages[pg] == 0).mean()), flush=True)
    x0, y0, x1, y1 = bb
    r = G.head_interior_white(pages[pg], (x0, y0, x1 - x0, y1 - y0))
    if r:
        done[g] = r
for o in rec["observations"]:
    if o["quantity"] == "notehead_ink" and o["subject"] in done:
        d = dict(o.get("detail") or {})
        d["interior_white"] = done[o["subject"]]
        o["detail"] = d
        n += 1
print("heads with a row", len(done), "of", len(boxes), "| notehead_ink rows written", n)
json.dump(rec, open(OUT, "w"), default=str)
tiles = json.load(open("out/2.153/notes.json"))
for d, l in tiles.items():
    if d.split("_")[0] != DOC.split("_")[0]:
        continue
    fill = {}
    for t in l:
        if t["glyph"] in done:
            fill.setdefault("half+" if t["beats"] >= 2 else "black", []).append(done[t["glyph"]]["rows_share"])
    for k, v in fill.items():
        v = np.array(v)
        print(d, k, len(v), "rows_share min/med/max %.3f %.3f %.3f" % (v.min(), np.median(v), v.max()))
