"""2.170 step 2e: first cause of every narrowed-beam head (both reasons), from the cell's own rows (canonical frame, 100 px = 1 space).
Own stem = a CV stem box overlapping the head box. Tip = the stem end away from the head. A stroke "is beam ink at THIS tip" when
its ink row reads it thick (thickness_ratio >= 1.75 lines, the reader's own cut) AND its x-span covers the stem's x AND its box
reaches within 0.5 space of the tip along the stem.
  A_dedup_dropped    : the only beam ink at this tip is a DETECTOR box that `_kept_beams` dropped because a CV stroke overlaps it in x
                       (the CV stroke stops short of this stem: the shattered beam)
  A_cv_short         : a CV stroke with beam ink lies within 2 spaces of this stem at the tip height but does not cover its x
                       (and no box covers it either)
  B_counted_refused  : beam ink at this tip exists and was in the count, but refused (why from the verdict)
  C_no_beam_at_tip   : nothing thick at this tip (no beam ink): the note is unbeamed or the beam is unread entirely
  NOSTEM             : no own CV stem
usage: causes_2_170.py EX.json CELLS.json OUT.json"""
import json
import sys
from collections import Counter

ex = json.load(open(sys.argv[1]))
cells = json.load(open(sys.argv[2]))["rows"]
THICK = 1.75


def ov(a, b):
    return min(a[0] + a[2], b[0] + b[2]) > max(a[0], b[0]) and min(a[1] + a[3], b[1] + b[3]) > max(a[1], b[1])


res = {}
t = Counter()
tr = Counter()
for s, f in ex["narrowed"].items():
    d = f["detail"] or {}
    ck = "cell/" + "/".join(s.split("/")[1:5])
    rows = cells.get(ck, [])
    g = next((o for o in rows if o["quantity"] == "glyph_box" and o["subject"] == s and o["_kind"] == "obs"), None)
    if g is None:
        continue
    hb = g["value"][1:5]
    stems = [o for o in rows if o["quantity"] == "stem" and o["_kind"] == "obs" and o.get("reader") == "cv_lines" and ov(o["value"], hb)]
    strokes = {o["id"]: o for o in rows if o["quantity"] == "beam_stroke" and o["_kind"] == "obs"}
    ink = {(o.get("detail") or {}).get("beam_row_id"): o for o in rows if o["quantity"] == "beam_stroke_ink" and o["_kind"] == "obs"}
    cv = [o for o in strokes.values() if o.get("reader") == "cv_lines"]
    refused = {r["id"]: r["why"] for r in d.get("refused_strokes") or []}
    if not stems:
        k = "NOSTEM"
    else:
        k = None
        for st in stems:
            x, y, w, h = st["value"]
            up = (y + h / 2.0) < hb[1] + hb[3] / 2.0
            tip = y if up else y + h
            hits = []
            near_cv = []
            for sid, o in strokes.items():
                bx, by, bw, bh = o["value"]
                r = ink.get(sid)
                thick = r is not None and ((r.get("detail") or {}).get("thickness_ratio") or 0) >= THICK
                if not thick:
                    continue
                reach = by - 50 <= tip <= by + bh + 50
                covers = bx <= x + w and bx + bw >= x
                if reach and covers:
                    hits.append(o)
                elif reach and o.get("reader") == "cv_lines" and min(abs(bx - (x + w)), abs(x - (bx + bw))) <= 200:
                    near_cv.append(o)
            if hits:
                cvh = [o for o in hits if o.get("reader") == "cv_lines"]
                det = [o for o in hits if o.get("reader") != "cv_lines"]
                if not cvh and det and all(any(c["value"][0] <= o["value"][0] + o["value"][2] and c["value"][0] + c["value"][2] >= o["value"][0]
                                               for c in cv) for o in det):
                    k = "A_dedup_dropped"
                else:
                    whys = sorted({refused.get(o["id"], "not_refused") for o in hits})
                    k = "B_counted:" + "+".join(whys)
                break
            if near_cv:
                k = "A_cv_short"
        if k is None:
            k = "C_no_beam_at_tip"
    res[s] = k
    t[(f["reason"], k.split(":")[0])] += 1
    tr[(f["reason"], k)] += 1
for kk, v in sorted(t.items(), key=lambda kv: -kv[1]):
    print(" %5d  %s" % (v, kk))
print()
for kk, v in tr.most_common(25):
    print(" %5d  %s" % (v, kk))
json.dump(res, open(sys.argv[3], "w"))
