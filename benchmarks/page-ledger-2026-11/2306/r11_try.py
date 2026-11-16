"""2306 r11: the reader on the r11 fixtures, before (no strokes: the r9 reader) and after (contact pass), for each tile's head; and how many heads in
each window change reading. Usage (cwd = tree): r11_try.py FX.json"""
import sys, os, json
sys.path.insert(0, os.getcwd())
from tools.omr.staged import page_stems as PS
fx = json.load(open(sys.argv[1]))
for name, c in fx.items():
    if not isinstance(c, dict):
        continue
    heads = [dict(h, box=tuple(h["box"])) for h in c["heads"]]
    verts = [dict(v, box=tuple(v["box"])) for v in c["verticals"]]
    cross = [dict(x, box=tuple(x["box"])) for x in c["crossers"]]
    held = {int(k): v for k, v in c["held"].items()}
    strokes = {int(k): dict(v, box=tuple(v["box"])) for k, v in c["strokes"].items()}
    a = PS.read(heads, verts, held, crossers=cross)["heads"]
    b = PS.read(heads, verts, held, crossers=cross, strokes=strokes)["heads"]
    hid = next((h["id"] for h in heads if c["glyph"] in h["members"]), None)
    ra, rb = a.get(hid) or {}, b.get(hid) or {}
    other = [(k, a[k]["how"], b[k]["how"], b[k].get("direction")) for k in a if k != hid and (a[k]["how"], a[k].get("stroke")) != (b[k]["how"], b[k].get("stroke"))]
    print("%-14s Sean: %-34s | before %-14s | after %-22s %-5s stroke %s margin %s %s" % (
        name, c["sean"], ra.get("how"), rb.get("how"), rb.get("direction"), rb.get("stroke"), rb.get("margin"),
        "" if rb.get("how") == "contact_with_head_ink" else [(f.get("why"), f.get("direction"), f.get("margin")) for f in rb.get("candidates") or []][:3]))
    for o in other:
        print("      other head changed:", o)
