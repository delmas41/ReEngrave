"""ROADMAP 2.153 probe check: does the PAGE-raster box line up with the record's own ink reading? For Sean-judged heads, the
record's `notehead_ink` centre-window ink vs the page raster's, and the injected rows_share. usage: iw_check_2_153.py SLICE_IW.json DOC"""
import json
import sys

sys.path.insert(0, ".")
import numpy as np  # noqa: E402

from tools.omr.preprocessing import render_page  # noqa: E402

sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
SL, DOC = sys.argv[1:3]
pdf = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}[DOC.split("_")[0]]
rec = json.load(open(SL))
tiles = {t["glyph"]: t for t in json.load(open("out/2.153/notes.json"))[DOC]}
box, ink = {}, {}
for o in rec["observations"]:
    if o["subject"] in tiles:
        if o["quantity"] == "glyph_box":
            box[o["subject"]] = o["detail"].get("bbox_page_px")
        if o["quantity"] == "notehead_ink":
            ink[o["subject"]] = o["detail"]
pages = {}
for g, t in list(tiles.items())[:40]:
    if g not in box or g not in ink:
        continue
    pg = int(g.split("/")[1])
    if pg not in pages:
        pages[pg] = render_page(pdf, pg, dpi=600).binary
    x0, y0, x1, y1 = [int(round(v)) for v in box[g]]
    crop = pages[pg][y0:y1, x0:x1]
    h, w = crop.shape
    c = crop[int(0.3 * h):int(0.7 * h), int(0.3 * w):int(0.7 * w)]
    print("%-24s sean %-5s box %dx%d  record center ink %.2f | page center ink %.2f | iw %s" % (
        g, t["sean"], w, h, ink[g]["ink_raw"]["windows"]["center"], float((c == 0).mean()),
        (ink[g].get("interior_white") or {}).get("rows_share")))
