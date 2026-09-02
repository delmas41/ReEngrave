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

from collections import Counter
from typing import Any

from .voicing import group_chords_in_measure, split_events_into_voices


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

# How far apart two beam detections must be before they count as separate
# LEVELS rather than two readings of one stroke.
#
# Measured, not guessed. Over 951 pairs of adjacent beams sharing a stem on an
# engraved Brahms 1 page, the gaps are plainly bimodal in units of staff-line
# spacing:
#
#     0.19 - 0.26   460 pairs   one physical beam, fragmented
#     0.65 - 0.79    69 pairs   genuinely stacked beams (a 16th)
#
# and 886 of the 951 pairs are classical-CV against classical-CV, so the small
# mode is that detector breaking a single stroke into pieces. The large mode is
# exactly where engraving convention puts stacked beams: thickness 0.5 of a
# staff space plus a 0.25 gap is 0.75 centre to centre.
#
# The old value, 0.22, sat INSIDE the duplicate mode — so a fragmented beam
# became two levels whenever its pieces landed more than 0.22 apart, halving the
# note. Anything in the empty ground between the modes merges every fragment and
# still separates real stacking; swept end-to-end for the value inside it that
# recovers the most correct durations (notes right, out of the matched set):
#
#     factor   beethoven   brahms   total
#     0.22        51         53      104     <- before
#     0.30        49         89      138
#     0.35        48         99      147     <- chosen
#     0.45        48         90      138
#
# Beethoven gives up three notes at any value above 0.22 and does not get them
# back lower down the band, so this is a real if small cost, paid for many times
# over on the denser page.
#
# The surrounding comments in this module assume a canonical line spacing of
# roughly 24-48 px. It is 100. Re-derive, do not scale, if these are retuned.
BEAM_Y_CLUSTER_FACTOR = 0.35

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


# Time-sig glyphs whose left edge sits within this many CANONICAL px of the
# cell's left edge are rejected as misreads. A real time signature is engraved
# AFTER the clef (+ key sig), so it lands ~1.5+ staff-spaces in (observed >=35
# canonical px on real detections); the digit detector, by contrast, clamps
# spurious reads of the stacked instrument-grouping numbers / margin junk on
# orchestral pages to x==0. Canonical coords are scale-normalized (staff span
# is constant, line spacing ~24 px), so this threshold is DPI-independent.
_TIMESIG_MIN_X_CANONICAL = 16


def _timesig_at_left_edge(d: Any) -> bool:
    """True if a time-sig glyph is jammed against the cell's left edge — the
    signature of an instrument-number / margin misread, not a real meter."""
    x = getattr(d, "x_canonical", None)
    return x is not None and x < _TIMESIG_MIN_X_CANONICAL


