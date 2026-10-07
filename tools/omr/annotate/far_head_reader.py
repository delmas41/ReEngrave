"""The far-head ledger reader, as ONE callable (ROADMAP 2.56, 2026-10-04).

Today's pieces, each keyword-gated OFF where it lives, in the exact
combination Sean accepted -- arm E3 of
`benchmarks/omr-local-staff-2026-09/score_combined_1004.py` (Litolff 40/3/1
of 44, Brahms 11/0/0):

  * `ledger_grid` round 8 + fix 1 (near-edge ledger) + the far-side rule,
  * the exclusion rules `connected` / `one_sided` /
    `drop_same_ink_other_staff`, and `drop_rungs_beyond_head`
    (`own_box` is REFUSED and never on),
  * `standard_head_box`: the page-measured head size, centred by the
    template's free search, used ONLY where its pre-set fit gate passes
    (IoU >= 0.70, offset <= 0.15 sp), the half note's counter filled first.

This module ports the benchmark scorer's plumbing (page head shape, page
templates, the per-head local staff lines, the position derivation) so the
STAGED gather can call it: nothing here imports `benchmarks/`, nothing here
reads a record, a truth file or a reference. It is pure arrays and boxes in,
(position, reason) out. Every constant the scorer set is kept as the scorer
had it; where a port had to choose, the choice is named in a comment.

Page frame throughout: PAGE PIXELS of the raster the boxes were measured on.
A position is in half-steps from the staff's top line (0..8 on the staff,
negative above, >8 below) -- `Q.NOTEHEAD_STAFF_POSITION`'s unit.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from . import head_template as ht
from . import ledger_grid as lg
from . import standard_head_box as shb

# ---------------------------------------------------------------------------
# The accepted combination (arm E3), named once.
# ---------------------------------------------------------------------------
READER_KEYWORDS: Dict[str, bool] = dict(
    near_edge_ledgers=True, restore_masked_near_edge=True,
    far_side_ledger=True, drop_beyond_head=True,
    drop_same_ink_other_staff=True,
    # lane-through-head-on (E5): a ledger through the head means the head is on it
    through_head_on_rung=True,
    # lane-farhead-note-first (2026-10-05, Sean's order): the note's own line
    # first, then the count to it, which must fit the gap. False = the run-2
    # reader (count outward from the staff), bit-identical.
    note_first=True,
    # lane-ledger-not-text (Sean 2026-10-05): a rung counted between must not be text ink
    ledger_not_text=True,
    # lane-farhead-not-a-note (Sean 2026-10-05): a box the record's own evidence says is NOT a notehead
    # (a barline, a tremolo slash, text, a sliver) is refused (abstained, never deleted) before it is read.
    not_a_note=True,
    # lane-edge-vs-through (Sean 2026-10-06): a middle rung the page does not show as a line is not taken
    # over a visible line at the head's staff-side edge (the head hangs beyond that line: the space).
    edge_vs_through=True,
    # lane-farhead-per-bar-grid (Sean 2026-10-06): the lines a head is read against start from the PER-BAR grid of the
    # bar it stands in (what `gather_notehead_positions` uses for the in-staff positions), not the staff-wide raw
    # lines, and are re-found only within PER_BAR_GRID_WINDOW_SP of that grid, at the CENTRE of the dark run.
    # False = the old flank re-measure (+-0.5 sp, the line's top row), bit-identical, on whatever lines are passed.
    per_bar_grid=True,
    # lane-edge-merge-unseen-ledgers (Sean 2026-10-06, "fix the edge-merging rule"; ROADMAP 2.57b), the three causes
    # that lost a ledger the print shows plainly. False = the old reader, bit-identical.
    #  edge_jut_kept: the edge collapse never drops a rung that shows a thin flat jut past the head;
    #  split_welded_bands: a region of long rows (a head body wider than the floor) holds every ledger plateau;
    #  walk_tol: the ledger walk's window is widened by WALK_CENTRE_TOL_PX at both ends (a gap between two band centres
    #            is known to +-half a pixel). OFF -- MEASURED AND REFUSED (FINDINGS 2026-10-06 lane-edge-merge-unseen-ledgers): it
    #            rescues one head (Litolff night 12) and moves five right Brahms heads to a wrong ledger count, because
    #            a head's own interior row sits only 0.57-0.65 of the last gap from it, on the same knife edge;
    #  rows_clear_of_box: a rung more than half a line thickness clear of the box's rows is not the head's own widest
    #            row, so it need not be wider than the head.
    edge_jut_kept=True, split_welded_bands=True, walk_tol=False, rows_clear_of_box=True)
#: band centres sit on a half-pixel grid, so two gaps compared by the walk window are each known to half a pixel
WALK_CENTRE_TOL_PX = 0.5
#: lane-chord-blob-split (E4): ONE blob laid over by exactly two same-staff
#: detector boxes that print over each other >= CHORD_SPLIT_OVERPRINT_SP is two
#: heads a third apart; split it into two standard boxes and place the ledger
#: between them. Off = bit-identical to the unsplit reader.
CHORD_SPLIT = True
CHORD_SPLIT_OVERPRINT_SP = 0.2
EXCLUSION_RULES: Dict[str, bool] = dict(connected=True, one_sided=True,
                                        jut_from_ink=True)

#: A page with fewer clean on-line heads than this has no MEASURED head shape
#: (`score_standard_box.MIN_PAGE_SHAPE_HEADS`). The scorer fell back to the
#: whole document's shape there; a per-page gather cannot see the document, so
#: the reader ABSTAINS (`no_page_shape`) rather than borrow a size.
MIN_PAGE_SHAPE_HEADS = 8

ACCIDENTAL_CLASSES = frozenset({
    "accidentalFlat", "accidentalSharp", "accidentalNatural",
    "accidentalDoubleFlat", "accidentalDoubleSharp"})

# --- shape measurement (shape_from_page.py, constants unchanged) -----------
OPEN_DIAMETER_SPACES = 0.42
WIN_HALF_SPACES = 1.25
NOMINAL_HALF_W_SPACES = 0.68
NOMINAL_HALF_H_SPACES = 0.55
ISOLATION_GAP_SPACES = 1.0
ISOLATION_CLASSES = ("notehead", "accidental", "rest")
AREA_SP2 = (0.7, 1.45)
LONG_AXIS_SP = (1.0, 1.8)
SOLIDITY_MIN = 0.90
ELLIPSE_IOU_MIN = 0.85
ECC_MIN_FOR_ANGLE = 1.12
MIN_DETECTOR_SCORE = 0.5
NON_HEAD_CLASS_WORDS = ("rest", "clef", "dynamic", "accidental", "fermata",
                        "ornament", "ottava", "time", "key")
OVERLAP_FRACTION_MAX = 0.20
STEM_RUN_SPACES = (2.0, 6.5)
STEM_REACH_PAST_HEAD_SPACES = 1.0
CUT_SPACES = 0.3                      # template_review_r7.CUT_SPACES
DEFAULT_THICKNESS_PX = 4.0            # mht._page_line_thickness_px's fallback


# ---------------------------------------------------------------------------
# lane-farhead-not-a-note (Sean, DECISIONS 2026-10-05). Of 12 seeded abstentions, 4 were not noteheads: two
# barlines/brackets, a tremolo slash, the "a 2" numeral. The reader is handed whatever the detector boxed as a
# notehead; this refuses a box the record's OWN evidence says is something else. It abstains with a named reason; it
# deletes nothing (the glyph, its box and its geometry row stay on the record).
#
# THRESHOLDS, STATED BEFORE LOOKING (the floors that are not new are IMPORTED from `notehead_precision`, never restated):
#   * on_a_barline : a measure cut (the record's own `cell_box` edge on this staff = where `measure_partition` cut
#                    at a barline) lies INSIDE the box's x extent AND the box is narrower than one staff space.
#                    BARLINE NOTE: the first draft (cut within 0.25 sp of the box, any width) was measured and
#                    refused real heads and dynamic letters (of 12 refusals no other reason made, 4 were real heads,
#                    6 dynamic letters; the cut is only within ~9 px of the barline ink). The conjunction cannot
#                    refuse a head-wide box; see FINDINGS.
#   * on_text      : a detector box of a text/dynamic class (`ledger_grid.is_text_class`) covers at least
#                    TEXT_OVERLAP_MIN (half) of the head box.
#   * tremolo_slash: 2.49's own SHAPE test (angle, elongation, fill) and CROSSING test (each side >= 30% of the
#                    glyph's ink) on the `Q.NOTEHEAD_STEM_CROSS_INK` row. 2.49's POSITION test (away from both stem
#                    ends) is deliberately NOT asked here -- see FINDINGS; the shape and crossing constants are 2.49's.
#   * too_narrow / clipped_fragment : `notehead_precision`'s own floors (1.0 sp wide for noteheadBlack*; under
#                    CLIPPED_NOTEHEAD_MAX_SPACES tall and on the cell's own edge).
#   * decided_not_a_notehead : the record already holds `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` True for the box (a re-read of
#                    a finished record; at GATHER there is no verdict yet and this is simply absent).
# ---------------------------------------------------------------------------
TEXT_OVERLAP_MIN = 0.5

NOT_A_NOTE_WORDS = {
    "decided_not_a_notehead": "the record already decided this box is not a notehead ({detail})",
    "on_a_barline": "a barline: the record's own measure cut runs through this box",
    "tremolo_slash": "a tremolo slash: a diagonal stroke across its stem, ink on both sides",
    "on_text": "text: a text or dynamic box the record holds lies over this box",
    "too_narrow": "too narrow to be a notehead (under one staff space wide)",
    "clipped_fragment": "a sliver cut off by the edge of its measure cell",
}


def _precision():
    # lazy: staged -> annotate is the usual direction; this reads two floors and two pure tests back
    from ..staged.adjudicators import notehead_precision as NP
    return NP


def not_a_note_reason(box, cls, spacing, *, cell_box=None, cross=None, barline_xs=(), text_boxes=(),
                      decided=None) -> Optional[Dict[str, Any]]:
    """Why this far "notehead" box is something else, or `None`. Pure: a box, its class, the local staff spacing
    (page px) and the record's own evidence about it. `dict(reason, words, drawn, also)`: `drawn` is the evidence to
    draw, `[(kind, geometry)]`; `also` every other reason that fired (the first in ORDER is the one named)."""
    if spacing is None or spacing <= 0:
        return None
    x0, y0, x1, y1 = (float(v) for v in box)
    NP = _precision()
    fired: List[Tuple[str, Any]] = []
    if decided:
        fired.append(("decided_not_a_notehead", decided))
    # a cut INSIDE the box, on a box narrower than a head (see the BARLINE note above: a margin test refused real
    # heads and dynamic letters that merely stood near a cut)
    cuts = ([float(x) for x in (barline_xs or ()) if x0 <= float(x) <= x1]
            if (x1 - x0) / spacing < NP.TOO_NARROW_MIN_SPACES else [])
    if cuts:
        fired.append(("on_a_barline", [("barline", min(cuts, key=lambda x: abs(x - (x0 + x1) / 2.0)))]))
    if cross and NP._tremolo_shape_ok(cross) and NP._tremolo_crossing_ok(cross):
        fired.append(("tremolo_slash", [("slash", (x0, y0, x1, y1))]))
    area = max(1e-9, (x1 - x0) * (y1 - y0))
    for tb in text_boxes or ():
        ox, oy = min(x1, tb[2]) - max(x0, tb[0]), min(y1, tb[3]) - max(y0, tb[1])
        if ox > 0 and oy > 0 and ox * oy / area >= TEXT_OVERLAP_MIN:
            fired.append(("on_text", [("text", tuple(tb))]))
            break
    if (str(cls or "").lower().startswith(NP.TOO_NARROW_CLASS_PREFIX)
            and (x1 - x0) / spacing < NP.TOO_NARROW_MIN_SPACES):
        fired.append(("too_narrow", [("box", (x0, y0, x1, y1))]))
    if cell_box is not None and (y1 - y0) / spacing < NP.CLIPPED_NOTEHEAD_MAX_SPACES:
        tol = NP.CELL_EDGE_TOLERANCE_PAGE_PX
        top, bot = abs(y0 - cell_box[1]) <= tol, abs(y1 - cell_box[3]) <= tol
        if top or bot:
            fired.append(("clipped_fragment", [("cell_edge", cell_box[1] if top else cell_box[3])]))
    if not fired:
        return None
    reason, detail = fired[0]
    words = NOT_A_NOTE_WORDS[reason].format(detail=detail if isinstance(detail, str) else "")
    drawn = detail if isinstance(detail, list) else []
    return dict(reason=reason, words=words, drawn=drawn, also=[r for r, _ in fired[1:]])


def head_kind(cls: Optional[str]) -> Optional[str]:
    """`filled` / `hollow` from the detector class name; `None` for neither."""
    cls = cls or ""
    if "Black" in cls:
        return "filled"
    if "Half" in cls or "Whole" in cls:
        return "hollow"
    return None


# ---------------------------------------------------------------------------
# local staff lines at a head's own x (truth_set_2_44c.local_staff_lines)
# ---------------------------------------------------------------------------
def _darkest_row(gray, x0: int, x1: int, y_lo: int, y_hi: int) -> Optional[float]:
    H, W = gray.shape
    x0, x1 = max(0, x0), min(W, x1)
    y_lo, y_hi = max(0, y_lo), min(H, y_hi)
    if x1 <= x0 or y_hi <= y_lo:
        return None
    band = gray[y_lo:y_hi, x0:x1].astype(float)
    row_mean = band.mean(axis=1)
    k = int(np.argmin(row_mean))
    if row_mean[k] >= np.median(row_mean) - 8.0:
        return None
    return float(y_lo + k)


def local_staff_lines(gray, global_lines: Sequence[float], head_x0: float,
                      head_x1: float, head_width: float) -> Optional[List[float]]:
    """The five lines re-measured in the two flanking bands of a head; `None`
    only where NEITHER flank finds all five."""
    spacing = (max(global_lines) - min(global_lines)) / 4.0
    if spacing <= 0:
        return None
    gap = head_width
    bands = [(int(head_x0 - gap - head_width), int(head_x0 - gap)),
             (int(head_x1 + gap), int(head_x1 + gap + head_width))]
    per_flank: List[List[float]] = []
    for x0, x1 in bands:
        lines = []
        for gy in sorted(global_lines):
            y = _darkest_row(gray, x0, x1, int(gy - spacing * 0.5),
                             int(gy + spacing * 0.5) + 1)
            if y is None:
                break
            lines.append(y)
        if len(lines) == 5:
            per_flank.append(lines)
    if not per_flank:
        return None
    return [sum(v) / len(v) for v in zip(*per_flank)]


def frame_lines_for_head(gray, global_lines: Sequence[float],
                         box: Sequence[float]) -> List[float]:
    """The staff's five lines AT THIS HEAD'S x; the global read unchanged only
    where neither flank finds all five (a declined local read is not an
    invented one). With `READER_KEYWORDS["per_bar_grid"]` the lines passed are
    the bar's own grid and `grid_lines_for_head` does the (narrower) re-find."""
    x0, _y0, x1, _y1 = box
    w = x1 - x0
    if READER_KEYWORDS.get("per_bar_grid"):
        return grid_lines_for_head(gray, list(global_lines), x0, x1, w if w > 0 else 20.0)
    loc = local_staff_lines(gray, list(global_lines), x0, x1, w if w > 0 else 20.0)
    return loc if loc is not None else list(global_lines)


