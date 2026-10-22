"""2.171 probe 3: THE CONTROL that must be able to fail. (a) my letterbox 'prod' boxes vs the 2.167d re-run's boxes made by the shipped
YoloDetector.detect (floor 0.05) -- same class, IoU > 0.8, |conf diff| ; (b) 'wide_rule' vs the 2.167d 'wide' re-run (the 0.13 -> 0.60 dot);
(c) subjects: the record's own conf vs my prod conf. A deliberately WRONG letterbox (shifted 7 px, fill white) is run elsewhere (L3/phase) and
shows what a failed reproduction looks like.
usage: e3_control.py lit|bra RUN.json"""
import json
import statistics
import sys

plate, run = sys.argv[1], sys.argv[2]
ROOT = __file__.rsplit("/probe/", 1)[0]
R = json.load(open(run))
RR = json.load(open(ROOT + "/probe/2.167d/data/%s_rerun.json" % plate))
SUB = json.load(open(ROOT + "/probe/2.171/data/subjects.json"))[plate]["subjects"]


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def cmp(mine, theirs, floor):
    n = m = 0
    diffs = []
    for t in theirs:
        if t[1] < floor:
            continue
        n += 1
        cand = [b for b in mine if b[0] == t[0] and iou(b[2:6], t[2:6]) > 0.8]
        if cand:
            b = max(cand, key=lambda b: iou(b[2:6], t[2:6]))
            m += 1
            diffs.append(abs(b[1] - t[1]))
    return n, m, diffs


for mine_name, theirs_name in (("prod", "base"), ("wide_rule", "wide")):
    N = M = 0
    D = []
    for key, r in R.items():
        if "conds" not in r or mine_name not in r["conds"]:
            continue
        v = RR[key]["variants"].get(theirs_name)
        if not v or "boxes" not in v:
            continue
        n, m, d = cmp(r["conds"][mine_name]["boxes"], v["boxes"], 0.10)
        N += n
        M += m
        D += d
    if N:
        print("%s %s vs 2.167d %s (boxes >= 0.10): %d of %d reproduced (class + IoU>0.8); conf diff median %.4f, max %.4f, >0.01: %d" % (
            plate, mine_name, theirs_name, M, N, statistics.median(D), max(D), sum(1 for x in D if x > 0.01)))
d = []
miss = 0
for key, r in R.items():
    if "subj" not in r:
        continue
    for i, sc in r["subj"].items():
        S = SUB[int(i)]
        if S["role"] == "lost" and S["cause"] == "A":
            continue
        a = sc["prod"]["any"]
        got = [b for b in r["conds"]["prod"]["boxes"] if b[0] == S["cls"] and abs(b[1] - S["rec_conf"]) < 0.02 and
               iou(b[2:6], S["bbox"]) > 0.5]
        if got:
            d.append(abs(got[0][1] - S["rec_conf"]))
        else:
            miss += 1
if d:
    print("%s subjects: record conf vs my prod conf: matched %d, not matched %d; conf diff median %.4f max %.4f" % (plate, len(d), miss, statistics.median(d), max(d)))
