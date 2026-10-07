import sys, json
sys.path.insert(0, '.')
import farhead_per_bar_grid_eval as E
import lines_combined_5_lib as D
from tools.omr.annotate import far_head_reader as FH, ledger_grid as lg
FH.EXCLUSION_RULES["jut_from_ink"] = True
S = "glyph/1/1/8/7/4"
fp, L, far, lf, _ = E.build("brahms1-breitkopf", 1, True)
FH.READER_KEYWORDS["edge_vs_through"] = True
h = [x for x in far if x["subject"] == S][0]
d = D.diagnose(fp, S, h["box"], h["cls"], lf(h))
lines = d["lines"]; box = d["box_used"]
x0, y0, x1, y1 = box
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
others = lg.exclusion_boxes_for(S, box, fp.nh, fp.acc, drop_same_ink_other_staff=FH.READER_KEYWORDS["drop_same_ink_other_staff"])
print("n others", len(others))
for name, kw in (("as reader", dict(head_box_x=(x0, x1), collapse_edges_box=(x0, y0, x1, y1))),
                 ("no head_box_x", dict(collapse_edges_box=(x0, y0, x1, y1))),
                 ("no collapse", dict(head_box_x=(x0, x1))),
                 ("neither", dict())):
    r = lg.measure_ledger_rungs(fp.gray, lines, cx, head_y=cy, exclude_boxes=others,
                                restore_masked_staff_side_rungs=FH.READER_KEYWORDS["restore_masked_near_edge"], **kw)
    print(name, [round(v, 1) for v in r["below"]])
# the OLD lines for comparison
old = [5976.0, 6001.5, 6029.0, 6056.0, 6083.5]
r = lg.measure_ledger_rungs(fp.gray, old, cx, head_y=cy, exclude_boxes=others, head_box_x=(x0, x1),
                            collapse_edges_box=(x0, y0, x1, y1),
                            restore_masked_staff_side_rungs=FH.READER_KEYWORDS["restore_masked_near_edge"])
print("old lines, new box", [round(v, 1) for v in r["below"]])
