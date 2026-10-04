"""3 print-check crops for the DOMINANT cause among the 14 right->wrong
heads under the GATHER+ADJUDICATE-only judge (2026-10-01): a local comb
mistrace that shifts EVERY head in one cell by the same ~0.6-1.0 staff
step, rather than a per-head boundary-tie flip. Orange = base flat grid
(Staff.line_ys / _cell_grid), green = an independently re-walked comb at
this window's own x-span (illustration of the SAME mechanism the lane's
earlier crops used -- not a byte-exact replay of the production per-step
value, which depends on the cell's own x0 and step history; the subject's
PRODUCTION position is printed in the legend so the two can be compared
honestly), red = the flagged head's own detector box, cyan = legend text.
"""
import sys, json
import numpy as np
import cv2

REPO = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-aa614525a6a8a7cfc"
ARM_REPO = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a3ef66441824adfff"
sys.path.insert(0, ARM_REPO)
from tools.omr.preprocessing import render_page, deskew
from tools.omr import measure_extractor as me

BASE_RECORD = json.loads(open(
    REPO + "/base-tree/benchmarks/acceptance/quick/out/beethoven5-litolff/beethoven5-litolff-p3.record.json"
).read())["record"]
ARM_RECORD = json.loads(open(
    REPO + "/benchmarks/acceptance/quick/out/beethoven5-litolff/beethoven5-litolff-p3.record.json"
).read())["record"]
PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
DPI = 600

OUT = REPO + "/out/print/2.48"
import os
os.makedirs(OUT, exist_ok=True)

_page_cache = {}


def get_page(page_index):
    # lane-2.48-recipe (2026-10-01): render_page() ALREADY binarizes+deskews
    # internally (see its own docstring) -- production's recipe
    # (tools/omr/staged/pipeline.py:prepare_pages) calls it exactly once and
    # never deskews a second time. This script used to call deskew() again
    # on render_page's own output, a divergence from the production recipe
    # measured (lane-2.48-recipe FINDINGS) to be a no-op on this page/DPI
    # but wrong in principle; fixed to the single call, matching GATHER.
    if page_index not in _page_cache:
        page = render_page(PDF, page_index, dpi=DPI)
        _page_cache[page_index] = page
    return _page_cache[page_index]


def subject_bbox(rec, sub):
    for o in rec["observations"]:
        if o["subject"] == sub and o["quantity"] == "glyph_box":
            return o["detail"].get("bbox_page_px")
    return None


def staff_lines(rec, page_idx, system, staff):
    key = f"staff/{page_idx}/{system}/{staff}"
    rows = [o for o in rec["observations"]
           if o["subject"] == key and o["quantity"] == "staff_lines"]
    if not rows:
        return None
    return [float(y) for y in rows[-1]["value"]]


def notehead_pos(rec, sub):
    rows = [o for o in rec["observations"]
           if o["subject"] == sub and o["quantity"] == "notehead_staff_position"]
    return float(rows[-1]["value"]) if rows else None


def crop_one(sub, label, base_pos, arm_pos, shift):
    parts = sub.split("/")
    page_idx, system, staff, cell, glyph_i = (int(x) for x in parts[1:6])
    bbox = subject_bbox(BASE_RECORD, sub)
    x0, y0, x1, y1 = bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    page = get_page(page_idx)
    lines = staff_lines(BASE_RECORD, page_idx, system, staff)
    spacing = (max(lines) - min(lines)) / 4.0

    win_x, win_y = 180, 130
    cx0, cy0 = max(0, int(cx - win_x)), max(0, int(cy - win_y))
    cx1 = min(page.rgb.shape[1], int(cx + win_x))
    cy1 = min(page.rgb.shape[0], int(cy + win_y))
    crop = page.rgb[cy0:cy1, cx0:cx1].copy()
    crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR) if crop.ndim == 2 else cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)
    crop = cv2.resize(crop, (crop.shape[1] * 2, crop.shape[0] * 2), interpolation=cv2.INTER_NEAREST)
    sc = 2

    # orange: base flat grid (what `_cell_grid` / the staff-wide lines answer)
    for ly in lines:
        yy = int(round((ly - cy0) * sc))
        if 0 <= yy < crop.shape[0]:
            cv2.line(crop, (0, yy), (crop.shape[1], yy), (0, 140, 255), 1)

    # green: an independently re-walked comb across this window's x-span
    shift_px = me._walk_comb_shift(page.binary, lines, cx0, cx1, spacing)
    if shift_px is not None:
        for ly in lines:
            path = ly + shift_px
            pts = []
            for x in range(cx0, cx1):
                yy = int(round((path[x - cx0] - cy0) * sc))
                if 0 <= yy < crop.shape[0]:
                    pts.append([int((x - cx0) * sc), yy])
            if len(pts) > 1:
                cv2.polylines(crop, [np.array(pts, dtype=np.int32)], False, (0, 220, 0), 1)

    # red: this head's own detector box (bracketed)
    bx0, by0 = int((x0 - cx0) * sc), int((y0 - cy0) * sc)
    bx1, by1 = int((x1 - cx0) * sc), int((y1 - cy0) * sc)
    cv2.rectangle(crop, (bx0, by0), (bx1, by1), (0, 0, 255), 2)
    cv2.line(crop, (bx0 - 10, by0), (bx0, by0), (0, 0, 255), 2)
    cv2.line(crop, (bx0, by0 - 10), (bx0, by0), (0, 0, 255), 2)

    legend = [
        f"{sub}  staff={system}.{staff} cell={cell}",
        f"orange=base flat grid  green=re-walked comb (illustration)",
        f"PRODUCTION: base_pos={base_pos:.2f}  arm_pos={arm_pos:.2f}  shift={shift:+.3f} sp",
    ]
    for i, text in enumerate(legend):
        cv2.putText(crop, text, (6, 18 + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1, cv2.LINE_AA)

    out_path = f"{OUT}/{label}.png"
    cv2.imwrite(out_path, crop)
    print(f"{sub}: wrote {out_path}")


CASES = [
    ("glyph/3/0/8/0/3", "dominant_cause_staff8_bar49_head1"),
    ("glyph/3/0/8/0/8", "dominant_cause_staff8_bar49_head4"),
    ("glyph/2/0/3/0/5", "dominant_cause_bass_chord_bar17"),
]

for sub, label in CASES:
    bp = notehead_pos(BASE_RECORD, sub)
    ap = notehead_pos(ARM_RECORD, sub)
    crop_one(sub, label, bp, ap, ap - bp)
