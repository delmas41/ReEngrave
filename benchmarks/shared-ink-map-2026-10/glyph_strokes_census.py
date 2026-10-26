"""ROADMAP 2.198: the sanity count the plan's step 2 asks for -- 2.185's "same cell, different class" doubles, re-found as boxes that stand on the same strokes.
usage: glyph_strokes_census.py ON.record.json
2.185's definition (benchmarks/omr-double-box-2026-10/FINDINGS.md): two detector boxes of ONE cell, different class, IoU >= 0.5 on the page (staff / brace boxes
left out). For each such pair, from the ON record's own `Q.GLYPH_STROKES` rows: the two stroke lists are EQUAL and non-empty ("same stroke set"), share at
least one stroke ("overlap"), or one/both are empty / abstained ("no strokes"). A control: pairs of boxes in different cells that do NOT overlap (the same
cell, IoU 0, different class) must share none."""
import collections, itertools, json, sys
sys.path.insert(0, ".")
from tools.omr.staged import record_io

rec = record_io.load_record(sys.argv[1])["record"]
boxes, gs, gabs = {}, {}, set()
for o in rec["observations"]:
    if o["quantity"] == "glyph_box":
        v, d = o.get("value"), o.get("detail") or {}
        if d.get("bbox_page_px") and isinstance(v, list) and v:
            boxes[o["subject"]] = (v[0], d["bbox_page_px"])
    elif o["quantity"] == "glyph_strokes":
        gs[o["subject"]] = tuple(o["value"])
for a in rec["abstentions"]:
    if a["quantity"] == "glyph_strokes":
        gabs.add(a["subject"])
cell = lambda s: "/".join(s.split("/")[:5])
bycell = collections.defaultdict(list)
for s, (cls, bb) in boxes.items():
    if cls not in ("staff", "brace"):
        bycell[cell(s)].append(s)


def iou(A, B):
    iw, ih = min(A[2], B[2]) - max(A[0], B[0]), min(A[3], B[3]) - max(A[1], B[1])
    if iw <= 0 or ih <= 0:
        return 0.0
    i = iw * ih
    return i / ((A[2] - A[0]) * (A[3] - A[1]) + (B[2] - B[0]) * (B[3] - B[1]) - i)


res = collections.Counter()
ctl = collections.Counter()
examples = []
for c, ss in bycell.items():
    for a, b in itertools.combinations(ss, 2):
        (ca, ba), (cb, bb) = boxes[a], boxes[b]
        if ca == cb:
            continue
        u = iou(ba, bb)
        sa, sb = gs.get(a), gs.get(b)
        if u >= 0.5:
            res["pairs"] += 1
            if a in gabs or b in gabs or sa is None or sb is None:
                res["no_stroke_map"] += 1
            elif not sa or not sb:
                res["no strokes (an empty list)"] += 1
            elif sa == sb:
                res["same stroke set"] += 1
                if len(examples) < 5:
                    examples.append((a, b, ca, cb, sa))
            elif set(sa) & set(sb):
                res["overlap, not equal"] += 1
            else:
                res["disjoint strokes"] += 1
        elif u == 0.0 and sa and sb:
            ctl["pairs_iou0"] += 1
            if set(sa) & set(sb):
                ctl["IOU0_sharing_a_stroke"] += 1
print("boxes", len(boxes), "with a GLYPH_STROKES row", len(gs), "abstained", len(gabs))
print("2.185 same-cell different-class pairs (IoU >= 0.5):", dict(res))
print("control (same cell, different class, IoU == 0, both with strokes):", dict(ctl))
for e in examples:
    print("   e.g.", e)
