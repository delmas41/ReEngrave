"""Nested/stacked arc pairs on ONE staff and ONE side of the heads: arcs whose
x-spans overlap by >= 80% of the shorter and that share at least one end
(within a head width), boxes disjoint in y, gap <= 3 spaces, owner DECIDED the
same staff for both, not refused, and heads of that staff standing UNDER the
shorter arc's span (so the side is measured against its own notes).

usage: nested.py record.json [--list]
"""
import collections
import json
import sys

from tools.omr.staged import record_io

rec = record_io.load_record(sys.argv[1])["record"]
obs = rec["observations"]
ver = {}
for v in rec["verdicts"]:
    if v["quantity"] in ("arc_is_not_an_arc", "arc_owner", "arc_kind"):
        ver[(v["quantity"], v["subject"])] = v

heads = collections.defaultdict(list)
for o in obs:
    if o["quantity"] != "glyph_box":
        continue
    d = o["detail"] or {}
    if d.get("category") != "notehead":
        continue
    pb = d.get("bbox_page_px")
    if not pb:
        continue
    p = o["subject"].split("/")
    heads["staff/%s/%s/%s" % (p[1], p[2], p[3])].append(
        ((pb[0] + pb[2]) / 2, (pb[1] + pb[3]) / 2, pb[2] - pb[0], pb[3] - pb[1]))

arcs = []
for o in obs:
    if o["quantity"] != "arc_box":
        continue
    sub = o["subject"]
    nv = ver.get(("arc_is_not_an_arc", sub))
    if nv and nv["outcome"] == "decided" and nv["value"] is True:
        continue
    pb = (o["detail"] or {}).get("bbox_page_px")
    ow = ver.get(("arc_owner", sub))
    if not pb or not (ow and ow["outcome"] == "decided" and isinstance(ow.get("value"), str) and ow["value"]):
        continue
    kv = ver.get(("arc_kind", sub))
    arcs.append(dict(sub=sub, box=pb, staff=ow["value"], det=o["value"],
                     kind=(kv["value"] if kv and kv["outcome"] == "decided" else None)))
by = collections.defaultdict(list)
for a in arcs:
    by[a["staff"]].append(a)
out = []
for staff, L in by.items():
    hs = heads.get(staff, [])
    if not hs:
        continue
    w = sum(h[2] for h in hs) / len(hs)
    h_ = sum(h[3] for h in hs) / len(hs)
    for i, a in enumerate(L):
        for b in L[i + 1:]:
            ax0, ay0, ax1, ay1 = a["box"]
            bx0, by0, bx1, by1 = b["box"]
            ov = min(ax1, bx1) - max(ax0, bx0)
            sh = min(ax1 - ax0, bx1 - bx0)
            if sh <= 0 or ov / sh < 0.8:
                continue
            if min(abs(ax0 - bx0), abs(ax1 - bx1)) > w:
                continue
            gap = max(by0 - ay1, ay0 - by1)
            if gap <= 0 or gap / h_ > 3.0:
                continue
            sx0, sx1 = (ax0, ax1) if (ax1 - ax0) < (bx1 - bx0) else (bx0, bx1)
            under = [h for h in hs if sx0 - w <= h[0] <= sx1 + w
                     and min(ay0, by0) - 3 * h_ <= h[1] <= max(ay1, by1) + 3 * h_]
            if not under:
                continue
            hy = sorted(h[1] for h in under)[len(under) // 2]
            ca, cb = (ay0 + ay1) / 2, (by0 + by1) / 2
            side = "above" if (ca < hy and cb < hy) else "below" if (ca > hy and cb > hy) else "straddle"
            near, far = (a, b) if abs(ca - hy) < abs(cb - hy) else (b, a)
            out.append(dict(side=side, gap=round(gap / h_, 2), near=near, far=far, a=a, b=b,
                            nsame=(abs(ax0 - bx0) <= w and abs(ax1 - bx1) <= w)))
c = collections.Counter((o["side"], "near=" + str(o["near"]["det"]), "far=" + str(o["far"]["det"])) for o in out)
print("nested/stacked pairs on one staff:", len(out))
for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
    print("  ", k, v)
if "--list" in sys.argv:
    for o in out:
        if o["side"] == "straddle":
            continue
        print(o["side"], o["gap"], "same_ends" if o["nsame"] else "shared_one_end", "near", o["near"]["sub"], o["near"]["det"], "far", o["far"]["sub"], o["far"]["det"],
              [round(v) for v in o["near"]["box"]], [round(v) for v in o["far"]["box"]])