def parse_time_signature(detections: list[Any]) -> dict[str, Any] | None:
    """Parse a time signature from the time-signature-digit detections in
    a cell, if any. Returns `{numerator, denominator, raw}` or None if no
    time sig markers were seen.

    Algorithm:
      0. Drop glyphs at the extreme left edge (`_timesig_at_left_edge`) —
         orchestral instrument-number misreads clamp there.
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
        if _timesig_at_left_edge(d):
            continue  # margin / instrument-number misread
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

    def _plausible(num: int, den: int) -> dict[str, Any] | None:
        """Reject meters that are not meters.

        Digits are concatenated positionally, so a run of spurious digit
        detections produces arbitrarily large numbers rather than failing:
        measured on an engraved Brahms 1 excerpt this emitted 686/868, 786/86
        and 68/862, which the exporter then wrote into MusicXML as
        `<beats>686</beats>`, making the file unparseable by music21 and by
        notation software. Nothing downstream was in a position to notice,
        because a meter is exactly the kind of fact the rest of the pipeline
        trusts. A denominator must be a note value — a power of two — and no
        repertoire meter has a numerator past the low thirties.
        """
        if den not in (1, 2, 4, 8, 16, 32, 64):
            return None
        if not (1 <= num <= 32):
            return None
        return {"numerator": num, "denominator": den, "raw": f"{num}/{den}"}

    if len(digit_dets) == 1:
        # One visible digit — guess it's the numerator.
        n = digit_dets[0][1]
        return _plausible(n, 4)

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
        except ValueError:
            return None
        return _plausible(num, den)

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
    except ValueError:
        return None
    return _plausible(num, den)


# ---------------------------------------------------------------------------
# Time signature INFERENCE (audit lever, 2026-07)
# ---------------------------------------------------------------------------
#
# DSv2 misclassifies time-sig digit glyphs, so `parse_time_signature` above
# returns None on most measures. Rather than attack the hard digit-detection
# problem, infer the meter from the rhythm the pipeline already resolves:
# majority-vote the per-measure summed durations across a page and back-fill
# the meter where detection failed. This unblocks (a) the per-measure
# rhythm-sum check (skipped when no meter is known) and (b) export, which
# otherwise hardcodes 4/4.
#
# What's actually inferred is the measure's total quarter-note LENGTH; a
# length maps to a canonical meter via the table below. Multiple meters
# share a length (6/8 and 3/4 are both 3.0 quarters; 4/4 and 2/2 both 4.0),
# so the denominator is a best-guess representative — the bar LENGTH (all
# the rhythm-sum check and empty-measure padding need) is what's reliable.
# Compound meters therefore surface as their simple equivalent (6/8 -> 3/4,
# 12/8 -> 6/4) with an identical bar length. Conservative by construction:
# abstains (returns None) unless one length wins a strong plurality.

# Measure total-length (quarter beats) -> representative (numerator,
# denominator). Only real, common meters appear; fused-measure lengths
# (8.5, 12.0, ...) and detection noise are intentionally absent so they
# never vote and never get inferred.
_INFERRABLE_METERS: dict[float, tuple[int, int]] = {
    2.0: (2, 4), 3.0: (3, 4), 4.0: (4, 4), 5.0: (5, 4), 6.0: (6, 4), 7.0: (7, 4),
    1.5: (3, 8), 2.5: (5, 8), 3.5: (7, 8), 4.5: (9, 8), 5.5: (11, 8),
}

# Vote gates (deliberately strict — "leave it null rather than guess wrong").
# The fraction bar is HIGH because the observed lengths are biased, not just
# noisy: on a sparse page no instrument fills the whole bar, so per-column-max
# UNDER-counts (e.g. Boléro p.1, a printed 3/4, has most columns summing to
# ~2.0 because instruments play 2 beats and rest the 3rd — a 0.6 gate inferred
# a wrong 2/4 there). Requiring near-consensus (>=0.8) means only a page where
# the vast majority of bars agree on one length fires; a mere plurality with
# real dissent abstains. (Residual limit: a page that under-counts CONSISTENTLY
# could still clear this — beat-sum inference is the last-resort fallback after
# detected-meter propagation, not a reliable primary.)
_INFER_MIN_VOTES = 6       # min measures/columns with a valid-meter length
_INFER_MIN_MODE_COUNT = 4  # min measures backing the winning meter
_INFER_MIN_FRACTION = 0.8  # winning meter must be this share of valid votes


def _meter_for_length(length_beats: float) -> tuple[int, int] | None:
    """Map an observed measure length (quarter beats) to a canonical meter,
    snapping to the nearest half-beat first (absorbs small rhythm-resolution
    error). Returns None for lengths that aren't a standard meter."""
    snapped = round(length_beats * 2.0) / 2.0
    return _INFERRABLE_METERS.get(snapped)


def measure_length_beats(detections: list[Any]) -> tuple[float, bool]:
    """Observed length of a measure in quarter-note beats, plus whether it
    contains any pitched note (vs rest-only / empty).

    The length is the FULLEST voice's summed durations: a complete voice
    spans the whole bar, and taking the max is robust to a voice with
    under-detected rests (which would sum short). `has_note` is False for
    empty or rest-only measures — a whole rest fills any bar regardless of
    meter, so those carry no meter evidence and callers should skip them.
    """
    events = group_chords_in_measure(detections)
    if not events:
        return 0.0, False
    length = 0.0
    for voice in split_events_into_voices(events):
        s = sum(ev["duration_beats"] for ev in voice)
        if s > length:
            length = s
    has_note = any(ev["kind"] == "chord" for ev in events)
    return length, has_note


def infer_time_signature_from_lengths(
    lengths: list[float],
    *,
    min_votes: int = _INFER_MIN_VOTES,
    min_mode_count: int = _INFER_MIN_MODE_COUNT,
    min_fraction: float = _INFER_MIN_FRACTION,
) -> dict[str, Any] | None:
    """Majority-vote a meter from a list of observed measure lengths.

    Each length is mapped to a canonical meter (`_meter_for_length`);
    lengths that aren't a standard meter are ignored. Returns the winning
    meter dict — tagged `source="inferred"` with `confidence`/`votes`/
    `voters` — only when it clears all three gates, else None.
    """
    votes: Counter[tuple[int, int]] = Counter()
    n_valid = 0
    for length in lengths:
        meter = _meter_for_length(length)
        if meter is None:
            continue
        n_valid += 1
        votes[meter] += 1
    if not votes:
        return None
    (num, den), count = votes.most_common(1)[0]
    if (n_valid < min_votes
            or count < min_mode_count
            or count / n_valid < min_fraction):
        return None
    return {
        "numerator": num,
        "denominator": den,
        "raw": f"{num}/{den}",
        "source": "inferred",
        "confidence": round(count / n_valid, 3),
        "votes": count,
        "voters": n_valid,
    }


