"""ROADMAP 2.190: for every merged accidental ink on the sample pages (slices built by build_slices_2_190.py), the detector's class pair against what the
shape reader says (a second reader of the same raster -- NOT truth), by pair kind. usage: table_2_190.py SLICEROOT"""
import collections, json, sys
from tools.omr.staged import accidental_shape as AS
root = sys.argv[1]
for plate in ("litolff", "brahms"):
    t = collections.defaultdict(collections.Counter); sing = collections.defaultdict(collections.Counter)
    for l in open("%s/%s/observations.jsonl" % (root, plate)):
        o = json.loads(l)
        if o["quantity"] != "accidental_staff_position": continue
        d = o["detail"]; sh = d.get("shape")
        if sh is None: continue
        s = AS.classify(sh if sh.get("bl") is not None else None)["shape"]
        oi = d.get("one_ink")
        if not oi:
            sing[d["detector_class"][8:]][s] += 1; continue
        cands = [oi["winner"]["class"]] + [r["class"] for r in oi["rivals"]]
        kind = "%s over %s" % (oi["winner"]["class"][8:], "/".join(sorted(r["class"][8:] for r in oi["rivals"])))
        pick = AS.choose(cands, {"shape": s})
        res = "unclear/unread" if s in ("unclear", "unread") else "agrees with winner" if pick["pick"] == oi["winner"]["class"] else \
              "names a RIVAL (switch)" if pick["pick"] else "names neither (not offered)"
        t[kind][res] += 1
    print("==", plate)
    tot = collections.Counter()
    for k, c in sorted(t.items(), key=lambda kv: -sum(kv[1].values())):
        print("  %-34s n=%3d  %s" % (k, sum(c.values()), dict(c))); tot.update(c)
    print("  ALL merged n=%d %s" % (sum(tot.values()), dict(tot)))
    print("  single boxes (class -> shape): %s" % {k: dict(v) for k, v in sing.items()})
