"""seeded sample, 5 per ON bucket (all of a bucket when it has fewer): the printed arcs to look at (seed 2752)"""
import json
import random
import collections
C = json.load(open("buckets.json"))
by = collections.defaultdict(list)
for c in C:
    by[c["bucket_on"]].append(c["n"])
rng = random.Random(2752)
for b in sorted(by):
    if b == "right":
        continue
    pick = by[b] if len(by[b]) <= 5 else sorted(rng.sample(by[b], 5))
    print(b, len(by[b]), pick)
