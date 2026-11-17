"""ROADMAP 2.313 -- per page: heads whose value the exporter refused (duration_narrowed / chord_value_undecided), from facts files (reads only).

    python3 benchmarks/landing-check-2026-11/perpage.py A.facts.json B.facts.json ...
"""
import collections
import sys

REF = ("duration_narrowed", "chord_value_undecided")
rows = {}
for n in sys.argv[1:]:
    f = json.load(open(n)) if False else __import__("json").load(open(n))
    c = collections.Counter()
    for k, g in f["glyphs"].items():
        p = k.split("/")
        if len(p) == 6 and g.get("head") and g.get("fate") in REF:
            c[int(p[1])] += 1
    rows[n.split("/")[-1]] = c
pages = sorted({p for c in rows.values() for p in c})
print("page " + " ".join("%-18s" % n[:18] for n in rows))
for p in pages:
    print("%4d " % p + " ".join("%-18d" % rows[n][p] for n in rows))
print("tot  " + " ".join("%-18d" % sum(c.values()) for c in rows.values()))
