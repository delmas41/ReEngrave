"""2.170 step 2d: for every `beam_discounted_uncertain` head WITH an own CV stem, why the 2.146 clean-tip rule did not decide:
the tip's beam-run row (`beam_stem_levels`, runs per side at the tip end) and the flag window (`stem_tip_ink`, value or abstention
why). Own stem = a CV stem box overlapping the head box (canonical, zero tolerance, as `geometry.stem_touches_head`); tip end = the
end away from the head. usage: tips_2_170.py EX.json CELLS.json [OUT.json]"""
import json
import sys
from collections import Counter

ex = json.load(open(sys.argv[1]))
cells = json.load(open(sys.argv[2]))["rows"]


def overlap(a, b):
    return min(a[0] + a[2], b[0] + b[2]) > max(a[0], b[0]) and min(a[1] + a[3], b[1] + b[3]) > max(a[1], b[1])


t = Counter()
per = {}
for s, f in ex["narrowed"].items():
    if f["reason"] != "beam_discounted_uncertain":
        continue
    d = f["detail"] or {}
    ck = "cell/" + "/".join(s.split("/")[1:5])
    rows = cells.get(ck, [])
    g = next((o for o in rows if o["quantity"] == "glyph_box" and o["subject"] == s and o["_kind"] == "obs"), None)
    if g is None:
        t["no_glyph_box"] += 1
        continue
    hb = g["value"][1:5]
    stems = [o for o in rows if o["quantity"] == "stem" and o["_kind"] == "obs" and o.get("reader") == "cv_lines"
             and overlap(o["value"], hb)]
    if not d.get("stems_attached"):
        k = "NOSTEM"
        per[s] = dict(k=k)
        t[k] += 1
        continue
    if not stems:
        t["stem_attached_but_none_overlap"] += 1
        continue
    states = []
    for st in stems:
        x, y, w, h = st["value"]
        hyc = hb[1] + hb[3] / 2.0
        end = "top" if (y + h / 2.0) < hyc else "bottom"
        lv = [o for o in rows if o["quantity"] == "beam_stem_levels" and o["_kind"] == "obs"
              and (o.get("detail") or {}).get("stem_row_id") == st["id"]]
        runs = None
        if lv:
            e = ((lv[0]["detail"] or {}).get("ends") or {}).get(end) or {}
            runs = len(e.get("left") or []) + len(e.get("right") or [])
        ti = [o for o in rows if o["quantity"] == "stem_tip_ink" and (o.get("detail") or {}).get("stem_row_id") == st["id"]
              and (o.get("detail") or {}).get("end") == end]
        if not ti:
            tip = "no_tip_row"
        else:
            o = ti[0]
            if o["_kind"] == "abs":
                tip = "unread:" + str((o.get("detail") or {}).get("why"))
            elif (o.get("detail") or {}).get("tip_disagree"):
                tip = "disputed"
            else:
                tip = "hook" if o.get("value") else "clean"
        states.append((end, "runs:%s" % runs, tip))
    k = " | ".join(sorted({"%s %s" % (a[1], a[2]) for a in states}))
    per[s] = dict(k=k, states=states)
    t[k] += 1
tot = sum(t.values())
print("beam_discounted_uncertain heads:", tot)
for k, v in t.most_common(30):
    print(" %5d  %s" % (v, k))
if len(sys.argv) > 3:
    json.dump(per, open(sys.argv[3], "w"))
