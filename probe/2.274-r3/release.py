"""What if the `continues_in_another_curve` abstention were not made?  (measure only; no pipeline code changed)
For every end_unbound abstention of ON whose ONLY unbound ends are `continues_in_another_curve`, take the head the binder itself named as the candidate for that end (the closest one) and
ask, against Sean's hand boxes: is that head at the printed arc's end?  Per printed arc (the one whose run this is), with the same tolerance as the audited scorer (2.5 sp; past an open cell edge anything).
Also: how far is the candidate head from the run's own end (`core_ends`), in spaces -- a half arc cut in two ends in mid-air, two arcs meeting at a note end AT the head."""
import json
import collections
from load import *  # noqa

C = json.load(open("buckets.json"))
rec = record("on")
bind = {e["ordinal"]: e for e in [v for v in rec["verdicts"] if v["quantity"] == "page_arc_binding"][0]["detail"]["runs"]}
runs = {o["detail"]["ordinal"]: o["detail"] for o in rec["observations"] if o["quantity"] == "page_arc" and o["value"] == "run"}
gb = {o["subject"]: ((o["detail"]["bbox_page_px"][0] + o["detail"]["bbox_page_px"][2]) / 2, (o["detail"]["bbox_page_px"][1] + o["detail"]["bbox_page_px"][3]) / 2)
      for o in rec["observations"] if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/0/")}
tot = collections.Counter()
rows = []
for e in bind.values():
    if e["status"] != "abstained" or e.get("why") != "end_unbound":
        continue
    un = e.get("unbound") or {}
    if not all((u or {}).get("unbound") == "continues_in_another_curve" for u in un.values()):
        tot["other unbound reason"] += 1
        continue
    r = runs[e["ordinal"]]
    ce = r.get("core_ends") or [r["points"][0], r["points"][-1]]
    ends = {}
    for side, pt in (("left", ce[0]), ("right", ce[1])):
        s = e.get(side) or {}
        key = s.get("head") or (s.get("candidates") or [None])[0]
        ends[side] = (key, pt)
    rows.append((e["ordinal"], ends, sorted(un.keys())))
    tot["runs released"] += 1
print(dict(tot))
res = collections.Counter()
for c in C:
    for e in c["bind"][:1]:
        pass
for ordv, ends, sides in rows:
    # the printed arcs this run lies on (census)
    for c in C:
        if not any(r["ordinal"] == ordv for r in c["runs"][:1]):
            continue
        kl, pl = ends["left"]
        kr, pr = ends["right"]
        if kl not in gb or kr not in gb:
            res["no head"] += 1
            continue
        dl, dr = (gb[kl][0] - c["x0"]) / SP, (gb[kr][0] - c["x1"]) / SP
        okl = abs(dl) <= REACH or (c["open_L"] and dl < 0)
        okr = abs(dr) <= REACH or (c["open_R"] and dr > 0)
        dist = [round(abs(gb[k][0] - p[0]) / SP, 1) for k, p in ((kl, pl), (kr, pr))]
        ok = okl and okr
        cur = c["bucket_on"]
        res[("would be right" if ok else "would be wrong", "now " + cur)] += 1
        rows_c = (c["n"], c["staff"], c["kind"], "released ends %+.1f / %+.1f sp" % (dl, dr), "end->head dist %s" % dist, "RIGHT" if ok else "wrong", "now bucket " + cur, "OFF " + c["bucket_off"])
        print(*rows_c)
for k, v in sorted(res.items(), key=lambda t: str(t)):
    print(v, k)
