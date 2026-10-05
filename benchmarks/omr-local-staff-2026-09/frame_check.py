"""lane-2.48-recipe (2026-10-01) -- does the fresh render sit in the SAME
pixel frame GATHER used? Measured here directly, both ways: (1) the
STAFF LINES (deterministic, no ink-centroid noise -- `detect_staves`'s own
integer-pixel output vs the record's stored `staff_lines`), and (2) 15
clean isolated noteheads' BOX vs their own ink (dx AND dy, via the ink
component itself, not just a y-only central-column scan). Then a control
that can fail (CLAUDE.md rule 7): a deliberate +4px vertical shift of the
fresh render, re-measured the same way, must show up as dy~=-4 (or +4,
sign depends on direction) on every item -- not scatter near zero.

NO re-gather. Reuses `boundary_measure.py`'s own ARM_RECORD, PROVENANCE_PDF,
PAGE_IDX, DPI and its "clean, >3px from any rounding boundary" head
selection (same 10 of its control; extended here to 15 by continuing its
own ordering) and `recheck_2_48_seeded.py`'s duck-typed-record helpers.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import cv2

from tools.omr.staff_detector import detect_staves

from frame import render_page_matching_gather
import boundary_measure as bm
import recheck_2_48_seeded as r48


def staff_line_check(pws, rec):
    """5 clean staff-line stretches: detect_staves()'s own line_ys on the
    fresh frame vs the record's stored `staff_lines` for the SAME staff
    key, on page 3. Picks the first 5 staves with 5 lines on page 3."""
    staff_keys = sorted({
        o["subject"] for o in rec["observations"]
        if o["quantity"] == "staff_lines" and o["subject"].split("/")[1] == str(bm.PAGE_IDX)
    })[:5]
    fresh_by_index = {st.staff_index: st for st in pws.staves}
    rows = []
    for sk in staff_keys:
        staff_ord = int(sk.split("/")[-1])
        stored = r48.obs(rec, sk, "staff_lines")["value"]
        fresh = fresh_by_index.get(staff_ord)
        if fresh is None:
            rows.append((sk, stored, None, None))
            continue
        dys = [f - s for f, s in zip(fresh.line_ys, stored)]
        rows.append((sk, stored, list(fresh.line_ys), dys))
    return rows


def ink_component_centre(binary, box_page):
    """The connected ink component whose bbox overlaps `box_page` the
    most, restricted to a window padded 30% around the box (so a
    neighbour's component outside the window cannot win by being
    larger) -- gives BOTH dx and dy, unlike the central-column y-only
    scan `boundary_measure.measure_notehead_ink_centre` uses."""
    x0, y0, x1, y1 = (float(v) for v in box_page)
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return None
    pad_x, pad_y = 0.5 * w, 0.5 * h
    wx0, wy0 = max(0, int(round(x0 - pad_x))), max(0, int(round(y0 - pad_y)))
    wx1, wy1 = min(binary.shape[1], int(round(x1 + pad_x))), min(binary.shape[0], int(round(y1 + pad_y)))
    if wx1 <= wx0 or wy1 <= wy0:
        return None
    window = (binary[wy0:wy1, wx0:wx1] == 0).astype(np.uint8)
    n, labels = cv2.connectedComponents(window, connectivity=8)
    if n <= 1:
        return None
    box_cx, box_cy = (x0 + x1) / 2.0 - wx0, (y0 + y1) / 2.0 - wy0
    bx0, by0, bx1, by1 = x0 - wx0, y0 - wy0, x1 - wx0, y1 - wy0
    best_label, best_overlap = None, 0.0
    for lbl in range(1, n):
        ys, xs = np.where(labels == lbl)
        ox0, ox1 = max(bx0, xs.min()), min(bx1, xs.max() + 1)
        oy0, oy1 = max(by0, ys.min()), min(by1, ys.max() + 1)
        overlap = max(0.0, ox1 - ox0) * max(0.0, oy1 - oy0)
        if overlap > best_overlap:
            best_overlap, best_label = overlap, lbl
    if best_label is None:
        return None
    ys, xs = np.where(labels == best_label)
    cx = float(xs.mean()) + wx0
    cy = float(ys.mean()) + wy0
    return cx, cy


def notehead_check(binary, rows, n=15):
    """15 clean heads (dist_boundary_px > 3, boundary_measure's own
    ordering, one per cell): box centre (record) vs ink-component centre
    (fresh render), dx AND dy."""
    clean_candidates = [r for r in rows if r["dist_boundary_px"] > 3.0]
    clean, seen = [], set()
    for r in clean_candidates:
        if r["cell_key"] in seen:
            continue
        seen.add(r["cell_key"])
        clean.append(r)
        if len(clean) >= n:
            break
    out = []
    for r in clean:
        box = r.get("box_page")
        if box is None:
            out.append((r["sub"], None, None))
            continue
        centre = ink_component_centre(binary, box)
        if centre is None:
            out.append((r["sub"], None, None))
            continue
        box_cx = (box[0] + box[2]) / 2.0
        box_cy = (box[1] + box[3]) / 2.0
        dx = box_cx - centre[0]
        dy = box_cy - centre[1]
        out.append((r["sub"], dx, dy))
    return out


def summarize(label, vals):
    xs = [v for v in vals if v is not None]
    if not xs:
        print(f"{label}: n/a")
        return
    print(f"{label}: n={len(xs)} mean={np.mean(xs):+.2f} std={np.std(xs):.2f} "
         f"min={min(xs):+.2f} max={max(xs):+.2f}")


def main():
    rec = bm.load_record(bm.ARM_RECORD)["record"]
    pw = render_page_matching_gather(bm.PROVENANCE_PDF, bm.PAGE_IDX, dpi=bm.DPI)
    pws_full = detect_staves(pw)

    print("=" * 70)
    print("STEP 2a -- 5 clean staff-line stretches: fresh detect_staves() "
         "vs record's stored staff_lines")
    print("=" * 70)
    for sk, stored, fresh, dys in staff_line_check(pws_full, rec):
        if fresh is None:
            print(f"  {sk:<16} stored={stored}  fresh=NOT FOUND")
        else:
            print(f"  {sk:<16} stored={stored}")
            print(f"  {'':16} fresh ={fresh}  dy_per_line={dys}")

    print()
    print("=" * 70)
    print("STEP 2b -- 15 clean isolated noteheads: record box-centre vs "
         "fresh-render ink-component centre (dx, dy)")
    print("=" * 70)

    # re-run boundary_measure's own row-building to get the same `rows`
    # (dist_boundary_px etc.) without re-deriving its logic
    all_rows, _near = bm.main()
    binary = pw.binary
    results = notehead_check(binary, all_rows)
    dxs, dys = [], []
    for sub, dx, dy in results:
        print(f"  {sub:<24} dx={('%+.2f' % dx) if dx is not None else 'n/a':<8} "
             f"dy={('%+.2f' % dy) if dy is not None else 'n/a'}")
        if dx is not None:
            dxs.append(dx)
        if dy is not None:
            dys.append(dy)
    summarize("dx", dxs)
    summarize("dy", dys)
    print("(scatter here is the SAME ink-centroid noise boundary_measure.py's "
         "own control already found -- 3.16px std on 10 clean heads via a "
         "different, y-only method; not a new finding, a cross-check.)")

    print()
    print("=" * 70)
    print("STEP 3 -- control: deliberate +4px vertical shift of the fresh "
         "render, same 15-head measurement, must show dy swing by ~4px")
    print("=" * 70)
    shifted_binary = np.roll(binary, 4, axis=0)
    shifted_binary[:4, :] = 255  # paper, not wrapped-around ink
    results_shifted = notehead_check(shifted_binary, all_rows)
    by_sub_shifted = {s: dy for s, _dx, dy in results_shifted}
    by_sub_base = {s: dy for s, _dx, dy in results}
    per_head_deltas = []
    for sub in by_sub_base:
        b, s = by_sub_base[sub], by_sub_shifted.get(sub)
        if b is None or s is None:
            continue
        per_head_deltas.append(s - b)
        print(f"  {sub:<24} base_dy={b:+.2f}  shifted_dy={s:+.2f}  "
             f"delta={s - b:+.2f}")
    dys_shifted = [dy for dy in by_sub_shifted.values() if dy is not None]
    summarize("dy under +4px shift", dys_shifted)
    if per_head_deltas:
        med = float(np.median(per_head_deltas))
        print(f"per-head delta: median={med:+.2f} mean={np.mean(per_head_deltas):+.2f} "
             f"std={np.std(per_head_deltas):.2f} (expect ~-4 per head: "
             f"shifting the ink down 4px should move EVERY head's "
             f"box-minus-ink by -4, head by head, even if the aggregate "
             f"mean is noisy)")
        ok = -6.0 <= med <= -2.0
        print(f"CONTROL {'PASSES' if ok else 'FAILS'} "
             f"(bar: per-head median delta within [-6,-2])")


if __name__ == "__main__":
    main()