# ---------------------------------------------------------------------------
# lane-farhead-per-bar-grid (Sean 2026-10-06). The raw staff-wide lines sit off the ink by the staff's tilt (p90 5.5 px,
# max ~19 px on Litolff); the per-bar grid in-staff positions already use is close to it. The old re-find searched
# +-0.5 sp around the RAW line, so where that line was >= 0.5 sp off it landed one line over, and took the line's TOP
# row, ~1.5 px high. THRESHOLDS, STATED BEFORE LOOKING: window +-0.3 sp of the grid line, one line per window, the
# CENTRE of the dark run (half-depth), never two lines within 0.5 sp (both go back to the grid and are counted).
# ---------------------------------------------------------------------------
PER_BAR_GRID_WINDOW_SP = 0.3
PER_BAR_GRID_MIN_SEPARATION_SP = 0.5
#: how often the re-find had to use the grid's own position (counted, never silent)
GRID_STATS: Dict[str, int] = dict(lines=0, refound=0, from_grid_not_found=0, from_grid_pair=0)


def cell_grid_page_lines(cell) -> Optional[List[float]]:
    """The five lines of ONE bar's grid in PAGE pixels -- the very rows
    `staged.gather._cell_grid` takes `top_y` and `half_step` from
    (`staff_line_ys_canonical`, which holds `staff.line_ys` plus the cell's own
    localized shift), carried back by the cell's own origin and scale. None
    where the cell has no grid."""
    ys = list(getattr(cell, "staff_line_ys_canonical", None) or [])
    bbox = getattr(cell, "bbox_page_px", None)
    up = getattr(cell, "upscale_factor", None)
    if len(ys) < 2 or not bbox or not up:
        return None
    return [float(bbox[1]) + float(y) / float(up) for y in ys]


