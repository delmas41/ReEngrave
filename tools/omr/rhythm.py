"""Rhythm resolution — turn raw detections into note/rest durations.

Phase 4c. Takes a cell's detections and produces:

  * a duration for each notehead (whole / half / quarter / 8th / 16th / ...)
  * a duration for each rest (intrinsic from class name)
  * augmentation dot count for each notehead / rest
  * an optional time signature parsed from the cell's left-hand digits

The hard case is **black noteheads** (`noteheadBlack*`), where the intrinsic
class only tells us "quarter or shorter" — the actual duration comes from
whether the note is beamed, flagged, or bare.

The DSv2 Phase 3.3 detector **does not emit `stem` detections** reliably
(zero stems across our smoke-test pages even at conf=0.05). So this module
infers durations directly from `beam` + `flag` + `augmentationDot`
detections rather than going through stems:

  - Beam-attached notehead: count distinct vertical levels of beams that
    horizontally overlap the notehead's x-range → 1 beam = 8th,
    2 = 16th, 3 = 32nd, 4 = 64th. (3+ is rare in keyboard music.)
  - Flag-attached notehead (unbeamed 8th+): pair the notehead to the
    nearest flag detection. The flag's class name encodes the duration
    (`flag8thUp` → 8th, `flag16thDown` → 16th, ...).
  - Otherwise: black notehead = quarter, half notehead = half, whole
    notehead = whole.

Augmentation dots (`augmentationDot` from the DSv2 "structural" category)
are paired to the nearest notehead/rest to their left at roughly the same
y-position, multiplying that note's duration by 1.5 (1 dot) or 1.75 (2 dots).
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Intrinsic duration tables
# ---------------------------------------------------------------------------
#
# duration_beats is expressed in quarter notes: quarter = 1.0.
# This keeps the math simple downstream (a 4/4 measure = 4 beats).

# Intrinsic durations from notehead class alone (BEFORE beams/flags/dots).
# Black noteheads default to "quarter" but get refined to 8th/16th/etc. when
# a beam/flag is attached.
_NOTEHEAD_INTRINSIC: dict[str, tuple[float, str]] = {
    "noteheadwhole": (4.0, "whole"),
    "noteheadhalf": (2.0, "half"),
    "noteheadblack": (1.0, "quarter"),
    "noteheaddoublewhole": (8.0, "double_whole"),
}

# Rests are unambiguous — class name encodes the duration directly.
_REST_DURATIONS: dict[str, tuple[float, str]] = {
    "restdoublewhole": (8.0, "double_whole"),
    "restwhole": (4.0, "whole"),
    "resthalf": (2.0, "half"),
    "restquarter": (1.0, "quarter"),
    "rest8th": (0.5, "eighth"),
    "rest16th": (0.25, "sixteenth"),
    "rest32nd": (0.125, "thirty_second"),
    "rest64th": (0.0625, "sixty_fourth"),
    "rest128th": (0.03125, "hundred_twenty_eighth"),
    # restHBar / restHNr are multi-measure rest indicators — caller can
    # fall back to None and skip.
}

# Flag class → (duration_beats, duration_type).
_FLAG_DURATIONS: dict[str, tuple[float, str]] = {
    "flag8thup": (0.5, "eighth"),
    "flag8thdown": (0.5, "eighth"),
    "flag16thup": (0.25, "sixteenth"),
    "flag16thdown": (0.25, "sixteenth"),
    "flag32ndup": (0.125, "thirty_second"),
    "flag32nddown": (0.125, "thirty_second"),
    "flag64thup": (0.0625, "sixty_fourth"),
    "flag64thdown": (0.0625, "sixty_fourth"),
    "flag128thup": (0.03125, "hundred_twenty_eighth"),
    "flag128thdown": (0.03125, "hundred_twenty_eighth"),
}

# Beam-count → (duration_beats, duration_type).  beams_count=1 means the
# notehead is connected to ONE level of beams → 8th. 2 levels → 16th, etc.
_BEAM_COUNT_DURATIONS: dict[int, tuple[float, str]] = {
    1: (0.5, "eighth"),
    2: (0.25, "sixteenth"),
    3: (0.125, "thirty_second"),
    4: (0.0625, "sixty_fourth"),
    5: (0.03125, "hundred_twenty_eighth"),
}


def _normalize_class(name: str) -> str:
    """Lower-case + strip non-alnum so 'noteheadBlackOnLine' →
    'noteheadblackonline'. Most lookups below test prefixes against this.
    """
    if not name:
        return ""
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _intrinsic_notehead_duration(class_name: str) -> tuple[float, str] | None:
    """Look up a notehead's intrinsic duration from its class name.

    Returns None for classes we don't recognize (e.g. unknown small variants).
    """
    norm = _normalize_class(class_name)
    for prefix, dur in _NOTEHEAD_INTRINSIC.items():
        if norm.startswith(prefix):
            return dur
    return None


def _rest_duration(class_name: str) -> tuple[float, str] | None:
    """Look up a rest's duration from its class name."""
    norm = _normalize_class(class_name)
    for key, dur in _REST_DURATIONS.items():
        if norm.startswith(key):
            return dur
    return None


