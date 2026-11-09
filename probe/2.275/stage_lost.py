"""2.275: for the real-note buckets, at which stage is the head lost? GATHER = no box (impossible here: every row is a detector box); ADJUDICATE = the
pitch or the duration is not decided; EXPORT = both decided, the exporter still refuses. Reads the p1 rows (the record's own verdicts).
usage: stage_lost.py PLATE INK.json PART.rows.jsonl"""
import collections
import json
import sys

plate, inkp, rowsp = sys.argv[1:4]
ink = json.load(open(inkp))
rows = {r["sub"]: r for r in (json.loads(l) for l in open(rowsp))}
print(plate)
for b in ("refused:duration_narrowed", "refused:no_pitch", "refused:chord_value_undecided"):
    c = collections.Counter()
    for s in ink["members"].get(b, []):
        r = rows[s]
        pitch = (r["pitch"] or ["none"])[0]
        pos = (r["position"] or ["none"])[0]
        dur = (r["duration"] or ["none"])[0]
        c[("pitch:" + pitch, "position:" + pos, "duration:" + dur)] += 1
    n = sum(c.values())
    print(" ", b, n)
    for k, v in c.most_common(6):
        print("     %4d  %s" % (v, k))