def _dark_run_centre(gray, x0: int, x1: int, lo: int, hi: int,
                     ext_lo: int, ext_hi: int) -> Optional[float]:
    """Centre (midpoint of top and bottom row) of the dark run whose darkest
    row lies in [lo, hi); the run is the contiguous rows at or below the
    half-depth between that row and the band's median, looked for in
    [ext_lo, ext_hi). None where no row stands out (`_darkest_row`'s test)."""
    H, W = gray.shape
    x0, x1 = max(0, x0), min(W, x1)
    ext_lo, ext_hi = max(0, ext_lo), min(H, ext_hi)
    lo, hi = max(lo, ext_lo), min(hi, ext_hi)
    if x1 <= x0 or hi <= lo:
        return None
    rows = gray[ext_lo:ext_hi, x0:x1].astype(float).mean(axis=1)
    k = lo - ext_lo + int(np.argmin(rows[lo - ext_lo:hi - ext_lo]))
    med = float(np.median(rows))
    if rows[k] >= med - 8.0:
        return None
    thr = (rows[k] + med) / 2.0
    a = b = k
    while a - 1 >= 0 and rows[a - 1] <= thr:
        a -= 1
    while b + 1 < len(rows) and rows[b + 1] <= thr:
        b += 1
    return float(ext_lo) + (a + b) / 2.0


