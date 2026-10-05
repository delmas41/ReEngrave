"""lane-offbox-check: for every truth-set reference the check FAILS, print how far the named line is from the box
(in staff spaces), the box height, and the spacing -- is it the row conversion or the box?

  python3 offbox_failing_refs.py <offbox.json>
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import offbox_check as C
import offbox_report as O

res = json.loads(Path(sys.argv[1]).read_text())
for doc, D in res.items():
    H = D["heads"]["RUN2"]
    M, miss = O.matched(D["truth"], H)
    for (h, s, g) in M:
        t = h["truth"][0]
        if C.passes(t, g["box"], g["lines"]):
            continue
        x0, y0, x1, y1 = g["box"]
        top, bot = min(g["lines"]), max(g["lines"])
        sp = (bot - top) / 4.0
        cy = (y0 + y1) / 2
        yl = C.row(g["lines"], t)
        glob_h = (y1 - y0) / sp
        row = dict(subject=s, ref=t, cls=g["cls"], box_source=g["box_source"], sp_px=round(sp, 1),
                   box_h_sp=round(glob_h, 2), box_w_sp=round((x1 - x0) / sp, 2),
                   line_minus_centre_sp=round((yl - cy) / sp, 2),
                   line_minus_top_edge_sp=round((yl - y0) / sp, 2), line_minus_bottom_edge_sp=round((yl - y1) / sp, 2),
                   local=g["local"], reader=g["dec"], geo=g["geo"])
        print(row)
