"""ROADMAP 2.159 -- PROBE (page images only, no gather). For EVERY notehead box of a night slice whose head was LOCATED by
an earlier GATHER reader (2.39b `notehead_recentre`, 2.73 `head_line_cut`, 2.115 part-boxed re-centre accepted), the 2.148
slit/hole reading (`gather.head_interior_white`) on the STANDARD head box at the located centre, read off the PAGE raster
(`render_page(...).binary`, 600 dpi, the pixels the cell raster is cut from). Same box `gather_notehead_ink` reads its 2.23
windows on; the production GATHER (this lane's `interior_white_located`) reads the cell raster.
Also the same reading on the DETECTOR's own page box (`iw_det`, = what 2.153's probe injected) as the control that the page
raster reproduces the stored cell reading.
usage: located_iw_2_159.py SLICEDIR DOC OUT.json"""
import glob
import json
import os
import sys

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged.geometry import standard_head_box  # noqa: E402

PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}
SD, DOC, OUT = sys.argv[1:4]
out = {}
for p in sorted(glob.glob(os.path.join(SD, DOC, "p*.observations.jsonl"))):
    pg = int(os.path.basename(p)[1:3])
    heads, space = {}, {}
    for line in open(p):
        if not any(q in line for q in ('"glyph_box"', '"notehead_recentre"', '"head_line_cut"', '"notehead_ink"',
                                         '"cell_staff_space"')):
            continue
        o = json.loads(line)
        q, s = o["quantity"], o["subject"]
        if q == "cell_staff_space":
            space[s] = float(o["value"])
        elif q == "glyph_box" and (o.get("detail") or {}).get("category") == "notehead":
            heads.setdefault(s, {})["box"] = o
        elif s.startswith("glyph/") and q in ("notehead_recentre", "head_line_cut", "notehead_ink"):
            heads.setdefault(s, {})[q] = o
    img = None
    for s, h in heads.items():
        b = h.get("box")
        if b is None:
            continue
        name, x, y, w, hh = b["value"]
        bb = b["detail"].get("bbox_page_px")
        sp_c = space.get(s.replace("glyph/", "cell/").rsplit("/", 1)[0])
        if not bb or not sp_c or w <= 0:
            continue
        k = (bb[2] - bb[0]) / float(w)            # page px per canonical px
        sp = sp_c * k
        cx, cy = (bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0
        src = None
        rc = h.get("notehead_recentre")
        if rc and G.is_regular_notehead(name):
            dx, dy = rc["value"]
            cx, cy, src = cx + dx * sp, cy + dy * sp, "recentre"
        loc = None
        if h.get("head_line_cut"):
            lx, ly, lw, lh = h["head_line_cut"]["value"]
            loc = (bb[0] + (lx - x) * k, bb[1] + (ly - y) * k, lw * k, lh * k)
            src = "head_line_cut"
        elif src is None:
            pb = ((h.get("notehead_ink") or {}).get("detail") or {}).get("part_boxed") or {}
            if (((h.get("notehead_ink") or {}).get("detail") or {}).get("box_source") == "part_boxed_recentre"
                    and pb.get("accepted")):
                cy, src = cy + pb["dy_sp"] * sp, "part_boxed_recentre"
        if src is None:
            continue
        if loc is None:
            x0, x1, y0, y1 = standard_head_box(cx, cy, sp)
            loc = (x0, y0, x1 - x0, y1 - y0)
        if img is None:
            img = render_page(PDFS[DOC], pg, dpi=600).binary
            print(DOC, "page", pg, img.shape, flush=True)
        r = G.head_interior_white(img, loc)
        det = G.head_interior_white(img, (bb[0], bb[1], bb[2] - bb[0], bb[3] - bb[1]))
        if r:
            out[s] = {"iw": r, "src": src, "box_page": [round(v, 1) for v in loc], "sp_page": round(sp, 2),
                      "iw_det": det}
json.dump(out, open(OUT, "w"))
print(DOC, "located heads read", len(out))
