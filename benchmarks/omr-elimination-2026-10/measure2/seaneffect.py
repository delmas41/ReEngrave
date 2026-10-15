"""Effect of each of Sean's answers on set membership (marks gaining/losing the symbol) -- R1 table vs Sean-only table.
Sean-only table = round-1 numbers + his rulings. python3 measure2/seaneffect.py"""
import json, sys, collections
sys.path.insert(0, ".")
import table as T1, table2 as T2
rows = json.load(open("measure2/truth2_rows.json"))
S = T2.build(widen=False, detector=False, litolff=False)
def sets(fn, *a): return [fn(r["d"], *a)[0] for r in rows]
A = [fn for fn in [None]]
r1 = [T1.candidates(r["d"])[0]["all"] for r in rows]
c2 = sets(T2.candidates, S)
gain = collections.Counter(); lose = collections.Counter(); gain_common = collections.Counter(); rare_only = collections.Counter()
for a, c in zip(r1, c2):
    for x in c["all"] - a: gain[x] += 1
    for x in c["common"] - a: gain_common[x] += 1
    for x in a - c["all"]: lose[x] += 1
    for x in c["rare"]: rare_only[x] += 1
print("gain (all):", dict(gain.most_common())); print("gain (common = excluding rare allowances):", dict(gain_common.most_common()))
print("lose:", dict(lose.most_common())); print("marks carrying each symbol ONLY as a rare allowance:", dict(rare_only.most_common()))
print("true marks recovered by Sean's answers:", [(r["id"], r["sym"]) for r, a, c in zip(rows, r1, c2) if r["sym"] in c["all"] and r["sym"] not in a])
print("true marks lost by Sean's answers:", [(r["id"], r["sym"]) for r, a, c in zip(rows, r1, c2) if r["sym"] not in c["all"] and r["sym"] in a])
