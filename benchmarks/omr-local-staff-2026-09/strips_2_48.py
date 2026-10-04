import sys, json, os
import numpy as np
import cv2

REPO = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a3ef66441824adfff"
sys.path.insert(0, REPO)
from tools.omr.preprocessing import render_page, deskew
from tools.omr import measure_extractor as me

OUT = REPO + "/benchmarks/omr-local-staff-2026-09/out/print/strips"
os.makedirs(OUT, exist_ok=True)

LITOLFF_PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
RECORD = json.loads(open(REPO + "/benchmarks/acceptance/quick/out/beethoven5-litolff/beethoven5-litolff-p3.record.json").read())["record"]

STAVES = [
    dict(page=3, system=0, staff=0, label="litolff_p3_staff3_0_0_flutes"),
    dict(page=1, system=0, staff=8, label="litolff_p1_staff1_0_8_dense_chord"),
]

SEG_WIDTH = 1600
STRIP_PAD = 60  # px above/below the staff span, for context


def staff_facts(page_idx, system, staff):
    key = f"staff/{page_idx}/{system}/{staff}"
    lines = extent = None
    for o in RECORD["observations"]:
        if o["subject"] != key:
            continue
        if o["quantity"] == "staff_lines":
            lines = [float(y) for y in o["value"]]
        elif o["quantity"] == "staff_extent":
            extent = o["value"]
    return lines, extent


_page_cache = {}


def get_page(page_idx):
    if page_idx not in _page_cache:
        page = render_page(LITOLFF_PDF, page_idx, dpi=600)
        rgb, binary, skew = deskew(page.rgb, page.binary)
        page.rgb, page.binary, page.skew_correction_deg = rgb, binary, skew
        _page_cache[page_idx] = page
    return _page_cache[page_idx]