def grid_lines_for_head(gray, grid: Sequence[float], head_x0: float,
                        head_x1: float, head_width: float) -> List[float]:
    """The bar's grid lines re-found at the head's own flanks, each only within
    PER_BAR_GRID_WINDOW_SP of its grid line, at the centre of the dark run. A
    line not found (in either flank) is the grid's own position, counted; two
    found lines closer than PER_BAR_GRID_MIN_SEPARATION_SP both go back to the
    grid. Never moves a line farther than the window."""
    g = sorted(float(v) for v in grid)
    if len(g) < 2:
        return list(g)
    sp = (g[-1] - g[0]) / (len(g) - 1)
    if sp <= 0:
        return list(g)
    gap = head_width
    bands = [(int(head_x0 - gap - head_width), int(head_x0 - gap)),
             (int(head_x1 + gap), int(head_x1 + gap + head_width))]
    win, ext = PER_BAR_GRID_WINDOW_SP * sp, 0.5 * sp
    found: List[Optional[float]] = []
    for gy in g:
        vals = []
        for bx0, bx1 in bands:
            c = _dark_run_centre(gray, bx0, bx1, int(np.floor(gy - win)), int(np.ceil(gy + win)) + 1,
                                 int(np.floor(gy - ext)), int(np.ceil(gy + ext)) + 1)
            if c is not None and abs(c - gy) <= win:
                vals.append(c)
        found.append(sum(vals) / len(vals) if vals else None)
    sep = PER_BAR_GRID_MIN_SEPARATION_SP * sp
    pair_bad = set()
    for i in range(len(g) - 1):
        if found[i] is not None and found[i + 1] is not None and found[i + 1] - found[i] < sep:
            pair_bad.update((i, i + 1))
    out = []
    for i, gy in enumerate(g):
        GRID_STATS["lines"] += 1
        if i in pair_bad:
            GRID_STATS["from_grid_pair"] += 1
            out.append(gy)
        elif found[i] is None:
            GRID_STATS["from_grid_not_found"] += 1
            out.append(gy)
        else:
            GRID_STATS["refound"] += 1
            out.append(found[i])
    return out


# ---------------------------------------------------------------------------
# page head shape (shape_from_page.py)
# ---------------------------------------------------------------------------
def _moments_shape(mask) -> Optional[Dict[str, float]]:
    m = cv2.moments(mask.astype(np.uint8), binaryImage=True)
    if m["m00"] < 5:
        return None
    mu20, mu02, mu11 = m["mu20"] / m["m00"], m["mu02"] / m["m00"], m["mu11"] / m["m00"]
    tr, det = mu20 + mu02, mu20 * mu02 - mu11 ** 2
    disc = max(0.0, tr * tr / 4.0 - det)
    l1, l2 = tr / 2.0 + disc ** 0.5, max(1e-9, tr / 2.0 - disc ** 0.5)
    theta_img = 0.5 * np.arctan2(2 * mu11, mu20 - mu02)
    return dict(long_px=4.0 * l1 ** 0.5, short_px=4.0 * l2 ** 0.5,
                ecc=(l1 / l2) ** 0.5, tilt_up_right_deg=float(-np.degrees(theta_img)),
                cx=m["m10"] / m["m00"], cy=m["m01"] / m["m00"], area=m["m00"])


def _head_blob(gray, box, lines, spacing, thickness_px) -> Dict[str, Any]:
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    hw = int(round(WIN_HALF_SPACES * spacing))
    wx0, wy0 = int(round(cx)) - hw, int(round(cy)) - hw
    wx1, wy1 = wx0 + 2 * hw + 1, wy0 + 2 * hw + 1
    H, W = gray.shape
    if wx0 < 0 or wy0 < 0 or wx1 > W or wy1 > H:
        return dict(ok=False, reason="window_off_page")
    win = gray[wy0:wy1, wx0:wx1]
    ink = win <= ht._otsu_threshold(win)
    cxl, cyl = cx - wx0, cy - wy0
    yy, xx = np.mgrid[0:win.shape[0], 0:win.shape[1]]
    nominal = (((xx - cxl) / (NOMINAL_HALF_W_SPACES * spacing)) ** 2
               + ((yy - cyl) / (NOMINAL_HALF_H_SPACES * spacing)) ** 2) <= 1.0
    half = int(round(thickness_px / 2.0)) + 1
    for ly in lines:
        r0, r1 = int(round(ly - wy0)) - half, int(round(ly - wy0)) + half + 1
        r0, r1 = max(0, r0), min(win.shape[0], r1)
        if r1 > r0:
            ink[r0:r1, :] &= nominal[r0:r1, :]
    d = max(3, int(round(OPEN_DIAMETER_SPACES * spacing)) | 1)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))
    op = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, k)
    num, labels = cv2.connectedComponents(op)
    if num <= 1:
        return dict(ok=False, reason="no_blob_after_opening")
    lab = int(labels[int(round(cyl)), int(round(cxl))])
    if lab == 0:
        ov = [(int(((labels == i) & nominal).sum()), i) for i in range(1, num)]
        n_ov, lab = max(ov)
        if n_ov == 0:
            return dict(ok=False, reason="no_blob_at_box_centre")
    blob = labels == lab
    border = np.zeros_like(blob)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    if (blob & border).any():
        return dict(ok=False, reason="blob_touches_window_edge")
    cnts, _ = cv2.findContours(blob.astype(np.uint8), cv2.RETR_EXTERNAL,
                               cv2.CHAIN_APPROX_NONE)
    outer = np.zeros(blob.shape, np.uint8)
    cv2.drawContours(outer, cnts, -1, 1, -1)
    outer = outer.astype(bool)
    hull = cv2.convexHull(max(cnts, key=cv2.contourArea))
    solidity = float(outer.sum() / max(1.0, cv2.contourArea(hull)))
    return dict(ok=True, outer=outer, solidity=solidity)


