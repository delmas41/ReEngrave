"""Cut the 2.306 real-case fixture from a saved Brahms p0 record: the page heads (page-mark groups, oval or box, head ink) and the page map's vertical
strokes (+ held strokes) inside the bars Sean labelled (his stem rects from data/hand-truth/pages/imslp317803/0.json), and 2.300 tile 2's bar.
Usage: cut_fixture.py REC.json OUT.json"""
import sys, os, json, collections
sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record

rec = load_record(sys.argv[1])["record"]
obs = rec["observations"]
pg = lambda s: int(s.split("/")[1])
T = json.load(open("data/hand-truth/pages/imslp317803/0.json"))
cells = {c["id"]: c for c in T["cells"]}
WANT = ["s0-st11-m0", "s0-st11-m1", "s0-st11-m2", "s0-st6-m1", "s0-st0-m6", "s0-st4-m3", "s0-st8-m5", "s0-st10-m1"]
rects = [cells[c]["rect"] for c in WANT if c in cells]
stems = [b["rect"] for b in T["boxes"] if b["cls"] == "stem" and b["cell_id"] in WANT]


def inside(b):
    cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
    return any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in rects)


gbox = {o["subject"]: o["detail"]["bbox_page_px"] for o in obs if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px")}
oval = {}
for o in obs:
    d = o.get("detail") or {}
    if o["quantity"] == "claimed_area" and d.get("source") == "page_head_one" and d.get("oval"):
        for m in d.get("members") or ():
            oval[m] = d["oval"]
heads = []
for o in obs:
    if o["quantity"] == "page_mark" and (o.get("detail") or {}).get("family") == "head" and pg(o["subject"]) == 0:
        mem = o["detail"]["members"]
        b = next((oval[m] for m in mem if m in oval), None) or next((gbox[m] for m in mem if m in gbox), None)
        if b and inside(b):
            heads.append(dict(id=o["subject"], members=mem, box=[round(float(v), 1) for v in b], sp=32.0, ink=any(m in oval for m in mem)))
verts, held = [], {}
for o in obs:
    if o["quantity"] == "page_stroke" and pg(o["subject"]) == 0 and o["value"] == "vertical":
        d = o["detail"]
        b = d["bbox_page_px"]
        grown = [b[0], b[1] - 200, b[2], b[3] + 200]
        if inside(b) or any(r[0] <= (b[0] + b[2]) / 2 <= r[2] and r[1] - 200 <= b[1] <= r[3] + 200 for r in rects):
            verts.append(dict(ord=d["ordinal"], box=[float(v) for v in b], sp=float(d.get("staff_space_local_px") or 32.0)))
    d = o.get("detail") or {}
    if o["quantity"] == "claimed_area" and pg(o["subject"]) == 0 and d.get("page_strokes") and d.get("owner") not in ("head", "stem"):
        for i in d["page_strokes"]:
            held.setdefault(int(i), d.get("owner"))
vo = {v["ord"] for v in verts}
fx = dict(about="ROADMAP 2.306 real-case fixture: Brahms 317803 p0 (600 dpi page px), cut from a gather of main 718c83964 by "
                "benchmarks/page-ledger-2026-11 2306 cut_fixture.py; heads = the 2.290 page heads (oval or box), verticals = the page map's vertical strokes; "
                "sean_stems = Sean's stem labels in these bars (data/hand-truth/pages/imslp317803/0.json); tile_2300_2 = 2.300 tile 2's bar (staff 6 bar 1: a dotted "
                "quarter chord a second apart -- one stem).",
          cells=WANT, heads=heads, verticals=verts, held={str(k): v for k, v in held.items() if k in vo}, sean_stems=stems,
          tile_2300_2=cells.get("s0-st6-m1", {}).get("rect"))
json.dump(fx, open(sys.argv[2], "w"), indent=0)
print("heads", len(heads), "verticals", len(verts), "sean stems", len(stems), "held", len(fx["held"]))
