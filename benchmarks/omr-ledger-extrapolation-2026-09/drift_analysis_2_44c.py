#!/usr/bin/env python3
"""ROADMAP 2.44c, Sean via manager: "could the geometry be off because the
staff has shifted?" Measurement only (CLAUDE.md §8). Reuses `truth_set_
2_44c.load_doc`/`build_rows` for the scored population (post both judge
fixes, FINDINGS §15) and adds, per scored far head:

  * **drift**: the staff's own top line, re-measured ROBUSTLY at the
    head's own x, minus the GLOBAL top line already on the record
    (`Q.STAFF_LINES`) -- same page-pixel frame, so a straight subtraction.
  * **spacing deviation**: the robustly re-measured spacing minus the
    global one.

"Robust" (per the manager's own spec, not the two-flank `local_geometry`
of FINDINGS §13/§14, which could be fooled by a stem or beam sitting in
one of its two bands): search OUTWARD from the head, column by column, up
to +-4 head widths; a column counts only where ALL FIVE lines are found as
a THIN dark run (<=0.35 of the global spacing thick) within +-0.5 spacing
of where the global read says each one is, consecutive runs are spaced
within 25% of the global spacing, AND the gaps between them carry no other
ink (a stem, a beam, or a ledger would fail this). Take the nearest >=5
clean columns (by |distance| from the head's own centre) and the per-line
MEDIAN across them.
"""
from __future__ import annotations

import collections
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "truth_set_2_44c", Path(__file__).resolve().parent / "truth_set_2_44c.py")
TS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(TS)

from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.pitch_resolver import _pitch_from_position  # noqa: E402

CLEAN_THIN_FRAC = 0.35
CLEAN_LINE_TOL_FRAC = 0.5
CLEAN_SPACING_TOL_FRAC = 0.25
CLEAN_GAP_MAX_INK_FRAC = 0.03
MIN_CLEAN_COLUMNS = 5
SEARCH_HEAD_WIDTHS = 4.0


def _column_dark(gray: "np.ndarray", x: int, y0: int, y1: int) -> "np.ndarray":
    H = gray.shape[0]
    y0, y1 = max(0, y0), min(H, y1)
    if y1 <= y0:
        return np.zeros(0, dtype=bool)
    return gray[y0:y1, x] < 128


def _thin_run_near(dark: "np.ndarray", y0: int, center_local: float,
                   max_thick: float) -> Optional[Tuple[float, float]]:
    """`(y_abs, thickness)` of the contiguous dark run covering
    `center_local` (an index into `dark`), or `None` if there is none, it
    is not THIN, or `center_local` itself is not dark."""
    n = len(dark)
    c = int(round(center_local))
    if c < 0 or c >= n or not dark[c]:
        return None
    lo = c
    while lo - 1 >= 0 and dark[lo - 1]:
        lo -= 1
    hi = c
    while hi + 1 < n and dark[hi + 1]:
        hi += 1
    thickness = hi - lo + 1
    if thickness > max_thick:
        return None
    return (y0 + (lo + hi) / 2.0, float(thickness))


def _clean_column(gray: "np.ndarray", x: int, global_lines: Sequence[float],
                  spacing: float) -> Optional[List[float]]:
    if x < 0 or x >= gray.shape[1] or spacing <= 0:
        return None
    tol = spacing * CLEAN_LINE_TOL_FRAC
    max_thick = spacing * CLEAN_THIN_FRAC
    found: List[float] = []
    thicks: List[float] = []
    for gy in global_lines:
        y0, y1 = int(gy - tol), int(gy + tol) + 1
        dark = _column_dark(gray, x, y0, y1)
        if dark.size == 0:
            return None
        center_local = gy - y0
        hit = _thin_run_near(dark, y0, center_local, max_thick)
        if hit is None:
            return None
        found.append(hit[0])
        thicks.append(hit[1])
    # consecutive spacing close to the global one
    for a, b in zip(found, found[1:]):
        if abs((b - a) - spacing) > spacing * CLEAN_SPACING_TOL_FRAC:
            return None
    # nothing else inked in the gaps -- margins are each line's OWN
    # measured half-thickness (+1 px slack), not a fixed guess, so the
    # gap test never re-tests the line's own edge pixels as "other ink".
    col_full = gray[:, x] < 128
    for (a, ta), (b, tb) in zip(zip(found, thicks), zip(found[1:], thicks[1:])):
        gap_lo = int(a + ta / 2.0) + 2
        gap_hi = int(b - tb / 2.0) - 1
        if gap_hi <= gap_lo:
            continue
        gap = col_full[gap_lo:gap_hi]
        if gap.size and gap.mean() > CLEAN_GAP_MAX_INK_FRAC:
            return None
    return found


