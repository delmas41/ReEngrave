"""2.105 tile 6: beam strokes (Q.BEAM_STROKE) in the cell overlapping a head box.
usage: beamcover.py RECORD KEY [KEY...]"""
import sys

from tools.omr.staged.readout import load_run
from tools.omr.staged.record import Q

run = load_run(sys.argv[1])
for key in sys.argv[2:]:
    g = run.glyphs[key]
    cell = g.cell_key
    sp = None
    for o in run.observations:
        if o["subject"] == cell and o["quantity"] == Q.CELL_STAFF_SPACE:
            sp = float(o["value"])
    val = [o for o in run.observations if o["subject"] == key and o["quantity"] == Q.GLYPH_BOX][0]["value"]
    _, x, y, w, h = val
    print(key, g.cls, "canon w,h spaces", round(w / sp, 2), round(h / sp, 2), "box_page", [round(v) for v in g.box_page])
    for o in run.observations:
        if o["quantity"] == Q.BEAM_STROKE and o["subject"].startswith(cell.replace("cell/", "glyph/")) or \
                (o["quantity"] == Q.BEAM_STROKE and o["subject"] == cell):
            b = o["value"]
            if not isinstance(b, (list, tuple)) or len(b) != 4:
                continue
            ix = max(0, min(x + w, b[0] + b[2]) - max(x, b[0]))
            iy = max(0, min(y + h, b[1] + b[3]) - max(y, b[1]))
            cov = ix * iy / (w * h)
            if cov > 0:
                ink = [r for r in run.observations if r["quantity"] == Q.BEAM_STROKE_INK and (r.get("detail") or {}).get("beam_row_id") == o["id"]]
                print("   stroke", o["id"], "cover", round(cov, 2), "w,h sp", round(b[2] / sp, 2), round(b[3] / sp, 2),
                      "ink", {k: (ink[0]["detail"].get(k)) for k in ("thickness_ratio", "sagitta_spaces")} if ink else None)
