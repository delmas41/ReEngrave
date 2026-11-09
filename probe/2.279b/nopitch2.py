"""2.279b: why no pitch for heads of a DECIDED-clef staff: position values, `_pitch_from_position`, clef-change claims on the staff.
usage: nopitch2.py RECORD NOPITCH.json STAFF [STAFF..]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.record_io import load_record      # noqa: E402
from tools.omr.staged.record import Q                    # noqa: E402
from tools.omr.staged.export import Record               # noqa: E402
from tools.omr.pitch_resolver import _pitch_from_position  # noqa: E402
from tools.omr.staged import clef_pagewide as CP         # noqa: E402

rec = Record(load_record(sys.argv[1]))
rows = json.load(open(sys.argv[2]))
print("OMR_CLEF_CARRY enabled:", CP.carry_enabled())
for st in sys.argv[3:]:
    cl = rec.verdict(Q.CLEF, st)
    print("==", st, cl["outcome"], cl["value"], cl.get("decider"))
    claims = [o for o in rec.obs(Q.CLAIMED_AREA, st) or []]
    print("  claimed_area rows on staff:", [(o.get("value"), (o.get("detail") or {}).get("source"), (o.get("detail") or {}).get("kind")) for o in claims][:6])
    for r in rows:
        if r["staff"] != st:
            continue
        o = rec.obs(Q.NOTEHEAD_STAFF_POSITION, r["sub"])
        pos = [x["value"] for x in o]
        far = rec.verdict(Q.NOTEHEAD_POSITION, r["sub"])
        npv = rec.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, r["sub"])
        pv = [_pitch_from_position(int(round(float(p))), str(cl["value"])) for p in pos]
        print("  ", r["sub"], "pos", pos, "far", (far or {}).get("outcome"), (far or {}).get("value"), "->", pv,
              "nan", (npv or {}).get("outcome"), (npv or {}).get("value"))

print("---- clef_pagewide claim rows per staff (obs = changes, abs = candidates)")
for st in sys.argv[3:]:
    for tag, src in (("obs", rec.observations), ("abs", rec.abstentions)):
        for o in src:
            if o.get("quantity") != Q.CLAIMED_AREA or not (o.get("subject") or "").startswith(st):
                continue
            d = o.get("detail") or {}
            if d.get("source") != CP.SOURCE:
                continue
            print(st, tag, o.get("subject"), o.get("value"),
                  {k: d.get(k) for k in ("change", "kind", "candidate", "strong", "family", "x_page", "weak")})

print("---- in force at each no_pitch head")
from tools.omr.staged import lane_report as LR
boxes = LR.glyph_boxes(rec.obs_of(Q.GLYPH_BOX))
import collections
for st in sys.argv[3:]:
    ch = []
    for o in rec.observations:
        d = o.get("detail") or {}
        if o.get("quantity") == Q.CLAIMED_AREA and (o.get("subject") or "") == st and d.get("source") == CP.SOURCE and d.get("change"):
            ch.append((float(o["value"][0]), d.get("kind"), o))
    ch.sort(key=lambda t: t[0])
    c = collections.Counter()
    for r in rows:
        if r["staff"] != st:
            continue
        x = (boxes[r["sub"]]["box"][0] + boxes[r["sub"]]["box"][2]) / 2
        f = CP.clef_in_force(x, ch, [], "bass")
        c[None if f is None else f[0]] += 1
    print(st, dict(c), "changes", [(round(x), k) for x, k, _ in ch])

print("---- the 7: x vs the weak F candidate at 2336")
st = "staff/4/1/3"
for r in rows:
    if r["staff"] == st:
        x = (boxes[r["sub"]]["box"][0] + boxes[r["sub"]]["box"][2]) / 2
        if x > 2167:
            print(r["sub"], round(x))
print("strong_stop_enabled:", CP.strong_stop_enabled())
