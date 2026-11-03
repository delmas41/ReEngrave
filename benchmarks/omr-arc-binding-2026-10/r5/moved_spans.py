"""Every head the hole moved (ON gather): its hole read again on the PAGE raster with local lines; pieces, cut, span.
args: plate ON.record out.json"""
import sys, json
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a8ed964f5bc0cc9cf")
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a8ed964f5bc0cc9cf/out/2.252r5")
from tools.omr.staged.record_io import load_record
import holes_page as HP
plate = sys.argv[1]
r = load_record(sys.argv[2]); r = r.get("record", r)
boxes, moved = {}, {}
for o in r["observations"]:
    if o["quantity"] == "glyph_box":
        boxes[o["subject"]] = (o.get("detail") or {}).get("bbox_page_px")
    elif o["quantity"] == "notehead_staff_position":
        d = o.get("detail") or {}
        if "from_head_hole" in d:
            moved[o["subject"]] = (d.get("detector_position_float"), float(o["value"]))
del r
out = []
for g, (pb, ph) in sorted(moved.items()):
    b = boxes.get(g)
    if not b:
        continue
    pg = int(g.split("/")[1])
    cy = (b[1] + b[3]) / 2
    hint = cy - pb * 7.87
    try:
        res = HP.run(plate, pg, b, 0.25, hint)
    except Exception as e:  # noqa
        res = {"err": str(e)}
    out.append(dict(g=g, box_pos=pb, hole_pos=ph, page=res))
    print(g, pb, "->", ph, res.get("holes"), res.get("ink_pos"))
json.dump(out, open(sys.argv[3], "w"), default=str)
