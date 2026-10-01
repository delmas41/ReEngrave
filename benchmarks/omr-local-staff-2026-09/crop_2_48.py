import sys, json
import numpy as np
import cv2

REPO = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a3ef66441824adfff"
sys.path.insert(0, REPO)
from tools.omr.preprocessing import render_page, deskew
from tools.omr import measure_extractor as me

RECORD = json.loads(open(REPO + "/benchmarks/acceptance/quick/out/beethoven5-litolff/beethoven5-litolff-p3.record.json").read())["record"]
PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
DPI = 600

OUT = REPO + "/benchmarks/omr-local-staff-2026-09/out/print"
import os
os.makedirs(OUT, exist_ok=True)

_page_cache = {}


def get_page(page_index):
    if page_index not in _page_cache:
        page = render_page(PDF, page_index, dpi=DPI)
        rgb, binary, skew = deskew(page.rgb, page.binary)
        page.rgb, page.binary, page.skew_correction_deg = rgb, binary, skew
        _page_cache[page_index] = page
    return _page_cache[page_index]


def subject_bbox(sub):
    for o in RECORD["observations"]:
        if o["subject"] == sub and o["quantity"] == "glyph_box":
            return o["detail"].get("bbox_page_px")
    return None


def staff_lines(page_idx, system, staff):
    key = f"staff/{page_idx}/{system}/{staff}"
    rows = [o for o in RECORD["observations"]
           if o["subject"] == key and o["quantity"] == "staff_lines"]
    if not rows:
        return None
    return [float(y) for y in rows[-1]["value"]]


def crop_one(sub, label):
    parts = sub.split("/")
    page_idx, system, staff, cell, glyph_i = (int(x) for x in parts[1:6])
    bbox = subject_bbox(sub)
    if bbox is None:
        print(f"{sub}: no bbox, skipped")
        return
    x0, y0, x1, y1 = bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    page = get_page(page_idx)
    lines = staff_lines(page_idx, system, staff)
    if lines is None:
        print(f"{sub}: no staff lines, skipped")
        return
    spacing = (max(lines) - min(lines)) / 4.0

    win_x = 160
    win_y = 120
    cx0, cy0 = int(cx - win_x), int(cy - win_y)
    cx1, cy1 = int(cx + win_x), int(cy + win_y)
    cx0, cy0 = max(0, cx0), max(0, cy0)
    cx1 = min(page.rgb.shape[1], cx1)
    cy1 = min(page.rgb.shape[0], cy1)
    crop = page.rgb[cy0:cy1, cx0:cx1].copy()
    if crop.ndim == 2:
        crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    else:
        crop = cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)

    # base flat comb (orange), at this window's x-span, unchanged across it.
    for ly in lines:
        yy = int(round(ly)) - cy0
        if 0 <= yy < crop.shape[0]:
            cv2.line(crop, (0, yy), (crop.shape[1], yy), (0, 140, 255), 1)

    # the NEW comb, walked across this window's own x-span (page coords).
    shift = me._walk_comb_shift(page.binary, lines, cx0, cx1, spacing)
    if shift is not None:
        for i, ly in enumerate(lines):
            path = ly + shift  # per-column page-y, aligned to cx0..cx1
            pts = np.array([[x - cx0, int(round(path[x - cx0])) - cy0]
                           for x in range(cx0, cx1)
                           if 0 <= int(round(path[x - cx0])) - cy0 < crop.shape[0]],
                          dtype=np.int32)
            if len(pts) > 1:
                cv2.polylines(crop, [pts], False, (0, 220, 0), 1)

    # the head's own box, in red.
    cv2.rectangle(crop, (int(x0 - cx0), int(y0 - cy0)),
                 (int(x1 - cx0), int(y1 - cy0)), (0, 0, 255), 1)

    out_path = f"{OUT}/{label}.png"
    cv2.imwrite(out_path, crop)
    print(f"{sub}: wrote {out_path}  (orange=base flat comb, green=new walked comb, red=head box)")


CASES = [
    ("glyph/1/0/10/7/1", "base_wrong_1"),
    ("glyph/1/0/10/8/1", "base_wrong_2"),
    ("glyph/1/0/3/7/3", "base_wrong_3_now_fixed"),
    ("glyph/1/0/7/1/1", "base_wrong_4_now_fixed"),
    ("glyph/1/0/7/12/1", "prev_attempt_regression_1"),
    ("glyph/1/0/7/15/0", "prev_attempt_regression_2"),
    ("glyph/1/0/7/2/0", "prev_attempt_regression_3"),
    ("glyph/1/0/8/0/5", "prev_attempt_regression_4_still_wrong"),
]

for sub, label in CASES:
    crop_one(sub, label)
