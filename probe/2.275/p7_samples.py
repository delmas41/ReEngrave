"""2.167 probe 7: for OUR OWN eyes (not evidence), a seeded random sample of the ink-level buckets whose real-note share is unknown,
written as {sub: {"page_bbox": ...}} files that `p4_crops.py sheet` turns into contact sheets, and the no_pitch / narrowed reasons.
usage: p7_samples.py INK.json PART.rows.jsonl OUTDIR [N=16] [SEED=7]"""
import collections
import json
import os
import random
import sys

ink = json.load(open(sys.argv[1]))
rows = {r["sub"]: r for r in (json.loads(l) for l in open(sys.argv[2]))}
out = sys.argv[3]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 16
rng = random.Random(int(sys.argv[5]) if len(sys.argv) > 5 else 7)
os.makedirs(out, exist_ok=True)
for b in ("refused:not_a_notehead:too_narrow", "refused:not_a_notehead:clipped_fragment", "refused:duration_narrowed",
          "refused:no_pitch", "refused:chord_value_undecided", "held_bar_sum", "refused:ink_is_a_whole_rest"):
    subs = sorted(ink["members"].get(b, []))
    if not subs:
        continue
    pick = sorted(rng.sample(subs, min(N, len(subs))))
    json.dump({s: {"page_bbox": rows[s]["bbox"]} for s in pick},
              open(os.path.join(out, b.replace(":", "_") + ".json"), "w"))
# reasons
c = collections.Counter()
for s in ink["members"].get("refused:no_pitch", []):
    r = rows[s]
    c[(tuple((r["pitch"] or ["-", "-"])[:2]), tuple((r["position"] or ["-", "-"])[:2]))] += 1
print("no_pitch: (pitch verdict), (position verdict):")
for k, v in c.most_common(8):
    print("  ", v, k)
c = collections.Counter()
for s in ink["members"]["refused:duration_narrowed"]:
    c[(rows[s]["duration"] or ["-", "-"])[1]] += 1
print("duration_narrowed ink reasons:", dict(c))
c = collections.Counter()
for s in ink["members"]["refused:not_a_notehead:too_narrow"]:
    r = rows[s]
    c[r["cls"]] += 1
print("too_narrow classes", dict(c))