def _page_column_lengths(page: dict[str, Any]) -> list[float]:
    """One observed length per (system, measure-column): the max measure
    length across the staves at that column.

    Voting per time-column rather than per staff-measure is what makes this
    work on orchestral scores — at any given bar SOME instrument plays the
    full measure, so the column max recovers the true bar length even when
    most staves are sparse (rests under-detected -> short sums). Fused
    (phase1_warning) and rest-only measures are excluded from the max.
    Within a system, staves share a renumbered measure_index, so grouping
    by that index aligns the columns.
    """
    lengths: list[float] = []
    for system in page.get("systems", []):
        columns: dict[int, float] = {}
        for staff in system.get("staves", []):
            for measure in staff.get("measures", []):
                if measure.get("phase1_warning"):
                    continue
                length, has_note = measure_length_beats(measure.get("detections", []))
                if not has_note or length <= 0:
                    continue
                idx = measure.get("measure_index", 0)
                if length > columns.get(idx, 0.0):
                    columns[idx] = length
        lengths.extend(columns.values())
    return lengths


def infer_page_time_signature(page: dict[str, Any], **kwargs: Any) -> dict[str, Any] | None:
    """Infer a page-level meter by voting the per-column measure lengths.
    Thin wrapper over `infer_time_signature_from_lengths`; returns None
    (abstains) unless the vote is confident."""
    return infer_time_signature_from_lengths(_page_column_lengths(page), **kwargs)


# Detected-meter PROPAGATION gates. Individual detections are unreliable, but
# they AGGREGATE into signal: several staves independently reading the same
# meter, with nothing plausible disagreeing, is stronger than any single read
# and stronger than beat-sum voting on a dense page whose rhythm is corrupted.
#
# SAFETY — the original hazard was the time-sig-digit detector MISREADING the
# stacked instrument-grouping numbers printed left of the clefs ("Flöten 1 2 3
# 4") as a time signature: on a continuation page with no printed meter that
# yields a spurious "2/4" on staff after staff, and those misreads would AGREE
# and propagate a wrong meter across the page. `parse_time_signature` now drops
# them at the source (`_timesig_at_left_edge` — they clamp to the cell's left
# edge, whereas a real meter sits after the clef). With that clean signal, a
# plausible DIGIT meter (num 2-16, denominator a power of two) is safe to
# aggregate too — validated on Boléro p.1 (printed 3/4 on every staff →
# propagated 3/4 correctly). Distinctive `C` / cut-`C` glyphs are always
# propagatable. Two gates still guard it: >=3 measures back the winner AND it
# is >=66% of the propagatable detections (so scattered stray reads can't win).
_PROPAGATE_MIN_COUNT = 2        # min STAVES backing the winning meter
_PROPAGATE_MIN_FRACTION = 0.66  # winner's share of propagatable detections
_PROPAGATABLE_RAWS = frozenset({"C", "C|"})  # common / cut-common glyphs
_VALID_DENOMINATORS = frozenset({1, 2, 4, 8, 16})  # power-of-two beat units

#: Share of a system's staves that must carry the same mid-staff meter before
#: it is believed to be a meter CHANGE rather than a misread.
_PROPAGATE_MIN_CHANGE_FRACTION = 0.5

#: ...and the share of a PAGE's staves that must open in the same meter before
#: it is propagated to the staves that read none. A meter is printed on every
#: staff, so a reading on a handful of them is a misread, however much those
#: few agree with each other.
_PROPAGATE_MIN_STAFF_FRACTION = 0.5

#: `source` values that mark a genuine reading of the page rather than a value
#: this module back-filled. `time_signature_locator` reads the header crop and
#: votes across the system, so its answer is evidence in exactly the way a
#: detection is; anything else with a `source` is derived and must not vote for
#: itself, or `backfill_page_time_signatures` stops being idempotent.
_READING_SOURCES = frozenset({"header_reader"})


def _is_propagatable_meter(ts: dict[str, Any]) -> bool:
    """A detected meter trustworthy enough to aggregate + propagate: the
    distinctive common/cut-common glyphs, or a plausible digit meter
    (numerator 2-16, denominator a power of two). Rejects garbage that could
    survive upstream filtering (6/6, 6/66, 1/1, 1/4)."""
    if ts.get("raw") in _PROPAGATABLE_RAWS:
        return True
    num, den = ts.get("numerator"), ts.get("denominator")
    return (
        isinstance(num, int) and isinstance(den, int)
        and 2 <= num <= 16 and den in _VALID_DENOMINATORS
    )


