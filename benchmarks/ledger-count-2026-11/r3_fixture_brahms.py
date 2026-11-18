"""ROADMAP 2.312 r3 -- cut the REAL page pixels of the one Brahms far head the box count read right and r2's ink count lost
(p0 glyph/0/0/5/5/6: a half note hanging under its fourth ledger below the staff; position 17 by the box count, which Sean's
hand-labelled page 0 agrees with, r2_brahms_truth.py) into `tools/omr/tests/data_ledger_count_to_ink_2_312_brahms.npz`.
Box and the staff lines the real run read it against are from r2's re-read (`lines_used`).

    PYTHONPATH=. python3 benchmarks/ledger-count-2026-11/r3_fixture_brahms.py
"""
import cv2
import numpy as np

from tools.omr.annotate import far_head_reader as FH
from tools.omr.preprocessing import render_page
from tools.omr.staged import lane_report as LR

G = "glyph/0/0/5/5/6"
BOX = [4146.4, 3740.4, 4188.6, 3778.5]
LINES = [3485.2, 3516.2, 3549.0, 3581.8, 3614.8]
POS = 17
gray = cv2.cvtColor(render_page(str(LR.LIB / LR.PLATES["brahms"]["pdf"]), 0, dpi=600).rgb, cv2.COLOR_RGB2GRAY)
sp = (LINES[-1] - LINES[0]) / 4.0
cx = (BOX[0] + BOX[2]) / 2.0
y0, y1 = int(LINES[0] - 3 * sp), int(BOX[3] + 3 * sp)
x0, x1 = int(cx - 5 * sp), int(cx + 5 * sp)
crop = gray[y0:y1, x0:x1].copy()
bb = [BOX[0] - x0, BOX[1] - y0, BOX[2] - x0, BOX[3] - y0]
ll = [v - y0 for v in LINES]
print("crop read:", FH.read_absolute_position(crop, ll, bb, G, [], []))
np.savez_compressed("tools/omr/tests/data_ledger_count_to_ink_2_312_brahms.npz", b1_gray=crop, b1_box=np.array(bb),
                    b1_lines=np.array(ll), b1_truth=np.array(POS))
