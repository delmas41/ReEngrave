"""ROADMAP 2.312 -- the population that matters: far heads WRITTEN blue on their own staff whose ledger count refused (Litolff pages 4, 8, 10), plus Sean's 2.311 tiles 2, 6, 8, 11 (wrong) and 3, 7.
For each: the reader's reason word; the page's ink at the head (raw finder on the page ink; the reader's own function with and without the other heads removed); a code-level category.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/ledger-count-2026-11 python3 benchmarks/ledger-count-2026-11/blue66.py HEADS_ALL.json HEADS_P.json KEY2311.json OUT.json
"""
import collections
import json
import sys

import numpy as np

from checksheet import page_image
from ledger_heights import load
from tools.omr.annotate import far_head_reader as FH
from tools.omr.annotate import ledger_grid as lg

allh = {h["key"]: h for h in json.load(open(sys.argv[1]))}
ph = json.load(open(sys.argv[2]))
key = json.load(open(sys.argv[3]))
rows, _ = load("litolff")
sl = rows["staff_lines"]
boxes_by_page = {}
for sub in rows["notehead_class"]:
    gb = rows["glyph_box"].get(sub)
    if gb:
        boxes_by_page.setdefault(int(sub.split("/")[1]), []).append((sub, tuple(gb["detail"]["bbox_page_px"])))

todo = []
for h in ph:
    g = int(round(h["geom"]))
    if (g <= -2 or g >= 10) and h["ledger_row"] is None and (h["pitch"] or {}).get("reason") == "position_and_clef_ledger_unread" \
            and h["written"] and h["written"]["blue"]:
        todo.append(("blue66", h["key"]))
SEAN = {2: "wrong", 6: "wrong", 8: "wrong", 11: "wrong", 3: "right", 7: "unconfirmed"}
for t in key:
    if t["tile"] in SEAN:
        todo.append(("sean%d_%s" % (t["tile"], SEAN[t["tile"]]), t["glyph"]))

cache = {}
out = []
for tag, k in todo:
    h = allh[k]
    p, s, st = (int(x) for x in k.split("/")[1:4])
    ys = [float(v) for v in sl["staff/%d/%d/%d" % (p, s, st)]["value"]]
    sp = (ys[4] - ys[0]) / 4.0
    b = tuple(h["box"])
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    if p not in cache:
        cache.clear()
        cache[p] = np.array(page_image("litolff", p).convert("L"))
    gray = cache[p]
    above = cy < ys[0]
    edge = ys[0] if above else ys[4]
    reason = ((h.get("ledger_refusal") or {}).get("detail") or {}).get("ledger_reason", "?")
    rw = reason.split(" (")[0]
    raw = lg.measure_ledger_rungs(gray, ys, cx, head_y=cy, head_box_x=(b[0], b[2]), collapse_edges_box=b).get("above" if above else "below", [])
    a = FH.read_absolute_position(gray, ys, b, k, [], [])
    c = FH.read_absolute_position(gray, ys, b, k, boxes_by_page.get(p, []), [])
    off = abs(cy - edge) / sp
    # stub-like ink: a row between the staff edge and the head whose dark run through the box column runs past the box by >= 0.3 sp on a side and is no longer than 4 sp
    stubs = 0
    lo, hi = (int(cy - 0.8 * sp), int(edge - 0.5 * sp)) if above else (int(edge + 0.5 * sp), int(cy + 0.8 * sp))
    for y in range(min(lo, hi), max(lo, hi), max(1, int(sp / 8))):
        row = gray[y - 1:y + 2, :].min(axis=0) < 128
        inside = [c0 for c0 in range(int(b[0]), int(b[2])) if row[c0]]
        if not inside:
            continue
        c0 = inside[len(inside) // 2]
        l = c0
        while l > 0 and row[l - 1]:
            l -= 1
        r = c0
        while r + 1 < row.size and row[r + 1]:
            r += 1
        run = (r - l + 1) / sp
        past = max((b[0] - l) / sp, (r + 1 - b[2]) / sp)
        if past >= 0.3 and run <= 4.0:
            stubs += 1
    if a[0] is not None and c[0] is None:
        cat = "shared with a neighbour head (reads when the other heads' ink is left in, refuses when it is removed)"
    elif a[0] is not None and c[0] is not None:
        cat = "reads here on the page ink; refused in the real run (other inputs: local lines / standard box / text, accidental, not-a-ledger boxes)"
    elif rw.startswith("count_does_not_fit"):
        cat = "count does not fit"
    elif off < 1.25:
        cat = "first space / first ledger: head centre within 1.25 sp of the staff edge, no line seen (geometry or a hidden first ledger)"
    elif raw:
        cat = "finder sees a line on raw ink away from the head's box (no_line_at_the_note_box / line not at the box)"
    elif stubs:
        cat = "no line found; stub-like ink beside the head exists (short or fused stub, the finder's tests failed)"
    else:
        cat = "no line found and no stub-like ink beside the head (nothing printed the finder could take)"
    out.append(dict(tag=tag, key=k, reason=rw, cat=cat, head_offset_sp=round(off, 2), raw_rungs=len(raw), stub_rows=stubs,
                    alone=a[1][:70], others_removed=c[1][:70], pitch=(h["pitch"] or {}).get("value"), geom=round(h["geom"], 2)))
json.dump(out, open(sys.argv[4], "w"), indent=1)
tal = collections.Counter(o["cat"] for o in out if o["tag"] == "blue66")
print("blue66:", sum(tal.values()))
for kk, v in tal.most_common():
    print("  %2d  %s" % (v, kk))
print("reason words:", collections.Counter(o["reason"] for o in out if o["tag"] == "blue66"))
for o in out:
    if o["tag"] != "blue66":
        print(o["tag"], o["key"], o["reason"], "| offset", o["head_offset_sp"], "raw rungs", o["raw_rungs"], "stubs", o["stub_rows"], "|", o["alone"], "|", o["cat"][:60])
