"""What stands at one page place in a record: page strokes (kind, box, claim owner), glyph boxes (class), area claims covering it, the page stem rows of
the glyphs there. Usage: probe_place.py REC.json PAGE x0 y0 x1 y1 [glyph keys...]"""
import sys, os, json
sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record

rec = load_record(sys.argv[1])["record"]
p = int(sys.argv[2])
X0, Y0, X1, Y1 = (float(v) for v in sys.argv[3:7])
keys = sys.argv[7:]
pg = lambda s: int(s.split("/")[1]) if s.split("/")[1].lstrip("-").isdigit() else None


def meets(b):
    return b[0] <= X1 and b[2] >= X0 and b[1] <= Y1 and b[3] >= Y0


own = {}
for o in rec["observations"]:
    d = o.get("detail") or {}
    if o["quantity"] == "claimed_area" and pg(o["subject"]) == p:
        for i in d.get("page_strokes") or ():
            own.setdefault(int(i), []).append("%s/%s/%s" % (d.get("owner"), d.get("source"), d.get("standing")))
        v = o["value"]
        if d.get("unit") == "area" and isinstance(v, list) and len(v) == 4 and meets(v):
            print("AREA CLAIM", d.get("owner"), d.get("standing"), [round(x) for x in v], d.get("scope"), o["subject"])
for o in rec["observations"]:
    d = o.get("detail") or {}
    if o["quantity"] == "page_stroke" and pg(o["subject"]) == p and meets(d["bbox_page_px"]):
        print("STROKE", d["ordinal"], o["value"], [round(x) for x in d["bbox_page_px"]], "th", d.get("thickness_spaces"), "L", d.get("length_spaces"), "owners", own.get(d["ordinal"]))
    if o["quantity"] == "glyph_box" and pg(o["subject"]) == p and d.get("bbox_page_px") and meets(d["bbox_page_px"]):
        print("GLYPH", o["subject"], o["value"][0] if isinstance(o["value"], list) else o["value"], [round(x) for x in d["bbox_page_px"]])
for o in rec["observations"] + rec["abstentions"]:
    if o["quantity"] == "page_stem" and o["subject"] in keys:
        print("PAGE_STEM", o["subject"], o.get("value"), json.dumps(o.get("detail"), default=str)[:600])
