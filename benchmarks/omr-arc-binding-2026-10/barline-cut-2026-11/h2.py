"""HYPOTHESIS 2: where does a barline-crossing arc first break? Ledger (deep-dive fate ledger, 20261104-night re-adjudicated) x cut.json.

Real arcs only (fate != not_an_arc). Litolff 8 sample pages; Brahms p0 + p5 (the pages the ledger holds).
CUT = a piece of the curve has a box end within 1 sp of an INTERIOR cell edge (suspected barline crossing; the box is clipped there).
JOINED = the page curve spans >1 cell. PARTNER = a box in the next cell meets this one at the edge (edge pair).
"""
import collections
import json


def cellof(k):
    return int(k.split("/")[-2]) if k else None


for plate in ("litolff", "brahms"):
    led = json.load(open("../deep-dive-2026-11/results/%s.base.ledger.json" % plate))["rows"]
    d = json.load(open("results/%s.cut.json" % plate))
    rows = {r["key"]: r for r in d["rows"]}
    real = [r for r in led if r["fate"] != "not_an_arc"]
    print("==", plate, "real arcs (curves/boxes)", len(real))
    tab = collections.defaultdict(collections.Counter)
    lost_rule = collections.defaultdict(collections.Counter)
    for r in real:
        ps = [rows.get(p) for p in r["pieces"]]
        ps = [p for p in ps if p]
        cut = any(p["cut_l"] or p["cut_r"] for p in ps)
        partner = any(p["partner_l"] or p["partner_r"] for p in ps)
        joined = bool(r["cells"] and len(r["cells"]) > 1)
        bound_cross = (r.get("bound_start") and r.get("bound_stop") and cellof(r["bound_start"]) != cellof(r["bound_stop"]))
        if not cut:
            grp = "A. no cut end"
        elif joined:
            grp = "B. cut, page curve joined across the barline"
        elif partner:
            grp = "C. cut, partner box across the barline but curve NOT joined"
        else:
            grp = "D. cut, other half never boxed (lone)"
        fate = "written" if r["fate"] in ("written", "written_as_slur") else ("lost:" + (r.get("lost_at") or "?")) if r["fate"] == "dropped" else r["fate"]
        tab[grp][fate] += 1
        tab[grp]["_n"] += 1
        if bound_cross:
            tab[grp]["_bound_across_cells"] += 1
        if r["fate"] == "dropped":
            lost_rule[grp][(r.get("lost_at"), str(r.get("lost_rule"))[:60])] += 1
    for g in sorted(tab):
        t = tab[g]
        n = t["_n"]
        wr = t["written"]
        print("  %-62s n=%4d written %4d (%.0f%%) | %s" % (g, n, wr, 100 * wr / n, dict((k, v) for k, v in sorted(t.items()) if k not in ("_n", "written"))))
    print("  lost-rule detail:")
    for g in sorted(lost_rule):
        print("   ", g, lost_rule[g].most_common(6))
