"""Crops for the 2 heads that go right->wrong under the SEEDED comb
(`recheck_2_48_seeded.py`'s own output: `glyph/3/0/0/2/4`, `glyph/3/1/0/6/0`
-- the pre-existing "comb commits to a real but wrong tilt" failure mode,
unaffected by seeding). NO re-gather, NO new run: re-uses the SAME
duck-typed-record recipe `recheck_2_48_seeded.py` already used (production
functions called directly on a fresh render+deskew of the committed arm
record's own stored geometry).

Per head: one crop (gather DPI, >=600px wide) with orange (today's per-bar
grid) and the seeded comb drawn at their ACTUAL production values across
the whole cell, small ticks on the columns where the comb's shift changed
(so Sean can see where it moved, not just where it ended up), a bracket on
the exact head, a legend, and a pixel-row ink-centre check at a clean
column AND at the head's own x (never "by eye").
"""
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.omr import measure_extractor as me
from frame import render_page_matching_gather  # lane-2.48-recipe
from tools.omr.types import PageWithStaves

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recheck_2_48_seeded import (
    ARM_RECORD, cell_key_of, duck_staff, expected_positions_for_page,
    load_record, obs, staff_key_of,
)
from tools.omr.acceptance_quick import _FAMILY_MAPS, _load_works_row, _reference_root

OUT_DIR = REPO_ROOT / "out/print/2.48/seeded/broken"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PDF = (
    "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
    "symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-"
    "1870--imslp984073.pdf"
)
DPI = 600
WORKS_ROW_ID = "beethoven-sym5-mvt1-984073-p3"
DOC_ID = "beethoven5-litolff"

SUBJECTS = ["glyph/3/0/0/2/4", "glyph/3/1/0/6/0"]


def ink_row_centres(binary, x0, x1, band_lo, band_hi, min_cov=0.6):
    """Row-run centres (not single peak rows) in `[band_lo,band_hi)` over
    columns `[x0,x1)` -- groups of consecutive rows at >= `min_cov` coverage,
    each collapsed to its own midpoint, so a 3px-thick printed line reads as
    ONE centre, not three separate 'peak rows'."""
    width = max(1, x1 - x0)
    row_ink = (binary[band_lo:band_hi, x0:x1] == 0).sum(axis=1)
    hit = row_ink >= min_cov * width
    centres = []
    i = 0
    while i < len(hit):
        if hit[i]:
            j = i
            while j < len(hit) and hit[j]:
                j += 1
            centres.append(band_lo + (i + j - 1) / 2.0)
            i = j
        else:
            i += 1
    return centres


def pick_clean_column(binary, cell_x0, cell_x1, avoid_x0, avoid_x1,
                      band_lo, band_hi, width=15):
    """The column window of `width` px inside the cell, outside the head's
    own box, with the LEAST total ink in the row band -- "clean" measured,
    not eyeballed."""
    best = None
    best_ink = None
    for x in range(cell_x0, cell_x1 - width, 5):
        if x < avoid_x1 + 10 and x + width > avoid_x0 - 10:
            continue  # overlaps the head's own box (+ margin)
        total = int((binary[band_lo:band_hi, x:x + width] == 0).sum())
        if best_ink is None or total < best_ink:
            best_ink = total
            best = x
    return best, best, best + width if best is not None else (None, None, None)


def bend_columns(paths, nominal_ys, min_delta=0.15):
    """Column indices (into `paths[0]`) where the comb's shift is at the
    GLOBAL max and GLOBAL min of its own excursion from the seed, across
    the whole cell -- the two points that bracket however much it moved --
    plus the column where it returns closest to the seed again (if that is
    a third, distinct location). A slow drift across a dense passage never
    trips a single-step threshold, so this reports the SHAPE of the whole
    excursion instead of hunting for one sharp per-column jump."""
    shift = paths[0] - nominal_ys[0]
    seed = shift[0]
    if np.ptp(shift) < min_delta:
        return []
    i_max = int(np.argmax(shift))
    i_min = int(np.argmin(shift))
    cols = sorted({i_max, i_min})
    return cols


