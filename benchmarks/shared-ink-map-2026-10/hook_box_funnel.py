"""ROADMAP 2.202: why did the hook-as-flag path fire 0 times? Funnel of detector beam boxes (gathered ON record), per plate.
usage: hook_box_funnel.py ON.gathered.record.json
Counts, in order: boxes with a Q.GLYPH_STROKES row; boxes with a hook-role stroke under them and no beam-role one; of those, boxes whose x-range overlaps a
CV beam row (so `_kept_beams` drops them before the stroke map is asked); boxes whose hook touches a vertical stroke that touches no beam-role stroke."""
import collections
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged import beam_strokes as BS
from tools.omr.staged import record_io
from tools.omr.staged.record import STROKE_GLYPH_BASE

rec = record_io.load_record(sys.argv[1])["record"]
strokes = collections.defaultdict(dict)
gs, gb, cv, det = {}, {}, collections.defaultdict(list), []
for o in rec["observations"]:
    q, s = o["quantity"], o["subject"]
    if q == "stroke":
        p = s.split("/")
        d = o["detail"]
        strokes["/".join(p[1:5])][int(p[5]) - STROKE_GLYPH_BASE] = BS.StrokeView(
            int(p[5]) - STROKE_GLYPH_BASE, o["value"], tuple(d["stroke_box"]), d["length_spaces"], d["thickness_spaces"], d.get("sagitta_spaces"),
            d["angle_deg"], tuple((a, b) for a, b in d["touches"]), d["staff_space_local_px"])
    elif q == "glyph_strokes":
        gs[s] = o["value"]
    elif q == "glyph_box" and o["reader"] == "detector" and o["value"][0] == "beam":
        gb[s] = o["value"]
    elif q == "beam_stroke" and o["reader"] == "cv_lines":
        cv["/".join(s.split("/")[1:5])].append((o["detail"]["x0"], o["detail"]["x1"]))
c = collections.Counter()
for s, v in gb.items():
    cell = "/".join(s.split("/")[1:5])
    c["detector beam boxes"] += 1
    if s not in gs:
        continue
    c["with a Q.GLYPH_STROKES row"] += 1
    views = list(strokes[cell].values())
    role = BS.roles(views)
    sup = BS.box_support(gs[s], role)
    c["support=" + sup["support"]] += 1
    if sup["support"] != "hook":
        continue
    x0, x1 = v[1], v[1] + v[3]
    if any(a <= x1 and b >= x0 for a, b in cv[cell]):
        c["hook box overlapped by a CV beam row (dropped by _kept_beams before the stroke map is asked)"] += 1
        continue
    hooks = [h for h in sup["hooks"]]
    ok = False
    for h in hooks:
        for j in role[h]["stem_ordinals"]:
            stem = strokes[cell][j]
            if not any(role.get(t, {}).get("role") == "beam" for t, _ in stem.touches):
                ok = True
    c["hook on a stem that carries no spanning beam"] += ok
    c["hook only on beamed stems"] += (not ok)
for k, n in c.items():
    print("%6d  %s" % (n, k))
