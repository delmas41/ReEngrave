"""2.192 cause census: every accidental box vs the rest boxes on the same page (from a 2.185 extract: boxes + verdicts).
usage: cause.py EXTRACT.json  -> counts by (accidental class, rest overlap, rest source, standing verdicts). Read-only."""
import json, sys, collections
d = json.load(open(sys.argv[1])); B = d["boxes"]
def inter(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]); return max(0, x1 - x0) * max(0, y1 - y0)
area = lambda a: (a[2] - a[0]) * (a[3] - a[1])
pg = lambda b: int(b["subject"].split("/")[1])
cell = lambda b: tuple(b["subject"].split("/")[1:5])
rests = collections.defaultdict(list)
for b in B:
    if b["cat"] == "rest" and b["bbox"]: rests[pg(b)].append(b)
vs = collections.defaultdict(list)
sup = {v["supersedes"] for v in d["verdicts"] if v.get("supersedes")}
for v in d["verdicts"]:
    if v["id"] not in sup: vs[v["subject"]].append(v)
def stand(sub, q):
    for v in vs[sub]:
        if v["quantity"] == q: return (v["outcome"], v["value"])
    return None
out = collections.Counter(); hist = collections.Counter(); rows = []
for a in B:
    if a["cat"] != "accidental" or not a["cls"].startswith("accidental") or not a["bbox"]: continue
    best = (0.0, 0.0, None)
    for r in rests[pg(a)]:
        i = inter(a["bbox"], r["bbox"]); iou = i / (area(a["bbox"]) + area(r["bbox"]) - i) if i else 0
        if iou > best[0]: best = (iou, i / area(a["bbox"]), r)
    iou, cont, r = best
    key = (a["cls"], "iou>=.5" if iou >= .5 else "iou.3-.5" if iou >= .3 else "iou.1-.3" if iou >= .1 else "none")
    if r is not None and iou >= .3:
        key += ("rest=" + r["cls"], "rest_src=" + str(r["source"] or r["reader"]), "same_cell=%s" % (cell(a) == cell(r)),
                "rest_kept=%s" % (stand(r["subject"], "rest_is_not_a_rest"),))
    out[key] += 1
    rows.append(dict(acc=a["subject"], cls=a["cls"], score=a["score"], bbox=a["bbox"], iou=round(iou, 3), rest=r and r["subject"] if iou >= .1 else None,
                     rest_cls=r and r["cls"], rest_score=r and r["score"], rest_bbox=r and r["bbox"], rest_src=r and (r["source"] or r["reader"])))
for k, v in sorted(out.items(), key=lambda x: (x[0][0], -x[1])): print("%6d" % v, k)
json.dump(rows, open(sys.argv[2], "w")) if len(sys.argv) > 2 else None