def walk_with_ticks(binary, nominal_ys, x0, x1, spacing, thickness):
    """A copy of _walk_comb_shift's own loop, ALSO recording which steps
    held vs committed a move -- for the strip's tick marks only; the
    production function's return contract is untouched."""
    max_thickness_px = me.CELL_LINE_WALK_CLEAN_THICKNESS_MULT * (
        thickness if thickness else me.CELL_LINE_WALK_DEFAULT_THICKNESS_SPACES * spacing)
    step_px = max(1, int(round(me.CELL_LINE_WALK_STEP_SPACES * spacing)))
    search_half_px = me.CELL_LINE_WALK_SEARCH_HALF_SPACES * spacing
    max_step_px = me.CELL_LINE_WALK_MAX_STEP_SPACES * spacing
    max_total_px = me.CELL_LINE_WALK_MAX_TOTAL_SPACES * spacing
    margin = me.CELL_LINE_WALK_BARLINE_MARGIN_PX
    top_y, bottom_y = min(nominal_ys), max(nominal_ys)
    xs = list(range(x0, x1, step_px))
    shift = 0.0
    shifts = []
    committed_at = []  # x positions where a move was committed
    held_at = []       # x positions where the step held (dirty/disagree)
    pending = []
    for xi in xs:
        xw0, xw1 = xi, min(x1, xi + step_px)
        has_barline = any(
            me._is_barline_column(binary, x, top_y, bottom_y)
            for x in range(xw0 - margin, xw1 + margin))
        candidates = []
        if not has_barline:
            for ny in nominal_ys:
                py = ny + shift
                found = me._measure_line_run_mid(
                    binary, xw0, xw1, py - search_half_px, py + search_half_px,
                    max_thickness_px)
                if found is not None:
                    candidates.append(found[0] - ny)
        step_ok = len(candidates) >= me.CELL_LINE_WALK_MIN_LINES_AGREE
        new_shift = None
        if step_ok:
            med = sorted(candidates)[len(candidates) // 2]
            inliers = [c for c in candidates if abs(c - med) <= me.CELL_LINE_WALK_OUTLIER_PX]
            if len(inliers) >= me.CELL_LINE_WALK_MIN_LINES_AGREE:
                new_shift = sum(inliers) / len(inliers)
        if new_shift is None:
            pending = []
            held_at.append(xi)
        else:
            if pending and abs(new_shift - pending[-1]) > me.CELL_LINE_WALK_OUTLIER_PX:
                pending = []
            pending.append(new_shift)
            if len(pending) >= me.CELL_LINE_WALK_MIN_CONSISTENT_RUN:
                commit = sum(pending) / len(pending)
                delta = max(-max_step_px, min(max_step_px, commit - shift))
                proposed = shift + delta
                if abs(proposed) <= max_total_px:
                    shift = proposed
                    committed_at.append(xi)
                pending = []
            else:
                held_at.append(xi)
        shifts.append(shift)
    xs_arr = np.array(xs, dtype=float)
    shifts_arr = np.array(shifts, dtype=float)
    all_cols = np.arange(x0, x1, dtype=float)
    per_col = np.interp(all_cols, xs_arr, shifts_arr)
    k = max(3, (int(round(0.5 * spacing / step_px)) | 1))
    if k > 1 and per_col.size > k:
        from scipy.ndimage import median_filter
        per_col = median_filter(per_col, size=k, mode="nearest")
    return per_col, committed_at, held_at


def render_staff(page_idx, system, staff, label):
    lines, extent = staff_facts(page_idx, system, staff)
    if lines is None or extent is None:
        print(f"{label}: no staff facts, skipped")
        return []
    x0, x1 = int(extent[0]), int(extent[1])
    spacing = (max(lines) - min(lines)) / 4.0
    page = get_page(page_idx)
    thickness = None  # record doesn't carry it separately per staff here
    shift, committed_at, held_at = walk_with_ticks(
        page.binary, lines, x0, x1, spacing, thickness)

    y0 = int(min(lines)) - STRIP_PAD
    y1 = int(max(lines)) + STRIP_PAD
    paths = []

    out_files = []
    n_segs = (x1 - x0 + SEG_WIDTH - 1) // SEG_WIDTH
    for seg in range(n_segs):
        sx0 = x0 + seg * SEG_WIDTH
        sx1 = min(x1, sx0 + SEG_WIDTH)
        crop = page.rgb[max(0, y0):y1, sx0:sx1].copy()
        if crop.ndim == 2:
            crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
        else:
            crop = cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)
        max_diff = 0.0
        diff_x = None
        for ly in lines:
            yy = int(round(ly)) - max(0, y0)
            if 0 <= yy < crop.shape[0]:
                cv2.line(crop, (0, yy), (crop.shape[1], yy), (0, 140, 255), 1)
        for ly in lines:
            seg_idx = np.arange(sx0, sx1) - x0
            seg_idx = seg_idx[(seg_idx >= 0) & (seg_idx < shift.shape[0])]
            if seg_idx.size == 0:
                continue
            path_y = ly + shift[seg_idx]
            xs_local = seg_idx + x0 - sx0
            pts = []
            for xl, yv in zip(xs_local, path_y):
                yy = int(round(yv)) - max(0, y0)
                if 0 <= yy < crop.shape[0]:
                    pts.append((int(xl), yy))
            if len(pts) > 1:
                cv2.polylines(crop, [np.array(pts, dtype=np.int32)], False,
                             (0, 220, 0), 1)
            diff = np.abs(shift[seg_idx])
            if diff.size:
                m = float(diff.max())
                if m > max_diff:
                    max_diff = m
                    diff_x = int(sx0 + seg_idx[np.argmax(diff)])
        for cx in committed_at:
            if sx0 <= cx < sx1:
                xx = cx - sx0
                cv2.line(crop, (xx, 0), (xx, 6), (0, 220, 0), 1)
        for hx in held_at:
            if sx0 <= hx < sx1 and (hx % 15 == 0):  # thin out grey ticks
                xx = hx - sx0
                cv2.line(crop, (xx, 0), (xx, 4), (160, 160, 160), 1)

        out_path = f"{OUT}/{label}_seg{seg}.png"
        cv2.imwrite(out_path, crop)
        out_files.append((out_path, max_diff, diff_x, y0))
        print(f"{label} seg{seg}: wrote {out_path}  max|green-orange|={max_diff:.2f}px"
             + (f" at x={diff_x}" if diff_x else ""))

        if max_diff >= 1.0 and diff_x is not None:
            zx0, zx1 = diff_x - 100, diff_x + 100
            zx0c, zx1c = max(0, zx0), min(page.rgb.shape[1], zx1)
            zy0c, zy1c = max(0, y0), min(page.rgb.shape[0], y1)
            if zx1c <= zx0c or zy1c <= zy0c:
                continue
            zcrop = page.rgb[zy0c:zy1c, zx0c:zx1c].copy()
            if zcrop.size == 0:
                continue
            if zcrop.ndim == 2:
                zcrop = cv2.cvtColor(zcrop, cv2.COLOR_GRAY2BGR)
            else:
                zcrop = cv2.cvtColor(zcrop, cv2.COLOR_RGB2BGR)
            for ly in lines:
                yy = int(round(ly)) - max(0, y0)
                if 0 <= yy < zcrop.shape[0]:
                    cv2.line(zcrop, (0, yy), (zcrop.shape[1], yy), (0, 140, 255), 1)
            seg_idx = np.arange(max(0, zx0), zx1) - x0
            seg_idx = seg_idx[(seg_idx >= 0) & (seg_idx < shift.shape[0])]
            for ly in lines:
                pts = []
                for xl in seg_idx:
                    yv = ly + shift[xl]
                    xx = int(xl + x0 - max(0, zx0))
                    yy = int(round(yv)) - max(0, y0)
                    if 0 <= yy < zcrop.shape[0]:
                        pts.append((xx, yy))
                if len(pts) > 1:
                    cv2.polylines(zcrop, [np.array(pts, dtype=np.int32)], False,
                                 (0, 220, 0), 1)
            zoom = cv2.resize(zcrop, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
            zpath = f"{OUT}/{label}_seg{seg}_zoom.png"
            cv2.imwrite(zpath, zoom)
            print(f"  zoom: wrote {zpath}")
            out_files.append((zpath, max_diff, diff_x, y0))
    return out_files


all_out = []
for cfg in STAVES:
    all_out += render_staff(cfg["page"], cfg["system"], cfg["staff"], cfg["label"])

print("\nCAPTIONS (orange=base flat comb, green=new comb, grey tick=held, green tick=committed update):")
for path, max_diff, diff_x, y0 in all_out:
    name = os.path.basename(path)
    print(f"{name}: orange=base flat comb, green=new walked comb; "
         f"max separation in this image = {max_diff:.2f}px"
         + (f" near page x={diff_x}" if diff_x else ""))
