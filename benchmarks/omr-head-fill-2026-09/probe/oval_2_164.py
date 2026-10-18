"""ROADMAP 2.164 -- the head-oval reading (`head_oval.ring_cover`) on the PAGE raster (`render_page(...).binary`, 600 dpi,
the raster `pws.page.binary` holds in GATHER) for: every 2.160 left-edge arc-tail candidate (both plates), and every head
Sean judged (2.160's join: real = he gave a value, non / rest = not a note). Writes OUT.json {doc: {glyph: reading}}.
usage: oval_2_164.py JOIN.json OUT.json"""
import json
import sys

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged.head_oval import ring_cover  # noqa: E402

PDFS = {"litolff": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                    "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"),
        "brahms": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                   "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")}
JOIN, OUT = sys.argv[1:3]
items = []
for doc in PDFS:
    for h in json.load(open("out/2.164/tails_%s.json" % doc))["hits"]:
        items.append((doc, h["glyph"], h["box"], h["sp"], "tail_candidate"))
for j in json.load(open(JOIN))["judged"]:
    if j.get("box") and j.get("sp"):
        items.append((j["doc"], j["glyph"], j["box"], j["sp"], "judged_" + j["side"]))
items.sort(key=lambda t: (t[0], int(t[1].split("/")[1])))
out = {"litolff": {}, "brahms": {}}
cur, img = None, None
for doc, g, box, sp, kind in items:
    pg = int(g.split("/")[1])
    if cur != (doc, pg):
        img = render_page(PDFS[doc], pg, dpi=600).binary
        cur = (doc, pg)
    r = ring_cover(img, box, sp)
    out[doc].setdefault(g, {"kinds": []})
    out[doc][g]["kinds"].append(kind)
    out[doc][g]["oval"] = r
json.dump(out, open(OUT, "w"), indent=0)
print({d: len(v) for d, v in out.items()})
