#!/usr/bin/env python3
"""lane-ledger-rungs (2026-10-01): why every geometry miss (on the 10
confirmed both-wrong heads, `glyph/1/0/10/14/1` dropped -- Sean confirmed
its reference pairing was wrong) lands exactly ONE STEP FARTHER from the
staff than the reference. MEASUREMENT ONLY -- no reader code touched.

Two measurements per head, on the 10 miss heads and a 10-head Litolff
control (geometry right, spread over `ledgers_out` 1-4 and both sides;
page 3 only -- no page-1 head in this far-head population has geometry
right, so no page-1 control exists to pick):

1. LEDGERS -- printed ledger rows read by pixel rows in a CLEAN column
   BESIDE the head (a stub strip offset from the head's own x, never
   through it), from the staff edge out to past the head. Reports each
   ledger's y and the gap to the previous one (outer line or last ledger)
   as a ratio of that staff's own local spacing.
2. BOX vs INK -- the head's own ink extent along y, read in two flanking
   column strips just off-centre (excluding both the exact centre column,
   where a stem usually runs, and any row already identified as a ledger
   in (1)); its centre vs the detector box's own centre, signed toward
   (-) or away (+) from the staff.

For each miss head, also reports where geometry would land stepping by
the MEASURED ledger gaps from (1) instead of nominal staff spacing.

Writes `ledger_breakdown_r3`-adjacent `outward_bias.csv` and prints the
summary table. 3 crops under `out/print/ledgers/outward/`.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

CSV_PATH = REPO / "benchmarks" / "omr-local-staff-2026-09" / "outward_bias.csv"
OUT_DIR = REPO / "out" / "print" / "ledgers" / "outward"

MISS_SUBJECTS = [
    "glyph/1/0/10/7/1", "glyph/1/0/10/8/1", "glyph/1/0/3/7/3",
    "glyph/3/0/0/2/1", "glyph/3/0/0/2/9", "glyph/3/0/0/6/2",
    "glyph/3/0/0/7/2", "glyph/3/0/8/9/0", "glyph/3/0/9/2/0",
    "glyph/3/0/9/3/5",
]
CONTROL_SUBJECTS = [
    "glyph/3/0/0/2/4", "glyph/3/0/0/5/12", "glyph/3/0/5/2/0",
    "glyph/3/0/7/0/7", "glyph/3/0/7/2/2", "glyph/3/0/7/3/1",
    "glyph/3/0/7/4/0", "glyph/3/0/7/6/1", "glyph/3/0/8/1/1",
    "glyph/3/1/0/6/0",
]

RED = (0, 0, 255)
GREEN = (0, 170, 0)
BLUE = (255, 120, 0)
MAGENTA = (255, 0, 255)
YELLOW = (0, 220, 220)
BLACK = (0, 0, 0)
MIN_WIDTH = 600


def _otsu_rows(strip: np.ndarray) -> np.ndarray:
    """Boolean per-row: is this row mostly ink, across `strip`'s columns?
    Otsu on the strip itself, then >=60% of the strip's columns dark."""
    thr = lg._otsu_threshold(strip)
    ink = strip <= thr
    return ink.mean(axis=1) >= 0.6


def _merge_rows_to_bands(is_ink_row: np.ndarray, y0: int, max_gap_px: int = 1
                         ) -> List[Tuple[float, int]]:
    """Contiguous True runs, bridging gaps of up to `max_gap_px` False
    rows in between, -> (centre_y, height)."""
    n = len(is_ink_row)
    starts = []
    runs: List[List[int]] = []
    i = 0
    while i < n:
        if is_ink_row[i]:
            j = i
            while j < n and is_ink_row[j]:
                j += 1
            if runs and i - runs[-1][1] <= max_gap_px:
                runs[-1][1] = j
            else:
                runs.append([i, j])
            i = j
        else:
            i += 1
    return [((s + e - 1) / 2.0 + y0, e - s) for s, e in runs]