def measure_clean_head(gray, box, lines, spacing, thickness_px) -> Dict[str, Any]:
    """Blob + gate + moments in staff spaces; `ok` only for a plausible head."""
    b = _head_blob(gray, box, lines, spacing, thickness_px)
    if not b["ok"]:
        return dict(ok=False, reason=b.get("reason", ""))
    ms = _moments_shape(b["outer"])
    if ms is None:
        return dict(ok=False, reason="empty")
    area_sp2 = ms["area"] / spacing ** 2
    long_sp, short_sp = ms["long_px"] / spacing, ms["short_px"] / spacing
    ell = np.zeros(b["outer"].shape, np.uint8)
    cv2.ellipse(ell, (int(round(ms["cx"])), int(round(ms["cy"]))),
                (max(1, int(round(ms["long_px"] / 2))), max(1, int(round(ms["short_px"] / 2)))),
                -ms["tilt_up_right_deg"], 0, 360, 1, -1)
    ell = ell.astype(bool)
    ell_iou = float((ell & b["outer"]).sum() / max(1, (ell | b["outer"]).sum()))
    reason = ""
    if ell_iou < ELLIPSE_IOU_MIN:
        reason = "not_oval"
    elif not (AREA_SP2[0] <= area_sp2 <= AREA_SP2[1]):
        reason = "area"
    elif not (LONG_AXIS_SP[0] <= long_sp <= LONG_AXIS_SP[1]):
        reason = "long_axis"
    elif b["solidity"] < SOLIDITY_MIN:
        reason = "solidity"
    return dict(ok=(reason == ""), reason=reason, long_sp=long_sp, short_sp=short_sp,
                tilt=ms["tilt_up_right_deg"], angle_defined=ms["ecc"] >= ECC_MIN_FOR_ANGLE)


def _symbol_gate(gray, h, page_boxes) -> bool:
    """Is this in-staff box plausibly a real head (detector score, no other
    symbol over it, a stem on the print for a filled head)?"""
    x0, y0, x1, y1 = h["box"]
    sp = h["spacing"]
    score = h.get("score")
    if score is None or score < MIN_DETECTOR_SCORE:
        return False
    area = max(1.0, (x1 - x0) * (y1 - y0))
    for (sub, cls, b) in page_boxes:
        if sub == h["subject"] or not any(w in cls.lower() for w in NON_HEAD_CLASS_WORDS):
            continue
        ox, oy = min(x1, b[2]) - max(x0, b[0]), min(y1, b[3]) - max(y0, b[1])
        if ox > 0 and oy > 0 and ox * oy / area > OVERLAP_FRACTION_MAX:
            return False
    if "Black" in (h.get("cls") or ""):
        H, W = gray.shape
        ry0, ry1 = max(0, int(y0 - 7 * sp)), min(H, int(y1 + 7 * sp))
        rx0, rx1 = max(0, int(x0 - 0.5 * sp)), min(W, int(x1 + 0.5 * sp))
        win = gray[ry0:ry1, rx0:rx1]
        ink = win <= ht._otsu_threshold(win)
        hy0, hy1 = int(y0) - ry0, int(y1) - ry0
        bands = [(int(x0 - 0.2 * sp) - rx0, int(x0 + 0.35 * sp) - rx0),
                 (int(x1 - 0.35 * sp) - rx0, int(x1 + 0.2 * sp) - rx0)]
        best = 0.0
        for c0, c1 in bands:
            for c in range(max(0, c0), min(ink.shape[1], c1 + 1)):
                col = ink[:, c]
                r = (hy0 + hy1) // 2
                if not col[min(max(r, 0), len(col) - 1)]:
                    continue
                a = r
                while a - 1 >= 0 and col[a - 1]:
                    a -= 1
                b_ = r
                while b_ + 1 < len(col) and col[b_ + 1]:
                    b_ += 1
                ext_up, ext_dn = (hy0 - a) / sp, (b_ - hy1) / sp
                run = (b_ - a + 1) / sp
                if (STEM_RUN_SPACES[0] <= run <= STEM_RUN_SPACES[1]
                        and max(ext_up, ext_dn) >= STEM_REACH_PAST_HEAD_SPACES):
                    best = max(best, run)
        if best == 0.0:
            return False
    return True


def page_line_thickness_px(gray, staff_lines_by_key: Dict[str, Sequence[float]],
                           notehead_boxes: Sequence[Tuple[str, tuple]]) -> float:
    """The page's staff-line thickness: the median dark run on the first
    staff's lines, sampled left of the first 30 noteheads
    (`measure_head_tilt._page_line_thickness_px`'s own rule)."""
    ranges = [(b[0] - 40, b[0] - 10) for (_s, b) in notehead_boxes[:30]]
    page_lines: List[float] = []
    for key in sorted(staff_lines_by_key)[:1]:
        page_lines = [float(y) for y in staff_lines_by_key[key]]
    t = None
    if page_lines and ranges:
        vals: List[float] = []
        for ly in page_lines:
            for (x0, x1) in ranges:
                x0i, x1i = max(0, int(x0)), min(gray.shape[1], int(x1))
                if x1i <= x0i:
                    continue
                y0i, y1i = max(0, int(ly) - 4), min(gray.shape[0], int(ly) + 5)
                band = gray[y0i:y1i, x0i:x1i]
                if band.size == 0:
                    continue
                thr = lg._otsu_threshold(band)
                run = float(((band <= thr).mean(axis=1) > 0.5).sum())
                if run > 0:
                    vals.append(run)
        t = float(np.median(vals)) if vals else None
    return t or DEFAULT_THICKNESS_PX


