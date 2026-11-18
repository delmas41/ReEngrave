"""ROADMAP 2.312 r2 -- OFF vs ON re-read (r2_reread.py) of the far-head ledger reader: what changed, and for round 1's 66 written-blue
heads (blue66.json, tag blue66) how many now read by count and why the rest still refuse.

    PYTHONPATH=. python3 benchmarks/ledger-count-2026-11/r2_compare.py OFF.json ON.json [blue66.json]
"""
import collections
import json
import sys


def word(r):
    return (r or "").split(" (")[0].split(";")[0]


off = json.load(open(sys.argv[1]))["heads"]
on = json.load(open(sys.argv[2]))["heads"]
ch = collections.Counter()
rows = []
for s in sorted(set(off) & set(on)):
    a, b = off[s]["got"], on[s]["got"]
    if a[1] == b[1]:
        continue
    k = ("read->read moved" if a[1] is not None and b[1] is not None else
         "refused->read" if b[1] is not None else "read->refused")
    ch[k] += 1
    rows.append((k, s, a[1], b[1], word(a[2])[:40], word(b[2])[:60]))
print("changed:", dict(ch), "of", len(set(off) & set(on)))
for r in rows:
    print("  %-17s %-20s %5s -> %5s | %s | %s" % r)
if len(sys.argv) > 3:
    b66 = [x["key"] for x in json.load(open(sys.argv[3])) if x["tag"] == "blue66"]
    now = collections.Counter()
    for k in b66:
        v = on.get(k)
        if v is None:
            now["not a job in the re-read"] += 1
        elif v["got"][1] is not None:
            now["reads by count"] += 1
        else:
            ink = ((v.get("cap") or {}).get("nf") or {}).get("ink") or {}
            w = word(v["got"][2])
            if not ink:
                w += " [ink not looked at: refused before the count]" if w.startswith("not_a_note") else " [box path]"
            elif not ink.get("ok"):
                w += " [ink: %s -> box path]" % ink.get("why")
            now["refuses: " + w[:80]] += 1
    print("blue66 (%d) now:" % len(b66))
    for k, v in now.most_common():
        print("  %3d  %s" % (v, k))
