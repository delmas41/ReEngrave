"""2.184: among rest inks the production detector keeps (>= 0.25), what differs between inks that sit as a different-class PAIR and singles.
Features from replay.py output only (no record). usage: features.py REPLAY.json  (prints median/rate tables)"""
import json, sys, collections, statistics as st
from tools.omr.staged.adjudicators.family_precision import REST_DUPLICATE_IOU_MIN as IOU
rp = json.load(open(sys.argv[1]))
def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0: return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i)
inks = []
for pg, rows in rp.items():
    bycell = collections.defaultdict(list)
    for r in rows:
        if not r["ag"] and r["conf"] >= 0.25: bycell[(pg,) + tuple(r["key"] or [])].append(r)
    for k, v in bycell.items():
        seen = set()
        for i, a in enumerate(v):
            if i in seen: continue
            grp = [j for j, b in enumerate(v) if j == i or iou(a["bbox"], b["bbox"]) >= IOU]
            seen |= set(grp)
            g = [v[j] for j in grp]
            top = max(g, key=lambda r: r["conf"])
            classes = {r["cls"] for r in g}
            sp = top["sp"]; b = top["bbox"]; c = top["cell"]
            inks.append(dict(page=pg, pair=len(classes) > 1, cls=top["cls"], classes=sorted(classes), conf=top["conf"], shown=top["shown_sp"],
                             h=(b[3]-b[1])/sp, w=(b[2]-b[0])/sp, ycen=((b[1]+b[3])/2 - top["staff_top"])/sp,
                             edge=min(b[0]-c[0], c[2]-b[2])/sp, cellw=(c[2]-c[0])/sp, imgsz=top["imgsz"]))
print(sys.argv[1].split("/")[-1], "inks", len(inks), "pairs", sum(i["pair"] for i in inks))
def tab(sel, label):
    P = [i for i in inks if i["pair"] and sel(i)]; S = [i for i in inks if not i["pair"] and sel(i)]
    print(f" {label}: pairs {len(P)} singles {len(S)}")
    for f in ("conf", "shown", "h", "w", "ycen", "edge", "cellw", "imgsz"):
        if P and S: print(f"   {f:6s} pair med {st.median(i[f] for i in P):7.2f}   single med {st.median(i[f] for i in S):7.2f}")
tab(lambda i: True, "all inks")
tab(lambda i: i["cls"] == "rest8th", "top class rest8th")
tab(lambda i: i["cls"] in ("rest8th","rest16th","restQuarter") and 1.3 < i["h"] < 2.6 and i["w"] < 1.5, "8th-rest-sized boxes (h 1.3-2.6 sp, w<1.5)")
# rate of pair by shown staff space bin and by edge
for f, bins in (("shown", [0,15,15.5,16,16.5,17,99]), ("edge", [0,1,2,4,8,99]), ("page", None)):
    print(" pair rate among 8th-rest-sized boxes by", f)
    sel = [i for i in inks if i["cls"] in ("rest8th","rest16th","restQuarter") and 1.3 < i["h"] < 2.6 and i["w"] < 1.5]
    if bins:
        for lo, hi in zip(bins, bins[1:]):
            v = [i for i in sel if lo <= i[f] < hi]
            if v: print(f"   [{lo},{hi}) n={len(v)} pair {100*sum(i['pair'] for i in v)/len(v):.1f}%")
    else:
        for pg in sorted({i["page"] for i in sel}, key=int):
            v = [i for i in sel if i["page"] == pg]; print(f"   page {pg} n={len(v)} pair {100*sum(i['pair'] for i in v)/len(v):.1f}%")
json.dump(inks, open(sys.argv[1].replace(".json", ".inks.json"), "w"))