#: Sean, via manager: "the note's centre is measured, not assumed" -- the
#: head's own ink rows (staff/ledger rows excluded), falling back to the
#: detector box centre only where the ink cannot be separated.
NOTE_INK_ROW_THRESHOLD = 0.15
NOTE_INK_LINE_EXCLUDE_FRAC = 0.3


def note_ink_centre(gray: "np.ndarray", px0: float, py0: float, px1: float,
                    py1: float, global_lines: Sequence[float], spacing: float
                    ) -> Tuple[float, str]:
    """`(centre_y, source)`, `source` in `{"ink", "fallback"}`. Scans the
    head's own box (padded a third of a space either way, so a head
    sitting flush with its own box edge is not clipped) for the row with
    densest ink in `[px0, px1]`, excluding rows within a staff/ledger
    line's own thin band, then widens to the contiguous inked run around
    it -- the SAME two-sided expansion `_thin_run_near` uses for a line,
    applied here to the head's own blob instead. Falls back to the
    detector box's own centre where no row clears the ink threshold (the
    'ink cannot be separated' case -- a merged cluster, or a box with no
    unexcluded ink at all)."""
    pad = spacing * 0.3
    x0, x1 = int(px0), int(px1)
    y0, y1 = int(py0 - pad), int(py1 + pad)
    fallback = ((py0 + py1) / 2.0, "fallback")
    if x1 <= x0 or y1 <= y0:
        return fallback
    region = gray[y0:y1, x0:x1] < 128
    if region.size == 0:
        return fallback
    row_frac = region.mean(axis=1)
    rows_y = np.arange(y0, y1)
    tol = spacing * NOTE_INK_LINE_EXCLUDE_FRAC
    is_line_row = np.zeros(len(rows_y), dtype=bool)
    for gy in global_lines:
        is_line_row |= (np.abs(rows_y - gy) <= tol)
    masked = row_frac.copy()
    masked[is_line_row] = 0.0
    if masked.max() < NOTE_INK_ROW_THRESHOLD:
        return fallback
    idx = int(np.argmax(masked))
    inked = masked > NOTE_INK_ROW_THRESHOLD
    lo = idx
    while lo - 1 >= 0 and inked[lo - 1]:
        lo -= 1
    hi = idx
    while hi + 1 < len(inked) and inked[hi + 1]:
        hi += 1
    return (y0 + (lo + hi) / 2.0, "ink")


#: `Q.NOTEHEAD_STAFF_POSITION`'s own top-line-origin half-step units: top
#: line = 0, each successive line/space = +1, so the middle (3rd of 5)
#: line = 4 and the bottom line = 8.
ANCHOR_TOP_OFFSET = 0
ANCHOR_MID_OFFSET = 4
ANCHOR_BOTTOM_OFFSET = 8


