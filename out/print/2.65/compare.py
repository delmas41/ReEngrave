"""ROADMAP 2.65: Sean's blind answers (answers.json) vs a record's ADJUDICATE duration for the same head.

Heads are matched by page-box overlap (IoU), never by glyph index.  Usage: compare.py <record.json>
"""
import json, os, sys
from tools.omr.staged import readout

HERE = os.path.dirname(os.path.abspath(__file__))
man = json.load(open(os.path.join(HERE, "heads-manifest.json")))
ans = json.load(open(os.path.join(HERE, "answers.json")))
run = readout.load_run(sys.argv[1])

def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix * iy
    return ix * iy / u if u else 0.0

rows = []
for h in man["heads"]:
    cands = [(iou(h["page_box"], g.box_page), g) for g in run.glyphs.values()
             if g.page == h["pdf_page_index"] and g.box_page and g.family == "note"]
    best = max(cands, key=lambda t: t[0], default=(0, None))
    if best[0] < 0.3:
        rows.append((h["n"], ans.get(str(h["n"])), "NO MATCHING HEAD", "", "")); continue
    g = best[1]
    d = run.standing(g.key, "duration", "ADJUDICATE")
    o = run.standing(g.key, "glyph_owner", "ADJUDICATE")
    dur = (readout.plain_duration(d.get("value")) if d and d.get("outcome") == "decided"
           else f"{d.get('outcome')} ({d.get('reason')}) {d.get('candidates') or ''}" if d else "no verdict")
    pos = run.standing(g.key, "notehead_position", "ADJUDICATE")
    rows.append((h["n"], ans.get(str(h["n"])), dur, g.key, (o or {}).get("value"), (pos or {}).get("value")))
for r in rows:
    print(f"{r[0]:>2} | Sean: {r[1]} | ours: {r[2]} | pos={r[5] if len(r) > 5 else ''} | {r[3]} owner={r[4]}")
