"""2.167 probe 8: which quantities carry the bytes of a record (to decide how to slim Brahms). usage: p8_sizes.py RECORD"""
import collections
import json
import sys
from pathlib import Path

d = json.loads(Path(sys.argv[1]).read_text())
rec = d["record"]
print("record keys", {k: (len(v) if hasattr(v, "__len__") else v) for k, v in rec.items()})
for part in ("observations", "verdicts"):
    c = collections.Counter()
    n = collections.Counter()
    for o in rec[part]:
        c[o["quantity"]] += len(json.dumps(o))
        n[o["quantity"]] += 1
    tot = sum(c.values())
    print(part, "total MB", round(tot / 1e6), "rows", sum(n.values()))
    for q, b in c.most_common(14):
        print("  %-34s %7.1f MB %8d rows" % (q, b / 1e6, n[q]))
print("other top-level keys:", [k for k in d if k != "record"])