def three_anchor_positions(note_centre: float, local_lines: Sequence[float],
                           local_half_step: float, above_staff: bool
                           ) -> Dict[str, int]:
    """The SAME note centre and local half-step, read off THREE different
    anchors (Sean, via manager -- unsure which is more robust to a bent
    page, so all three are scored): the local TOP line, the local MIDDLE
    line, and the local OUTER line NEAREST the note (top if the note is
    above the staff, bottom if below) -- the nearest-outer anchor needs
    the SHORTEST extrapolation of the three for a far note, at the cost of
    never being checked by a line on the note's own side for an in-staff
    head (not reached here; this function is only called for far heads)."""
    anchors = {
        "top": (local_lines[0], ANCHOR_TOP_OFFSET),
        "middle": (local_lines[2], ANCHOR_MID_OFFSET),
        "nearest_outer": ((local_lines[0], ANCHOR_TOP_OFFSET) if above_staff
                         else (local_lines[-1], ANCHOR_BOTTOM_OFFSET)),
    }
    out = {}
    for name, (anchor_y, offset) in anchors.items():
        steps = offset + (note_centre - anchor_y) / local_half_step
        out[name] = int(round(steps))
    return out


def robust_local_lines(gray: "np.ndarray", head_cx: float, head_x0: float,
                       head_x1: float, head_w: float,
                       global_lines: Sequence[float], spacing: float
                       ) -> Tuple[Optional[List[float]], int]:
    """`(median_lines_or_None, n_clean_found)`. Searches outward from the
    head's own edges (never through its own ink) up to
    `SEARCH_HEAD_WIDTHS` head-widths either side, nearest first."""
    max_dist = int(SEARCH_HEAD_WIDTHS * max(head_w, 1.0))
    collected: List[List[float]] = []
    for d in range(1, max_dist + 1):
        for x in (int(head_x0) - d, int(head_x1) + d):
            cols = _clean_column(gray, x, global_lines, spacing)
            if cols is not None:
                collected.append(cols)
        if len(collected) >= MIN_CLEAN_COLUMNS:
            break
    if len(collected) < MIN_CLEAN_COLUMNS:
        return None, len(collected)
    arr = np.array(collected)   # (n, 5)
    return [float(v) for v in np.median(arr, axis=0)], len(collected)