def _dominant_detected_meter(
    page: dict[str, Any],
    *,
    min_count: int = _PROPAGATE_MIN_COUNT,
    min_fraction: float = _PROPAGATE_MIN_FRACTION,
    min_staff_fraction: float = _PROPAGATE_MIN_STAFF_FRACTION,
) -> dict[str, Any] | None:
    """The dominant *detected* meter safe to propagate across a page — a
    propagatable meter (`_is_propagatable_meter`: common/cut-common glyph or a
    plausible digit meter) read on `min_count`+ measures with no plausible
    dissent. Counts genuine READINGS — detections (no `source`) and the header
    reader's (`_READING_SOURCES`) — and ignores meters this module back-filled,
    keeping `backfill_page_time_signatures` idempotent. Returns a meter dict
    tagged `source="detected_propagated"`, or None.

    **One vote per STAFF, not per measure.** A meter, once read, is carried onto
    every later measure of its staff, so counting measures counts one reading
    many times: on page 3 of the Beethoven 5 scan a single `timeSig4` box at
    confidence 0.42, on one staff of nineteen, was carried through eighteen bars
    and arrived here as eighteen unanimous votes for common time, which it then
    propagated across a 2/4 page. A staff is the unit that actually witnesses a
    meter, and `min_count` counts staves.

    A meter is also printed on every staff of a system, so the winner must be
    read on `min_staff_fraction` of the page's staves as well — two spurious
    readings that happen to agree are unanimous among themselves.

    Assumes `drop_uncorroborated_meter_changes` has already run over the page —
    it is what keeps a misread in the MIDDLE of a staff from voting at all."""
    votes: Counter[tuple[int, int]] = Counter()
    n_staves = 0
    for system in page.get("systems", []):
        for staff in system.get("staves", []):
            n_staves += 1
            for measure in staff.get("measures", []):
                ts = measure.get("time_signature")
                if not ts or (ts.get("source") and ts["source"] not in _READING_SOURCES):
                    continue
                if not _is_propagatable_meter(ts):
                    continue
                # The meter this staff opens in — its one vote.
                votes[(ts.get("numerator"), ts.get("denominator"))] += 1
                break
    if not votes:
        return None
    (num, den), count = votes.most_common(1)[0]
    total = sum(votes.values())
    needed = max(min_count, int(round(min_staff_fraction * n_staves)))
    if count < needed or count / total < min_fraction:
        return None
    raw = "C" if (num, den) == (4, 4) else "C|" if (num, den) == (2, 2) else f"{num}/{den}"
    return {
        "numerator": num,
        "denominator": den,
        "raw": raw,
        "source": "detected_propagated",
        "votes": count,
        "voters": total,
    }


def drop_uncorroborated_meter_changes(
    page: dict[str, Any],
    *,
    min_fraction: float = _PROPAGATE_MIN_CHANGE_FRACTION,
) -> int:
    """Undo mid-staff meter CHANGES that only one staff saw. Returns how many
    measures were reverted; mutates `page`.

    A time signature is printed at the start of a staff, or where the meter
    changes — and a change is a system-wide event, printed on every staff of
    the system at the same bar. A change that appears on one staff in the
    middle of a system is therefore not a meter, it is ink that resembled one.

    It matters because a meter, once read, is carried forward onto every later
    measure of the staff, so a single false reading rewrites the rest of the
    staff and then votes for itself as many times as there are bars left. On
    Beethoven 5 page 1 — a 2/4 page — five `timeSig4` boxes fired on BARLINE
    fragments in bars 6 to 12, each became 4/4 through the single-digit guess
    in `parse_time_signature`, and the page went out as common time on all
    twelve staves. Nothing downstream was placed to doubt it, because a meter is
    exactly the kind of fact the rest of the pipeline takes on trust.

    Reverting means restoring the meter that was in effect before the change,
    which is the meter the staff started the system with. A change corroborated
    on `min_fraction` of the system's staves at the same measure index is left
    alone, so a genuine mid-movement meter change still survives.
    """
    reverted = 0
    for system in page.get("systems", []):
        staves = system.get("staves", [])
        if not staves:
            continue
        # Where each staff's meter changes, and to what.
        changes: list[tuple[dict, int, tuple[int, int]]] = []
        for staff in staves:
            previous: tuple[int, int] | None = None
            for measure in staff.get("measures", []):
                ts = measure.get("time_signature")
                current = (ts.get("numerator"), ts.get("denominator")) if ts else None
                index = measure.get("measure_index") or 0
                if current is not None and previous is not None and current != previous:
                    changes.append((staff, index, current))
                if current is not None:
                    previous = current
        if not changes:
            continue
        witnesses: Counter[tuple[int, tuple[int, int]]] = Counter()
        for _staff, index, meter in changes:
            witnesses[(index, meter)] += 1
        needed = max(2, int(round(min_fraction * len(staves))))
        for staff, index, meter in changes:
            if witnesses[(index, meter)] >= needed:
                continue
            measures = staff.get("measures", [])
            before = None
            for measure in measures:
                if (measure.get("measure_index") or 0) >= index:
                    break
                if measure.get("time_signature"):
                    before = measure["time_signature"]
            for measure in measures:
                if (measure.get("measure_index") or 0) < index:
                    continue
                ts = measure.get("time_signature")
                if not ts:
                    continue
                if (ts.get("numerator"), ts.get("denominator")) != meter:
                    break  # a later change takes over; leave it to its own test
                measure["time_signature"] = dict(before) if before else None
                reverted += 1
    return reverted