# ---------------------------------------------------------------------------
# the per-page context
# ---------------------------------------------------------------------------
def pooled_shape(samples: Sequence[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    """The median head shape of `samples` (clean on-line heads, from one page
    or pooled over a document); `None` below `MIN_PAGE_SHAPE_HEADS`."""
    if len(samples) < MIN_PAGE_SHAPE_HEADS:
        return None
    med = lambda k: float(np.median([m[k] for m in samples]))
    return dict(width_sp=med("long_sp"), height_sp=med("short_sp"), tilt_deg=med("tilt"))


class FarHeadPage:
    """Everything the reader needs from ONE page, measured once.

    `heads`: every notehead on the page as dicts with `subject`, `box` (page
    px), `pos` (the geometry position, int), `cls`, `score`, `global_lines`.
    `page_boxes`: every detection `(subject, class, box)` on the page.
    `staff_lines_by_key`: `staff/p/s/st` -> its five global lines.

    `shape` is `None` until a shape is adopted: this page's own where it has
    `MIN_PAGE_SHAPE_HEADS` clean on-line heads, else a pooled document shape
    handed in through `adopt` (the scorer's own fallback). `read` abstains
    (`no_page_shape`) while there is none.
    """

    def __init__(self, gray, heads: Sequence[Dict[str, Any]],
                 page_boxes: Sequence[Tuple[str, str, tuple]],
                 staff_lines_by_key: Dict[str, Sequence[float]],
                 not_a_note: Optional[Dict[str, Dict[str, Any]]] = None):
        self.gray = gray
        # lane-farhead-not-a-note: per far-head subject, the record's evidence that the box may not be a note --
        # `dict(cell_box, cross, barline_xs, decided)`; absent = no evidence = never refused for want of it
        self.not_a_note: Dict[str, Dict[str, Any]] = dict(not_a_note or {})
        self.page_boxes = list(page_boxes)
        self.nh = [(h["subject"], tuple(h["box"])) for h in heads]
        self.acc = [(s, b) for (s, c, b) in self.page_boxes if c in ACCIDENTAL_CLASSES]
        # lane-ledger-not-text: the record's own text / dynamic boxes
        self.text_boxes = [tuple(b) for (_s, c, b) in self.page_boxes if lg.is_text_class(c)]
        self.thickness = page_line_thickness_px(gray, staff_lines_by_key, self.nh)
        in_staff = [h for h in heads if 0 <= h["pos"] <= 8 and head_kind(h.get("cls"))]
        spacings, on = [], []
        for h in in_staff:
            lines = frame_lines_for_head(gray, h["global_lines"], h["box"])
            sp = (max(lines) - min(lines)) / 4.0
            spacings.append(sp)
            if head_kind(h["cls"]) != "filled" or h["pos"] % 2 != 0:
                continue
            hh = dict(h, spacing=sp)
            if not self._isolated(hh):
                continue
            if not _symbol_gate(gray, hh, self.page_boxes):
                continue
            meas = measure_clean_head(gray, h["box"], lines, sp, self.thickness)
            if meas["ok"] and meas["angle_defined"]:
                on.append(meas)
        self.samples = on                       # this page's clean on-line heads
        self.n_on_line = len(on)
        if not spacings:
            # no in-staff head on this page to measure the LOCAL spacing from:
            # the staves' own global spacing (every far head's own spacing is
            # still re-measured locally at read time)
            spacings = [(max(v) - min(v)) / 4.0
                        for v in staff_lines_by_key.values() if len(v) >= 2]
        self.med_sp = float(np.median(spacings)) if spacings else None
        self.shape: Optional[Dict[str, float]] = None
        self.shape_source: Optional[str] = None
        self.templates = None
        own = pooled_shape(on)
        if own is not None:
            self.adopt(own, f"page n={len(on)}")

    def adopt(self, shape: Dict[str, float], source: str) -> bool:
        """Bind a head shape (this page's own, or the document pool's) and
        build the page's templates from it. False where the page has no
        spacing to scale the templates by."""
        if self.med_sp is None or self.med_sp <= 0:
            return False
        self.shape, self.shape_source = dict(shape), source
        tilt = shape["tilt_deg"]
        self.templates = ht.build_geometry_templates(
            {"filled": tilt, "hollow": tilt}, {},
            self.thickness * ht.CANONICAL_PX_PER_SPACE / self.med_sp,
            width_spaces={"filled": shape["width_sp"], "hollow": shape["width_sp"]},
            height_spaces={"filled": shape["height_sp"], "hollow": shape["height_sp"]})
        return True

    def _isolated(self, h) -> bool:
        gap = ISOLATION_GAP_SPACES * h["spacing"]
        x0, y0, x1, y1 = h["box"]
        for (s, c, b) in self.page_boxes:
            if s == h["subject"] or not any(k in c.lower() for k in ISOLATION_CLASSES):
                continue
            if b[0] < x1 + gap and b[2] > x0 - gap and b[1] < y1 + gap and b[3] > y0 - gap:
                return False
        return True

    # -- the standard box, hollow-filled (score_standard_box_hollow) --------
    def _standard_box(self, h, lines, spacing) -> Dict[str, Any]:
        shp, tm = self.shape, self.templates
        gray_f, _info = shb.fill_counter(
            self.gray, h["box"], spacing, self.thickness, shp["height_sp"],
            shp["width_sp"], h["kind"] == "hollow")
        others = [b for (s, b) in self.nh if s != h["subject"]] \
            + [b for (_s, b) in self.acc]
        st = shb.standard_head_box(gray_f, h["box"], spacing, tm, shp, h["kind"], others)
        poly = ht.geometry_outline_poly(st["centre"][0], st["centre"][1], spacing,
                                        shp["tilt_deg"], shp["width_sp"], shp["height_sp"])
        chk = _oval_vs_ink(gray_f, h["box"], spacing, self.thickness, list(lines), poly,
                           st["centre"][0], st["centre"][1])
        iou, off = chk["iou_open"], chk["offset_open_sp"]
        st["fit"] = dict(iou_open=iou, offset_open_sp=off)
        st["pass"] = bool(st["placed"] and off is not None and iou >= shb.FIT_IOU_MIN
                          and off <= shb.FIT_OFFSET_MAX_SPACES)
        return st

    def refuse_not_a_note(self, subject: str, box, cls, spacing) -> Optional[Dict[str, Any]]:
        """`not_a_note_reason` over this subject's own evidence, or `None` (switched off, or no reason)."""
        if not READER_KEYWORDS.get("not_a_note"):
            return None
        ev = self.not_a_note.get(subject) or {}
        return not_a_note_reason(
            box, cls, spacing, cell_box=ev.get("cell_box"), cross=ev.get("cross"),
            barline_xs=ev.get("barline_xs") or (), text_boxes=self.text_boxes, decided=ev.get("decided"))

    def read(self, subject: str, box: Sequence[float], cls: Optional[str],
             global_lines: Sequence[float]) -> Dict[str, Any]:
        """The far head's absolute position: `dict(pos, reason, box_source,
        fit)`. `pos` is `None` (with a reason word) where the reader cannot
        say -- never a default. A box the record's own evidence says is not a
        note abstains `not_a_note:<reason>` before anything is read."""
        if READER_KEYWORDS.get("not_a_note") and len(global_lines) >= 2:
            _lines = frame_lines_for_head(self.gray, global_lines, tuple(float(v) for v in box))
            _sp = (max(_lines) - min(_lines)) / 4.0
            _nan = self.refuse_not_a_note(subject, box, cls, _sp)
            if _nan is not None:
                return dict(pos=None, reason="not_a_note:" + _nan["reason"], box_source=None,
                            not_a_note=_nan, spacing=_sp)
        if self.shape is None:
            return dict(pos=None, reason="no_page_shape", box_source=None,
                        n_on_line=self.n_on_line)
        box = tuple(float(v) for v in box)
        lines = frame_lines_for_head(self.gray, global_lines, box)
        spacing = (max(lines) - min(lines)) / 4.0
        if spacing <= 0:
            return dict(pos=None, reason="bad_spacing", box_source=None)
        h = dict(subject=subject, box=box,
                 kind="hollow" if head_kind(cls) == "hollow" else "filled")
        st = self._standard_box(h, lines, spacing)
        use = tuple(st["box"]) if st["pass"] else box
        box_source = "standard" if st["pass"] else "detector"
        nh, rungs, split = self.nh, None, None
        if CHORD_SPLIT:
            split = self._chord_split(subject, box, lines, spacing)
            if split is not None:
                use, rungs = split["box"], split["rungs_y"]
                box_source = "chord_split"
                # the blob's other head is this head's own ink: not blanked
                nh = [(s, b) for (s, b) in self.nh if s not in split["subjects"]]
        detail: Dict[str, Any] = {}
        pos, reason = read_absolute_position(
            self.gray, lines, use, subject, nh, self.acc,
            chord_split_rungs_y=rungs, detail_out=detail,
            text_boxes=self.text_boxes, thickness_px=self.thickness)
        return dict(pos=pos, reason=reason, box_source=box_source,
                    fit=st["fit"], shape_source=self.shape_source,
                    box_used=tuple(use), lines_used=list(lines), detail=detail,
                    chord_split=None if split is None else dict(
                        partner=split["subjects"][1:], rung_y=split["rung_y"],
                        source=split["source"]))

    def _chord_split(self, subject, box, lines, spacing):
        """The split of this head's blob into two page-standard boxes, or
        None. Only same-staff boxes may share a blob; exactly two (this head
        and one other) are split."""
        stem = subject.split("/")[:4]
        others = [(s, tuple(b)) for (s, b) in self.nh
                  if s != subject and s.split("/")[:4] == stem]
        cl = lg.chord_blob_cluster(box, [b for (_s, b) in others])
        if len(cl) != 2:
            return None
        clset = set(cl[1:])
        subs = [subject] + [s for (s, b) in others if b in clset]
        shp = self.shape
        res = lg.split_chord_blob(
            self.gray, cl, spacing, shp["width_sp"], shp["height_sp"],
            shp["tilt_deg"],
            exclude_boxes=[b for (s, b) in others if s not in subs],
            staff_span=(min(lines), max(lines)),
            min_box_overprint_sp=CHORD_SPLIT_OVERPRINT_SP)
        if not res.get("split"):
            return None
        order = sorted(range(2), key=lambda i: (cl[i][1] + cl[i][3]) / 2.0)
        return dict(box=tuple(res["boxes"][order.index(0)]), rungs_y=res["rungs_y"],
                    rung_y=round(res["rung_y"], 1), source=res["rung_source"],
                    subjects=subs)


def _oval_vs_ink(gray, box, spacing, thickness, line_ys, poly_page, cx_oval, cy_oval):
    """IoU of the template oval with the head's ink blob, and the centre
    offset in spaces (`template_review_r7.oval_vs_ink`)."""
    x0, y0, x1, y1 = box
    m = int(round(CUT_SPACES * spacing))
    rx0, ry0, rx1, ry1 = int(x0) - m, int(y0) - m, int(x1) + m + 1, int(y1) + m + 1
    pad = int(round(1.5 * spacing))
    wx0, wy0 = rx0 - pad, ry0 - pad
    wx1, wy1 = rx1 + pad, ry1 + pad
    H, W = gray.shape
    wx0, wy0, wx1, wy1 = max(0, wx0), max(0, wy0), min(W, wx1), min(H, wy1)
    win = gray[wy0:wy1, wx0:wx1]
    ink = win <= ht._otsu_threshold(win)
    oval = np.zeros(ink.shape, np.uint8)
    cv2.fillPoly(oval, [np.array([[x - wx0, y - wy0] for x, y in poly_page], np.int32)], 1)
    oval = oval.astype(bool)
    half = int(round(thickness / 2.0)) + 1
    for ly in line_ys:
        r = int(round(ly - wy0))
        r0, r1 = max(0, r - half), min(ink.shape[0], r + half + 1)
        if r1 > r0:
            ink[r0:r1, :] &= oval[r0:r1, :]
    d = max(3, int(round(0.42 * spacing)) | 1)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))
    ink_open = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, k).astype(bool)
    cut = np.zeros(ink.shape, bool)
    cut[max(0, ry0 - wy0):max(0, ry1 - wy0), max(0, rx0 - wx0):max(0, rx1 - wx0)] = True

    def one(mask):
        cand = mask & cut
        num, lab = cv2.connectedComponents(cand.astype(np.uint8))
        keep = np.zeros_like(cand)
        for i in range(1, num):
            comp = lab == i
            if (comp & oval).any():
                keep |= comp
        if not keep.any():
            return 0.0, None
        iou = float((keep & oval).sum() / (keep | oval).sum())
        ys, xs = np.nonzero(keep)
        off = float(np.hypot(xs.mean() + wx0 - cx_oval, ys.mean() + wy0 - cy_oval) / spacing)
        return iou, off
    iou_o, off_o = one(ink_open)
    return dict(iou_open=round(iou_o, 2),
                offset_open_sp=None if off_o is None else round(off_o, 2))


