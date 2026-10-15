"""2.120 round 2: Brahms 317803 pdf 0 truth survival + candidate-set sizes under 4 table variants.
python3 measure2/truth2.py  -> measure2/truth2.out, measure2/truth2_rows.json
Truth read via tools.omr.hand_truth.store (REPO main checkout); two labels overridden in the MEASUREMENT only."""
import json, sys, collections, statistics, os
sys.path.insert(0, "."); sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/roadmap-start-d5bd81")
import table as T1, table2 as T2, descriptors as D1, descriptors2 as D
from pathlib import Path
REPO = "/Users/seanjohnson/Desktop/ReEngrave"
PDF = REPO + "/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
OV = json.load(open("truth_overrides.json")); OV = {k: v for k, v in OV.items() if not k.startswith("_")}
from tools.omr.hand_truth import store as ST
pt = ST.load(Path(REPO) / "data/hand-truth/pages/imslp317803/0.json")
page = json.load(open(REPO + "/data/hand-truth/pages/imslp317803/0.json"))
boxes = [(b.id, b.cls, list(b.rect)) for b in pt.boxes]
assert len(boxes) == 1566, len(boxes)
g = D1.page_gray(PDF, 0); m = D1.StaffModel(page)
rows = []
for i, cls, rect in boxes:
    c2 = OV[i]["now"] if i in OV else cls
    rows.append(dict(id=i, cls=cls, cls2=c2, sym=T1.symbol_of(c2), d=D.describe(rect, g, m)))
json.dump(rows, open("measure2/truth2_rows.json", "w"))
V = {"R1 (round-1 table, overrides applied)": (None, T1.S, T1.candidates),
     "S  (+ Sean's answers only)": (T2.build(widen=False, detector=False, litolff=False), None, T2.candidates),
     "W  (+ measured widening only)": (T2.build(sean=False, detector=False, litolff=False), None, T2.candidates),
     "R2 (S + W)": (T2.build(detector=False, litolff=False), None, T2.candidates),
     "R2D (+ detector-box widening)": (T2.build(litolff=False), None, T2.candidates),
     "R2DL (+ Litolff head_half fill) = FINAL": (T2.build(), None, T2.candidates)}
res = {}
for name, (S2, S1, fn) in V.items():  # noqa
    out = []
    for r in rows:
        if S2 is None: c, tr = fn(r["d"])
        else: c, tr = fn(r["d"], S2)
        out.append(dict(all=sorted(c["all"]), conv=sorted(c["conv"]), common=sorted(c.get("common", c["all"])), why=tr.get(r["sym"], [])))
    res[name] = out
def rep(name, out):
    n = len(rows); sa = sum(r["sym"] in o["all"] for r, o in zip(rows, out)); sc = sum(r["sym"] in o["conv"] for r, o in zip(rows, out))
    sz = [len(o["all"]) for o in out]; cz = [len(o["common"]) for o in out]
    print("%-42s survive all %4d/%d (%.2f%%)  conv %4d/%d | size all med %.0f p90 %d mean %.2f | common med %.0f mean %.2f | <=3: %d" % (
        name, sa, n, 100 * sa / n, sc, n, statistics.median(sz), sorted(sz)[int(.9 * (n - 1))], statistics.mean(sz), statistics.median(cz), statistics.mean(cz), sum(x <= 3 for x in sz)))
print("truth n", len(rows), "overrides", list(OV))
for name, out in res.items(): rep(name, out)
full = res["R2DL (+ Litolff head_half fill) = FINAL"]
print("\nREMAINING FAILURES (R2):")
for r, o in zip(rows, full):
    if r["sym"] not in o["all"]:
        d = r["d"]; print(" ", r["id"], r["cls"], "->", r["sym"], "w%.2f h%.2f fill%.2f %s %s xs%.1f edge%s" % (d["w"], d["h"], d["fill"], d["loc"], d["zone"], d["xs"], d["edge"]), "|", "; ".join(w[1] for w in o["why"]))
print("\nFAILURES under R1 fixed by R2:", [r["id"] for r, a, b in zip(rows, res["R1 (round-1 table, overrides applied)"], full) if r["sym"] not in a["all"] and r["sym"] in b["all"]])
print("NEW failures under R2 (survived R1):", [r["id"] for r, a, b in zip(rows, res["R1 (round-1 table, overrides applied)"], full) if r["sym"] in a["all"] and r["sym"] not in b["all"]])
print("\nPER CLASS (R2): n surv | all med/p90/max | common med | R1 all med | top set")
pc = collections.defaultdict(list)
for r, o, o1 in zip(rows, full, res["R1 (round-1 table, overrides applied)"]): pc[r["cls2"]].append((r, o, o1))
for k, v in sorted(pc.items(), key=lambda kv: -len(kv[1])):
    sa = [len(o["all"]) for r, o, o1 in v]; sc = [len(o["common"]) for r, o, o1 in v]; s1 = [len(o1["all"]) for r, o, o1 in v]
    top = collections.Counter(tuple(o["all"]) for r, o, o1 in v).most_common(1)[0]
    print(" %-22s n%4d surv%4d | all med%3.0f p90%3d max%3d | common med%3.0f | R1 med%3.0f | %s x%d" % (
        k, len(v), sum(r["sym"] in o["all"] for r, o, o1 in v), statistics.median(sa), sorted(sa)[int(.9 * (len(sa) - 1))], max(sa), statistics.median(sc), statistics.median(s1), "/".join(top[0]), top[1]))
print("\nPER SYMBOL candidate-set mean size, marks of that true symbol: R1 -> S -> W -> R2 -> R2D -> R2DL(final)")
bysym = collections.defaultdict(list)
for idx, r in enumerate(rows): bysym[r["sym"]].append(idx)
for s, ix in sorted(bysym.items(), key=lambda kv: -len(kv[1])):
    print(" %-15s n%4d  %s" % (s, len(ix), " -> ".join("%.2f" % statistics.mean(len(res[n][i]["all"]) for i in ix) for n in V)))
# which symbols gained/lost membership in how many marks, R1 -> R2
gain = collections.Counter(); lose = collections.Counter()
for a, b in zip(res["R1 (round-1 table, overrides applied)"], full):
    for x in set(b["all"]) - set(a["all"]): gain[x] += 1
    for x in set(a["all"]) - set(b["all"]): lose[x] += 1
print("\nsymbol gained in how many marks' sets (R1->R2):", dict(gain.most_common()))
print("symbol lost from how many marks' sets (R1->R2):", dict(lose.most_common()))
rare = sum(bool(set(o["all"]) - set(o["common"])) for o in full)
print("marks whose set contains a RARE member:", rare, "/", len(rows))
