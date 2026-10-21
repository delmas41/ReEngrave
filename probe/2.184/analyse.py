"""2.184: from replay.py output + the record clusters: (1) does the replay reproduce the record's pairs; (2) co-firing of a second rest class on every rest ink
(floor 0.05) -- pairs are the part where BOTH are >= 0.25; (3) what a class-agnostic merge would keep. usage: analyse.py REPLAY.json CL.json"""
import json, sys, collections
rp = json.load(open(sys.argv[1])); cl = json.load(open(sys.argv[2]))
def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0: return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i)
IOU = 0.3  # REST_DUPLICATE_IOU_MIN checked below
from tools.omr.staged.adjudicators.family_precision import REST_DUPLICATE_IOU_MIN as IOU
tot = collections.Counter(); inks_all = []
for pg, rows in rp.items():
    pg = int(pg)
    cw = [r for r in rows if not r["ag"]]
    # group by cell key
    bycell = collections.defaultdict(list)
    for r in cw: bycell[tuple(r["key"] or [])].append(r)
    prod = {k: [r for r in v if r["conf"] >= 0.25] for k, v in bycell.items()}
    # record pairs on this page
    rec_pairs = [c for c in cl if int(c["cluster"][0].split("/")[1]) == pg]
    def ctr(c):
        xs = [(b[0]+b[2])/2 for b in c["bbox"]]; ys = [(b[1]+b[3])/2 for b in c["bbox"]]
        return sum(xs)/len(xs), sum(ys)/len(ys)
    # replay pairs: production-floor boxes of different class with IoU >= IOU
    rpairs = []
    for k, v in prod.items():
        seen = set()
        for i, a in enumerate(v):
            for j, b in enumerate(v):
                if j > i and a["cls"] != b["cls"] and iou(a["bbox"], b["bbox"]) >= IOU:
                    rpairs.append((a, b))
    found = 0
    for c in rec_pairs:
        x, y = ctr(c)
        if any(abs((a["bbox"][0]+a["bbox"][2])/2 - x) < 12 and abs((a["bbox"][1]+a["bbox"][3])/2 - y) < 12 for a, b in rpairs): found += 1
    tot["rec_pairs"] += len(rec_pairs); tot["rec_found_in_replay"] += found; tot["replay_pairs"] += len(rpairs)
    # co-firing on each production rest ink: inks = union of production rest boxes linked by IoU; second = best other-class box at 0.05
    for k, v in prod.items():
        for a in v:
            others = [b for b in bycell[k] if b is not a and b["cls"] != a["cls"] and iou(a["bbox"], b["bbox"]) >= IOU]
            sec = max((b["conf"] for b in others), default=0.0)
            inks_all.append((a["cls"], a["conf"], sec))
print(sys.argv[1].split("/")[-1], dict(tot))
# per class: share of production rest boxes that have a different-class box >=0.25 / in [0.05,0.25) / none
byc = collections.defaultdict(list)
for cls, c, s in inks_all: byc[cls].append((c, s))
for cls, v in sorted(byc.items(), key=lambda kv: -len(kv[1])):
    n = len(v)
    print(f"  {cls:11s} n={n:5d}  other-class >=0.25: {sum(1 for c,s in v if s>=0.25):4d}  in [0.05,0.25): {sum(1 for c,s in v if 0.05<=s<0.25):4d}  none: {sum(1 for c,s in v if s<0.05):4d}")
# pair rate vs top conf (one entry per box with a rival; use boxes whose own conf is >= rival's)
bins = [(0.25,0.4),(0.4,0.5),(0.5,0.6),(0.6,0.7),(0.7,0.8),(0.8,1.01)]
print("  top-of-ink conf bin -> inks, share with a >=0.25 rival, share with a 0.05-0.25 rival")
for lo, hi in bins:
    v = [(c, s) for cls, c, s in inks_all if lo <= c < hi and c >= s]
    if v: print(f"   [{lo},{hi}) n={len(v):5d}  rival>=0.25 {100*sum(1 for c,s in v if s>=0.25)/len(v):5.1f}%  rival 0.05-0.25 {100*sum(1 for c,s in v if 0.05<=s<0.25)/len(v):5.1f}%")
