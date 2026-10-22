"""2.192: on the frozen-sample slices (2.190-built, with shapes), list every accidental box that contests a rest box (IoU >= .5, same cell) and what
the shape rule says. usage: sample_contest.py SLICEROOT OUT.json"""
import json, sys, collections
sys.path.insert(0, ".")
from tools.omr.staged import accidental_shape as AS, one_ink as OI
root, out = sys.argv[1:3]
res = []
for plate in ("litolff", "brahms"):
    obs = [json.loads(l) for l in open("%s/%s/observations.jsonl" % (root, plate))]
    vs = {}
    for l in open("%s/%s/verdicts.jsonl" % (root, plate)):
        v = json.loads(l)
        if v["quantity"] == "rest_is_not_a_rest": vs[v["subject"]] = v
    boxes = [o for o in obs if o["quantity"] == "glyph_box" and o["reader"] != "x" and isinstance(o["value"], list)]
    pos = {o["subject"]: o for o in obs if o["quantity"] == "accidental_staff_position"}
    cells = collections.defaultdict(list)
    for o in boxes: cells["/".join(o["subject"].split("/")[:5])].append(o)
    for c, bs in cells.items():
        rests = [b for b in bs if (b.get("detail") or {}).get("category") == "rest"]
        for a in bs:
            if (a.get("detail") or {}).get("category") != "accidental" or not a["value"][0].startswith("accidental"): continue
            for r in rests:
                v = vs.get(r["subject"])
                if v and v.get("value") is True: continue
                i = OI.iou(a["value"][1:5], r["value"][1:5])
                if i >= .5:
                    p = pos.get(a["subject"]); d = (p or {}).get("detail") or {}
                    sh = AS.classify(d["shape"] if isinstance(d.get("shape"), dict) and d["shape"].get("bl") is not None else None)
                    vd = AS.on_rest_verdict(d.get("detector_class") or a["value"][0], sh)
                    res.append(dict(plate=plate, acc=a["subject"], cls=a["value"][0], rest=r["subject"], rest_cls=r["value"][0], iou=round(i, 2),
                                    page=int(a["subject"].split("/")[1]), shape=sh["shape"], keep=vd["keep"], why=vd["why"], bl=d.get("shape", {}).get("bl"), tr=d.get("shape", {}).get("tr")))
json.dump(res, open(out, "w"), indent=1)
c = collections.Counter((r["plate"], r["cls"], r["rest_cls"], r["keep"], r["why"]) for r in res)
for k, v in sorted(c.items()): print(v, k)
