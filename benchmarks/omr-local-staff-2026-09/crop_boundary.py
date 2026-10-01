"""3 crops for ROADMAP 2.48's boundary question (lane-2.48-boundary).

NO re-gather -- reuses `recheck_2_48_seeded.py`'s own duck-typed-record
recipe (production functions called directly on a fresh render+deskew of
the committed ARM record's own stored geometry), and `crop_2_48_broken.py`'s
own drawing conventions (orange = today's per-bar grid, green = seeded
comb, magenta bracket = the subject). Adds: the detector's own box (red),
and the head's own ink top/bottom edge (cyan ticks) from
`boundary_measure.measure_notehead_ink_centre`, plus a pixel-row check at
the head's own x and at a clean column (never "by eye" -- CLAUDE.md rule 7).
"""
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.omr import measure_extractor as me
from frame import render_page_matching_gather  # lane-2.48-recipe
from tools.omr.types import PageWithStaves

from recheck_2_48_seeded import ARM_RECORD, duck_staff, load_record, obs
from crop_2_48_broken import ink_row_centres, pick_clean_column
from boundary_measure import measure_notehead_ink_centre

OUT_DIR = REPO_ROOT / "out" / "print" / "2.48" / "boundary"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PDF = (
    "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
    "symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-"
    "1870--imslp984073.pdf"
)
DPI = 600

# 3 near-boundary heads sampled from boundary_measure.py's own near-boundary
# list (<=2px), spread across different staves/bars.
SUBJECTS = ["glyph/3/0/0/2/9", "glyph/3/0/9/2/0", "glyph/3/1/6/11/0"]


