"""2.251 carry: every clef* box on one staff (any size) and what step 1's second witness says of it.

python3 work-2.251/clefboxes.py PLATE BOXES.jsonl PG:SYS:STAFF ...
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
sys.path.insert(0, os.getcwd())
import crops  # noqa: E402
import scan_claims as SC  # noqa: E402
from tools.omr.staged import clef_pagewide as CP  # noqa: E402

plate, bpath = sys.argv[1], sys.argv[2]
boxes = SC.load_boxes(bpath)
for a in sys.argv[3:]:
    pg, s, li = (int(v) for v in a.split(":"))
    ink = SC.page_ink(plate, pg)
    for ss, l2, t, cells in SC.staves_of(plate, pg):
        if (ss, l2) != (s, li):
            continue
        lines = [float(v) for v in t["line_ys"]]
        sp = (lines[4] - lines[0]) / 4.0
        print("==", a, "sp %.1f lines" % sp, lines)
        for name, pb, sc, c, subj in sorted(boxes.get((pg, s, li), []), key=lambda b: b[1][0]):
            if not name.startswith("clef"):
                continue
            ll = CP.local_lines(ink, lines, sp, pb[0])
            got = CP.read_box(name, pb, ink, ll, sp)
            print("  c%d x=%d %s %.2f h=%.1fsp top-off=%.1fsp -> %s %s %s" % (c, pb[0], name, sc or 0, (pb[3] - pb[1]) / sp,
                  (pb[1] - lines[0]) / sp, got["passed"], got["why"], got["kind"]))