def process(sub, rec, ref_root, family_map, expected):
    page_idx = int(sub.split("/")[1])
    staff_key = staff_key_of(sub)
    cell_key = cell_key_of(sub)
    staff = duck_staff(rec, staff_key)

    page = render_page_matching_gather(PDF, page_idx, dpi=DPI)
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

    def pos_at(top_y, half_step, y):
        return (y - top_y) / half_step

    # positions at the head's own x
    orange_top = nominal_ys[0] + orange_shift
    orange_pos = pos_at(orange_top, spacing_px / 2.0, y_center)
    if paths is not None:
        col = max(0, min(len(paths[0]) - 1, int(round(x_center)) - x0))
        ys_here = [float(p[col]) for p in paths]
        gaps = [ys_here[i + 1] - ys_here[i] for i in range(4)]
        half_step_comb = sum(gaps) / 4.0 / 2.0
        comb_top = ys_here[0]
        comb_pos = pos_at(comb_top, half_step_comb, y_center)
    else:
        comb_top, half_step_comb, comb_pos = orange_top, spacing_px / 2.0, orange_pos

    exp = expected.get(sub)

    bends = bend_columns(paths, nominal_ys) if paths is not None else []

    # ── crop ──────────────────────────────────────────────────────────────
    # Pad against the STAFF *and* the head's own box (a far/ledger note can
    # sit well outside the staff -- CLAUDE.md §10's amplification-by-distance
    # case) so the bracket is never clipped.
    pad = 45
    cy0 = int(min(min(staff.line_ys), bbox[1]) - pad)
    cy1 = int(max(max(staff.line_ys), bbox[3]) + pad)
    cx0, cx1 = x0 - 15, x1 + 15
    top_margin = 90  # room for the legend block, ABOVE the crop content
    crop = page.rgb[cy0:cy1, cx0:cx1].copy()
    scale = max(1, int(round(640 / crop.shape[1])) + 1)
    scale = max(scale, 3)
    crop_big = cv2.resize(crop, (crop.shape[1] * scale, crop.shape[0] * scale),
                          interpolation=cv2.INTER_NEAREST)
    # White legend strip ABOVE the music, never over it.
    legend = np.full((top_margin, crop_big.shape[1], 3), 255, dtype=np.uint8)
    crop_big = np.vstack([legend, crop_big])
    y_shift = top_margin

    def to_xy(px, py):
        return (int(round((px - cx0) * scale)),
               int(round((py - cy0) * scale)) + y_shift)

    # orange: rigid, across the whole cell
    for ny in staff.line_ys:
        y = ny + orange_shift
        xa, ya = to_xy(x0, y)
        xb, yb = to_xy(x1, y)
        cv2.line(crop_big, (xa, ya), (xb, yb), (0, 140, 255), 1)

    # seeded comb: production's own array
    if paths is not None:
        for path in paths:
            pts = [to_xy(x0 + i, float(y)) for i, y in enumerate(path)]
            for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
                cv2.line(crop_big, (xa, ya), (xb, yb), (0, 200, 0), 1)
        # bend ticks on the top line's own path
        top_path = paths[0]
        for col in bends:
            px, py = x0 + col, float(top_path[col])
            tx, ty = to_xy(px, py)
            cv2.line(crop_big, (tx, ty - 6), (tx, ty + 6), (255, 0, 0), 1)

    # the subject: a corner bracket on the exact head
    hx0, hy0 = to_xy(bbox[0], bbox[1])
    hx1, hy1 = to_xy(bbox[2], bbox[3])
    b = 10
    cv2.line(crop_big, (hx0 - b, hy0), (hx0, hy0), (255, 0, 255), 2)
    cv2.line(crop_big, (hx0, hy0 - b), (hx0, hy0), (255, 0, 255), 2)
    cv2.line(crop_big, (hx1 + b, hy1), (hx1, hy1), (255, 0, 255), 2)
    cv2.line(crop_big, (hx1, hy1 + b), (hx1, hy1), (255, 0, 255), 2)

    # legend + labels
    y_txt = 18
    cv2.putText(crop_big, sub, (8, y_txt), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
               (0, 0, 0), 1)
    y_txt += 16
    cv2.putText(crop_big, f"ref={exp}  orange={orange_pos:.2f}  comb={comb_pos:.2f}",
               (8, y_txt), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
    y_txt += 16
    cv2.line(crop_big, (8, y_txt), (28, y_txt), (0, 140, 255), 2)
    cv2.putText(crop_big, "orange = today's per-bar grid", (32, y_txt + 4),
               cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)
    y_txt += 16
    cv2.line(crop_big, (8, y_txt), (28, y_txt), (0, 200, 0), 2)
    cv2.putText(crop_big, "green = seeded comb", (32, y_txt + 4),
               cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)
    y_txt += 16
    cv2.line(crop_big, (8, y_txt), (28, y_txt), (255, 0, 0), 2)
    cv2.putText(crop_big, "red tick = comb bent here", (32, y_txt + 4),
               cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)

    out_path = OUT_DIR / f"{sub.replace('/', '_')}.png"
    cv2.imwrite(str(out_path), crop_big)

    # ── pixel-row frame check (not by eye) ──────────────────────────────
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
        col = max(0, min(len(nominal_ys) and (paths[0].shape[0] - 1 if paths is not None else 0),
                         (cx0_ + cx1_) // 2 - x0))
        orange_rows = [y + orange_shift for y in staff.line_ys]
        comb_rows = ([float(p[col]) for p in paths] if paths is not None
                    else orange_rows)
        report[label] = dict(x_range=(cx0_, cx1_), ink_centres=centres,
                             orange=orange_rows, comb=comb_rows)

    return dict(sub=sub, exp=exp, orange_pos=orange_pos, comb_pos=comb_pos,
               n_bends=len(bends), bend_cols_page_x=[x0 + c for c in bends],
               crop=str(out_path), report=report)


def main():
    rec = load_record(ARM_RECORD)
    works_row = _load_works_row(WORKS_ROW_ID)
    ref_root = _reference_root(works_row["reference"]["catalog_path"])
    family_map = _FAMILY_MAPS[DOC_ID]
    expected = expected_positions_for_page(rec, ref_root, family_map, 3)

    for sub in SUBJECTS:
        r = process(sub, rec, ref_root, family_map, expected)
        print("=" * 70)
        print("subject:", r["sub"], " reference pos:", r["exp"])
        print(f"  orange pos (today) = {r['orange_pos']:.3f}   "
             f"seeded comb pos = {r['comb_pos']:.3f}")
        print(f"  comb's excursion extremes ({r['n_bends']} marked), at page-x:",
             r["bend_cols_page_x"])
        for label, rep in r["report"].items():
            print(f"  [{label}] x={rep['x_range']}")
            print(f"    real ink-row centres: {[round(c,1) for c in rep['ink_centres']]}")
            print(f"    orange predicts:      {[round(y,1) for y in rep['orange']]}")
            print(f"    comb predicts:        {[round(y,1) for y in rep['comb']]}")
        print("  crop:", r["crop"])


if __name__ == "__main__":
    main()