# ---------------------------------------------------------------------------
# the position derivation (score_truth_set_rungs._reader_absolute_position_impl,
# round-7 cleanups dropped: they are disabled there, "measured net negative")
# ---------------------------------------------------------------------------
def read_absolute_position(gray, lines: Sequence[float], box: Sequence[float],
                           subject: str,
                           page_notehead_boxes: Sequence[Tuple[str, tuple]],
                           page_accidental_boxes: Sequence[Tuple[str, tuple]],
                           chord_split_rungs_y: Optional[Sequence[float]] = None,
                           detail_out: Optional[Dict[str, Any]] = None,
                           text_boxes: Optional[Sequence[tuple]] = None,
                           thickness_px: Optional[float] = None,
                           ) -> Tuple[Optional[int], str]:
    """(absolute position, reason) of a head outside its staff, read from the
    printed ledgers. `lines` are the staff lines AT the head's x. `detail_out`,
    when given, receives the note-first reader's line / count (`note_first`)."""
    with lg.exclusion_rules(connected=EXCLUSION_RULES["connected"],
                            own_box=None,
                            one_sided=EXCLUSION_RULES["one_sided"],
                            jut_from_ink=EXCLUSION_RULES["jut_from_ink"]):
        return _read(gray, lines, box, subject, page_notehead_boxes,
                     page_accidental_boxes, chord_split_rungs_y, detail_out,
                     text_boxes, thickness_px)


