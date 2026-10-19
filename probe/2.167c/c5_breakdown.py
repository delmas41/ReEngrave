"""2.167c probe 5: tally the agent's labels of the sampled held bars, cross with overfull/short and with the mechanical features.
usage: c5_breakdown.py"""
import collections
import json

L = json.load(open("probe/2.167c/labels.json"))
HELD = {"lit": 564, "bra": 915}
for plate, hf, ff in (("lit", "scr/lit_held.json", "scr/lit_feat.json"), ("bra", "scr/brahms_held.json", "scr/bra_feat.json")):
    S = json.load(open("scr/%s_sheets/sample.json" % plate))
    held = {(r["page"], r["system"], r["staff"], r["cell"]): r for r in json.load(open(hf))}
    feat = {(r["page"], r["system"], r["staff"], r["cell"]): r for r in json.load(open(ff))}
    fam = collections.Counter()
    sub = collections.Counter()
    cross = collections.Counter()
    for i, k in enumerate(S):
        lab = L[plate][str(i)]
        f = feat[tuple(k)]
        fam[lab[0]] += 1
        sub[lab] += 1
        cross[(lab[0], "over" if f["over"] else "short")] += 1
    n = len(S)
    print(plate, "n", n, "families", dict(fam), "sub", dict(sub))
    print("  scaled to %d held:" % HELD[plate], {k: round(v / n * HELD[plate]) for k, v in fam.items()})
    print("  cross", dict(cross))
    print("  sample over:", sum(v for (a, b), v in cross.items() if b == "over"), "short:", sum(v for (a, b), v in cross.items() if b == "short"))
