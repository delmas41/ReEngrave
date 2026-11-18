"""2.312 r2: tile 11 (glyph/16/1/10/1/7, Sean: C2 on the second ledger line below, bass) -- what the count reads when the box is not
refused as too narrow; and the head's ink extent. PYTHONPATH=. OMR_LEDGER_COUNT_TO_INK=1 python3 benchmarks/ledger-count-2026-11/r2_probe11.py"""
import json

import cv2

from tools.omr.annotate import far_head_reader as FH
from tools.omr.annotate import ledger_grid as lg
from tools.omr.preprocessing import render_page
from tools.omr.staged import lane_report as LR

D = LR.RECORDS / "claim-readout-slices-2306-smp4-lit"
lines = None
for l in open(D / "observations.jsonl"):
    if '"subject": "staff/16/1/10", "quantity": "staff_lines"' in l:
        lines = [float(v) for v in json.loads(l)["value"]]
        break
box = (726.4, 3621.2, 741.2, 3631.5)
g = cv2.cvtColor(render_page(str(LR.LIB / LR.PLATES["litolff"]["pdf"]), 16, dpi=600).rgb, cv2.COLOR_RGB2GRAY)
sp = (lines[-1] - lines[0]) / 4
print("lines", lines, "sp", sp)
print("ink", lg.head_ink_box(g, box, sp, None, 1.0))
det = {}
print("count", FH.read_absolute_position(g, lines, box, "glyph/16/1/10/1/7", [], [], detail_out=det))
nf = det.get("note_first") or {}
print({k: nf.get(k) for k in ("reason", "how", "line_y", "between", "gaps", "ink")})
