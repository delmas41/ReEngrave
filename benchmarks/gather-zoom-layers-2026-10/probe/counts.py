"""2.152 -- error counts per gallery source and document, from analyze_tiles rows. usage: counts.py ROWS.json"""
import json
import sys
from collections import Counter, defaultdict

rows = json.load(open(sys.argv[1]))
ERR = {"phantom_head", "phantom_rest", "rest_as_head", "value_error", "lost_note", "lost_rest", "rest_for_note"}
src = defaultdict(Counter)
for r in rows:
    key = r["item"] if r["item"] in ("2.145", "2.146", "2.148", "2.150", "2.151") else "older index galleries"
    s = "ERROR" if r["status"] in ERR else r["status"]
    src[(key, r["doc"])][s] += 1
print("source, doc -> status counts (ERROR = %s)" % sorted(ERR))
for k in sorted(src):
    print(k, dict(src[k]))
tot = Counter("ERROR" if r["status"] in ERR else r["status"] for r in rows)
print("TOTAL", dict(tot), "rows", len(rows))
print("by doc", {d: sum(1 for r in rows if r["doc"] == d and r["status"] in ERR) for d in ("litolff", "brahms", "brahms_p0p3")})
print("errors by kind", dict(Counter(r["status"] for r in rows if r["status"] in ERR)))
print("older-index errors", [(r["item"], r["n"], r["doc"], r["status"]) for r in rows
                             if r["status"] in ERR and r["item"] not in ("2.145", "2.146", "2.148", "2.150", "2.151")])
