"""Template-matching symbol detector.

Given a MeasureCell (Phase 1 output) and a SymbolLibrary, locate symbols by
two complementary passes:

  1. Notehead search — slide each notehead template across the no-staff
     image, find peak NCC responses, non-max-suppress, and emit a
     SymbolDetection per surviving peak. This handles beam groups (multiple
     noteheads in one connected component) which a "classify-whole-CC"
     approach cannot.

  2. Per-CC classification — for each remaining connected component (rests,
     accidentals, clefs, time-sig digits, isolated barlines), compute Hu
     moments → screen library by Hu distance → run multi-scale NCC against
     top-k candidates → emit best match if above threshold.

Public:
    detect_symbols(cell, library, ...) -> list[SymbolDetection]
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import cv2
import numpy as np


# Phase 2.6 + 2.7 staged-rollout switch. Set OMR_PHASE26_FIXES to one of:
#   "0" / "off"            — Phase 2.5 baseline behavior (all fixes off)
#   "1" / "barlines"       — Fix 1 only: drop barline + stem categories
#   "2" / "clef"           — Fixes 1 + 2: also mask leading clef in m0
#   "3" / "accidentals"    — Fixes 1 + 2 + 3: also raise accidental threshold
#   "4" / "rest_gate" /    — Fixes 1 + 2 + 3 + 4: also gate rest detections
#       "all" / unset        to a y-band around the staff (Phase 2.7).
# Defaults to "all" so production code paths get the full fix stack.
def _phase26_level() -> int:
    raw = (os.environ.get("OMR_PHASE26_FIXES") or "all").strip().lower()
    if raw in {"0", "off", "none", "baseline"}:
        return 0
    if raw in {"1", "barlines"}:
        return 1
    if raw in {"2", "clef"}:
        return 2
    if raw in {"3", "accidentals"}:
        return 3
    if raw in {"4", "rest_gate", "rests", "all"}:
        return 4
    return 4


# Phase 2.8: independent toggle for the staff-vicinity text gate. When on,
# notehead and flag detections whose bbox center is too far from any staff
# line are dropped — this kills detections that match against tempo letters,
# dynamics markings ("f", "d", "V"), and bracket / number glyphs sitting
# well above or below the staff. The gate is geometric only, so it does
# NOT introduce any OCR or new template work.
def _phase28_text_gate_enabled() -> bool:
    raw = (os.environ.get("OMR_PHASE28_FIX_TEXT_GATE") or "on").strip().lower()
    return raw not in {"0", "off", "none", "baseline", "false", "no"}


def _in_staff_vicinity(y_center: int,
                       staff_line_ys: list[int],
                       max_line_spacings_away: float = 3.0) -> bool:
    """Return True if `y_center` lies within `max_line_spacings_away` line
    spacings of the staff (above the top line or below the bottom line).

    The center-only check is intentional. Bbox-edge checks were considered
    and rejected: flags on high ledger-line noteheads have bboxes that
    extend well above the staff (the flag head itself), but the flag head's
    CENTER still sits comfortably within ~2.5 line spacings of the staff
    top. Text glyphs ("V" in vivace, "f" in forte) have their bbox centers
    several spacings away from the staff because they are drawn in the
    open space between staff and tempo marking row.
    """
    if not staff_line_ys:
        # No staff info → fall back to no filtering (preserve recall over
        # precision in the degenerate case).
        return True
    ys = sorted(staff_line_ys)
    gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
    if not gaps:
        return True
    spacing = sum(gaps) / len(gaps)
    top = ys[0] - max_line_spacings_away * spacing
    bottom = ys[-1] + max_line_spacings_away * spacing
    return top <= y_center <= bottom

from .types import MeasureCell
from .symbol_library.loader import SymbolLibrary, LibraryEntry, Match
from .symbol_library.builder import hu_moments


@dataclass
class SymbolDetection:
    cell: MeasureCell
    smufl_name: str
    category: str
    x_canonical: int
    y_canonical: int
    width_canonical: int
    height_canonical: int
    confidence: float
    pitch: str | None = None

    @property
    def y_center(self) -> int:
        return self.y_canonical + self.height_canonical // 2

    @property
    def x_center(self) -> int:
        return self.x_canonical + self.width_canonical // 2


# --------------------------------------------------------------------------
# Component extraction
# --------------------------------------------------------------------------


def _binarize_for_components(image: np.ndarray, threshold: int = 180) -> np.ndarray:
    """Phase 1 convention: 255=paper, 0=ink. Return a uint8 mask where
    255=ink (foreground) for connectedComponentsWithStats."""
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    return mask


def _estimate_line_spacing(cell: MeasureCell) -> float:
    if len(cell.staff_line_ys_canonical) >= 2:
        ys = sorted(cell.staff_line_ys_canonical)
        gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
        return float(sum(gaps) / len(gaps))
    return 24.0  # canonical default


def _extract_components(
    cell: MeasureCell,
    min_area_factor: float = 0.25,
    max_area_factor: float = 60.0,
) -> list[tuple[int, int, int, int, int]]:
    """Return list of (x, y, w, h, area) for each non-degenerate component.

    Area thresholds are expressed as multiples of (line_spacing²) so they
    scale with the staff size in canonical coords.
    """
    img = cell.image_no_staff if cell.image_no_staff is not None else cell.image
    mask = _binarize_for_components(img)
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)

    spacing = _estimate_line_spacing(cell)
    min_area = max(8, int(min_area_factor * spacing * spacing))
    max_area = int(max_area_factor * spacing * spacing)

    out: list[tuple[int, int, int, int, int]] = []
    for i in range(1, n):  # skip background label 0
        x, y, w, h, area = (int(stats[i, cv2.CC_STAT_LEFT]),
                            int(stats[i, cv2.CC_STAT_TOP]),
                            int(stats[i, cv2.CC_STAT_WIDTH]),
                            int(stats[i, cv2.CC_STAT_HEIGHT]),
                            int(stats[i, cv2.CC_STAT_AREA]))
        if area < min_area or area > max_area:
            continue
        if w < 3 or h < 3:
            continue
        out.append((x, y, w, h, area))
    return out


# --------------------------------------------------------------------------
# Detection driver
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Pass 1: Notehead search (handles beam groups)
# --------------------------------------------------------------------------


def _find_noteheads(
    cell: MeasureCell,
    library: SymbolLibrary,
    confidence_threshold: float = 0.55,
    scales: tuple[float, ...] = (0.85, 1.0, 1.15),
    clef_mask_px: int = 0,
) -> list[SymbolDetection]:
    """Slide each notehead template across the cell, find NCC peaks above
    threshold, non-max-suppress, emit detections.

    If `clef_mask_px` > 0, peaks whose x-center falls inside the first
    `clef_mask_px` pixels are dropped (Phase 2.6 Fix 2: suppress noteheads
    inside the leading clef glyph of m0).
    """
    img = cell.image_no_staff if cell.image_no_staff is not None else cell.image
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Ink-positive for cv2.matchTemplate (paper→0, ink→255)
    comp = (255 - img).astype(np.uint8)
    ch, cw = comp.shape
    spacing = _estimate_line_spacing(cell)

    # Pick notehead templates whose canonical size is closest to the
    # observed staff spacing. SMuFL noteheads at 96px have body ~24-26 px
    # tall, vs. our staff spacing of ~52 px, so we scale templates ~2×.
    notehead_entries = [e for e in library.entries if e.category == "notehead"]
    if not notehead_entries:
        return []

    # Adapt template scale to staff spacing.
    # A notehead body should be ~ line_spacing tall. Find the per-entry scale
    # that lands its height closest to `spacing`.
    adaptive_scales = []
    for e in notehead_entries:
        tpl_h = e.shape[0]
        base_s = spacing / max(1, tpl_h)
        # Sample around the adaptive base scale
        adaptive_scales.append((e, [base_s * s for s in scales]))

    # Bounding y-range for noteheads: ±3 line spacings beyond the staff.
    # (Ledger-line notes can extend up to ~6 line positions out, so 3
    # spacings = 6 half-steps gives reasonable margin without flooding
    # the search with beam-region false positives.)
    if cell.staff_line_ys_canonical:
        ys_sorted = sorted(cell.staff_line_ys_canonical)
        y_lo = max(0, ys_sorted[0] - int(3 * spacing))
        y_hi = min(ch, ys_sorted[-1] + int(3 * spacing))
    else:
        y_lo, y_hi = 0, ch

    raw_hits: list[tuple[int, int, int, int, float, str]] = []  # (x,y,w,h,score,name)

    for entry, scale_set in adaptive_scales:
        tpl_raw = entry.load_image(library.data_dir)
        tpl = (255 - tpl_raw).astype(np.uint8)
        for s in scale_set:
            new_h = max(4, int(round(tpl.shape[0] * s)))
            new_w = max(4, int(round(tpl.shape[1] * s)))
            if new_h >= ch or new_w >= cw:
                continue
            tpl_s = cv2.resize(tpl, (new_w, new_h), interpolation=cv2.INTER_AREA)
            try:
                res = cv2.matchTemplate(comp, tpl_s, cv2.TM_CCOEFF_NORMED)
            except cv2.error:
                continue
            # Find all peaks above threshold
            ys, xs = np.where(res >= confidence_threshold)
            for yy, xx in zip(ys, xs):
                # Reject matches whose CENTER is outside the staff-vicinity
                # window — beam false-positives sit well below the staff.
                cy = int(yy) + new_h // 2
                if cy < y_lo or cy > y_hi:
                    continue
                cx = int(xx) + new_w // 2
                if clef_mask_px > 0 and cx < clef_mask_px:
                    continue
                raw_hits.append((int(xx), int(yy), new_w, new_h,
                                 float(res[yy, xx]), entry.smufl_name))

    # Non-max suppression: greedy keep-highest, suppress overlaps with
    # IoU > 0.3 or center-distance < 0.6 × line spacing.
    raw_hits.sort(key=lambda r: r[4], reverse=True)

    def _overlaps(a, b) -> bool:
        ax, ay, aw, ah = a[:4]
        bx, by, bw, bh = b[:4]
        # Center distance
        acx, acy = ax + aw / 2.0, ay + ah / 2.0
        bcx, bcy = bx + bw / 2.0, by + bh / 2.0
        dx, dy = acx - bcx, acy - bcy
        if (dx * dx + dy * dy) ** 0.5 < 0.6 * spacing:
            return True
        # IoU
        ix0, iy0 = max(ax, bx), max(ay, by)
        ix1, iy1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
        iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
        inter = iw * ih
        ua = aw * ah + bw * bh - inter
        if ua <= 0:
            return False
        return inter / ua > 0.3

    kept: list[tuple[int, int, int, int, float, str]] = []
    for h in raw_hits:
        if any(_overlaps(h, k) for k in kept):
            continue
        kept.append(h)

    detections: list[SymbolDetection] = []
    for (x, y, w, h, score, name) in kept:
        detections.append(SymbolDetection(
            cell=cell,
            smufl_name=name,
            category="notehead",
            x_canonical=x,
            y_canonical=y,
            width_canonical=w,
            height_canonical=h,
            confidence=score,
        ))
    return detections


# --------------------------------------------------------------------------
# Pass 2: Per-CC classification for non-notehead symbols
# --------------------------------------------------------------------------


def _classify_components(
    cell: MeasureCell,
    library: SymbolLibrary,
    skip_regions: list[tuple[int, int, int, int]],
    confidence_threshold: float = 0.55,
    top_k: int = 10,
    scales: tuple[float, ...] = (0.85, 1.0, 1.15),
    suppress_barlines: bool = True,
    suppress_stems: bool = True,
    clef_mask_first_measure_px: int | None = None,
    cell_is_first_measure: bool = False,
    accidental_threshold: float | None = None,
) -> list[SymbolDetection]:
    """Classify each non-notehead-overlapping CC against the rest of the
    library (excluding noteheads, which pass 1 already handled).

    Phase 2.6 filters:
      - `suppress_barlines`: skip every barline-category template. Barlines
        come from the Phase-1 morphological pipeline, not from within a cell.
        A quarter-note stem looks identical to barlineSingle inside a cell.
      - `suppress_stems`: skip the procedural-stem template. Stems are not
        useful as standalone detections; they're either part of a notehead
        or a barline (handled by Phase 1).
      - `clef_mask_first_measure_px` + `cell_is_first_measure`: skip CCs
        whose x_center sits inside the first `N` px of the cell when this
        is measure-index 0 (the staff's leading clef glyph).
      - `accidental_threshold`: when set, accidental-category candidates
        must clear this stricter NCC threshold to be emitted. Helps reduce
        sharps misclassified as restQuarter / timeSig1.
    """
    img = cell.image_no_staff if cell.image_no_staff is not None else cell.image
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    comps = _extract_components(cell)

    suppressed_cats: set[str] = set()
    if suppress_barlines:
        suppressed_cats.add("barline")
    if suppress_stems:
        suppressed_cats.add("stem")

    non_notehead = [e for e in library.entries
                    if e.category != "notehead"
                    and e.category not in suppressed_cats]

    spacing = _estimate_line_spacing(cell)

    detections: list[SymbolDetection] = []
    for (x, y, w, h, _area) in comps:
        # If CC is a beam-group sized blob (much bigger than a single
        # symbol), skip classification — that's pass 1's territory.
        if w > 3 * spacing and h > 2 * spacing:
            continue

        # Phase 2.6 Fix 2: clef mask. Only the FIRST measure of a staff has
        # a leading clef. Any CC whose x-center sits in the first
        # `clef_mask_first_measure_px` of the cell is suppressed in m0.
        # (Mid-piece clef changes in non-zero measures are out of scope.)
        if (cell_is_first_measure
                and clef_mask_first_measure_px is not None
                and (x + w / 2.0) < clef_mask_first_measure_px):
            continue

        # Skip CCs whose bbox overlaps any notehead bbox by > 50% — that's
        # likely a notehead and pass 1 already handled it.
        skip = False
        for (sx, sy, sw, sh) in skip_regions:
            ix0, iy0 = max(x, sx), max(y, sy)
            ix1, iy1 = min(x + w, sx + sw), min(y + h, sy + sh)
            iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
            inter = iw * ih
            cc_area = w * h
            if cc_area > 0 and inter / cc_area > 0.5:
                skip = True
                break
        if skip:
            continue

        crop = img[y:y + h, x:x + w]
        try:
            hu = hu_moments(crop)
        except cv2.error:
            continue
        # Screen against non-noteheads, with Phase 2.6 category suppression
        # (barlines, stems) baked into the Hu-distance mask so they never
        # appear among the top-k candidates.
        diffs = library._hu_matrix - hu[None, :]
        dists = np.sqrt(np.sum(diffs * diffs, axis=1))
        for i, e in enumerate(library.entries):
            if e.category == "notehead" or e.category in suppressed_cats:
                dists[i] = np.inf
        order = np.argsort(dists)[:top_k]
        candidates = [library.entries[i] for i in order]
        if not candidates:
            continue

        pad = 4
        padded = cv2.copyMakeBorder(crop, pad, pad, pad, pad,
                                    cv2.BORDER_CONSTANT, value=255)
        matches = library.match(padded, candidates=candidates, scales=scales)
        if not matches:
            continue
        best = matches[0]
        # Phase 2.6 Fix 3: per-category thresholds for the most confused
        # non-notehead symbols. The Phase 2.5 baseline confused sharps with
        # restQuarter (conf~0.56) and timeSig1 (conf~0.83) — the rest/digit
        # templates fire on the sharp's vertical-bar-with-cross-strokes.
        # Two interventions:
        #   1. Raise the floor for `rest` and `time_sig_digit` so the
        #      0.56-conf rest can't slip through.
        #   2. Also raise the floor for `accidental` so when a sharp IS
        #      correctly matched, only a strong match wins (defensive).
        # If best is rest/digit/accidental, see if a same-CC accidental
        # candidate scored within `accidental_swap_margin` of the winner —
        # if so, prefer the accidental.
        cat_threshold = {
            "rest": 0.70,
            "time_sig_digit": 0.85,
            "accidental": accidental_threshold if accidental_threshold is not None
                else confidence_threshold,
        }
        floor = cat_threshold.get(best.category, confidence_threshold)
        if best.score < floor:
            # Look for a same-CC accidental candidate that's a strong
            # alternative — promotes sharps that lost the NCC race to a
            # rest/digit template by a small margin.
            promoted = None
            for m in matches[1:5]:
                if m.category == "accidental" and m.score >= (
                        accidental_threshold or confidence_threshold):
                    promoted = m
                    break
            if promoted is None:
                continue
            best = promoted
        if best.score < confidence_threshold:
            continue
        detections.append(SymbolDetection(
            cell=cell,
            smufl_name=best.smufl_name,
            category=best.category,
            x_canonical=x,
            y_canonical=y,
            width_canonical=w,
            height_canonical=h,
            confidence=best.score,
        ))
    return detections


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------


def detect_symbols(
    cell: MeasureCell,
    library: SymbolLibrary,
    confidence_threshold: float = 0.55,
    notehead_threshold: float = 0.6,
    top_k: int = 10,
    scales: tuple[float, ...] = (0.85, 1.0, 1.15),
    suppress_barlines: bool = True,
    suppress_stems: bool = True,
    clef_mask_line_spacings: float = 2.5,
    accidental_threshold: float = 0.70,
    rest_y_band_line_spacings: float = 0.0,
    notehead_vicinity_line_spacings: float = 2.0,
    flag_vicinity_line_spacings: float = 2.5,
    flag_min_height_line_spacings: float = 2.8,
) -> list[SymbolDetection]:
    """Detect symbols in `cell` by sliding-window notehead search + per-CC
    classification of remaining components. Returns detections ordered by
    x_center. Robust against empty / sliver cells.

    Phase 2.6 keyword args (defaults reflect the chosen fixes):
      * `suppress_barlines` — drop the barline category entirely. Barlines
        are detected by Phase 1's morphological per-system pipeline, and
        from inside a measure cell the barline template is indistinguishable
        from a quarter-note stem.
      * `suppress_stems` — drop the procedural-stem template for the same
        reason: stems-as-symbols are not useful here.
      * `clef_mask_line_spacings` — width (in line-spacings) of the
        leading-clef suppression zone on measure-index-0 cells. The G/F clef
        glyph generates spurious notehead/flag matches against its curves;
        masking the first ~2-2.5 line-spacings of the cell removes them.
      * `accidental_threshold` — minimum NCC score required to emit an
        accidental-category detection. Sharps tend to be misclassified as
        restQuarter or timeSig1 at the default 0.55 floor; raising the bar
        for the accidental category specifically cuts these false IDs.
      * `rest_y_band_line_spacings` — half-width (in line-spacings) of the
        y-band around the staff inside which rest-category detections are
        kept. A rest's bounding-box CENTER must lie within
        `[top_staff_line - K*spacing, bottom_staff_line + K*spacing]`.
        Rests in real music are drawn on the staff (whole/half rest on the
        4th line, quarter rest centered between top and bottom); they never
        appear above the top line or below the bottom line. Phase 2.7.
      * `notehead_vicinity_line_spacings` — max line-spacings away from the
        staff a notehead bbox CENTER may be. Phase 2.8 text gate. The
        existing _find_noteheads search-window margin is 3sp; this gate
        tightens that to 2sp at the post-detection stage, killing 3
        dynamicForte FPs on Beethoven (at 2.05, 2.57, 2.58sp from staff).
        Costs 2 ledger-line TPs (at 2.58 and 2.61sp); net +1 precision.
        Both lost TPs are in cells that already have 0 FPs, so per-cell
        precision is unchanged — only the absolute TP count drops by 2.
      * `flag_vicinity_line_spacings` — same idea, for flag-category
        detections. Default 2.5sp catches text glyphs sitting >2.5sp from
        the staff (e.g. "d" in "dim." that lives below the staff).
      * `flag_min_height_line_spacings` — minimum bbox HEIGHT (in line
        spacings) for a flag detection to be kept. Real flags appear on a
        stem, and the connected component the flag template matches against
        is typically the flag + stem + (sometimes) notehead — its bbox is
        always >=3 line spacings tall. Text glyphs ("V" in "vivace", a 2/2
        digit, a tempo bracket) match with much shorter bboxes. In the
        Phase 2.7 corpus all 5 TP flags have h/sp >= 3.16 and all 6 FP
        flags have h/sp <= 2.55, making this an unusually clean cutoff.
        Default 2.8 leaves margin on both sides.
    """
    if cell.image is None or min(cell.image.shape[:2]) < 20:
        return []

    img = cell.image_no_staff if cell.image_no_staff is not None else cell.image
    # Skip cells with too little ink (Phase 1 over-detection produces empty
    # slivers; don't crash on those).
    mask = _binarize_for_components(img)
    ink_count = int(np.count_nonzero(mask))
    if ink_count < 50:
        return []

    # Phase 2.6 staged rollout: turn fixes on/off by env var (or via kwargs
    # for explicit callers). The env var is read only at runtime so the
    # benchmark script can flip between levels without rebuilding.
    level = _phase26_level()
    if level < 1:
        suppress_barlines = False
        suppress_stems = False
    if level < 2:
        clef_mask_line_spacings = 0.0
    if level < 3:
        accidental_threshold = 0.55  # baseline confidence_threshold
    # Phase 2.7 rest y-band gate: on iff level >= 4. We track this with a
    # separate flag so the gate's margin (which can legitimately be 0.0)
    # is independent of whether the gate is enabled.
    rest_y_band_enabled = (level >= 4)
    # Phase 2.8 text gate: independent env switch (default on). When off
    # the notehead / flag vicinity filters are skipped — this lets us A/B
    # the new gate against the Phase 2.7 baseline without code changes.
    text_gate_enabled = _phase28_text_gate_enabled()

    spacing = _estimate_line_spacing(cell)
    clef_mask_px = int(round(clef_mask_line_spacings * spacing))
    cell_is_first_measure = (cell.measure_index == 0)

    noteheads = _find_noteheads(
        cell, library,
        confidence_threshold=notehead_threshold,
        scales=scales,
        clef_mask_px=clef_mask_px if cell_is_first_measure else 0,
    )
    notehead_regions = [(d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical)
                        for d in noteheads]
    others = _classify_components(
        cell, library, skip_regions=notehead_regions,
        confidence_threshold=confidence_threshold,
        top_k=top_k, scales=scales,
        suppress_barlines=suppress_barlines,
        suppress_stems=suppress_stems,
        clef_mask_first_measure_px=clef_mask_px,
        cell_is_first_measure=cell_is_first_measure,
        accidental_threshold=accidental_threshold,
    )
    detections = noteheads + others

    # Phase 2.7: Rest y-band gate. Rests live ON the staff:
    #   - whole rest hangs from the 2nd-from-top line (center ~= top + 0.5sp)
    #   - half rest sits on the 2nd-from-top line   (center ~= top + 1.0sp)
    #   - quarter and shorter rests are centered vertically on the staff
    #     (center ~= midpoint of top and bottom lines)
    # 8th/16th rest bodies are tall and their TOP corners extend ~1sp
    # above the top staff line, but their CENTER still sits on the staff
    # (around the middle line). So we gate on the bbox CENTER, not the
    # top/bottom, and require the center to lie within the staff lines
    # plus a small K-line-spacing tolerance. With K=0 (the default), only
    # rests whose center is inside the [top_line, bottom_line] band
    # survive — which is the structurally correct rule for traditional
    # five-line staff notation.
    if rest_y_band_enabled and cell.staff_line_ys_canonical:
        ys_sorted = sorted(cell.staff_line_ys_canonical)
        margin = rest_y_band_line_spacings * spacing
        y_lo = ys_sorted[0] - margin
        y_hi = ys_sorted[-1] + margin
        kept: list[SymbolDetection] = []
        for d in detections:
            if d.category == "rest":
                cy = d.y_center
                if cy < y_lo or cy > y_hi:
                    continue
            kept.append(d)
        detections = kept

    # Phase 2.8: notehead + flag text gate. Two complementary filters
    # target the same problem: tempo/dynamics letters and digits being
    # matched as music symbols.
    #   1. Staff-vicinity check (bbox CENTER must be near the staff). Real
    #      noteheads + flags live on or near the staff; text glyphs in the
    #      dynamics / tempo region sit further away.
    #   2. Flag bbox-height check (CC height must span ~3 line spacings).
    #      Flags appear on stems, and the CC the flag template hits is the
    #      flag + stem (+ sometimes notehead). Text glyphs match with much
    #      shorter CCs. Verified clean on the Phase 2.7 corpus: all TP
    #      flags have h/sp >= 3.16, all FP flags have h/sp <= 2.55.
    if text_gate_enabled and cell.staff_line_ys_canonical:
        kept: list[SymbolDetection] = []
        for d in detections:
            if d.category == "notehead":
                if not _in_staff_vicinity(
                    d.y_center, cell.staff_line_ys_canonical,
                    notehead_vicinity_line_spacings,
                ):
                    continue
            elif d.category == "flag":
                if not _in_staff_vicinity(
                    d.y_center, cell.staff_line_ys_canonical,
                    flag_vicinity_line_spacings,
                ):
                    continue
                # Flag-specific: enforce a minimum CC height. A real flag
                # template always matches against a tall CC (flag + stem).
                if (d.height_canonical / max(1.0, spacing)
                        < flag_min_height_line_spacings):
                    continue
            kept.append(d)
        detections = kept

    detections.sort(key=lambda d: d.x_center)
    return detections