def backfill_page_time_signatures(page: dict[str, Any], **kwargs: Any) -> dict[str, Any] | None:
    """Decide a page meter and back-fill it onto every measure/staff whose
    `time_signature` is still None (detection missed it). Genuine detected
    meters are never overwritten. Records the result on
    `page["inferred_time_signature"]` (the dict's `source` says how it was
    decided). Mutates `page` in place; returns the meter dict, or None when
    neither method is confident (nothing is touched).

    Two methods, most-reliable first:
      1. **Propagate a dominant plausible DETECTED meter.** Aggregated digit
         detections beat beat-sum voting on dense pages where rhythm
         resolution is corrupted but the meter WAS read on some measures.
      2. **Beat-sum inference** (`infer_page_time_signature`) as the fallback
         when detection gave nothing usable.

    Uncorroborated mid-staff meter changes are undone first
    (`drop_uncorroborated_meter_changes`); without that, one misread bar votes
    once for every bar after it.
    """
    dropped = drop_uncorroborated_meter_changes(page)
    if dropped:
        page["uncorroborated_meter_changes_reverted"] = dropped
    meter = _dominant_detected_meter(page)
    if meter is None:
        meter = infer_page_time_signature(page, **kwargs)
    if meter is None:
        return None
    for system in page.get("systems", []):
        for staff in system.get("staves", []):
            if not staff.get("time_signature"):
                staff["time_signature"] = dict(meter)
            for measure in staff.get("measures", []):
                if not measure.get("time_signature"):
                    measure["time_signature"] = dict(meter)
    page["inferred_time_signature"] = dict(meter)
    return meter


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


def _deduplicate_beams(beams: list, line_spacing: float) -> list:
    """Drop beam detections that overlap another beam too closely.

    YOLO + classical-CV often both fire on the same physical beam stroke
    at slightly different bboxes. If left alone, the cluster-counter
    treats the duplicate detections as separate vertical levels and
    over-counts beam depth (a 16th becomes a 32nd, etc.).

    Greedy: sort by confidence (descending), keep the first detection,
    drop any later beam whose center is within `line_spacing × 0.18` in
    y AND whose x-range overlaps the kept beam by ≥ 60%.

    THE 0.18 IS DELIBERATELY BELOW the 0.26 top of the measured duplicate mode
    (see BEAM_Y_CLUSTER_FACTOR), and raising it to match was tried and is worse.
    Widening this to 0.35 took Brahms's duration accuracy from 0.485 back to
    0.260 — undoing the entire gain from tuning the cluster boundary — while
    leaving recall, precision and the matched set untouched.

    Merging and dropping are not interchangeable. Clustering collapses fragments
    into one LEVEL while every detection stays available to the end-window and
    anchor logic; this function DELETES detections, and the greedy keep-highest-
    confidence pass then discards real strokes whose partner happened to be
    kept. Fragments are better merged late than removed early.
    """
    y_tol = max(3, int(round(line_spacing * 0.18)))
    sorted_beams = sorted(
        beams,
        key=lambda b: -getattr(b, "confidence", 1.0),
    )
    kept: list = []
    for b in sorted_beams:
        b_y_c = b.y_canonical + b.height_canonical // 2
        b_x_l = b.x_canonical
        b_x_r = b.x_canonical + b.width_canonical
        b_w = max(1, b.width_canonical)
        is_dup = False
        for k in kept:
            k_y_c = k.y_canonical + k.height_canonical // 2
            if abs(b_y_c - k_y_c) > y_tol:
                continue
            # x overlap fraction
            k_x_l = k.x_canonical
            k_x_r = k.x_canonical + k.width_canonical
            overlap = max(0, min(b_x_r, k_x_r) - max(b_x_l, k_x_l))
            if overlap / b_w >= 0.6:
                is_dup = True
                break
        if not is_dup:
            kept.append(b)
    return kept


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
                            beam_y_cluster_tol: float,
                            end_window: float | None = None) -> int:
    """Count distinct vertical beam levels attached to one end of a stem.

    Beams attach to ONE end of a stem (the end opposite the notehead).
    Counting across the WHOLE stem includes beams that belong to other
    voices/staves rendered nearby and inflates the count.

    Algorithm:
      1. Find every beam whose x-range overlaps the stem's x.
      2. Partition them by which stem end they're nearer to (top vs
         bottom).
      3. Within `end_window` of each end, count clusters using
         `beam_y_cluster_tol`.
      4. Return the LARGER of the two end-counts (whichever end has
         beams is the "free" end).

    `end_window` defaults to `4 × beam_y_cluster_tol` — enough room
    for 3-4 stacked beam levels (a 64th-note's worth) at one end.
    """
    s_x_l = stem.x_canonical
    s_x_r = stem.x_canonical + stem.width_canonical
    s_y_top = stem.y_canonical
    s_y_bot = stem.y_canonical + stem.height_canonical
    if end_window is None:
        end_window = beam_y_cluster_tol * 4.0

    top_ys: list[int] = []
    bot_ys: list[int] = []
    for b in beams:
        b_x_l = b.x_canonical
        b_x_r = b.x_canonical + b.width_canonical
        if b_x_r < s_x_l - 5 or b_x_l > s_x_r + 5:
            continue
        b_y_c = b.y_canonical + b.height_canonical // 2
        # Must be at one end of the stem (not in the middle).
        d_top = abs(b_y_c - s_y_top)
        d_bot = abs(b_y_c - s_y_bot)
        if d_top <= end_window and d_top <= d_bot:
            top_ys.append(b_y_c)
        elif d_bot <= end_window:
            bot_ys.append(b_y_c)

    def _count(ys: list[int]) -> int:
        if not ys:
            return 0
        ys = sorted(ys)
        levels = 1
        for i in range(1, len(ys)):
            if ys[i] - ys[i - 1] > beam_y_cluster_tol:
                levels += 1
        return levels

    return max(_count(top_ys), _count(bot_ys))


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

    # Beams stack at ONE end of the stem, within a few beam-thicknesses of
    # each other — `_beams_attached_to_stem` enforces that and stays sane
    # because of it. This fallback did not, and swept every beam in a window
    # 5.5 staff-spaces tall (550 canonical px, taller than a whole staff) into
    # one count. Measured on an engraved Brahms 1 page: 183 noteheads came
    # through here reporting levels of 5, 6, 7 and 8. An eight-beam note is a
    # 1024th; the deepest note in the repertoire is a 64th. The counts were
    # then capped at 4, so the page reported 29 sixty-fourth notes in a passage
    # that contains none, each one an eighth or a quarter cut to a sixteenth of
    # its length.
    #
    # So apply the same physical rule: keep only the beams grouped at the end
    # FARTHEST from the notehead — the free end of the stem, where beams
    # actually attach — and count levels within that group alone.
    attached_ys.sort()
    if abs(attached_ys[0] - nh_y_center) >= abs(attached_ys[-1] - nh_y_center):
        anchor = attached_ys[0]        # beams above → stem points up
    else:
        anchor = attached_ys[-1]       # beams below → stem points down
    end_window = beam_y_cluster_tol * 4.0
    grouped = [y for y in attached_ys if abs(y - anchor) <= end_window]

    # Cluster ys: every contiguous run separated by < tol is one level.
    levels = 1
    for i in range(1, len(grouped)):
        if grouped[i] - grouped[i - 1] > beam_y_cluster_tol:
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


