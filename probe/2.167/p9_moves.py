"""2.167b probe 9: box-level movement of the first-cause bucket between two nights' PART.rows.jsonl (same detector boxes, same subjects).
usage: python3 probe/2.167/p9_moves.py OLD.part.rows.jsonl NEW.part.rows.jsonl [TOP=14]
Prints the (old bucket -> new bucket) matrix of boxes that changed, and for boxes that went into a held bar, the old duration/chord reason."""
import collections
import json
import sys

old = {r["sub"]: r for r in map(json.loads, open(sys.argv[1]))}
new = {r["sub"]: r for r in map(json.loads, open(sys.argv[2]))}
top = int(sys.argv[3]) if len(sys.argv) > 3 else 14
assert set(old) == set(new), (len(old), len(new), len(set(old) ^ set(new)))
mv = collections.Counter()
for s, o in old.items():
    n = new[s]
    if o["bucket"] != n["bucket"]:
        mv[(o["bucket"], n["bucket"])] += 1
print("boxes", len(old), "changed", sum(mv.values()))
for (a, b), c in mv.most_common(top):
    print("%5d  %s -> %s" % (c, a, b))
why = collections.Counter()
for s, o in old.items():
    n = new[s]
    if o["bucket"] != n["bucket"] and n["bucket"] == "held_bar_sum":
        why[(o["bucket"], tuple(map(str, (o["duration"] or [None, None])[:2])), tuple(map(str, (n["duration"] or [None, None])[:2])))] += 1
print("into held: old bucket, old duration verdict, new duration verdict")
for k, c in why.most_common(8):
    print("%5d  %s" % (c, k))
