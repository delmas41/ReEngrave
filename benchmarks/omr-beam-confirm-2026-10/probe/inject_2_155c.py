"""ROADMAP 2.155 continue-a-level -- replay 2.155b tile 13's cell (Litolff cell/6/1/9/9) under the new beam rule, NO page gather.

`cells_2_155c.py` shows the new rule changes this cell only by ONE added CV stroke. This builds the rows the gather would file for
it with the gather's own code (`gather_cv_lines` + `gather_beam_stroke_ink` on the prepared cell, detector boxes from the record,
into a scratch log), keeps the rows that belong to the NEW stroke (its `Q.BEAM_STROKE`, its `Q.BEAM_STEM_JOIN` rows -- stem ids
mapped to the record's own stem rows by box -- and its `Q.BEAM_STROKE_INK`), injects them into a slice of system (6,1) of the
tightened record (t2_litolff_tight_def), and replays the slice (`replay_util_2_153.rebuild` + `rerun.run_stages`) in the env the
caller sets. CONTROL: the same slice replayed WITHOUT the injection must give the record's stored reading for every glyph of the cell.
usage: inject_2_155c.py OUT.json     (env: OMR_STEM_AT_BAR_EDGE=1, optionally OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM=1)"""
import copy
import json
import sys
from types import SimpleNamespace

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
sys.path.insert(0, "benchmarks/omr-beam-confirm-2026-10/probe")
from replay_util_2_153 import rebuild  # noqa: E402
from score_2_155 import load, reading  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.pipeline import prepare_pages  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")
CELL, NEW = "cell/6/1/9/9", (763, 597, 254, 26)
rec = load("out/2.155/t2_litolff_tight_def.record.json")


def in_sys(s):
    p = s.split("/")
    return not (len(p) >= 3 and p[1].lstrip("-").isdigit() and p[2].lstrip("-").isdigit()) or (p[1], p[2]) == ("6", "1")


sl = {k: [x for x in rec[k] if in_sys(x["subject"])] for k in ("observations", "abstentions")}
sl["verdicts"] = [v for v in rec["verdicts"] if in_sys(v["subject"])]
sl0 = copy.deepcopy(sl)

# the gather's own rows for the cell, at the current code
(pws, cells), = prepare_pages(PDF, [6])
cb = next(o["value"] for o in rec["observations"] if o["subject"] == CELL and o["quantity"] == "cell_box")
c = next(x for x in cells if tuple(float(v) for v in x.bbox_page_px) == tuple(float(v) for v in cb))
sub = R.cell(6, 1, 9, 9)
rows = sorted((int(o["subject"].split("/")[5]), o["value"]) for o in rec["observations"]
              if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/6/1/9/9/"))
dets = [SimpleNamespace(smufl_name=v[0], x_canonical=v[1], y_canonical=v[2], width_canonical=v[3], height_canonical=v[4],
                        x_center=v[1] + v[3] / 2.0, y_center=v[2] + v[4] / 2.0) for _i, v in rows]
scratch = R.Log()
G.gather_cv_lines(scratch, [c], {c.staff_index: (1, 9)}, detections={sub.to_key(): dets})
G.gather_beam_stroke_ink(scratch, [c], {c.staff_index: (1, 9)})
sj = scratch.to_json()
stems_rec = {tuple(o["value"]): o["id"] for o in sl["observations"] if o["subject"] == CELL and o["quantity"] == "stem"}
stems_new = {o["id"]: tuple(o["value"]) for o in sj["observations"] if o["quantity"] == "stem"}
assert set(stems_new.values()) == set(stems_rec), (stems_new, stems_rec)    # the stems are the record's own
# REPLACE the cell's CV strokes (and every row keyed to one of them) with the gather's own rows at the current code
old_cv = {o["id"] for o in sl["observations"] if o["subject"] == CELL and o["quantity"] == "beam_stroke" and o["reader"] == "cv_lines"}
for kind in ("observations", "abstentions"):
    sl[kind] = [o for o in sl[kind] if o["id"] not in old_cv and (o.get("detail") or {}).get("beam_row_id") not in old_cv]
new_cv = {o["id"] for o in sj["observations"] if o["quantity"] == "beam_stroke" and o["reader"] == "cv_lines"}
print("CV strokes: record", sorted(tuple(o["value"]) for o in rec["observations"] if o["id"] in old_cv),
      "-> now", sorted(tuple(o["value"]) for o in sj["observations"] if o["id"] in new_cv))
top = max(int(x["id"].split(":")[1]) for k in ("observations", "abstentions") for x in sl[k])
idmap, inject, k = {}, [], top + 1
for o in sj["observations"]:
    if o["id"] in new_cv:
        idmap[o["id"]] = "obs:%06d" % k
        k += 1
for kind in ("observations", "abstentions"):
    for o in sj[kind]:
        d = o.get("detail") or {}
        if o["id"] in new_cv:
            o = copy.deepcopy(o)
            o["id"] = idmap[o["id"]]
        elif d.get("beam_row_id") in new_cv:
            o = copy.deepcopy(o)
            o["id"] = "%s:%06d" % (o["id"].split(":")[0], k)
            k += 1
            o["detail"]["beam_row_id"] = idmap[d["beam_row_id"]]
            if "stem_row_id" in o["detail"]:
                o["detail"]["stem_row_id"] = stems_rec[stems_new[o["detail"]["stem_row_id"]]]
        else:
            continue
        o["basis"] = []
        inject.append((kind, o))
print("injected", [(kind, o["quantity"], o.get("value"), (o.get("detail") or {}).get("end")) for kind, o in inject])

glyphs = sorted({o["subject"] for o in sl["observations"] if o["subject"].startswith("glyph/6/1/9/9/") and o["quantity"] == "glyph_box"})
res = {}
for arm in ("control", "injected"):
    s2 = copy.deepcopy(sl)
    if arm == "control":
        s2 = copy.deepcopy(sl0)
    else:
        for kind, o in inject:
            s2[kind].append(o)
    log, _ = rebuild(s2)
    RR.run_stages(log)
    out = log.to_json()
    res[arm] = {g: reading(out, g) for g in glyphs}
stored = {g: reading(rec, g) for g in glyphs}
for g in glyphs:
    f = lambda r: r.get("written") if r["outcome"] == "decided" else (r["outcome"], r.get("cands"))  # noqa: E731
    print(g, stored[g].get("cls"), "| stored", f(stored[g]), "| control", f(res["control"][g]), "| injected", f(res["injected"][g]))
ctl_ok = all((stored[g]["outcome"], stored[g].get("written")) == (res["control"][g]["outcome"], res["control"][g].get("written"))
             for g in glyphs)
print("CONTROL faithful:", ctl_ok)
json.dump(dict(stored=stored, res=res, control_faithful=ctl_ok), open(sys.argv[1], "w"), indent=1, default=str)