def _read(gray, global_lines, box, subject, page_notehead_boxes,
          page_accidental_boxes, chord_split_rungs_y=None,
          detail_out=None, text_boxes=None,
          thickness_px=None) -> Tuple[Optional[int], str]:
    ys = sorted(float(v) for v in global_lines)
    if len(ys) < 2:
        return None, "no_staff_lines"
    spacing = (ys[-1] - ys[0]) / 4.0
    if spacing <= 0:
        return None, "bad_spacing"
    top, bottom = ys[0], ys[-1]
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    if cy < top:
        side, edge, sign, edge_pos, near_y = "above", top, -1.0, 0, y1
    else:
        side, edge, sign, edge_pos, near_y = "below", bottom, 1.0, 8, y0
    others = lg.exclusion_boxes_for(
        subject, box, page_notehead_boxes, page_accidental_boxes,
        drop_same_ink_other_staff=READER_KEYWORDS["drop_same_ink_other_staff"])
    items = lg.measure_ledger_rungs(
        gray, ys, cx, head_y=cy, exclude_boxes=others, head_box_x=(x0, x1),
        collapse_edges_box=(x0, y0, x1, y1), head_center_y=None,
        restore_masked_staff_side_rungs=READER_KEYWORDS["restore_masked_near_edge"],
        keep_edge_juts=READER_KEYWORDS.get("edge_jut_kept", False),
        split_welded_bands=READER_KEYWORDS.get("split_welded_bands", False),
        walk_tol_px=(WALK_CENTRE_TOL_PX if READER_KEYWORDS.get("walk_tol") else 0.0),
        outline_margin_px=(0.5 * float(thickness_px)
                           if READER_KEYWORDS.get("rows_clear_of_box") and thickness_px else 0.0),
    ).get(side, [])

    # Round 6 (Sean, flute chords): two heads of one chord, outside the staff,
    # a THIRD apart, neither with a line through it, necessarily have a ledger
    # between them.
    stack_reason = None
    if chord_split_rungs_y is not None:
        # the split blob's own ledgers (every printed jut, and the one between
        # the two heads) replace the stacked-thirds partner search
        for _ry in chord_split_rungs_y:
            if (_ry < top) == (sign < 0):
                items = lg.insert_rung(items, sign, _ry)
        stack_reason = "chord_split_rung"
    elif not lg.has_through_head_rung(items, (x0, y0, x1, y1)):
        for psub, pbox in page_notehead_boxes:
            if psub == subject:
                continue
            px0, py0, px1, py1 = pbox
            pcy = (py0 + py1) / 2.0
            if top <= pcy <= bottom:
                continue
            pside = "above" if pcy < top else "below"
            if pside != side:
                continue
            if not lg.heads_are_a_third_apart((x0, y0, x1, y1), pbox, spacing):
                continue
            p_others = [b for (s, b) in page_notehead_boxes if s != psub]
            p_items = lg.measure_ledger_rungs(
                gray, ys, (px0 + px1) / 2.0, head_y=pcy,
                exclude_boxes=p_others, head_box_x=(px0, px1),
            ).get(side, [])
            if lg.has_through_head_rung(p_items, pbox):
                continue
            if sign * (cy - edge) >= sign * (pcy - edge):
                box_outer, box_inner = (x0, y0, x1, y1), pbox
            else:
                box_outer, box_inner = pbox, (x0, y0, x1, y1)
            lateral = [b for (s, b) in page_notehead_boxes if s not in (subject, psub)]
            res = lg.third_stack_rung(gray, box_outer, box_inner, spacing,
                                      exclude_boxes=lateral)
            items = lg.insert_rung(items, sign, res["y"])
            stack_reason = ("ink_confirmed_by_third" if res["confirmed"]
                            else "implied_by_third")
            break

    if READER_KEYWORDS.get("note_first"):
        nf = lg.derive_note_first_step(
            gray, (x0, y0, x1, y1), edge, sign, spacing, items,
            exclude_boxes=others,
            far_side_partner_boxes=[b for (s_, b) in page_notehead_boxes
                                    if s_ != subject],
            ledger_not_text=READER_KEYWORDS.get("ledger_not_text", False),
            text_boxes=text_boxes,
            edge_vs_through=READER_KEYWORDS.get("edge_vs_through", False))
        if detail_out is not None:
            detail_out["note_first"] = nf
            detail_out["edge_y"] = edge
        if nf["offset"] is None:
            return None, nf["reason"]
        tag = f" ({stack_reason})" if stack_reason is not None else ""
        return edge_pos + int(sign * nf["offset"]), nf["reason"] + tag

    step = lg.derive_far_head_step(
        items, edge, sign, near_y, spacing,
        img_gray=gray, head_box=(x0, y0, x1, y1), exclude_boxes=others,
        head_center_y=None,
        near_edge_ledgers=READER_KEYWORDS["near_edge_ledgers"],
        far_side_ledger=READER_KEYWORDS["far_side_ledger"],
        far_side_partner_boxes=[b for (s_, b) in page_notehead_boxes if s_ != subject],
        drop_rungs_beyond_head=READER_KEYWORDS["drop_beyond_head"],
        through_head_on_rung=READER_KEYWORDS["through_head_on_rung"],
    )
    if step["offset"] is None:
        return None, step["reason"]
    if stack_reason is not None:
        return (edge_pos + int(sign * step["offset"]),
                f"{step['reason']} ({stack_reason})")
    return edge_pos + int(sign * step["offset"]), step["reason"]