# ---------------------------------------------------------------------------
# Tuplets
# ---------------------------------------------------------------------------
#
# A triplet's noteheads are ORDINARY eighths on the page — the printed note
# value is right and the bracket says three of them occupy two's worth of
# time. So nothing here re-reads a duration; it multiplies one that was
# already correct, which is why this sits after the beam/flag resolution
# rather than inside it.
#
# Measured cost of not doing it: on the engraved Mahler 5 benchmark ALL 15 of
# the wrong durations were `1/3 -> 1/2`, one triplet figure read straight five
# times over, and that is 87 of the work's 154 OMR-NED edits — 57% of its whole
# budget. The detections were already in the JSON (`tuplet3`, `tupletBracket`)
# and no module in the pipeline contained the string "tuplet".
# See benchmarks/omr-ned-2026-08/WRONG_NOTE_ATTRIBUTION_2026-09-01.md.

#: Only the triplet ships. `tuplet5`/`tuplet6`/`tuplet7` are in the DSv2 class
#: space and would each need their own normal-count convention (a 6 is 6-in-4
#: in simple time and 6-in-4 or 6-in-3 depending on how the engraver counts),
#: and none of them occurs in anything measured here. Reading a digit we have
#: not measured is how a correct bar becomes a wrong one, so they abstain.
_TUPLET_NORMAL_FOR: dict[int, int] = {3: 2}


def _tuplet_digit(class_name: str) -> int | None:
    """The number painted on a tuplet bracket: `tuplet3` -> 3. Else None."""
    norm = _normalize_class(class_name)
    if not norm.startswith("tuplet"):
        return None
    tail = norm[len("tuplet"):]
    return int(tail) if tail.isdigit() else None


def _x_span(d) -> tuple[float, float]:
    return (float(d.x_canonical), float(d.x_canonical + d.width_canonical))


def _x_centre(d) -> float:
    return float(d.x_canonical) + d.width_canonical / 2.0


