"""ROADMAP 2.157 -- fold harness_2_157.py outputs (one per slice) into the before/after numbers.
A tile is counted once per document (the first slice it is found in: the groups are disjoint in tile systems).
usage: sum_2_157.py OUT.json [OUT.json ...]"""
import collections
import json
import sys

GOOD = ("right", "narrowed_holding")
seen = set()
tot = collections.Counter()
rows = []
for p in sys.argv[1:]:
    r = json.load(open(p))
    st, H = r["stored_tiles"], r["harness"]
    o, f = H["old"]["tiles"], H["fixed"]["tiles"]
    tot["glyphs"] += r["glyphs_stored"]
    for h in ("old", "fixed"):
        tot["first_differs_" + h] += H[h]["first_duration_differs_from_stored"]
    tot["fixed_eq_probe_files"] += bool(r.get("fixed_equals_probe_2_153"))
    tot["files"] += 1
    for g in f:
        if f[g] == "missing" or (r["doc"], g) in seen:
            continue
        seen.add((r["doc"], g))
        tot["tiles"] += 1
        tot["old_ne_stored"] += o[g] != st[g]
        tot["fixed_ne_stored"] += f[g] != st[g]
        tot["old_ne_fixed"] += o[g] != f[g]
        tot["old_breaks_good"] += (st[g] in GOOD and f[g] in GOOD and o[g] not in GOOD) or (
            st[g] == "right" and f[g] == "right" and o[g] != "right")
        if o[g] != f[g] or f[g] != st[g]:
            rows.append((r["doc"], g, "stored=" + st[g], "old=" + o[g], "fixed=" + f[g]))
for k, v in tot.items():
    print("%-22s %d" % (k, v))
for x in rows:
    print("  ", *x)
