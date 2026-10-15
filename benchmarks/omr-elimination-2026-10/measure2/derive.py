"""2.120 round 2: derive the widened bounds from MEASURED truth, stated margin 15%.
python3 measure2/derive.py   (reads measure/truth.json = round-1 rows; applies truth_overrides.json)
Rule: new upper = max(old, 1.15 x truth max); new lower = min(old, 0.85 x truth min), only for the bounds that
eliminated a true mark in round 1. Split-half check: the same rule fitted on even staves, tested on odd staves
(and the reverse) -- one system on the page, so staves are the only split there is."""
import json, sys
sys.path.insert(0, ".")
import table as T1
MARGIN = float(sys.argv[1]) if len(sys.argv) > 1 else 0.15
R = json.load(open("measure/truth.json"))
OV = json.load(open("truth_overrides.json"))
for r in R:
    if r["id"] in OV: r["sym"] = T1.symbol_of(OV[r["id"]]["now"])
def staff(r): return int(r["d"]["cell"].split("-st")[1].split("-")[0])
# (symbol, feature, which bound, table key)
TARGETS = [("dynamic_letter", "w", "hi"), ("tie", "fill", "hi"), ("tie", "h", "hi"), ("barline", "fill", "lo"),
           ("barline", "h", "lo"), ("flag", "w", "hi"), ("beam", "h", "lo")]
IDX = {"w": (0, 1), "h": (2, 3), "fill": None}
def old(sym, feat, side):
    s = T1.S[sym]
    lo, hi = (s["fill"] if feat == "fill" else (s["env"][IDX[feat][0]], s["env"][IDX[feat][1]]))
    return lo if side == "lo" else hi
def propose(rows, sym, feat, side):
    v = [r["d"][feat] for r in rows if r["sym"] == sym]
    o = old(sym, feat, side)
    return (min(o, round((1 - MARGIN) * min(v), 2)) if side == "lo" else max(o, round((1 + MARGIN) * max(v), 2))), min(v), max(v), len(v)
out = {}
print("symbol feat side | n truth range | old -> new | split-half: fit-even test-odd lost, fit-odd test-even lost")
for sym, feat, side in TARGETS:
    new, mn, mx, n = propose(R, sym, feat, side)
    lost = []
    for fit, test in ((0, 1), (1, 0)):
        nf, *_ = propose([r for r in R if staff(r) % 2 == fit], sym, feat, side)
        t = [r["d"][feat] for r in R if r["sym"] == sym and staff(r) % 2 == test]
        lost.append(sum((x < nf) if side == "lo" else (x > nf) for x in t))
    out["%s.%s.%s" % (sym, feat, side)] = new
    print("%-15s %-4s %s | n%3d %.2f-%.2f | %s -> %s | %s" % (sym, feat, side, n, mn, mx, old(sym, feat, side), new, lost))
json.dump(out, open("measure2/derived_bounds.json", "w"), indent=1)
