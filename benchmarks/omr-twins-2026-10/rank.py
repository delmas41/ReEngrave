"""2.119 step 3: rank split points. python3 rank.py -> out/ranking.json + prints"""
import json, collections, sys, statistics as st
from pathlib import Path
OUT = Path(__file__).resolve().parent / "out"
a = json.load(open(OUT / "analysis.json"))

def family(t):
    c = t["code"]; n = t["nums"]
    if c == "not_detected": return ("S0 DETECTOR", "no box at all")
    if c.startswith("class_wrong"): return ("S1 DETECTOR", "class wrong (hollow head called black)")
    if c.startswith("not_a_notehead"): return ("S2 ADJUDICATE refusal", "refused as not-a-notehead: " + c.split(":", 1)[1])
    if c == "duration_narrowed": return ("S4 ADJUDICATE duration", "duration left narrowed, no INFER collapse: " + (n.get("dur_reason") or "?").split(":", 1)[-1])
    if c == "chord_value_undecided": return ("S4 EVALUATE/EXPORT chord value", "chord value undecided (stem value abstained on a chord)")
    if c.startswith("held_bar"): return ("S6 EXPORT bar-sum hold-out", "bar held: " + c.split(":", 1)[1])
    if c == "unread_gap_in_partial_bar": return ("S6 EXPORT partial bar", "inside the red unread gap of a partial bar")
    return ("??", c)

def fam_group(f):
    return {"S4 ADJUDICATE duration": "A duration narrowed", "S6 EXPORT bar-sum hold-out": "B bar-sum hold-out", "S0 DETECTOR": "C detector: no box",
            "S2 ADJUDICATE refusal": "E refused not-a-notehead", "S6 EXPORT partial bar": "D partial-bar gap", "S1 DETECTOR": "F detector: wrong class",
            "S4 EVALUATE/EXPORT chord value": "G chord value undecided"}.get(f, f)

res = {}
tot = collections.Counter(); tot_fine = collections.Counter(); bykind = collections.defaultdict(collections.Counter)
for doc in ("brahms", "litolff"):
    d = a[doc]; T = {t["id"]: t for t in d["truth"]}
    for p in d["pairs"]:
        m = T[p["missed"]]; w = T[p["written"]]
        f, fine = family(m); g = fam_group(f)
        m["split_family"] = f; m["split_group"] = g; m["split_fine"] = fine
        tot[(doc, g)] += 1; tot_fine[(doc, g, fine)] += 1
        for dim, v in (("head", m["kind"]), ("stem", m["stem"]), ("pos", m["posk"])):
            bykind[(dim, v)][(doc, g)] += 1
print("== split points, family level (pairs) ==")
allg = collections.Counter()
for (doc, g), n in tot.items(): allg[g] += n
for g, n in allg.most_common(): print(f"{n:3d}  {g}   (brahms {tot[('brahms', g)]}, litolff {tot[('litolff', g)]})")
print("== split points, reason level ==")
allf = collections.Counter()
for (doc, g, fine), n in tot_fine.items(): allf[(g, fine)] += n
for (g, fine), n in allf.most_common(): print(f"{n:3d}  {g} | {fine}")
print("== by kind ==")
for (dim, v), c in sorted(bykind.items()):
    print(dim, v, sum(c.values()), dict(c))
# miss rate per kind
print("== miss rate per kind ==")
for doc in ("brahms", "litolff"):
    for dim in ("kind", "stem", "posk"):
        c = collections.defaultdict(lambda: [0, 0])
        for t in a[doc]["truth"]:
            c[t[dim]][0] += 1; c[t[dim]][1] += t["stage"] < 7
        print(doc, dim, {k: f"{v[1]}/{v[0]}" for k, v in c.items()})
    c = collections.defaultdict(lambda: [0, 0])
    for t in a[doc]["truth"]:
        k = (t["kind"], t["stem"], t["posk"]); c[k][0] += 1; c[k][1] += t["stage"] < 7
    print(doc, "signature", {"/".join(k): f"{v[1]}/{v[0]}" for k, v in sorted(c.items())})
json.dump({"family": allg, "fine": {f"{g} | {fn}": n for (g, fn), n in allf.items()}}, open(OUT / "ranking.json", "w"), indent=1)
json.dump(a, open(OUT / "analysis_ranked.json", "w"), default=str)
