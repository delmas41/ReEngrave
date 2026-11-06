"""Precision of WRITTEN arcs on Brahms p0 against Sean's hand arc boxes: does a hand arc exist where we wrote one? (arc existence, not end notes)
python3 handprec.py LEDGER.json"""
import json
import sys

sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ab22b9e5e1af96e0b/benchmarks/omr-arc-binding-2026-10/deep-dive-2026-11")
TRUTH = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ab22b9e5e1af96e0b/data/hand-truth/pages/imslp317803/0.json"
truth = [b for b in json.load(open(TRUTH))["boxes"] if b["cls"] in ("slur", "tie")]
led = json.load(open(sys.argv[1]))


def iou(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    i = (x1 - x0) * (y1 - y0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def hit(box):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return any(iou(box, t["rect"]) >= 0.2 or (t["rect"][0] <= cx <= t["rect"][2] and t["rect"][1] <= cy <= t["rect"][3]) for t in truth)


rows = [r for r in led["rows"] if r.get("page") == 0 and r["fate"] in ("written", "two_arcs", "wrong_note")]
ok = sum(1 for r in rows if hit(r["box"]))
print("written curves on p0: %d, with a hand arc under the box: %d (%.3f); no hand arc: %d" % (len(rows), ok, ok / max(1, len(rows)), len(rows) - ok))
for r in rows:
    if not hit(r["box"]):
        print("  no hand arc:", r["curve"], r["fate"], r["classes"], [round(x) for x in r["box"]])