def process(sub, rec, page_cache):
    page_idx, system, staff_i, cell_i, _g = (int(x) for x in sub.split("/")[1:])
    staff_key = f"staff/{page_idx}/{system}/{staff_i}"
    cell_key = f"cell/{page_idx}/{system}/{staff_i}/{cell_i}"
    staff = duck_staff(rec, staff_key)

    if page_idx not in page_cache:
        page = render_page_matching_gather(PDF, page_idx, dpi=DPI)
        page_cache[page_idx] = page
    page = page_cache[page_idx]
    pws = PageWithStaves(page=page, staves=[staff], barlines=[])

    cell_box = obs(rec, cell_key, "cell_box")["value"]
    x0, _y0, x1, _y1 = (int(v) for v in cell_box)

    gb = obs(rec, sub, "glyph_box")
    x_center = gb["detail"]["x_center_page"]
    y_center = gb["detail"]["y_center_page"]
    bbox = gb["detail"]["bbox_page_px"]

    offset = me._cell_line_offset(pws, staff, x0, x1)
    orange_shift = float(offset[0]) if offset is not None else 0.0
    paths = me._trace_cell_local_lines(pws, staff, x0, x1,
                                       seed_shift_px=orange_shift)
    nominal_ys = [float(y) for y in staff.line_ys]
    spacing_px = float(staff.line_spacing_px)

    orange_top = nominal_ys[0] + orange_shift
    orange_pos = (y_center - orange_top) / (spacing_px / 2.0)
    if paths is not None:
        col = max(0, min(len(paths[0]) - 1, int(round(x_center)) - x0))
        ys_here = [float(p[col]) for p in paths]
        gaps = [ys_here[i + 1] - ys_here[i] for i in range(4)]
        half_step_comb = sum(gaps) / 4.0 / 2.0
        comb_top = ys_here[0]
        comb_pos = (y_center - comb_top) / half_step_comb
    else:
        comb_pos = orange_pos

    half_step_px = spacing_px / 2.0
    residual_today = abs(orange_pos - round(orange_pos))
    dist_boundary_px = (0.5 - residual_today) * half_step_px

    ink_ctx = dict(box_page=bbox, spacing_px=spacing_px, staff=staff,
                   x0=x0, orange_shift=orange_shift, seeded_paths=paths,
                   nominal_ys=nominal_ys)
    ink_y = measure_notehead_ink_centre(page.binary, ink_ctx)

    # ── crop ──────────────────────────────────────────────────────────────
    pad = 45
    cy0 = int(min(min(staff.line_ys), bbox[1]) - pad)
    cy1 = int(max(max(staff.line_ys), bbox[3]) + pad)
    cx0, cx1 = x0 - 15, x1 + 15
    top_margin = 110
    crop = page.rgb[cy0:cy1, cx0:cx1].copy()
    scale = max(3, int(round(640 / crop.shape[1])) + 1)
    crop_big = cv2.resize(crop, (crop.shape[1] * scale, crop.shape[0] * scale),
                          interpolation=cv2.INTER_NEAREST)
    legend = np.full((top_margin, crop_big.shape[1], 3), 255, dtype=np.uint8)
    crop_big = np.vstack([legend, crop_big])
    y_shift = top_margin

    def to_xy(px, py):
        return (int(round((px - cx0) * scale)),
               int(round((py - cy0) * scale)) + y_shift)

    for ny in staff.line_ys:
        y = ny + orange_shift
        xa, ya = to_xy(x0, y)
        xb, yb = to_xy(x1, y)
        cv2.line(crop_big, (xa, ya), (xb, yb), (0, 140, 255), 1)

    if paths is not None:
        for path in paths:
            pts = [to_xy(x0 + i, float(y)) for i, y in enumerate(path)]
            for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
                cv2.line(crop_big, (xa, ya), (xb, yb), (0, 200, 0), 1)

    # detector box (red)
    rx0, ry0 = to_xy(bbox[0], bbox[1])
    rx1, ry1 = to_xy(bbox[2], bbox[3])
    cv2.rectangle(crop_big, (rx0, ry0), (rx1, ry1), (0, 0, 255), 1)

    # box centre (magenta bracket, as before)
    hx0, hy0 = to_xy(bbox[0], bbox[1])
    hx1, hy1 = to_xy(bbox[2], bbox[3])
    b = 10
    cv2.line(crop_big, (hx0 - b, hy0), (hx0, hy0), (255, 0, 255), 2)
    cv2.line(crop_big, (hx0, hy0 - b), (hx0, hy0), (255, 0, 255), 2)
    cv2.line(crop_big, (hx1 + b, hy1), (hx1, hy1), (255, 0, 255), 2)
    cv2.line(crop_big, (hx1, hy1 + b), (hx1, hy1), (255, 0, 255), 2)

    # ink centre (cyan tick across the box width)
    if ink_y is not None:
        xa, ya = to_xy(bbox[0], ink_y)
        xb, yb = to_xy(bbox[2], ink_y)
        cv2.line(crop_big, (xa, ya), (xb, yb), (255, 255, 0), 2)

    # legend
    y_txt = 18
    cv2.putText(crop_big, f"{sub}  dist_to_boundary={dist_boundary_px:.2f}px",
               (8, y_txt), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
    y_txt += 16
    cv2.putText(crop_big,
               f"orange={orange_pos:.3f}  comb={comb_pos:.3f}  "
               f"box_y={y_center:.1f}  ink_y={('%.1f' % ink_y) if ink_y is not None else 'n/a'}",
               (8, y_txt), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 0, 0), 1)
    y_txt += 18
    for color, label in (((0, 140, 255), "orange = today's per-bar grid"),
                         ((0, 200, 0), "green = seeded comb"),
                         ((0, 0, 255), "red = detector box"),
                         ((255, 0, 255), "magenta = box centre (bracket)"),
                         ((255, 255, 0), "cyan = measured ink centre")):
        cv2.line(crop_big, (8, y_txt), (28, y_txt), color, 2)
        cv2.putText(crop_big, label, (32, y_txt + 4), cv2.FONT_HERSHEY_SIMPLEX,
                   0.36, (0, 0, 0), 1)
        y_txt += 15

    out_path = OUT_DIR / f"{sub.replace('/', '_')}.png"
    cv2.imwrite(str(out_path), crop_big)

    # ── pixel-row frame check (never by eye) ────────────────────────────
    band_lo = int(min(staff.line_ys) - 10)
    band_hi = int(max(staff.line_ys) + 10)
    clean_x0, _, clean_x1 = pick_clean_column(
        page.binary, x0, x1, int(bbox[0]), int(bbox[2]), band_lo, band_hi)
    report = {}
    for label, cx0_, cx1_ in (("head_x", int(x_center) - 7, int(x_center) + 8),
                              ("clean_x", clean_x0, clean_x1)):
        if cx0_ is None:
            continue
        centres = ink_row_centres(page.binary, cx0_, cx1_, band_lo, band_hi)
        col = max(0, min((paths[0].shape[0] - 1) if paths is not None else 0,
                         (cx0_ + cx1_) // 2 - x0))
        orange_rows = [y + orange_shift for y in staff.line_ys]
        comb_rows = ([float(p[col]) for p in paths] if paths is not None
                    else orange_rows)
        report[label] = dict(x_range=(cx0_, cx1_), ink_row_centres=centres,
                             orange=orange_rows, comb=comb_rows)

    print(f"\n{sub}  dist_to_boundary={dist_boundary_px:.2f}px  "
         f"orange_pos={orange_pos:.3f}  comb_pos={comb_pos:.3f}  "
         f"box_y={y_center:.2f}  ink_y={ink_y}")
    for label, d in report.items():
        print(f"  {label} x={d['x_range']}: ink row-centres={d['ink_row_centres']}, "
             f"orange lines={[round(y,1) for y in d['orange']]}, "
             f"comb lines={[round(y,1) for y in d['comb']]}")
    return out_path


def main():
    rec = load_record(ARM_RECORD)  # recheck_2_48_seeded.load_record already unwraps ["record"]
    page_cache = {}
    for sub in SUBJECTS:
        path = process(sub, rec, page_cache)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
