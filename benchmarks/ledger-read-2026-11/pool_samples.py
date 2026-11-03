"""2.255: the far-head reader's head-shape samples per page of the WHOLE night record (the document pool GATHER builds
page by page), so a slice re-read adopts the same pool.  usage: pool_samples.py PLATE OUT.json"""
import collections
import json
import sys

import cv2

from tools.omr.annotate import far_head_reader as FH
from tools.omr.preprocessing import render_page
from tools.omr.staged import lane_report as LR
from tools.omr.staged.judged import iter_array

plate, out = sys.argv[1], sys.argv[2]
rp = LR.record_path(plate, "20261029-night")
boxes = collections.defaultdict(list)
geo, staff_lines = {}, {}
for o in iter_array(rp, "observations"):
    q = o.get("quantity")
    s = o.get("subject") or ""
    if q == "glyph_box":
        boxes[LR.page_of(s)].append((s, o["value"][0], tuple(float(v) for v in o["detail"]["bbox_page_px"])))
    elif q == "notehead_staff_position":
        geo[s] = int(round(float(o["value"])))
    elif q == "staff_lines":
        staff_lines[s] = [float(v) for v in o["value"]]
pdf = str(LR.LIB / LR.PLATES[plate]["pdf"])
res = {}
for page in sorted(p for p in boxes if p is not None):
    heads, used = [], {}
    for (s, c, b) in boxes[page]:
        if not c.startswith("notehead") or s not in geo:
            continue
        p = s.split("/")
        own = "staff/%s/%s/%s" % (p[1], p[2], p[3])
        if own not in staff_lines:
            continue
        used[own] = staff_lines[own]
        heads.append(dict(subject=s, box=b, pos=geo[s], cls=c, score=1.0, global_lines=staff_lines[own]))
    pi = render_page(pdf, page, dpi=600)
    gray = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2GRAY)
    ctx = FH.FarHeadPage(gray, heads, boxes[page], used)
    res[page] = ctx.samples
    print(plate, page, "samples", len(ctx.samples), flush=True)
json.dump({str(k): v for k, v in res.items()}, open(out, "w"), default=float)