def analyse(doc_id: str) -> None:
    loaded = TS.load_doc(doc_id)
    rows = TS.build_rows(doc_id, loaded)
    rec = loaded["rec"]
    gray = loaded["gray"]

    scored = [r for r in rows if r["truth_pitches"]]
    print(f"=== {doc_id} === scored far heads: {len(scored)}")

    too_few = 0
    drift_right: List[float] = []
    drift_wrong: List[float] = []
    mid_drift_right: List[float] = []
    mid_drift_wrong: List[float] = []
    dev_right: List[float] = []
    dev_wrong: List[float] = []
    predicted_hits = 0
    predicted_total = 0
    centre_source: "collections.Counter[str]" = collections.Counter()
    variant_tally: Dict[str, "collections.Counter[str]"] = {
        "top": collections.Counter(), "middle": collections.Counter(),
        "nearest_outer": collections.Counter()}
    variant_hist: Dict[str, "collections.Counter[Any]"] = {
        "top": collections.Counter(), "middle": collections.Counter(),
        "nearest_outer": collections.Counter()}

    LETTER = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}

    def letter_octave(name):
        if not name:
            return None
        letter = name[0]
        rest = name[1:]
        i = 0
        while i < len(rest) and rest[i] in "#b":
            i += 1
        try:
            octv = int(rest[i:])
        except ValueError:
            return None
        return letter, octv

    def height(p):
        return p[1] * 7 + LETTER[p[0]]

    for r in scored:
        sub = r["subject"]
        page, system, staff = (int(x) for x in sub.split("/")[1:4])
        staff_key = f"staff/{page}/{system}/{staff}"
        line_rows = rec.obs(Q.STAFF_LINES, staff_key)
        box = r.get("page_box")
        if not line_rows or not box:
            continue
        global_lines = sorted(float(y) for y in line_rows[-1]["value"])
        global_top = global_lines[0]
        global_spacing = (global_lines[-1] - global_lines[0]) / 4.0
        if global_spacing <= 0:
            continue
        px0, py0, px1, py1 = box
        cx = (px0 + px1) / 2.0
        head_w = px1 - px0 if px1 > px0 else global_spacing
        local_lines, n_clean = robust_local_lines(
            gray, cx, px0, px1, head_w, global_lines, global_spacing)
        if local_lines is None:
            too_few += 1
            continue
        local_top = local_lines[0]
        local_mid = local_lines[2]
        local_spacing = (local_lines[-1] - local_lines[0]) / 4.0
        local_half_step = local_spacing / 2.0
        global_mid = global_lines[2]
        drift = local_top - global_top
        mid_drift = local_mid - global_mid
        dev = local_spacing - global_spacing

        geom = letter_octave(r.get("geom_pitch"))
        truth = tuple(r["truth_pitches"][0])
        if geom is None:
            continue
        is_right = geom == truth
        (drift_right if is_right else drift_wrong).append(drift)
        (mid_drift_right if is_right else mid_drift_wrong).append(mid_drift)
        (dev_right if is_right else dev_wrong).append(dev)

        # --- prediction: predicted px error = drift + dev * steps_from_staff
        steps_from_staff = r["raw_pos"]   # signed half-steps, geometry's own
        predicted_px = drift + dev * steps_from_staff
        predicted_diatonic = predicted_px / global_spacing   # 1 space = 1 diatonic step at a line/space pattern? NB: half_step=1 diatonic step
        actual_diff = height(geom) - height(truth)
        predicted_total += 1
        if not is_right:
            # predicted direction matches actual error's sign, and within 1 step of magnitude
            if (predicted_diatonic == 0 and actual_diff == 0) or (
                    predicted_diatonic != 0 and
                    (predicted_diatonic > 0) == (actual_diff > 0) and
                    abs(round(predicted_diatonic) - actual_diff) <= 1):
                predicted_hits += 1

        # --- three-anchor robust local geometry, note's measured centre
        clef_v = rec.value(Q.CLEF, staff_key)
        note_centre, source = note_ink_centre(gray, px0, py0, px1, py1,
                                              global_lines, global_spacing)
        centre_source[source] += 1
        above_staff = steps_from_staff < 0
        positions = three_anchor_positions(note_centre, local_lines,
                                           local_half_step, above_staff)
        for name, pos in positions.items():
            tally = variant_tally[name]
            hist = variant_hist[name]
            if clef_v is None:
                tally["unscored"] += 1
                continue
            vp = letter_octave(_pitch_from_position(pos, str(clef_v)))
            if vp is None:
                tally["unscored"] += 1
                continue
            if vp == truth:
                tally["right"] += 1
                hist[0] += 1
            else:
                tally["wrong"] += 1
                d = height(vp) - height(truth)
                hist[d if d in (-2, -1, 0, 1, 2) else
                    ("octave" if abs(d) == 7 else "other")] += 1

    def mean(xs):
        return sum(xs) / len(xs) if xs else float("nan")

    print(f"too few clean columns: {too_few} / {len(scored)}")
    print(f"TOP-line drift (px): right mean={mean(drift_right):.2f} n={len(drift_right)}  "
         f"wrong mean={mean(drift_wrong):.2f} n={len(drift_wrong)}")
    print(f"MIDDLE-line drift (px): right mean={mean(mid_drift_right):.2f} "
         f"n={len(mid_drift_right)}  wrong mean={mean(mid_drift_wrong):.2f} "
         f"n={len(mid_drift_wrong)}")
    print(f"spacing dev (px): right mean={mean(dev_right):.3f} n={len(dev_right)}  "
         f"wrong mean={mean(dev_wrong):.3f} n={len(dev_wrong)}")
    print(f"prediction (drift + dev*steps) explains {predicted_hits} of "
         f"{predicted_total - len(drift_right)} geometry misses "
         f"(sign match, within 1 step)")
    print(f"note-centre source: {dict(centre_source)}")
    for name in ("top", "middle", "nearest_outer"):
        print(f"anchor={name:<14} {dict(variant_tally[name])}  "
             f"hist={dict(variant_hist[name])}")


def main() -> int:
    for doc_id in TS.DOCS:
        analyse(doc_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
