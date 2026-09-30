import json, random
pairs = json.load(open("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/pairs_a_extended.json"))

def bucket(p):
    refused = bool(p["refused1"]) or bool(p["refused2"])
    return (p["has_overlap"], refused, p["stem_side"])

from collections import defaultdict
buckets = defaultdict(list)
for p in pairs:
    buckets[bucket(p)].append(p)
for k, v in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
    print(k, len(v))

random.seed(42)
sample = []
# overlap, same side, 2.30-caught (already refused) -- 5
b = buckets.get((True, True, "same"), [])
sample += random.sample(b, min(5, len(b)))
# overlap, same side, NOT caught (both stand) -- 8
b = buckets.get((True, False, "same"), [])
sample += random.sample(b, min(8, len(b)))
# no overlap, same side (candidate "second apart" duplicate) -- 4
b = buckets.get((False, False, "same"), [])
sample += random.sample(b, min(4, len(b)))
# no overlap, opposite side (candidate real dyad) -- 3
b = buckets.get((False, False, "opposite"), [])
sample += random.sample(b, min(3, len(b)))

print("\nsample size", len(sample))
json.dump(sample, open("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/sample_a.json", "w"), indent=1)
for s in sample:
    print(s["cell"], s["g1"], s["g2"], s["cls"], "overlap" if s["has_overlap"] else "no_overlap", s["stem_side"], "refused" if (s["refused1"] or s["refused2"]) else "stands")
