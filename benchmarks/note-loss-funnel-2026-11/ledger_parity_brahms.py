"""ROADMAP 2.311 small test -- Brahms p0, truth = Sean's note-head class (OnLine / InSpace) = the parity of the position
(top line 0, line even, space odd). Match: label rect to record head box, IoU >= 0.8. A parity error is an off-by-one-step pitch.
    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/ledger_parity_brahms.py LH.json
"""
import collections, json, sys
from ledger_heights import owed, side, bin_of
lh = json.load(open(sys.argv[1]))["brahms"]["heads"]
p0 = [h for h in lh if h["page"] == 0 and not h["other_staff"]]
d = json.load(open("data/hand-truth/pages/imslp317803/0.json"))
nb = [b for b in d["boxes"] if b["cls"].startswith("notehead")]
def iou(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x1 - x0) * max(0, y1 - y0)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u else 0
t = collections.defaultdict(collections.Counter)
n_un = 0
for b in nb:
    best = max(p0, key=lambda h: iou(h["box"], b["rect"]), default=None)
    if best is None or iou(best["box"], b["rect"]) < 0.8:
        n_un += 1
        continue
    want = 0 if b["cls"].endswith("OnLine") else 1
    k = bin_of(owed(best["final"]), side(best["final"]))
    t[k]["n"] += 1
    t[k]["final parity wrong"] += int(best["final"] % 2 != want)
    t[k]["round(geometry) parity wrong"] += int(best["geom_round"] % 2 != want)
    if best["ledger"] is not None:
        t[k]["ledger-decided n"] += 1
        t[k]["ledger-decided wrong"] += int(best["final"] % 2 != want)
    else:
        t[k]["geometry-decided n"] += 1
        t[k]["geometry-decided wrong"] += int(best["final"] % 2 != want)
print("labelled heads with no record head box:", n_un)
for k in sorted(t):
    print(k, dict(t[k]))