def read_ledgers_beside(gray: np.ndarray, box, lines, side: str, spacing: float
                        ) -> List[float]:
    """Printed ledger rows between the staff edge and (a little past) the
    head, read in a clean column strip OFFSET from the head's own x --
    tries the right side first, then the left, keeping whichever finds
    more bands (a stem or a neighbour can foul one side)."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    edge = min(lines) if side == "above" else max(lines)
    sign = -1.0 if side == "above" else 1.0
    far = cy + sign * 0.6 * spacing
    yy0 = int(min(edge, far)) - 2
    yy1 = int(max(edge, far)) + 2
    h, w = gray.shape
    yy0, yy1 = max(0, yy0), min(h, yy1)

    best: List[Tuple[float, int]] = []
    for off_lo, off_hi in ((0.85, 1.05), (-1.05, -0.85)):
        sx0 = int(cx + off_lo * spacing)
        sx1 = int(cx + off_hi * spacing)
        sx0, sx1 = max(0, min(sx0, sx1)), min(w, max(sx0, sx1))
        if sx1 - sx0 < 2 or yy1 <= yy0:
            continue
        strip = gray[yy0:yy1, sx0:sx1]
        is_ink = _otsu_rows(strip)
        bands = _merge_rows_to_bands(is_ink, yy0)
        thin = [(y, h_) for (y, h_) in bands if h_ <= max(2, int(0.35 * spacing))]
        if len(thin) > len(best):
            best = thin
    ys = sorted((y for y, _ in best), key=lambda y: sign * (y - edge))
    return [y for y in ys if sign * (y - edge) > 0.3 * spacing]


def ink_extent_flanking(gray: np.ndarray, box, ledger_ys: List[float],
                        spacing: float) -> Optional[Tuple[float, float]]:
    """The head's own ink extent (top, bottom) in two flanking strips just
    off-centre (0.15..0.35 spaces each side -- excludes a central stem),
    within the box's own y-range padded a little, rows matching an
    already-found ledger excluded."""
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2.0
    pad = 0.3 * spacing
    h, w = gray.shape
    yy0 = max(0, int(y0 - pad))
    yy1 = min(h, int(y1 + pad))
    rows_any = np.zeros(yy1 - yy0, dtype=bool)
    for off_lo, off_hi in ((0.15, 0.35), (-0.35, -0.15)):
        sx0 = max(0, int(cx + off_lo * spacing))
        sx1 = min(w, int(cx + off_hi * spacing))
        if sx1 - sx0 < 1:
            continue
        strip = gray[yy0:yy1, sx0:sx1]
        if strip.size == 0:
            continue
        thr = lg._otsu_threshold(strip)
        ink = (strip <= thr).any(axis=1)
        rows_any |= ink
    for ly in ledger_ys:
        li = int(round(ly)) - yy0
        for d in (-1, 0, 1):
            if 0 <= li + d < len(rows_any):
                rows_any[li + d] = False
    idx = np.flatnonzero(rows_any)
    if idx.size == 0:
        return None
    return float(idx[0] + yy0), float(idx[-1] + yy0)


def measure_one(doc_id, loaded, subject) -> Optional[dict]:
    rec = loaded["rec"]
    rows = {r["subject"]: r for r in score._far_head_rows(doc_id, loaded)}
    row = rows.get(subject)
    if row is None:
        return None
    box = row["page_box"]
    if not box:
        return None
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    line_rows = rec.obs(Q.STAFF_LINES, row["staff_key"])
    lines = sorted(float(v) for v in line_rows[-1]["value"])
    spacing = (lines[-1] - lines[0]) / 4.0
    half_step = spacing / 2.0
    side = "above" if cy < lines[0] else "below"
    edge = lines[0] if side == "above" else lines[-1]
    sign = -1.0 if side == "above" else 1.0
    edge_pos = 0 if side == "above" else 8
    gray = score.PageCache(loaded["cfg"]).get(row["page"])

    ledger_ys = read_ledgers_beside(gray, box, lines, side, spacing)
    gaps = []
    prev = edge
    for ly in ledger_ys:
        gaps.append(abs(ly - prev) / spacing)
        prev = ly

    ink = ink_extent_flanking(gray, box, ledger_ys, spacing)
    box_center = (y0 + y1) / 2.0
    if ink is not None:
        ink_top, ink_bot = ink
        ink_center = (ink_top + ink_bot) / 2.0
        # signed: + = box centre is FARTHER from the staff than ink centre
        box_minus_ink = sign * (box_center - ink_center)
    else:
        box_minus_ink = None

    geom_pos = int(round(row["raw_pos"]))
    return dict(
        subject=subject, side=side, spacing_px=round(spacing, 3),
        edge_y=edge, box=box, lines=lines, gray=gray,
        ledger_ys=ledger_ys, gap_ratios=gaps,
        box_center=box_center, ink_extent=ink, box_minus_ink_px=box_minus_ink,
        geom_pos=geom_pos, half_step=half_step, sign=sign, edge_pos=edge_pos,
    )


def stepped_geometry(m: dict, ref_pos: int) -> Tuple[Optional[int], bool]:
    """Where would geometry land stepping by the MEASURED ledger gaps
    (from step 1) instead of nominal staff spacing?

    Builds a half-step marker grid outward from the edge: marker[0] =
    edge (offset 0); marker[2k] = the k-th MEASURED ledger (offset 2k);
    marker[2k-1] = the midpoint between marker[2k-2] and marker[2k] (the
    "space" half-step between two measured ledgers, offset 2k-1) --
    i.e. each found ledger's own gap is used, never the nominal spacing,
    for every marker up to the last found ledger. Beyond the last found
    ledger (no further measurement available), the grid extends at
    nominal half-step spacing. The head's own box-centre distance from
    the edge is then rounded to the NEAREST marker, which names the
    stepped position.
    """
    sign, edge, half_step = m["sign"], m["edge_y"], m["half_step"]
    ledger_ys = m["ledger_ys"]
    box_center = m["box_center"]

    grid = [edge]
    prev = edge
    for ly in ledger_ys:
        grid.append((prev + ly) / 2.0)  # the space half-step before this ledger
        grid.append(ly)                 # the ledger line itself
        prev = ly
    # Extend outward at nominal half-step spacing beyond the last
    # measurement -- no further ledger was found to measure from.
    nxt = grid[-1]
    while len(grid) < 20:
        nxt = nxt + sign * half_step
        grid.append(nxt)

    dists = [sign * (g - edge) for g in grid]
    target = sign * (box_center - edge)
    best_i = min(range(len(dists)), key=lambda i: abs(dists[i] - target))
    stepped_pos = m["edge_pos"] + sign * best_i
    return int(round(stepped_pos)), int(round(stepped_pos)) == ref_pos


def render_crop(m: dict, ref_pos: int, out_path: Path):
    gray = m["gray"]
    box = m["box"]
    lines = m["lines"]
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    spacing = m["spacing_px"]
    top, bottom = lines[0], lines[-1]
    side = m["side"]
    farthest = cy
    for ly in m["ledger_ys"]:
        farthest = min(farthest, ly) if side == "above" else max(farthest, ly)
    margin = 1.2 * spacing
    wy0 = min(top, farthest) - margin
    wy1 = max(bottom, farthest) + margin
    wx0 = cx - 1.8 * spacing
    wx1 = cx + 1.8 * spacing
    native_w = max(1, int(round(wx1 - wx0)))
    native_h = max(1, int(round(wy1 - wy0)))
    scale = max(3, -(-MIN_WIDTH // native_w))
    out_w, out_h = native_w * scale, native_h * scale
    h, w = gray.shape
    px0, py0 = max(0, int(wx0)), max(0, int(wy0))
    px1, py1 = min(w, int(wx0) + native_w), min(h, int(wy0) + native_h)
    canvas = np.full((native_h, native_w, 3), 255, dtype=np.uint8)
    if px1 > px0 and py1 > py0:
        patch = cv2.cvtColor(gray[py0:py1, px0:px1], cv2.COLOR_GRAY2BGR)
        canvas[py0 - int(wy0):py1 - int(wy0), px0 - int(wx0):px1 - int(wx0)] = patch
    big = cv2.resize(canvas, (out_w, out_h), interpolation=cv2.INTER_NEAREST)

    def to_big(px, py):
        return (int(round((px - wx0) * scale)), int(round((py - wy0) * scale)))

    for ly in lines:
        if ly < wy0 or ly > wy1:
            continue
        _, by = to_big(wx0, ly)
        cv2.line(big, (0, by), (out_w, by), GREEN, 1)
    for ly in m["ledger_ys"]:
        _, by = to_big(wx0, ly)
        cv2.line(big, (int(0.3 * out_w), by), (out_w, by), MAGENTA, 3)
    if m["ink_extent"] is not None:
        for iy in m["ink_extent"]:
            _, by = to_big(wx0, iy)
            cv2.line(big, (0, by), (int(0.3 * out_w), by), YELLOW, 3)
    bx0, by0 = to_big(x0, y0)
    bx1, by1 = to_big(x1, y1)
    cv2.rectangle(big, (bx0, by0), (bx1, by1), RED, max(1, scale // 3))

    TEXT_W = max(out_w, 900)
    text_h = 130
    tile = np.full((out_h + text_h, TEXT_W, 3), 255, dtype=np.uint8)
    tile[:out_h, :out_w, :] = big
    lines_txt = [
        f"{m['subject']}  geom={m['geom_pos']}  ref={ref_pos}",
        f"magenta = measured ledgers (beside, {len(m['ledger_ys'])} found); "
        f"gaps/spacing = {['%.2f'%g for g in m['gap_ratios']]}",
        f"yellow = ink extent (flanking cols); box-ink px = "
        f"{m['box_minus_ink_px']:.1f}" if m["box_minus_ink_px"] is not None else
        "yellow = ink extent: not found",
    ]
    for i, t in enumerate(lines_txt):
        cv2.putText(tile, t[:150], (6, out_h + 20 + i * 24), cv2.FONT_HERSHEY_SIMPLEX,
                   0.46, BLACK, 1, cv2.LINE_AA)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), tile)

    # pixel-row check, printed not asserted
    report = []
    for ly in m["ledger_ys"]:
        y_lo, y_hi = max(0, int(ly) - 1), min(h, int(ly) + 2)
        x_lo, x_hi = max(0, int(cx + 0.85 * spacing)), min(w, int(cx + 1.05 * spacing))
        if x_hi <= x_lo:
            x_lo, x_hi = max(0, int(cx - 1.05 * spacing)), min(w, int(cx - 0.85 * spacing))
        strip = gray[y_lo:y_hi, x_lo:x_hi] < 128
        cov = float(strip.any(axis=0).mean()) if strip.size else 0.0
        report.append(f"ledger y={ly:.1f} coverage={cov:.2f} {'OK' if cov >= 0.5 else 'MISS'}")
    return report


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def main() -> int:
    loaded = ts.load_doc("beethoven5-litolff")
    rec = loaded["rec"]
    csv_rows = []
    miss_results = []
    control_results = []

    ref_by_subject = {}
    with open(REPO / "benchmarks/omr-local-staff-2026-09/ledger_breakdown_r3.csv") as f:
        for r in csv.DictReader(f):
            if r["doc"] == "beethoven5-litolff":
                ref_by_subject[r["subject"]] = int(r["ref_pos"])

    for group, subs in (("miss", MISS_SUBJECTS), ("control", CONTROL_SUBJECTS)):
        for sub in subs:
            m = measure_one("beethoven5-litolff", loaded, sub)
            if m is None:
                print(f"WARNING: could not measure {sub}")
                continue
            ref_pos = ref_by_subject.get(sub)
            stepped_pos, stepped_right = (None, None)
            if group == "miss" and ref_pos is not None:
                stepped_pos, stepped_right = stepped_geometry(m, ref_pos)
            row = dict(
                group=group, subject=sub, side=m["side"],
                ref_pos=ref_pos, geom_pos=m["geom_pos"],
                spacing_px=m["spacing_px"],
                n_ledgers_found=len(m["ledger_ys"]),
                gap1_ratio=(m["gap_ratios"][0] if len(m["gap_ratios"]) > 0 else ""),
                gap2_ratio=(m["gap_ratios"][1] if len(m["gap_ratios"]) > 1 else ""),
                all_gap_ratios=";".join(f"{g:.3f}" for g in m["gap_ratios"]),
                box_minus_ink_px=(round(m["box_minus_ink_px"], 2)
                                 if m["box_minus_ink_px"] is not None else ""),
                stepped_pos=(stepped_pos if stepped_pos is not None else ""),
                stepped_right=(stepped_right if stepped_right is not None else ""),
            )
            csv_rows.append(row)
            (miss_results if group == "miss" else control_results).append((sub, m, ref_pos))

    fields = ["group", "subject", "side", "ref_pos", "geom_pos", "spacing_px",
             "n_ledgers_found", "gap1_ratio", "gap2_ratio", "all_gap_ratios",
             "box_minus_ink_px", "stepped_pos", "stepped_right"]
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in csv_rows:
            w.writerow(r)
    print(f"wrote {len(csv_rows)} rows to {CSV_PATH}")

    def summarize(name, results):
        gap1s = [m["gap_ratios"][0] for _, m, _ in results if len(m["gap_ratios"]) > 0]
        gap2s = [m["gap_ratios"][1] for _, m, _ in results if len(m["gap_ratios"]) > 1]
        bmi = [m["box_minus_ink_px"] for _, m, _ in results if m["box_minus_ink_px"] is not None]
        print(f"{name}: n={len(results)}  median gap1/spacing={median(gap1s)}  "
             f"median gap2/spacing={median(gap2s)}  median box-ink px={median(bmi)}")

    print("\n=== Summary table ===")
    summarize("misses", miss_results)
    summarize("controls", control_results)

    n_fixed = sum(1 for sub, m, ref in miss_results
                 if ref is not None and stepped_geometry(m, ref)[1])
    print(f"misses fixed by stepping on measured gaps: {n_fixed} of {len(miss_results)}")

    # --- 3 crops ---
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    chosen = miss_results[:3]
    for sub, m, ref in chosen:
        out_path = OUT_DIR / f"{sub.replace('/', '-')}.png"
        pr = render_crop(m, ref, out_path)
        print(f"wrote {out_path}")
        for line in pr:
            print(f"  {line}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
