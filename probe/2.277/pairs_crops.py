"""2.277: crops of merged head pairs by box IoU, both sides of the 0.5 line (OUR look).  usage: pairs_crops.py DUMP_ON.json OUTDIR [seed]"""
import collections, json, os, pathlib, random, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from tools.omr.staged import lane_report as LR

D = json.load(open(sys.argv[1]))
out = pathlib.Path(sys.argv[2])
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 7)
marks = {}
for c in D["cf"].values():
    marks.update(c.get("marks") or {})
R = {r["sub"]: r for r in D["rows"]}
bp = {}
for line in open(LR.slice_dir(D["plate"], D["tag"]) / "observations.jsonl"):
    if '"glyph_box"' in line[:300]:
        o = json.loads(line)
        if o["quantity"] == "glyph_box" and o["subject"] in marks:
            bp[o["subject"]] = o["detail"]["bbox_page_px"]
g = collections.defaultdict(list)
for k, m in marks.items():
    if k in R and k in bp:
        g[m].append(k)


def iou(a, b):
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def kept(k):
    return next(iter(R[k]["fate"].values()), [None])[0] is False


B = collections.defaultdict(list)
for m, ks in g.items():
    kp = [k for k in ks if kept(k)]
    if len(kp) < 2:
        continue
    a, b = kp[0], kp[1]
    v = iou(bp[a], bp[b])
    key = "0.0-0.2" if v < .2 else "0.2-0.35" if v < .35 else "0.35-0.5" if v < .5 else "0.5-0.7" if v < .7 else "0.7-0.9" if v >= .7 and v < .9 else "0.9+"
    B[key].append((a, b, round(v, 2)))
items = []
for key in ("0.0-0.2", "0.2-0.35", "0.35-0.5", "0.5-0.7", "0.7-0.9", "0.9+"):
    v = B.get(key, [])
    print(key, len(v))
    for a, b, x in rng.sample(v, min(4, len(v))):
        u = [min(bp[a][0], bp[b][0]), min(bp[a][1], bp[b][1]), max(bp[a][2], bp[b][2]), max(bp[a][3], bp[b][3])]
        items.append(dict(plate=D["plate"], page=int(a.split("/")[1]), box=u, role="case", pair=[a, b], iou=x, bucket=key))
print(LR.cut_tiles(items, out))
for n, it in enumerate(items, 1):
    print(n, it["bucket"], it["iou"])
