"""2.277 measure step: re-adjudicate a saved slice (flags as the environment says), dump a COMPACT per-box table.

usage: dump.py PLATE TAG OUT.json     (env flags apply: OMR_CLAIM_FINAL=0|1 ...)
One row per detector box: subject, cls, box, family, strokes [(ord, share)], partial, the verdicts' reasons per precision quantity.
One row per stroke: ink px, owner state/family.  READ-ONLY w.r.t. the record on disk.
"""
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")

from tools.omr.staged import lane_report as LR            # noqa: E402
from tools.omr.staged.review import rerun as RR           # noqa: E402
from tools.omr.staged.record import STROKE_GLYPH_BASE     # noqa: E402

plate, tag, out = sys.argv[1:4]
t0 = time.time()
rec = LR.load_slices(LR.slice_dir(plate, tag))
rec["verdicts"] = []
log, _ = RR.rebuild_gather(rec)
del rec
RR.run_stages(log)
res = log.to_json()
print("stages done %.0fs" % (time.time() - t0), flush=True)
obs, vs = res["observations"], res["verdicts"]

PRECISION = ("notehead_is_not_a_notehead", "rest_is_not_a_rest", "accidental_is_not_an_accidental", "ledger_is_not_a_ledger",
             "dynamic_is_not_a_dynamic", "articulation_is_not_an_articulation", "flag_is_not_a_flag", "arc_is_not_an_arc",
             "arpeggiato_is_not_an_arpeggiato", "keysig_marker_is_not_a_marker", "tuplet_marker_is_not_a_marker")
boxes, gs, strokes = {}, {}, {}
for o in obs:
    q = o["quantity"]
    if q == "glyph_box":
        boxes[o["subject"]] = o
    elif q == "glyph_strokes":
        gs[o["subject"]] = o
    elif q == "stroke":
        g = int(o["subject"].rsplit("/", 1)[1])
        if STROKE_GLYPH_BASE <= g < 400000:
            d = o["detail"]
            b = d.get("stroke_box") or [0, 0, 0, 0]
            strokes[(o["subject"].rsplit("/", 1)[0], g - STROKE_GLYPH_BASE)] = (round(float(d.get("fill") or 0) * b[2] * b[3], 1), o["value"])
fate, owner, cfs, owns_by_cell = {}, {}, {}, {}
for v in vs:
    q = v["quantity"]
    if q in PRECISION:
        fate.setdefault(v["subject"], {})[q] = [bool(v["value"]) if v["outcome"] == "decided" else None, v.get("reason"), v["outcome"]]
    elif q == "stroke_owner" and v["outcome"] == "decided":
        owner[v["subject"]] = (v.get("detail") or {}).get("strokes") or {}
        if (v.get("detail") or {}).get("claim_final"):
            cfs[v["subject"]] = v["detail"]["claim_final"]
        owns_by_cell[v["subject"]] = (v.get("detail") or {}).get("box_owns") or []
rows = []
for sub, b in boxes.items():
    g = gs.get(sub)
    cell = "cell/" + sub.split("/", 1)[1].rsplit("/", 1)[0]
    cs = cell
    st = []
    if g:
        sh = (g.get("detail") or {}).get("shares") or []
        for i, o in enumerate(g["value"] or []):
            st.append([int(o), float(sh[i]) if i < len(sh) else 1.0, 1])
        for o, s in (g.get("detail") or {}).get("partial") or []:
            st.append([int(o), float(s), 0])
    own = owner.get(cs, {})
    srows = []
    for o, s, cov in st:
        ink = strokes.get((cs.replace("cell/", "glyph/", 1), o))
        e = own.get(str(o))
        srows.append([o, s, cov, ink[0] if ink else None, ink[1] if ink else None, (e[0], e[1]) if e else None])
    rows.append({"sub": sub, "cls": b["value"][0], "box": b["value"][1:5], "reader": b.get("reader"), "cat": (b.get("detail") or {}).get("category"),
                 "score": b.get("score"), "strokes": srows, "fate": fate.get(sub, {})})
json.dump({"plate": plate, "tag": tag, "flags": {k: v for k, v in os.environ.items() if k.startswith("OMR_CLAIM")}, "rows": rows, "cf": cfs, "box_owns": owns_by_cell},
          open(out, "w"))
print("wrote", out, len(rows), "boxes %.0fs" % (time.time() - t0))
