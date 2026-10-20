"""2.172 probe 2: read v1's output, answer (b) lost symbols found per family and plate, (c) kept symbols dropped, (d) new boxes per view/family,
(cost) the time multiplier, and the control (record match; perturbed run). Pure JSON, no detector.
usage: v2_analyse.py  -> probe/2.172/data/analysis.txt"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "probe/2.172/data"
SUB = json.load(open(ROOT / "probe/2.171/data/subjects.json"))
VARS = ["full", "noaa", "nophase", "bare"]


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def fam(cls):
    if cls == "augmentationDot":
        return "dot"
    if cls.startswith("flag"):
        return "flag"
    if cls.startswith("rest"):
        return "rest"
    if cls in ("noteheadBlackOnLine", "noteheadBlackInSpace"):
        return "blackhead"
    return "other"


def hits(S, box, sp, top, bot):
    bb = S["bbox"]
    if S["region"]:
        cx = (bb[0] + bb[2]) / 2
        bx, by = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        return abs(bx - cx) < 0.9 * sp and top - 1.5 * sp <= by <= bot + 1.5 * sp
    return iou(bb, box) > 0.3


out = []


def P(*a):
    s = " ".join(str(x) for x in a)
    out.append(s)
    print(s)


for plate, name in (("lit", "Litolff"), ("bra", "Brahms")):
    f = D / ("%s_v1.json" % plate)
    if not f.exists():
        continue
    V1 = json.load(open(f))
    rr = json.load(open(ROOT / ("probe/2.167d/data/%s_rerun.json" % plate)))
    P("\n=== %s: %d bars" % (name, len(V1)))
    # control 1
    rn = sum(v.get("rec_n", 0) for v in V1.values())
    rm = sum(v.get("rec_match", 0) for v in V1.values())
    P("CONTROL record boxes reproduced by the production call (class, conf within 0.01, IoU>0.8): %d of %d" % (rm, rn))
    pf = D / ("%s_v1_perturb.json" % plate)
    if pf.exists() and plate == "lit":
        PV = json.load(open(pf))
        P("CONTROL it can fail: imgsz +32 on the first %d bars reproduces %d of %d" % (len(PV), sum(v["rec_match"] for v in PV.values()),
                                                                                 sum(v["rec_n"] for v in PV.values())))
    # cost
    tp = sum(v["t_prod"] for v in V1.values() if "t_prod" in v)
    for var in VARS:
        tv = sum(v["variants"][var]["t"] for v in V1.values() if "variants" in v and var in v["variants"])
        calls = sum(v["variants"][var].get("calls", 0) for v in V1.values() if "variants" in v and var in v["variants"])
        P("  time %s: production %.1f s, views %.1f s -> multiplier %.2fx on the detector call (%d view calls, each a batch of %s phases)" % (
            var, tp, tv, 1 + tv / tp, calls, {"full": 3, "noaa": 3, "nophase": 1, "bare": 1}[var]))
    subs = SUB[plate]["subjects"]
    lost = [s for s in subs if s["role"] == "lost" and s["want"] and s["cause"] in ("A", "B", "C")]
    lostD = [s for s in subs if s["role"] == "lost" and s["want"] and s["cause"] == "D"]
    kept = [s for s in subs if s["role"] == "kept"]
    P("lost A/B/C located: %d (%s); D (a later gate): %d; kept: %d" % (
        len(lost), dict(collections.Counter((s["cause"], s["want"]) for s in lost)), len(lostD), len(kept)))
    for var in VARS:
        c = collections.Counter()
        tot = collections.Counter()
        wrongfam = 0
        refus = collections.Counter()
        for s in lost:
            R = V1.get(s["key"])
            if not R or "variants" not in R or var not in R["variants"]:
                continue
            r = rr[s["key"]]
            sp, top, bot = r["spacing"], r["lines"][0], r["lines"][4]
            tot[s["want"]] += 1
            kk = [b for b in R["variants"][var].get("kept", []) if hits(s, b["box"], sp, top, bot)]
            if any(b["fam"] == s["want"] for b in kk):
                c[s["want"]] += 1
            elif kk:
                wrongfam += 1
            else:
                rf = [b for b in R["variants"][var].get("refused", []) if hits(s, b["box"], sp, top, bot) and b["fam"] == s["want"]]
                if rf:
                    refus[rf[0]["why"]] += 1
        P("  [%s] lost A/B/C found in the right family: %d of %d  by family %s ; a kept box of ANOTHER family on it: %d ; refused by the merge: %s" % (
            var, sum(c.values()), sum(tot.values()), {k: "%d/%d" % (c[k], tot[k]) for k in tot}, wrongfam, dict(refus)))
        # by cause
        cc = collections.Counter()
        ct = collections.Counter()
        for s in lost:
            R = V1.get(s["key"])
            if not R or "variants" not in R or var not in R["variants"]:
                continue
            r = rr[s["key"]]
            sp, top, bot = r["spacing"], r["lines"][0], r["lines"][4]
            ct[s["cause"]] += 1
            if any(b["fam"] == s["want"] and hits(s, b["box"], sp, top, bot) for b in R["variants"][var].get("kept", [])):
                cc[s["cause"]] += 1
        P("         by cause: %s" % {k: "%d/%d" % (cc[k], ct[k]) for k in sorted(ct)})
    # (c) kept symbols
    nk = nc = 0
    for s in kept:
        R = V1.get(s["key"])
        if not R:
            continue
        r = rr[s["key"]]
        sp, top, bot = r["spacing"], r["lines"][0], r["lines"][4]
        nk += 1
        if any(fam(b[0]) == s["want"] and hits(s, b[2:6], sp, top, bot) for b in R["prod"]):
            nc += 1
    P("(c) kept symbols n=%d, still carried by an untouched production box after the merge: %d (merge removes/changes no production box by construction; "
      "the production list is read BEFORE the views run and is not passed back)" % (nk, nc))
    # (d) new boxes
    for var in VARS:
        cnt = collections.Counter()
        refc = collections.Counter()
        for k, R in V1.items():
            if "variants" not in R or var not in R["variants"]:
                continue
            for b in R["variants"][var].get("kept", []):
                cnt[(b["view"], b["fam"])] += 1
            for b in R["variants"][var].get("refused", []):
                refc[b["why"]] += 1
        P("  [%s] new boxes kept in %d bars: %s ; refused by the merge %s" % (var, len(V1), dict(sorted(cnt.items())), dict(refc)))
    # new boxes on the subjects of each role
    full_new = []
    for k, R in V1.items():
        if "variants" in R and "full" in R["variants"]:
            for b in R["variants"]["full"].get("kept", []):
                full_new.append((k, b))
    onlost = 0
    for k, b in full_new:
        r = rr[k]
        sp, top, bot = r["spacing"], r["lines"][0], r["lines"][4]
        if any(s["key"] == k and s["want"] == b["fam"] and hits(s, b["box"], sp, top, bot) for s in lost):
            onlost += 1
    P("  [full] of %d new boxes, %d sit on a located lost A/B/C symbol of the same family; %d do not (to be judged on crops)" % (
        len(full_new), onlost, len(full_new) - onlost))
open(D / "analysis.txt", "w").write("\n".join(out) + "\n")
