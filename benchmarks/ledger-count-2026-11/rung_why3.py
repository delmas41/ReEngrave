"""ROADMAP 2.312 Part 1 step 1c -- for the seeded 30: how far (in spaces of its own staff) is the head's centre from the nearest line of ANOTHER staff on the page, and from its own staff edge.
    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/ledger-count-2026-11 python3 benchmarks/ledger-count-2026-11/rung_why3.py WHY.json
"""
import json, sys
from ledger_heights import load
why = json.load(open(sys.argv[1]))
rows, _ = load("litolff")
sl = rows["staff_lines"]
for w in why:
    p, s, st = w["key"].split("/")[1:4]
    own = sl["staff/%s/%s/%s" % (p, s, st)]["value"]
    sp = (own[4] - own[0]) / 4
    b = rows["glyph_box"][w["key"]]["detail"]["bbox_page_px"]
    cy = (b[1] + b[3]) / 2
    best = None
    for k, r in sl.items():
        q = k.split("/")[1:]
        if q[0] != p or k == "staff/%s/%s/%s" % (p, s, st):
            continue
        ys = r["value"]
        d_edge = min(abs(cy - ys[0]), abs(cy - ys[4]))
        inside = ys[0] <= cy <= ys[4]
        if best is None or d_edge < best[0]:
            best = (d_edge / sp, inside)
    print(w["i"], w["key"], w["side"], "own edge %.2f sp" % abs(w["head_offset_sp"]), "| nearest OTHER staff edge %.2f sp" % best[0], "(inside it)" if best[1] else "")