def _beamed_groups(beamed_noteheads: list, beams: list, pad: float) -> list[list]:
    """Split beamed noteheads into the groups the beam boxes say they form.

    GROUPING BY ADJACENCY WOULD BE WRONG, for the reason `export.annotate_beams`
    already records: two beat-groups in one bar sit next to each other and would
    merge into a single run. The beam box gives the extent.

    The box is PADDED, because it bounds the beam INK and a beam starts at the
    first stem — with stems up, the first notehead's centre sits a notehead's
    width to the left of it. Unpadded, every stem-up group loses its first note:
    measured on Mahler's first triplet, beam box x 1659-1957 against noteheads
    centred 1621, 1770, 1918.
    """
    groups: list[list] = []
    for beam in beams:
        lo, hi = _x_span(beam)
        members = [nh for nh in beamed_noteheads if lo - pad <= _x_centre(nh) <= hi + pad]
        if len(members) >= 2:
            groups.append(sorted(members, key=_x_centre))
    return groups


def _tuplet_groups(noteheads: list, out: dict, dets, beams: list,
                   nh_width: float) -> list[tuple[list, int, int]]:
    """Beamed groups that a tuplet marker claims, as `(members, actual, normal)`.

    TWO KINDS OF MARKER, READ DIFFERENTLY, because they sit differently on the
    page. The DIGIT is printed over the middle of the group, so its centre must
    fall inside the group's span. The BRACKET encloses the group, so the group's
    span must fall inside the bracket's — the detected brackets are much wider
    than the notes they cover (one measured at 1846px against a 478px group),
    and testing the bracket's centre instead rejects every one of them.

    A bracket alone carries NO number. It is accepted only for a group of
    exactly three, which is the only reading available for an unnumbered
    bracket, and only when it covers exactly one group in the cell — a wide box
    over two groups cannot say which one it means.
    """
    beamed = [nh for nh in noteheads if (out.get(id(nh)) or {}).get("beam_levels", 0) >= 1]
    if not beamed:
        return []
    groups = _beamed_groups(beamed, beams, pad=nh_width)
    if not groups:
        return []

    digits: list[tuple[float, int]] = []
    brackets: list[tuple[float, float]] = []
    for d in dets:
        if getattr(d, "category", "") != "structural":
            continue
        norm = _normalize_class(getattr(d, "smufl_name", ""))
        if norm == "tupletbracket":
            brackets.append(_x_span(d))
            continue
        digit = _tuplet_digit(getattr(d, "smufl_name", ""))
        if digit is not None:
            digits.append((_x_centre(d), digit))
    if not digits and not brackets:
        return []

    claimed: list[tuple[list, int, int]] = []
    for members in groups:
        lo = _x_centre(members[0])
        hi = _x_centre(members[-1])
        actual = None
        for centre, digit in digits:
            if lo - nh_width <= centre <= hi + nh_width:
                actual = digit
                break
        if actual is None:
            enclosing = [b for b in brackets if b[0] <= lo and hi <= b[1]]
            if len(enclosing) == 1 and len(members) == 3 and sum(
                1 for g in groups
                if enclosing[0][0] <= _x_centre(g[0])
                and _x_centre(g[-1]) <= enclosing[0][1]
            ) == 1:
                actual = 3
        if actual is None:
            continue
        normal = _TUPLET_NORMAL_FOR.get(actual)
        # The group must have as many notes as the digit claims. A triplet
        # written as quarter-plus-eighth is real and is NOT handled: it would
        # need the group's written length rather than its count, and nothing
        # measured here contains one. Abstaining leaves it exactly as wrong as
        # it is today; guessing could make a correct group wrong.
        if normal is None or len(members) != actual:
            continue
        claimed.append((members, actual, normal))
    return claimed


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
    # Beam clustering: a single physical beam may produce multiple
    # detections (CV bbox + YOLO bbox + a fragment from morphological
    # post-processing) at slightly different y positions — those merge
    # into one cluster. Two STACKED beams (16th-note doubles) sit ~10–14
    # px apart center-to-center at canonical resolution. So we want a
    # tolerance just under that:  0.22 × line_spacing ≈ 10–11 px keeps
    # near-duplicates merged but separates stacked-beam levels.
    beam_y_cluster_tol = line_spacing * BEAM_Y_CLUSTER_FACTOR

    noteheads: list = []
    rests_raw: list = []
    beams: list = []
    flags: list = []
    aug_dots: list = []
    for d in dets:
        cat = getattr(d, "category", "")
        cls = _normalize_class(getattr(d, "smufl_name", ""))
        if cat == "notehead":
            noteheads.append(d)
        elif cat == "rest":
            rests_raw.append(d)
        elif cat == "flag":
            flags.append(d)
        elif cat == "structural" and cls == "beam":
            beams.append(d)
        elif cat == "structural" and cls == "augmentationdot":
            aug_dots.append(d)

    # ── Spurious-rest filter ──────────────────────────────────────────────
    # YOLO occasionally produces "rest" detections in dense note clusters
    # (noteheadHalf misclassified as restHalf, etc.) and far above the
    # staff (where ledger lines or markings sit). Real rests live on or
    # very near the staff and don't coexist with noteheads at the same x.
    # Drop rest detections that:
    #   (a) sit more than 2× line_spacing above the top staff line, or
    #   (b) sit more than 2× line_spacing below the bottom staff line, or
    #   (c) overlap a notehead's x-center within ~1 notehead width
    #       (duplicate detection of the same glyph).
    staff_lines = getattr(cell, "staff_line_ys_canonical", None) or []
    if staff_lines:
        staff_top = min(staff_lines)
        staff_bot = max(staff_lines)
    else:
        staff_top = 0
        staff_bot = cell.height if cell is not None else 0
    nh_avg_w = (
        sum(n.width_canonical for n in noteheads) / len(noteheads)
        if noteheads
        else 30
    )
    rest_y_margin = line_spacing * 2.0
    rest_dup_x_tol = max(nh_avg_w * 0.7, line_spacing * 0.8)
    rests: list = []
    for r in rests_raw:
        r_y_c = r.y_canonical + r.height_canonical // 2
        if r_y_c < staff_top - rest_y_margin:
            continue
        if r_y_c > staff_bot + rest_y_margin:
            continue
        # Duplicate-of-notehead filter: any notehead at this x with overlap?
        r_x_c = r.x_canonical + r.width_canonical // 2
        is_dup = False
        for nh in noteheads:
            nh_x_c = nh.x_canonical + nh.width_canonical // 2
            if abs(nh_x_c - r_x_c) < rest_dup_x_tol:
                is_dup = True
                break
        if is_dup:
            continue
        # Duplicate-of-earlier-rest filter: skip rests of the same class
        # whose x-center is within ~1 notehead-width of one we've already
        # kept. YOLO sometimes emits 2-3 rest detections clustered on
        # the same physical glyph (whole-rest, half-rest, etc.).
        rest_class = _normalize_class(getattr(r, "smufl_name", ""))
        is_dup_rest = False
        for existing in rests:
            if _normalize_class(getattr(existing, "smufl_name", "")) != rest_class:
                continue
            ex_x_c = existing.x_canonical + existing.width_canonical // 2
            if abs(ex_x_c - r_x_c) < rest_dup_x_tol:
                is_dup_rest = True
                break
        if is_dup_rest:
            continue
        rests.append(r)

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

    # Deduplicate beams: if two beam detections overlap heavily in both
    # x AND y, they're the same physical beam (CV + YOLO both fired on
    # the same stroke). Keep the one with higher confidence. Without
    # this, the cluster-counter sees doubled levels and over-counts.
    beams = _deduplicate_beams(beams, line_spacing)

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
        # Beam levels this notehead's duration rests on. Stays 0 for whole and
        # half noteheads, which the beam refinement below never touches.
        beam_levels = 0
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
                # Cap at 4 levels (64th note). 128th notes basically
                # never appear in classical engraving, and 5+ beam
                # levels almost always means duplicate-detection noise.
                # Capping at 4 converts the noise to a still-rare-but-
                # plausible 64th rather than an impossible 128th.
                capped = min(n_beam_levels, 4)
                refined = _BEAM_COUNT_DURATIONS.get(capped)
                if refined is not None:
                    base_beats, base_type = refined
                    beam_levels = capped
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
            # How many beam levels this duration rests on. Recorded because it
            # is the most fragile input to the number above — beam levels come
            # from clustering y-positions, so one extra or missing cluster
            # halves or doubles the duration — and because a later pass that
            # knows the meter can arbitrate exactly that. 0 means the duration
            # came from a flag or from the notehead class, neither of which the
            # correction touches. See `transcribe._reconcile_measure_to_meter`.
            "beam_levels": beam_levels,
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

    # ── Tuplets ───────────────────────────────────────────────────────────
    # Applied LAST, and to `duration_beats` only: `duration_type` stays the
    # written value ("eighth"), which is what MusicXML's <type> and LilyPond's
    # `8` both want inside a tuplet. Rests inside a tuplet group are not
    # scaled — pairing a rest to a beam group needs a signal the beam box does
    # not carry, and a wrongly-scaled rest would corrupt the bar's length.
    for group_id, (members, actual, normal) in enumerate(
            _tuplet_groups(noteheads, out, dets, beams, nh_avg_w), start=1):
        for nh in members:
            rec = out.get(id(nh))
            if rec is None:
                continue
            rec["duration_beats"] = round(
                rec["duration_beats"] * normal / actual, 6)
            rec["tuplet"] = {"actual": actual, "normal": normal}
            # Group id so the exporters can put `type="start"`/`"stop"` on the
            # right notes without re-deriving the grouping from x positions.
            rec["tuplet_group"] = group_id

    return out
