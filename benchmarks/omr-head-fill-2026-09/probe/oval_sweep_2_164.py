"""ROADMAP 2.164 -- sweep `head_oval.oval_width`'s two free settings (head-tall span, slack) over: the 28
left-edge candidates that STAND as notes on the night records (the lane's eye split them 20 tails / 8 boxes holding a
real head -- NOT evidence, the control set), and every head Sean judged (2.160 join: real / non / rest). Prints, per
setting, the tails' and the real heads' ring_cover range. Page raster = render_page(...).binary (600 dpi).
usage: oval_sweep_2_164.py JOIN.json OUT.json"""
import json
import sys

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged import head_oval as HO  # noqa: E402

PDFS = {"litolff": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                    "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"),
        "brahms": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                   "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")}
EYE_TAIL = {"litolff": {"3/1/5/3/1", "3/1/5/3/3", "3/1/5/15/2", "4/0/5/12/14", "5/1/4/2/1", "12/1/10/11/4",
                        "13/0/1/10/9", "13/1/4/2/2"},
            "brahms": {"14/0/13/3/4", "14/1/9/4/15", "17/1/5/2/21", "18/0/5/4/13", "18/1/3/5/19", "21/0/1/6/12",
                       "21/0/3/6/18", "26/1/1/6/17", "26/1/2/6/21", "26/1/3/6/16", "26/1/9/3/20", "26/1/9/4/18"}}
EYE_REAL = {"litolff": {"2/0/7/10/3", "2/1/1/14/3", "10/1/0/1/4", "12/0/2/1/7", "12/0/2/3/11", "14/1/2/11/5"},
            "brahms": {"16/0/11/3/7", "16/0/11/5/3"}}
SETTINGS = [(0.5, 0.25)]
JOIN, OUT = sys.argv[1:3]
items = []
for doc in PDFS:
    for h in json.load(open("out/2.164/tails_%s.json" % doc))["hits"]:
        g = h["glyph"][6:]
        lab = "eye_tail" if g in EYE_TAIL[doc] else "eye_real" if g in EYE_REAL[doc] else None
        if lab:
            items.append((doc, h["glyph"], h["box"], h["sp"], lab))
for j in json.load(open(JOIN))["judged"]:
    if j.get("box") and j.get("sp"):
        items.append((j["doc"], j["glyph"], j["box"], j["sp"], "judged_" + j["side"]))
items.sort(key=lambda t: (t[0], int(t[1].split("/")[1])))
rows = []
cur = img = None
for doc, g, box, sp, lab in items:
    pg = int(g.split("/")[1])
    if cur != (doc, pg):
        img = render_page(PDFS[doc], pg, dpi=600).binary
        cur = (doc, pg)
    r = dict(doc=doc, glyph=g, label=lab)
    for s, k in SETTINGS:
        HO.HEAD_TALL_SPACES, HO.SLACK_SPACES = s, k
        o = HO.oval_width(img, box, sp)
        r["%.1f/%.2f" % (s, k)] = None if o is None else o["oval_width_sp"]
        r["tallcols"] = None if o is None else round(o["head_tall_columns"] / sp, 3)
    rows.append(r)
json.dump(rows, open(OUT, "w"), indent=0)
for s, k in SETTINGS:
    key = "%.1f/%.2f" % (s, k)
    line = [key]
    for lab in ("eye_tail", "eye_real", "judged_real", "judged_non", "judged_rest"):
        v = sorted(x[key] for x in rows if x["label"] == lab and x[key] is not None)
        nn = sum(1 for x in rows if x["label"] == lab and x[key] is None)
        line.append("%s n%d none%d [%s .. %s] lo3=%s" % (lab, len(v), nn, v[0] if v else "-", v[-1] if v else "-",
                                                       v[:3] if lab != "eye_tail" else v[-3:]))
    print(" | ".join(line))