def _flag_duration(class_name: str) -> tuple[float, str] | None:
    """Look up a flag's duration from its class name."""
    norm = _normalize_class(class_name)
    return _FLAG_DURATIONS.get(norm)


# ---------------------------------------------------------------------------
# Time signature parsing
# ---------------------------------------------------------------------------
#
# DSv2 emits per-digit detections (`timeSig0` through `timeSig9`) plus
# `timeSigCommon` (= 4/4) and `timeSigCutCommon` (= 2/2). The numerator sits
# above the denominator at the start of the staff (after clef + key sig).


def parse_time_signature(detections: list[Any]) -> dict[str, Any] | None:
    """Parse a time signature from the time-signature-digit detections in
    a cell, if any. Returns `{numerator, denominator, raw}` or None if no
    time sig markers were seen.

    Algorithm:
      1. Common / cut-common shortcuts win first.
      2. Otherwise collect timeSig0-9 detections, sort by x then y.
         If we have an even number of digits stacked top-and-bottom at the
         same x, take the top half as numerator, bottom half as denominator.
      3. Single digit → assume denominator=4 (best guess).
    """
    digit_dets = []
    for d in detections:
        cat = getattr(d, "category", "")
        cls = _normalize_class(getattr(d, "smufl_name", ""))
        if cat != "time_sig_digit":
            continue
        if cls == "timesigcommon":
            return {"numerator": 4, "denominator": 4, "raw": "C"}
        if cls in ("timesigcuttime", "timesigcutcommon"):
            return {"numerator": 2, "denominator": 2, "raw": "C|"}
        # timesigN → digit
        if cls.startswith("timesig") and len(cls) > len("timesig"):
            tail = cls[len("timesig"):]
            if tail.isdigit():
                digit_dets.append((d, int(tail)))
    if not digit_dets:
        return None

    # Sort by x first, then split by y (top digits = numerator, bottom = denom).
    digit_dets.sort(key=lambda pair: pair[0].x_canonical)
    if len(digit_dets) == 1:
        # One visible digit — guess it's the numerator.
        n = digit_dets[0][1]
        return {"numerator": n, "denominator": 4, "raw": f"{n}/4"}

    # Cluster by x position. If all digits are at similar x, they're stacked
    # (single numerator+denominator). If x varies, we have multi-digit
    # numerators (e.g. 12/8).
    xs = [d.x_canonical for d, _ in digit_dets]
    x_span = max(xs) - min(xs)
    avg_digit_w = sum(d.width_canonical for d, _ in digit_dets) / len(digit_dets)
    if x_span < avg_digit_w * 0.6:
        # All stacked at same x — split top/bottom by y.
        sorted_by_y = sorted(digit_dets, key=lambda pair: pair[0].y_canonical)
        mid = len(sorted_by_y) // 2
        top = sorted_by_y[:mid] or [sorted_by_y[0]]
        bot = sorted_by_y[mid:]
        try:
            num = int("".join(str(v) for _, v in top))
            den = int("".join(str(v) for _, v in bot))
            return {"numerator": num, "denominator": den, "raw": f"{num}/{den}"}
        except ValueError:
            return None

    # Multi-digit numerator and denominator: cluster digits into top row and
    # bottom row by y, then concatenate within each row by x.
    y_median = sorted(d.y_canonical for d, _ in digit_dets)[len(digit_dets) // 2]
    top_row = sorted(
        ((d, v) for d, v in digit_dets if d.y_canonical < y_median),
        key=lambda pair: pair[0].x_canonical,
    )
    bot_row = sorted(
        ((d, v) for d, v in digit_dets if d.y_canonical >= y_median),
        key=lambda pair: pair[0].x_canonical,
    )
    if not top_row or not bot_row:
        return None
    try:
        num = int("".join(str(v) for _, v in top_row))
        den = int("".join(str(v) for _, v in bot_row))
        return {"numerator": num, "denominator": den, "raw": f"{num}/{den}"}
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Beam / flag / dot pairing
# ---------------------------------------------------------------------------


def _staff_line_spacing(cell) -> float:
    """Average gap between adjacent staff lines (canonical coords), with a
    sensible fallback when the cell has no staff line metadata.
    """
    lines = getattr(cell, "staff_line_ys_canonical", None) or []
    if len(lines) >= 2:
        ys = sorted(lines)
        gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
        return sum(gaps) / len(gaps)
    return 24.0  # canonical default


def _stem_for_notehead(nh, stems, max_x_distance: float):
    """Find the stem touching this notehead (classical-CV stems).

    A stem "touches" a notehead if its x-range is within
    `max_x_distance` of the notehead's x-range (either side — stem-up
    notes have the stem on the right, stem-down on the left) AND its
    y-range overlaps the notehead's y-range.

    Returns the stem (a `line_detection.LineDetection` or any
    quack-compatible object exposing `x_canonical` etc.) or None.
    """
    nh_x_l = nh.x_canonical
    nh_x_r = nh.x_canonical + nh.width_canonical
    nh_y_top = nh.y_canonical
    nh_y_bot = nh.y_canonical + nh.height_canonical
    best = None
    best_dist = float("inf")
    for s in stems:
        s_x_l = s.x_canonical
        s_x_r = s.x_canonical + s.width_canonical
        # Horizontal proximity (closest edge-to-edge gap)
        if s_x_r < nh_x_l:
            dx = nh_x_l - s_x_r
        elif s_x_l > nh_x_r:
            dx = s_x_l - nh_x_r
        else:
            dx = 0
        if dx > max_x_distance:
            continue
        # Vertical: stem must reach into the notehead's y-range
        s_y_top = s.y_canonical
        s_y_bot = s.y_canonical + s.height_canonical
        if s_y_bot < nh_y_top - 5 or s_y_top > nh_y_bot + 5:
            continue
        if dx < best_dist:
            best_dist = dx
            best = s
    return best


def _beams_attached_to_stem(stem, beams,
                            beam_y_cluster_tol: float) -> int:
    """Count distinct vertical beam levels attached to a stem.

    A beam attaches to a stem if its x-range overlaps the stem's x AND
    its y-position is anywhere within the stem's vertical extent (with a
    small tolerance). This naturally handles both stem-up (beams above
    the notehead) and stem-down (beams below).
    """
    s_x_l = stem.x_canonical
    s_x_r = stem.x_canonical + stem.width_canonical
    s_y_top = stem.y_canonical
    s_y_bot = stem.y_canonical + stem.height_canonical

    attached_ys: list[int] = []
    for b in beams:
        b_x_l = b.x_canonical
        b_x_r = b.x_canonical + b.width_canonical
        # x overlap: beam's range must reach the stem's range
        if b_x_r < s_x_l - 5 or b_x_l > s_x_r + 5:
            continue
        b_y_c = b.y_canonical + b.height_canonical // 2
        if b_y_c < s_y_top - 10 or b_y_c > s_y_bot + 10:
            continue
        attached_ys.append(b_y_c)
    if not attached_ys:
        return 0
    attached_ys.sort()
    levels = 1
    for i in range(1, len(attached_ys)):
        if attached_ys[i] - attached_ys[i - 1] > beam_y_cluster_tol:
            levels += 1
    return levels


def _beam_levels_for_notehead(nh, beams, max_stem_distance: float,
                              beam_y_cluster_tol: float,
                              x_tolerance: float) -> int:
    """Count distinct vertical beam levels attached to one notehead.

    A beam "attaches" to a notehead if its x-range (extended by
    `x_tolerance` on each side) covers the notehead's center AND its y is
    within `max_stem_distance` of the notehead's y. The x-tolerance is
    important because YOLO's bounding boxes for beams routinely end ~20–
    50px short of the actual beam stroke on either end, leaving edge
    noteheads stranded outside the bbox if we require strict containment.
    Beams within `beam_y_cluster_tol` of each other count as one level
    (allows for a wide single beam being detected as one box).
    """
    nh_x_center = nh.x_canonical + nh.width_canonical // 2
    nh_y_center = nh.y_canonical + nh.height_canonical // 2

    attached_ys: list[int] = []
    for b in beams:
        left = b.x_canonical - x_tolerance
        right = b.x_canonical + b.width_canonical + x_tolerance
        if not (left <= nh_x_center <= right):
            continue
        b_y_center = b.y_canonical + b.height_canonical // 2
        if abs(b_y_center - nh_y_center) > max_stem_distance:
            continue
        attached_ys.append(b_y_center)
    if not attached_ys:
        return 0
    # Cluster ys: every contiguous run separated by < tol is one level.
    attached_ys.sort()
    levels = 1
    for i in range(1, len(attached_ys)):
        if attached_ys[i] - attached_ys[i - 1] > beam_y_cluster_tol:
            levels += 1
    return levels


def _flag_for_notehead(nh, flags, max_x_distance: float):
    """Find the nearest flag detection to a notehead (vertically aligned,
    within reasonable x distance). Returns the flag detection or None.

    Flag classes encode stem direction (Up/Down); we don't enforce that
    here since the notehead's stem direction isn't reliably available
    from a 0-stem detector.
    """
    nh_x_center = nh.x_canonical + nh.width_canonical // 2
    best = None
    best_dist = float("inf")
    for f in flags:
        f_x_center = f.x_canonical + f.width_canonical // 2
        dx = abs(f_x_center - nh_x_center)
        if dx > max_x_distance:
            continue
        if dx < best_dist:
            best_dist = dx
            best = f
    return best


def _pair_dots_to_targets(dots, targets) -> dict[int, int]:
    """Each `augmentationDot` detection is matched to the nearest
    target (notehead or rest) to its LEFT at roughly the same y-position.
    Returns {id(target): dot_count}.
    """
    result: dict[int, int] = {}
    for dot in dots:
        dot_y = dot.y_canonical + dot.height_canonical // 2
        dot_x_left = dot.x_canonical
        best = None
        best_dist = float("inf")
        for tgt in targets:
            tgt_x_right = tgt.x_canonical + tgt.width_canonical
            if tgt_x_right > dot_x_left:
                # Target must be to the LEFT of the dot.
                continue
            tgt_y = tgt.y_canonical + tgt.height_canonical // 2
            if abs(tgt_y - dot_y) > max(dot.height_canonical, 12) * 1.2:
                continue
            dx = dot_x_left - tgt_x_right
            if dx > max(dot.width_canonical, 12) * 5:
                continue
            score = dx + abs(tgt_y - dot_y) * 2
            if score < best_dist:
                best_dist = score
                best = tgt
        if best is not None:
            result[id(best)] = result.get(id(best), 0) + 1
    return result


def _dot_multiplier(n_dots: int) -> float:
    """1 dot → 1.5×, 2 dots → 1.75×, etc."""
    mult = 1.0
    add = 0.5
    for _ in range(n_dots):
        mult += add
        add /= 2
    return mult


def _name_for_dots(n_dots: int) -> str:
    if n_dots == 0:
        return ""
    if n_dots == 1:
        return "dotted_"
    return f"{n_dots}dotted_"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def resolve_rhythms_for_cell(
    dets,
    cell,
    *,
    extra_lines: dict[str, list] | None = None,
) -> dict[int, dict[str, Any]]:
    """For each notehead and rest in `dets`, decide a duration.

    Returns `{id(detection): {"duration_beats", "duration_type", "dots"}}`.
    Caller merges this into the output dicts.

    For noteheads: precedence is (beams > flags > intrinsic class).
    For rests: just the intrinsic class duration.
    For both: augmentation dots multiply the duration.

    Args:
        dets: list of detection objects (YOLO SymbolDetection or dicts).
        cell: the MeasureCell — used for staff-line spacing reference.
        extra_lines: optional output from
            `tools.omr.line_detection.detect_lines(cell)` —
            `{"stems": [LineDetection...], "beams": [LineDetection...]}`.
            When provided, classical-CV beams REPLACE the YOLO beams
            (cleaner endpoints) and the stems are used as the primary
            anchor for beam-counting: notehead → stem → beams attached
            to that stem. Falls back to direct notehead → beam pairing
            when no stem is found.
    """
    line_spacing = _staff_line_spacing(cell)
    # A stem typically spans ~3.5 staff-spacings; allow a bit more for safety.
    max_stem_distance = line_spacing * 5.5
    # Beams within ~70% of a staff-line spacing of each other are the same
    # beam thickness; further apart = a new beam level.
    beam_y_cluster_tol = line_spacing * 0.7

    noteheads: list = []
    rests: list = []
    beams: list = []
    flags: list = []
    aug_dots: list = []
    for d in dets:
        cat = getattr(d, "category", "")
        cls = _normalize_class(getattr(d, "smufl_name", ""))
        if cat == "notehead":
            noteheads.append(d)
        elif cat == "rest":
            rests.append(d)
        elif cat == "flag":
            flags.append(d)
        elif cat == "structural" and cls == "beam":
            beams.append(d)
        elif cat == "structural" and cls == "augmentationdot":
            aug_dots.append(d)

    # Classical-CV stems are pure additive value — the YOLO detector
    # doesn't emit stems at all, so we have no prior anchor to lose.
    # Classical-CV beams, on the other hand, are MORE conservative than
    # YOLO's (precise endpoints, fewer false positives) but in practice
    # miss real beams that YOLO catches. So we UNION the two beam lists
    # rather than replacing: the loose YOLO bboxes set the broad
    # coverage, the CV bboxes add coverage where YOLO misses.
    stems: list = []
    if extra_lines is not None:
        cv_stems = extra_lines.get("stems") or []
        cv_beams = extra_lines.get("beams") or []
        if cv_stems:
            stems = list(cv_stems)
        if cv_beams:
            beams = beams + list(cv_beams)

    # Pair augmentation dots to whichever notehead / rest sits to their left
    # at the same y. (Dots after rests are rarer but real.)
    dot_targets = noteheads + rests
    dots_by_target_id = _pair_dots_to_targets(aug_dots, dot_targets)

    out: dict[int, dict[str, Any]] = {}

    # ── Noteheads ─────────────────────────────────────────────────────────
    for nh in noteheads:
        intrinsic = _intrinsic_notehead_duration(getattr(nh, "smufl_name", ""))
        if intrinsic is None:
            continue
        base_beats, base_type = intrinsic

        # Only black noteheads can shorten via beams / flags. Whole / half
        # noteheads can technically be beamed in modern notation but it's
        # vanishingly rare for engraved music; skip the refinement.
        if base_type == "quarter":
            n_beam_levels = 0
            # Prefer stem-anchored beam-counting when stems are available.
            # A stem is a precise vertical line that the beams visibly
            # attach to; pairing through the stem rather than directly
            # from the notehead is much more accurate.
            if stems:
                stem = _stem_for_notehead(
                    nh, stems,
                    max_x_distance=max(nh.width_canonical * 0.6,
                                       line_spacing * 0.4),
                )
                if stem is not None:
                    n_beam_levels = _beams_attached_to_stem(
                        stem, beams, beam_y_cluster_tol
                    )
            if n_beam_levels == 0:
                # No stem found (or no stems available) — fall back to
                # direct notehead → beam pairing.
                n_beam_levels = _beam_levels_for_notehead(
                    nh, beams, max_stem_distance, beam_y_cluster_tol,
                    x_tolerance=max(nh.width_canonical * 0.6,
                                    line_spacing * 0.6),
                )
            if n_beam_levels >= 1:
                refined = _BEAM_COUNT_DURATIONS.get(
                    n_beam_levels,
                    # Fall back to 64th-equivalent for >5 beams
                    (1.0 / (2 ** n_beam_levels), f"{n_beam_levels}beams"),
                )
                base_beats, base_type = refined
            else:
                # No beam — look for a flag.
                f = _flag_for_notehead(nh, flags, max_x_distance=max(
                    nh.width_canonical * 1.2, line_spacing * 1.5
                ))
                if f is not None:
                    fd = _flag_duration(getattr(f, "smufl_name", ""))
                    if fd is not None:
                        base_beats, base_type = fd

        n_dots = dots_by_target_id.get(id(nh), 0)
        final_beats = base_beats * _dot_multiplier(n_dots)
        final_type = f"{_name_for_dots(n_dots)}{base_type}"

        out[id(nh)] = {
            "duration_beats": round(final_beats, 4),
            "duration_type": final_type,
            "dots": n_dots,
        }

    # ── Rests ─────────────────────────────────────────────────────────────
    for rd in rests:
        intrinsic = _rest_duration(getattr(rd, "smufl_name", ""))
        if intrinsic is None:
            continue
        base_beats, base_type = intrinsic
        n_dots = dots_by_target_id.get(id(rd), 0)
        final_beats = base_beats * _dot_multiplier(n_dots)
        final_type = f"{_name_for_dots(n_dots)}{base_type}"
        out[id(rd)] = {
            "duration_beats": round(final_beats, 4),
            "duration_type": final_type,
            "dots": n_dots,
        }

    return out
