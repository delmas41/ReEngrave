"""For each cut (two-piece) hole move: does another head box of the cell hold a piece's centre? args: ON.record ms.json"""
import sys, json
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a8ed964f5bc0cc9cf")
from tools.omr.staged.record_io import load_record
r = load_record(sys.argv[1]); r = r.get("record", r)
heads = {}
for o in r["observations"]:
    if o["quantity"] == "glyph_box" and isinstance(o["value"], list) and str(o["value"][0]).startswith("notehead"):
        heads[o["subject"]] = (o.get("detail") or {}).get("bbox_page_px")
del r
for m in json.load(open(sys.argv[2])):
    h = (m["page"].get("holes") or [])
    if not h or h[0][1] != 2:
        continue
    step, n, cy, span, dx, off = h[0]
    sp = m["page"]["sp"]
    g = m["g"]
    cell = g.rsplit("/", 1)[0] + "/"
    b = heads[g]
    cx = (b[0] + b[2]) / 2
    ys = (cy - off[0] * sp, cy + off[1] * sp)
    hits = []
    for og, ob in heads.items():
        if og == g or not og.startswith(cell) or not ob:
            continue
        for y in ys:
            if ob[0] <= cx <= ob[2] and ob[1] <= y <= ob[3]:
                hits.append((og, round(y)))
    print(g, m["box_pos"], "->", m["hole_pos"], "neighbours holding a piece:", hits)
