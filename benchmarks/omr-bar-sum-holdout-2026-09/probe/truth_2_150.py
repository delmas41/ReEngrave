"""ROADMAP 2.150 -- every record rest box on Sean's hand-truth page (Brahms 317803 pdf 0) against his boxes.
usage: truth_2_150.py ROWS.json [OUT.json]   (ROWS from cache_2_150.py)
For each record rest box: the record's verdict and, from Sean's page, the label his boxes give that ink
(a Sean rest box overlapping >= 0.3 of the smaller box -> 'rest'; else the class of the Sean box covering most of it).
Also: every Sean rest box the record kept no rest on (a MISSED rest) and what the record holds there.
Who says it's right: Sean's boxes (the hand-truth page), never our own output."""
import json, sys, collections

ROWS = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else None
d = json.load(open(ROWS))
HT = json.load(open("data/hand-truth/pages/imslp317803/0.json"))
truth = []
for b in HT["boxes"]:
    x0, y0, x1, y1 = b["rect"]
    truth.append((b["cls"], (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), b["id"]))


def inter(a, b):
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    return ix * iy if ix > 0 and iy > 0 else 0.0


def area(a):
    return max(1e-9, (a[2] - a[0]) * (a[3] - a[1]))


def label(bb):
    """Sean's reading of this ink: ('rest', cls) if one of his rest boxes shares >= 0.3 of the smaller box,
    else the class of his box covering most of OUR box, else 'nothing'."""
    best_rest, best = None, None
    for cls, r, i in truth:
        ov = inter(bb, r)
        if not ov:
            continue
        if cls.startswith("rest") and ov / min(area(bb), area(r)) >= 0.3:
            if best_rest is None or ov > best_rest[0]:
                best_rest = (ov, cls, i)
        share = ov / area(bb)
        if best is None or share > best[0]:
            best = (share, cls, i)
    if best_rest:
        return "rest", best_rest[1], best_rest[2]
    if best and best[0] >= 0.2:
        return "not_rest", best[1], best[2]
    return "nothing", None, None


V = d["verdicts"]
rows = []
for s, cls in d["rest_rows"].items():
    if not s.startswith("glyph/0/"):
        continue
    b = d["boxes"].get(s)
    if not b or not b[3]:
        continue
    v = V.get(s, {}).get("rest_is_not_a_rest") or [None, None, None]
    du = V.get(s, {}).get("duration") or [None, None, None]
    t = label(b[3])
    rows.append(dict(glyph=s, cls=cls, score=round(b[1] or 0, 3), bbox=[round(x) for x in b[3]],
                     refused=v[1], reason=v[2], duration=du[:3], truth=t[0], truth_cls=t[1], truth_id=t[2]))
tab = collections.Counter((r["refused"], r["truth"], r["truth_cls"] if r["truth"] != "rest" else "rest") for r in rows)
print("record rest boxes on page 0:", len(rows))
for k, n in sorted(tab.items(), key=lambda x: (str(x[0][0]), -x[1])):
    print("  refused=%s  sean=%-9s %-22s %d" % (k[0], k[1], k[2], n))
kept = [r for r in rows if r["refused"] is False]
print("KEPT:", len(kept), "of which Sean rest:", sum(r["truth"] == "rest" for r in kept))
for r in kept:
    if r["truth"] != "rest":
        print("   kept-not-rest", r["glyph"], r["cls"], r["score"], r["bbox"], r["truth"], r["truth_cls"], r["duration"])
# Sean's rests: which did the record keep?
missed = []
for cls, rr, i in truth:
    if not cls.startswith("rest"):
        continue
    hit = [r for r in kept if inter(r["bbox"], rr) / min(area(r["bbox"]), area(rr)) >= 0.3]
    anyr = [r for r in rows if inter(r["bbox"], rr) / min(area(r["bbox"]), area(rr)) >= 0.3]
    if not hit:
        missed.append(dict(id=i, cls=cls, rect=[round(x) for x in rr],
                           record=[(r["glyph"], r["cls"], r["reason"]) for r in anyr]))
print("Sean rests:", sum(c.startswith("rest") for c, _, _ in truth), "not kept by the record:", len(missed))
for m in missed:
    print("   missed", m)
if OUT:
    json.dump(dict(rows=rows, missed=missed), open(OUT, "w"), indent=1)
