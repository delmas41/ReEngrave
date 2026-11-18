"""ROADMAP 2.312 r2 -- cut the REAL page pixels of Sean's judged 2.311 ledger tiles into the fast-tier fixture
`tools/omr/tests/data_ledger_count_to_ink_2_312.npz` (CLAUDE rule 7: a control for a page rule is built from a real judged case).

    PYTHONPATH=. python3 benchmarks/ledger-count-2026-11/r2_fixture.py OFF_REREAD.json

OFF_REREAD.json: r2_reread.py's output on those glyphs; the staff lines each head was read against IN THE REAL RUN (`lines_used`:
the bar's own grid re-measured at the head, `frame_lines_for_head`) are taken from it -- 1 px of the outer line moves a chain gap.

Per tile: the page grey (Litolff, 600 dpi) from the staff's far line to 3 sp past the head, 5 sp each side; the head's detector box and
the five staff lines the real run read it against in crop coordinates; Sean's position (his words, our conversion, answers-2.311-ledger.json).
Positions: half-steps down from the top line (treble -3 = B5, bass 12 = C2).
"""
import json
import sys

import cv2
import numpy as np

from tools.omr.annotate import far_head_reader as FH
from tools.omr.preprocessing import render_page
from tools.omr.staged import lane_report as LR

# tile: (glyph, Sean's position, what he said it is)
TILES = {
    1: ("glyph/6/1/7/9/3", -4, "C6"), 2: ("glyph/4/0/0/14/4", -3, "B5"), 3: ("glyph/9/0/0/3/5", -7, "F6"),
    4: ("glyph/2/1/0/14/5", -7, "F6"), 5: ("glyph/8/0/0/15/4", -5, "D6"), 6: ("glyph/2/1/7/14/0", -7, "F6"),
    8: ("glyph/8/1/0/5/5", -5, "D6"), 9: ("glyph/6/0/5/11/6", -5, "D6"),
}
D = LR.RECORDS / "claim-readout-slices-2306-smp4-lit"
want_boxes = {g for g, _p, _n in TILES.values()}
want_staves = {"staff/" + "/".join(g.split("/")[1:4]) for g in want_boxes}
boxes, lines = {}, {}
for l in open(D / "observations.jsonl"):
    h = l[:220]
    if '"quantity": "glyph_box"' in h:
        o = json.loads(l)
        if o["subject"] in want_boxes:
            boxes[o["subject"]] = [float(v) for v in o["detail"]["bbox_page_px"]]
    elif '"quantity": "staff_lines"' in h:
        o = json.loads(l)
        if o["subject"] in want_staves:
            lines[o["subject"]] = [float(v) for v in o["value"]]
used = {k: v["lines"] for k, v in json.load(open(sys.argv[1]))["heads"].items() if v.get("lines")}
pdf = str(LR.LIB / LR.PLATES["litolff"]["pdf"])
out = {}
pages = {}
for t, (g, pos, name) in sorted(TILES.items()):
    p = int(g.split("/")[1])
    if p not in pages:
        pages[p] = cv2.cvtColor(render_page(pdf, p, dpi=600).rgb, cv2.COLOR_RGB2GRAY)
    gray = pages[p]
    b = boxes[g]
    ys = used.get(g) or lines["staff/" + "/".join(g.split("/")[1:4])]
    sp = (ys[-1] - ys[0]) / 4.0
    cx = (b[0] + b[2]) / 2.0
    y0 = int(min(ys[0], b[1]) - 3 * sp)
    y1 = int(max(ys[-1], b[3]) + 3 * sp)
    x0, x1 = int(cx - 5 * sp), int(cx + 5 * sp)
    crop = gray[y0:y1, x0:x1].copy()
    bb = [b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0]
    ll = [v - y0 for v in ys]
    out["t%d_gray" % t] = crop
    out["t%d_box" % t] = np.array(bb)
    out["t%d_lines" % t] = np.array(ll)
    out["t%d_sean" % t] = np.array(pos)
    r = FH.read_absolute_position(crop, ll, bb, g, [], [])
    print(t, g, "Sean", pos, name, "| crop read:", r[0], r[1][:60])
np.savez_compressed("tools/omr/tests/data_ledger_count_to_ink_2_312.npz", **out)
