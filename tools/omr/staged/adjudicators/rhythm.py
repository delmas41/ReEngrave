"""Duration, tuplets, and the meter.

⚠️ THIS FILE HOLDS THE THIRD HARD EDGE, THE ONE THE DESIGN'S INPUT DOCUMENT
SAID DID NOT EXIST.

`rhythm.measure_length_beats` (`:382-390`) sums `ev["duration_beats"]`;
`_page_column_lengths` (`:453`) calls it per measure; `infer_page_time_
signature` (`:467`) votes those lengths. `duration_beats` is WRITTEN at
`transcribe.py:2335`. So the meter vote's input is the rhythm pass's OUTPUT
FIELD, not its conclusion -- a genuine data dependency.

It is not fatal, because the meter is a DECISION, so under the split it
consumes the DURATION VERDICT and adjudication-order constraints are free.
But it forces a classification the design did not make: `Q.DURATION` is a
VERDICT, not a measurement. The measurements are `Q.BEAM_STROKE`, `Q.FLAG`,
`Q.AUG_DOT` and `Q.NOTEHEAD_CLASS`.

⚠️ AND IT IS A GENUINE LOOP, broken today only by ordering:
`transcribe.py:5382` votes the meter out of committed durations, then `:5410`
REWRITES `duration_beats` from the settled meter. Vote once, repair once. The
repair is a bounded EVALUATE consequence, not a second adjudication.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..adjudicate import (Candidate, Checkable, Evidence, Mode, Ruling,
                          Term, decision, is_relocated_copy, tally)
from collections import Counter

from ... import transcribe as _legacy_stems
from ... import voicing as _legacy_voicing

from .. import movements as _movements
from ..record import (ABSTAIN, DOCUMENT, Kind, Outcome, Q, READERS, Scope,
                      State, Subject, meter_at)
# ⚠️ ROADMAP 2.12l: ONLY the module-level threshold `METER_DIGIT_X_MAX_SPACES`
# is read from here (`_meter_digit_witness_cells`'s own pre-filter, below) --
# never `notehead_precision`'s VERDICT itself at this import site. Aliased
# `_NP`, the same shape `notehead_precision.py` already uses for its own
# sibling import (`from . import ownership as _ledger`); no circular import
# (`notehead_precision.py` does not import `rhythm`).
from . import notehead_precision as _NP
# ⚠️ ROADMAP 2.27d: `grand_staff_partner_staff` is the ONE query "is this
# staff one half of a decided brace pair, and which staff is the other
# half" -- shared with `adjudicators/text.py` and `adjudicators/ownership.py`
# rather than re-derived here a third time (same shape as the `_NP` import
# just above).
from . import structure as _structure
# ⚠️ ROADMAP 2.27c: the SAME sibling-import shape, for `_owned_by_a_
# different_staff` -- `ownership.py` imports neither `rhythm` nor
# `notehead_precision`, so this is not a new circular-import risk.
from . import ownership as _own


#: Notehead class -> written value in beats, before dots and beams.
#: ⚠️ A notehead class is a MEASUREMENT of the glyph; the duration it composes
#: into is a VERDICT, and this table is the composition's first step.
_HEAD_BEATS = {
    "noteheadWhole": 4.0, "noteheadHalf": 2.0, "noteheadBlack": 1.0,
    "noteheadDoubleWhole": 8.0,
}

#: A dot goes ABOVE its note or level with it, NEVER under. (A-DUR-2)
#:
#: ⚠️ ASYMMETRIC ON PURPOSE, and the asymmetry is paid for: Brahms's Viola
#: plays double stops -- two noteheads a space apart, each with its own dot --
#: so the lower dot is equidistant from both noteheads. A SYMMETRIC window
#: TIES, and the upper note comes out double-dotted while the lower loses its
#: dot entirely.
#:
#: ⚠️ And the unit is STAFF SPACES, not the dot's own bounding box. The old
#: gate was `max(dot.height, 12) * 1.2` -- a length derived from a small, noisy
#: box -- and the on-a-line case landed within a few pixels of it and went
#: either way: one horn's dotted half read as a half in bars 1 and 5 and as a
#: dotted half in bars 2, 3, 4 and 6. Measured over 116 dots the signed
#: offsets are BIMODAL and nothing else: 52 at 0.00 spaces, 52 at +0.50,
#: nothing between +0.57 and +3.75.
DOT_ABOVE_NOTE_MAX_SPACES = 0.75
DOT_BELOW_NOTE_MAX_SPACES = 0.25

#: ROADMAP 2.23 -- `Q.NOTEHEAD_INK`'s `center` window must read at or below
#: this to admit "hollow". Measured on the engraved fixture's own truth
#: (`benchmarks/omr-head-fill-2026-09/FINDINGS.md` §1, 372 heads via the
#: detector's own `noteheadHalf`/`noteheadBlack`/`noteheadWhole` class,
#: which agrees with the truth at F1 0.951 on this fixture): every
#: confirmed BLACK head reads `center == 1.0` (532/532); every confirmed
#: HOLLOW HALF head reads `center <= 0.4486` (206/206) -- a clean gap with
#: no overlap.
#:
#: ⚠️ ROADMAP 2.73 RAISED THIS FROM 0.5 TO 0.75, ON SCANS, BY MEASUREMENT AND
#: NOT BY FITTING THE TILES THAT PROMPTED IT. The engraved gap is wide; a scan
#: is not engraved: Litolff's half-note hole is a thin slanted sliver, so its
#: centre window reads mostly ink (Sean's 8 judged Litolff half notes read
#: 0.51-0.72 and every one missed the 0.5 cut). The cut now sits where the
#: FILLED heads stop: Sean's 222 hand-labelled black heads on Brahms 317803
#: pdf 0 read `center >= 0.85` (5th percentile 1.0; his 23 half heads read
#: 0.08-0.84), and on Litolff p3 207 of 228 black-class kept heads read
#: >= 0.95 (`benchmarks/omr-head-fill-2026-09/FINDINGS.md` §8). 0.75 is under
#: both floors; the engraved control still reads 0 of 262 black heads
#: hollow. Together with the ring gap below, which a filled head cannot meet.
HEAD_FILL_HOLLOW_CENTER_MAX = 0.75

#: ROADMAP 2.23 -- the `ring` window must clear `center` by at least this
#: much (same source, same 372 heads): every confirmed HOLLOW HALF head
#: clears by >= 0.1294; every confirmed BLACK head's `ring` reads BELOW its
#: own `center` (gap negative, since a filled head is dense everywhere).
#: A head whose ring and centre read close together is not this rule's
#: population either way -- DECLINED, not defaulted.
#:
#: ⚠️ KNOWN GAP, NOT A DEFECT OF THIS THRESHOLD: confirmed WHOLE heads on
#: the same fixture also read `center == 1.0` (6/6, n small) -- a wide,
#: short box's 30%-shrunk interior lands back on the ellipse's own ink
#: rather than its hole. This test therefore CANNOT separate a genuine
#: WHOLE head from BLACK by ink alone; it catches the HALF-read-as-BLACK
#: population (which is what §17b's crops show) and abstains on the rest,
#: never guessing (rule 6).
HEAD_FILL_HOLLOW_RING_GAP_MIN = 0.1


def _ink_reads_decisively_hollow(ink_detail: Dict[str, Any]) -> bool:
    """`Q.NOTEHEAD_INK.detail` says the ink disagrees with a BLACK class --
    ROADMAP 2.23. Either raster (`ink_raw`, off the UNERASED canonical
    image; `ink_net`, off the staff-erased one) may carry the reading; a
    real head is witnessed by whichever raster still shows it (the same
    two-raster design `gather_notehead_ink`'s own docstring states), so
    ONE of them reading decisively hollow is enough -- this function does
    not require both to agree, only that at least one is decisive and
    neither one's own `center`/`ring` pair is missing where it reads.
    """
    # ⚠️ ROADMAP 2.73: `ink_off_line` is the same reading with the line rows
    # left out, so a staff or ledger line through the hole (which reads as
    # fill on the other two) cannot hide a hollow head. Any ONE decisive
    # reading is enough; none is required to agree.
    for key in ("ink_raw", "ink_net", "ink_off_line"):
        reading = ink_detail.get(key)
        if not isinstance(reading, dict):
            continue
        windows = reading.get("windows") or {}
        center, ring = windows.get("center"), windows.get("ring")
        if center is None or ring is None:
            continue
        if (center <= HEAD_FILL_HOLLOW_CENTER_MAX
                and (ring - center) >= HEAD_FILL_HOLLOW_RING_GAP_MIN):
            return True
    return False


#: ROADMAP 2.70. The abstention reasons that say the CV beam reader RAN on
#: the cell and found no stroke to accept -- a reading ("looked, none"), unlike
#: `not_implemented`/`reader_unavailable` ("did not look"). The reasons are
#: `gather_cv_lines`' own: `no_line_accepted` (it ran, accepted nothing of the
#: kind) and `no_stems_to_join` (fewer than two stems in the cell, so nothing
#: for a beam to join -- a claim about OUR stem reading, not the print; it is
#: accepted here only because the caller already requires THIS head's own stem
#: and a hollow-reading ink).
_BEAM_READER_RAN_EMPTY = (ABSTAIN.NO_LINE_ACCEPTED, ABSTAIN.NO_STEMS_TO_JOIN)


def _beam_reader_looked(ev: Evidence, cell) -> Optional[str]:
    """Did the CV beam reader look at this cell? ROADMAP 2.70.

    `"read"` -- it filed strokes; `"ran_empty:<reason>"` -- it ran and every
    abstention it filed says it accepted none (a cell with no beam at all has
    NO stroke row, so `Evidence.state` calls it DECLINED, and
    `adjudicate_duration` spells that `reader_declined`: Litolff p6
    `glyph/6/1/1/0/10`, a half note, was gated out of 2.23 by exactly that
    conflation); `None` -- it never ran, or ran and failed, which is "cannot
    tell" (rule 8) and never "nothing".
    """
    state = ev.state(Q.BEAM_STROKE, scope=Scope.SELF_AND_ANCESTORS,
                     subject=cell)
    if state is State.READ:
        return "read"
    if state is not State.DECLINED:
        return None
    reasons = [r.reason for r in ev.refusals(
        Q.BEAM_STROKE, scope=Scope.SELF_AND_ANCESTORS, subject=cell)]
    if reasons and all(r in _BEAM_READER_RAN_EMPTY for r in reasons):
        return "ran_empty:" + sorted(set(reasons))[0]
    return None


def _kept_beams(ev: Evidence, cell):
    """CV strokes, plus the YOLO boxes no CV stroke already explains.

    ⚠️ KEPT, NOT UNIONED AND NOT REPLACED, and both alternatives are measured.
    A YOLO beam box bounds the STACK: a box over two strokes contributes a
    centre in the GAP between them, and the run then has no gap wide enough to
    cluster -- three sixteenths read as three eighths. UNIONING them cost
    pooled 0.1917 against 0.1861 for this rule. REPLACING outright scores five
    edits BETTER and is REFUSED: it is the only arm that regresses an authored
    fixture, and the notes that lose EVERY beam they had go from 4 to 7. Five
    edits is less than one measure's amplification is worth; the beams are the
    thing.
    """
    rows = ev.rows(Q.BEAM_STROKE, scope=Scope.SELF_AND_ANCESTORS, subject=cell)
    cv = [r for r in rows if r.reader == READERS.CV_LINES]
    yolo = [r for r in rows if r.reader == READERS.DETECTOR]

    def _overlaps(a, b) -> bool:
        return (a.detail.get("x0", 0) <= b.detail.get("x1", 0)
                and a.detail.get("x1", 0) >= b.detail.get("x0", 0))

    kept = list(cv)
    for box in yolo:
        if not any(_overlaps(box, stroke) for stroke in cv):
            kept.append(box)
    return kept, cv, yolo


#: How far past a stroke's end a notehead may sit and still MAYBE be under it,
#: in notehead widths. (A-DUR-3)
#:
#: ⚠️ A beam stroke ends at the last stem it joins, so a note at the end of a
#: group sits within a notehead's width of the end and the reading is
#: genuinely *"under it, possibly not"*. That ambiguity is the whole reason
#: this returns a RANGE.
BEAM_EDGE_TOLERANCE_WIDTHS = 1.0


def _boxes_overlap(a, b) -> bool:
    """Do two (x, y, w, h) boxes share any area? No tolerance, and none needed.

    ⚠️ MEASURED RATHER THAN CHOSEN. Over the 707 stem/beam pairs of the
    engraved Beethoven 5 iv fixture that overlap in x, 685 also overlap in y
    and the 22 that do not are separated by **35 px or more** -- nothing sits
    in 1-34, so a tolerance would be decoration. Notehead/stem attachment
    separates the same way: 819 heads take exactly one stem, and where none
    overlaps the nearest is 94 px away but for three pairs at 1-2 px.
    """
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax <= bx + bw and ax + aw >= bx
            and ay <= by + bh and ay + ah >= by)


#: How far a FLAG may stand from a head's read stem and still hang from it,
#: and how far past that stem's tip a stroke must lie before it is out of the
#: stem's reach -- in the cell's own staff spaces. (ROADMAP 2.18b)
#:
#: CONVENTION ASSUMED: a flag and a beam are drawn FROM the stem (CLAUDE.md
#: §10, [C12]), so on the print they touch; a gap between their boxes is the
#: READERS' error, not the engraving's. WHAT WOULD FALSIFY IT: a crop where a
#: flag joined through this tolerance hangs from a different stem, or where a
#: stroke dropped as beyond the tip is the note's own beam. NOT CONFIRMED with
#: Sean.
#:
#: ⚠️⚠️ MEASURED, AND THE ENGRAVED ZERO ABOVE DOES NOT TRANSFER. On Breitkopf
#: 317803 p1 (`benchmarks/omr-missing-notes-2026-09/FINDINGS.md` §11):
#:   * every detected flag's nearest read stem is 0.00 (106), 0.01-0.32 (13)
#:     or 1.31+ (15) spaces away -- **nothing between 0.33 and 1.30**;
#:   * the strokes that stand over a head's own column on its stem side, which
#:     this rule never judges, are **0.00-0.80** spaces from its read stem
#:     (n = 101, max 0.80) -- so a stroke further than that past the tip is
#:     further than any of this plate's own beams stand from their stems.
#: 0.8 is the second population's maximum and lies inside the first's empty
#: interval. In units of THIS cell's `Q.CELL_STAFF_SPACE`; a cell without one
#: gets zero (flags back to overlap, and no beyond-the-tip rule at all).
#:
#: ⚠️ IT DOES NOT WIDEN THE STEM->BEAM JOIN -- measured and refused, see
#: `_stem_joined`.
STEM_JOIN_TOLERANCE_SPACES = 0.8


def _box_gap(a, b) -> float:
    """The gap between two (x, y, w, h) boxes: 0 where they overlap or touch,
    else the LARGER of the x and y separations (so `<= tol` means both are).
    `_box_gap(a, b) <= 0` is exactly `_boxes_overlap(a, b)`."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    gx = max(0.0, max(ax, bx) - min(ax + aw, bx + bw))
    gy = max(0.0, max(ay, by) - min(ay + ah, by + bh))
    return max(gx, gy)


def _join_tolerance(ev: Evidence, cell) -> float:
    """`STEM_JOIN_TOLERANCE_SPACES` in this cell's canonical pixels, or 0."""
    rows = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS,
                   subject=cell)
    if not rows:
        return 0.0
    try:
        space = float(rows[-1].value)
    except (TypeError, ValueError):
        return 0.0
    return STEM_JOIN_TOLERANCE_SPACES * space if space > 0 else 0.0


def _xywh(row) -> Optional[Tuple[float, float, float, float]]:
    v = row.value
    if not isinstance(v, (list, tuple)) or len(v) < 4:
        return None
    return (float(v[0]), float(v[1]), float(v[2]), float(v[3]))


def _xywh_head(value) -> Optional[Tuple[float, float, float, float]]:
    """`Q.GLYPH_BOX` is `(smufl_name, x, y, w, h)` -- the name comes FIRST.

    ⚠️ Its own consumers already index past it (`x_center = v[1] + v[3]/2`),
    so the offset is not new; it is spelled once here so a second reader of
    the same row cannot get it wrong.
    """
    if not isinstance(value, (list, tuple)) or len(value) < 5:
        return None
    return (float(value[1]), float(value[2]),
            float(value[3]), float(value[4]))


def _cell_boxes(ev: Evidence, cell):
    """`{glyph key: box row}` for every detection in a cell.

    ⚠️ DELIBERATELY NOT MEMOISED, AND TWO CACHES WERE WRITTEN AND DELETED
    FIRST. The decision is per GLYPH and this map is per CELL, so it is built
    once per notehead — on a dense scan cell, ~100 noteheads over ~300
    detections. A module dict keyed on `id(log)` went red inside a minute
    (CPython recycles an id the moment an object is collected, so two `Log`s
    made in sequence share one and the second reads the first's rows); hanging
    it on the log is impossible, because `Log` has `__slots__`. Both were
    reverted rather than propped up: a cache needs a rule for when to forget,
    and a rule that has to be right for a measurement to be right does not
    belong in the measurement.

    ⚠️ The cost is REAL and is recorded rather than hidden: one adjudication of
    four Litolff scan pages takes ~5 minutes. If it ever needs fixing, the fix
    is `Evidence` caching its own row queries — one place, for every decision —
    not a bolt-on here.
    """
    return {r.subject.to_key(): r for r in ev.rows(
        Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS, subject=cell)}


def _stem_joined(beams, stems, head_box):
    """The beams THIS notehead's stem reaches: (rows, the stems used).

    ⚠️⚠️ A NOTE IS JOINED TO A BEAM BY ITS STEM, AND TESTING THE NOTEHEAD'S
    CENTRE INSTEAD IS WHY BAR SUMS WERE WRONG ON PERFECT INK. A beam stroke
    runs from the FIRST stem it joins to the LAST, and a stem stands at the
    SIDE of its notehead -- so the outer note of every beamed group has its
    centre roughly half a notehead width PAST the stroke's end. Measured on
    the engraved fixture: 114 narrowed durations have a stem that meets a
    beam while the centre test reads `none_over_this_note`, and the overshoot
    clusters at **0.35-0.47 notehead widths**, which is the stem offset and
    nothing else. `BEAM_EDGE_TOLERANCE_WIDTHS` then caught them as POSSIBLE,
    so the reading came out as a RANGE that a consumer had to collapse -- and
    `_bar_lengths_for` collapsed it to the longest.

    ⚠️ ADDITIVE, NEVER SUBTRACTIVE. This is a second tier beside the centre
    test, in the shape `_dedupe_cross_staff_detections`'s ledger ladder
    already has: it can only turn a POSSIBLE into a CERTAIN, so a page whose
    stems are not read behaves exactly as before. Stem-ONLY was measured and
    refused -- same bars, but 60 narrowed against 16, because a head whose
    stem the CV missed then loses its beam entirely.

    ⚠️⚠️ ROADMAP 2.18b MEASURED A TOLERANCE HERE AND REFUSED IT. On Breitkopf
    p1 a head's stem misses strokes that stand over its own column by
    0.00-0.80 spaces, continuously, and the 25 class-E strokes (stem side,
    within reach, not touched) sit in the same band -- no empty interval to
    put a tolerance in. Built anyway at 0.8 and priced, it turned narrowed
    eighths into SIXTEENTHS and a 32nd: many of those strokes are a SECOND
    READING of a beam the head already counts (two CV components 0.5 spaces
    apart, one print beam), and joining them adds a level. So the join stays
    at overlap and E stays NARROWED (FINDINGS §11).

    ⚠️ THE Y HALF OF THE OVERLAP IS UNEXERCISED BY THAT FIXTURE and is tested
    directly instead: on a clean engraving every beam sits at its stems' ends,
    so sweeping a y tolerance 0-64 px moves one row and no bar. It is kept
    because a stem in another octave crossing a beam's column is real ink and
    the x test alone would join them.
    """
    if head_box is None:
        return [], []
    attached = [s for s in stems
                if _xywh(s) and _boxes_overlap(_xywh(s), head_box)]
    if not attached:
        return [], []
    joined = []
    for b in beams:
        box = _xywh(b)
        if box and any(_boxes_overlap(_xywh(s), box) for s in attached):
            joined.append(b)
    return joined, attached


def _beyond_own_stem(beams, stems, attached, side, tol: float):
    """`(strokes kept, strokes that are not this note's)`. ROADMAP 2.18b.

    ⚠️ A BEAM IS DRAWN AT THE STEM'S END AND RUNS FROM THE FIRST STEM IT JOINS
    TO THE LAST (CLAUDE.md §10). A stroke that lies past the tip of this
    head's own read stem by more than the join tolerance, AND that no read
    stem in the cell reaches within it, joins nothing: it is not this note's
    beam. On Breitkopf p1 that is the detector's `beam` box on a hairpin or a
    slur, and the next staff's beam through the cell's pad (FINDINGS §11).

    ⚠️ BOTH HALVES, AND THE SECOND IS THE GUARD. "Past the tip" alone would
    drop the real beam of a head whose stem the CV read SHORT (a shattered
    stem), deciding it unbeamed -- `cannot tell` turned into an answer (rule
    8). A real beam is joined by the other stems of its group; a stroke no
    read stem reaches at all has nothing tying it to any note. Where this
    head has no read stem, or no own stem direction, there is no tip and
    every stroke stays -- and so it does where the cell has no staff-space
    unit (`tol == 0`): "past the tip by more than the slack" cannot be asked
    without the unit the slack is measured in.
    """
    if side is None or not attached or tol <= 0:
        return list(beams), []
    boxes = [_xywh(s) for s in attached if _xywh(s)]
    if not boxes:
        return list(beams), []
    stem_boxes = [_xywh(s) for s in stems if _xywh(s)]
    kept, beyond = [], []
    for b in beams:
        box = _xywh(b)
        if box is None:
            kept.append(b)
            continue
        if side == "up":
            tip = min(sy for (_sx, sy, _sw, _sh) in boxes)
            past = tip - (box[1] + box[3])
        else:
            tip = max(sy + sh for (_sx, sy, _sw, sh) in boxes)
            past = box[1] - tip
        if past > tol and all(_box_gap(sb, box) > tol for sb in stem_boxes):
            beyond.append(b)
        else:
            kept.append(b)
    return kept, beyond


def _ledger_line_glyph_boxes(ev: Evidence, cell):
    """Canonical `(x, y, w, h)` of every DETECTOR-boxed `ledgerLine` glyph
    in THIS cell. ROADMAP 2.25.

    ⚠️ `Q.GLYPH_BOX` ALREADY, so no new `wants` entry: it is the SAME
    quantity this decision reads for the head's own box, at the SAME
    canonical-per-cell frame `Q.BEAM_STROKE` uses -- unlike `Q.WEDGE_BOX`'s
    CV reader, which files page pixels and no canonical box at all
    (`adjudicate_wedge_anchor`'s own docstring: *"comparing a cell-frame
    wedge against a page-frame notehead is the frame error that made
    Q.ONSET_COLUMN report 1,062 columns of nothing"*). Two GLYPH_BOX-family
    rows in ONE cell need no conversion because they are already the same
    frame, which is why this connection is built and the wedge one (below,
    named but not built) is not.
    """
    out = []
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        v = r.value
        if (isinstance(v, (list, tuple)) and len(v) >= 5
                and v[0] == "ledgerLine"):
            out.append(_xywh_head(v))
    return out


def _not_a_ledger_line(beams, ledger_boxes, keep=()):
    """`(kept, dropped)`. ROADMAP 2.25.

    ⚠️ A STROKE THAT OVERLAPS A BOXED `ledgerLine` GLYPH IS THAT LEDGER
    LINE, NOT THIS NOTE'S BEAM. `benchmarks/omr-bar-sum-holdout-2026-09/
    FINDINGS.md` SS17c crops (Brahms #1, #4; Litolff #4): a note standing on
    its own ledger ladder has a short, thick, roughly horizontal run of ink
    at each rung -- exactly the shape `line_detection`'s beam opening and the
    detector's own `beam` class both fire on. Two readers naming the SAME
    ink two different things is not two facts; the ledgerLine reading
    (`Q.GLYPH_BOX`, a DETECTION) is the more specific claim about what the
    ink IS, and a beam stroke that stands where a ledger line is boxed
    inherits that claim rather than contesting it.

    ⚠️ ADDITIVE, NEVER SUBTRACTIVE OF THE RECORD -- same discipline as
    `_beyond_own_stem`: it can only remove a stroke from THIS note's count,
    never add one, and a cell with no boxed ledger line drops nothing, so a
    page the detector never boxed a ledgerLine on behaves exactly as before.
    No rule-8 guard is added here (unlike `_beyond_own_stem`'s): pricing
    (FINDINGS SS19) found no case where this step alone left a note with no
    other mark, and 2.18b's own guard already covers the general fallback
    where it does.
    """
    if not ledger_boxes:
        return list(beams), []
    kept, dropped = [], []
    keep = set(keep)
    for b in beams:
        box = _xywh(b)
        # ⚠️ ROADMAP 2.75: `keep` is the strokes that PASS every beam test the
        # ink can read (thick, straight, a stem found at BOTH ends). The
        # detector draws `ledgerLine` boxes over real beams too (Litolff p3
        # cell 3/0/7/4: a 1.5-space-tall box over a stem-down beam), and a
        # ledger line has no stem at either end.
        if b.id not in keep and box is not None \
                and any(_boxes_overlap(box, lb)
                        for lb in ledger_boxes if lb is not None):
            dropped.append(b)
        else:
            kept.append(b)
    return kept, dropped


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.71 -- a TREMOLO SLASH is not a beam level (Sean, 2026-10-09:
# *"The trem slash is very different from a beam. Beams have to be connected to
# other notes - slashes never are. ... The slash crosses both sides of the stem
# with a thick line at an angle."*). `gather.stem_slashes` names it ONCE
# (`Q.STEM_SLASH`: a thick angled stroke crossing both sides of one stem and
# joined to no other stem); a beam stroke that IS that ink is dropped from the
# count here, by the same fact the hook reader blanked it by.
# ─────────────────────────────────────────────────────────────────────────────

#: A stroke is the slash's own ink where at least this share of its box lies
#: inside the slash's footprint (padded by `SLASH_FOOTPRINT_PAD_SPACES`) AND it
#: is no wider than the footprint plus `SLASH_EXTRA_WIDTH_SPACES` -- a long beam
#: that merely passes the footprint is not the slash.
SLASH_STROKE_INSIDE_MIN = 0.6
SLASH_FOOTPRINT_PAD_SPACES = 0.3
SLASH_EXTRA_WIDTH_SPACES = 0.8


def _slash_footprints(ev: Evidence, cell) -> List[Tuple[float, float, float, float]]:
    """Every PASSING slash's footprint `(x0, y0, x1, y1)` in this cell's
    canonical frame, read off `Q.STEM_SLASH` (GATHER). Empty where no row says
    a slash stands here -- a cell the reader never ran on drops nothing."""
    out: List[Tuple[float, float, float, float]] = []
    for r in ev.rows(Q.STEM_SLASH, scope=Scope.SELF_AND_ANCESTORS, subject=cell):
        for s in (r.detail or {}).get("strokes") or ():
            b = s.get("box")
            if s.get("reason") is None and isinstance(b, (list, tuple)) \
                    and len(b) == 4:
                out.append(tuple(float(v) for v in b))
    return out


def _not_a_slash(ev: Evidence, cell, beams):
    """`(kept, dropped, rows)`. ROADMAP 2.71. A beam stroke that is a read
    tremolo slash's own ink is not this note's beam level; it also does not
    NARROW the head (it is a mark of another kind, not an absence), so the
    caller keeps it out of the rule-8 guards."""
    feet = _slash_footprints(ev, cell)
    if not feet:
        return list(beams), [], ()
    space_rows = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS,
                         subject=cell)
    space = float(space_rows[-1].value) if space_rows else 0.0
    pad = SLASH_FOOTPRINT_PAD_SPACES * space
    extra = SLASH_EXTRA_WIDTH_SPACES * space
    kept, dropped = [], []
    for b in beams:
        box = _xywh(b)
        hit = False
        if box is not None and box[2] > 0 and box[3] > 0:
            bx0, by0, bx1, by1 = box[0], box[1], box[0] + box[2], box[1] + box[3]
            for fx0, fy0, fx1, fy1 in feet:
                ix = min(bx1, fx1 + pad) - max(bx0, fx0 - pad)
                iy = min(by1, fy1 + pad) - max(by0, fy0 - pad)
                if ix <= 0 or iy <= 0:
                    continue
                if (ix * iy) / (box[2] * box[3]) >= SLASH_STROKE_INSIDE_MIN \
                        and box[2] <= (fx1 - fx0) + extra:
                    hit = True
                    break
        (dropped if hit else kept).append(b)
    used = tuple(r for r in ev.rows(Q.STEM_SLASH, scope=Scope.SELF_AND_ANCESTORS,
                                     subject=cell)
                 if any(s.get("reason") is None
                        for s in (r.detail or {}).get("strokes") or ())
                 ) if dropped else ()
    return kept, dropped, used


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.25b -- the three larger classes 2.25 named and did not build:
# a stroke that belongs to the NEIGHBOUR staff through the cell's own pad, a
# stroke that is a decided SLUR/TIE's own ink, and a stroke inside a hairpin.
# All three need a page<->canonical conversion `Q.BEAM_STROKE` itself never
# carries -- this is that ONE helper, used by all three, round-trip tested.
# ─────────────────────────────────────────────────────────────────────────────


def _cell_frame(ev: Evidence, cell) -> Optional[Tuple[float, float, float]]:
    """`(origin_x, origin_y, up)` solving `page = origin + canonical / up`
    for THIS cell -- the SAME affine `gather._page_box` computes forward
    (`gather.py`: *"canonical cell coordinates -> page pixels"*), solved
    backward from any ONE `Q.GLYPH_BOX` row in the cell that already
    carries BOTH frames (its own `value` is canonical, its own
    `detail.bbox_page_px` is page).

    ⚠️ NOT A NEW QUANTITY. There is no persisted `upscale_factor` on a saved
    record -- it is a runtime attribute of the GATHER-time cell object, not
    written down -- so this recovers it from data the record already
    carries twice over (the same box, in both frames), rather than
    inventing one. `Q.CELL_BOX` is not needed either: ONE dual-frame box
    fully determines the transform (two points fix an affine map with a
    known, uniform scale -- `_upscale_to_canonical` resizes a cell by ONE
    factor, never separate x/y ones).

    ⚠️ DECLINED, NEVER GUESSED, where no such row exists in this cell
    (CLAUDE.md rule 6; the same discipline `adjudicate_wedge_anchor`
    states: *"a row without them abstains"*) -- every one of this item's
    three new connections falls through to KEEPING the stroke where this
    returns `None`, exactly as `_beyond_own_stem` does with no staff-space
    unit.
    """
    for row in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                       subject=cell):
        v = row.value
        d = row.detail or {}
        page = d.get("bbox_page_px")
        if not isinstance(v, (list, tuple)) or len(v) < 5 \
                or not page or len(page) != 4:
            continue
        cx, cy, cw, ch = float(v[1]), float(v[2]), float(v[3]), float(v[4])
        px0, py0, px1, py1 = (float(x) for x in page)
        up = None
        if px1 - px0 > 0:
            up = cw / (px1 - px0)
        elif py1 - py0 > 0:
            up = ch / (py1 - py0)
        if not up:
            continue
        return (px0 - cx / up, py0 - cy / up, up)
    return None


def _to_page(box, frame):
    """Canonical `(x, y, w, h)` -> page pixels, through `_cell_frame`."""
    ox, oy, up = frame
    x, y, w, h = box
    return (ox + x / up, oy + y / up, w / up, h / up)


def _to_canonical(box, frame):
    """Page-pixel `(x, y, w, h)` -> this cell's canonical, through
    `_cell_frame` -- the exact inverse of `_to_page`."""
    ox, oy, up = frame
    x, y, w, h = box
    return ((x - ox) * up, (y - oy) * up, w * up, h * up)


def _joins_n_stems(box, stems) -> int:
    """How many DIFFERENT `Q.STEM` boxes this stroke's box overlaps -- the
    signature of a genuine beamed group (drawn to span several stems), used
    below as the override that keeps a real beam even where it happens to
    sit inside a slur's or a hairpin's own box."""
    return sum(1 for s in stems if _xywh(s) and _boxes_overlap(_xywh(s), box))


def _not_the_neighbours_beam(ev: Evidence, cell, beams, stems, own_stems):
    """`(kept, dropped)`. ROADMAP 2.25b, class 1 (`other_staff_via_pad`,
    150 Brahms / 7 Litolff heads, FINDINGS SS13).

    ⚠️ THE DECIDED FACT IS A STEM, NOT A DISTANCE. A stroke lying beyond
    THIS staff's own outer line (`Q.STAFF_LINES`, page frame) -- in the pad
    the cell's own crop reaches into (CLAUDE.md SS10: "the measure cell is
    padded 4 spaces... and reaches the next staff's ink") -- that ALSO
    overlaps, in page pixels, a `Q.STEM` row filed on the NEIGHBOURING
    staff's own SAME-cell subject ("or cells of the neighbouring staff",
    the manager's own fallback -- an ownership CONTEST is not asked; the
    stem merely being filed there is enough) is that staff's beam.

    ⚠️ THE OVERRIDE (rule 6, never discount past a stronger fact): a stroke
    ALSO reached by one of THIS head's own attached stems stays, whatever
    else it touches -- a beam spanning a wide group can legitimately pass
    near a neighbour's stem without being that neighbour's ink.

    ⚠️ DECLINED, NEVER GUESSED, where this cell's or the neighbour cell's
    own `_cell_frame` cannot be solved (no dual-frame glyph box in either)
    -- the stroke stays, exactly as `_not_a_ledger_line` leaves every
    stroke where the cell holds no boxed ledger line.

    ⚠️ ROADMAP 2.27d: A STROKE TOUCHING ONLY THE PART'S OWN OTHER STAFF IS
    NOT DROPPED. On a DECIDED brace pair (`Q.GROUP_SYMBOL` "brace", the same
    fact `adjudicators/text.py`'s grand-staff dynamics rule connects to)
    the OTHER staff of the pair is not "the neighbour" for this rule's
    purpose -- a beam crossing from one hand's stems to the other's is ONE
    beam of the PART. If a stroke touches BOTH the partner's stems and some
    OTHER staff's (a three-staff crowd), it still drops: the exemption is
    for the decided pair only, never a guess about which neighbour a mixed
    touch means. Off a decided brace this is exactly the 2.25b rule,
    unchanged -- inert on every orchestral system (control: a bracket of
    two ordinary staves, e.g. two horns, never decides "brace" and every
    touch there still drops, as before this roadmap item).
    """
    lines = ev.rows(Q.STAFF_LINES, scope=Scope.SELF_AND_ANCESTORS,
                    subject=cell.at(Kind.STAFF))
    frame = _cell_frame(ev, cell)
    if not lines or not lines[-1].value or frame is None:
        return list(beams), []
    ys = [float(y) for y in lines[-1].value]
    top, bottom = min(ys), max(ys)

    # `(neighbour_staff_index, page_box)` -- kept per-staff, not flattened,
    # so the brace exemption below can ask WHICH staff a touched stem
    # belongs to rather than merely whether some neighbour has one there.
    neighbour_stems_page: List[Tuple[int, Tuple[float, float, float, float]]] = []
    for delta in (-1, 1):
        st = cell.staff + delta if cell.staff is not None else None
        if st is None or st < 0:
            continue
        ncell = Subject(Kind.CELL, page=cell.page, system=cell.system,
                        staff=st, cell=cell.cell)
        nframe = _cell_frame(ev, ncell)
        if nframe is None:
            continue
        for s in ev.rows(Q.STEM, scope=Scope.EXACT, subject=ncell):
            box = _xywh(s)
            if box is not None:
                neighbour_stems_page.append((st, _to_page(box, nframe)))
    if not neighbour_stems_page:
        return list(beams), []

    home_sub = Subject(Kind.STAFF, page=cell.page, system=cell.system,
                       staff=cell.staff)
    # ⚠️ ROADMAP 2.27d, THE CHEAP HALF READ DIRECTLY. Every orchestral
    # system fails one of these two checks (no group ever decides
    # `Q.GROUP_SYMBOL` "brace"), so confirming them here -- before asking
    # `structure` to enumerate the system's other staves -- is a real
    # short-circuit on the common case, and it is what makes `wants`'
    # declaration of both quantities true of THIS file's own body.
    partner_staff = None
    brace = ev.verdict(Q.GROUP_SYMBOL, subject=home_sub.at(Kind.SYSTEM))
    if brace is not None and brace.value == "brace":
        own_group = ev.verdict(Q.STAFF_GROUP, subject=home_sub)
        if own_group is not None and own_group.value is not None:
            partner_key = _structure.grand_staff_partner_staff(
                ev, home_sub.to_key())
            if partner_key is not None:
                partner_staff = Subject.from_key(partner_key).staff

    kept, dropped = [], []
    for b in beams:
        box = _xywh(b)
        if box is None:
            kept.append(b)
            continue
        # ⚠️ THE OVERRIDE IS A BOX TEST, NOT AN ID TEST -- `own_stems` are
        # STEM rows and `b` is a BEAM row; the two never share an id. The
        # question is whether THIS stroke is reached by one of this head's
        # own attached stems, the same overlap test `_stem_joined` uses.
        if any(sbox and _boxes_overlap(box, sbox)
               for sbox in (_xywh(s) for s in own_stems)):
            kept.append(b)
            continue
        page_box = _to_page(box, frame)
        pyc = page_box[1] + page_box[3] / 2.0
        beyond_outer = pyc < top or pyc > bottom
        touching_staffs = {nst for nst, nb in neighbour_stems_page
                           if _boxes_overlap(page_box, nb)}
        if beyond_outer and touching_staffs:
            if partner_staff is not None and touching_staffs <= {partner_staff}:
                # ⚠️ ROADMAP 2.27d: every staff this stroke touches is the
                # decided brace partner and none other -- the part's own
                # cross-staff beam, kept.
                kept.append(b)
            else:
                dropped.append(b)
        else:
            kept.append(b)
    return kept, dropped


def _not_a_decided_arc(ev: Evidence, cell, beams, stems):
    """`(kept, dropped)`. ROADMAP 2.25b, class 2 (`arc_box`, 139 Brahms
    heads, FINDINGS SS13).

    ⚠️ THE DECIDED FACT IS `Q.ARC_KIND`, NOT MERE OVERLAP WITH A BOX (rule
    6). `adjudicate_arc_kind` runs before `duration` in `adjudicate.ORDER`,
    so its verdict is already settled: an `Q.ARC_BOX` glyph this decision
    reads must have DECIDED (`tie` or `slur`) before a stroke over it is
    discounted -- an abstained or refused arc box (`Q.ARC_IS_NOT_AN_ARC`)
    proves nothing about the ink and discounts nothing.

    ⚠️ THE OVERRIDE, THE MANAGER'S OWN POSITIVE CONTROL: *"a real beam
    overlapping a slur's box still counts when it joins >= 2 of this
    staff's stems"* -- `_joins_n_stems`, over every `Q.STEM` filed in THIS
    cell (not just this note's own), because a genuine beam is drawn to
    span several stems and a slur's bounding box coincidentally covering
    one is not evidence against that.
    """
    arcs = []
    for r in ev.rows(Q.ARC_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        d = r.detail or {}
        if not all(k in d for k in ("x0", "x1", "y0", "y1")):
            continue
        v = ev.verdict(Q.ARC_KIND, subject=r.subject)
        if v is None or v.outcome is not Outcome.DECIDED:
            continue
        arcs.append((float(d["x0"]), float(d["y0"]),
                    float(d["x1"]) - float(d["x0"]),
                    float(d["y1"]) - float(d["y0"])))
    if not arcs:
        return list(beams), []
    kept, dropped = [], []
    for b in beams:
        box = _xywh(b)
        if box is None:
            kept.append(b)
            continue
        if any(_boxes_overlap(box, a) for a in arcs) \
                and _joins_n_stems(box, stems) < 2:
            dropped.append(b)
        else:
            kept.append(b)
    return kept, dropped


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.74 -- a BEAM is thick, straight, and stands on two stems.
#
# Sean, 2026-10-09 (DECISIONS), on 2.65 tiles 1, 4, 15 and 21, where a slur, a
# tie or a hairpin boxed as a beam made an eighth read a sixteenth or a
# 128th: *"A beam must not only connect to its note but also to another
# note."* / *"A beam never has an arc."* / *"The thickness on a beam is
# always more than a hairpin."* Each is a test a stroke must PASS to count as
# this note's beam, and each is READ OFF THE INK (`Q.BEAM_STROKE_INK`, GATHER):
# a test that could not be read ABSTAINS -- the stroke stays and the existing
# rules judge it -- it never passes or fails by default (rule 8).
#
# CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED beyond Sean's
# three lines: the numbers below. A beam is `BEAM_THICKNESS_RATIO_MIN` times
# the staff line's own thickness, measured at the stroke's own columns on the
# plate (a hairpin's line is about one). Falsified by a print-confirmed beam
# under it, a slur over it, or a real beam this drops (`FINDINGS.md` §15
# crops).
# ─────────────────────────────────────────────────────────────────────────────

#: A beam's median thickness, in multiples of the staff line's thickness AT its
#: own columns. Local on purpose (CLAUDE.md §10: a scan's weight changes
#: across a system), a ratio and never a pixel count (two plates, two
#: resolutions).
#:
#: ⚠️ MEASURED ON BOTH PLATES (`FINDINGS.md` §15, the CV strokes with a stem
#: read at BOTH ends -- the strokes most surely beams): Brahms p0-1 172 of 174
#: read 2.5 or more; Litolff p1-3 130 of 131 read 2.0 or more; the thin strokes
#: (hairpin lines, slur and tie arcs, staff-line residue) read 1.75 or less on
#: both. 1.75 sits in the empty interval of both plates (it is the midpoint of
#: the thin population's top, ~1.5, and the thinnest beam, 2.0), and is far
#: from the hairpin line's own ~1.0-1.3.
BEAM_THICKNESS_RATIO_MIN = 1.75

#: How far a beam may bow from straight, in staff spaces (the sagitta of a
#: parabola fitted to its straightest edge or centre line). "A beam never has
#: an arc."
#:
#: ⚠️ MEASURED, AND IT IS THE LOOSER OF THE TWO RULERS. Brahms p0-1 and
#: Litolff p1-3: every CV stroke at or over the thickness cut reads 0.00-0.23
#: spaces but one (a real Brahms beam FUSED to a slur's tail, 0.30); the thin
#: slur strokes read 0.18-0.26. The populations overlap, so a cut that keeps the
#: fused beam cannot refuse a slur by its bow alone -- the thickness rule does
#: that work. What this cut refuses is a THICK stroke bowed past it: on both
#: plates, detector boxes over a whole cluster of ink (0.4-1.4 spaces).
BEAM_SAGITTA_MAX_SPACES = 0.40

#: How far (staff spaces) a one-stem stroke may lie from a stroke that stands
#: on two stems and still be that beam group's own secondary level (a
#: beamlet). A secondary beam sits about 0.3-0.7 spaces from the primary.
BEAM_BEAMLET_GAP_SPACES = 1.0


#: A stroke whose box lies at least this much INSIDE the cell's notehead boxes
#: is those heads' own ink, not a beam. ROADMAP 2.75 (Sean, 2026-10-09, 2.74
#: review Litolff 1: printed eighth, read 32nd then 16th).
#:
#: ⚠️ MEASURED, `FINDINGS.md` §16. The stroke on that tile (obs:036863, a
#: second ledger line through a row of three heads, fused with them: 1.08
#: spaces thick, which is why 2.74's thickness test passed it) lies 0.80
#: inside the heads' boxes. Of 1,659 CV/detector strokes on Brahms p0-1 and
#: Litolff p1-3 the ones over 0.5 are rows of heads and ledger lines through
#: them; a beam stands at the far end of its stems and runs BETWEEN them. The
#: cut sits in the gap between the beams the crops show (0.0-0.3, a beam
#: touching one head's edge) and the head rows (0.55 and up).
BEAM_THROUGH_HEADS_MIN = 0.5


#: A detector box wider than this (staff spaces) is not ONE notehead: a head is
#: ~1.3 spaces wide and a whole note ~1.8 (CLAUDE.md §10). Measured on Brahms p1
#: (`FINDINGS.md` §16): a `noteheadWholeOnLine` box 3.2 spaces wide stood over a
#: real stem-down beam (cell 1/0/0/4) and would have refused it as "the heads'
#: ink" -- so a box this wide is a cluster the detector drew, never evidence of
#: where a head's ink is.
BEAM_HEAD_BOX_MAX_SPACES = 2.2


def _notehead_glyph_boxes(ev: Evidence, cell, space: float):
    """Canonical `(x, y, w, h)` of every DETECTOR-boxed notehead in THIS
    cell -- the same `Q.GLYPH_BOX` family `_ledger_line_glyph_boxes` reads, at
    the same canonical frame `Q.BEAM_STROKE` is in -- that is head-SIZED
    (`BEAM_HEAD_BOX_MAX_SPACES`). `[]` where the cell has no staff-space unit:
    without it a box cannot be judged a head, and the rule then does not run.
    ROADMAP 2.75."""
    out = []
    if not space or space <= 0:
        return out
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        v = r.value
        if (isinstance(v, (list, tuple)) and len(v) >= 5
                and str(v[0]).startswith("notehead")):
            b = _xywh_head(v)
            if b is not None and b[2] <= BEAM_HEAD_BOX_MAX_SPACES * space:
                out.append(b)
    return out


def _covered_fraction(box, others) -> float:
    """The fraction of `box`'s area (`x, y, w, h`) that lies inside the UNION
    of `others` -- exact (a sweep over the y breakpoints), because a row of
    heads overlaps itself and summing the intersections would count a shared
    corner twice."""
    x, y, w, h = box
    if w <= 0 or h <= 0:
        return 0.0
    clipped = []
    for ox, oy, ow, oh in others:
        x0, x1 = max(x, ox), min(x + w, ox + ow)
        y0, y1 = max(y, oy), min(y + h, oy + oh)
        if x1 > x0 and y1 > y0:
            clipped.append((x0, y0, x1, y1))
    if not clipped:
        return 0.0
    ys = sorted({c[1] for c in clipped} | {c[3] for c in clipped})
    area = 0.0
    for ya, yb in zip(ys, ys[1:]):
        spans = sorted((c[0], c[2]) for c in clipped if c[1] <= ya and c[3] >= yb)
        covered, last = 0.0, None
        for a, b in spans:
            if last is None or a > last:
                covered += b - a
                last = b
            elif b > last:
                covered += b - last
                last = b
        area += covered * (yb - ya)
    return area / float(w * h)


def _beam_anchor_ids(ev: Evidence, cell, beams, tol: float, head_boxes):
    """The ids of strokes that PASS every beam test the ink can READ: thick
    (`BEAM_THICKNESS_RATIO_MIN`), straight (`BEAM_SAGITTA_MAX_SPACES`), a stem
    found at BOTH ends, and not lying through the cell's heads. A test the ink
    did not read fails the stroke here (it is NOT an anchor), so this only ever
    EXEMPTS a stroke from a refusal that rests on a box -- never admits one.
    ROADMAP 2.75."""
    ink = _beam_ink_rows(ev, cell)
    out = set()
    for b in beams:
        row = ink.get(b.id)
        if row is None:
            continue
        d = row.detail or {}
        ratio, sag = d.get("thickness_ratio"), d.get("sagitta_spaces")
        ends = d.get("end_stems") or []
        if ratio is None or sag is None or ratio < BEAM_THICKNESS_RATIO_MIN \
                or sag > BEAM_SAGITTA_MAX_SPACES:
            continue
        if not (len(ends) == 2 and all(isinstance(e, dict) and e.get("found")
                                       for e in ends)):
            continue
        box = _xywh(b)
        if box is None or (head_boxes and _covered_fraction(box, head_boxes)
                           >= BEAM_THROUGH_HEADS_MIN):
            continue
        out.add(b.id)
    return out


def _voice_stems(own_stems, head_box):
    """`{"up": [stems], "down": [stems]}` -- this head's own stems split by
    which way they run from the head's centre. A head with a stem each way is
    one printed head shared by TWO voices (a unison): each voice's stem has its
    OWN beam. ROADMAP 2.75."""
    if head_box is None:
        return {"up": [], "down": []}
    hyc = head_box[1] + head_box[3] / 2.0
    out = {"up": [], "down": []}
    for s in own_stems:
        b = _xywh(s)
        if b is None:
            continue
        out["up" if (b[1] + b[3] / 2.0) < hyc else "down"].append(s)
    return out


def _beam_ink_rows(ev: Evidence, cell) -> Dict[str, Any]:
    """`{beam row id: Q.BEAM_STROKE_INK row}` for this cell. ROADMAP 2.74."""
    out: Dict[str, Any] = {}
    for r in ev.rows(Q.BEAM_STROKE_INK, scope=Scope.SELF_AND_ANCESTORS,
                     subject=cell):
        bid = (r.detail or {}).get("beam_row_id")
        if bid:
            out[bid] = r
    return out


def _stems_a_stroke_stands_on(row, ink_row, stems, tol: float):
    """`(distinct stem count, read)`. How many different stems the stroke
    stands on: every read `Q.STEM` within the join tolerance of its box, plus
    each end the INK says a vertical run leaves. `read` is False where the
    ink reader did not say either end (then the count says nothing). ROADMAP
    2.74.

    ⚠️ PERMISSIVE ON PURPOSE, because the only use of a LOW count is to
    refuse a stroke: a stem within `tol` of the box counts even though it
    does not touch it (the join the CV beam reader itself used), so the
    stroke is refused only where nothing, anywhere near it, is a stem.
    """
    box = _xywh(row)
    ends = (ink_row.detail or {}).get("end_stems") or []
    ends_read = (len(ends) == 2
                 and all(isinstance(e, dict) and e.get("found") is not None
                         for e in ends))
    if box is None or not ends_read or tol <= 0:
        return 0, False
    xs = []
    for s in stems:
        sb = _xywh(s)
        if sb is not None and _box_gap(sb, box) <= tol:
            xs.append(sb[0] + sb[2] / 2.0)
    for e in ends:
        if e.get("found") and e.get("x") is not None:
            xs.append(float(e["x"]))
    xs.sort()
    distinct, last = 0, None
    for x in xs:
        if last is None or x - last > 0.75 * tol:
            distinct += 1
            last = x
    return distinct, True


#: A stroke stands on stems where at least this many DIFFERENT read stems END
#: inside its box. ROADMAP 2.77b (Sean, 2.74: *"A beam must not only connect to
#: its note but also to another note."*) -- the same two stems, counted off the
#: CV stem rows instead of the ink reader's end window.
#:
#: ⚠️ MEASURED, `FINDINGS.md` §16.7. Over the 109 strokes the ink reader read
#: at BOTH ends with a stem found at NEITHER (thick and straight: the population
#: 2.77's `no_stem_at_ends` refuses) on Litolff p0-3 and Brahms p0-1, 5 have two
#: or more read stems ending inside their box, and all 5 are printed beams on
#: the page crops (a sloped beam's end window misses its stem; 4 of the 5 are
#: detector boxes); the dynamic letter's foot bar 2.77 was built to refuse has
#: none (its stems end 24-36 px above it); 5 have exactly one and 99 none (not
#: eye-checked: they stay refused, as before).
BEAM_STEMS_ENDING_MIN = 2

#: Two read stems closer than this (staff spaces, centre to centre) are one
#: stem read twice (a stem fused to a head and cut in two), not two stems.
BEAM_STEMS_ENDING_SEPARATION_SPACES = 0.4


def _stems_ending_in(box, stems, separation: float) -> int:
    """How many DIFFERENT read `Q.STEM` stems END inside this stroke's box: the
    stem overlaps the box in x and its top or bottom edge lies within the box's
    y range. A stem that merely passes beside or through a stroke (a bar under
    a beam, a secondary beam across stems) ends elsewhere and is not counted.
    ROADMAP 2.77b.

    ⚠️ INSIDE THE BOX, NOT WITHIN A TOLERANCE OF IT, and measured: the stems
    that stand on a dynamic letter's foot bar (Litolff p3) end 24-36 px above
    it and a tolerance of the join's size (80 px) would credit them."""
    bx, by, bw, bh = box
    xs = []
    for s in stems:
        sb = _xywh(s)
        if sb is None:
            continue
        sx, sy, sw, sh = sb
        if sx + sw < bx or sx > bx + bw:
            continue
        if by <= sy <= by + bh or by <= sy + sh <= by + bh:
            xs.append(sx + sw / 2.0)
    xs.sort()
    distinct, last = 0, None
    for x in xs:
        if last is None or x - last > separation:
            distinct += 1
            last = x
    return distinct


def _not_a_beam_by_ink(ev: Evidence, cell, beams, stems, tol: float):
    """`(kept, {stroke id: reason}, ink rows read)`. ROADMAP 2.74.

    A stroke is NOT a beam where the ink READS it so, by the first that
    fails: `too_thin` (median thickness under `BEAM_THICKNESS_RATIO_MIN`
    staff lines -- a hairpin's line, a slur's or tie's tapering arc),
    `not_straight` (bowed more than `BEAM_SAGITTA_MAX_SPACES` -- a slur or a
    tie), `one_stem` (nothing but one stem stands at either end of it -- a
    stroke that joins its own note and no other). A stroke with no
    `Q.BEAM_STROKE_INK` row, or whose reading left a test unread, is KEPT:
    the existing rules (`_beyond_own_stem`, the 2.38 ink join) judge it.

    ⚠️ ADDITIVE, NEVER SUBTRACTIVE OF THE RECORD, same discipline as
    `_not_a_ledger_line`: it only removes a stroke from THIS note's count,
    and where that leaves a stemmed head with no mark the caller applies the
    same rule-8 narrowing 2.25b's neighbour/arc discounts do.

    ⚠️ ONE STEM IS DECIDED FROM THE ENDS OF THE STROKE, NOT FROM THIS HEAD'S
    OWN: "joins this note's stem" is `_stem_joined` and the 2.38 ink join,
    read where they have always been read. This asks the other half -- is
    there ANOTHER note's stem -- of the stroke itself, so a beam read for a
    head whose own stem was never boxed is still judged.
    """
    ink = _beam_ink_rows(ev, cell)
    why: Dict[str, str] = {}          # stroke id -> why it is not a beam
    # ⚠️ ROADMAP 2.75, FIRST, AND WITHOUT AN INK ROW: a stroke lying through the
    # cell's own noteheads is those heads' ink (a row of heads fused by the CV
    # opening, a ledger line through them), and its thickness, straightness and
    # stems -- all read at the heads' end -- say nothing about a beam. It is
    # a connection to the heads the detector boxed, never a guess from shape.
    head_boxes = _notehead_glyph_boxes(
        ev, cell, tol / STEM_JOIN_TOLERANCE_SPACES if tol > 0 else 0.0)
    if head_boxes:
        for b in beams:
            box = _xywh(b)
            if box is not None and _covered_fraction(box, head_boxes) \
                    >= BEAM_THROUGH_HEADS_MIN:
                why[b.id] = "through_heads"
    if not ink and not why:
        return list(beams), {}, ()
    anchors = []                      # strokes that PASS all three, read
    for b in beams:
        if b.id in why:
            continue
        row = ink.get(b.id)
        if row is None:
            continue
        d = row.detail or {}
        ratio, sag = d.get("thickness_ratio"), d.get("sagitta_spaces")
        if ratio is not None and ratio < BEAM_THICKNESS_RATIO_MIN:
            why[b.id] = "too_thin"
        elif sag is not None and sag > BEAM_SAGITTA_MAX_SPACES:
            why[b.id] = "not_straight"
        else:
            n, read = _stems_a_stroke_stands_on(b, row, stems, tol)
            ends = d.get("end_stems") or []
            if read and not any(e.get("found") for e in ends) \
                    and _stems_ending_in(
                        _xywh(b), stems,
                        BEAM_STEMS_ENDING_SEPARATION_SPACES
                        * (tol / STEM_JOIN_TOLERANCE_SPACES)
                        ) < BEAM_STEMS_ENDING_MIN:
                # ⚠️ ROADMAP 2.75: the ink READ both ends and found a stem at
                # NEITHER. A beam stands on its stems; a stem merely NEAR the
                # box (which `_stems_a_stroke_stands_on` counts, permissively)
                # is not one at its end. A beamlet has one stem at one end.
                # Litolff p3 tile 9: a 243 x 32 px bar under a real beam (the
                # foot of an `f`), counted as a third level.
                # ⚠️ ROADMAP 2.77b (crop 8): ... UNLESS two or more read stems
                # END inside the stroke's own box -- the ink reader's end
                # window is a column probe and misses the stem of a SLOPED
                # beam; the CV stem rows are the second witness (a stem each
                # side of a beam). Such a stroke falls through to the tests
                # below like any other.
                why[b.id] = "no_stem_at_ends"
            elif read and n < 2:
                why[b.id] = "one_stem"
            elif read:
                anchors.append(b)
    # ⚠️ A BEAMLET IS A BEAM. The short secondary stroke of a dotted eighth and
    # a sixteenth hangs from ONE stem toward its neighbour and stops; Sean's
    # rule is about the BEAM of a group, and a stub that is part of that beam
    # stands on its stem and under (or over) the primary stroke that stands on
    # two. A one-stem stroke that lies within `BEAM_BEAMLET_GAP_SPACES` of a
    # stroke that PASSED, overlapping it in x, is that group's secondary level
    # and stays; one that stands alone (a slur's arc, a hairpin's line, the
    # next voice's) does not. `tol` is `STEM_JOIN_TOLERANCE_SPACES` spaces, so
    # a space is `tol / STEM_JOIN_TOLERANCE_SPACES`.
    space = tol / STEM_JOIN_TOLERANCE_SPACES if tol > 0 else 0.0
    for b in beams:
        if why.get(b.id) != "one_stem":
            continue
        box = _xywh(b)
        for a in anchors:
            ab = _xywh(a)
            if box is None or ab is None:
                continue
            x_overlap = min(box[0] + box[2], ab[0] + ab[2]) - max(box[0], ab[0])
            y_gap = max(box[1], ab[1]) - min(box[1] + box[3], ab[1] + ab[3])
            if x_overlap > 0 and y_gap <= BEAM_BEAMLET_GAP_SPACES * space:
                del why[b.id]
                break
    kept, dropped, used = [], {}, []
    for b in beams:
        if b.id in why:
            dropped[b.id] = why[b.id]
            if b.id in ink:
                used.append(ink[b.id])
        else:
            kept.append(b)
    return kept, dropped, tuple(used)


#: `wedge_box` (class 3, the hairpin) is NAMED, NOT BUILT -- ROADMAP 2.25b.
#: An exploratory pass priced it on real Brahms/Litolff gathers and eye-
#: checked crops before this decision was reverted: the `>= 2 stems`
#: override (borrowed from the arc class, below) did not reliably
#: separate a real down-stem beam from a hairpin's own ink, because
#: CLAUDE.md §10's own convention -- "a hairpin sits UNDER its staff" --
#: puts a hairpin in the SAME territory a down-stem's beam legitimately
#: occupies; 2 of 2 wedge-tagged crops looked like a real beam wrongly
#: discounted. A wrongly dropped beam WRITES A WRONG VALUE, which is worse
#: than the narrowing this class would have prevented, so it stays out of
#: `adjudicate_duration` (Sean, before merge). `Q.WEDGE_ANCHOR` also
#: cannot gate it -- it runs AFTER `duration` in `adjudicate.ORDER` -- so
#: there is no stronger fact to build this on without a bigger change.
#: `benchmarks/omr-missing-notes-2026-09/FINDINGS.md` SS13h.


#: `flag8thUp` -> 1 level, `flag16thDown` -> 2, and so on. DERIVED from
#: `rhythm._FLAG_DURATIONS` rather than restated, so the two cannot drift.
#:
#: ⚠️⚠️ A FLAG CLASS NAMES A VALUE, IT IS NOT A TALLY. `adjudicate_duration`
#: did `levels = len(flags)`, so a single `flag16thUp` -- one glyph, two
#: levels -- read as an EIGHTH. Counting glyphs is right for beam strokes,
#: which are drawn one per level, and wrong for flags, which are drawn as one
#: glyph however many hooks it has.
def _flag_levels_table() -> Dict[str, int]:
    from ...rhythm import _FLAG_DURATIONS
    out: Dict[str, int] = {}
    for name, (beats, _type) in _FLAG_DURATIONS.items():
        levels = 0
        v = 1.0
        while v > beats + 1e-9:
            v /= 2.0
            levels += 1
        out[name] = levels
    return out


_FLAG_LEVELS = _flag_levels_table()


def _flag_levels_for(value) -> Optional[int]:
    return _FLAG_LEVELS.get(str(value).lower())


#: The ROLE-half of a flag class: `flag8thUp` -> `up`, `flag16thDown` ->
#: `down`. ⚠️ THE SUFFIX AND NOTHING ELSE. The SHAPE-half -- how many hooks --
#: is `_FLAG_LEVELS`' business and is read there; these two functions read one
#: name for two different claims ON PURPOSE, which is the whole of ROADMAP
#: 2.12's methodology said in two lookups.
_FLAG_ROLE_SUFFIX = {"up": "up", "down": "down"}


def _flag_class_direction(value) -> Optional[str]:
    """Which way the DETECTOR says this flag's stem points -- one witness.

    ⚠️ IT IS A GUESS FROM A CROP AND IS TREATED AS ONE. A flag is drawn from
    the far end of a stem, so a reader with the stem in hand knows the
    direction and a reader with only the flag's own 40 px is inferring it from
    the hook's curl. `adjudicate_stem_direction` has the stem
    (`gather_cv_lines` reads 916 of them on a three-page record) and decides
    the same fact from it; this value exists so the two can DISAGREE on the
    record instead of one of them silently standing in for the other.
    """
    s = str(value).lower()
    for suffix, direction in _FLAG_ROLE_SUFFIX.items():
        if s.endswith(suffix):
            return direction
    return None


def _flag_direction(ev: Evidence, flags) -> Dict[str, Any]:
    """ROADMAP 2.12e — a flag's stem direction is the STEM's, not its name.

    ⚠️ THE FLAG IS STILL A FLAG WHATEVER WAY IT POINTS. Its SHAPE claim -- *a
    flag of N hooks stands on this stem* -- is what `_flag_levels_for` reads
    and what sets the duration, and it is untouched here. Only the ROLE-half
    is reassigned, and a disagreement never drops the flag: a detector that
    curled the hook the wrong way has still seen a flag.

    ⚠️ IT DECIDES NOTHING AND CHANGES NO DURATION, DELIBERATELY. Nothing on
    this path reads a flag's `Up`/`Down` suffix today -- the audit's row 9 is
    *"THE VALUE EXISTS AND NOTHING READS IT"* -- so the whole of this line is
    a CONNECT (CLAUDE.md §2 rule 6): it puts the comparison on the record,
    where none was, so a later stage can weigh it and so the disagreement rate
    can be measured at all. A rule that ACTED on the disagreement would be a
    new mechanism and needs its own roadmap item and its own print check.

    ⚠️ AND THE UNJOINABLE COUNT IS WHY THE LINE EXISTS. `source` says which of
    three things happened -- the stem answered, the stem ABSTAINED, or no
    `stem_direction` verdict reached this head at all -- because *no reader
    ran* and *the reader could not say* are the distinction the record exists
    for (CLAUDE.md §4b) and folding them would hide the join's real reach.
    """
    claims = [c for c in (_flag_class_direction(f.value) for f in flags)
              if c is not None]
    if not flags:
        return {}
    out: Dict[str, Any] = {"flag_class_says": sorted(set(claims)) or None}

    v = ev.verdict(Q.STEM_DIRECTION)
    if v is None:
        out["flag_direction"] = None
        out["flag_direction_source"] = "no_stem_direction_verdict"
        return out
    if v.outcome is not Outcome.DECIDED:
        out["flag_direction"] = None
        out["flag_direction_source"] = "stem_direction_" + v.outcome.value
        out["stem_direction_reason"] = v.reason
        return out

    stem_says = str(v.value)
    out["flag_direction"] = stem_says
    out["flag_direction_source"] = "stem_direction"
    # ⚠️ RECORDED, NEVER DROPPED. The flag keeps counting as a flag and the
    # detector's opinion keeps its place beside the stem's answer; what is
    # written down is that the two do not agree about this one piece of ink.
    if claims and any(c != stem_says for c in claims):
        out["detector_role_disagrees"] = True
    return out


def _attached_flags(ev: Evidence, cell, attached_stems, tol: float = 0.0):
    """The flags on THIS notehead's stem: (rows, levels).

    ⚠️⚠️ `Q.FLAG` IS GATHERED ON THE FLAG'S OWN GLYPH SUBJECT AND WAS READ ON
    THE NOTEHEAD'S, so not one of 134 rows on a three-page record ever reached
    a duration -- `beam_evidence == "flag"` fired ZERO times. `ev.rows(Q.FLAG)`
    asks the subject under adjudication, and a flag is a different detection
    with its own glyph index. The mark had to be ATTACHED and nothing attached
    it.

    ⚠️ THE ATTACHMENT IS THE STEM, AND HERE THAT IS STRICTLY BETTER THAN THE
    LEGACY RULE. `rhythm._flag_for_notehead` matches on x-centre proximity and
    says in its own docstring that it cannot enforce stem direction because
    "the notehead's stem direction isn't reliably available from a 0-stem
    detector". On this path the stems ARE available -- `gather_cv_lines`
    reads them -- so a flag is claimed only where it touches a stem that
    touches this head. A flag is drawn FROM the stem's far end, so the two
    boxes meet.

    Measured on the engraved Beethoven 5 iv fixture: m211 prints 100 eighths
    and 80 eighth rests, and every one of those eighths was read as a QUARTER
    -- four `quarter + 8th-rest` pairs summing to 6.0 in a 4/4 bar, on 20 of
    23 staves.

    ⚠️ ROADMAP 3.4g-4: A REFUSED FLAG IS SKIPPED BEFORE THE STEM TEST, not
    after. `Q.FLAG_IS_NOT_A_FLAG` is decided on the flag's own glyph subject
    (`f.subject`), the same one `Q.FLAG` is gathered on, so no join is needed
    -- unlike the key-signature marker, this family's quantity already names
    its glyph.
    """
    # ⚠️ NO `if not attached_stems: return` FAST PATH. One was written and a
    # mutation arm SURVIVED it -- `any()` over an empty list is already False,
    # so the early return was a second spelling of a rule that lives one line
    # below, and a rule a mutation cannot break is a protection that is not
    # there. Deleted rather than propped up with a test.
    boxes = _cell_boxes(ev, cell)
    out = []
    for f in ev.rows(Q.FLAG, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        refusal = ev.verdict(Q.FLAG_IS_NOT_A_FLAG, subject=f.subject)
        if refusal is not None and refusal.outcome is Outcome.DECIDED \
                and refusal.value is True:
            continue
        box_row = boxes.get(f.subject.to_key())
        box = _xywh_head(box_row.value) if box_row else None
        if box is None:
            continue
        # ⚠️ ROADMAP 2.18b: within `tol` (`STEM_JOIN_TOLERANCE_SPACES`), not
        # overlap. 13 of 134 detected flags on Breitkopf p1 stood 0.01-0.32
        # spaces off their stem and were never attached, so the note was
        # written a QUARTER with the flag's own box on the record.
        if any(_box_gap(_xywh(st), box) <= tol for st in attached_stems
               if _xywh(st)):
            out.append(f)
    # ⚠️ THE MAX, NOT THE SUM. Two flag detections on one stem are two
    # readings of one glyph, not two glyphs; a 16th flag alone already says
    # two levels.
    levels = 0
    for f in out:
        lv = _flag_levels_for(f.value)
        if lv:
            levels = max(levels, lv)
    return out, levels


def _in_augmentation_window(dot_box, head_box, max_above, max_below):
    """Does `dot_box` sit in `head_box`'s augmentation-dot window?

    ⚠️ PULLED OUT OF `_attached_dots`'S OWN LOOP, ROADMAP 2.12c, so
    `adjudicate_dot_role` can ask the identical per-candidate question
    without re-deriving it -- a second spelling of "is this box right of and
    level with that head" would be free to drift from the one this project
    already paid to measure. The three tests and their order are unchanged
    from the loop this replaced.
    """
    dot_x_left, _dot_y0, dot_w, dot_h = dot_box
    dot_y = _dot_y0 + dot_h / 2.0
    hx, hy0, hw, hh = head_box
    hx_right = hx + hw
    if hx_right > dot_x_left:
        return False                          # the note must be to the LEFT
    hy = hy0 + hh / 2.0
    above = hy - dot_y                        # positive: the dot sits HIGHER
    if above > max_above or above < -max_below:
        return False
    dx = dot_x_left - hx_right
    if dx > max(dot_w, 12) * 5:
        return False
    return True


#: A staccato sits ABOVE or BELOW its head, centred on the head's x -- the
#: mirror shape of the augmentation-dot window above. ROADMAP 2.12c.
#:
#: ⚠️ MEASURED, PER CLAUDE.md RULE 5/"measure before fixing any cut, and cut
#: in the gap": `benchmarks/omr-shape-role-2026-09/probe/dot_role_offsets.py`
#: over every `augmentationDot` and `articStaccato*` box on the three
#: acceptance records, offset from its NEAREST notehead centre, in staff
#: spaces. The Breitkopf record (6,816 dots, 2,818 staccati -- the larger,
#: cleaner population; Litolff's MERGING plate agrees qualitatively and is
#: noisier) shows two separated clusters:
#:   * augmentation dots: dx +1.00..+1.75 (peak 1.25-1.50, 5,049 of 6,816 --
#:     a notehead is ~1.3 staff spaces wide, so a dot just past its right
#:     edge lands there) and dy in [-0.25, +0.75] -- an INDEPENDENT
#:     confirmation of `DOT_ABOVE_NOTE_MAX_SPACES` / `DOT_BELOW_NOTE_MAX_SPACES`
#:     above, measured from the opposite side;
#:   * staccati: dx in [-0.25, +0.25] (2,378 of 2,818) and |dy| with a VALLEY
#:     at [0.50, 0.75) -- 19 of 2,818 -- then a ramp to a peak at
#:     [1.00, 1.25) -- 970. The cut below is taken in that valley.
#: CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: Sean has not
#: adjudicated a print crop of this family; ask before trusting a borderline
#: case, and see `benchmarks/omr-shape-role-2026-09/FINDINGS.md` Sec.2.12c.
STACCATO_CENTRED_MAX_SPACES = 0.5
#: ROADMAP 2.59: widest gap, head edge to dot, at which a dot may follow a note
#: owned by ANOTHER staff (`OMR_DOT_FOLLOWS_NOTE`).
FOREIGN_DOT_MAX_GAP_SPACES = 0.75
STACCATO_OFFSET_MIN_SPACES = 0.75


def _in_staccato_window(dot_box, head_box, space,
                        centred_max_spaces=STACCATO_CENTRED_MAX_SPACES,
                        offset_min_spaces=STACCATO_OFFSET_MIN_SPACES):
    """Does `dot_box` sit in `head_box`'s staccato window -- centred on its
    x, at least `offset_min_spaces` staff spaces above or below it?"""
    if not space:
        return False
    dx0, dy0, dw, dh = dot_box
    hx, hy0, hw, hh = head_box
    dot_cx, dot_cy = dx0 + dw / 2.0, dy0 + dh / 2.0
    head_cx, head_cy = hx + hw / 2.0, hy0 + hh / 2.0
    if abs(dot_cx - head_cx) > centred_max_spaces * space:
        return False
    if abs(head_cy - dot_cy) < offset_min_spaces * space:
        return False
    return True


#: ROADMAP 2.59 follow-up (lane-staccato-unread, Sean 2026-10-07, Litolff
#: `12/1/6/2/9`: "not sure why it can't see that the first cell is a staccato
#: note"). THE TEST, stated before any count: a staccato's note is read from
#: EVERY real head on the page, not only the heads this staff's strip owns --
#: a note is often filed in (or owned by) the staff just below/above the strip
#: that boxed its staccato dot, exactly like an augmentation dot's (2.59).
#: Window and offset are the home window's own (`STACCATO_CENTRED_MAX_SPACES`,
#: `STACCATO_OFFSET_MIN_SPACES`), plus a REACH the home window never had: the
#: dot lies no farther than `STACCATO_MAX_GAP_SPACES` from the head's nearest
#: edge (= `ownership.DOT_STACK_MAX_SPACES`, the reader's own stacked test).
#: It answers STACCATO ONLY -- a mark above/below a head is never lengthening.
STACCATO_MAX_GAP_SPACES = 2.0


def _foreign_staccato_owner(dot_box, foreign_targets, space):
    """The nearest head, of ANY other staff's strip or owner, whose staccato
    window holds `dot_box` and that is within `STACCATO_MAX_GAP_SPACES` of
    it. -> its key, or None (never a guess: no head in the window abstains)."""
    best, best_dist = None, float("inf")
    dcx = dot_box[0] + dot_box[2] / 2.0
    dcy = dot_box[1] + dot_box[3] / 2.0
    for key, hb in foreign_targets:
        if not _in_staccato_window(dot_box, hb, space):
            continue
        hcy = hb[1] + hb[3] / 2.0
        if abs(hcy - dcy) - hb[3] / 2.0 > STACCATO_MAX_GAP_SPACES * space:
            continue
        dist = (hb[0] + hb[2] / 2.0 - dcx) ** 2 + (hcy - dcy) ** 2
        if dist < best_dist:
            best_dist, best = dist, key
    return best


def _refused_as_a_notehead(ev: Evidence, subject) -> bool:
    v = ev.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, subject=subject)
    return (v is not None and v.outcome is Outcome.DECIDED
            and v.value is True)


def _dot_page_context(ev: Evidence, cell, dot_box_row, dot_box, space, boxes):
    """ROADMAP 2.59 round 2 (`OMR_DOT_FOLLOWS_NOTE`): the dot against the PAGE.

    -> None where the dot has no page box (DECLINED, not defaulted), else
    `{"on_a_barline", "stacked", "neighbour_heads"}`. `stacked` is
    `ownership.dot_stacked_under_a_note` over every NON-REFUSED notehead of
    this cell and of the cells of the staves just above and below it in the
    same bar -- the padded cell reaches into them, and a staccato's note is
    often the neighbour's. `neighbour_heads` are those neighbours' heads in
    THIS dot's canonical frame, for the foreign augmentation window.
    """
    pb = (dot_box_row.detail or {}).get("bbox_page_px")
    if not pb or len(pb) != 4 or not dot_box[2]:
        return None
    k = (pb[2] - pb[0]) / float(dot_box[2])        # page px per canonical px
    if k <= 0:
        return None
    sp_page = space * k
    cell_rows = ev.rows(Q.CELL_BOX, scope=Scope.SELF_AND_ANCESTORS,
                        subject=cell)
    cell_page = (list(cell_rows[-1].value)
                 if cell_rows and len(cell_rows[-1].value) == 4 else None)
    notes_page, neighbour = [], []
    cells = [(cell, boxes, False)]
    for ds in (-1, 1):
        if cell.staff + ds < 0:
            continue
        nc = Subject(Kind.CELL, page=cell.page, system=cell.system,
                     staff=cell.staff + ds, cell=cell.cell)
        cells.append((nc, _cell_boxes(ev, nc), True))
    for c, cb, is_nb in cells:
        for r in ev.rows(Q.NOTEHEAD_CLASS, scope=Scope.SELF_AND_DESCENDANTS,
                         subject=c):
            if _refused_as_a_notehead(ev, r.subject):
                continue
            row_ = cb.get(r.subject.to_key())
            hp = (row_.detail or {}).get("bbox_page_px") if row_ else None
            if not hp or len(hp) != 4:
                continue
            notes_page.append(tuple(hp))
            if is_nb:
                neighbour.append((r.subject.to_key(), (
                    dot_box[0] + (hp[0] - pb[0]) / k,
                    dot_box[1] + (hp[1] - pb[1]) / k,
                    (hp[2] - hp[0]) / k, (hp[3] - hp[1]) / k)))
    return {"on_a_barline": _own.mark_on_a_barline(pb, cell_page, sp_page),
            "stacked": _own.dot_stacked_under_a_note(pb, notes_page, sp_page),
            "neighbour_heads": neighbour}


def _attached_dots(ev: Evidence, cell, head_box, space):
    """The augmentation dots belonging to THIS notehead.

    ⚠️ `Q.AUG_DOT` had the same fault as `Q.FLAG` -- 157 rows on a three-page
    record, ZERO durations carrying a dot -- and the two constants written for
    exactly this decision, `DOT_ABOVE_NOTE_MAX_SPACES` and
    `DOT_BELOW_NOTE_MAX_SPACES`, sat here with a paragraph of measured
    justification and were **used by nothing in this module**.

    ⚠️ THE GEOMETRY IS THE PAID-FOR ONE, in its own units. A dot is printed to
    the RIGHT of its note, and NOT at its note's height: a note in a space
    takes its dot in the same space, a note ON A LINE takes it in the space
    ABOVE. Over 116 dots the signed offsets are bimodal -- 52 at 0.00 spaces,
    52 at +0.50, nothing between +0.57 and +3.75 -- so the window is
    asymmetric, and the asymmetry is what decides a double stop, where the
    lower dot is equidistant from both noteheads and a symmetric window ties.

    ⚠️ AND THE CLAIM IS RECIPROCAL, WHICH IS WHAT MAKES A PER-GLYPH DECISION
    SAFE. The legacy rule assigns each dot to its own nearest target, globally;
    this decision sees one notehead. So a dot is claimed only where THIS head
    is the best target the dot has in the cell -- the same assignment, asked
    from the other end, so two heads can never both take one dot.

    ⚠️⚠️ THE POOL IS EVENTS, NOT NOTEHEADS -- `Q.NOTEHEAD_CLASS` *AND*
    `Q.REST` -- AND IT HAS TO BE, TWICE OVER. `_pair_dots_to_targets` builds
    exactly this pool (`dot_targets = noteheads + rests`, "dots after rests
    are rarer but real") under the same two constants, so a rest reading no
    dot here was a divergence from the paid-for rule and not a narrower
    reading of it. And the reciprocity above is only sound over the WHOLE
    pool: scored against noteheads alone, a dot printed after a rest is
    awarded to some notehead further off, because the rule asks which target
    is best among those it can see. Widening the pool can therefore TAKE a
    dot from a notehead, which is the rule working, not a regression.

    ⚠️ ROADMAP 2.12c. `Q.AUG_DOT` now also holds every `articStaccato*` box
    (tagged `detail.detector_role`), because the class only guesses the role
    and this decision must not. Each row is admitted here ONLY where
    `adjudicate_dot_role` DECIDED it augmentation -- a staccato-positioned
    row is excluded whatever class the detector gave it, and a dot-classed
    row that `adjudicate_dot_role` could not place (or placed as a
    staccato) is excluded the same way. That decision runs the identical
    `_in_augmentation_window` test this function always ran, so no
    previously-dotted note stops being dotted; it only adds the reciprocal
    of the 2.12c gate -- a staccato-classed box sitting where a dot sits now
    reaches this pool too.
    """
    if head_box is None or not space:
        return []
    boxes = _cell_boxes(ev, cell)
    # ⚠️ ROADMAP 2.27c, the SAME shape 2.27 fixed for articulation/fermata/
    # ornament owners: `cell`'s own `Q.NOTEHEAD_CLASS`/`Q.REST` rows can hold
    # a head that is really the NEIGHBOUR staff's, filed here only because
    # the padded cell's crop reached into its ink. A candidate `glyph_owner`
    # has already DECIDED belongs elsewhere is dropped before it can win the
    # dot -- except `mine`'s OWN row, which is never dropped for THIS test:
    # `mine` may itself be such a ghost (duration is read for every note
    # regardless of ownership, per the 2.27 map's own note that EXPORT, not
    # this decision, is where a ghost is finally held out), and dropping it
    # here would silently take away its ability to claim its own dot.
    mine_key = ev.subject.to_key()
    home = cell.at(Kind.STAFF).to_key()
    heads = []
    # ⚠️ OMR_DOT_FOLLOWS_NOTE (lane-dot-not-a-note, Sean 2026-10-07): a dot
    # belongs to the note immediately to its LEFT, whichever staff owns that
    # note. A head owned by another staff is therefore kept in the pool, but
    # flagged: it may take a dot ONLY when `adjudicate_dot_role` named it as
    # that dot's note (checked per dot below), so a ghost can still never
    # steal a dot from a home head (the 2.27c fault) and a distant ghost can
    # never turn a staccato into an augmentation.
    keep_foreign = _own.dot_follows_note_enabled()
    foreign_keys = set()
    for q in (Q.NOTEHEAD_CLASS, Q.REST):
        for r in ev.rows(q, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
            foreign = (r.subject.to_key() != mine_key
                       and _own._owned_by_a_different_staff(ev, r, home))
            if foreign and not keep_foreign:
                continue
            box_row = boxes.get(r.subject.to_key())
            b = _xywh_head(box_row.value) if box_row else None
            if b is not None:
                heads.append((r.subject.to_key(), b))
                if foreign:
                    foreign_keys.add(r.subject.to_key())
    mine = None
    for key, b in heads:
        if b == head_box and key == ev.subject.to_key():
            mine = key
    if mine is None:
        mine = ev.subject.to_key()

    max_above = max(1.0, space * DOT_ABOVE_NOTE_MAX_SPACES)
    max_below = max(1.0, space * DOT_BELOW_NOTE_MAX_SPACES)
    out = []
    for d in ev.rows(Q.AUG_DOT, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        role = ev.verdict(Q.DOT_ROLE, subject=d.subject)
        if (role is None or role.outcome is not Outcome.DECIDED
                or role.value != "augmentation"):
            continue
        box_row = boxes.get(d.subject.to_key())
        db = _xywh_head(box_row.value) if box_row else None
        if db is None:
            continue
        dot_x_left = db[0]
        dot_y = db[1] + db[3] / 2.0
        best, best_score = None, float("inf")
        named = ((role.detail or {}).get("head")
                 if foreign_keys else None)
        for key, hb in heads:
            if key in foreign_keys and key != named:
                continue
            if not _in_augmentation_window(db, hb, max_above, max_below):
                continue
            hx_right = hb[0] + hb[2]
            hy = hb[1] + hb[3] / 2.0
            dx = dot_x_left - hx_right
            score = dx + abs(hy - dot_y) * 2
            if score < best_score:
                best_score, best = score, key
        if best == mine:
            out.append(d)
    return out


#: A dot box whose ink is at least this share elongated stroke is not a dot
#: (Sean 2026-10-09: "mostly overlap"). Real dots read 0.0 on Brahms p1.
DOT_ON_STROKE_MIN = 0.5


@decision(
    quantity=Q.DOT_ROLE,
    checkable=Checkable.UNCHECKABLE,
    # ⚠️ ROADMAP 2.27c ADDS `Q.GLYPH_OWNER`: a candidate notehead/rest already
    # DECIDED to belong to another staff must not win this dot. `Q.GLYPH_
    # OWNER` is decided well before `Q.DOT_ROLE` in `adjudicate.ORDER`
    # (beside `Q.ARC_OWNER`, long before the rhythm block), so this reads a
    # settled verdict, never a hole -- `test_staged_dot_role.py`'s
    # `TestGlyphOwnerPrecedesDotRoleInORDER` asserts the order directly.
    composed_from=(Q.AUG_DOT, Q.GLYPH_BOX, Q.NOTEHEAD_CLASS, Q.REST,
                   Q.CELL_STAFF_SPACE, Q.GLYPH_OWNER, Q.CELL_BOX,
                   Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.DOT_STROKE_INK),
    scope=Kind.GLYPH,
    wants=(Q.AUG_DOT, Q.GLYPH_BOX, Q.NOTEHEAD_CLASS, Q.REST,
           Q.CELL_STAFF_SPACE, Q.GLYPH_OWNER, Q.CELL_BOX,
           Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.DOT_STROKE_INK),
    reasons=("right_of_and_level_with_a_head", "centred_and_offset_from_a_head",
             "no_glyph_box", "no_cell_staff_space",
             "no_notehead_or_rest_in_cell", "dot_role_ambiguous",
             "owned_by_another_staff", "on_a_barline", "on_a_stroke"),
    mode=Mode.ADDITIVE,
    subjects_from=Q.AUG_DOT,
)
def adjudicate_dot_role(ev: Evidence) -> Ruling:
    """A small filled dot's ROLE -- does it lengthen the note (augmentation)
    or mark it short (staccato) -- ROADMAP 2.12c.

    CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (CLAUDE.md
    Sec.2 rule 3 -- ask first, and nobody has been asked yet): an
    augmentation dot sits to the RIGHT of its notehead and level with it (a
    space higher on a line note); a staccato sits directly ABOVE or BELOW,
    centred on the head's x, on the side opposite the stem. It would be
    falsified by a Sean-adjudicated print crop reading a decided role the
    other way; none has been adjudicated yet
    (`benchmarks/omr-shape-role-2026-09/FINDINGS.md` Sec.2.12c).

    DECISIONS 2026-09-23 "SHAPE FROM THE CLASS, ROLE FROM THE GEOMETRY":
    `Q.AUG_DOT` pools two detector classes now (`augmentationDot` and
    `articStaccato*`, `detail.detector_role` remembers which) because both
    name the SAME shape -- one small filled dot -- and the class is only a
    guess about which role it plays. This is the decision that reads the
    role from the ink's POSITION instead. `_attached_dots` (the
    augmentation window's own owner, this file, above) reads this verdict
    back rather than re-deriving the same test twice; `export.py` reads it
    to route a staccato-role mark to the file, since `gather_glyph_families`
    no longer files these classes into `Q.ARTICULATION_MARK` at all.

    The augmentation window is tried FIRST, against every notehead OR rest
    in the cell -- the identical pool `_attached_dots` scores against, and
    for the identical reason: a dot after a rest is rarer but real. Only
    where NOTHING in that pool admits it is the staccato window tried,
    against noteheads alone (a staccato marks a NOTE, never a rest), taking
    the nearest qualifying head as the mark's owner. Neither window fitting
    is an ABSTENTION and never a default: CLAUDE.md rule 8, "a fallback
    never converts cannot-tell into an answer".
    """
    rows = ev.rows(Q.AUG_DOT)
    if not rows:
        return Ruling.abstain("no_notehead_or_rest_in_cell")
    row = rows[-1]
    v = row.value
    if not (isinstance(v, (list, tuple)) and len(v) >= 2):
        return Ruling.abstain("dot_role_ambiguous")

    box_rows = ev.rows(Q.GLYPH_BOX)
    dot_box = _xywh_head(box_rows[-1].value) if box_rows else None
    if dot_box is None:
        return Ruling.abstain("no_glyph_box")

    # ⚠️⚠️ ROADMAP 2.69 FOLLOW-UP (Sean, 2026-10-09, DECISIONS): *"a dot can
    # not fully or mostly overlap a flag but it can touch it"*. A box whose
    # own ink mostly lies on an elongated stroke (the curled tip of a flag,
    # a stem, a beam) is part of that mark and never a lengthening dot --
    # overlap, not contact, is the test, so a round dot touching a flag
    # (`Q.DOT_STROKE_INK` near 0) is untouched. ABSTAINS, never defaults: the
    # box is not a dot, and nothing here says what it is.
    stroke = ev.rows(Q.DOT_STROKE_INK)
    if stroke and isinstance(stroke[-1].value, (int, float)) \
            and float(stroke[-1].value) >= DOT_ON_STROKE_MIN:
        return Ruling(value=None, reason="on_a_stroke",
                      used=(stroke[-1].id,),
                      detail={"dot_stroke_fraction": float(stroke[-1].value),
                              "detector_class": (row.detail or {}).get(
                                  "detector_class")})

    cell = ev.subject.at(Kind.CELL)
    space_row = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS,
                        subject=cell)
    space = float(space_row[-1].value) if space_row else None
    if not space:
        return Ruling.abstain("no_cell_staff_space")

    boxes = _cell_boxes(ev, cell)
    keep_foreign = _own.dot_follows_note_enabled()
    ctx = None
    if keep_foreign:
        ctx = _dot_page_context(ev, cell, box_rows[-1], dot_box, space, boxes)
        if ctx is not None and ctx["on_a_barline"]:
            return Ruling.abstain("on_a_barline", **{
                "detector_class": (row.detail or {}).get("detector_class")})
    # ⚠️ ROADMAP 2.27c: the dot itself has no staff of its own to defend (it
    # is `ev.subject`, not a candidate), so unlike `_attached_dots` above
    # there is no self-reference to protect -- every candidate that
    # `glyph_owner` has already DECIDED belongs to another staff is simply
    # excluded, the same filter 2.27 built for articulation/fermata/ornament
    # owners.
    home = cell.at(Kind.STAFF).to_key()
    all_targets = []                    # heads AND rests, for the aug window
    note_targets = []                   # noteheads only, for the staccato one
    n_raw = n_excluded = 0
    foreign_targets = []                # (key, box): owned by another staff
    refused_targets = []                # (key, box): refused as a notehead
    all_keys = []                       # parallel to all_targets
    for q in (Q.NOTEHEAD_CLASS, Q.REST):
        for r in ev.rows(q, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
            n_raw += 1
            box_row = boxes.get(r.subject.to_key())
            if keep_foreign and q == Q.NOTEHEAD_CLASS \
                    and _refused_as_a_notehead(ev, r.subject):
                # a refused fragment is not a note: it is the LAST resort for
                # a dot, after every real note (Brahms `16/1/10/4/3`)
                rb_ = _xywh_head(box_row.value) if box_row else None
                if rb_ is not None:
                    refused_targets.append((r.subject.to_key(), rb_))
                continue
            b = _xywh_head(box_row.value) if box_row else None
            if _own._owned_by_a_different_staff(ev, r, home):
                n_excluded += 1
                if b is not None:
                    foreign_targets.append((r.subject.to_key(), b))
                continue
            if b is None:
                continue
            all_targets.append(b)
            all_keys.append(r.subject.to_key())
            if q == Q.NOTEHEAD_CLASS:
                note_targets.append((r.subject.to_key(), b))
    if keep_foreign and ctx is not None:
        foreign_targets += ctx["neighbour_heads"]
    if not all_targets and not (keep_foreign and (foreign_targets
                                                  or refused_targets)):
        # ⚠️ Apart from a genuinely empty cell, so a stray dot with nothing
        # of its own to attach to can be told from one whose only candidates
        # were the neighbour's ink.
        if n_excluded and n_excluded == n_raw:
            return Ruling.abstain("owned_by_another_staff", n_candidates=n_raw)
        return Ruling.abstain("no_notehead_or_rest_in_cell")

    used = (row.id, box_rows[-1].id) + ((space_row[-1].id,) if space_row
                                        else ())
    detail = {"detector_role": (row.detail or {}).get("detector_role"),
              "detector_class": (row.detail or {}).get("detector_class")}

    max_above = max(1.0, space * DOT_ABOVE_NOTE_MAX_SPACES)
    max_below = max(1.0, space * DOT_BELOW_NOTE_MAX_SPACES)
    home_best, home_score = None, float("inf")
    stacked = bool(keep_foreign and ctx is not None and ctx["stacked"])
    for key, hb in ([] if stacked else zip(all_keys, all_targets)):
        if _in_augmentation_window(dot_box, hb, max_above, max_below):
            if not keep_foreign:
                return Ruling(value="augmentation",
                              reason="right_of_and_level_with_a_head",
                              used=used, detail=detail)
            sc = (dot_box[0] - (hb[0] + hb[2])
                  + abs(hb[1] + hb[3] / 2.0
                        - (dot_box[1] + dot_box[3] / 2.0)) * 2)
            if sc < home_score:
                home_score, home_best = sc, key
    if home_best is not None:
        # same best-head score `_attached_dots` uses; names the note so the
        # dot's owner can follow it (`ownership.reconcile_dot_owners`)
        return Ruling(value="augmentation",
                      reason="right_of_and_level_with_a_head",
                      used=used, detail={**detail, "head": home_best})

    dot_cx = dot_box[0] + dot_box[2] / 2.0
    dot_cy = dot_box[1] + dot_box[3] / 2.0
    best_owner, best_dist = None, float("inf")
    for key, hb in note_targets:
        if not _in_staccato_window(dot_box, hb, space):
            continue
        hx, hy0, hw, hh = hb
        dist = ((hx + hw / 2.0 - dot_cx) ** 2
                + (hy0 + hh / 2.0 - dot_cy) ** 2)
        if dist < best_dist:
            best_dist, best_owner = dist, key
    if best_owner is not None:
        return Ruling(value="staccato",
                      reason="centred_and_offset_from_a_head", used=used,
                      detail={**detail, "owner": best_owner,
                              "articulation": "staccato"})

    if keep_foreign:
        # ⚠️ lane-staccato-unread: nothing of THIS staff's holds the dot, but a
        # note filed in (or owned by) the next strip does -- the dot is its
        # staccato. Tried BEFORE the foreign augmentation below so a mark
        # standing over a note's column can never become lengthening.
        fowner = _foreign_staccato_owner(dot_box, foreign_targets, space)
        if fowner is not None:
            return Ruling(value="staccato",
                          reason="centred_and_offset_from_a_head", used=used,
                          detail={**detail, "owner": fowner,
                                  "articulation": "staccato",
                                  "head_owned_elsewhere": True})
    if keep_foreign:
        # ⚠️ LAST, and only where nothing of THIS staff's fits either window:
        # the dot trails the note immediately to its left even though another
        # staff owns that note (Brahms `18/1/12/6/18`, `5/0/1/5/32`). Tried
        # after the staccato window so a distant neighbour's note can never
        # turn a staccato into an augmentation (measured: 8 of 14 Litolff
        # role changes were exactly that when it came first).
        dot_x_left, dot_y = dot_box[0], dot_box[1] + dot_box[3] / 2.0
        best, best_score = None, float("inf")
        for key, hb in ([] if stacked else foreign_targets):
            if not _in_augmentation_window(dot_box, hb, max_above, max_below):
                continue
            # a dot sits right beside its note: the gap from the head's right
            # edge, in staff spaces, is capped far tighter than the window's
            # own 5-dot-widths (measured in the three crops this rule was cut
            # from: 0.2-0.3 sp for the real ones, 1.1+ sp for the two that
            # were another note's staccato)
            if dot_x_left - (hb[0] + hb[2]) > FOREIGN_DOT_MAX_GAP_SPACES * space:
                continue
            score = (dot_x_left - (hb[0] + hb[2])
                     + abs(hb[1] + hb[3] / 2.0 - dot_y) * 2)
            if score < best_score:
                best_score, best = score, key
        if best is not None:
            return Ruling(value="augmentation",
                          reason="right_of_and_level_with_a_head",
                          used=used, detail={**detail, "head": best,
                                             "head_owned_elsewhere": True})
    if keep_foreign and not stacked:
        # LAST: no real note takes the dot, so the refused fragment the old
        # reading used still does (it is where the note's ink is) -- never
        # converting "cannot tell" into more than the old reading said.
        dot_x_left, dot_y = dot_box[0], dot_box[1] + dot_box[3] / 2.0
        best, best_score = None, float("inf")
        for key, hb in refused_targets:
            if not _in_augmentation_window(dot_box, hb, max_above, max_below):
                continue
            score = (dot_x_left - (hb[0] + hb[2])
                     + abs(hb[1] + hb[3] / 2.0 - dot_y) * 2)
            if score < best_score:
                best_score, best = score, key
        if best is not None:
            return Ruling(value="augmentation",
                          reason="right_of_and_level_with_a_head",
                          used=used, detail={**detail, "head": best,
                                             "head_refused": True})
    return Ruling.abstain("dot_role_ambiguous", **detail)


def _beam_levels(beams, x_center, width, joined=(), join_witness=None,
                 stem_x=None):
    """How many strokes cover this notehead's column: (CERTAIN, POSSIBLE).

    ⚠️ THE LEVEL IS AN INTERPRETATION OVER STROKES, WHICH IS WHY IT IS
    COMPUTED HERE AND NOT IN GATHER.

    ⚠️⚠️ AND IT RETURNS A RANGE, NOT A NUMBER, BECAUSE THE READING IS A RANGE.
    The first version returned an int, and that reproduced
    `pitch_resolver.py:181` ONE LAYER UP: `pos_float` is computed and rounded
    away there, and a level "two, possibly three" was collapsed at the moment
    of counting here. **Keeping the measurement is not sufficient** -- the
    strokes were on the record and intact -- if the INTERPRETATION collapses at
    the first opportunity.

    ⚠️ ROADMAP 2.38: `join_witness` (`{stroke id: True/False/None}`, from
    `_beam_join_witness`) is consulted for a stroke this test would
    otherwise count as merely POSSIBLE (the padded column match). Where the
    ink-continuity reader says the stem's own ink DOES run into this
    stroke, it is promoted to CERTAIN; where it says it does NOT, the
    stroke is dropped from the count entirely (neither certain nor
    possible -- rule 8's "count the level"/"drop it", never a silent
    guess); where the reader never reached it (`None`), the stroke stays
    exactly as box geometry alone would have called it, and the note stays
    narrowed -- the same "declined never defaults" rule 8 states for every
    other ink witness in this module.

    ⚠️⚠️ ROADMAP 2.38b: A CERTAIN stroke (exact column overlap, or already
    stem-joined by box) is NEVER dropped for a NOT-JOINED ink reading --
    that was measured and refused (Brahms p1 print check: `duration`
    verdicts DECIDED using only a NOT-JOINED witness read the wrong level
    ~50 of 165 times, because dropping a CERTAIN stroke silently promoted
    a WRONG box-only count -- some certain attributions were already wrong
    before this lane existed, box overlap with a stroke that is not this
    stem's, and only stayed NARROWED before because an extra, now-correctly
    -dropped POSSIBLE stroke kept `possible > certain`). A certain stroke
    the ink reads NOT JOINED is instead returned in `certain_conflicts` --
    a DISAGREEMENT between two witnesses, which `adjudicate_duration`
    turns into a NARROW (`beam_certain_not_joined`), never a silent count
    change here. JOINED or declined (`None`) leaves a certain stroke
    exactly as before -- unaffected, the positive control this rule must
    never move.

    ⚠️⚠️ ROADMAP 2.43: `stem_x`, THIS HEAD'S OWN STEM'S PADDED X-SPAN
    (`_own_stem_x_span`), GATES THE PADDED-COLUMN "POSSIBLE" BRANCH.
    Before this, the branch asked only *is this stroke within one
    notehead-width of the HEAD's own centre* -- nothing about the STEM, so
    a YOLO `beam` box standing nowhere near this note's stem (a hairpin, a
    slur, a neighbour's mark the earlier discount tiers did not name, or
    plain noise) still counted as POSSIBLE whenever it happened to fall
    within that width, `join_witness` or no `join_witness` -- a stroke the
    ink reader itself could only mark `declined`/never-reached stayed a
    witness for THIS note regardless. [C12]/2.18's own words: *"a note's
    beams stand on the side its stem points to"* -- by the same logic they
    stand at its STEM's column, not merely near its head. DECISIONS
    2026-09-30 (Sean), on the stage readout: 28 hollow + 21 black Litolff
    p3 heads narrowed this exact way, every one `cv_beams: 0`,
    `beams_by_stem: 0`, `beam_evidence: none_over_this_note` -- the stray
    box was never joined, never even ink-witnessed, and stood over no read
    stem of this note's, yet still made the length undecided. Where this
    head has no own stem (`stem_x is None`), the test is unchanged -- 2.18's
    own "no side -> every stroke stays" rule extended once more: there is
    no stem column to ask the question of.
    """
    joined_ids = {b.id for b in joined}
    if x_center is None:
        # ⚠️ No box means no head to attach a stem to either, so `joined` is
        # empty here by construction -- it is read rather than assumed zero so
        # the two callers cannot drift apart.
        return (len(joined_ids), len(joined_ids), ())
    pad = (width or 0.0) * BEAM_EDGE_TOLERANCE_WIDTHS
    certain = possible = 0
    certain_conflicts = []
    for b in beams:
        x0 = b.detail.get("x0", 0)
        x1 = b.detail.get("x1", 0)
        if b.id in joined_ids or x0 <= x_center <= x1:
            certain += 1
            possible += 1
            if (join_witness or {}).get(b.id) is False:
                certain_conflicts.append(b.id)
        elif x0 - pad <= x_center <= x1 + pad:
            # ⚠️ YOLO-SOURCED STROKES ONLY. A CV stroke (`READERS.CV_LINES`)
            # is real ink continuity the raster itself shows near this
            # head -- a beamlet ending short of this note's own stem (a
            # genuine secondary-beam shape, `TestANeighbourStaffsBeamThrough
            # ThePad`'s and 2.38's own sibling tests) is real evidence this
            # column test already exists to hold as a genuine MAYBE, and
            # this gate must not drop it. A YOLO `beam` DETECTION with no CV
            # counterpart, past `_kept_beams`'s own dedup, is the population
            # DECISIONS 2026-09-30 actually names -- a box the detector drew
            # that stands nowhere near this note's stem at all.
            if (stem_x is not None and b.reader == READERS.DETECTOR
                    and not (x0 <= stem_x[1] and x1 >= stem_x[0])):
                # Not over THIS note's own stem column -- not a witness for
                # this note, whatever else it is.
                continue
            witness = (join_witness or {}).get(b.id)
            if witness is True:
                certain += 1
                possible += 1
            elif witness is False:
                continue
            else:
                possible += 1
    return (certain, possible, tuple(certain_conflicts))


def _beam_join_witness(ev: Evidence, cell, kept, own_stems, side
                       ) -> Tuple[Dict[str, Optional[bool]], tuple]:
    """`({stroke id: True/False/None}, the rows read)`. ROADMAP 2.38.

    For every candidate stroke in `kept`, does THIS head's OWN stem's ink
    run continuously into it at the tip, per `Q.BEAM_STEM_JOIN`? `None` --
    no evidence either way -- where this head has no own stem direction, no
    own stem, or the quantity never reached the matching (stem, stroke,
    end) triple.

    ⚠️ ONLY THE END THIS HEAD'S OWN STEM POINTS TO, same reason
    `_stem_tip_flag_ink` (2.18c) gives: GATHER files a row for both a
    stem's top and its bottom because it does not know the true tip;
    reading the wrong end asks the question of the wrong physical
    junction.

    ⚠️ MULTIPLE OWN STEMS (a chord sharing one physical stem should not
    produce more than one `Q.STEM` row, but nothing enforces that upstream)
    are folded with `any()`: if ink shows a join from ANY of this head's own
    stems to a stroke, that stroke counts as joined for this head. A
    disagreement between two of this head's own stems is not a case this
    lane's own two documents present, and folding rather than refusing
    keeps the common one-stem case simple; a future disagreement would be
    silently resolved in the JOINED direction, which is the more permissive
    reading, not the more cautious one -- named here rather than hidden.
    """
    if side not in ("up", "down") or not own_stems or not kept:
        return {}, ()
    end = "top" if side == "up" else "bottom"
    stem_ids = {s.id for s in own_stems}
    rows = ev.rows(Q.BEAM_STEM_JOIN, scope=Scope.SELF_AND_ANCESTORS,
                   subject=cell)
    by_stroke: Dict[str, list] = {}
    for r in rows:
        if r.detail.get("end") != end:
            continue
        if r.detail.get("stem_row_id") not in stem_ids:
            continue
        by_stroke.setdefault(r.detail.get("beam_row_id"), []).append(r)
    witness: Dict[str, Optional[bool]] = {}
    used: list = []
    for b in kept:
        matched = by_stroke.get(b.id)
        if not matched:
            witness[b.id] = None
            continue
        witness[b.id] = any(bool(m.value) for m in matched)
        used.extend(matched)
    return witness, tuple(used)


#: The shortest run of ink (staff spaces) beside a head the ruler's direction is
#: believed for. ROADMAP 2.77b. It is the CV stem finder's own floor
#: (`line_detection.detect_stems`, `min_height_lines=2.0`: nothing shorter is a
#: stem anywhere in the pipeline), and it is MEASURED: over the 366 heads of
#: Litolff p0-3 and Brahms p0-1 whose own CV stem decided a direction
#: (`stem_projection`) and whose ruler read up or down, the ruler agrees with
#: that direction on **306 of 307 at 2.0 spaces or more** (100% at 2.0-2.5, 100%
#: at 2.5-3.0, 208 of 209 over 3.0) and on 27 of 29 at 1.5-2.0 and 23 of 30
#: under 1.5 -- the short runs are a neighbouring head of a stack, not a stem.
REACH_STEM_MIN_SPACES = 2.0


def _own_stem_side(ev: Evidence) -> Tuple[Optional[str], Any]:
    """The way THIS head's own stem points, or `(None, None)`.

    ⚠️ ONLY `stem_projection` -- the direction read off a stem attached to
    THIS head. `beam_mate` is borrowed from a neighbour on a stroke over this
    head (BEST, not forced -- its own docstring says so), and using it to
    choose among those same strokes would let the strokes vouch for
    themselves. An abstained or absent direction gives no side, and the
    column test then stands exactly as it was before 2.18.
    """
    v = ev.verdict(Q.STEM_DIRECTION)
    if (v is not None and v.outcome is Outcome.DECIDED
            and v.reason == "stem_projection" and v.value in ("up", "down")):
        return str(v.value), v
    # ⚠️ ROADMAP 2.77b (Sean, 2026-10-09, rhythm-leftovers-2 crop 9): WHERE NO
    # CV STEM IS ATTACHED THE HEAD'S OWN INK STILL SAYS WHICH WAY ITS STEM
    # RUNS. `Q.HEAD_STEM_REACH` is a ruler on the page raster beside THIS
    # head (never a stroke, so the strokes cannot vouch for themselves, which
    # is why `beam_mate` stays excluded above): `up` or `down` is the one
    # direction a vertical run of ink leaves the head. The crop-9 head had its
    # stem read `up` 4.45 spaces and no CV stem at all (two stacked heads fuse
    # into one too-WIDE component, `RUN_TOO_WIDE`), so its direction came from
    # `beam_mate` (`down`, from the NEXT staff's beam below it) and the beam
    # across the head's own bottom counted as its own. `both` and `none`
    # claim nothing and leave the column test exactly as it was.
    reach = ev.rows(Q.HEAD_STEM_REACH)
    if reach and reach[-1].value in ("up", "down"):
        d = reach[-1].detail or {}
        ext = d.get("up_ext" if reach[-1].value == "up" else "down_ext")
        if isinstance(ext, (int, float)) and ext >= REACH_STEM_MIN_SPACES:
            return str(reach[-1].value), reach[-1]
    return None, None


def _on_stem_side(beams, head_box, side):
    """`(strokes on the stem side of this head, strokes on the far side)`.

    ⚠️⚠️ ROADMAP 2.18: THE COLUMN TEST WAS BLIND IN Y. `_beam_levels` counts
    a stroke by its x-range alone, so on a two-voice staff the OTHER voice's
    beam under a stem-up head -- or, through the cell's 4-space pad, the next
    staff's beam -- counted as this note's: CERTAIN where it covered the
    column, POSSIBLE where it ended within a notehead's width. [C12]: a beam
    joins STEM ENDS, so a note's beams stand on the side its stem points to;
    a stroke whose centre is across the head's own centre from it cannot be
    one of them. That FOLLOWS (it is forced by the engraving, given a stem
    read off this head), so it belongs here and not in INFER.

    Measured on Breitkopf 317803 p1 (`benchmarks/omr-missing-notes-2026-09/
    FINDINGS.md` §10): 39 of the 104 heads EXPORT refuses as
    `duration_narrowed` are narrowed ONLY by far-side strokes, and 29 carry a
    far-side stroke among their CERTAIN levels too.

    ⚠️ THE CENTRE OF THE HEAD, NOT ITS EDGE. A stroke lying THROUGH the head
    (the CV opening fuses a row of heads into one horizontal run) sits within
    a fraction of a space of the centre and lands on whichever side its own
    centre happens to fall; this rule is NOT claimed as a fix for that fault,
    which is a beam reader's false positive and not a question of side.
    """
    if side is None or head_box is None:
        return list(beams), []
    hyc = head_box[1] + head_box[3] / 2.0
    sign = -1.0 if side == "up" else 1.0
    near, far = [], []
    for b in beams:
        box = _xywh(b)
        if box is None:
            near.append(b)
            continue
        (near if ((box[1] + box[3] / 2.0) - hyc) * sign > 0
         else far).append(b)
    return near, far


def _head_class(ev: Evidence) -> Optional[str]:
    rows = ev.rows(Q.NOTEHEAD_CLASS)
    if not rows:
        return None
    return max(rows, key=lambda r: (r.score or 0.0)).value


def _head_is_open(base: Optional[float], ev: Evidence) -> bool:
    """Is THIS glyph's own notehead OPEN (hollow)? ROADMAP 2.43, DECISIONS
    2026-09-30 (Sean): *"Correct, open noteheads are never beamed except
    tremolo."*

    Two independent witnesses, either one enough: (a) the detector's own
    CLASS already says so -- every `_HEAD_BEATS` entry but `noteheadBlack`
    (`noteheadHalf*`, `noteheadWhole*`, `noteheadDoubleWhole*`) is drawn
    hollow and none of them is ever beamed, so `base` (the head's own beat
    value before any mark) not being the black head's own `1.0` already
    settles it; (b) a decisively hollow `Q.NOTEHEAD_INK` reading on THIS
    glyph (2.23's `_ink_reads_decisively_hollow`) settles it even where the
    detector's class reads BLACK.

    ⚠️ A TREMOLO STROKE THROUGH A HOLLOW HEAD'S STEM IS A TREMOLO, NOT A
    BEAM LEVEL (Sean, same line) -- out of scope here, named only: this
    function only answers *is the head open*, and `adjudicate_duration` is
    the one that must not let a beam-shaped reading narrow it.
    """
    if base is not None and base != _HEAD_BEATS["noteheadBlack"]:
        return True
    for row in ev.rows(Q.NOTEHEAD_INK):
        if _ink_reads_decisively_hollow(row.detail or {}):
            return True
    return False


def _own_stem_x_span(own_stems, tol: float) -> Optional[Tuple[float, float]]:
    """The x-span THIS head's own stem(s) occupy, padded by `tol` -- or
    `None` where this head has no own stem to test a stroke's column
    against. ROADMAP 2.43.

    ⚠️ REUSES `tol` (`STEM_JOIN_TOLERANCE_SPACES`, already the slack past a
    stem's TIP) rather than inventing a second, untested number for the
    slack across its WIDTH -- CONVENTION ASSUMED / WHAT WOULD FALSIFY IT: a
    real beam whose box, at this tolerance, still does not overlap its own
    stem's padded x-span / NOT CONFIRMED with Sean.
    """
    boxes = [b for b in (_xywh(s) for s in own_stems) if b is not None]
    if not boxes:
        return None
    x0 = min(b[0] for b in boxes) - tol
    x1 = max(b[0] + b[2] for b in boxes) + tol
    return (x0, x1)


def _stem_tip_flag_ink(ev: Evidence, cell, own_stems, side: Optional[str]
                       ) -> Tuple[Optional[bool], tuple]:
    """Does THIS head's own stem tip carry flag-shaped ink the detector
    never boxed? `(None, ())` -- no evidence either way -- where this head
    has no own stem direction, no own stem, or `Q.STEM_TIP_INK` never
    reached the matching end (an older record with no such row, every
    reading here abstained, or the window was guarded off). ROADMAP 2.18c.

    ⚠️ ONLY THE END THIS HEAD'S OWN STEM POINTS TO. `gather._observe_stem_
    tip_ink` files a row for BOTH a stem's top and its bottom, because
    GATHER does not know which is the true tip; reading the wrong one would
    ask the question of the wrong end of the same physical stem -- exactly
    the fault `_own_stem_side` (2.18) exists to keep out of the beam join,
    asked again here of a different reader.
    """
    if side not in ("up", "down") or not own_stems:
        return None, ()
    end = "top" if side == "up" else "bottom"
    ids = {s.id for s in own_stems}
    rows = ev.rows(Q.STEM_TIP_INK, scope=Scope.SELF_AND_ANCESTORS,
                   subject=cell)
    matched = tuple(r for r in rows if r.detail.get("end") == end
                    and r.detail.get("stem_row_id") in ids)
    if not matched:
        return None, ()
    return any(bool(r.value) for r in matched), matched


def _stem_tip_hook_count(rows) -> Tuple[Optional[int], int, int]:
    """What the stem-tip reader says about HOW MANY hooks, over the rows that
    SAW one. ROADMAP 2.69 (Sean, 2026-10-09).

    Returns `(counted, lo, hi)`. `counted` is an int only where EVERY row
    that saw a hook counted the same level; otherwise `None` and `[lo, hi]`
    is the bracket of flag levels the ink leaves open, both >= 1 -- a hook
    seen rules out the head's own value, so level 0 is never in the bracket.
    A row from before the count existed (no `hooks_min`/`hooks_max` in its
    detail) brackets the two levels the old narrowing could not choose
    between: an eighth or a sixteenth.
    """
    seen = [r for r in rows if r.value]
    counts = {r.detail.get("hooks") for r in seen}
    if seen and len(counts) == 1:
        only = next(iter(counts))
        if isinstance(only, int) and not isinstance(only, bool) and only >= 1:
            return int(only), int(only), int(only)
    lo = min((max(1, int(r.detail.get("hooks_min") or 1)) for r in seen),
             default=1)
    hi = max((int(r.detail.get("hooks_max") or 2) for r in seen), default=2)
    return None, lo, max(lo, hi)


def _at_level_value(base: float, level: int, n_dots: int) -> float:
    """The written value of a head of `base` beats carrying `level` beam or
    flag levels and `n_dots` dots -- the arithmetic every branch of
    `adjudicate_duration` spells inline."""
    b = base / (2 ** level) if level else base
    t, add = b, b
    for _ in range(n_dots):
        add /= 2.0
        t += add
    return t


@decision(
    quantity=Q.DURATION,
    checkable=Checkable.MIXED,
    checked_by=(
        '"bar sum: the durations of one voice in one bar must equal the meter (rhythm_sum_warning -- 111 of 193 scan staves, UNCONSUMED)"',
    ),
    implicates=(Q.DURATION, Q.METER, Q.GLYPH_OWNER, Q.MEASURE_PARTITION,
                Q.TUPLET_RATIO),
    # ⚠️ ROADMAP 2.12b PUTS `Q.STAFF_LINES` AND `Q.STAFF_SPACING` IN
    # `composed_from`, AND THAT IS A CLAIM ABOUT THE VALUE. A `restWhole` and
    # a `restHalf` are the same rectangle one line apart, so for those two
    # classes the staff's own lines are not context -- they are where the
    # VALUE comes from, and the class is the corroborating witness.
    # ⚠️ ROADMAP 2.12c ADDS `Q.DOT_ROLE`: `Q.AUG_DOT` now pools two classes
    # and the VALUE this decision reaches for -- how many dots lengthen the
    # note -- depends on which of its rows the geometry actually placed as an
    # augmentation dot, not on which rows merely carry the class.
    # ⚠️ `Q.GROUP_SYMBOL`/`Q.STAFF_GROUP` JOIN AT ROADMAP 2.27d, same reason
    # `Q.ARC_BOX`/`Q.ARC_KIND` did at 2.25b: `_not_the_neighbours_beam` now
    # asks whether the touched neighbour is a DECIDED brace partner before
    # discounting a cross-staff stroke, so the OUTCOME can depend on a fact
    # about the SYSTEM and the neighbour's own STAFF_GROUP, not only on this
    # glyph's own cell.
    composed_from=(Q.BEAM_STROKE, Q.FLAG, Q.AUG_DOT, Q.DOT_ROLE,
                   Q.NOTEHEAD_CLASS, Q.STEM, Q.REST, Q.STAFF_LINES,
                   Q.STAFF_SPACING, Q.FLAG_IS_NOT_A_FLAG, Q.STEM_DIRECTION,
                   Q.STEM_TIP_INK, Q.NOTEHEAD_INK, Q.ARC_BOX, Q.ARC_KIND,
                   Q.GROUP_SYMBOL, Q.STAFF_GROUP, Q.GLYPH_OWNER,
                   Q.BEAM_STEM_JOIN, Q.BEAM_STROKE_INK, Q.STEM_SLASH,
                   # ⚠️ ROADMAP 2.77b: the head's own stem direction where no
                   # CV stem is attached (`_own_stem_side`), so the beams that
                   # can be its own, and with them the value, depend on it;
                   # and the physical-mark group that says the owner holds a
                   # twin of a contest's losing copy.
                   Q.HEAD_STEM_REACH, Q.MARK_GROUP),
    scope=Kind.GLYPH,
    # ⚠️ `Q.STEM_SLASH` JOINS AT ROADMAP 2.71: a beam stroke that is a read
    # tremolo slash's own ink is not counted (`_not_a_slash`), so the level,
    # and with it the value and the OUTCOME, depends on it.
    # ⚠️ `Q.ARC_BOX`/`Q.ARC_KIND` JOIN AT ROADMAP 2.25b: a beam stroke
    # standing inside a DECIDED slur/tie's own box is discounted from this
    # note's beam count (`_not_a_decided_arc`) unless it joins >= 2 of this
    # cell's own stems -- so the OUTCOME can depend on facts about a
    # DIFFERENT glyph entirely, and hiding that from `wiring`/`trace` would
    # be exactly the anti-pattern `Q.STEM`'s own comment below names.
    # `Q.WEDGE_BOX` does NOT join: the hairpin class was named and NOT
    # built (Sean, before merge -- see the comment above `_flag_levels_
    # table`, where the removed `_not_inside_a_wedge` used to live).
    # `Q.STEM` itself is ALSO now read at the NEIGHBOURING staff's
    # cell (`_not_the_neighbours_beam`), a second subject this same
    # quantity reaches -- `composed_from` names the QUANTITY, not the
    # subject, so no new entry is needed for that one.
    # ⚠️ `Q.STEM_DIRECTION` JOINED `composed_from` AT ROADMAP 2.18. Under
    # 2.12e it was a `wants` only -- a flag's direction does not touch its
    # hook count, and zero durations moved. 2.18 makes it choose WHICH beam
    # strokes can be this note's (`_on_stem_side`), so the level, and with it
    # the value, now depends on it; declaring otherwise would hide the
    # dependence from `wiring` and `trace`.
    # ⚠️ `Q.STEM_TIP_INK` JOINS IT AT ROADMAP 2.18c, for the same reason: a
    # head that would otherwise DECIDE its head value NARROWS instead where
    # its own stem's tip reads flag-shaped ink the detector never boxed
    # (`_stem_tip_flag_ink`), so the OUTCOME, not only the value, depends on
    # it.
    # ⚠️ `Q.NOTEHEAD_INK` JOINS IT AT ROADMAP 2.23, same reason as
    # `Q.STEM_TIP_INK`: a head that would otherwise DECIDE its head value
    # NARROWS instead where the ink under its OWN box reads decisively
    # hollow against the detector's BLACK class (`_ink_reads_decisively_
    # hollow`).
    # ⚠️ `Q.BEAM_STEM_JOIN` JOINS IT AT ROADMAP 2.38: a stroke `_beam_levels`
    # would otherwise count as merely POSSIBLE (`beams_ambiguous`) is
    # promoted to CERTAIN, or dropped outright, by `_beam_join_witness`'s
    # ink-continuity reading -- so the OUTCOME, not only the value, depends
    # on it, same reason `Q.STEM_TIP_INK` is declared above rather than left
    # a bare `wants`.
    wants=(Q.BEAM_STROKE, Q.FLAG, Q.AUG_DOT, Q.DOT_ROLE, Q.NOTEHEAD_CLASS,
           Q.STEM, Q.TUPLET_RATIO, Q.GLYPH_BOX, Q.REST, Q.CELL_STAFF_SPACE,
           Q.STAFF_LINES, Q.STAFF_SPACING, Q.STEM_DIRECTION,
           Q.FLAG_IS_NOT_A_FLAG, Q.STEM_TIP_INK, Q.NOTEHEAD_INK,
           Q.ARC_BOX, Q.ARC_KIND, Q.GROUP_SYMBOL, Q.STAFF_GROUP,
           Q.GLYPH_OWNER, Q.BEAM_STEM_JOIN, Q.BEAM_STROKE_INK, Q.STEM_SLASH,
           Q.HEAD_STEM_REACH, Q.MARK_GROUP),
    reasons=("head_and_marks", "beams_ambiguous", "flags_disagree",
             "flag_ink_unread", "hooks_counted", "beam_discounted_uncertain",
             "beam_certain_not_joined",
             "head_fill_from_ink", "hollow_head_bare_stem", "no_notehead",
             "unknown_head", "rest_class", "unreadable_rest",
             "rest_slot_contradicts_class", "rest_stands_where_no_rest_hangs",
             "owned_by_another_staff"),
    mode=Mode.ADDITIVE,
    # ⚠️ NOTEHEADS *AND* RESTS. One question -- how long is this event -- for
    # two kinds of ink. A rest reads its value straight off its class and
    # needs no beam, flag or stem, so the branch below is short; what it must
    # NOT be is a second quantity, or every consumer would ask twice for one
    # fact.
    subjects_from=(Q.NOTEHEAD_CLASS, Q.REST),
    # ⚠️ EVALUATE's `reconcile_duration` supersedes this verdict, so the
    # revision is DECLARED here. Without it `Log.record` raises
    # `AlreadyAdjudicated` -- which is the no-fixpoint guard working, not a
    # bug. The bound lives on the rule.
    revises=Q.DURATION,
)
def adjudicate_duration(ev: Evidence) -> Ruling:
    """The written value, composed from the marks around one notehead.

    ⚠️ ITS RELIABILITY IS ITS WEAKEST INPUT, not the sum of them -- which is
    why `composed_from` names five quantities and why `tally` is deliberately
    not used here. Today `Q.BEAM_STROKE` and `Q.STEM` are DECLARED STUBS
    (`gather_cv_lines`), so every beamed note falls back to its head value and
    `declined` says so on the record rather than the duration silently being
    wrong.

    ⚠️ THE BEAM LEVEL IS THE FRAGILE INPUT and the reason
    `_reconcile_measure_to_meter` exists: durations come from clustering beam
    y-positions, so one extra or missing cluster HALVES OR DOUBLES a note.
    That repair belongs to EVALUATE and is bounded there.
    """
    rest = ev.rows(Q.REST)
    if rest:
        return _rest_ruling(ev, rest)

    head = _head_class(ev)
    if head is None:
        return Ruling.abstain("no_notehead")

    # ⚠️⚠️ ROADMAP 2.77b (Sean, 2026-10-09, rhythm-leftovers-2 crop 9): A COPY
    # THE CONTEST AWARDED TO ANOTHER STAFF, WHOSE TWIN THAT STAFF HOLDS, HAS NO
    # DURATION OF ITS OWN. The detector boxed ONE printed head in each of two
    # staves' padded cells and `glyph_owner` named one the winner; a resolved
    # contest DROPS the loser, it never relocates it (CLAUDE.md §10;
    # `is_relocated_copy` is the one test EXPORT, `consequences._left_the_bar`
    # and the articulation owners apply). What the loser's home cell holds
    # around it is the home staff's own notes' marks, not this head's: crop 9's
    # loser counted two of them (a beam below the head against a stem that
    # runs up) and decided a SIXTEENTH on a printed eighth, a value nothing
    # writes and every population count then included.
    #
    # THE TWIN IS READ OFF `Q.MARK_GROUP` (the same physical mark filed on the
    # owner staff), not assumed: a lone copy -- the owner's box refused, a
    # record gathered without mark groups, `OMR_RELOCATE_AT_EXPORT`'s own
    # population -- is the only reading of that head there is and keeps its
    # duration. An owner that ABSTAINED names no loser either.
    owner = ev.verdict(Q.GLYPH_OWNER)
    if owner is not None and owner.outcome is Outcome.DECIDED \
            and is_relocated_copy(ev.subject, owner.value):
        me = ev.subject.to_key()
        twin = None
        for g in ev.rows(Q.MARK_GROUP):
            for m in (g.detail or {}).get("members") or ():
                ms = Subject.from_key(m).at(Kind.STAFF) if m != me else None
                if ms is not None and ms.to_key() == owner.value:
                    twin = m
        if twin is not None:
            return Ruling.abstain("owned_by_another_staff",
                                  owner=owner.value, twin=twin,
                                  head=str(head))

    base = None
    for name, beats in _HEAD_BEATS.items():
        if str(head).startswith(name):
            base = beats
            break
    if base is None:
        return Ruling.abstain("unknown_head", head=str(head))

    # ⚠️⚠️ ROADMAP 2.43, DECISIONS 2026-09-30 (Sean): "open noteheads are
    # never beamed except tremolo" -- computed once, up front, and read at
    # every beam-shaped narrowing below (never the flag branches: a flag
    # box actually attached to an open head is a contradiction the tree
    # already handles unchanged, not this rule's business).
    hollow = _head_is_open(base, ev)
    # ⚠️ NARROWER THAN `hollow`, AND DELIBERATELY SO: the detector's CLASS
    # alone, with NO ink witness folded in. `_stem_tip_flag_ink` (2.18c)
    # infers an unread FLAG from CV ink at the stem's own tip; a
    # detector-class HALF/WHOLE/DOUBLE-WHOLE head can never carry one
    # either (same convention), so that inference is skipped there too --
    # but a BLACK-classed head whose ink separately reads decisively
    # hollow (2.23) is `_head_fill_from_ink`'s OWN, already-ordered
    # territory (`test_it_NEVER_FIRES_where_stem_tip_ink_ALREADY_narrowed`
    # depends on `flag_ink_unread` still being TRIED first there), so
    # `hollow`'s ink half must not also gate it.
    open_by_class = base is not None and base != _HEAD_BEATS["noteheadBlack"]

    used = [r.id for r in ev.rows(Q.NOTEHEAD_CLASS)]

    box = ev.rows(Q.GLYPH_BOX)
    x_center = head_width = None
    if box:
        v = box[-1].value
        if isinstance(v, (list, tuple)) and len(v) >= 4:
            x_center = float(v[1]) + float(v[3]) / 2.0
            head_width = float(v[3])
        used.append(box[-1].id)

    cell = ev.subject.at(Kind.CELL)
    kept, cv, yolo = _kept_beams(ev, cell)
    # ⚠️ `Q.STEM` WAS DECLARED IN `wants` AND `composed_from` AND READ BY
    # NOTHING -- this project's own named anti-pattern, inside the decision
    # whose docstring calls the beam level its fragile input. The stems were
    # gathered (916 rows on a three-page fixture) and the association that
    # needs them was being made on the notehead's centre instead.
    stems = ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell)
    head_box = None
    if box:
        hb = _xywh_head(box[-1].value)
        head_box = hb
    # ⚠️ MOVED EARLY FOR ROADMAP 2.25b: `_not_the_neighbours_beam`'s own
    # override (a stroke THIS head's own stem reaches stays, whatever else
    # it touches) needs this head's attached stems before any filtering,
    # not only after 2.18's side test. Reused below where 2.18/2.18b read it.
    own_stems = _stems_on(head_box, stems) if head_box is not None else []
    # ⚠️ ROADMAP 2.25, FIRST: a stroke standing where a `ledgerLine` glyph is
    # boxed in THIS cell is that ledger line, not a beam -- dropped before
    # side/tolerance filtering ever sees it, so those steps (which reason
    # about a NOTE's stem) work on a set that no longer holds ink that is
    # not even a mark of duration at all. `used` gets nothing for the ones
    # dropped: a stroke this decision refused to count is not evidence it
    # composed from.
    ledger_boxes = _ledger_line_glyph_boxes(ev, cell)
    tol = _join_tolerance(ev, cell)
    kept, ledger_dropped = _not_a_ledger_line(
        kept, ledger_boxes,
        keep=_beam_anchor_ids(
            ev, cell, kept, tol,
            _notehead_glyph_boxes(
                ev, cell, tol / STEM_JOIN_TOLERANCE_SPACES if tol > 0 else 0.0)))
    # ⚠️ ROADMAP 2.71 (Sean, 2026-10-09): a stroke that is a read TREMOLO
    # SLASH's own ink is not a beam level of anything. Same tier as the ledger
    # line, and BEFORE every guard below on purpose: a slash is a mark of
    # another kind, not an absence, so removing it never narrows the head
    # (rule 8 guards a note a refused stroke WOULD have marked).
    kept, slash_dropped, slash_used = _not_a_slash(ev, cell, kept)
    used.extend(r.id for r in slash_used)
    # ⚠️ ROADMAP 2.25b, SAME TIER: a stroke that is the NEIGHBOUR staff's own
    # beam (through the cell's pad) or a DECIDED slur/tie's own ink -- each a
    # CONNECTION to a fact already on the record about the OTHER object,
    # never a guess from mere overlap (rule 6; FINDINGS SS13f/SS13h). Both
    # are additive-safe and run before 2.18/2.18b for the same reason the
    # ledger-line drop does. (A third class, the hairpin, was named and NOT
    # built -- see the comment above `_flag_levels_table`.)
    before_2_25b = list(kept)
    kept, neighbour_dropped = _not_the_neighbours_beam(
        ev, cell, kept, stems, own_stems)
    kept, arc_dropped = _not_a_decided_arc(ev, cell, kept, stems)
    # ⚠️⚠️ RULE 8, APPLIED TO 2.25b (manager, before merge): discounting a
    # stroke as the neighbour's or a decided arc's own ink may not by
    # itself turn a marked note into an unmarked one. Recorded here, before
    # 2.18/2.18b touch `kept` further, and read again near the bottom of
    # this function once flags are known -- a stemmed head that had SOME
    # candidate stroke before this tier, has NONE after it, and these two
    # rules (not an empty page) are why, is the population that guard
    # covers; the SAME test 2.18b's own `beyond_stem_kept_no_other_mark`
    # runs for a different cause.
    discount_removed_all_marks = (bool(before_2_25b) and not kept
                                  and bool(neighbour_dropped or arc_dropped))
    # ⚠️ ROADMAP 2.18: only strokes on the side this head's OWN stem points
    # to can be its beams (`_on_stem_side`). No own stem direction -> no side
    # -> every stroke stays, exactly as before.
    side, side_verdict = _own_stem_side(ev)
    # ⚠️ ROADMAP 2.77b: a stem the RULER read where the CV rung attached none.
    # Such a head HAS a stem whose tip nothing examined (two stacked heads fuse
    # into one too-wide component and the CV finds no stem at all), so a mark
    # that is discounted or put on the far side of it is NOT evidence that the
    # head carries none -- rule 8 applies exactly as it does to a CV stem.
    reach_stem = (side is not None and not own_stems
                  and getattr(side_verdict, "quantity", None)
                  == Q.HEAD_STEM_REACH)
    kept, far_side = _on_stem_side(kept, head_box, side)
    # the side test alone emptied the head's candidate strokes (reach stem only)
    far_removed_all_marks = reach_stem and bool(far_side) and not kept
    if side_verdict is not None:
        used.append(side_verdict.id)
    # ⚠️ ROADMAP 2.18b: `STEM_JOIN_TOLERANCE_SPACES` in THIS cell's pixels
    # (0 where the cell has no unit). It sets the reach past the stem tip
    # (`_beyond_own_stem`) and the flag attachment; the beam join itself
    # stays at overlap (`_stem_joined`).
    tol = _join_tolerance(ev, cell)
    kept_all = kept
    kept, beyond = _beyond_own_stem(kept, stems, own_stems, side, tol)
    # ⚠️ ROADMAP 2.74 (Sean, 2026-10-09): a stroke the INK reads as too thin,
    # bowed, or standing on one stem is not a beam. Read off
    # `Q.BEAM_STROKE_INK`; an unread test keeps the stroke (rule 8). AFTER
    # the side and beyond-the-tip tests on purpose: it judges the strokes
    # that would otherwise COUNT, so a stroke those tests refuse anyway is
    # not one the ink "removed".
    pre_ink = list(kept)
    kept, ink_dropped, ink_used = _not_a_beam_by_ink(
        ev, cell, kept, stems, tol)
    joined, attached = _stem_joined(kept, stems, head_box)
    # ⚠️ ROADMAP 2.43: THIS HEAD'S OWN STEM'S PADDED X-SPAN, gating
    # `_beam_levels`'s merely-POSSIBLE column match (`None` where this head
    # has no own stem -- unchanged there).
    stem_x = _own_stem_x_span(own_stems, tol)
    # ⚠️ ROADMAP 2.38: the ink-continuity witness for whatever this pass's
    # OWN `kept` set turns out to be -- recomputed below too, since the
    # rule-8 guard can restore `kept_all` and change which strokes are
    # merely POSSIBLE (the only ones the witness is ever consulted for).
    join_witness, join_used = _beam_join_witness(ev, cell, kept, own_stems,
                                                 side)
    used.extend(r.id for r in join_used)
    certain, possible, certain_conflicts = _beam_levels(
        kept, x_center, head_width, joined, join_witness, stem_x=stem_x)
    # ⚠️⚠️ RULE 8: DROPPING A STROKE MAY NOT BY ITSELF MAKE A NOTE UNMARKED.
    # Where the strokes past the tip were the ONLY thing over this head, and
    # its stem carries no beam and no flag once they go, the note would fall
    # to its head value -- a decision made from ABSENCE. Priced on Breitkopf
    # p1 (FINDINGS §11), 3 of the 6 judgeable notes that fell that way print
    # a flag or a beam no reader read (against 10 of 69 across every stemmed
    # head the page wrote at its head value), so the strokes stay and the
    # reading stays what it was.
    beyond_guarded = False
    if beyond and not possible and not _attached_flags(
            ev, cell, attached, tol)[1]:
        kept, beyond, beyond_guarded = kept_all, [], True
        pre_ink = list(kept)
        kept, ink_dropped, ink_used = _not_a_beam_by_ink(
            ev, cell, kept, stems, tol)
        joined, attached = _stem_joined(kept, stems, head_box)
        join_witness, join_used = _beam_join_witness(ev, cell, kept,
                                                      own_stems, side)
        used.extend(r.id for r in join_used)
        certain, possible, certain_conflicts = _beam_levels(
            kept, x_center, head_width, joined, join_witness, stem_x=stem_x)
    # ⚠️⚠️ ROADMAP 2.75 (Sean, 2026-10-09: rhythm-leftovers tiles 8 and 9,
    # printed EIGHTHS read 16th and 32nd): ONE PRINTED HEAD SHARED BY TWO
    # VOICES carries a stem each way and each stem has its OWN beam -- the
    # up-stem's beam over the head, the down-stem's under it (Litolff p3: the
    # unison of two eighth-note voices). `_beam_levels` counted both beams as
    # levels of ONE stem and read two levels (and a stray third). Each stem's
    # levels are counted against ITS side only; where the voices agree that is
    # the head's level, where they differ the head is a RANGE (rule 8: never
    # one voice's value for both). Only where this head has no single decided
    # stem direction (`side is None`) and a stem on each side.
    voice_levels = None
    if side is None and head_box is not None:
        vs = _voice_stems(own_stems, head_box)
        if vs["up"] and vs["down"]:
            voice_levels = {}
            v_kept: list = []
            v_conf: list = []
            for vside in ("up", "down"):
                near, _far = _on_stem_side(kept, head_box, vside)
                near, _beyond_v = _beyond_own_stem(near, stems, vs[vside],
                                                   vside, tol)
                v_joined, _v_att = _stem_joined(near, vs[vside], head_box)
                v_wit, v_used = _beam_join_witness(ev, cell, near, vs[vside],
                                                   vside)
                used.extend(r.id for r in v_used)
                c, pz, cc = _beam_levels(
                    near, x_center, head_width, v_joined, v_wit,
                    stem_x=_own_stem_x_span(vs[vside], tol))
                voice_levels[vside] = [c, pz]
                v_kept.extend(b for b in near if b not in v_kept)
                v_conf.extend(cc)
            certain = min(v[0] for v in voice_levels.values())
            possible = max(v[1] for v in voice_levels.values())
            certain_conflicts = tuple(v_conf)
            kept = v_kept
    # ⚠️⚠️ ROADMAP 2.43, DECISIONS 2026-09-30 (Sean): "open noteheads are
    # never beamed except tremolo" -- a hollow head's beam levels are FIXED
    # AT ZERO, whatever `_beam_levels` (or a stray YOLO `beam` box in its
    # cell) would otherwise have counted. Overridden here, AFTER every
    # geometric filter above has already run (so `yolo_kept`/`beams_far_
    # side`/etc. below still report what the cell actually held, for
    # tracing), and BEFORE `levels` and `beam_evidence` are read from it, so
    # every branch downstream (`beams_ambiguous`, `beam_certain_not_joined`,
    # `beam_discounted_uncertain`) sees an unambiguous zero and never fires.
    # ⚠️ ROADMAP 2.70: what the strokes said BEFORE the override just below
    # zeroed them. A hollow-reading head whose stem a beam is joined to is the
    # 2.23 false positive (a black head read hollow), so the bare-stem rule
    # must see the strokes the override hid.
    strokes_before_hollow = (certain, possible, len(certain_conflicts))
    if hollow:
        certain = possible = 0
        certain_conflicts = ()
    levels = certain
    used.extend(b.id for b in kept)
    used.extend(r.id for r in ink_used)
    # ⚠️ ROADMAP 2.74, RULE 8: the ink's refusals may not by themselves turn a
    # marked note into an unmarked one -- the same shape as 2.25b's guard,
    # WITHOUT its `own_stems` condition (a chord head shares a stem no box of
    # its own overlaps, and Brahms p1 page 0 holds ~45 of them: beamed
    # eighths whose only 'beam' was a detector box lying on a staff line).
    # It fires only where the strokes the ink refused WOULD HAVE COUNTED for
    # this head (a stroke over some other note's column, or one the beyond-the-
    # tip guard restored for nothing, never marked it): the head had a level
    # before the ink refused it and has none after.
    pre_possible = 0
    if ink_dropped and not possible:
        pre_joined, _ = _stem_joined(pre_ink, stems, head_box)
        pre_witness, _ = _beam_join_witness(ev, cell, pre_ink, own_stems, side)
        _pc, pre_possible, _pk = _beam_levels(
            pre_ink, x_center, head_width, pre_joined, pre_witness,
            stem_x=stem_x)
    ink_removed_all_marks = bool(ink_dropped) and pre_possible > 0 \
        and not possible
    used.extend(s.id for s in attached)

    # ⚠️ THREE STATES, AND THEY MUST NOT COLLAPSE INTO ONE. A duration that is
    # right BECAUSE THE BEAMS WERE READ and one that is right because the note
    # HAPPENED TO BE UNBEAMED are different facts, and the second must not be
    # promoted to the first when the CV rung lands. `beam_evidence` says
    # which, and `declined` carries the reader's own abstention beside it.
    if ev.state(Q.BEAM_STROKE, scope=Scope.SELF_AND_ANCESTORS,
                subject=cell) is not State.READ:
        beam_evidence = "reader_declined"
    elif levels:
        beam_evidence = "read"
    else:
        beam_evidence = "none_over_this_note"

    flags, flag_levels = _attached_flags(ev, cell, attached, tol)
    # ⚠️⚠️ ROADMAP 2.18b, RULE 8: FLAGS THAT DISAGREE NARROW. `_attached_flags`
    # returns the MAX of its flags' levels, which is right while they agree
    # (two boxes, one glyph). Where one mark is boxed as `flag8th*` AND
    # `flag16th*` (Breitkopf p1 `glyph/1/1/9/0/13`, Litolff idx 3
    # `glyph/3/0/7/3/5`, both reached through the join tolerance) the max is
    # an argmax over a disagreement. A box an existing verdict refuses never
    # got here (`_attached_flags` skips it), so it does not vote.
    flag_level_votes: Dict[int, int] = {}
    for f in flags:
        lv = _flag_levels_for(f.value)
        if lv:
            flag_level_votes[lv] = flag_level_votes.get(lv, 0) + 1
    flags_disagree = False
    if flag_levels and not levels:
        # A flag says the same thing a beam does for an unbeamed note.
        levels = flag_levels
        used.extend(r.id for r in flags)
        beam_evidence = "flag"
        flags_disagree = len(flag_level_votes) > 1
    beats = base / (2 ** levels) if levels else base

    # dots lengthen: each adds half of what stands so far.
    space_row = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS,
                        subject=cell)
    space = float(space_row[-1].value) if space_row else None
    if space_row:
        used.append(space_row[-1].id)
    dots = _attached_dots(ev, cell, head_box, space)
    n_dots = len(dots)
    used.extend(r.id for r in dots)
    total, add = beats, beats
    for _ in range(n_dots):
        add /= 2.0
        total += add

    # ⚠️ A TUPLET SCALES THE TIME AND LEAVES THE WRITTEN VALUE ALONE. The
    # noteheads of a triplet are ORDINARY eighths on the page; the bracket
    # says three of them occupy two's worth. So `duration_beats` is scaled and
    # `written` is not -- which is what MusicXML's <type> and LilyPond's `8`
    # both want inside a tuplet.
    ratio = ev.verdict(Q.TUPLET_RATIO, subject=ev.subject.at(Kind.CELL))
    scaled = total
    if ratio is not None and isinstance(ratio.value, dict):
        num = ratio.value.get("actual")
        den = ratio.value.get("normal")
        if num and den and ev.subject.glyph in (ratio.value.get("members") or []):
            scaled = total * den / num
            used.append(ratio.id)

    shared = {"head": str(head), "head_is_open": hollow,
              "beam_evidence": beam_evidence,
              "cv_beams": len(cv), "yolo_beams": len(yolo),
              "yolo_kept": (len(kept) + len(far_side) + len(beyond)
                           + len(ledger_dropped) + len(slash_dropped)
                           + len(neighbour_dropped)
                           + len(arc_dropped) + len(ink_dropped)
                           - len(cv)),
              "beams_ledger_line": len(ledger_dropped),
              # ⚠️ ROADMAP 2.71: strokes that were a tremolo slash's own ink.
              "beams_slash": len(slash_dropped),
              "beams_neighbour_staff": len(neighbour_dropped),
              "beams_decided_arc": len(arc_dropped),
              # ⚠️ ROADMAP 2.74: strokes the ink read as not a beam, by why.
              "beam_voices": voice_levels,
              "beams_not_by_ink": len(ink_dropped),
              "beams_not_by_ink_why": {
                  w: sum(1 for v in ink_dropped.values() if v == w)
                  for w in sorted(set(ink_dropped.values()))},
              "beam_side": side, "beams_far_side": len(far_side),
              "beams_beyond_stem": len(beyond),
              "beyond_stem_kept_no_other_mark": beyond_guarded,
              "join_tolerance_px": round(tol, 2),
              "stems_attached": len(attached), "beams_by_stem": len(joined),
              "flags_attached": len(flags), "flag_levels": flag_levels,
              "dots_attached": n_dots,
              "staff_space": space,
              "levels_certain": certain, "levels_possible": possible,
              # ⚠️ ROADMAP 2.12e. Read AFTER `flag_levels` is fixed, so the
              # ordering on the page says what the code does: the hook count
              # is the flag's SHAPE claim and sets the duration; the direction
              # is its ROLE claim and comes from the stem. Empty where this
              # head carries no flag, so a reader cannot mistake *no flag* for
              # *a flag with no direction*.
              **_flag_direction(ev, flags)}

    # ⚠️⚠️ ROADMAP 2.38b, RULE 8, CHECKED FIRST. A CERTAIN stroke (box
    # geometry) the ink reads NOT JOINED is a DISAGREEMENT between two
    # independent witnesses, not a count to silently correct in either
    # direction -- `_beam_levels`'s own docstring has the measured
    # argument (Brahms p1: ~50 of 165 NOT-JOINED-only decisions were wrong
    # beam_levels). NARROW between the level AS BOX GEOMETRY ALONE COUNTS
    # IT (`certain`, unchanged) and the level WITHOUT the disputed
    # stroke(s) (`certain` minus however many disagree) -- never straight
    # to either, and EQUAL support: nothing here says which witness is
    # right, only that they disagree.
    if certain_conflicts:
        disputed = len(certain_conflicts)
        cands = []
        for level in sorted({certain, max(certain - disputed, 0)}):
            b = base / (2 ** level) if level else base
            t, add = b, b
            for _ in range(n_dots):
                add /= 2.0
                t += add
            cands.append(Candidate(
                value={"beats": _scale(t, ratio, ev), "written": t,
                       "dots": n_dots, "beam_levels": level},
                support=1.0))
        return Ruling.narrow(cands, "beam_certain_not_joined",
                             used=tuple(used), **shared,
                             certain_conflicts=len(certain_conflicts))

    # ⚠️ WHERE THE BEAM READING IS A RANGE, SO IS THE DURATION. Narrowing is
    # not a weaker answer than deciding -- it is the true one, and it is what
    # lets `reconcile_duration` search ADMITTED levels instead of arithmetic
    # +/-1. A note whose strokes are unambiguous still DECIDES.
    if flags_disagree:
        # ⚠️ ROADMAP 2.74 / 2.69 (tile 15): the detector boxed ONE flag as
        # both `flag8th*` and `flag16th*`. The stem-tip reader COUNTS the
        # hooks at this head's own stem (2.69) -- the same fact, off the ink,
        # from a reader that does not share the detector's box. Where its
        # count is one of the levels the boxes vote for, it breaks the tie
        # (the counted ink is the witness that can say which box is right);
        # where it names a level NO box voted for, or did not count, the
        # disagreement stands and narrows as before (never an argmax).
        _tip, _tip_rows = _stem_tip_flag_ink(ev, cell, own_stems, side)
        if _tip:
            _counted, _lo, _hi = _stem_tip_hook_count(_tip_rows)
            if _counted is not None and _counted in flag_level_votes:
                used.extend(r.id for r in _tip_rows)
                t = _at_level_value(base, _counted, n_dots)
                return Ruling(value={"beats": _scale(t, ratio, ev),
                                     "written": t, "dots": n_dots,
                                     "beam_levels": _counted},
                              reason="hooks_counted", used=tuple(used),
                              detail={**shared, "hooks_counted": _counted,
                                      "flags_disagree_settled_by_hooks": True,
                                      "flag_level_votes": {
                                          str(k): v for k, v in
                                          sorted(flag_level_votes.items())}})
        cands = []
        for level in sorted(flag_level_votes):
            b = base / (2 ** level)
            t, add = b, b
            for _ in range(n_dots):
                add /= 2.0
                t += add
            cands.append(Candidate(
                value={"beats": _scale(t, ratio, ev), "written": t,
                       "dots": n_dots, "beam_levels": level},
                # ⚠️ SUPPORT = how many attached boxes name this level; no
                # other ordering is claimed.
                support=float(flag_level_votes[level])))
        return Ruling.narrow(cands, "flags_disagree", used=tuple(used),
                             **shared, flag_level_votes={
                                 str(k): v for k, v in
                                 sorted(flag_level_votes.items())})

    if possible > certain and beam_evidence in ("read", "none_over_this_note"):
        cands = []
        for level in range(certain, possible + 1):
            b = base / (2 ** level) if level else base
            t, add = b, b
            for _ in range(n_dots):
                add /= 2.0
                t += add
            cands.append(Candidate(
                value={"beats": _scale(t, ratio, ev), "written": t,
                       "dots": n_dots, "beam_levels": level},
                # ⚠️ SUPPORT, NOT PROBABILITY: a stroke that certainly covers
                # the note outranks one that merely might, and the ORDER is
                # the whole claim. These numbers are in this function's own
                # units and must never be normalised.
                support=2.0 if level == certain else 1.0))
        return Ruling.narrow(cands, "beams_ambiguous", used=tuple(used),
                             **shared)

    # ⚠️⚠️ ROADMAP 2.25b, RULE 8 (manager, before merge). Reached only where
    # this head has a STEM (a rest or an unstemmed head has no beam to lose)
    # and `discount_removed_all_marks` fired above: the neighbour-staff or
    # decided-arc connection discounted every candidate stroke this head
    # had, and nothing else (no flag) stands over it. Deciding the head
    # value outright there would convert *the ink we discounted might have
    # been a real beam* into a silent quarter -- rule 8's own words. NARROW
    # between the head value and ONE beam level instead, exactly the
    # `flag_ink_unread` shape below: never straight to a specific count,
    # because the discount says nothing about HOW MANY levels the ink
    # would have been.
    # ⚠️ ROADMAP 2.43: `not hollow` -- an OPEN head is never beamed (Sean,
    # DECISIONS 2026-09-30), so a discount that removed its candidate
    # strokes must not narrow it toward one anyway.
    if (((discount_removed_all_marks and (own_stems or reach_stem))
         or ink_removed_all_marks or far_removed_all_marks)
            and beam_evidence == "none_over_this_note"
            and not flag_levels and not hollow):
        cands = []
        for level in (0, 1):
            b = base / (2 ** level) if level else base
            t, add = b, b
            for _ in range(n_dots):
                add /= 2.0
                t += add
            cands.append(Candidate(
                value={"beats": _scale(t, ratio, ev), "written": t,
                       "dots": n_dots, "beam_levels": level},
                support=2.0 if level == 1 else 1.0))
        return Ruling.narrow(cands, "beam_discounted_uncertain",
                             used=tuple(used), **shared)

    # ⚠️⚠️ ROADMAP 2.18c, RULE 8. Reached only where NOTHING over this head
    # was read as a beam or a flag (`beam_evidence == "none_over_this_note"`,
    # not `"reader_declined"` -- the reader ran and found no mark, which is
    # different from never having run at all) -- so today's fallback is the
    # head's own value, "quarter". `benchmarks/omr-missing-notes-2026-09/
    # FINDINGS.md` SS11.4b: ~6 of 53 such heads on Breitkopf p1 PRINT a flag
    # nothing on the record witnesses -- `cannot tell` written as an answer.
    # `_stem_tip_flag_ink` is a SECOND, CV witness at the stem's own tip;
    # where it reads flag-shaped ink, NARROW instead of deciding -- and only
    # ever between the head value and ONE flag level. Never straight to
    # eighth: the ink says a hook is there, not how many, and deciding a
    # specific count from it would be exactly the guess rule 6 forbids.
    # ⚠️ ROADMAP 2.43: `not open_by_class` -- there is no such notation as an
    # open head carrying a flag, so a detector-class HALF/WHOLE/DOUBLE-WHOLE
    # head's stem tip is never asked this question either. NOT `hollow`'s
    # ink half: an ink-decided-hollow BLACK-classed head is `head_fill_
    # from_ink`'s own territory below, tried in this ORDER on purpose
    # (`test_it_NEVER_FIRES_where_stem_tip_ink_ALREADY_narrowed`).
    tip_ink = tip_ink_rows = None
    if beam_evidence == "none_over_this_note" and not flag_levels \
            and not open_by_class:
        tip_ink, tip_ink_rows = _stem_tip_flag_ink(ev, cell, own_stems, side)
    if tip_ink:
        used.extend(r.id for r in tip_ink_rows)

        # ⚠️⚠️ ROADMAP 2.69 (Sean, 2026-10-09: *"Count the hooks and if you
        # can't count use the fact that there is a hook to help later
        # deduction"*) REPLACES 2.18c's head-value-or-one-flag-level
        # narrowing. A hook SEEN on this head's own stem rules out the
        # head's own value -- a flagged note is never a quarter -- so level
        # 0 is in NEITHER branch below. Counted: DECIDED at that level.
        # Seen but not counted: NARROWED over the flag levels the ink leaves
        # open (>= 1 only), the lowest best-supported, and EVALUATE's
        # `reconcile_duration` settles it where exactly one candidate makes
        # the bar add up (INFER, labelled, where it does not).
        def _at_level(level):
            b = base / (2 ** level)
            t, add = b, b
            for _ in range(n_dots):
                add /= 2.0
                t += add
            return t

        counted, lo, hi = _stem_tip_hook_count(tip_ink_rows)
        if counted is not None:
            t = _at_level(counted)
            return Ruling(value={"beats": _scale(t, ratio, ev), "written": t,
                                 "dots": n_dots, "beam_levels": counted},
                          reason="hooks_counted", used=tuple(used),
                          detail={**shared, "hooks_counted": counted})
        cands = []
        for level in range(lo, hi + 1):
            t = _at_level(level)
            cands.append(Candidate(
                value={"beats": _scale(t, ratio, ev), "written": t,
                       "dots": n_dots, "beam_levels": level},
                # ⚠️ SUPPORT, NOT PROBABILITY, same convention as
                # `beams_ambiguous` above: the ink's own lower bound (the
                # hooks it certainly shows) outranks the levels it merely
                # does not exclude, and the ORDER is the whole claim.
                support=2.0 if level == lo else 1.0))
        return Ruling.narrow(cands, "flag_ink_unread", used=tuple(used),
                             **shared, hooks_min=lo, hooks_max=hi)

    # ⚠️⚠️ ROADMAP 2.23. CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT
    # CONFIRMED (nobody has been asked, CLAUDE.md rule 3): a hollow
    # (half/whole) notehead's own interior stays near-empty even where its
    # BORDER merges with neighbouring ink on a MERGING plate (CLAUDE.md
    # §10), so `Q.NOTEHEAD_INK`'s `center` window stays decisively lighter
    # than its `ring` window; a genuinely filled BLACK head shows the
    # opposite. It would be falsified by a Sean-adjudicated crop where a
    # confirmed BLACK head reads this way, or a confirmed HOLLOW head does
    # not (`benchmarks/omr-head-fill-2026-09/FINDINGS.md`).
    #
    # Reached only where NOTHING else already narrowed or added a mark to
    # this note (no flags, no ambiguous beams, no stem-tip flag ink) and the
    # detector's own class says BLACK (a hollow head never carries a beam
    # or a flag, so this is exactly the population `beam_evidence ==
    # "none_over_this_note"` names). `benchmarks/omr-bar-sum-holdout-2026-09/
    # FINDINGS.md` §17b: on Litolff 1/i this is the single biggest minimal-
    # fix class over the whole movement's held bars (`F`, 300 bars, 405
    # released as the sole fix).
    #
    # ⚠️ NEVER FLIPPED OUTRIGHT (rule 6: connect, never guess). Where the
    # ink is decisive, NARROW between the head as the detector read it and
    # BOTH hollow readings (half, whole) -- `reconcile_duration` (2.19,
    # 2.22) is the only place that picks among them, and only where exactly
    # one candidate lands the bar's own arithmetic exactly. Where the ink is
    # not decisive, this note is unchanged -- a fallback never converts
    # "cannot tell" into an answer (rule 8).
    fill_row = None
    if not flag_levels and not tip_ink \
            and base == _HEAD_BEATS["noteheadBlack"]:
        ink_rows = ev.rows(Q.NOTEHEAD_INK)
        if ink_rows:
            fill_row = ink_rows[-1]
    ink_hollow = (fill_row is not None
                  and _ink_reads_decisively_hollow(fill_row.detail or {}))

    # ⚠️⚠️ ROADMAP 2.70 (Sean, DECISIONS 2026-10-09): *"A hollow note with
    # nothing on the stem is always a half note."* CONVENTION CONFIRMED. The
    # ink outranks the detector's black class where ALL of these hold: the
    # ink reads the head decisively hollow (2.23's own cut, NOT loosened);
    # the head has its OWN stem (a stemless hollow head is a WHOLE note, or a
    # whole rest boxed as a head, never a half -- it keeps the 2.23 narrowing
    # below); and NOTHING is on that stem, each part READ and none assumed:
    # no beam stroke joined to it (`strokes_before_hollow`, the readings a
    # hollow head's fixed-zero hides), no attached flag box, no hook at the
    # tip (a tip nobody measured is "cannot tell"), and a CV beam reader that
    # LOOKED (`_beam_reader_looked`) -- a cell with no beam at all is
    # `ran_empty`, not `reader_declined`. A tremolo slash on the stem is NOT
    # a beam (ROADMAP 2.71, built apart); if the beam reader counts one as a
    # stroke this rule stands down, which is the safe direction.
    if ink_hollow and own_stems and not flags \
            and strokes_before_hollow == (0, 0, 0):
        beam_reader = _beam_reader_looked(ev, cell)
        tip_looked, tip_rows = tip_ink, (tip_ink_rows or ())
        if tip_looked is None and beam_reader is not None:
            # `tip_ink` is only asked above where the old spelling of "the
            # reader spoke" held; ask it here for a cell that ran empty.
            tip_looked, tip_rows = _stem_tip_flag_ink(ev, cell, own_stems,
                                                      side)
        if beam_reader is not None and tip_looked is False:
            used.append(fill_row.id)
            used.extend(r.id for r in tip_rows)
            t, add = 2.0, 2.0
            for _ in range(n_dots):
                add /= 2.0
                t += add
            return Ruling(
                value={"beats": _scale(t, ratio, ev), "written": t,
                       "dots": n_dots, "beam_levels": 0,
                       "head_fill": "half"},
                reason="hollow_head_bare_stem", used=tuple(used),
                detail={**shared, "beam_reader": beam_reader,
                        "stem_tip_hook": False,
                        "notehead_ink": fill_row.detail or {}})

    if beam_evidence == "none_over_this_note" and ink_hollow:
        ink_detail = fill_row.detail or {}
        used.append(fill_row.id)
        cands = []
        for fill_base, name, support in (
                (base, "black", 1.0),
                (2.0, "half", 2.0),
                (4.0, "whole", 1.0)):
            t, add = fill_base, fill_base
            for _ in range(n_dots):
                add /= 2.0
                t += add
            cands.append(Candidate(
                value={"beats": _scale(t, ratio, ev), "written": t,
                      "dots": n_dots, "beam_levels": 0,
                      "head_fill": name},
                # ⚠️ SUPPORT, NOT PROBABILITY, same convention as
                # every other branch above: `half` outranks the
                # always-available detector reading because it is
                # the single-step misread §17b's own crops show
                # (a lone quarter-valued chord in a 2/4 bar); `whole`
                # is the rarer two-step misread and ranks with the
                # detector's own reading, not above it.
                support=support))
        return Ruling.narrow(cands, "head_fill_from_ink",
                             used=tuple(used), **shared,
                             notehead_ink=ink_detail)

    return Ruling(value={"beats": scaled, "written": total,
                         "dots": n_dots, "beam_levels": levels},
                  reason="head_and_marks", used=tuple(used), detail=shared)


def _rest_slot(ev: Evidence, box_rows) -> Tuple[Optional[float], Dict[str, Any],
                                                List[str]]:
    """This rest's centre as a staff step, in `WHOLE_REST_STEP`'s own frame.

    ⚠️ `_staff_step` IS CALLED, NOT COPIED. It is the function
    `adjudicate_notehead_is_a_whole_rest` measures the mirror case with -- *is
    this ink the detector called a notehead actually a whole rest* -- and the
    two questions are one measurement asked from opposite sides. A second
    spelling here would be free to answer differently about the same ink on
    the same page, and a reader would have no way to tell the drift from a
    reading fault.

    ⚠️ PAGE PIXELS, and the frame control is that there is no other frame
    available: `Q.GLYPH_BOX` carries `bbox_page_px` BESIDE its canonical box
    and omits it rather than inventing one, `Q.STAFF_LINES` and
    `Q.STAFF_SPACING` are filed in the page frame, and a canonical box --
    measured inside one cell rescaled so the staff span is constant -- cannot
    be compared with a staff's own lines at all. Where the page box is missing
    this returns `None` and the caller leaves the class's reading alone.

    Returns `(step, detail, used_row_ids)`; `step` is `None` where the
    measurement could not be made, and `detail` says which input was missing.
    """
    page_box = None
    used: List[str] = []
    for r in box_rows:
        page_box = (r.detail or {}).get("bbox_page_px") or page_box
    if not page_box:
        return None, {"slot": "no_page_frame"}, used

    staff = ev.subject.at(Kind.STAFF)
    lines = ev.rows(Q.STAFF_LINES, scope=Scope.SELF_AND_ANCESTORS,
                    subject=staff)
    space = ev.rows(Q.STAFF_SPACING, scope=Scope.SELF_AND_ANCESTORS,
                    subject=staff)
    if not lines or not space:
        return None, {"slot": ABSTAIN.NO_STAFF_GEOMETRY}, used
    step = _staff_step(page_box, lines[-1].value, space[-1].value)
    if step is None:
        return None, {"slot": ABSTAIN.NO_STAFF_GEOMETRY}, used
    used = [lines[-1].id, space[-1].id]

    detail: Dict[str, Any] = {"slot": "measured", "staff_step": round(step, 3)}
    # ⚠️⚠️ RECORDED HERE, DECIDED NOWHERE -- AND THE RESTRAINT IS THE POINT.
    # A staff is 8 half-steps tall in this frame (bottom line 0, top line 8),
    # so a rest measuring outside that stands on ink the cell reached but the
    # staff does not own: the measure cell is padded 4 staff spaces (6 where
    # the neighbour is far) and on a conductor's page that reaches the NEXT
    # STAFF'S ink (CLAUDE.md §10). Measured: 276 of the 433 rests that land on
    # neither convention are outside their own staff -- 186 of Breitkopf's 235
    # clustered at step -7.3, which is the next staff down, not a slot error.
    #
    # ⚠️ IT MUST NOT BECOME A SECOND ABSTAIN REASON. *Which staff owns this
    # ink* is `glyph_owner`'s contest, resolved by ladder, then range, then
    # distance, and a resolved contest DROPS the loser. A duration decision
    # inventing an ownership verdict would be a second, weaker copy of that
    # contest wearing a rhythm decision's name. So the fact goes on the record
    # beside the step and the reason word stays one.
    detail["outside_its_own_staff"] = (
        "below" if step < 0.0 else "above" if step > 8.0 else None)
    # ⚠️⚠️ `Q.REST_POSITION` IS **NOT** READ HERE, AND THE REASON IS A
    # MEASUREMENT AND A TOOL BLIND SPOT, NOT AN OVERSIGHT.
    #
    # `reach.py` names `adjudicate_duration` as that quantity's FIRST
    # CONSUMER, and on the face of it this is the day the entry comes out:
    # `positions._rest_discriminator` measures which EDGE of the rectangle is
    # nearer a line and how decisively (`attach_margin`), which is strictly
    # more of the convention than a centre is. Two things stop it.
    #
    #   1. It files ZERO rows on ALL THREE acceptance records, measured
    #      (`probe/rest_slot_and_flag_join.py`): `OMR_FAMILY_POSITIONS` is
    #      DEFAULT OFF. A rule resting on it would be inert exactly where it
    #      is needed -- CLAUDE.md §6b, reach before accuracy.
    #   2. Declaring it in `wants` opens a NEW finding on `inventory --check`
    #      -- *"duration wants 'rest_position', which no gather site observes
    #      and no decision produces"* -- because `inventory._producers` walks
    #      the AST of `gather.py` AND NOTHING ELSE, so every quantity
    #      `positions.py` observes is invisible to it. That is a blind spot in
    #      the tool, and closing it is a change to a derived check, which is
    #      its own roadmap item and not this one. Suppressing the finding with
    #      a `KNOWN_GAPS` entry would be worse: a known entry is a reason a
    #      gap EXISTS, never a reason one is acceptable.
    #
    # So the slot is measured from the box and the staff, which every record
    # carries. REMOVE THIS NOTE the day either constraint goes.
    return step, detail, used


#: The three answers the slot can give, spelled as
#: `benchmarks/omr-shape-role-2026-09/probe/role_disagreement.py` spells them,
#: so the rule's census and the audit's table use ONE vocabulary.
#:
#: ⚠️⚠️ `class_not_contradicted` IS NOT `the slot confirms the class`, and the
#: weaker word is the true one. Each class's band is bounded only on the side
#: the other convention lies on (see `_rest_slot_verdict`), so ink displaced
#: AWAY from both slots -- 97 Breitkopf and 13 Litolff rests standing wholly
#: ABOVE the staff they are filed on -- falls in here rather than in a
#: disagreement bucket. Calling that `agrees` would be this rule claiming
#: corroboration it has not got, and 2.12b-cal made the word truer still: the
#: whole-rest band now reaches a step and a third below its slot, so a great
#: deal of what it covers is ink it can say nothing against.
SLOT_NOT_CONTRADICTED = "class_not_contradicted"
SLOT_OTHER = "lands_on_the_other_convention"
SLOT_NEITHER = "lands_on_neither_convention"


def _rest_slot_verdict(name: str, step: Optional[float]) -> Optional[str]:
    """Which of the three the slot says -- or `None` where nothing was measured.

    ⚠️⚠️ **ROADMAP 2.12b-cal: THE BANDS ARE MEASURED, AND EACH CLASS IS
    BOUNDED ONLY ON THE SIDE THE OTHER CONVENTION LIES ON.** 2.12b asked
    *which of two slots one line apart is this ink nearer*, with a slack of
    half the gap -- a comparison whose answer is fixed by the convention's two
    nominal lines and cannot be widened past 1.0 without going silent
    everywhere. Sean adjudicated the rows it fired on: **ten of ten are whole
    rests**, at steps 4.16-4.713. So the comparison was reading a real
    population's low tail as a role error.

    What replaced it is a BAND per class, from the plate:

      * a `restWhole` is contradicted only BELOW
        `WHOLE_REST_STEP - REST_SLOT_TOLERANCE_WHOLE` (5.5 - 1.35 = 4.15) --
        the extent of the print-confirmed whole-rest population;
      * a `restHalf` only ABOVE
        `HALF_REST_STEP + REST_SLOT_TOLERANCE_HALF` (4.5 + 0.5 = 5.0) --
        NOT measured, because these plates print 3 half rests inside a staff.

    ⚠️ AND NO EDGE ON THE FAR SIDE, WHICH IS A CONVENTION ARGUMENT AND NOT A
    TOLERANCE CHOICE. There is no third rest convention above the whole rest's
    slot or below the half rest's, so ink there is DISPLACED, not AMBIGUOUS,
    and displacement is not this decision's question -- 111 confirmed rests
    stand outside their own staff altogether and `glyph_owner` owns that
    contest. An upper edge on the whole band would convert 2-3% of a
    print-confirmed population into abstentions to answer a question nothing
    asked.

    ⚠️ `other` AND `neither` ARE TWO FACTS THAT MUST NOT COLLAPSE. Ink landing
    where the OTHER convention puts a rest is a role error the geometry could
    repair; ink landing on NEITHER is a rectangle standing where no rest of
    either kind can hang, which is a weaker claim and a different finding. The
    other band's far edge is carried over from the whole rest's own measured
    tolerance -- the two glyphs are the same rectangle and whatever displaces
    one displaces the other -- and it only ever bounds a NARROWING, never
    creates a DECISION.

    ⚠️ THE AUDIT PROBE NO LONGER AGREES WITH THIS FUNCTION, AND THAT IS
    DELIBERATE. `benchmarks/omr-shape-role-2026-09/probe/role_disagreement.py`
    `f_rest_whole_half` keeps the nominal 0.5 because it is the 2.12 AUDIT's
    frozen measurement, and its 134 / 433 split is the population this
    calibration was derived against; a probe rewritten to match the rule it
    priced would be a probe that can no longer price it.
    `probe/rest_slot_calibration.py` records both verdicts per row for exactly
    this reason.
    """
    slot = _REST_SLOT_BY_CLASS.get(name.lower())
    if slot is None or step is None:
        return None
    if slot == WHOLE_REST_STEP:
        if step >= WHOLE_REST_STEP - REST_SLOT_TOLERANCE_WHOLE:
            return SLOT_NOT_CONTRADICTED
        return (SLOT_OTHER
                if step >= HALF_REST_STEP - REST_SLOT_TOLERANCE_WHOLE
                else SLOT_NEITHER)
    if step <= HALF_REST_STEP + REST_SLOT_TOLERANCE_HALF:
        return SLOT_NOT_CONTRADICTED
    return (SLOT_OTHER if step <= WHOLE_REST_STEP + REST_SLOT_TOLERANCE_WHOLE
            else SLOT_NEITHER)


def _rest_ruling(ev: Evidence, rest_rows) -> Ruling:
    """A rest's value is its SHAPE, and for two of the classes its SLOT.

    ⚠️⚠️ ROADMAP 2.12b. `restWhole` and `restHalf` are THE SAME RECTANGLE and
    differ only in which line they touch and on which side -- a whole rest
    HANGS below the fourth line from the bottom, a half rest SITS on the
    third. The registry says so in terms: *the vertical slot is the rest's
    IDENTITY, not decoration -- NO shape, size or aspect-ratio classifier can
    ever separate a whole rest from a half rest.* So the detector deciding
    between them is reporting something it cannot know, and this function
    used to take that report as the value.

    It no longer does. The slot is MEASURED (`_rest_slot`) and the class
    becomes the corroborating witness, recorded beside it:

      * the measurement does not contradict the class -> DECIDED exactly as
        before, with `slot_says: "class_not_contradicted"` on the record --
        the weaker word, deliberately, because each band is bounded only on
        the side facing the other convention and ink displaced away from BOTH
        slots also lands here;
      * the rectangle lands on the OTHER convention -> NARROWED over both
        values, the measured one first. Not flipped: see the branch's own
        note -- a bowed plate and multi-voice displacement both move a rest
        off its slot, and EXPORT already refuses to argmax a narrowing;
      * it lands on NEITHER -> ABSTAIN. No fallback to the class, because the
        class is the guess the ink has just contradicted.

    ⚠️⚠️ ROADMAP 2.12b-cal, 2026-09-23 -- **THE BANDS CAME FROM THE PLATES,
    NOT FROM THE CONVENTION'S NOMINAL LINES.** 2.12b's slack was half the gap
    between the two slots, so the rule contradicted a `restWhole` below step
    4.75; Sean adjudicated ten of the rows that fired and **all ten are whole
    rests**, measured at 4.16-4.713. The print-confirmed whole-rest population
    (n = 3,259 over the three acceptance records, p5 5.01 / p50 5.41 / p95
    5.91, reaching to 4.16) is one continuous distribution with **no gap
    anywhere through the half rest's slot** -- and the half-rest population
    that would have to separate from it is **3 rows inside a staff in the
    whole corpus**. So the two families do not separate on this repertoire,
    and `REST_SLOT_TOLERANCE_WHOLE` says by how much. 124 of the 134 rows
    2.12b narrowed are DECIDED whole here; the slot's remaining claim is the
    ~40 rows a step or more below even that.

    ⚠️ ONLY THOSE TWO CLASSES. Every other rest names its value by its shape
    and no slot can speak to it; `_REST_SLOT_BY_CLASS` holds the whole domain.

    ⚠️ THE TABLE IS `rhythm._REST_DURATIONS`, IMPORTED RATHER THAN RESTATED.
    It is the paid-for mapping, including the two entries it deliberately
    omits -- `restHBar` / `restHNr` are MULTI-MEASURE REST INDICATORS and name
    no single value, so the lookup returns None and this abstains with a
    reason instead of inventing one.

    ⚠️ A TUPLET DOES NOT SCALE A REST HERE, and that is a measured position
    rather than an omission: pairing a rest to a beam group needs a signal the
    beam box does not carry, so the legacy reader leaves rests out of the
    ratio and so does this. A triplet whose middle member is a rest therefore
    comes out long; that is the honest reading of the evidence available, and
    it is recorded (`tuplet_in_cell`) so a later decision can see the case
    without re-deriving it.

    ⚠️ AND THE BAR-LENGTH CONVENTION IS NOT HERE. A lone whole rest stands for
    the BAR whatever the meter -- 90.3% of wrong rest durations on the scan
    gate are exactly that -- but it is a fact about the CELL and the METER,
    not about the glyph, so it belongs to EVALUATE where the meter is settled.
    See `consequences.size_measure_rest`.
    """
    from ...rhythm import _rest_duration

    row = max(rest_rows, key=lambda r: (r.score or 0.0))
    found = _rest_duration(str(row.value))
    if found is None:
        return Ruling.abstain("unreadable_rest", rest=str(row.value),
                              note="multi-measure indicator: names no single "
                                   "value")
    base, written_type = found

    # ⚠️ THE SAME READ A NOTEHEAD MAKES, AND IT USED TO BE `ev.rows(Q.AUG_DOT)`
    # ON THE REST'S OWN GLYPH SUBJECT -- the exact fault fixed for noteheads,
    # in this same function, one branch over: GATHER files a dot at the DOT's
    # subject, so asking the rest's own subject for one returns nothing and
    # every dotted rest read as undotted. Measured over the three documents,
    # 848 `aug_dot` rows attach 752 to a notehead and exactly ONE to a rest,
    # so this is CONSISTENCY rather than payoff -- what it removes is a module
    # that dots noteheads and silently not rests, which is worse than the
    # even gap it replaced.
    cell = ev.subject.at(Kind.CELL)
    box = ev.rows(Q.GLYPH_BOX)
    rest_box = _xywh_head(box[-1].value) if box else None
    space_row = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS,
                        subject=cell)
    space = float(space_row[-1].value) if space_row else None
    dots = _attached_dots(ev, cell, rest_box, space)
    used = [row.id] + [r.id for r in dots]
    if box:
        used.append(box[-1].id)
    if space_row:
        used.append(space_row[-1].id)
    total, add = base, base
    for _ in range(len(dots)):
        add /= 2.0
        total += add

    ratio = ev.verdict(Q.TUPLET_RATIO, subject=ev.subject.at(Kind.CELL))
    detail: Dict[str, Any] = {
        "rest": str(row.value), "written_type": written_type,
        "tuplet_in_cell": ratio is not None and ratio.value is not None}

    # ── ROADMAP 2.12b — THE SLOT DECIDES; THE CLASS CORROBORATES ────────────
    step, slot_detail, slot_used = _rest_slot(ev, box)
    detail.update(slot_detail)
    used.extend(slot_used)
    slot = _rest_slot_verdict(str(row.value), step)
    detail["slot_says"] = slot
    if slot is not None:
        detail["slot_convention"] = {
            "restWhole": WHOLE_REST_STEP, "restHalf": HALF_REST_STEP,
            # ⚠️ BOTH, AND NAMED APART, because one is MEASURED HERE from the
            # print-confirmed population (2.12b-cal) and the other is the
            # convention's own midpoint on a plate that prints nothing to
            # measure. A record that carried one number could not say which.
            "tolerance_below_whole_half_steps": REST_SLOT_TOLERANCE_WHOLE,
            "tolerance_above_half_half_steps": REST_SLOT_TOLERANCE_HALF,
            "whole_band_from": round(
                WHOLE_REST_STEP - REST_SLOT_TOLERANCE_WHOLE, 3),
            "half_band_to": round(
                HALF_REST_STEP + REST_SLOT_TOLERANCE_HALF, 3),
            "frame": "bottom line 0, one step per half space, up positive"}

    if slot == SLOT_NEITHER:
        # ⚠️ ABSTAIN, AND THE REST IS HELD OUT RATHER THAN VALUED. This is a
        # rectangle standing where NEITHER convention puts a rest, so the one
        # measurement that can separate a whole rest from a half rest has
        # separated nothing -- and the class cannot be fallen back on, because
        # the class is precisely the guess this ink has just contradicted.
        # CLAUDE.md §2 rule 8: a fallback never converts *cannot tell* into an
        # answer, and 4.0 quarters of silence is a very loud answer.
        #
        # ⚠️ IT IS THE BIGGER BUCKET AND THE WEAKER CLAIM -- 433 rows against
        # 134 on the two scans -- and `benchmarks/omr-shape-role-2026-09/`
        # §5 says in terms that it is a DIFFERENT finding. Crops go to Sean
        # (`out/print/`); nothing here reads the population as repaired.
        return Ruling.abstain("rest_stands_where_no_rest_hangs", **detail)

    if slot == SLOT_OTHER:
        # ⚠️ NARROWED, NOT FLIPPED, AND THE REFUSAL TO FLIP IS THE POINT.
        # The geometry is the measurement that can separate these two glyphs
        # and the class is a guess from a crop -- but the convention's own
        # registry entry names two killers for the absolute slot on this
        # repertoire: a scanned staff tilts and bows up to a whole step, and
        # *in multi-voice writing rests are displaced from their default
        # position*, which destroys the absolute-position discriminator
        # outright. Deciding here would be a default flipped on agreement
        # with our own reading, which CLAUDE.md §2 rule 5 forbids until a
        # print check says otherwise. EXPORT already refuses to argmax a
        # narrowing, so the bar is held out and counted rather than filled
        # with either answer.
        #
        # ⚠️ THE ORDER IS THE CLAIM. `support` is in this decision's own units
        # and is not a probability: the MEASURED slot outranks the class,
        # which is the whole of "shape from the class, role from the geometry"
        # said as a number a later stage can read.
        other_name = ("restHalf" if str(row.value).lower() == "restwhole"
                      else "restWhole")
        other = _rest_duration(other_name)
        cands = [Candidate(value={"beats": total, "written": total,
                                  "dots": len(dots), "beam_levels": 0,
                                  "is_rest": True, "rest": str(row.value)},
                           support=1.0)]
        if other is not None:
            o_total, add = other[0], other[0]
            for _ in range(len(dots)):
                add /= 2.0
                o_total += add
            cands.append(Candidate(
                value={"beats": o_total, "written": o_total,
                       "dots": len(dots), "beam_levels": 0, "is_rest": True,
                       "rest": other_name},
                support=2.0))
        return Ruling.narrow(cands, "rest_slot_contradicts_class",
                             used=tuple(used),
                             **{**detail, "slot_prefers": other_name})

    return Ruling(
        value={"beats": total, "written": total, "dots": len(dots),
               "beam_levels": 0, "is_rest": True},
        reason="rest_class", used=tuple(used), detail=detail)


def _scale(total: float, ratio, ev: Evidence) -> float:
    if ratio is not None and isinstance(ratio.value, dict):
        num, den = ratio.value.get("actual"), ratio.value.get("normal")
        if num and den and ev.subject.glyph in (ratio.value.get("members") or []):
            return total * den / num
    return total


def _tuplet_marker_refused(ev: Evidence, mark) -> bool:
    """Did a human strike out the glyph THIS `Q.TUPLET_MARKER` row IS?

    ROADMAP 3.4g-4. Unlike the key-signature marker, `Q.TUPLET_MARKER` is
    gathered on its own glyph subject, so the refusal is read there directly
    and no frame/class/point join is needed.
    """
    refusal = ev.verdict(Q.TUPLET_MARKER_IS_NOT_A_MARKER, subject=mark.subject)
    return (refusal is not None and refusal.outcome is Outcome.DECIDED
            and refusal.value is True)


@decision(
    quantity=Q.TUPLET_RATIO,
    checkable=Checkable.MIXED,
    checked_by=(
        '"bar sum: a wrong ratio breaks it"',
        '"the group must hold exactly as many notes as the digit claims"',
    ),
    implicates=(Q.TUPLET_RATIO, Q.DURATION, Q.METER),
    composed_from=(Q.TUPLET_MARKER, Q.BEAM_STROKE, Q.NOTEHEAD_CLASS,
                   Q.TUPLET_MARKER_IS_NOT_A_MARKER),
    scope=Kind.CELL,
    wants=(Q.TUPLET_MARKER, Q.BEAM_STROKE, Q.NOTEHEAD_CLASS,
           Q.TUPLET_MARKER_IS_NOT_A_MARKER),
    reasons=("digit", "bracket", "no_marker", "wrong_member_count",
             "ambiguous_bracket"),
    mode=Mode.ADDITIVE,
    subjects_from=Q.TUPLET_MARKER,
)
def adjudicate_tuplet(ev: Evidence) -> Ruling:
    """A triplet's noteheads are ORDINARY eighths; the marker says they take
    two's worth of time.

    ⚠️ TWO MARKERS, READ DIFFERENTLY, BECAUSE THEY SIT DIFFERENTLY. The DIGIT
    is printed over the MIDDLE of its group, so its centre must fall inside
    the group's span. The BRACKET ENCLOSES the group, so the group must fall
    inside the BRACKET's span -- detected brackets are far wider than the
    notes they cover (one measured at 1846px over a 478px group) and testing a
    bracket's CENTRE rejects every one of them.

    ⚠️ IT ABSTAINS RATHER THAN GUESSING, deliberately and in four ways:
    only `3:2` (5/6/7 each need their own normal-count convention and none
    occurs in anything measured); the group must have EXACTLY as many notes as
    the digit claims, so a triplet written quarter-plus-eighth is left alone;
    an unnumbered bracket is read only over a group of exactly three and only
    when it covers exactly one group in the cell; and rests are NOT scaled,
    because pairing a rest to a beam group needs a signal the beam box does
    not carry.
    """
    # ⚠️ SELF_AND_DESCENDANTS, not EXACT. A tuplet marker is detected as a
    # GLYPH and the ratio is a fact of the CELL, so a cell-scope decision
    # reading at EXACT scope finds nothing and reports `no_marker` -- which
    # reads exactly like a cell that prints no tuplet. Found by the test
    # asserting a REASON rather than just an outcome.
    #
    # ⚠️ ROADMAP 3.4g-4: A REFUSED MARKER READS EXACTLY LIKE NO MARKER AT ALL,
    # not like a cell whose digit disagrees with its bracket. `Q.TUPLET_
    # MARKER_IS_NOT_A_MARKER` is decided on the marker's own glyph subject
    # (`m.subject`) -- the same one `Q.TUPLET_MARKER` is gathered on -- so, as
    # with the flag, no cross-quantity join is needed.
    marks = [m for m in ev.rows(Q.TUPLET_MARKER, scope=Scope.SELF_AND_DESCENDANTS)
             if not _tuplet_marker_refused(ev, m)]
    if not marks:
        return Ruling.abstain("no_marker")

    heads = sorted(ev.rows(Q.NOTEHEAD_CLASS, scope=Scope.SELF_AND_DESCENDANTS),
                   key=lambda r: r.subject.glyph or 0)
    if len(heads) != 3:
        # ⚠️ Not a failure -- the honest answer where the group is not the
        # shape the marker claims. `3:2` over four notes is somebody else's
        # tuplet or a misread marker, and guessing would corrupt the bar.
        return Ruling.abstain("wrong_member_count", n_heads=len(heads))

    digits = [m for m in marks if not m.detail.get("is_bracket")]
    brackets = [m for m in marks if m.detail.get("is_bracket")]

    if digits:
        reason = "digit"
        marker = digits[0]
    elif len(brackets) == 1:
        reason = "bracket"
        marker = brackets[0]
    else:
        return Ruling.abstain("ambiguous_bracket", n_brackets=len(brackets))

    return Ruling(value={"actual": 3, "normal": 2,
                         "members": [h.subject.glyph for h in heads]},
                  reason=reason,
                  used=tuple([marker.id] + [h.id for h in heads]),
                  detail={"marker": str(marker.value)})


#: A chord's noteheads sit within this fraction of a NOTEHEAD WIDTH of each
#: other in x. (A-EVENT-1)
#:
#: ⚠️ NOT A NEW CONSTANT — it is `voicing.group_chords_in_measure`'s own
#: default, reproduced so the record's grouping and the exporter's are ONE
#: rule rather than two that can drift. Adaptive rather than a pixel count:
#: 0.6 of the MEAN notehead width in the bar, wide enough for the stem-shifted
#: seconds of a chord and narrow enough to keep a rapid passage's notes apart.
EVENT_X_TOLERANCE_WIDTHS = 0.6

#: Fallback when the bar holds no notehead to measure a width from — the same
#: number, and the same reason, as the legacy fallback.
EVENT_X_TOLERANCE_FALLBACK_PX = 30.0


def _box_of(rows):
    """`glyph_box` value is (class, x, y, w, h)."""
    out = {}
    for r in rows:
        val = r.value
        if not isinstance(val, (list, tuple)) or len(val) < 5:
            continue
        _name, x, _y, w, _h = val[0], val[1], val[2], val[3], val[4]
        sub = r.subject
        if sub.glyph is None:
            continue
        out[sub.glyph] = (float(x) + float(w) / 2.0, float(w))
    return out


@decision(
    quantity=Q.EVENT,
    checkable=Checkable.CHECKABLE,
    checked_by=(
        '"the bar sum: one event contributes ONE duration, so a bar of events must equal the meter"',
    ),
    # ⚠️ THE GROUPING IMPLICATES ITSELF. A bar that does not sum may hold a
    # wrong duration, a wrong meter -- or two notes I merged that are not
    # simultaneous, or one chord I split in two. A check that implicated only
    # the durations would have quietly decided the grouping was innocent.
    implicates=(Q.EVENT, Q.DURATION, Q.METER),
    composed_from=(Q.GLYPH_BOX,),
    scope=Kind.CELL,
    # ⚠️ `Q.STEM` AND `Q.STEM_DIRECTION` ARE BOTH DECLARED AND THEY ARE NOT
    # THE SAME INPUT. The first is read only to REPORT the guard's input state
    # (`stem_evidence`); the second is what the guard actually runs on. A bar
    # whose stems were read and whose directions all abstained is a real state
    # and the two fields are how it is told from a bar with no stems at all.
    wants=(Q.GLYPH_BOX, Q.NOTEHEAD_CLASS, Q.REST, Q.STEM, Q.STEM_DIRECTION),
    reasons=("x_clustered", "nothing_to_group"),
    mode=Mode.ADDITIVE,
    subjects_from=(Q.NOTEHEAD_CLASS, Q.REST),
)
def adjudicate_event(ev: Evidence) -> Ruling:
    """Which glyphs of this bar sound TOGETHER.

    ⚠️ THIS EXISTED ONLY AT SERIALISATION TIME UNTIL 2026-09-09.
    `group_chords_in_measure` was called from exactly one place —
    `export._events` — so every stage before EXPORT counted each chord member
    as a separate time-advancing event. That includes
    `consequences.reconcile_duration`, the pipeline's own bar-sum check, which
    therefore could not match the meter on any bar holding a chord: 38.2% of
    the bars on one measured page, where the double-count destroyed 5 of the
    18 bars that landed exactly on the printed meter.

    ⚠️ THE POSITION IS A MEASUREMENT; THE GROUPING IS NOT. `Q.GLYPH_BOX`
    already carries every glyph's x — the ingredient was on the record all
    along and nothing read it — but *"these are simultaneous"* is an
    interpretation of those positions under a tolerance, so it is a decision.

    ⚠️ A REST IS ITS OWN EVENT. It occupies time alone; nothing sounds with
    silence.

    ⚠️⚠️ THE DIVISI GUARD IS UNAVAILABLE HERE, AND IT IS RECORDED RATHER THAN
    OMITTED. The legacy rule additionally refuses to merge two noteheads at
    the same x whose STEMS POINT OPPOSITE WAYS — two divisi voices, not one
    chord — an audit follow-up from 2026-07. `Q.STEM` is a declared stub on
    this path, so that tier cannot run, and `_directions_conflict` is
    consequently already inert in `export._events` too (it never sets
    `stem_direction`). So this reproduces what the exporter does TODAY,
    exactly; it does not reproduce what the legacy rule can do with stems.
    The state of `Q.STEM` is read and reported per cell so the missing tier is
    on the record and not in a comment.
    """
    heads = ev.rows(Q.NOTEHEAD_CLASS, scope=Scope.SELF_AND_DESCENDANTS)
    rests = ev.rows(Q.REST, scope=Scope.SELF_AND_DESCENDANTS)
    boxes = _box_of(ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS))

    head_ids = sorted({r.subject.glyph for r in heads
                       if r.subject.glyph is not None and r.subject.glyph in boxes})
    rest_ids = sorted({r.subject.glyph for r in rests
                       if r.subject.glyph is not None and r.subject.glyph in boxes})
    if not head_ids and not rest_ids:
        return Ruling.abstain("nothing_to_group")

    # The tolerance is measured off THIS bar's own noteheads.
    if head_ids:
        widths = [boxes[g][1] for g in head_ids]
        tol = (sum(widths) / len(widths)) * EVENT_X_TOLERANCE_WIDTHS
    else:
        tol = EVENT_X_TOLERANCE_FALLBACK_PX

    # ⚠️⚠️ THE DIVISI GUARD IS LIVE, AND IT WAS `not_implemented` UNTIL ITS
    # INPUT EXISTED. A real chord's noteheads share ONE physical stem, so two
    # heads at nearly the same x whose stems point OPPOSITE ways are two
    # simultaneous voices and not one chord -- x-only grouping merged them and
    # then mode-voted one duration over the pair, corrupting both. That is the
    # legacy rule (`voicing._directions_conflict`, an audit follow-up from
    # 2026-07) and it is reproduced here rather than imported, because the
    # legacy function reads a detection dict and this reads the record.
    #
    # ⚠️ AN UNKNOWN DIRECTION NEVER BLOCKS A MERGE, exactly as it does not
    # there. A head whose stem the CV rung missed must behave as it did before
    # this quantity existed; only an explicit CONFLICT separates.
    directions = {}
    for g in head_ids:
        sub = Subject(Kind.GLYPH, page=ev.subject.page,
                      system=ev.subject.system, staff=ev.subject.staff,
                      cell=ev.subject.cell, glyph=g)
        d = ev.verdict(Q.STEM_DIRECTION, subject=sub)
        if d is not None and d.outcome == "decided":
            directions[g] = d.value

    def _conflicts(g, grp) -> bool:
        mine = directions.get(g)
        if not mine:
            return False
        theirs = {directions[i] for i in grp if directions.get(i)}
        return bool(theirs) and mine not in theirs

    groups = []
    separated = 0
    for g in sorted(head_ids, key=lambda i: boxes[i][0]):
        x = boxes[g][0]
        target = None
        blocked = False
        # Backward scan: groups are created in non-decreasing x, so once one
        # is further than the tolerance every earlier one is too.
        for grp in reversed(groups):
            gx = sum(boxes[i][0] for i in grp) / len(grp)
            if abs(x - gx) > tol:
                break
            if _conflicts(g, grp):
                # ⚠️ `continue`, NOT `break` -- a divisi split creates two
                # groups at nearly the same x, back to back, so the group this
                # head belongs to may be the one BEHIND the conflicting one.
                # The legacy scan spells it the same way and the two must
                # agree.
                blocked = True
                continue
            target = grp
            break
        if target is None:
            groups.append([g])
            if blocked:
                separated += 1
        else:
            target.append(g)

    events = [{"glyphs": sorted(grp),
               "x": round(sum(boxes[i][0] for i in grp) / len(grp), 2),
               "kind": "chord"} for grp in groups]
    events += [{"glyphs": [g], "x": round(boxes[g][0], 2), "kind": "rest"}
               for g in rest_ids]
    events.sort(key=lambda e: (e["x"], e["glyphs"][0]))

    stem_state = ev.state(Q.STEM, scope=Scope.SELF_AND_DESCENDANTS)
    chorded = sum(1 for e in events if len(e["glyphs"]) > 1)
    return Ruling(
        value={"events": events},
        reason="x_clustered",
        used=tuple(r.id for r in heads) + tuple(r.id for r in rests),
        detail={"n_events": len(events),
                "n_glyphs": len(head_ids) + len(rest_ids),
                "n_chords": chorded,
                "tolerance_px": round(tol, 2),
                # ⚠️ IT SAID `not_implemented` UNTIL `Q.STEM_DIRECTION`
                # EXISTED, and the field was written that way on purpose: an
                # earlier draft wrote `divisi_guard: "ran"` wherever stem rows
                # merely EXISTED, which claims a check that never happened.
                # Now it reports what the guard actually DID -- and it still
                # reports the state of its input beside it, because a guard
                # that ran over a bar whose stems were never read has
                # separated nothing and must not read as a clean bill.
                "divisi_guard": ("ran" if directions else
                                 "no_direction_decided"),
                "divisi_separated": separated,
                "directions_decided": len(directions),
                "stem_evidence": stem_state.value},
    )


#: A meter must be agreed by this share of the staves that SPOKE. (A-METER-1)
#: ⚠️ Not tuned here, but not arbitrary either: over an 11-source corpus every
#: one of the 12 correct readings was agreed by 0.909 of its system or more,
#: and the single WRONG reading by exactly 0.500.
METER_AGREEMENT_FLOOR = 0.70

#: ...and the share of the SYSTEM'S OWN STAVES that must have read it at all.
#: (A-METER-2)
#:
#: ⚠️⚠️ THE OTHER HALF OF THE LEGACY RULE, AND DROPPING IT SHIPPED A WRONG
#: METER AT FULL AGREEMENT. `METER_AGREEMENT_FLOOR` divides by the staves that
#: SPOKE, so three spurious readings that happen to agree score 3/3 = 1.0 --
#: `rhythm._dominant_detected_meter` says exactly this in its own docstring:
#: *"two spurious readings that happen to agree are unanimous among
#: themselves"*, and requires `_PROPAGATE_MIN_STAFF_FRACTION = 0.5` of the
#: page's staves as well.
#:
#: Measured on Beethoven 5 / Litolff p.2, whose reference is 2/4 on all 18
#: parts and which PRINTS NO TIME SIGNATURE AT ALL (it opens at bar 17):
#:
#:   * system 1 -- **3 staves of 11** matched a common-time `C`, agreed 1.0,
#:     and the system shipped **4/4**;
#:   * page 1 of the same run -- **12 staves of 12** read the true `2/4`.
#:
#: 3/11 = 0.27 against 12/12 = 1.0, so the floor separates them with room to
#: spare. A meter is printed on EVERY staff of a system; a reading on a
#: handful of them is a misread however much those few agree.
METER_COVERAGE_FLOOR = 0.5


# Carry a DECIDED meter forward onto systems that read none. (`_carry_meter`.)
#
# ⚠️ PROMOTED 2026-10-07 (roadmap 0.2c): this was the flag `OMR_METER_CARRY`,
# default ON since 2026-09-15 (Sean's call); the flag, its predicate and the
# OFF path are REMOVED and the carry always runs. What follows is the record
# of why the carry needs the bars to weigh it, and it is kept because
# `_carry_meter`, `_nearest_read_system` and `A-METER-6` point at it.
#
# ⚠️⚠️ THE CARRY NEEDS THE WEIGHING BECAUSE THE HAZARD IS MEASURED, NOT
# BECAUSE IT IS FEARED.
# A meter is a fact of the MOVEMENT, so a carry is right until a movement
# starts and catastrophic afterwards -- and on the very document the benefit
# was measured on, THE MOVEMENT START READS NOTHING.
#
# Beethoven 5 / Litolff `984073`, one call each:
#
#   * BENEFIT -- p1/s0 decides `2/4` from **12 of 12** staves; p2/s0 reads
#     nothing and p2/s1 reads 3 spurious `C`. Both want p1's answer.
#   * HAZARD -- p17 is the *Andante con moto*, a NEW MOVEMENT printing `3/8`
#     on every staff. All three of its systems abstain `no_evidence`: the
#     template reader RAN on all 20 staves and declined `below_threshold`,
#     because Litolff sets `3` over `8` as heavy nearly-touching digits that
#     do not correlate with the Bravura templates. So an unconditional carry
#     stamps movement 1's `2/4` onto the whole Andante.
#
# Four guards were looked for and each is REFUTED by measurement, not by
# argument:
#
#   1. *"a movement start reads SOME meter, a continuation reads none"* --
#      inverted. The continuations p14-p16 read 1-4 spurious `C`/`4/4`; the
#      movement start reads 0.
#   2. *the KEY SIGNATURE changes at a movement boundary* -- unusable on a
#      scan. Only a handful of staves per system decide a key and they
#      disagree with each other (p14/s1 reads {-5, -3, -1, 2}); the true -4
#      of the Andante is never among them.
#   3. *the printed TEMPO HEADING* -- p17 prints "Andante con moto." three
#      times, and it is the right signal in principle. `direction` yields
#      **0 decided verdicts** in the staged record today, so it cannot be
#      asked.
#   4. *a distance bound* -- DECISIVE. Movement 1 occupies pages 1-16, so a
#      meter read on p1 legitimately governs 16 pages. Any bound under 16
#      truncates a legitimate carry in this document and any bound of 16 or
#      more reaches the Andante. No reach constant separates them.
#
# So the blocking input is named and it is a MOVEMENT-START signal, not a
# tuning constant. (Sean flipped the carry ON anyway on 2026-09-15 and the
# bars weigh it; the movement-start signal itself is still missing.)


# ─────────────────────────────────────────────────────────────────────────────
# A carried meter is WEIGHED, not gated. (A-METER-3)
#
# Sean, 2026-09-09: *"We need probability based decisions with layers of
# information ... this is where the math that can be determined by its own
# equation could be weighed more heavily than information that can only be
# derived. If the measure is what we think it is - does the math of the notes
# make sense. If not then the meter should decrease in probability."*
#
# So the bars do not VETO the carry, they move its standing. A carried meter
# starts with the support of the reading it came from, and every bar it claims
# to govern adds to or subtracts from that, in this module's one sanctioned
# form: signed terms summed against a threshold (`adjudicate.Term`/`tally`).
#
# ⚠️ NOT A PROBABILITY, and the distinction is measured rather than stylistic.
# `adjudicate`'s docstring bans them because the one attempt at calibrated
# identity probabilities reached ECE 0.1277 and failed WORST at the top of the
# range -- a bin promising 0.989 and delivering 0.692. Summed signed terms are
# the same shape without the claim: they order and they threshold, they do not
# assert that a number is a frequency.
#
# ⚠️ WHAT IS CALIBRATABLE HERE, AND IT IS THE INTERESTING PART. That failure
# was diagnosed as the CORPUS, not the estimator -- the tier that would supply
# labels was empty. A bar sum needs no such corpus: it is
# `Checkable.CHECKABLE`, provable against itself on any document with no truth
# file and no human, so this family COULD be genuinely calibrated later from
# the score library alone. Nothing here does that yet.
# ─────────────────────────────────────────────────────────────────────────────

#: What the carry is worth alone: a real reading, voted by every staff of its
#: system -- but on another system, and possibly in another movement.
W_METER_CARRIED = 1.0

#: What one bar that FITS the carried meter is worth, and one that does not.
#:
#: ⚠️ SYMMETRIC, AND DECLARED UNMEASURED. There is a real argument for
#: asymmetry in EACH direction: an agreeing bar is unlikely by chance, while a
#: disagreeing bar is routine because our durations are unreliable -- even on
#: a page whose meter is READ, only half the bars land exactly. The two pages
#: available separate under every ratio tried, so the corpus cannot choose,
#: and a constant a measurement cannot settle is left neutral rather than
#: tuned to n=2.
W_METER_BAR_FITS = 1.0
W_METER_BAR_CONTRADICTS = -1.0

#: The support a carried meter needs before it stands.
#:
#: ⚠️ THE STRUCTURE IS THE CLAIM, NOT THE NUMBER: at these weights TWO net
#: contradicting bars outweigh ANY carry, and no amount of carrying outweighs
#: the bars. That is Sean's ordering made structural -- information checkable
#: by its own arithmetic cannot be outvoted by information merely inherited.
#:
#: At 2.0 a carry also needs at least one net agreeing bar to stand at all, so
#: a page with nothing to check against does not carry (`W_METER_CARRIED`
#: alone is 1.0 and falls short). Measured on Beethoven 5 / Litolff `984073`
#: carrying `2/4`: page 2 (a CONTINUATION, truth 2/4) scores 1 + 8 - 2 = +7;
#: page 17 (the *Andante*, truth 3/8) scores 1 + 1 - 7 = -5.
METER_CARRY_FLOOR = 2.0

#: How many bars must be assessable before the bars may settle anything.
#:
#: ⚠️ A SEPARATE CONSTANT FROM THE FLOOR, DELIBERATELY, and `A-CLEF-6` is why:
#: `MARGIN_FLOOR` there carries two jobs and the file records that a sweep of
#: it moves both behaviours at once. "Is there enough evidence to judge?" and
#: "does the evidence support it?" are two questions, and folding the first
#: into the threshold would hide it.
#:
#: ⚠️ MEASURED, AND IT CLOSES A REAL LEAK. On the *Andante* two of its three
#: systems refuse the carried `2/4` outright (support -3.0 and -1.0), and the
#: third CARRIED IT WRONGLY at support exactly +2.0: one bar that happened to
#: sum to 2.0, nothing contradicting it, landing precisely on the floor. One
#: bar is not a system's worth of evidence -- the same argument
#: `METER_COVERAGE_FLOOR` makes for readings ("two spurious readings that
#: happen to agree are unanimous among themselves"), applied to bars. Page 2's
#: systems have 10 and 9 assessable bars and are untouched.
METER_CARRY_MIN_BARS = 2

#: A bar needs this many staves reading it before it may vote on bar LENGTH.
#: ⚠️ Two staves that agree are not a system; the same "unanimous among
#: themselves" fault `METER_COVERAGE_FLOOR` exists for.
METER_CARRY_MIN_STAVES_PER_BAR = 3


# ─────────────────────────────────────────────────────────────────────────────
# THE BARS MAY NAME A LENGTH ON THEIR OWN. (A-DUR-7)
#
# Sean, 2026-09-09: *"If there is no meter glyph then we have to deal with bar
# sums... We have 12 systems and 10 of them say 4/4 for 6 measures."* And
# A-DUR-6's governing rule: *"If there is no established meter then it must
# derive the most likely meter based off of the order of determination
# above."*
#
# Until now the bars could only CORROBORATE a candidate someone else proposed
# -- a carried meter or a printed glyph. A system with neither had nothing,
# however clearly its own arithmetic spoke.
#
# ⚠️ WHAT THE BARS CAN AND CANNOT SAY, and the split is the whole design. A
# bar sum is a LENGTH in quarter-notes. It is not a meter: 2.0 is `2/4` and
# also `4/8`, and 4.0 is `4/4`, `2/2` and a common-time `C`. So the bars name
# the length and the ENGRAVING is borrowed from a system that actually read
# one -- and where no such system exists the decision says exactly that
# rather than picking a spelling. Naming a form we never saw would be the
# laundered guess this module's own docstring bans.
# ─────────────────────────────────────────────────────────────────────────────

# ⚠️ PROMOTED 2026-10-07 (roadmap 0.2c): `_meter_from_bars` was gated by the
# flag `OMR_METER_FROM_BARS`, default ON since 2026-09-15 (Sean's call, with
# the carry). The flag, its predicate and the OFF path are REMOVED. This rung
# is the one that cannot cross a movement boundary: every term comes from bars
# inside ONE system, so the *Andante* cannot be handed movement 1's `2/4` by
# this route however many pages of it precede. Only the SPELLING reaches back,
# and only where the length already matches.


#: ⚠️⚠️ THERE IS ONE CONSTANT HERE AND THERE WERE TWO. A separate
#: `METER_FROM_BARS_MIN_ASSESSABLE = 4` was written first, on
#: `METER_CARRY_MIN_BARS`'s reasoning that *"is there enough evidence to
#: judge?"* and *"does the evidence support it?"* are two questions and
#: folding the first into the threshold hides it. **On these weights it
#: cannot bind, and a mutation proved it**: a bar is worth 1.0, so support
#: can never reach a floor of 4.0 without four assessable bars, and deleting
#: the constant outright broke no test. It is gone rather than left as
#: decoration -- a gate that cannot fire reads to the next person as a
#: protection that is not there. The reasoning stands and would need weights
#: that separate the two, which n = 24 systems on one document cannot supply.

#: The support a bar-named length needs before it stands, in the same signed
#: currency the carry uses (`W_METER_BAR_FITS` / `W_METER_BAR_CONTRADICTS`,
#: reused rather than restated so the two mechanisms cannot drift apart about
#: what a bar is worth).
#:
#: ⚠️ "THE LONGER THE MORE LIKELY" IS THE ACCUMULATION, NOT A RUN-LENGTH
#: CONSTANT. Each agreeing bar adds 1.0 and each disagreeing bar subtracts
#: 1.0, so a long coherent stretch clears any floor and a short one does not
#: -- which is Sean's ordering without a second threshold to tune.
#:
#: ⚠️ CONSECUTIVENESS IS DELIBERATELY NOT REQUIRED, and that is a measurement
#: rather than a simplification. The literal reading of "for 6 measures" is a
#: RUN of consecutive bars; over the same 24 systems the longest such run
#: is **5** on the one page whose meter is read, **3** on the two that want
#: one, and **1** on the two dense finale systems -- because an unassessable
#: bar (under three staves, or no cross-staff majority) breaks a run without
#: contradicting anything. Requiring consecutiveness would spend the evidence
#: on the page's legibility rather than on its meter.
#:
#: ⚠️ AT 4.0 THE FLOOR IS EXERCISED BY A REAL NEGATIVE. Reached systems score
#: +10 (p.1, meter read, control), +6 and +7 (p.2, truth 2/4, both correct)
#: and **-2** on the *Andante*'s first system, whose four assessable bars
#: read four different lengths. The n is 4 and it is not a sweep.
METER_FROM_BARS_FLOOR = 4.0



def _corroborate(ev: Evidence, candidate: dict) -> dict:
    """Do this system's own bars agree with `candidate`?

    ⚠️ THE BARS NEED ONLY REFUSE A WRONG METER, NOT NAME THE RIGHT ONE, and
    the difference is what makes this usable at all. On the *Andante* the bars
    name NOTHING -- with lone whole rests excluded only 8 of 29 bars reach a
    majority and the true 1.5 gets zero votes, because a movement's opening
    page has most instruments resting and the few that play are the dense ones
    we read worst. They are still perfectly able to say the bar is not 2.0.

    ⚠️⚠️ A LONE WHOLE REST IS NEVER READ HERE, AND "not read" IS STRONGER THAN
    "read then discarded". Two separate reasons:

    * THE CIRCULARITY. An engraver fills an otherwise silent bar with ONE
      centred whole rest whatever the meter, so the glyph stands for THE BAR
      and says nothing about its length -- and the 4.0 we give it is our own
      default *for want of a meter*. Counting it reads that default straight
      back as evidence, and a page of rests would confirm 4/4 for ever.
      Measured on p.17: left in, 13 of 17 agreeing bars vote 4.0.
    * THE PROVENANCE. `size_measure_rest` SUPERSEDES exactly these durations
      using the meter, so merely touching them puts them in the meter's basis
      and the record then reports a genuine fixpoint
      (`UphillConsequence`) -- correctly, because a basis is what a decision
      TOUCHED, not what it finally believed. So the lone rest is identified
      from the EVENT grouping plus the `Q.REST` measurement, and its duration
      verdict is never requested.
    """
    num, den = candidate.get("numerator"), candidate.get("denominator")
    if not num or not den:
        return {"state": "no_candidate"}
    expected = float(num) * 4.0 / float(den)
    return _score_bars(_bar_lengths_for(ev), expected)


def _bar_lengths_for(ev: Evidence) -> dict:
    """{cell_index: [length per staff]} for every bar of this system that can
    speak about its own LENGTH. See `_corroborate` for why a whole rest is
    never read here."""
    whole_rests = {r.subject for r in
                   ev.rows(Q.REST, scope=Scope.SELF_AND_DESCENDANTS)
                   if r.value == "restWhole"}
    bars: dict = {}
    for grouping in ev.verdicts(Q.EVENT, scope=Scope.SELF_AND_DESCENDANTS):
        if grouping.outcome is not Outcome.DECIDED:
            continue
        cell = grouping.subject
        events = (grouping.value or {}).get("events") or []

        def _sub(gi):
            return Subject(Kind.GLYPH, page=cell.page, system=cell.system,
                           staff=cell.staff, cell=cell.cell, glyph=gi)

        # ⚠️ ANY whole rest disqualifies the BAR, not just a lone one. The
        # narrower "only if it is the bar's single event" rule left a real
        # hole: the EVENT grouping and `size_measure_rest`'s own population
        # can disagree about whether a rest is alone (a glyph with no standing
        # duration verdict is an event here and invisible there), so a bar
        # this rule kept was still a bar whose rest the consequence later
        # superseded -- and the record reported the fixpoint. A bar holding a
        # whole rest cannot corroborate a meter that may rewrite it.
        if any(_sub(gi) in whole_rests
               for e in events for gi in (e.get("glyphs") or [])):
            continue
        total = 0.0
        for event in events:
            beats = []
            for gi in event.get("glyphs") or []:
                got = ev.verdict(Q.DURATION, subject=_sub(gi))
                if got is None:
                    continue
                val = (got.value if got.outcome is Outcome.DECIDED
                       else (got.candidates[0].value if got.candidates else None))
                if val:
                    beats.append(float(val.get("beats") or 0.0))
            if beats:
                total += Counter(beats).most_common(1)[0][0]
        if total > 0:
            bars.setdefault(cell.cell, []).append(round(total, 4))
    return bars


def _score_bars(bars: dict, expected: float) -> dict:
    """Signed terms for one candidate meter, over the bars that can speak."""
    terms = []
    agree = disagree = 0
    observed = Counter()
    for cell_index, lengths in sorted(bars.items()):
        if len(lengths) < METER_CARRY_MIN_STAVES_PER_BAR:
            continue
        mode, n = Counter(lengths).most_common(1)[0]
        if n / len(lengths) < 0.5:
            continue                 # the staves do not agree with EACH OTHER
        observed[mode] += 1
        if abs(mode - expected) < 1e-6:
            agree += 1
            terms.append(Term("bar_%d_fits" % cell_index, W_METER_BAR_FITS))
        else:
            disagree += 1
            terms.append(Term("bar_%d_is_%s" % (cell_index, mode),
                              W_METER_BAR_CONTRADICTS))
    if len(terms) < METER_CARRY_MIN_BARS:
        # ⚠️ NOT "carry anyway", and NOT the same row as a carry the bars
        # outweighed. A page with too little to check against is exactly the
        # page where a movement may have started unseen; abstaining is the
        # status quo, carrying unverified is the hazard.
        return {"state": "too_few_assessable_bars",
                "bars_assessable": len(terms),
                "bars_agree": agree, "bars_disagree": disagree,
                "bar_lengths_seen": dict(observed.most_common(6))}
    return {"terms": terms, "bars_agree": agree, "bars_disagree": disagree,
            # ⚠️ WHAT THE BARS THEMSELVES SAY, recorded even though nothing
            # consumes it. On the *Andante* it is the honest answer that they
            # name NOTHING -- 1.0, 3.0 and 5.0 with no mode -- which is a
            # different fact from "they disagree with the carry" and a reader
            # of the record should be able to tell them apart.
            "bar_lengths_seen": dict(observed.most_common(6))}


# ─────────────────────────────────────────────────────────────────────────────
# A METER CHANGE, in Sean's order: the GLYPH opens the question, the MATH
# settles it. (A-METER-4)
#
# Sean, 2026-09-09: *"any time signature glyph should be the heaviest weight
# ... Any glyph registers should be the biggest sign that all measures at that
# point should be viewed as likely a new time signature then does the math add
# up and for how long - the longer the more likely."*
#
# ⚠️ MEASURED, AND IT INVERTED THE RATIONALE I HAD. On Beethoven 5 / Litolff
# p.62 the print changes to 3/4 mid-system. The page prints bar 147, so the
# reference's change at bar 155 is CELL 8 -- and the detector's `timeSig3` +
# `timeSig4` land on cell 8 EXACTLY, while the bar-math anomaly sits at cell 6,
# two bars early and wrong. The glyph is the precise signal; the arithmetic is
# the noisy corroborator.
#
# ⚠️ SO A CHANGE IS NEVER PROPOSED FROM BAR MATH ALONE. A run of odd sums is
# what a badly-read page looks like -- the *Andante* refuses every meter
# including its own -- and proposing a change from it would manufacture meters
# out of noise. The glyph must open the question; the math may then confirm it,
# refuse it, or choose between two readings of it.
# ─────────────────────────────────────────────────────────────────────────────

#: One staff that reads a COMPLETE meter (a numerator over a denominator) at a
#: mid-staff bar. Alone it clears `METER_CHANGE_FLOOR` -- which is Sean's
#: ordering taken literally: a printed time signature IS the biggest sign.
W_CHANGE_GLYPH_PAIR = 3.0

#: A digit at that bar that does NOT pair into a meter. Weak, and deliberately
#: so: it says "something meter-shaped is printed here" without saying what.
W_CHANGE_GLYPH_LOOSE = 0.5

#: Each subsequent bar whose length matches the proposed new meter, and each
#: that does not. ⚠️ "for how long - the longer the more likely" is expressed
#: by these ACCUMULATING over the run rather than by any run-length constant.
W_CHANGE_BAR_FITS = 1.0
W_CHANGE_BAR_CONTRADICTS = -1.0

#: What a change needs before it is written into the meter's segments.
#: ⚠️ At 3.0 a single staff reading a complete meter clears it and two
#: contradicting bars sink it again -- the same structural ordering the carry
#: uses, with the glyph in the place the carry gives to a prior reading.
METER_CHANGE_FLOOR = 3.0


# ─────────────────────────────────────────────────────────────────────────────
# AN UNCORROBORATED CHANGE GOVERNS ITS OWN SYSTEM AND IS NOT CARRIED OFF IT.
# (A-METER-6)
#
# A meter change is printed at ONE bar of ONE system, ON EVERY STAFF of that
# system — the same convention `key_signature_corroboration` transplants for
# key signatures. So a change read on exactly one staff of a twelve-staff
# system is the weakest meter fact this pipeline can produce: at
# `W_CHANGE_GLYPH_PAIR = 3.0` it clears `METER_CHANGE_FLOOR` alone, by design
# (*"a printed time signature IS the biggest sign"*), and nothing else is
# asked of it.
#
# ⚠️⚠️ THE OBVIOUS RULE — REFUSE AN UNCORROBORATED CHANGE — WAS MEASURED AND IS
# REFUSED, BECAUSE IT DELETES THE ONE TRUE METER CHANGE THIS PROJECT HAS EVER
# FOUND ON A SCAN. Beethoven 5 / Litolff p.62 prints `3/4` at the bar the
# reference names; we read it on **ONE staff of seventeen**, at support 3.0
# with its bars silent (0 fit / 0 contradict). The three false changes on the
# same corpus read one staff too, at support 3.0, 4.0 and 4.5 — two of them
# HIGHER than the true one, and the only one whose bars say anything at all
# (p.61's `C`, 1 bar fitting) is FALSE. **Stave count, support and bar math all
# fail to separate the populations**, and CLAUDE.md already records the same
# fact from the other direction: *"the p.62 `3/4` this project celebrates is
# also one staff of seventeen"*.
#
# ⚠️ SO THE ACTION IS WEAKENED UNTIL IT IS ONE-SIDED. A change does TWO things,
# and only the second is where one staff's reading gets amplified:
#
#   1. it governs the bars of ITS OWN system, through `record.meter_at` —
#      local, visible in the file, and checkable against the print;
#   2. it becomes, through `_meter_in_force_at_end`, the meter CARRIED onto
#      every following system that abstains — a document-wide claim built out
#      of a single glyph on a single staff.
#
# This rule gates (2) and leaves (1) exactly as it was. The p.62 `3/4` still
# reaches the file on its own system, to the byte; what it may no longer do is
# decide page 63. That is the `METER_SOURCE_REASONS` discipline — *"neither is
# ink on the source's own page, so admitting either would make
# `pages_since_read` a lie about the distance back to ink"* — extended one
# step, from WHICH VERDICTS may be carried from to WHICH SEGMENTS of them.
#
# ⚠️ IT IS THE STRONGER WITNESS (other staves reading THE SAME meter) PAIRED
# WITH THE WEAKER ACTION, and that pairing is deliberate.
# `key_signature_corroboration` takes the opposite pair for a stated reason: it
# REVERTS, so it needs the weakest possible witness (another staff changes at
# the same BAR, whatever value it reads) or it would break transposing
# instruments, which genuinely carry different keys at one bar. A meter has no
# such exemption — its own docstring says so: *"A meter change is corroborated
# by other staves reading THE SAME METER, because a meter is one fact shared by
# the system"* — and confining costs at most a carry where reverting costs the
# music. `staves_reading_a_meter` is recorded beside it so the weaker witness
# can be priced later without a re-gather.
# ─────────────────────────────────────────────────────────────────────────────

#: How many staves of a system must read the SAME meter at one bar for that
#: change to be carried off the system — the staff itself plus one witness.
#:
#: ⚠️ NOT A TUNED CONSTANT, and on the four-page corpus that set it, it could
#: not be one: the TRUE and FALSE one-staff populations OVERLAP at exactly 1
#: (see A-METER-6), so no threshold separates them there and every value above
#: 1 confines the same four segments. 2 is the weakest bar that can confine
#: anything at all — `key_signature_corroboration.MIN_WITNESSES`' own
#: reasoning — and it remains the ABSOLUTE floor below which nothing is ever
#: corroborated, on a system of any size.
#:
#: ⚠️⚠️ ROADMAP 2.12j — "FOR THE SAME REASON IT IS NOT A FRACTION OF THE
#: SYSTEM" IS SUPERSEDED, NOT DELETED (a correction beside the measurement it
#: corrects is worth more than a gap). That reasoning guarded against a
#: HYPOTHETICAL 24-staff score; `_required_corroboration` below is a
#: MEASUREMENT on a real 12-14-staff whole movement (Brahms 1/i, Breitkopf):
#: eleven mid-system `change_only` segments, each corroborated at this
#: absolute floor alone (2-4 of 12-14 staves, 14.3%-28.6% coverage), each with
#: `bars_fit: 0` on every one of its own bars — a control that can never fail,
#: since `len(staves) >= 2` alone already clears `METER_CHANGE_FLOOR` before a
#: single bar term is added (`W_CHANGE_GLYPH_PAIR = 3.0` twice is 6.0). Two
#: staves independently misreading the SAME wrong meter is not evidence a
#: THIRTEEN-staff system printed anything — CLAUDE.md §10's "a key change is
#: printed at one bar on every staff of the system" is the convention this
#: file already assumes for meter (2.12d's own CONVENTION ASSUMED note). See
#: `_required_corroboration` for what changed and why it does not touch any
#: existing corroborated fixture (every one already reads at or near 100%).
METER_CHANGE_MIN_STAVES = 2

#: ROADMAP 2.12j. The prior art this raises the floor with: the LEGACY
#: pipeline's OWN sibling guard, `tools/omr/rhythm.py:631`
#: `drop_uncorroborated_meter_changes`, already uses
#: `max(2, round(0.5 * n_staves))` — cited, never imported (LEGACY is frozen
#: and may not be read from `tools/omr/staged/`, CLAUDE.md §3), so the number
#: is reused and the two modules stay independent.
METER_CHANGE_COVERAGE_FLOOR = 0.5


def _required_corroboration(total_staves: Optional[int]) -> int:
    """How many staves must agree before a mid-system meter fact (a CHANGE or
    a CAUTIONARY) is `corroborated` — `METER_CHANGE_MIN_STAVES`, raised on a
    system large enough that two staves are no longer a meaningful fraction
    of it.

    ⚠️ `total_staves` MAY BE `None` (`Q.SYSTEM_STAFF_COUNT` undecided) — the
    ABSENCE of a count is not evidence the system is large, so the ABSOLUTE
    floor alone applies, exactly as before this item. This is the same
    "missing is not zero" discipline `Outcome.ABSTAINED` uses everywhere else
    in this file.

    ⚠️ THIS RAISES THE FLOOR; IT NEVER LOWERS IT. `max` with
    `METER_CHANGE_MIN_STAVES` means a tiny system (say 2 staves) still needs
    both, not `round(0.5 * 2) == 1` — a fraction can only make agreement
    HARDER to reach, never easier than the two-witness floor A-METER-6 always
    required.
    """
    if not total_staves:
        return METER_CHANGE_MIN_STAVES
    return max(METER_CHANGE_MIN_STAVES,
               round(METER_CHANGE_COVERAGE_FLOOR * total_staves))


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.12d — THE SAME AGREEMENT ALSO GATES WHETHER A CHANGE GOVERNS ITS
# OWN SYSTEM, NOT ONLY WHETHER IT IS CARRIED OFF IT.
#
# A-METER-6 above deliberately left rule (1) — "it governs the bars of ITS
# OWN system" — ungated, measured on four pages of two scans where the TRUE
# and FALSE one-staff populations overlapped at support 3.0-4.5 and confining
# it would have deleted the one true meter change this project had then
# found (Litolff p.62, one staff of seventeen).
#
# ⚠️⚠️ RE-MEASURED 2026-09-28 ON A FRESH WHOLE-MOVEMENT BREITKOPF GATHER
# (`benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` §13, "the funnel") AND
# THE TRADE FLIPPED. `system/1/1` reads a lone-staff `4/4` at support 3.0 with
# `bars_contradict: 1` — the bars themselves disagreeing with the one staff
# that read it — and still governed the whole system under the old rule,
# because rule (1) asked nothing but `METER_CHANGE_FLOOR`. Whole-movement,
# 91.4% of every bar 2.8 holds out is judged against a `4.0` the plate does
# not print anywhere in this movement outside one 9/8 bar at measure 8, and
# 859 of those bars' OWN readings already sum to the TRUE meter — thrown away
# only because an uncorroborated glyph on one staff had already overwritten
# `in_force` for everything after it on that system.
#
# CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: CLAUDE.md §10's
# "a key change is printed at one bar on every staff of the system" is taken
# to hold for a METER change too — an engraver does not silently retime one
# part alone. It would be FALSIFIED by a genuine printed meter change this
# gate refuses because the system's OTHER staves were simply never detected
# at that bar (a coverage failure wearing a convention failure's clothes) —
# which is exactly the risk A-METER-6 priced against Litolff p.62 and the
# risk this reversal now accepts on the strength of the Brahms evidence
# above. NOT CONFIRMED WITH SEAN — crops are cut for his read under
# `benchmarks/omr-shape-role-2026-09/out/print/m212d-*`.
#
# The BAR side of A-METER-6 is unchanged and is not what this gate asks:
# `support` already folds `bars_fit`/`bars_contradict` into the floor a
# candidate must clear before it is a candidate at all (`METER_CHANGE_FLOOR`,
# above). This gate is orthogonal to that, and it is the SAME threshold
# `METER_CHANGE_MIN_STAVES` already computes into `corroborated` for rule
# (2) — reused, not retuned: tonight's evidence is about whether to also
# apply the existing number to rule (1), not about what the number should
# be. A stronger, fraction-of-the-system threshold is visible in the fresh
# record too (`system/2/0` corroborates at 2 of an orchestral system's staves
# and is still wrong) and is NOT this item's to fix — flagged, not chased.
#
# ⚠️⚠️ ROADMAP 2.12j — CHASED. The batch re-decision of the whole movement
# (this constant, `_required_corroboration`) found ELEVEN such segments, not
# one, together governing thousands of held-out bars through the carry — see
# `benchmarks/omr-shape-role-2026-09/FINDINGS.md` PART 8. `corroborated` now
# reads `_required_corroboration(total_staves)` instead of the bare absolute
# floor; this gate (`METER_CHANGE_GATES_OWN_SYSTEM`) is unchanged and still
# reads that SAME flag, so the fix lands entirely in what "corroborated"
# means, not in a second place that has to agree with this one.
# ─────────────────────────────────────────────────────────────────────────────

#: Not a flag (CLAUDE.md: no new flag, no new benchmark derived check or
#: handoff without a roadmap item, and this roadmap item is explicit that a
#: pricing arm's "base" is the SAME tree with this parameter set False, never
#: a new `OMR_*` env var). A plain module constant, the same shape
#: `METER_CHANGE_MIN_STAVES` already is and is already read directly by this
#: suite's own tests (`rhythm_mod.METER_CHANGE_MIN_STAVES`).
METER_CHANGE_GATES_OWN_SYSTEM = True


#: The reason word a DECLINED mid-system change is filed under — never a
#: verdict `reason` (the system's own outcome keeps "voted" / "change_only" /
#: etc, unaffected by how many of its candidate changes were declined), only
#: a per-candidate tag inside `declined_changes` so a reader can tell "this
#: system's own change never existed" apart from "this system printed a
#: change we chose not to act on."
METER_CHANGE_NOT_SYSTEM_WIDE = "meter_change_not_system_wide"


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.12l — A PRINTED CHANGE WHOSE DIGITS WERE BOXED AS NOTEHEADS.
#
# `benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` §15b: on Breitkopf
# 317803 pdf p1, system/1/0 cell 1 prints a 6/8 change on every staff, and
# the detector boxes both digits as `noteheadWhole*`/`noteheadBlack*` --
# `Q.METER_GLYPH` (`timeSig*` classes only) never fires there, so this
# system's own `_meter_changes` loop above never even VISITS that cell (it
# only walks `by_cell`, built from `Q.METER_GLYPH`). Nothing reads the
# change; `system/1/0` stays 9/4 to its own end and hands that wrong value
# on into `system/1/1`, whose own bars then refuse the carry outright.
#
# `notehead_precision.adjudicate_notehead_is_not_a_notehead` (ROADMAP 2.12l,
# same item) now REFUSES those two boxes, reason `is_a_meter_digit` --
# backed by a cross-staff quorum, so it fires only where the SAME pattern
# repeats on most of the system's staves, never on one staff's own chord.
# This file reads that refusal back as a WITNESS: a change IS printed at
# that cell, its VALUE unread. CLAUDE.md rule 6 ("connect, never guess") and
# rule 8 (a fallback never turns "cannot tell" into an answer) both apply --
# so this never sets a numerator/denominator from the witness alone. Two
# uses, both value-free:
#
#   1. `_meter_changes` files the cell into `declined_changes` (this
#      system's OWN record of what it saw and refused, next to the
#      corroboration failures ROADMAP 2.12d already keeps there) with NO
#      numerator/denominator -- a witness, not a candidate.
#   2. `_carry_meter` reads that same fact back off `src`'s own recorded
#      value (`found.value["declined_changes"]`, already on the record from
#      (1) -- no second query) and, where the carry is refused by `src`'s
#      OWN later bars, relabels the generic `carry_outweighed_by_the_bars`/
#      `carry_not_corroborated` to `meter_change_digits_misread` -- the SAME
#      shape ROADMAP 2.12k already uses to LABEL a return the bars proved
#      but the reader missed, applied to a different, specifically-known
#      cause. It is still an ABSTENTION either way; only the word changes.
# ─────────────────────────────────────────────────────────────────────────────

#: `notehead_precision.METER_DIGIT_REASON`'s own spelling, cited rather than
#: imported: that module already keeps its thresholds self-contained (see
#: its own file docstring) and this file is the meter chain's home, not a
#: dependency of the notehead decision. The two are the SAME LITERAL and a
#: test asserts it (`test_staged_meter_digit_witness.py`), so a rename of
#: one without the other fails loudly rather than reading as "nothing found".
METER_DIGIT_REASON = "is_a_meter_digit"

#: Filed on a `declined_changes` entry (this system's own, or read back off
#: a carry source's) with NO numerator/denominator: a change is printed
#: here, unread -- never a value, only a place. Also the abstain reason
#: `_carry_meter` returns when a carry it would otherwise refuse generically
#: is refused for exactly this known cause.
METER_CHANGE_DIGITS_MISREAD = "meter_change_digits_misread"


def _meter_digit_witness_cells(ev: Evidence,
                               total_staves: Optional[int]) -> Dict[int, tuple]:
    """ROADMAP 2.12l. `{cell_index: (staff, ...)}` for every cell of THIS
    system where a QUORUM of staves carry a `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD`
    verdict reasoned `is_a_meter_digit` -- read back as a fact, never
    re-derived (the notehead decision already did the cross-staff geometry;
    this only counts how many staves it fired on).

    ⚠️ THE SAME FLOOR A MID-SYSTEM METER FACT ALREADY NEEDS
    (`_required_corroboration`, ROADMAP 2.12j), reused rather than a second
    number that could drift from it -- "printed on the system" means the
    same thing whether the witness is a read digit or a misread one.

    ⚠️ ONE QUERY, `Scope.SELF_AND_DESCENDANTS` OFF `ev.subject` (the
    SYSTEM this decision already scopes to) -- the SAME shape
    `_last_cell_per_staff` already uses for `Q.MEASURE_PARTITION`, called
    once per system, never per glyph.
    """
    # ⚠️⚠️ TWO PASSES, AND THE ORDER IS WHAT KEEPS THIS DECISION'S OWN
    # FOOTPRINT HONEST. A first cut read `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD`
    # VERDICTS broadly (`ev.verdicts(..., scope=SELF_AND_DESCENDANTS)`) and
    # was measured to break `test_stage_review_evidence.py` TWICE: every
    # notehead verdict returned by that call is marked `considered` by THIS
    # decision (`Evidence._seen`), so `adjudicate_meter` ended up
    # transitively citing a human's confirm/refuse row on a glyph six staff
    # spaces from any barline, in a system that prints no meter change at
    # all -- `verdicts_that_named_it`/`basis_names_human` (review tooling
    # that answers "which decisions would a human's correction touch")
    # reported `adjudicate_meter` for EVERY notehead in the document, not
    # the handful near a bar's own head.
    #
    # The fix is not a narrower SCOPE (any `SELF_AND_DESCENDANTS` sweep of a
    # VERDICT marks everything it returns, however small the result) but a
    # narrower QUERY: find candidates from OBSERVATIONS first (`Q.GLYPH_BOX`,
    # `Q.CELL_STAFF_SPACE` -- plain detector/geometry rows, never a human's,
    # so being marked `considered` here is inert for that tracking) filtered
    # to the SAME near-barline x-window `notehead_precision` itself gates
    # on, and only THEN ask each SURVIVING candidate's own verdict by EXACT
    # subject (`ev.verdict`, not `ev.verdicts`) -- a handful of glyphs per
    # system, never the population. `wants` still declares
    # `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` (this file's own docstring said so
    # first); it is read narrowly now, not left unread.
    by_cell: Dict[int, set] = {}
    spacing_by_cell: Dict[Tuple[int, int], float] = {}
    for r in ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_DESCENDANTS):
        st, ce = getattr(r.subject, "staff", None), getattr(r.subject, "cell", None)
        if st is None or ce is None:
            continue
        try:
            sp = float(r.value)
        except (TypeError, ValueError):
            continue
        if sp > 0:
            spacing_by_cell[(int(st), int(ce))] = sp
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS):
        sub = r.subject
        st, ce, gl = (getattr(sub, "staff", None), getattr(sub, "cell", None),
                     getattr(sub, "glyph", None))
        if st is None or ce is None or gl is None or int(ce) == 0:
            continue                  # cell 0 is the OPENING, not a change
        v = r.value
        if not isinstance(v, (list, tuple)) or len(v) != 5:
            continue
        if not str(v[0]).lower().startswith("notehead"):
            continue
        sp = spacing_by_cell.get((int(st), int(ce)))
        if sp is None:
            continue
        if not (0.0 <= float(v[1]) / sp <= _NP.METER_DIGIT_X_MAX_SPACES):
            continue                  # not near a barline -- not a candidate
        found = ev.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, subject=sub)
        if (found is not None and found.outcome is Outcome.DECIDED
                and found.reason == METER_DIGIT_REASON):
            by_cell.setdefault(int(ce), set()).add(int(st))
    floor = _required_corroboration(total_staves)
    return {c: tuple(sorted(sts)) for c, sts in by_cell.items()
            if len(sts) >= floor}


def _ocr_at_bar_candidates(ev: Evidence) -> Dict[int, dict]:
    """ROADMAP 2.29. `{cell_index: majority reading}` for every cell of this
    system `Q.METER_OCR_AT_BAR` read anything plausible at -- most systems
    empty, and every system empty while `OMR_METER_OCR_AT_BAR` is off
    (CLAUDE.md, "off writes nothing at all").

    ⚠️ FETCHED HERE, ONCE, AND PASSED DOWN -- the same shape `_carry_meter`
    already uses for `n_cells` (see that function's own comment): a `Q.`
    read a further call inside `_meter_changes` would be invisible to
    `inventory._never_read`'s depth-3 walk from `adjudicate_meter` and read
    as an INERT declaration despite being genuinely consumed.

    ⚠️ READ BACK, NEVER RE-DERIVED -- the same "connect, never guess" shape
    `_carry_source_digit_misread` already uses for the digit witness itself.
    NEVER TREATED AS A DECISION: `_meter_changes` files this on a
    `declined_changes` entry as `ocr_candidate`, a value for the carry
    ladder (or a human) to weigh -- see the ROADMAP 2.12l block comment
    above `_meter_digit_witness_cells`. This function itself decides
    nothing about the SYSTEM's meter.
    """
    by_cell: Dict[int, dict] = {}
    for r in ev.rows(Q.METER_OCR_AT_BAR, scope=Scope.SELF_AND_DESCENDANTS):
        cell_index = getattr(r.subject, "cell", None)
        if cell_index is None:
            continue
        v = r.value
        if not isinstance(v, (list, tuple)) or len(v) != 2:
            continue
        by_cell.setdefault(int(cell_index), {}).setdefault(
            (int(v[0]), int(v[1])), []).append(r)
    out: Dict[int, dict] = {}
    for cell_index, by_value in by_cell.items():
        (num, den), witnesses = max(by_value.items(), key=lambda kv: len(kv[1]))
        out[cell_index] = {"numerator": num, "denominator": den,
                           "raw": "%d/%d" % (num, den),
                           "staves_reading_it": len(witnesses)}
    return out


def _carry_source_digit_misread(value: Optional[dict]) -> Optional[dict]:
    """The first `declined_changes` entry on a `Q.METER` VALUE (this
    system's own, or a carry source's) filed `meter_change_digits_misread`,
    or None. Reads a fact already on the record (filed by
    `_meter_changes`/`_with_segments` below) -- no second query, no new
    evidence."""
    for c in (value or {}).get("declined_changes") or ():
        if c.get("declined_reason") == METER_CHANGE_DIGITS_MISREAD:
            return c
    return None
# ─────────────────────────────────────────────────────────────────────────────


#: The meters the repertoire actually prints, from the template reader's own
#: `DEFAULT_METERS` -- imported rather than restated so the two readers cannot
#: drift apart about what a meter IS.
#:
#: ⚠️ IMPORTED AT MODULE LOAD AND NOT GUARDED. The first version wrapped this
#: in `except Exception: frozenset()`, which swallowed a wrong relative import
#: and left the set EMPTY -- so the gate silently admitted nothing and every
#: change was refused. That is this project's own "an optional pass may abstain
#: quietly, it may not fail like a defect quietly", reproduced inside the fix
#: for a different quiet failure.
from ... import time_signature_locator as _tsl
_PLAUSIBLE_METERS = frozenset((n, d) for n, d, _raw in _tsl.DEFAULT_METERS)

#: Bar length in quarter-notes -> the meters that print it, from the template
#: reader's own table. ⚠️ A LENGTH NO METER HAS IS NOT A CANDIDATE: without
#: this the *Andante*'s bars would nominate 1.0 quarter-notes, and
#: `rhythm._drop_implausible_meters` already names `1/4` in its own docstring
#: as garbage that survives upstream filtering.
_METER_LENGTHS: dict = {}
for _n, _d in sorted(_PLAUSIBLE_METERS):
    _METER_LENGTHS.setdefault(round(_n * 4.0 / _d, 6), []).append((_n, _d))


def _meter_from_digits(rows) -> Optional[tuple]:
    """One staff's meter glyphs at one bar -> (numerator, denominator).

    ⚠️ THE STACK IS THE READING. A time signature is two digits stacked, so the
    numerator is simply the higher one -- `y_center` is on every row and is the
    whole of what distinguishes them. A bar whose digits do not separate into
    two heights says "something is printed here" and nothing more, which is
    what `W_CHANGE_GLYPH_LOOSE` is for.
    """
    digits = []
    for r in rows:
        name = str(r.value)
        if not name.startswith("timeSig"):
            continue
        tail = name[len("timeSig"):]
        if not tail.isdigit():
            continue                      # timeSigCommon and friends: no pair
        y = (r.detail or {}).get("y_center")
        if y is None:
            continue
        digits.append((float(y), int(tail)))
    if len(digits) < 2:
        return None
    digits.sort()
    top, bottom = digits[0], digits[-1]
    if top[0] == bottom[0]:
        return None                       # all at one height: not a stack
    return (top[1], bottom[1])


#: The one-glyph meters, and what each one NAMES. Derived from
#: `time_signature_locator.LETTER_METERS` (raw -> SMuFL glyph) inverted, so the
#: two modules cannot drift about which glyph is which letter, and paired with
#: the numbers `DEFAULT_METERS` already gives that raw.
_LETTER_BY_GLYPH = {"timeSigCommon": (4, 4, "C"),
                    "timeSigCutCommon": (2, 2, "C|")}
#: ⚠️ BOTH ASSERTS ARE LOAD-BEARING AND NEITHER IS DECORATION. The first fails
#: the moment `time_signature_locator` learns a third one-glyph meter and this
#: table does not; the second is the same gate `_meter_changes` applies to a
#: digit reading, so a letter can never nominate a meter the digits could not.
assert set(_LETTER_BY_GLYPH) == set(_tsl.LETTER_METERS.values())
assert all((n, d) in _PLAUSIBLE_METERS for n, d, _raw in _LETTER_BY_GLYPH.values())


def _meter_from_letter(rows) -> Optional[tuple]:
    """One staff's meter glyphs at one bar, read as a LETTER meter.

    ⚠️⚠️ THIS EXISTS BECAUSE A CHANGE PRINTED AS `C` WAS DETECTED AND DROPPED,
    which is this repository's most expensive recurring shape. `4/4` and `C`
    are one bar length and two engravings; `_meter_from_digits` needs two
    stacked digits and says so in its own comment (*"timeSigCommon and
    friends: no pair"*), so a system whose meter CHANGES to common time
    produced no candidate at all -- while the glyph sat on the record.
    Measured on an engraved Beethoven 5 finale at the 3/4 -> 4/4 change of bar
    209: `timeSigCommon` detected on **23 staves of 23**, unanimous, and
    `_meter_changes` proposed nothing.

    ⚠️ IT EARNS `W_CHANGE_GLYPH_PAIR`, NOT `W_CHANGE_GLYPH_LOOSE`, and the
    weight's name is what misleads. That constant is worth what it is because
    the staff read a COMPLETE meter -- a numerator AND a denominator -- and a
    letter meter is complete in one glyph. The loose weight is for ink that is
    meter-shaped without saying what it is, which a `C` never is.

    ⚠️ AMBIGUOUS INK ABSTAINS. A staff carrying BOTH a `timeSigCommon` and a
    `timeSigCutCommon` at one bar has not read a meter, it has read two, and a
    stroke through a C is exactly the distinction that is easy to lose (see
    `time_signature_locator._looks_cut`, which reads it by position rather than
    by template for that reason).
    """
    seen = {_LETTER_BY_GLYPH[str(r.value)] for r in rows
            if str(r.value) in _LETTER_BY_GLYPH}
    if len(seen) != 1:
        return None
    return next(iter(seen))


def _bar_run(bars: dict, from_cell: int, expected: float) -> tuple:
    """(bars that FIT, bars that do NOT) from `from_cell` onward."""
    fits = misses = 0
    for cell_index, lengths in sorted(bars.items()):
        if cell_index < from_cell or len(lengths) < METER_CARRY_MIN_STAVES_PER_BAR:
            continue
        mode, n = Counter(lengths).most_common(1)[0]
        if n / len(lengths) < 0.5:
            continue
        if abs(mode - expected) < 1e-6:
            fits += 1
        else:
            misses += 1
    return fits, misses


def _last_cell_per_staff(ev: Evidence) -> dict:
    """Each staff of this system -> the index of its LAST measure cell.

    ⚠️ PER STAFF, NOT PER SYSTEM, because the staves of one system do not
    always agree about how many bars they hold — on the Breitkopf Brahms the
    scan reads 8 cells where the print has 7 bars, and the extra one is the
    trailing sliver the cautionary sits in.
    """
    out = {}
    for v in ev.verdicts(Q.MEASURE_PARTITION, scope=Scope.SELF_AND_DESCENDANTS):
        if v.outcome is not Outcome.DECIDED or not isinstance(v.value, int):
            continue
        staff = getattr(v.subject, "staff", None)
        if staff is not None and v.value > 0:
            out[staff] = v.value - 1
    return out


def _total_staff_count(ev: Evidence) -> Optional[int]:
    """ROADMAP 2.12j. This system's own `Q.SYSTEM_STAFF_COUNT`, or `None`.

    ⚠️ FETCHED HERE, BESIDE `_bar_lengths_for`/`_last_cell_per_staff`, NOT
    inside `_meter_changes` — the same `inventory._never_read` depth-3 shape
    those two are already threaded as arguments for (see `_meter_changes`'s
    own docstring). `Q.SYSTEM_STAFF_COUNT` is already in `adjudicate_meter`'s
    `wants`, read the identical way at that decision's own top level.
    """
    v = ev.verdict(Q.SYSTEM_STAFF_COUNT)
    return v.value if v is not None and v.value else None


# ─────────────────────────────────────────────────────────────────────────────
# A CAUTIONARY IS NOT A CHANGE. (A-METER-5)
#
# An engraver announcing a new meter prints it TWICE: once after the final
# barline of the system that is ending -- the courtesy, or cautionary,
# signature -- and once at the head of the system that is beginning. The first
# governs NO BAR. It is a statement about the next system.
#
# `_meter_changes` had no notion of one: any meter glyph past cell 0 was a
# change. Measured on Brahms 1 mvt 1, whose LilyPond render and whose Breitkopf
# scan both print a cautionary `9/8` after page 0's last barline, it proposed a
# change at that page's last cell in BOTH printings -- support 57.0 engraved
# (19 staves) and 26.5 scanned -- and the segment would re-size a bar the
# cautionary does not govern.
#
# ⚠️ THE RULE IS THE ENGRAVING CONVENTION, NOT A FITTED THRESHOLD: a change is
# put at a system's START, and the cautionary exists precisely so it can be.
# So a meter standing in a system's LAST cell is the announcement, not the
# change -- unless the bar it would govern says otherwise, which is the one
# thing that could distinguish a genuine last-bar change from a courtesy.
#
# Measured over every change in this corpus: **all four TRUE changes sit at a
# non-last cell** (Litolff p.62 cell 8 of 13, Brahms 1 mvt 1 cell 1 of 8,
# Beethoven 5 mvt 4 cell 3 of 9, Brahms 1 mvt 4 cell 6 of 8) and **both
# cautionaries sit at a last cell**, 6 of 7 and 7 of 8.
#
# ⚠️ IT IS RECORDED, NOT DISCARDED. A cautionary states the meter of the NEXT
# system, and the document's own answer to a misread opening is often exactly
# that -- on the Breitkopf scan the opening `9/8` is voted `9/4` while the
# cautionary one system earlier reads `9` over `8` on ten and twenty staves.
# Consuming it belongs with the carry, so it goes on the record where the carry
# can find it rather than being dropped here.
# ─────────────────────────────────────────────────────────────────────────────


# ─── BEGIN template-at-bar consumer ──────────────────────────────────────────
# Everything between this marker and its END marker is the consumer for
# `Q.METER_TEMPLATE_AT_BAR`, the template reader aimed at a mid-staff bar head
# (`gather.gather_meter_at_bars`, default OFF). It is kept contiguous and
# marked so it can be moved wholesale, because the WEIGHING around it
# (`METER_CHANGE_FLOOR`, `W_CHANGE_*`) is being changed in parallel and this
# block deliberately touches none of it.

#: How many staves of one system must AGREE on one meter, read off their own
#: bar heads at the same bar, before any of their readings is admitted.
#:
#: ⚠️⚠️ THIS IS WHERE THE SAFETY IS, AND IT IS MEASURED. A mid-staff crop is an
#: EMPTY WINDOW almost everywhere, and `key_signature_template` already taught
#: this project what that costs: *the reader that can say "zero" is the one
#: that must never be given an empty window*. Over **1,612 mid-staff bar-head
#: windows on ten real scanned pages of two publishers** (Brahms 1 /
#: Breitkopf, Beethoven 5 / Litolff), none of which prints a meter change,
#: the reader answered above its own floor:
#:
#:     admitted on 1 staff  ->  16 spurious readings, 16 spurious columns
#:     admitted on 2        ->                         2 spurious columns
#:     admitted on 3        ->                         **0**
#:
#: ⚠️ IT IS NOT A NUMBER READ OFF THAT CORPUS, WHICH IS WHY IT IS 3 AND NOT
#: 2.5-ish. A meter change is printed on EVERY staff of the system at one bar
#: — that is what an engraver does — so agreement across staves is the shape
#: the real thing has, and this project has made that argument twice already
#: (`vote_system_time_signature`'s `min_staff_fraction`, and
#: `OMR_KEYSIG_CORROBORATION`). The corpus says where the noise stops; the
#: convention says why the test is agreement at all.
#:
#: ⚠️ THE COST IS UNMEASURED AND IS ONE-SIDED: no page in reach prints a
#: mid-staff meter change, so what this refuses has never been observed. A
#: real change on a badly-read system where only two staves clear the floor is
#: refused by this, and that refusal has not been priced.
METER_TEMPLATE_AT_BAR_MIN_STAVES = 3


def _template_readings_at_bars(ev: Evidence) -> dict:
    """`{cell: {(num, den, raw): {staves}}}` from `Q.METER_TEMPLATE_AT_BAR`.

    ⚠️ THE KEY CARRIES THE PRINTED FORM, for the same reason `_meter_changes`
    already keys on it: `C` and `4/4` are one bar length and two engravings,
    and a page must not average them into one answer.

    Empty when the gatherer is off, which is its default — so with the flag
    off this function returns `{}` and the block below is a no-op.
    """
    out: dict = {}
    for row in ev.rows(Q.METER_TEMPLATE_AT_BAR, scope=Scope.SELF_AND_DESCENDANTS):
        detail = row.detail or {}
        cell = detail.get("cell")
        value = row.value
        if cell is None or not isinstance(value, (tuple, list)) or len(value) != 2:
            continue
        cell = int(cell)
        if cell == 0:
            continue                      # cell 0 states the staff's OPENING
        num, den = int(value[0]), int(value[1])
        raw = detail.get("raw") or f"{num}/{den}"
        out.setdefault(cell, {}).setdefault((num, den, raw), set()).add(
            row.subject.staff)
    return out


def _admit_template_consensus(readings: dict, at_this_bar: dict,
                              already_read: set) -> dict:
    """Fold an AGREEING set of bar-head template readings into `readings`.

    Returns `{key: n_admitted}` for the record. A reading admitted here is
    indistinguishable downstream from a glyph reading by the same staff, which
    is the point: it IS a reading of a printed meter, taken by the better
    reader on a crop the detector was never asked about.

    ⚠️ GAPS ONLY, INHERITED RATHER THAN RE-DECIDED. A staff that already read
    a meter from its own DIGITS at this bar keeps that reading and this adds
    nothing for it — the same precedence `adjudicate_key_signature` applies to
    `key_signature_template`, and for the same reason: the second reader is
    the one that can OVER-produce, so it speaks where the first was silent.
    """
    admitted: dict = {}
    for key, staves in sorted(at_this_bar.items()):
        if len(staves) < METER_TEMPLATE_AT_BAR_MIN_STAVES:
            continue
        gained = sorted(st for st in staves if st not in already_read)
        if not gained:
            continue
        seen = set(readings.setdefault(key, []))
        for st in gained:
            if st not in seen:
                readings[key].append(st)
        admitted[key] = len(gained)
    return admitted
# ─── END template-at-bar consumer ────────────────────────────────────────────


def _meter_changes(ev: Evidence, opening: dict, bars: dict,
                   last_cell: dict, templates: Optional[dict] = None,
                   total_staves: Optional[int] = None,
                   digit_witnesses: Optional[dict] = None,
                   ocr_at_bar: Optional[dict] = None) -> tuple:
    """Every mid-system meter change this system's own evidence supports.

    Takes its facts as arguments — `opening`, `bars`, `last_cell` and
    `total_staves` — rather than reaching for them, which is how `bars`
    already worked. ⚠️ The inconsistency was surfaced by
    `inventory._never_read`, which follows a decision's own helpers to depth
    3: with `last_cell` fetched HERE the read sat one level too deep and
    `measure_partition` was reported as an inert `wants` entry. The check was
    right that the call chain was one link longer than the others, and moving
    the fetch beside `_bar_lengths_for` is the fix the report was pointing at
    — not a workaround for it. `total_staves` (ROADMAP 2.12j) follows the
    SAME shape for the SAME reason: `Q.SYSTEM_STAFF_COUNT` is fetched by the
    two callers, beside `_bar_lengths_for`, not by this function.

    Returns `(changes, cautionaries, declined)` — segment dicts in bar order,
    each with `from_cell` and the terms that carried it. The GLYPH opens each
    candidate; the bar math confirms it, refuses it, or chooses between two
    staves that read it differently.

    ⚠️ A CAUTIONARY IS SEPARATED OUT RATHER THAN DROPPED — see `A-METER-5`
    above. It is a statement about the NEXT system and governs nothing here.

    ⚠️ 2.12d: A CANDIDATE THAT CLEARS THE FLOOR BUT NOT THE STAVES IS
    SEPARATED OUT THE SAME WAY, into `declined` — see
    `METER_CHANGE_GATES_OWN_SYSTEM` above. It never reaches `changes`, never
    updates `in_force`, and is recorded under `METER_CHANGE_NOT_SYSTEM_WIDE`
    so a reader can tell "the system printed nothing here" apart from "the
    system printed something we chose not to act on."

    ⚠️ 2.12j: "THE STAVES" IS NOW A FRACTION OF `total_staves`, NOT A BARE
    COUNT — see `_required_corroboration`. `None` (staff count undecided)
    falls back to the absolute floor alone, exactly as before this item.

    ⚠️ 2.12l: `digit_witnesses` FOLLOWS THE SAME SHAPE, FOR THE SAME REASON
    — `{cell_index: (staff, ...)}`, fetched by the caller
    (`_meter_digit_witness_cells`, beside `_total_staff_count`) and passed
    in rather than read here, or `inventory --check` reports `meter`'s own
    `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` declaration as inert (the read would sit
    one helper-frame deeper than `_never_read`'s depth-3 bound). `{}` where
    the flag has nothing or the caller supplied none.
    """
    digit_witnesses = digit_witnesses or {}
    rows = ev.rows(Q.METER_GLYPH, scope=Scope.SELF_AND_DESCENDANTS)
    cautionaries: list = []
    declined: list = []
    by_cell: dict = {}
    for r in rows:
        cell = (r.detail or {}).get("cell")
        if cell is None or int(cell) == 0:
            continue                      # cell 0 states the staff's OPENING
        by_cell.setdefault(int(cell), []).append(r)
    # ─── BEGIN template-at-bar consumer ──────────────────────────────────────
    # Empty dict when `OMR_METER_TEMPLATE_AT_BAR` is off, which is the default.
    # ⚠️ A CANDIDATE COLUMN THE DETECTOR OPENED IS STILL WHAT MAKES A BAR
    # ASKABLE — the gatherer only ever looks where some staff saw meter-shaped
    # ink — so this can add staves to a bar, never a bar to the page.
    #
    # ⚠️ TAKEN AS AN ARGUMENT, NOT FETCHED HERE, and `inventory --check` is
    # what said so: it follows a decision's own helpers to a bounded depth, and
    # fetched here the read sat one level too deep, so `meter` was reported as
    # declaring `meter_template_at_bar` in `wants` and never reading it — the
    # INERT DECLARATION anti-pattern, bought with a green line. `last_cell` was
    # moved for exactly this reason and this follows it.
    templates = templates if templates is not None else {}
    # ─── END template-at-bar consumer ────────────────────────────────────────

    out = []
    # ⚠️⚠️ THE METER IN FORCE, NOT THE OPENING — and comparing against the
    # opening was TWO bugs, both measured.
    #
    # 1. A RESTATEMENT OF THE SEGMENT ALREADY ACCEPTED WAS EMITTED AGAIN. Each
    #    candidate was tested against the system's OPENING only, so once a
    #    change to `4/4` was accepted at cell 2, cells 3, 4, 5 and 6 proposing
    #    `4/4` all differed from the opening and were appended too. Measured on
    #    Brahms 1 / Breitkopf p.1: **five consecutive segments, every one of
    #    them `4/4`** — a system does not change meter five times to the meter
    #    it is already in.
    # 2. A CHANGE *BACK* TO THE OPENING WAS SILENTLY DROPPED, which is the same
    #    comparison failing in the other direction. A movement that goes
    #    `3/4 -> 4/4 -> 3/4` — Beethoven 9's finale does it repeatedly — could
    #    record the departure and never the return.
    #
    # Both disappear by comparing against what is actually in force at that
    # bar, which is the opening until a segment supersedes it. ⚠️ This is not
    # a threshold and there is nothing to tune: a segment identical to its
    # predecessor changes nothing, by the definition of `record.meter_at`.
    in_force = (opening.get("numerator"), opening.get("denominator"))
    # ⚠️ ROADMAP 2.12l: CELLS THE MAIN LOOP ACTUALLY EVALUATED, NOT MERELY
    # CELLS `by_cell` HAS A ROW FOR. A stray, unreadable `Q.METER_GLYPH`
    # detection (one lone `timeSig1`, no stacked partner) puts a cell in
    # `by_cell` without ever producing a `readings` entry -- measured on the
    # Breitkopf fixture itself, staff 9 fires one at cell 1, the SAME cell
    # the digit witness names -- and `by_cell`'s bare presence must not be
    # allowed to silently shadow the far stronger cross-staff witness below.
    cells_with_a_candidate: set = set()
    # ⚠️ ROADMAP 2.72: A BAR THE DETECTOR SAID NOTHING ABOUT IS STILL A BAR
    # WHERE THE STAVES' OWN TEMPLATE READINGS AGREE. This loop used to visit
    # only cells with a `Q.METER_GLYPH` row ("this can add staves to a bar,
    # never a bar to the page" -- true while the gatherer asked only where
    # some staff had detected meter-shaped ink). The gatherer's candidates now
    # include the stacked-head pair the detector boxes where it fails to box a
    # time signature, so a printed change can reach this function with no
    # glyph row at all; `_admit_template_consensus` below is the gate that
    # refuses a lone or scattered reading (>= 3 staves, one meter).
    for cell in sorted(set(by_cell) | set(templates)):
        per_staff = {}
        for r in by_cell.get(cell, ()):
            per_staff.setdefault(r.subject.staff, []).append(r)

        # ⚠️ THE STAVES MAY DISAGREE, AND THE MATH IS WHAT SETTLES IT. On p.62
        # cell 8 one staff reads 3 over 4 and another reads four 4s; a vote
        # alone would tie. Each distinct reading is scored on its own, and the
        # bars that follow decide -- which is the layering working rather than
        # a tie-break rule.
        readings: dict = {}
        loose = 0
        staves_with_a_meter: set = set()
        for staff, staff_rows in per_staff.items():
            # ⚠️ DIGITS FIRST AND THE LETTER ONLY AFTER, so a bar that prints
            # digits is never re-read as a letter by a stray detection.
            pair = _meter_from_digits(staff_rows)
            # ⚠️ THE KEY CARRIES THE PRINTED FORM, because `adjudicate_meter`'s
            # own rule is that `C` and `4/4` are ONE bar length and TWO
            # engravings and a page must not average them into one answer.
            read = ((pair[0], pair[1], f"{pair[0]}/{pair[1]}") if pair
                    else _meter_from_letter(staff_rows))
            if read is None:
                loose += len(staff_rows)
            else:
                readings.setdefault(read, []).append(staff)
                # ⚠️ ACROSS ALL READINGS, so this counts staves that read a
                # COMPLETE meter here whatever value they read. It is the
                # WEAKER witness of A-METER-6 and NOTHING DECIDES ON IT — it is
                # recorded so the weaker rule can be priced later without a
                # re-gather, the way `cautionary` was recorded before anything
                # consumed it.
                staves_with_a_meter.add(staff)
        # ─── BEGIN template-at-bar consumer ──────────────────────────────────
        # A no-op with the flag off (`templates` is `{}`), and a no-op wherever
        # fewer than `METER_TEMPLATE_AT_BAR_MIN_STAVES` staves of this system
        # read the SAME meter off their own bar heads at this bar.
        #
        # ⚠️⚠️ IT DELIBERATELY DOES NOT FEED `staves_with_a_meter`, AND THAT IS
        # A DECISION TAKEN AT THE MERGE. That set is A-METER-6's weaker witness,
        # defined over what the DETECTOR's glyphs said and recorded so the
        # weaker rule can be priced later WITHOUT a re-gather. Folding a second
        # reader into it would silently change what such a pricing measures —
        # two readers pooled into one number that was defined over one of them.
        # The template's contribution is reported APART, as
        # `staves_from_bar_head_template`, which is this repository's own rule
        # (`cv_glyphs` beside `detector_glyphs`; `detector` beside
        # `cv_hairpins`) rather than a new convention.
        template_admitted = _admit_template_consensus(
            readings, templates.get(cell, {}),
            already_read={st for st, rs in per_staff.items()
                          if (_meter_from_digits(rs)
                              or _meter_from_letter(rs)) is not None})
        # ─── END template-at-bar consumer ────────────────────────────────────
        if not readings:
            continue
        cells_with_a_candidate.add(cell)

        best = None
        for (num, den, raw), staves in sorted(readings.items()):
            # ⚠️ A METER MUST BE ONE THE REPERTOIRE PRINTS, and without this
            # the detector proposes meters that do not exist. Measured: p.61
            # cell 3 produced a change to **1/1** at support 5.0, out of
            # `timeSig1` detections -- a confident reading of a meter nobody
            # has ever engraved. The list is `time_signature_locator`'s own
            # `DEFAULT_METERS`, imported rather than restated so the two
            # readers cannot drift apart about what a meter is.
            if (num, den) not in _PLAUSIBLE_METERS:
                continue
            expected = float(num) * 4.0 / float(den)
            fits, misses = _bar_run(bars, cell, expected)
            terms = [Term(f"glyph_pair_staff_{st}", W_CHANGE_GLYPH_PAIR)
                     for st in staves]
            terms += [Term("glyph_loose", W_CHANGE_GLYPH_LOOSE)
                      for _ in range(loose)]
            terms += [Term(f"bar_fits_{i}", W_CHANGE_BAR_FITS)
                      for i in range(fits)]
            terms += [Term(f"bar_contradicts_{i}", W_CHANGE_BAR_CONTRADICTS)
                      for i in range(misses)]
            support = tally(terms)
            # ⚠️ `raw` IS THE INK HERE, unlike the form a bar-derived meter
            # BORROWS. `_form_for_length` refuses to copy a letter because the
            # borrowing system printed nothing we could read; this system's own
            # staves read the `C`, so `symbol="common"` reaching the export is
            # a claim the page supports.
            cand = {"from_cell": cell, "numerator": num, "denominator": den,
                    "raw": raw, "support": round(support, 3),
                    "staves_reading_it": sorted(staves),
                    "staves_reading_a_meter": len(staves_with_a_meter),
                    # ⚠️ A-METER-6. Written on EVERY change, including the
                    # corroborated ones, so `True` means "asked and answered"
                    # rather than "this build did not look" -- the
                    # `empty_bars_padded_without_meter` lesson, where a counter
                    # written only on the bad branch made "we sized all 184
                    # correctly" and "this figure was never computed" read
                    # identically.
                    # ⚠️ 2.12j: `_required_corroboration`, NOT THE BARE
                    # ABSOLUTE FLOOR — see that helper and the constant above
                    # it. `total_staves=None` (staff count undecided) reduces
                    # to the SAME `METER_CHANGE_MIN_STAVES` this always was.
                    "corroborated": (len(staves)
                                     >= _required_corroboration(total_staves)),
                    "bars_fit": fits, "bars_contradict": misses,
                    "loose_digits": loose}
            # ─── BEGIN template-at-bar consumer ──────────────────────────────
            # ⚠️ RECORDED, NEVER NETTED AWAY. A change that exists only because
            # the template reader was asked at this bar must SAY so, or the
            # flag's effect becomes invisible the moment the verdict is read
            # rather than the log. Absent (not zero) when nothing was admitted,
            # so a flag-off record carries no new key at all.
            if template_admitted.get((num, den, raw)):
                cand["staves_from_bar_head_template"] = (
                    template_admitted[(num, den, raw)])
            # ─── END template-at-bar consumer ────────────────────────────────
            if best is None or support > best["support"]:
                best = cand
        if best is None or best["support"] < METER_CHANGE_FLOOR:
            continue
        # ⚠️ THE CAUTIONARY TEST COMES BEFORE THE RESTATEMENT ONE, because a
        # courtesy signature is not a restatement of anything on THIS system —
        # it names the next one, and calling it a restatement would lose it.
        reading = best["staves_reading_it"]
        # ⚠️ ROADMAP 2.72: A GLYPH IN THE TAIL IS A COURTESY BY CONSTRUCTION.
        # `last_cell` is `Q.MEASURE_PARTITION - 1`, and since 2.47b the
        # partition does NOT count the trailing strip a cautionary stands in
        # (`cautionary_tail_not_a_bar`), so on Brahms 1/i p.0 the last BAR is
        # cell 6 and the printed `9/8` courtesy stands in cell 7. The old test
        # (`== cell`) was written when that strip WAS a cell; after 2.47b it
        # never matched, the `9/8` fell through as a CHANGE at a cell that is
        # not a bar, and `_adjacent_corroborated_cautionary` (2.12h) found no
        # `cautionary` on the system before page 1's `9/8` header -- so the
        # misread `9/4` was never weighed against it. A glyph past the last bar
        # needs no bar test: there is no bar there to fit. At the last bar
        # itself the old test stands (a genuine last-bar change is possible
        # and only the bars can say).
        if reading and (
                all(st in last_cell and cell > last_cell[st]
                    for st in reading)
                or (all(last_cell.get(st) == cell for st in reading)
                    and not best["bars_fit"])):
            cautionaries.append(dict(best, cautionary=True))
            continue
        # ⚠️ 2.12d, AND IT COMES BEFORE THE RESTATEMENT TEST FOR THE SAME
        # REASON THE CAUTIONARY TEST DOES: a candidate nobody but one staff
        # printed is not evidence about whether the system changed AT ALL,
        # so it must not be allowed to silently agree with `in_force` either
        # — it is declined outright, on its own terms, before anything asks
        # what it would have meant. Only the SAME-VALUE requirement
        # `METER_CHANGE_MIN_STAVES` already computes into `corroborated`; the
        # bar math stays exactly where A-METER-6 left it, already folded into
        # `support` before a candidate is even a candidate for this gate.
        if not best["corroborated"] and METER_CHANGE_GATES_OWN_SYSTEM:
            declined.append(dict(best, declined_reason=METER_CHANGE_NOT_SYSTEM_WIDE))
            continue
        if (best["numerator"], best["denominator"]) == in_force:
            continue                      # a RESTATEMENT, not a change
        out.append(best)
        in_force = (best["numerator"], best["denominator"])
    # ─── ROADMAP 2.12l: a printed change GATHER never proposed at all ──────
    # ⚠️ AFTER THE MAIN LOOP, NOT INSIDE IT: a cell whose digits were boxed as
    # noteheads has no `readings` for the loop above to visit, refuse or
    # accept, which is exactly the gap this closes.
    # ⚠️ `cells_with_a_candidate`, NEVER THE BARE `by_cell` -- a stray,
    # unreadable `Q.METER_GLYPH` detection (no stacked partner: `loose`, not
    # a `readings` entry) puts a cell in `by_cell` without the main loop ever
    # having evaluated it, and that must not shadow a real cross-staff
    # witness (measured: staff 9's lone `timeSig1` at cell 1 on the Breitkopf
    # fixture is exactly this shape, at the SAME cell the digit witness
    # names).
    # ⚠️ NEVER A CELL THE MAIN LOOP ALREADY SPOKE FOR. `out`'s own from_cells
    # are real, READ changes; a witness at or before the LAST of them is
    # already governed by an actual value and must not be second-guessed by
    # a weaker, value-free fact.
    last_read_cell = max([0] + [c["from_cell"] for c in out])
    for cell, staves in sorted(digit_witnesses.items()):
        if cell in cells_with_a_candidate or cell <= last_read_cell:
            continue
        entry = {"from_cell": cell, "numerator": None,
                "denominator": None, "raw": None,
                "declined_reason": METER_CHANGE_DIGITS_MISREAD,
                "staves_with_digit_witness": list(staves)}
        # ⚠️ ROADMAP 2.29: A CANDIDATE, ABSENT-NOT-ZERO, NEVER A VALUE ON
        # THIS ENTRY'S OWN `numerator`/`denominator`. The digit witness
        # above is still value-free by construction (`is_a_meter_digit`
        # names a PLACE, never a reading); where the OCR reader also read
        # something plausible at this same cell, it rides alongside as a
        # candidate for `_carry_meter` (or a human) to weigh -- see
        # `_ocr_at_bar_candidate_for_cell`'s own docstring.
        ocr_candidate = (ocr_at_bar or {}).get(cell)
        if ocr_candidate is not None:
            entry["ocr_candidate"] = ocr_candidate
        declined.append(entry)
    # ─────────────────────────────────────────────────────────────────────────
    return out, cautionaries, declined


#: Which fields of a change candidate reach the SEGMENT, written ONCE.
#:
#: ⚠️⚠️ THERE ARE TWO SEGMENT-BUILDING SITES — `_with_segments` and
#: `_change_only` — AND THEY EACH HAND-LISTED THESE FIELDS. A-METER-6 added
#: `corroborated` to the first and not the second, so a `change_only` verdict's
#: segment carried no flag, `_meter_in_force_at_end`'s
#: `seg.get("corroborated", True)` read it as an OLD record, and a one-staff
#: change was carried forward exactly as before. Green everywhere: the
#: behavioural test that caught it is the one asserting the walk RUNS OUT.
#:
#: A field list written twice is the *two records of one thing nothing forces
#: to agree* shape this project has paid for repeatedly. Derived once here, so
#: the next field cannot be added to one site only.
#: ⚠️ `staves_from_bar_head_template` is here and is ABSENT-NOT-ZERO by the
#: projection's own `if k in change`: a change the bar-head template reader did
#: not contribute to carries no such key at all, so a flag-off record is
#: byte-identical and a reader cannot mistake *"nothing was admitted"* for
#: *"the mechanism ran and found none"*.
_SEGMENT_FIELDS = ("from_cell", "numerator", "denominator", "raw", "support",
                   "staves_reading_it", "staves_reading_a_meter",
                   "corroborated", "bars_fit", "bars_contradict",
                   "staves_from_bar_head_template")


def _segment_from_change(change: dict) -> dict:
    """One `_meter_changes` candidate, projected onto a `segments` entry."""
    return {k: change[k] for k in _SEGMENT_FIELDS if k in change}


def _with_segments(ev: Evidence, opening: dict) -> dict:
    """The system's meter, plus any change its own evidence supports.

    ⚠️ ONE FACT, NOT TWO. `segments` always exists -- a one-entry list where
    nothing changes -- so a consumer never has to ask whether this system is
    the special case. `record.meter_at` is how a bar's meter is read.
    """
    total_staves = _total_staff_count(ev)
    changes, cautionaries, declined = _meter_changes(
        ev, opening, _bar_lengths_for(ev), _last_cell_per_staff(ev),
        # ─── template-at-bar consumer: `{}` with the flag off ───
        _template_readings_at_bars(ev),
        total_staves=total_staves,
        # ⚠️ ROADMAP 2.12l: fetched HERE, beside `total_staves`, not inside
        # `_meter_changes` -- see that function's own docstring.
        digit_witnesses=_meter_digit_witness_cells(ev, total_staves),
        # ⚠️ ROADMAP 2.29: fetched HERE too, for the SAME reason.
        ocr_at_bar=_ocr_at_bar_candidates(ev))
    # ⚠️ A-METER-6's flag rides along in `_segment_from_change`: a segment still
    # governs THIS system's bars through `record.meter_at` exactly as before,
    # and the flag is read only by `_meter_in_force_at_end`, on the way OFF.
    #
    # ⚠️⚠️ AND SO DOES `staves_from_bar_head_template`, THROUGH THE SAME ONE
    # PROJECTION. This branch arrived with a hand-written dict literal here and
    # a second, patched-on assignment for that field — which had ALREADY
    # dropped it once (the whitelist that did not carry it). That is the exact
    # *a field list written twice* shape `_SEGMENT_FIELDS` was introduced to
    # end, so the merge resolves toward the helper and DELETES the literal. It
    # is also strictly better than what either side had: the field now reaches
    # `_change_only`'s segments too, which the literal never could.
    segments = [dict(opening, from_cell=0)]
    segments.extend(_segment_from_change(c) for c in changes)
    out = dict(opening, segments=segments)
    if cautionaries:
        # ⚠️ ON THE VALUE, NOT IN `detail`, because it is a fact about the
        # music the next system opens with — a consumer reading this system's
        # meter is exactly who needs to find it.
        out["cautionary"] = cautionaries[-1]
    if declined:
        # ⚠️ 2.12d, ON THE VALUE beside `cautionary` for the same reason: a
        # reader of this system's meter is exactly who needs to see what was
        # printed here and refused, not only what took effect. Never read by
        # `meter_at` (segments only) or by `_meter_in_force_at_end` (which
        # strips to a fixed key set), so it cannot leak into a carry.
        out["declined_changes"] = declined
    return out


#: Which verdicts may be carried from, or have their spelling borrowed.
#:
#: ⚠️⚠️ IT WAS `reason == "voted"` ALONE, AND THAT EXCLUDED INK. A
#: `change_only` verdict's value is a meter READ on this system's own staves --
#: `_meter_changes` builds it from `Q.METER_GLYPH` rows and weighs it against
#: the bars -- so refusing it as a source refused exactly the evidence the gate
#: exists to require. Beethoven 5 / Litolff p.62 is the case: it reads the
#: printed `3/4` at the bar the reference names, on a system whose opening is
#: unknown, and no later system could be handed it.
#:
#: ⚠️ WHAT STAYS OUT IS WHAT A CARRY WOULD CHAIN ONTO. `carried` is another
#: system's answer repeated, and `derived_from_bars` is arithmetic with a
#: BORROWED spelling -- neither is ink on the source's own page, so admitting
#: either would make `pages_since_read` a lie about the distance back to ink.
def _meter_in_force_at_end(value: dict, n_cells: int) -> Optional[dict]:
    """The source system's LAST CORROBORATED meter, or None if it has none.

    ⚠️ THE READ-OFF GOES THROUGH `record.meter_at`, which is the whole reason
    that helper exists -- its docstring says it *is* how a bar's meter is read
    and it was called by nothing but its own tests. Asking it for the source's
    last bar is the question a carry has always been asking.

    ⚠️⚠️ AN UNCORROBORATED SEGMENT IS SKIPPED HERE AND ONLY HERE (A-METER-6).
    A change one staff read governs its own system's bars through `meter_at`
    exactly as before; what this refuses is letting it become the meter handed
    to every following system that abstains. The segments are filtered BEFORE
    `meter_at` runs, so the fallback is the previous corroborated meter -- the
    opening, usually -- rather than nothing.

    ⚠️ **None IS A REAL OUTCOME AND IS NOT A FAILURE.** A `change_only`
    verdict's only segment IS the change, so where that change is
    uncorroborated the system has NO meter anyone corroborated and is not a
    carry source at all. Returning the unfiltered value there would reinstate
    exactly the amplification this rule exists to stop, and returning a
    default would be a fallback converting *cannot tell* into a definite
    answer -- the one conversion this project's own rule forbids outright.

    ⚠️ THE SOURCE'S OWN BAR-SCOPED FIELDS ARE STRIPPED, and must be: they
    describe the SOURCE's bar ranges and mean nothing in this system's
    numbering. This system's own segments are added by `_with_segments`, from
    its own ink -- including its own `cautionary`, which is a statement about
    the system AFTER it and travels with neither.
    """
    if not value:
        return None
    segments = value.get("segments")
    if segments:
        # ⚠️ `seg.get("corroborated", True)` -- a segment with no flag is an
        # OPENING (segment 0 never carries one) or a record written before
        # A-METER-6, and neither is a single-staff mid-system change. Defaulting
        # to False there would silently refuse every carry on an older record.
        kept = [s for s in segments if s.get("corroborated", True)]
        if not kept:
            return None
        value = dict(value, segments=kept)
    at_end = meter_at(value, n_cells - 1 if n_cells else 0) or value
    carried = {k: v for k, v in at_end.items()
               if k not in ("segments", "cautionary", "support",
                            "staves_reading_it", "staves_reading_a_meter",
                            "corroborated", "bars_fit", "bars_contradict",
                            "from_cell")}
    # ⚠️⚠️ THE CONTRACT IS *A METER OR NOTHING*, AND SAYING SO TAKES A LINE.
    # Found by a mutation arm: `{"segments": []}` is TRUTHY, so the filter
    # above is skipped, `meter_at` falls back to the value itself and this
    # returned `{}` — which `_carry_meter` tests with `carried is None` and
    # therefore accepts, walking an empty dict into `_corroborate` as though a
    # meter had been handed on. Unreachable today (`_with_segments` always
    # writes the opening), which is why nothing exercised it.
    #
    # "A fallback must never convert *cannot tell* into a definite answer" is
    # about the value a caller READS, so the guard belongs on the way OUT and
    # not only on the way in.
    if carried.get("numerator") is None or carried.get("denominator") is None:
        return None
    return carried


METER_SOURCE_REASONS = ("voted", "change_only")

#: ROADMAP 2.22b: a carried meter DECIDED because the bars were silent (too
#: few assessable, none contradicting) -- Sean 2026-09-28, "a change holds
#: until the plate prints a change back". Not a carry SOURCE (above): a carry
#: still never chains onto a carry.
METER_CARRIED_UNCONTESTED = "carried_uncontested"


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.12k — A CHANGE HOLDS UNTIL A PRINTED CHANGE BACK, AND THE RETURN
# IS ALWAYS PRINTED (Sean, 2026-09-28).
#
# A CORROBORATED CAUTIONARY (2.12h, above) is independent evidence that a
# meter change is printed at `here`'s own opening (cell 0) -- corroborated on
# several staves of the PRECEDING system, not a guess. So where `_carry_meter`
# tries that change as `here`'s candidate and this system's OWN bars cannot
# sustain it -- too few assessable to check at all, or enough to check and
# net against it -- the honest reading is not "the change silently reverted",
# it is "a printed RETURN exists somewhere in this system and we did not read
# it": GATHER produced no glyph for it (measured on Brahms 1/i Breitkopf
# `317803`, `system/1/0` cell 1 -- FINDINGS SS2.12h.b/PART 7 -- a clean, printed
# `6/8` twelve of fourteen staves show by eye and the detector boxes on none).
#
# ⚠️ CONNECT, NEVER GUESS (CLAUDE.md rule 6). This does not name what the
# return prints -- we do not know, and asserting a numerator/denominator we
# never read would be exactly the "cannot tell converted into an answer"
# rule 8 forbids. It renames ONLY the two abstentions `_carry_meter` already
# reaches when `is_cautionary_source` is True, so the fact that a return is
# MISSING is labelled instead of reading identically to any other unrelated
# carry failure (sparse ink, an unrelated page).
#
# ⚠️ WHY §4a PUTS THIS IN ADJUDICATE AND NOT INFER. The carry-weighing this
# rests on (`_carry_meter`/`_corroborate`) already lives here; INFER's own
# harness (`infer._admit`) requires a PRIOR verdict of the SAME quantity at
# the SAME subject to already exist before it may speak, and forces every
# accepted proposal to `Outcome.DECIDED` with a concrete value -- exactly the
# thing rule 4 and rule 8 both forbid once the value is "a meter we never
# read". Staying an ABSTENTION, merely a more informative one, is what keeps
# this an ADJUDICATE fact: "it can read it; else abstains" -- and this still
# abstains, it just names WHY precisely enough for export to act on it.
#
# ⚠️ THE CELL IS ALWAYS 1, NOT A BRAHMS-SPECIFIC NUMBER.
# `_adjacent_corroborated_cautionary` only ever names `here`'s own OPENING
# (cell 0) -- see its own docstring -- so the first bar this system's
# abstention does NOT independently confirm is always the very next one.
METER_RETURN_NOT_READ_REASON = "meter_return_not_read"
METER_RETURN_MARK_CELL = 1
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.12h — A CAUTIONARY NAMES THE VERY NEXT SYSTEM'S OPENING.
#
# A-METER-5 already reads and RECORDS a courtesy signature (`cautionary` on
# the value, never a segment of the printing system's own bars) with the
# comment that consuming it "belongs with the carry" — but nothing ever did.
# Brahms 1 / Breitkopf, whole-movement: `system/0/0`'s last cell corroborates
# a `9/8` cautionary at support 26.5 on 9 of 14 staves (measured, not a
# fixture number); `system/1/0` — the very next system — VOTES its own
# opening unanimously (10 of 10 staves that spoke) at `9/4`, and every one of
# those 10 template readings carries a THIN margin over its own runner-up
# (0.04-0.09, never `9/8`) with a score barely over `min_score`. A print crop
# of the header (`benchmarks/omr-shape-role-2026-09/out/print/
# m212h-brahms1-breitkopf/`) shows `9/8` engraved, not `9/4` — the "9" is
# right, the denominator "8" is not.
#
# ⚠️ THE TEMPLATE READER'S OWN SCORE FOR A GENUINE `9/8` CANDIDATE IS NOT ON
# THE RECORD AT ALL — `LocatedTimeSignature` keeps only the WINNER and its
# single runner-up, so an ADJUDICATE-only fix cannot "pick a better
# candidate" out of what GATHER wrote down; it can only WEIGH the vote
# against a DIFFERENT witness already on the record. The cautionary is
# exactly that witness: read from a different crop, on more staves, at
# higher support, by the same per-staff template reader.
#
# ⚠️ CONNECT, NEVER GUESS (CLAUDE.md rule 6). This does not adopt the
# cautionary on its own say-so — a corroborated courtesy signature could
# itself be a misread. It reroutes a vote that CONTRADICTS one through the
# existing fallback ladder, where `_carry_meter` weighs the cautionary
# against THIS system's own bars via `_corroborate` exactly as any other
# carry candidate is weighed (`METER_CARRY_FLOOR`, `METER_CARRY_MIN_BARS`) —
# the same safety net that already refuses a bad carry
# (`carry_outweighed_by_the_bars`). A vote is never simply overruled; it is
# RECHECKED against a witness the vote itself cannot see, and if the bars
# refuse the cautionary too the system ABSTAINS (rule 8: never converts
# "cannot tell" into an answer) rather than asserting either one.
#
# ⚠️ ADJACENCY, NOT "nearest system with a decided meter". A cautionary is a
# statement about the system directly after it and nothing farther — so only
# the STRICT immediate predecessor in document order (by page then system,
# `Subject`'s own ordering) may ever supply one, never a system `_carry_meter`
# had to walk past an abstention to reach.
# ─────────────────────────────────────────────────────────────────────────────


def _movement_spans(ev: Evidence) -> tuple:
    """ROADMAP 4.2: the declared `Q.MOVEMENT_SPANS` fact, empty with none
    supplied (the single-movement default).

    ⚠️ READ HERE, IN THIS MODULE, RATHER THAN THROUGH `movements.
    spans_from_evidence` (which does not exist for exactly this reason).
    `inventory --check` and `wiring --check` both trace a decision's reads by
    walking helpers defined in ITS OWN FILE; a call that crossed into
    `movements.py` would be invisible to either tool and `Q.MOVEMENT_SPANS`
    would report as an inert, unreachable declaration on `adjudicate_meter`
    even though this line reads it every time.

    ⚠️ ROADMAP 4.2b, THE FALLBACK ADDED BELOW. A human `--movements` is filed
    at GATHER time as an OBSERVATION on this exact subject/quantity, and
    `ev.rows()` reads it -- so where one was given, it is returned first and
    ALWAYS (CLAUDE.md rule 3: a human always wins over detection, and the
    `if rows:` below never even looks at the alternative). Where none was
    given, `adjudicators.movement.adjudicate_movement_start` may have
    DECIDED a detected set of spans -- filed as a VERDICT on the same
    subject/quantity, not an observation, because it runs in ADJUDICATE and
    ADJUDICATE reads no raster. `ev.verdict()` is declared through the SAME
    `wants=(..., Q.MOVEMENT_SPANS)` this function's `rows()` call already
    requires, so no new declaration was needed; what makes the fallback
    reachable at all is `adjudicate.ORDER` running `movement_start` before
    `adjudicate_meter` -- see the comment on `Q.MOVEMENT_SPANS` at the top of
    that list.
    """
    rows = ev.rows(Q.MOVEMENT_SPANS, subject=DOCUMENT)
    if rows:
        return tuple(rows[0].value or ())
    verdict = ev.verdict(Q.MOVEMENT_SPANS, subject=DOCUMENT)
    if verdict is not None and verdict.outcome is Outcome.DECIDED:
        return tuple(verdict.value or ())
    return ()


def _adjacent_corroborated_cautionary(ev: Evidence,
                                      here: Subject) -> Optional[Dict[str, Any]]:
    """The STRICT immediate predecessor system's cautionary, if corroborated.

    None where `here` is the document's first system, where the predecessor's
    own meter is not DECIDED, or where it decided one but printed no
    cautionary — or printed one no second staff confirmed (A-METER-6's own
    `corroborated` flag, computed once by `_meter_changes` and read here
    rather than re-derived).

    ⚠️ ROADMAP 4.2: ALSO None ACROSS A MOVEMENT BOUNDARY. A courtesy
    signature announces the very next system's opening — but where `--
    movements` has drawn a boundary between the two, "the very next system"
    is a different movement's first system, and a meter/key carry may never
    cross one (CLAUDE.md §1). With no `Q.MOVEMENT_SPANS` fact on the record
    `_movements.same_movement` is always True, so a record with no
    `--movements` is unaffected.
    """
    all_systems = ev.subjects(Kind.SYSTEM)
    try:
        idx = all_systems.index(here)
    except ValueError:
        return None
    if idx <= 0:
        return None
    prev = all_systems[idx - 1]
    spans = _movement_spans(ev)
    if not _movements.same_movement(spans, here, prev):
        return None
    found = ev.verdict(Q.METER, subject=prev)
    if found is None or found.outcome is not Outcome.DECIDED:
        return None
    caution = (found.value or {}).get("cautionary")
    if not caution or not caution.get("corroborated"):
        return None
    num, den = caution.get("numerator"), caution.get("denominator")
    if not num or not den:
        return None
    return {"numerator": int(num), "denominator": int(den),
            "raw": caution.get("raw") or f"{num}/{den}",
            "source": prev.to_key(),
            "support": caution.get("support"),
            "staves_reading_it": caution.get("staves_reading_it")}


def _carry_meter(ev: Evidence, instead_of: str) -> Optional[Ruling]:
    """The nearest preceding system whose meter was READ, or None.

    ⚠️ A CARRY NEVER CHAINS ONTO A CARRY. Only a `voted` verdict is a source,
    so `pages_since_read` is the true distance back to ink rather than the
    distance to whoever last repeated the answer. That is what makes the
    number in the record worth reading: a meter carried 16 pages is visibly
    suspect where a chain of 16 one-page hops would each look local.

    ⚠️ It is also why this needs no reach constant of its own -- see
    the `_carry_meter` note on the carry's hazard, where the reach bound is refuted outright.

    ⚠️⚠️ ROADMAP 4.2: A CARRY NEVER CROSSES A `--movements` BOUNDARY. Walking
    backward through the document's systems STOPS outright (not merely
    "skips") the first time it steps into a movement earlier than `here`'s --
    movements are contiguous, non-overlapping page/system ranges, so every
    system further back is in that SAME earlier movement or one earlier
    still, and none of them may answer for `here`. With no `Q.MOVEMENT_SPANS`
    fact on the record `_movements.same_movement` is always True, so this is
    a no-op on a record with no `--movements` -- exactly the pre-4.2 walk.
    """
    here = ev.subject
    spans = _movement_spans(ev)
    #: Sources walked PAST because A-METER-6 left them nothing carryable.
    #: ⚠️ A page with no carry source and a page that walked past one are two
    #: different pages and must not read the same in the log.
    skipped_uncorroborated: list = []
    # ⚠️ 2.12h, computed ONCE: the strict immediate predecessor's corroborated
    # cautionary, if any. See the block comment above
    # `_adjacent_corroborated_cautionary` for why this is safe to prefer over
    # "in force at end" on its OWN named system only.
    adjacent_caution = _adjacent_corroborated_cautionary(ev, here)
    for src in reversed([s for s in ev.subjects(Kind.SYSTEM) if s < here]):
        if not _movements.same_movement(spans, here, src):
            # ⚠️ BREAK, NOT CONTINUE. Every system before `src` in document
            # order is in `src`'s movement or an earlier one, never `here`'s.
            break
        found = ev.verdict(Q.METER, subject=src)
        if found is None or found.outcome is not Outcome.DECIDED:
            continue
        if found.reason not in METER_SOURCE_REASONS:
            continue
        pages = (here.page or 0) - (src.page or 0)
        # ⚠️ 2.12h: THIS source, and only this one, may be the cautionary's
        # own named system -- `_adjacent_corroborated_cautionary` already
        # checked strict adjacency and corroboration, so nothing here
        # re-derives either.
        is_cautionary_source = (adjacent_caution is not None
                                and adjacent_caution["source"] == src.to_key())
        # ⚠️ ROADMAP 2.12l: `src`'s OWN recorded value, read back (no second
        # query -- `_meter_changes` already filed it there). `None` where
        # `src` printed no unread digit change, which is the common case.
        digit_misread = (_carry_source_digit_misread(found.value)
                         if not is_cautionary_source else None)
        # ⚠️⚠️ THE SECOND WITNESS, AND IT IS WHAT MAKES THE CARRY SAFE
        # WITHOUT A MOVEMENT DETECTOR. A carried meter is a CANDIDATE; this
        # system's own bars confirm or refuse it. A movement boundary needs no
        # detecting because the new movement's bars simply contradict the old
        # movement's meter -- measured 8 agree / 1 disagree on a continuation
        # page and 1 / 7 on the Andante.
        # ⚠️⚠️ THE CANDIDATE IS THE SOURCE'S *END* METER, NOT ITS OPENING.
        # The old `{k: v for k, v in found.value.items() if k != "segments"}`
        # handed on the meter a source had already STOPPED being in -- Brahms
        # 1 i passed the ONE-bar `9/8` that opens its source instead of the
        # `6/8` governing seven of eight bars, and Brahms 1 iv passed `C`
        # instead of the `¢` the same system had just read on 24 staves of 24.
        #
        # ⚠️ AND CORROBORATING THE OPENING WAS THE SAME BUG'S SECOND HALF:
        # reading the end meter only AFTER the check left the carry weighing a
        # meter it was not going to carry, so a correct carry was refused
        # `carry_outweighed_by_the_bars` at -2.0, 0 agreeing / 3 disagreeing.
        #
        # ⚠️ The cell count is fetched HERE and passed down, not read inside
        # the helper -- the same shape `_meter_changes` uses for `bars` and
        # `last_cell`, and for the same reason: `inventory._never_read`
        # follows a decision's own helpers to depth 3, and a `Q.` read one
        # link further reads as an INERT declaration.
        n_cells = 0
        for mp in ev.verdicts(Q.MEASURE_PARTITION,
                              scope=Scope.SELF_AND_DESCENDANTS, subject=src):
            if mp.outcome is Outcome.DECIDED and isinstance(mp.value, int):
                n_cells = max(n_cells, mp.value)
        # ⚠️ 2.12h: THE COURTESY SIGNATURE OUTRANKS "in force at end" ON ITS
        # OWN NAMED SYSTEM. A cautionary states what `here` opens with
        # directly; `_meter_in_force_at_end` only ever answers what the
        # SOURCE's own bars were doing, which is a different question the
        # moment a change is printed between them.
        if is_cautionary_source:
            carried = {"numerator": adjacent_caution["numerator"],
                      "denominator": adjacent_caution["denominator"],
                      "raw": adjacent_caution["raw"]}
        else:
            carried = _meter_in_force_at_end(found.value, n_cells)
        if carried is None:
            # ⚠️ A-METER-6: this source's only meter is a change ONE staff
            # read, so it has nothing anyone corroborated to hand on. Keep
            # walking back — a source with no carryable meter is not a source,
            # the same treatment `METER_SOURCE_REASONS` gives a `carried` one.
            # ⚠️ RECORDED, NOT SILENT: skipping is a decision, and a page that
            # found no source at all and a page that walked past one must not
            # read the same in the log.
            skipped_uncorroborated.append(src.to_key())
            continue
        check = _corroborate(ev, carried)
        if "terms" not in check:
            # ⚠️ ROADMAP 2.12k: TOO FEW BARS TO CHECK THE CAUTIONARY'S OWN
            # CHANGE AGAINST IS STILL "the change could not be sustained
            # here", not a different fact. See the block comment above
            # `METER_RETURN_NOT_READ_REASON`.
            if is_cautionary_source:
                return Ruling.abstain(METER_RETURN_NOT_READ_REASON,
                                      carried_from=src.to_key(),
                                      pages_since_read=pages,
                                      instead_of=instead_of,
                                      carried_via_cautionary=is_cautionary_source,
                                      skipped_uncorroborated=skipped_uncorroborated,
                                      at_cell=METER_RETURN_MARK_CELL,
                                      **check)
            # ⚠️ ROADMAP 2.12l: THE SAME LABELLING 2.12k USES ABOVE, for a
            # DIFFERENT, specifically-known cause -- `src` itself recorded a
            # printed change its own digits could not be read at, so "too
            # few bars to check the carry against" is not a generic gap here,
            # it is the same gap that change witnessed.
            #
            # ⚠️⚠️ ROADMAP 2.46: THIS MUST NOT FIRE WHERE `here`'S OWN (too
            # few to reach `_corroborate`'s floor) BARS ALREADY AGREE WITH
            # THE CARRY AND NONE DISAGREE. CLAUDE.md §10: "the carry is
            # WEIGHED by the bars, not gated" -- a witness on `src`, however
            # many systems back, is evidence about the SOURCE's own next bar,
            # not a standing veto over every later system regardless of what
            # its own ink says. Measured on the whole-movement Brahms record
            # (`benchmarks/omr-meter-digits-2026-09/FINDINGS.md` ROADMAP
            # 2.46): before this gate, `system/1/1` (`bars_agree: 1,
            # bars_disagree: 0`) and `system/6/0` (same) were abstained
            # `meter_change_digits_misread` citing a witness on `system/0/0`
            # -- 25+ systems back -- despite their OWN one assessable bar
            # fitting the carry 1-for-1. `clean_here` is exactly the test
            # `METER_RETURN_NOT_READ_REASON`'s own sibling branch below
            # already uses for "no vote against the carry" (`not
            # check.get("bars_disagree")`), tightened to also require at
            # least one bar that DID agree -- a page with literally nothing
            # to say falls through to 2.22b's `carried_uncontested`, not to
            # silence being read as corroboration for THIS branch specifically.
            clean_here = bool(check.get("bars_agree")) and not check.get("bars_disagree")
            if digit_misread is not None and not clean_here:
                # ⚠️ ROADMAP 2.29: THE OCR CANDIDATE RIDES ALONG, STILL NOT
                # DECIDED. `digit_misread["ocr_candidate"]` (absent, not
                # `None`, where the OCR reader never read this cell -- see
                # `_ocr_at_bar_candidate_for_cell`) is a NAME for what the
                # carry ladder or a human should look at next, not a value
                # this abstention asserts. `Ruling.abstain` refuses `value`
                # by construction (`record.Verdict.__post_init__`), so
                # surfacing it in `detail` is the only way to weigh it
                # without silently deciding it here.
                extra = {}
                if "ocr_candidate" in digit_misread:
                    extra["ocr_candidate"] = digit_misread["ocr_candidate"]
                return Ruling.abstain(METER_CHANGE_DIGITS_MISREAD,
                                      carried_from=src.to_key(),
                                      pages_since_read=pages,
                                      instead_of=instead_of,
                                      carried_via_cautionary=is_cautionary_source,
                                      skipped_uncorroborated=skipped_uncorroborated,
                                      digit_misread_at_cell=digit_misread["from_cell"],
                                      **extra, **check)
            # ⚠️⚠️ ROADMAP 2.22b: WHERE THE BARS ARE SILENT, THE CARRY HOLDS.
            # Sean, 2026-09-28 (DECISIONS): "a meter change holds until the
            # plate prints a change back"; CLAUDE.md §10: "the carry is
            # WEIGHED by the bars, not gated". Too few assessable bars is
            # not a vote against the carry -- it is no vote -- so a system
            # that READ nothing of its own (`no_evidence`), whose one or
            # two speaking bars contradict nothing, and on which no printed
            # change was witnessed unread, is IN the meter it was carried
            # into. Applied by the manager from Sean's recorded words
            # (FINDINGS §17g); the question stays open in
            # `held-mvt-2026-09-29-W-manifest.json` for him to overturn.
            # Still ABSTAINED, each with its own reason: a bar that DOES
            # contradict it (not silent); a system whose own staves read a
            # meter-shaped thing (`instead_of` other than `no_evidence`);
            # a printed change witnessed here but unread (2.12l's digit
            # witness, below); the two labelled cases above (2.12k's
            # cautionary return, 2.12l's witness on the source); and a
            # carry never crosses a movement boundary (the walk above
            # BREAKS at one, 4.2).
            if instead_of == "no_evidence" and not check.get("bars_disagree"):
                value = _with_segments(ev, carried)
                unread_here = _carry_source_digit_misread(value)
                if unread_here is None:
                    return Ruling(value=value, reason=METER_CARRIED_UNCONTESTED,
                                  used=(found.id,), margin=W_METER_CARRIED,
                                  detail={"carried_from": src.to_key(),
                                          "pages_since_read": pages,
                                          "instead_of": instead_of,
                                          "carried_via_cautionary":
                                              is_cautionary_source,
                                          "skipped_uncorroborated":
                                              skipped_uncorroborated,
                                          **check})
                return Ruling.abstain(
                    "carry_not_corroborated", carried_from=src.to_key(),
                    pages_since_read=pages, instead_of=instead_of,
                    carried_via_cautionary=is_cautionary_source,
                    skipped_uncorroborated=skipped_uncorroborated,
                    unread_change_on_this_system_at_cell=unread_here["from_cell"],
                    **check)
            return Ruling.abstain("carry_not_corroborated",
                                  carried_from=src.to_key(),
                                  pages_since_read=pages,
                                  instead_of=instead_of,
                                  carried_via_cautionary=is_cautionary_source,
                                  skipped_uncorroborated=skipped_uncorroborated,
                                  **check)
        # ⚠️ THE CARRY IS A TERM, NOT A DECISION. It enters the sum on the
        # same footing as the bars and can be outweighed by them.
        terms = [Term("carried_from_read_meter", W_METER_CARRIED,
                      (found.id,))] + check["terms"]
        support = tally(terms)
        detail = {"carried_from": src.to_key(),
                  "pages_since_read": pages,
                  "instead_of": instead_of,
                  # ⚠️ 2.12h: WHICH FACT of the source travelled -- its own
                  # in-force meter, or the courtesy signature naming `here`
                  # directly -- because the two answer different questions
                  # and a reader must be able to tell them apart.
                  "carried_via_cautionary": is_cautionary_source,
                  "source_share": (adjacent_caution.get("support")
                                   if is_cautionary_source
                                   else (found.detail or {}).get("share")),
                  "source_staves_spoke":
                      (len(adjacent_caution.get("staves_reading_it") or [])
                       if is_cautionary_source
                       else (found.detail or {}).get("n_staves_spoke")),
                  "support": round(support, 3),
                  "floor": METER_CARRY_FLOOR,
                  "bars_agree": check["bars_agree"],
                  "bars_disagree": check["bars_disagree"],
                  "bar_lengths_seen": check["bar_lengths_seen"],
                  "skipped_uncorroborated": skipped_uncorroborated}
        if support < METER_CARRY_FLOOR:
            # ⚠️ Its own reason, and the SUPPORT is on the record beside it: a
            # carry the bars outweighed, a carry with nothing to check against
            # and a page with no carry available are three different pages,
            # and a reader must be able to tell them apart.
            #
            # ⚠️ ROADMAP 2.12k: WHERE THE BARS THEMSELVES OUTWEIGH THE
            # CAUTIONARY'S OWN CONFIRMED CHANGE, that is the literal case the
            # roadmap item names -- "where the bars overturn a CARRIED meter
            # change". See `METER_RETURN_NOT_READ_REASON`'s block comment.
            if is_cautionary_source:
                return Ruling.abstain(METER_RETURN_NOT_READ_REASON,
                                      at_cell=METER_RETURN_MARK_CELL, **detail)
            # ⚠️ ROADMAP 2.12l: see the identical branch above -- `src` itself
            # named the cause, so the generic "the bars outweighed it" is not
            # the truest thing to say here either.
            if digit_misread is not None:
                return Ruling.abstain(
                    METER_CHANGE_DIGITS_MISREAD,
                    digit_misread_at_cell=digit_misread["from_cell"], **detail)
            return Ruling.abstain("carry_outweighed_by_the_bars", **detail)
        # ⚠️ A CARRIED METER IS STILL SUBJECT TO A CHANGE PRINTED ON THIS
        # SYSTEM. The carry says what the music was doing; a time signature
        # standing at bar N says it stopped doing it there.
        return Ruling(value=_with_segments(ev, carried), reason="carried",
                      used=(found.id,), margin=support, detail=detail)
    if skipped_uncorroborated:
        # ⚠️ A-METER-6, and this is the ONLY path where the rule alone changes
        # the OUTCOME rather than the value carried: every source back to the
        # start of the document had nothing corroborated to hand on. Before
        # this rule that page took a single staff's reading and spread it
        # forward; now it abstains, NAMING the sources it walked past.
        # ⚠️ `_meter_fallbacks` prefers this over `_change_only`'s bare
        # "nothing here", which is its own documented ordering — the most
        # INFORMATIVE refusal, not the last one tried.
        return Ruling.abstain("carry_source_uncorroborated",
                              instead_of=instead_of,
                              skipped_uncorroborated=skipped_uncorroborated)
    return None


def _bars_opinion(ev: Evidence) -> dict:
    """What this system's OWN bars say about their length, on their own.

    ⚠️ NO CANDIDATE IS SUPPLIED, which is what separates this from
    `_corroborate`. There the bars answer *"is it 2/4?"*; here they answer
    *"what is it?"*, and the difference is that a wrong answer cannot be
    inherited from somewhere else -- the reach of this reader is exactly one
    system.
    """
    bars = _bar_lengths_for(ev)
    voted = []
    for cell_index, lengths in sorted(bars.items()):
        if len(lengths) < METER_CARRY_MIN_STAVES_PER_BAR:
            continue
        mode, n = Counter(lengths).most_common(1)[0]
        if n / len(lengths) < 0.5:
            continue                 # the staves do not agree with EACH OTHER
        voted.append(round(mode, 6))
    seen = Counter(voted)
    if not voted:
        return {"state": "no_assessable_bars", "bars_assessable": 0,
                "bar_lengths_seen": {}}
    # ⚠️ ONLY A LENGTH SOME METER PRINTS may stand for election. See
    # `_METER_LENGTHS`.
    plausible = Counter({length: n for length, n in seen.items()
                         if length in _METER_LENGTHS})
    if not plausible:
        return {"state": "no_plausible_length",
                "bars_assessable": len(voted),
                "bar_lengths_seen": dict(seen.most_common(6))}
    # ⚠️ A TIE HERE IS RESOLVED BY FIRST APPEARANCE, and it does not matter:
    # a tie means no length dominates, so whichever is chosen scores at or
    # below (n/2 - n/2) = 0 and the floor refuses it. This is the *Andante*'s
    # own case -- 3.0, 3.5 and 1.5 at one bar each.
    length, _ = plausible.most_common(1)[0]
    scored = _score_bars(bars, length)
    if "terms" not in scored:
        return dict(scored, state="too_few_assessable_bars")
    return {"state": "named", "length": length,
            "support": round(tally(scored["terms"]), 3),
            "floor": METER_FROM_BARS_FLOOR,
            "terms": scored["terms"],
            "bars_assessable": len(voted),
            "bars_agree": scored["bars_agree"],
            "bars_disagree": scored["bars_disagree"],
            "bar_lengths_seen": scored["bar_lengths_seen"]}


def _form_for_length(ev: Evidence, length: float) -> Optional[dict]:
    """A preceding system that READ a meter of exactly this length, if any.

    ⚠️ THE BARS NAME THE LENGTH; THE ENGRAVING IS BORROWED. `2/4` and `4/8`
    are one bar length and two printings, and no arithmetic separates them --
    so the spelling comes from a system that actually saw one, on the same
    "only ink is a source" discipline `_carry_meter` uses (`reason == "voted"`
    and nothing else, so a borrow can never chain onto a borrow).

    ⚠️⚠️ THE LETTER IS DELIBERATELY NOT BORROWED. `raw` reaches
    `staged.export` as `symbol="common"` / `"cut"`, which is a positive claim
    that a `C` is PRINTED on this system -- and this system printed nothing we
    could read. So the borrowed meter is spelled in digits and the source's
    own `raw` is recorded beside it rather than copied. The same distinction
    `export._mxl_attributes_block` already makes for `rhythm._propagated_meter`.

    ⚠️ ROADMAP 4.2: THE SAME MOVEMENT-BOUNDARY STOP `_carry_meter` USES. A
    borrowed spelling is still a carry in every sense CLAUDE.md §1 means by
    the word, and must not reach across a `--movements` boundary either.
    """
    here = ev.subject
    spans = _movement_spans(ev)
    for src in reversed([s for s in ev.subjects(Kind.SYSTEM) if s < here]):
        if not _movements.same_movement(spans, here, src):
            break
        found = ev.verdict(Q.METER, subject=src)
        if found is None or found.outcome is not Outcome.DECIDED:
            continue
        if found.reason not in METER_SOURCE_REASONS:
            continue
        # ⚠️ EVERY SEGMENT OF THE SOURCE IS ELIGIBLE, NOT JUST ITS OPENING. A
        # system that printed `6/8` and changed to `9/8` READ BOTH, so both are
        # spellings this document has evidence for; asking only the top-level
        # fields silently skips a source whose opening happens to be the wrong
        # length while the meter it changed TO is the right one.
        val = found.value or {}
        for seg in (val.get("segments") or [val]):
            num, den = seg.get("numerator"), seg.get("denominator")
            if not num or not den:
                continue
            if abs(float(num) * 4.0 / float(den) - length) > 1e-6:
                continue
            return {"numerator": int(num), "denominator": int(den),
                    "source": src.to_key(), "source_raw": seg.get("raw"),
                    "source_id": found.id}
    return None


def _meter_from_bars(ev: Evidence, instead_of: str) -> Optional[Ruling]:
    """This system's own bars, asked what the meter is. Default OFF.

    ⚠️ IT RUNS ONLY WHERE THE READING AND THE CARRY BOTH FAILED, so it can
    never overturn ink and never overturn a carry the bars already weighed.

    ⚠️ IT CANNOT CROSS A MOVEMENT BOUNDARY, and that is the structural reason
    it is a different mechanism from the carry rather than a second copy of
    it. Every term comes from bars inside this one system, so the *Andante*'s
    first system cannot be handed movement 1's `2/4` by this route however
    many pages of `2/4` precede it -- its own four bars read four different
    lengths and it scores -2.0. The only thing that reaches back is the
    SPELLING, and that is gated on the length already matching.
    """
    op = _bars_opinion(ev)
    if op["state"] != "named":
        return None                   # the caller's own abstention stands
    # ⚠️ The `Term` objects are dropped before `op` becomes record `detail`:
    # the SUPPORT and the counts are what a reader needs, and a Term does not
    # serialise. Their sum is already in `op["support"]`.
    op.pop("terms")
    if op["support"] < METER_FROM_BARS_FLOOR:
        # ⚠️ Falls THROUGH rather than abstaining here: a system whose bars
        # name nothing may still print a change, and `_change_only` is what
        # finds it.
        return None
    form = _form_for_length(ev, op["length"])
    if form is None:
        # ⚠️ A REAL ANSWER, NOT A GAP: *"these bars are 3.0 quarter-notes
        # long and nothing on this document has told us whether that is
        # printed 3/4, 6/8 or 12/16"*. Still routed through `_change_only`,
        # because a printed change on this same system is evidence this
        # reader does not have.
        return _change_only(ev, "bars_name_a_length_without_a_form",
                            instead_of=instead_of,
                            candidate_forms=[f"{n}/{d}" for n, d
                                             in _METER_LENGTHS[op["length"]]],
                            **op)
    opening = {"numerator": form["numerator"],
               "denominator": form["denominator"],
               "raw": f"{form['numerator']}/{form['denominator']}"}
    detail = {"instead_of": instead_of,
              "form_borrowed_from": form["source"],
              "form_source_raw": form["source_raw"], **op}
    return Ruling(value=_with_segments(ev, opening), reason="derived_from_bars",
                  used=(form["source_id"],), margin=op["support"],
                  detail=detail)


def _change_only(ev: Evidence, why: str, **detail) -> Ruling:
    """A system whose OPENING meter is unknown but which prints a CHANGE.

    ⚠️ THIS IS THE RANGE-SCOPED FACT EARNING ITS KEEP. Beethoven 5 / Litolff
    p.62 reads a usable meter on 2 staves of 17 -- far under the coverage
    floor -- so the system abstains and a system-scoped meter would have had
    nowhere to put the `3/4` its print states plainly at bar 155. As segments
    it says the true thing: *unknown until bar 8, 3/4 from there*.
    """
    total_staves = _total_staff_count(ev)
    changes, cautionaries, declined = _meter_changes(
        ev, {}, _bar_lengths_for(ev), _last_cell_per_staff(ev),
        # ─── template-at-bar consumer: `{}` with the flag off ───
        _template_readings_at_bars(ev),
        total_staves=total_staves,
        # ⚠️ ROADMAP 2.12l: see `_with_segments`'s identical fetch.
        digit_witnesses=_meter_digit_witness_cells(ev, total_staves))
    if cautionaries:
        detail = dict(detail, cautionary=cautionaries[-1])
    if declined:
        # ⚠️ 2.12d. A system whose ONLY candidate meter fact was a lone-staff
        # change now has NOTHING left once that candidate is declined — the
        # abstention below is real, not a gap, and `why` (the reason its
        # OPENING was never read either) is still the truest thing to say:
        # the system read nothing usable anywhere. `declined_changes` says
        # what was printed and refused, so the two are not the same abstain.
        detail = dict(detail, declined_changes=declined)
    if not changes:
        return Ruling.abstain(why, **detail)
    first = changes[0]
    # ⚠️ `_segment_from_change`, NOT a second hand-written field list — see its
    # docstring: this site is where A-METER-6's flag was silently missing.
    segments = [_segment_from_change(c) for c in changes]
    return Ruling(value={"numerator": first["numerator"],
                         "denominator": first["denominator"],
                         "raw": first["raw"], "segments": segments},
                  reason="change_only",
                  detail={"opening_unknown_because": why,
                          "n_changes": len(changes), **detail})


def _meter_fallbacks(ev: Evidence, why: str, **detail) -> Ruling:
    """Everything to try when this system's own READING failed, in order.

    ⚠️⚠️ AN ABSTENTION IS NOT AN ANSWER, AND CHAINING THESE WITH `or` TREATED
    IT AS ONE. `_carry_meter` returns a `Ruling` both when it decides and when
    the bars OUTWEIGH it, and both are truthy -- so `a() or b() or c()`
    stopped at a refusal and never asked the later rungs. Measured on
    Beethoven 5 / Litolff p.63, which is exactly the case the mechanisms exist
    for: the carried `2/4` is refused at **-6.0 (1 agree / 8 disagree)** and
    **-7.0 (0/8)**, and with `OMR_METER_FROM_BARS` also on the page STILL
    abstained `carry_outweighed_by_the_bars` -- because the bar reader was
    unreachable behind the refusal it had itself caused. Off its own flag the
    same page names **length 3.0 at +5.0**, which is the printed 3/4.

    ⚠️ IT ALSO COST THE PRINTED CHANGE. `_change_only` sat behind the same
    `or`, so a system whose carry was refused could not report a meter change
    printed on it either. That half predates `OMR_METER_FROM_BARS`.

    So the order is by WHAT EACH KNOWS, and a refusal never blocks a rung that
    might know more:

      1. a CARRY the bars corroborated -- it names an engraving that was read;
      2. this system's OWN BARS -- self-checking arithmetic, which is why it
         outranks a carry the same bars just refused (Sean's ordering);
      3. a CHANGE printed on this system;
      4. failing all three, the most INFORMATIVE refusal, which is not the
         last one tried: a refusal naming the bar length beats one naming only
         the carry's support, which beats a bare "nothing here".
    """
    carried = _carry_meter(ev, why)
    if carried is not None and not carried.abstained:
        return carried
    from_bars = _meter_from_bars(ev, why)
    if from_bars is not None and not from_bars.abstained:
        return from_bars
    changed = _change_only(ev, why, **detail)
    if not changed.abstained:
        return changed
    return from_bars or carried or changed


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.29 — a SECOND, INDEPENDENT reader of the system's OPENING meter.
# `meter_digit_ocr` OCRs the numerator/denominator halves of the SAME header
# crop `Q.METER_TEMPLATE`'s own NCC match already read; see that module's
# docstring for why the two readers' failure modes do not correlate (shape
# match vs. stroke topology) rather than merely asserting it here.
# ─────────────────────────────────────────────────────────────────────────────


def _ocr_opening_reading(ev: Evidence) -> Optional[Tuple[int, int, float, tuple]]:
    """`(numerator, denominator, share, witness_rows)` for the OCR reader's
    OWN majority reading of this system's opening, or `None` where it read
    nothing at all. ⚠️ NO coverage/agreement floor of its own -- this reader
    has no measured floor yet (CLAUDE.md rule 5: reach before accuracy), so
    `adjudicate_meter` decides what a disagreement means; this only reports
    what was read."""
    rows = ev.rows(Q.METER_OCR, scope=Scope.SELF_AND_DESCENDANTS)
    if not rows:
        return None
    tally: dict = {}
    for row in rows:
        v = row.value
        if not isinstance(v, (list, tuple)) or len(v) != 2:
            continue
        tally.setdefault((int(v[0]), int(v[1])), []).append(row)
    if not tally:
        return None
    best, witnesses = max(tally.items(), key=lambda kv: len(kv[1]))
    return best[0], best[1], len(witnesses) / len(rows), tuple(witnesses)


def _bar_corroboration_margin(ev: Evidence, candidate: dict) -> Optional[float]:
    """Net signed support (`Term.weight` summed) this system's own bars give
    `candidate`, via the SAME `_corroborate` the carry ladder already uses --
    never a second arbiter. `None` where the bars have nothing assessable to
    say (too few bars, or no candidate), which `adjudicate_meter` treats as
    "the bars did not settle it", never as a zero."""
    check = _corroborate(ev, candidate)
    terms = check.get("terms")
    if terms is None:
        return None
    return sum(t.weight for t in terms)


@decision(
    quantity=Q.METER,
    checkable=Checkable.MIXED,
    checked_by=(
        '"bar sum, on every bar of every staff it governs"',
        '"a meter is a SYSTEM fact: a mid-staff change no other staff witnessed is a misread (21 fired on scans, 0 survive)"',
    ),
    implicates=(Q.METER, Q.DURATION, Q.MEASURE_PARTITION),
    composed_from=(Q.METER_GLYPH, Q.METER_TEMPLATE, Q.METER_TEMPLATE_AT_BAR,
                   # ⚠️ ROADMAP 2.29: a SECOND, INDEPENDENT reader of the
                   # opening (`Q.METER_OCR`) and of a mid-bar change,
                   # including a 2.12l witness cell with no template
                   # reading at all (`Q.METER_OCR_AT_BAR`, read back by
                   # `_meter_digit_witness_cells`).
                   Q.METER_OCR, Q.METER_OCR_AT_BAR,
                   Q.DURATION,
                   # ⚠️ ROADMAP 2.12l: `_meter_digit_witness_cells` finds its
                   # candidates from `Q.GLYPH_BOX`/`Q.CELL_STAFF_SPACE` (plain
                   # GATHER facts, read broadly and safely) and confirms only
                   # the survivors against THIS decision's own verdict, one
                   # subject at a time -- never a raster of its own.
                   Q.GLYPH_BOX, Q.CELL_STAFF_SPACE,
                   Q.NOTEHEAD_IS_NOT_A_NOTEHEAD),
    scope=Kind.SYSTEM,
    wants=(Q.METER_GLYPH, Q.METER_TEMPLATE, Q.METER_TEMPLATE_AT_BAR,
           Q.METER_OCR, Q.METER_OCR_AT_BAR,
           Q.DURATION, Q.DOSSIER_FACT,
           Q.SYSTEM_STAFF_COUNT, Q.METER, Q.EVENT, Q.REST,
           Q.MEASURE_PARTITION, Q.MOVEMENT_SPANS,
           Q.GLYPH_BOX, Q.CELL_STAFF_SPACE, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD),
    reasons=("voted", "no_agreement", "no_evidence",
             "too_few_staves_read_it", "carried",
             # ⚠️ ROADMAP 2.22b: the carry held where the bars were silent.
             "carried_uncontested",
             "carry_not_corroborated", "carry_outweighed_by_the_bars",
             "carry_source_uncorroborated",
             "change_only", "derived_from_bars",
             "bars_name_a_length_without_a_form",
             "opening_disagrees_with_prior_cautionary",
             # ⚠️ ROADMAP 2.12k. See `METER_RETURN_NOT_READ_REASON`'s block
             # comment above `_carry_meter`: a corroborated cautionary
             # confirmed a printed change into this system, and the change
             # could not be sustained by this system's own bars -- an
             # ABSTENTION, still, just one that says a printed RETURN exists
             # and was not read rather than reading like any other refusal.
             "meter_return_not_read",
             # ⚠️ ROADMAP 2.12l. See `METER_CHANGE_DIGITS_MISREAD`'s block
             # comment above `_meter_digit_witness_cells`: a printed change
             # whose digits were boxed as noteheads, refused there and read
             # back here -- an ABSTENTION naming the specific, known cause
             # rather than the generic "the bars outweighed it."
             "meter_change_digits_misread",
             # ⚠️ ROADMAP 2.29: the template and OCR readers disagree about
             # this system's opening and this system's own bars did not
             # settle it either -- NARROWED, never an argmax on either
             # reader's share.
             "template_ocr_disagree"),
    mode=Mode.ADDITIVE,
)
def adjudicate_meter(ev: Evidence) -> Ruling:
    """A meter is a fact of the SYSTEM, printed once on every staff.

    ⚠️ ONE VOTE PER STAFF. The rows are already per-staff (GATHER emits one),
    which is the fix for the fault that once turned a single `timeSig4` at
    confidence 0.42 into eighteen unanimous votes.

    ⚠️ THE VOTE KEY IS THE PRINTED FORM, NOT THE BAR LENGTH. `C` and `4/4` are
    one bar length and two engravings, and a page must not average them into
    one answer -- musicdiff charges the difference at 3 edits per staff.

    ⚠️ NOT WIRED HERE: the bar-sum check. It is this decision's strongest
    constraint (`implicates` names it) and it is the one redundant group with
    a DERIVED member, so consuming it is a bounded REPAIR and belongs in
    EVALUATE, not in this vote. See `consequences.reconcile_duration`.
    """
    rows = ev.rows(Q.METER_TEMPLATE, scope=Scope.SELF_AND_DESCENDANTS)
    ocr = _ocr_opening_reading(ev)
    if not rows:
        # ⚠️ THE CARRY IS TRIED ONLY WHERE THIS SYSTEM'S OWN EVIDENCE FAILED,
        # so it can never overturn a reading. Off by default -- see
        # the carry-hazard note above `_carry_meter` for the movement-boundary hazard, measured.
        #
        # ⚠️ ROADMAP 2.29: WHERE ONLY THE OCR READ, IT IS STILL NOT DECIDED
        # HERE. `ocr` is handed to `_meter_fallbacks` as a NAMED CANDIDATE
        # for the carry ladder to weigh (CLAUDE.md rule 6) -- never asserted
        # as this system's opening on its own say, however plausible.
        fallback = _meter_fallbacks(ev, "no_evidence")
        if ocr is not None:
            import dataclasses
            fallback = dataclasses.replace(
                fallback, detail=dict(fallback.detail,
                                      ocr_only_candidate={
                                          "numerator": ocr[0],
                                          "denominator": ocr[1],
                                          "share": round(ocr[2], 3)}))
        return fallback

    tally_: dict = {}
    for row in rows:
        raw = row.detail.get("raw") or str(row.value)
        tally_.setdefault(raw, []).append(row)

    best_raw, witnesses = max(tally_.items(), key=lambda kv: len(kv[1]))

    # ⚠️ COVERAGE FIRST, AND IT IS A DIFFERENT QUESTION FROM AGREEMENT.
    # "Do the staves that spoke agree?" and "did enough of them speak?" are
    # two facts, and the second is the one a handful of spurious readings
    # passes trivially -- they are unanimous among themselves. Reported apart,
    # with its own reason, so a page that shipped a wrong meter and a page
    # whose staves disagreed are never the same row.
    n_staves = ev.verdict(Q.SYSTEM_STAFF_COUNT)
    total = n_staves.value if n_staves is not None and n_staves.value else None
    coverage = (len(witnesses) / float(total)) if total else None
    if coverage is not None and coverage < METER_COVERAGE_FLOOR:
        return _meter_fallbacks(
            ev, "too_few_staves_read_it",
            coverage=round(coverage, 3),
            n_staves_spoke=len(rows),
            n_staves_on_system=total,
            would_have_been=best_raw)

    share = len(witnesses) / len(rows)
    if share < METER_AGREEMENT_FLOOR:
        # ⚠️ Recorded, not defaulted. A system whose staves disagree about the
        # meter is exactly the page a human should see.
        return _meter_fallbacks(
            ev, "no_agreement",
            share=round(share, 3),
            readings={k: len(v) for k, v in tally_.items()})

    opening = {"numerator": witnesses[0].value[0],
               "denominator": witnesses[0].value[1],
               "raw": best_raw}

    # ─── ROADMAP 2.29: THE OCR READER WEIGHS IN ON THE SAME OPENING ────────
    # ⚠️ A SECOND, INDEPENDENT READER OF THE SAME INK (see `meter_digit_ocr`'s
    # own docstring for why OCR and the NCC template are not one signal
    # wearing two names). Silent where `ocr is None` -- an OCR abstention is
    # not evidence either way, and the template's own vote stands exactly as
    # it always has.
    ocr_used: tuple = ()
    ocr_detail: dict = {}
    if ocr is not None:
        ocr_num, ocr_den, ocr_share, ocr_rows = ocr
        if (ocr_num, ocr_den) == (opening["numerator"], opening["denominator"]):
            # AGREE: a second witness for the SAME opening, never a second
            # vote -- the template's own share still decides the margin.
            ocr_used = tuple(r.id for r in ocr_rows)
            ocr_detail = {"ocr_agrees": True, "ocr_share": round(ocr_share, 3)}
        else:
            # DISAGREE. Never an argmax on reader share (CLAUDE.md rule 5/6):
            # ask this system's OWN bars which of the two candidates they
            # corroborate, through the SAME `_corroborate` the carry ladder
            # already uses -- never re-derived, never a new arbiter.
            template_candidate = {"numerator": opening["numerator"],
                                  "denominator": opening["denominator"]}
            ocr_candidate = {"numerator": ocr_num, "denominator": ocr_den}
            t_margin = _bar_corroboration_margin(ev, template_candidate)
            o_margin = _bar_corroboration_margin(ev, ocr_candidate)
            if (t_margin is not None and o_margin is not None
                    and t_margin != o_margin):
                # The bars settle it -- DECIDED, but on the bars' own say,
                # never on which reader merely spoke first or loudest.
                if o_margin > t_margin:
                    opening = {"numerator": ocr_num, "denominator": ocr_den,
                              "raw": "%d/%d" % (ocr_num, ocr_den)}
                    used = tuple(r.id for r in ocr_rows)
                else:
                    used = tuple(r.id for r in witnesses)
                return Ruling(
                    value=_with_segments(ev, opening),
                    reason="voted", margin=share, used=used,
                    detail={"share": round(share, 3),
                            "n_staves_spoke": len(rows),
                            "template_ocr_disagree": True,
                            "template_reading": template_candidate,
                            "ocr_reading": ocr_candidate,
                            "template_bar_margin": t_margin,
                            "ocr_bar_margin": o_margin,
                            "settled_by": "bars"})
            # Neither the bars nor an argmax may settle it: NARROW. "It is
            # one of these" (`Ruling.narrow`), and the carry ladder at the
            # NEXT system sees a NARROWED, not DECIDED, verdict here and
            # falls to its own evidence rather than inheriting either guess.
            return Ruling.narrow(
                candidates=(
                    Candidate(value=dict(template_candidate, raw=best_raw),
                             support=share),
                    Candidate(value=dict(ocr_candidate,
                                        raw="%d/%d" % (ocr_num, ocr_den)),
                             support=ocr_share)),
                reason="template_ocr_disagree",
                used=tuple(r.id for r in witnesses) + tuple(r.id for r in ocr_rows),
                template_reading=template_candidate, ocr_reading=ocr_candidate,
                template_share=round(share, 3), ocr_share=round(ocr_share, 3))
    # ─────────────────────────────────────────────────────────────────────

    # ⚠️ ROADMAP 2.12h. A vote -- however unanimous -- is not the only
    # witness to this system's OPENING: the immediately preceding system's
    # own courtesy signature names it directly (A-METER-5). Where that
    # cautionary is CORROBORATED and disagrees, this vote is not asserted
    # outright; it is rerouted through the same fallback ladder an
    # unreadable opening already uses, so `_carry_meter` can weigh the
    # cautionary against THIS system's own bars (`_corroborate`) exactly as
    # any other carry candidate -- never a blind swap, and never a default.
    # See the block comment above `_adjacent_corroborated_cautionary`.
    caution = _adjacent_corroborated_cautionary(ev, ev.subject)
    if caution is not None and (
            (caution["numerator"], caution["denominator"])
            != (opening["numerator"], opening["denominator"])):
        return _meter_fallbacks(
            ev, "opening_disagrees_with_prior_cautionary",
            would_have_been=best_raw, would_have_been_share=round(share, 3),
            contradicts_cautionary=caution)
    return Ruling(value=_with_segments(ev, opening),
                  reason="voted", margin=share,
                  used=tuple(r.id for r in witnesses) + ocr_used,
                  detail=dict({"share": round(share, 3),
                              "n_staves_spoke": len(rows)}, **ocr_detail))





# ─────────────────────────────────────────────────────────────────────────────
# Cross-staff simultaneity — the column through a system
# ─────────────────────────────────────────────────────────────────────────────

#: How close two staves' events must sit to be called the same instant.
#:
#: ⚠️ READ OFF A MEASURED DISTRIBUTION AGAINST A NULL, NOT TUNED TO A SCORE.
#: Over 51 real bars (Brahms 1 / Breitkopf, 6 systems, 13-14 staves) the
#: nearest event in another staff sits at a median 0.027 staff spaces; a
#: reshuffle of the same events inside the same bar span gives 0.122. The
#: separation is ~4x at the median and holds at every density, while the mere
#: EXISTENCE of a near neighbour does not (see `ONSET_COLUMN_*` in FINDINGS).
#: 0.10 is where the real/null ratio is largest; 0.25 and 0.5 wash out.
ONSET_COLUMN_TOLERANCE_SPACES = 0.10

#: Below this many staves a "column" is not corroboration, it is one reading.
ONSET_COLUMN_MIN_WITNESSES = 2


def _page_x_of(rows) -> Dict[Tuple[int, int, int], float]:
    """(staff, cell, glyph) -> page-frame x centre, for rows that carry one.

    ⚠️ Rows WITHOUT a page frame are dropped rather than fallen back to the
    canonical x. A canonical x is measured inside one rescaled cell, so using
    it here would silently compare two different units across staves — the
    exact fault this decision exists to avoid.

    ⚠️⚠️ THE KEY IS THE WHOLE ADDRESS, AND KEYING ON THE GLYPH ORDINAL ALONE
    IS A REAL BUG THAT WAS WRITTEN AND MEASURED. `Subject.glyph` counts
    within its CELL, so it is unique for `adjudicate_event` (scope `CELL`,
    where `_box_of` may key on it) and NOT unique here (scope `SYSTEM`):
    glyph 3 of staff 0 and glyph 3 of staff 9 are different ink at the same
    ordinal, and one dict entry silently took the other's x. The tell was
    that 699 of 814 corroborated columns had a residual of EXACTLY zero —
    fourteen staves agreeing to the float, which no scan does. A plausible
    column count is not evidence that the columns are real.
    """
    out: Dict[Tuple[int, int, int], float] = {}
    for r in rows:
        sub = r.subject
        if sub.glyph is None or sub.cell is None or sub.staff is None:
            continue
        x = (r.detail or {}).get("x_center_page")
        if x is not None:
            out[(sub.staff, sub.cell, sub.glyph)] = float(x)
    return out


@decision(
    quantity=Q.ONSET_COLUMN,
    checkable=Checkable.CHECKABLE,
    checked_by=(
        '"a column is an instant: every staff of the system either sounds '
        'something in it or is silent there, and a staff whose event sits '
        'alone at an x its neighbours all skip is the one to look at"',
    ),
    # ⚠️ It implicates the GROUPING, never the pitch or the duration. A
    # misaligned event says this staff read a different set of onsets — which
    # is Q.EVENT's business one scope down — and says nothing about how long
    # any of them are.
    implicates=(Q.ONSET_COLUMN, Q.EVENT),
    # ⚠️ `Q.STAFF_SPACING` is in here because it is not decoration: the
    # tolerance IS a staff-space count, so a wrong spacing moves every column
    # boundary on the system. A consumer weighing this verdict has to be able
    # to see that its unit came from somewhere.
    composed_from=(Q.EVENT, Q.GLYPH_BOX, Q.STAFF_SPACING),
    scope=Kind.SYSTEM,
    wants=(Q.EVENT, Q.GLYPH_BOX, Q.STAFF_SPACING),
    reasons=("columns_read", "single_staff", "no_page_frame", "nothing_to_align"),
    mode=Mode.ADDITIVE,
)
def adjudicate_onset_column(ev: Evidence) -> Ruling:
    """Which events of DIFFERENT staves sound at the same instant.

    ⚠️⚠️ THIS RECORDS; IT DOES NOT OVERTURN. Sean's governing principle is
    additive evidence rather than a gate, and the measurement says why it must
    be here in particular: against a circular-shift null on 51 real bars the
    page needs 1,483 columns where the null needs 2,409 — but the
    corroboration RATE rises with density while the information falls (sparse
    2.06x, dense 1.52x), so much of the alignment on a crowded bar is
    available by chance. A rule that re-grouped a staff's events to match its
    neighbours would, on a 26-staff page, be enforcing density.

    ⚠️ `Q.EVENT` IS CONSUMED, NOT REDONE. Within-staff simultaneity is already
    decided per cell under a tolerance measured off that bar's own noteheads;
    this groups those verdicts. Re-clustering the glyphs here would answer the
    same question twice and let the two answers disagree.

    ⚠️ THE UNIT IS STAFF SPACES AND THE FRAME IS THE PAGE. Both are load-
    bearing: pixels are a property of one scan's resolution, and a canonical x
    is measured inside one rescaled cell, so neither crosses a staff boundary.
    A cell whose glyphs carry no page frame is DECLINED by name.
    """
    ev_verdicts = ev.verdicts(Q.EVENT, scope=Scope.SELF_AND_DESCENDANTS)
    if not ev_verdicts:
        return Ruling.abstain("nothing_to_align")

    boxes = _page_x_of(ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS))
    if not boxes:
        return Ruling.abstain("no_page_frame")

    # (measure index) -> staff -> [page x of each event]
    per_bar: Dict[int, Dict[int, List[float]]] = {}
    used: List[str] = []
    for v in ev_verdicts:
        sub = v.subject
        if sub.cell is None or sub.staff is None or not isinstance(v.value, dict):
            continue
        xs: List[float] = []
        for e in v.value.get("events", ()):
            gx = [boxes[(sub.staff, sub.cell, g)]
                  for g in e.get("glyphs", ())
                  if (sub.staff, sub.cell, g) in boxes]
            if gx:
                xs.append(sum(gx) / len(gx))
        if xs:
            per_bar.setdefault(sub.cell, {}).setdefault(sub.staff, []).extend(xs)
            used.append(v.id)

    if not per_bar:
        return Ruling.abstain("no_page_frame")

    spacing = _system_spacing(ev)
    if spacing is None:
        return Ruling.abstain("no_page_frame")
    tol_px = spacing * ONSET_COLUMN_TOLERANCE_SPACES

    bars: List[Dict[str, Any]] = []
    for mi in sorted(per_bar):
        by_staff = per_bar[mi]
        if len(by_staff) < ONSET_COLUMN_MIN_WITNESSES:
            bars.append({"measure": mi, "staves": len(by_staff),
                         "note": "single_staff"})
            continue
        points = sorted((x, st) for st, xs in by_staff.items() for x in xs)
        # ⚠️ Single-link chaining is REFUSED. A first cut merged distinct
        # onsets 323 px apart on a dense bar by walking neighbour to
        # neighbour; a column must stay within the tolerance of its OWN
        # centre, which is the same discipline `_dedupe_cross_staff_detections`
        # needed when one-winner-per-cluster chained distinct glyphs.
        cols: List[List[Tuple[float, int]]] = []
        for x, st in points:
            if cols and abs(x - (sum(p[0] for p in cols[-1]) / len(cols[-1]))) <= tol_px:
                cols[-1].append((x, st))
            else:
                cols.append([(x, st)])
        span = points[-1][0] - points[0][0]
        n_ev = len(points)
        rows_out = []
        for c in cols:
            xs = [p[0] for p in c]
            witnesses = sorted({p[1] for p in c})
            centre = sum(xs) / len(xs)
            rows_out.append({
                "x_page": round(centre, 2),
                "witnesses": witnesses,
                "n_witness": len(witnesses),
                "residual_spaces": round(
                    (max(xs) - min(xs)) / spacing, 4) if len(xs) > 1 else 0.0,
            })
        corroborated = [c for c in rows_out
                        if c["n_witness"] >= ONSET_COLUMN_MIN_WITNESSES]
        bars.append({
            "measure": mi,
            "staves": len(by_staff),
            "columns": rows_out,
            "n_columns": len(rows_out),
            "n_corroborated": len(corroborated),
            "alone": [c["x_page"] for c in rows_out if c["n_witness"] == 1],
            # ⚠️ THE DENSITY TRAVELS WITH THE VERDICT. A consumer that reads
            # corroboration without it cannot tell evidence from crowding.
            "events_per_space": round(n_ev / (span / spacing), 2)
            if span > spacing else None,
        })

    read = [b for b in bars if "columns" in b]
    if not read:
        return Ruling.abstain("single_staff")
    all_res = [c["residual_spaces"] for b in read for c in b["columns"]
               if c["n_witness"] > 1]
    return Ruling(
        value={"bars": bars},
        reason="columns_read",
        used=tuple(used),
        detail={
            "n_bars": len(read),
            "n_columns": sum(b["n_columns"] for b in read),
            "n_corroborated": sum(b["n_corroborated"] for b in read),
            "n_alone": sum(len(b["alone"]) for b in read),
            "median_residual_spaces": round(
                sorted(all_res)[len(all_res) // 2], 4) if all_res else None,
            "tolerance_spaces": ONSET_COLUMN_TOLERANCE_SPACES,
            "staff_spacing_px": round(spacing, 2),
        },
    )


def _system_spacing(ev: Evidence) -> Optional[float]:
    """The system's staff-line spacing in PAGE pixels, or None.

    ⚠️ Read from `Q.STAFF_SPACING`, which `gather_geometry` measures per staff
    in the page frame. Median across the system's staves: one warped staff
    must not set the unit for the rest.
    """
    rows = ev.rows(Q.STAFF_SPACING, scope=Scope.SELF_AND_DESCENDANTS)
    vals = []
    for r in rows:
        try:
            v = float(r.value)
        except (TypeError, ValueError):
            continue
        if v > 0:
            vals.append(v)
    if not vals:
        return None
    vals.sort()
    return vals[len(vals) // 2]


# ─────────────────────────────────────────────────────────────────────────────
# Stem direction, and the voices it splits
# ─────────────────────────────────────────────────────────────────────────────


class _Shim:
    """The three fields `transcribe._stem_direction` reads off a detection.

    ⚠️ A SHIM AND NOT A REIMPLEMENTATION, deliberately. That function's rule
    was paid for by a real regression -- comparing a single notehead's centre
    against a stem's MIDPOINT handed the two members of a double stop opposite
    directions, which reads as divisi and split Brahms's Viola chords into two
    voices through a `<backup>` -- so the arithmetic is CALLED here rather
    than restated, and the tested code is the code that runs.
    """

    __slots__ = ("y_canonical", "height_canonical", "x_canonical",
                 "width_canonical")

    def __init__(self, x, y, w, h):
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h


def _project(stem_row, heads, head_box) -> str:
    """The direction of ONE stem, from the whole group of heads it carries.

    ⚠️ FACTORED OUT RATHER THAN DUPLICATED. The beam-mate tier below needs the
    direction of a NEIGHBOUR's stem, and it must be the same computation --
    two copies of *"direction belongs to the stem and is decided from the whole
    group on it"* would be free to disagree, and the disagreement would look
    like a reading fault rather than a drift.
    """
    sx, sy, sw, sh = _xywh(stem_row)
    group = [_Shim(*_xywh_head(h.value)) for h in heads
             if _boxes_overlap(_xywh_head(h.value), (sx, sy, sw, sh))]
    if not group:
        group = [_Shim(*head_box)]
    return _legacy_stems._stem_direction(_Shim(sx, sy, sw, sh), group)


def _on_beam(head_box, beam) -> bool:
    """Does this head's x-CENTRE stand inside the beam's span?

    ⚠️ THE CENTRE, NOT AN OVERLAP, AND THE DIFFERENCE IS 4 POINTS OF ACCURACY.
    Scored against the heads whose direction a STEM already decided, an
    overlap test reads 0.798 and the centre test 0.829 -- a head whose box
    merely grazes the end of a stroke is usually hanging from the NEXT group.
    """
    hx = head_box[0] + head_box[2] / 2.0
    return beam[0] <= hx <= beam[0] + beam[2]


def _heads_in(ev, cell):
    """Every notehead row of this bar, with a readable box.

    ⚠️ SPELLED ONCE because both tiers need it and the cost of asking is what
    made the first draft of the beam tier slow: `ev.rows` at
    `SELF_AND_DESCENDANTS` walks the cell, so WHERE it is called matters more
    than how it is written.
    """
    return [r for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                               subject=cell)
            if (r.detail or {}).get("category") == "notehead"
            and _xywh_head(r.value) is not None]


def _direction_from_a_beam_mate(ev, cell, head_box, stems):
    """A head with no stem of its own, answered by a head that shares its BEAM.

    ⚠️⚠️ THE CLAIM IS PHYSICAL AND NOT GEOMETRIC, WHICH IS THE WHOLE RESULT.
    A beam joins stem TIPS, so every stem hanging from one stroke points the
    same way -- a fact about how the mark was engraved rather than a
    measurement of where ink fell. Both readings were scored on the 1,443
    heads a stem already decided, LEAVE-ONE-OUT:

        always the commoner direction (baseline)        0.506
        where the beam SITS relative to the head        0.829
        what a head on the SAME BEAM says, majority     0.938
        what a head on the SAME BEAM says, UNANIMOUS    0.984

    The geometric rule is refused at 0.829: this quantity feeds
    `adjudicate_event`'s divisi guard, whose own reasoning is that an UNKNOWN
    is better than a confident wrong answer, and one head in six is not an
    unknown.

    ⚠️ UNANIMITY, NOT A MAJORITY, and it costs 15 of 167 reach to buy 4.6
    points. A head standing on two strokes whose mates disagree is exactly the
    two-voice bar this quantity exists to keep straight, and `stems_disagree`
    one branch up already refuses that case when the stems are the head's own.

    ⚠️⚠️ IT IS NOT IN `INFER`, AND THAT IS NOT A PREFERENCE. Borrowing a
    neighbour's reading is BEST rather than FORCED, so the fourth stage is
    where the claim belongs -- but `Q.STEM_DIRECTION` is ORDER 17 and its only
    two consumers, `Q.EVENT` (21) and `Q.VOICES` (22), read it inside
    ADJUDICATE. INFER runs after all of ADJUDICATE, so a rule there would
    write a verdict **after both readers had already looked**, and reach
    nothing at all. The stage boundary is honoured by the REASON instead:
    `beam_mate` is a different word from `stem_projection`, so a consumer or
    a cleanup count can separate what was read from what was borrowed.

    Returns `(direction, cited row ids, detail)` or None.
    """
    beams = [b for b in ev.rows(Q.BEAM_STROKE, scope=Scope.SELF_AND_ANCESTORS,
                                subject=cell) if _xywh(b) is not None]
    on = [b for b in beams if _on_beam(head_box, _xywh(b))]
    if not on:
        return None

    heads = _heads_in(ev, cell)
    votes, cited, mates = set(), [], 0
    for b in on:
        bbox = _xywh(b)
        for h in heads:
            other = _xywh_head(h.value)
            if other == head_box or not _on_beam(other, bbox):
                continue
            its = _stems_on(other, stems)
            if not its:
                continue
            answers = {_project(s, heads, other) for s in its}
            if len(answers) != 1:
                # ⚠️ A MATE THAT CANNOT ANSWER FOR ITSELF IS NOT A WITNESS.
                # It is the `stems_disagree` case, and letting it vote would
                # launder an ambiguity into a corroboration.
                continue
            votes |= answers
            cited.extend([b.id, h.id] + [s.id for s in its])
            mates += 1
    if mates == 0 or len(votes) != 1:
        return None
    return (votes.pop(), sorted(set(cited)),
            {"beams_on": len(on), "mates": mates,
             # ⚠️ WRITTEN EVEN WHEN THE TIER DOES NOT FIRE'S SIBLING CASE
             # WOULD BE ZERO: a reader must be able to tell "one mate agreed"
             # from "many did", because the first is not corroboration.
             "unanimous": True})


def _stems_on(head_box, stems):
    """Every stem whose box overlaps this notehead's.

    ⚠️ THE SAME ATTACHMENT TEST `_stem_joined` USES, and imported from beside
    it rather than re-derived: box overlap with NO tolerance, because the
    populations separate with nothing between them (819 heads take exactly one
    stem; where none overlaps the nearest is 94 px away but for three pairs at
    1-2 px).
    """
    return [s for s in stems if _xywh(s) and _boxes_overlap(_xywh(s), head_box)]


@decision(
    quantity=Q.STEM_DIRECTION,
    composed_from=(Q.STEM, Q.GLYPH_BOX, Q.BEAM_STROKE),
    scope=Kind.GLYPH,
    # ⚠️ `Q.NOTEHEAD_CLASS` is the DOMAIN, not a `wants`. A declaration the
    # body never reads records nothing -- `Evidence` fills `missing`/`declined`
    # only for quantities actually queried -- so it cannot be told from one
    # that is read and always present. `inventory --check` fails on it.
    wants=(Q.STEM, Q.GLYPH_BOX, Q.BEAM_STROKE),
    subjects_from=Q.NOTEHEAD_CLASS,
    reasons=("stem_projection", "beam_mate", "no_stem", "stems_disagree",
             "no_evidence"),
    mode=Mode.ADDITIVE,
)
def adjudicate_stem_direction(ev: Evidence) -> Ruling:
    """Which way this notehead's stem points.

    ⚠️ DIRECTION BELONGS TO THE STEM AND IS DECIDED FROM THE WHOLE GROUP ON
    IT. A double stop is two heads on ONE physical stem, so the direction is
    computed once from every head that stem carries and handed to each of
    them. Deciding it head-by-head against the stem's midpoint is the
    documented regression: for any interval wider than the stem is long the
    same stem comes out above the lower head and below the upper one, the two
    members disagree, `group_chords_in_measure`'s divisi guard refuses to
    merge them, and one chord exports as two voices one note each. Thirds were
    unaffected, which is what made it look intermittent.

    ⚠️ IT WAS GATHERED AND READ BY NOTHING FOR THE DIRECTION. `Q.STEM` has
    carried 916 rows on a three-page fixture since the CV rung was wired, and
    `gather_coverage` reported `stem_direction` in `NO_VOCABULARY` -- derivable
    from a row already on the record and undeclared. It is what the divisi
    guard runs on, so while it was undeclared that guard was inert in
    `export._events` and `adjudicate_event` said so in its own docstring.

    ⚠️ TWO DIFFERENT SILENCES, AND THEY MUST NOT COLLAPSE. `no_stem` means the
    CV rung read no stem meeting this head -- a whole note has none, and on a
    scan a stem is often simply missed -- while `stems_disagree` means two
    stems meet it and point opposite ways, which is ink we cannot read. The
    first is ordinary; the second is a warning.

    ⚠️ NO CONSTANT, and the attachment test it borrows has none either: the
    populations separate with nothing between them, so a tolerance would be
    decoration.
    """
    box = ev.rows(Q.GLYPH_BOX)
    head_box = _xywh_head(box[-1].value) if box else None
    if head_box is None:
        return Ruling.abstain("no_evidence")

    cell = ev.subject.at(Kind.CELL)
    stems = ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell)

    mine = _stems_on(head_box, stems)
    if not mine:
        # ⚠️⚠️ THE BEAM ROWS ARE ASKED FOR BEFORE THE HEADS, AND THE ORDER IS
        # MEASURED RATHER THAN TIDY. An earlier draft hoisted the whole-cell
        # glyph scan above this branch so both tiers could share it, and the
        # stem pass went from 80 s to minutes on four pages: `ev.rows` at
        # `SELF_AND_DESCENDANTS` walks the cell, and hoisting made all 793
        # STEMLESS heads pay for a scan they had never paid for. Asking the
        # beams first means only the heads that actually stand on one -- 245
        # of 793 here -- reach the scan at all.
        borrowed = _direction_from_a_beam_mate(ev, cell, head_box, stems)
        if borrowed is not None:
            value, cited, detail = borrowed
            return Ruling(value=value, reason="beam_mate",
                          used=(box[-1].id,) + tuple(cited), detail=detail)
        return Ruling.abstain("no_stem", used=(box[-1].id,))

    # Every notehead in this bar, so a stem's whole group can be found.
    heads = _heads_in(ev, cell)

    answers, used = set(), [box[-1].id]
    for s in mine:
        answers.add(_project(s, heads, head_box))
        used.append(s.id)

    if len(answers) != 1:
        # ⚠️ ABSTAIN RATHER THAN VOTE. A head met by two stems pointing
        # opposite ways is exactly the divisi/double-stop ambiguity this
        # quantity exists to keep straight, and picking one would hand the
        # guard downstream a confident wrong answer -- worse than the unknown
        # it already tolerates (`_directions_conflict` never blocks a merge on
        # an unknown direction).
        return Ruling.abstain("stems_disagree", n_stems=len(mine),
                              answers=sorted(answers))

    return Ruling(value=answers.pop(), reason="stem_projection",
                  used=tuple(used),
                  detail={"n_stems": len(mine), "heads_on_stem": len(heads)})


# ─────────────────────────────────────────────────────────────────────────────
# A WHOLE REST WEARING A NOTEHEAD'S LABEL
#
# ⚠️ STAFF SPACES AND STAFF STEPS, NEVER PIXELS. The staves of one plate differ
# in spacing and the DPI differs between runs, so a pixel constant here would be
# a property of one render of one page.
#
# Every cut below is DERIVED from a population the rule never judges -- the
# document's own 395 correctly-detected `restWhole` glyphs on Beethoven 5 /
# Litolff `984073` pp.1-4 -- and is then SWEPT, because a constant read off the
# population it is about to judge is a constant fitted to it.
# (`benchmarks/omr-note-where-silence-2026-09/probe/sweep.py`.)
#
#   height  p05 0.46  p95 0.84 staff spaces   (a notehead's median is 1.31)
#   aspect  p05 1.63  p95 3.09                (a notehead's median is 1.14)

#: ⚠️ A NARROW PLATEAU, and saying so is the point. 0.80 and 0.84 fire on the
#: same 25 glyphs; 0.90 admits two more and 0.75 loses eight. The two it admits
#: were cropped and are ambiguous ink in bars that hold real notes, so the cut
#: is LOAD-BEARING rather than cosmetic -- which is an argument for keeping it
#: at the conservative edge, not for trusting it on a second document.
WHOLE_REST_INK_MAX_HEIGHT_SPACES = 0.84
#: ⚠️ Also narrow: 1.40 admits two more (both ambiguous), 1.80 loses two real
#: whole rests. There is no plateau here at all; it is the document's own p05.
WHOLE_REST_INK_MIN_ASPECT = 1.63
#: ⚠️ THE UPPER BOUND SITS IN A MEASURED EMPTY INTERVAL and costs nothing: the
#: widest of the 25 catches is 2.35 and the next thing a one-sided rule admitted
#: is a 5.49 sliver of line residue. Anywhere in 2.40-4.50 gives the identical
#: answer. It exists because that sliver is not a whole rest EITHER, and a
#: decision may only claim what it can support -- excluding it by description
#: rather than reaching the right outcome through a wrong one.
WHOLE_REST_INK_MAX_ASPECT = 3.09
#: Where a whole rest HANGS: under the fourth staff line from the bottom. With
#: the bottom line 0 and one step per half space its body spans step 6 down to
#: step 5, so its centre is 5.5. ⚠️ NOT TUNED -- it is the engraving convention,
#: and it is an obligation rather than a preference, which is what makes it
#: usable as a witness at all.
WHOLE_REST_STEP = 5.5
#: Where a HALF rest SITS: on the third line from the bottom, its body
#: standing in the space ABOVE it, so its centre is one half space -- one step
#: -- lower in this frame than the whole rest's.
#:
#: ⚠️ DERIVED FROM `WHOLE_REST_STEP`, NEVER TYPED. The two rests are the same
#: rectangle one line apart, and that is the whole content of the convention
#: (`docs/engraving-conventions.md`, *A whole rest HANGS under the 4th line; a
#: half rest SITS on the 3rd -- and they are the same shape*). Two independent
#: constants would be free to drift into a gap that is not one line, which is
#: the one number this rule stands on.
HALF_REST_STEP = WHOLE_REST_STEP - 1.0
#: How far BELOW its slot a whole rest's centre may stand and still be read as
#: a whole rest, in half steps. ⚠️⚠️ **MEASURED HERE, ROADMAP 2.12b-cal,
#: 2026-09-23** -- it replaces a nominal 0.5, which was half the gap between
#: the two slots and therefore a statement about the CONVENTION rather than
#: about these plates.
#:
#: The derivation, reproducible with one command
#: (`probe/rest_slot_calibration.py --all` then `--derive`):
#:
#:   * the print-confirmed whole-rest population -- every `restWhole` the
#:     bands do not contradict, standing inside its own staff, on all three
#:     acceptance records, plus the ten Sean adjudicated against the print --
#:     is **n = 3,259, p5 5.01, p50 5.41, p95 5.91, min 4.16, max 7.93**;
#:   * **Sean, 2026-09-23: ten of ten of the rows the nominal band called the
#:     other convention are WHOLE RESTS** (`out/print/ADJUDICATION-sean-
#:     2026-09-23-rests.json`), measured at steps **4.16 - 4.713** -- the
#:     bottom 0.3% of that population's own low tail;
#:   * so the tolerance is the distance from the slot to the LOWEST rest a
#:     human has confirmed off the print: 5.5 - 4.16 = 1.34, rounded out to
#:     **1.35** so that rest is inside the band rather than on its edge.
#:
#: ⚠️ THE POOLED p5/p95 IS NOT THE BAND, AND THE REASON IS THE WHOLE FINDING.
#: A ±(p95-p5)/2 band is ±0.45 -- the nominal 0.5 back again -- and it
#: contradicts ten of ten rests a musician read off the plate. The dispersion
#: of the BULK is not the extent of the POPULATION: on a scan the tail is the
#: thing being measured, because warp and multi-voice displacement move
#: individual rests and not the median.
#:
#: ⚠️ IT SITS BELOW THE PLATEAU, DELIBERATELY. The narrowed count is flat at
#: 68 rows for a tolerance of 1.60-1.90 (the measured density trough of the
#: `restWhole` population, steps 3.4-3.9); 1.35 lies under it, which is the
#: conservative side -- it NARROWS 24 rows a wider band would DECIDE, and a
#: narrowing loses nothing (EXPORT refuses to argmax one) while a decision on
#: ink no one has looked at is a default flipped on agreement with our own
#: reading (CLAUDE.md §2 rule 5).
REST_SLOT_TOLERANCE_WHOLE = 1.35
#: The same question for the HALF rest, ABOVE its slot -- and it is **NOT
#: MEASURED HERE**, which is why it is a second constant and not the first
#: one reused.
#:
#: ⚠️⚠️ THESE PLATES PRINT ALMOST NO HALF RESTS AND THERE IS NOTHING TO
#: MEASURE. Across all three acceptance records the detector says `restHalf`
#: **44 times against 3,918 `restWhole`** (1.1%), and **3 of those 44 stand
#: inside the staff they are filed on** -- 31 of Breitkopf's 35 sit at step
#: −7.4, which is the next staff down through the cell's pad. A tolerance
#: derived from three rows would be a number wearing a measurement's clothes.
#: So this stays at the convention's own midpoint, unchanged from 2.12b, and
#: says so. It is the number to revisit when a plate that prints half rests
#: is read.
REST_SLOT_TOLERANCE_HALF = 0.5
#: The two classes whose ROLE-half this rule reads, and the slot each claims.
#:
#: ⚠️ EXACTLY TWO, AND NOTHING ELSE IS TOUCHED. `restQuarter`, `restEighth`
#: and the rest of the table name a value by their SHAPE -- a quarter rest is
#: not a half rest one line away, it is a different glyph -- so no slot can
#: corroborate or contradict them and this rule must be silent about them.
#: A lone quarter rest does NOT mean the bar (CLAUDE.md §10), and widening
#: this map is how that fact would be lost.
_REST_SLOT_BY_CLASS = {"restwhole": WHOLE_REST_STEP,
                       "resthalf": HALF_REST_STEP}
#: ⚠️ THE TOLERANCE IS STAFF-LINE REGISTRATION ERROR, NOT ENGRAVING SLACK.
#: `Q.STAFF_LINES` models a staff as five ideal rows while a scanned staff tilts
#: and bows 8-17 page px across its width (CLAUDE.md, `OMR_CELL_LINE_TRACE`),
#: which on this plate is up to a whole step. Measured: the document's own
#: correctly-read whole rests spread over steps 2.5-5.9. Plateau 1.0-1.5.
WHOLE_REST_STEP_TOLERANCE = 1.0
#: How far along the staff the NEIGHBOUR witness looks, in bars. ⚠️ Deliberately
#: SHORT: a tacet part prints a whole rest in every bar, so a real one always
#: has a neighbour within a bar or two, while a long reach would let one distant
#: rest vouch for ink anywhere on the staff. 3, 4 and 8 all admit the same one
#: extra glyph, which on the crop is a blob beside a slur.
WHOLE_REST_NEIGHBOUR_BARS = 2
#: How closely the neighbour's height must agree, in staff steps. Plateau
#: 1.0-3.0; below 1.0 it loses a real catch. It can be loose precisely because
#: it is only ever the SECOND witness.
WHOLE_REST_NEIGHBOUR_STEPS = 1.5


def _staff_step(page_box, line_ys, spacing) -> Optional[float]:
    """This ink's centre as a STAFF STEP -- bottom line 0, one step per half
    space, up positive.

    ⚠️ EVERYTHING IS IN PAGE PIXELS. `Q.STAFF_LINES` and `Q.STAFF_SPACING` are
    filed in the page frame and `Q.GLYPH_BOX` carries `bbox_page_px` beside its
    CANONICAL box. Mixing the two is the fault `Q.ONSET_COLUMN` paid for: a
    canonical box is measured inside one cell rescaled so the staff span is
    constant, so it cannot be compared with a staff's own lines at all.
    """
    if not page_box or len(page_box) != 4 or not line_ys or not spacing:
        return None
    try:
        bottom = max(float(y) for y in line_ys)
        half = float(spacing) / 2.0
    except (TypeError, ValueError):
        return None
    if half <= 0:
        return None
    return (bottom - (float(page_box[1]) + float(page_box[3])) / 2.0) / half


def _rest_shaped(height_spaces: float, aspect: float) -> bool:
    """Is this ink the SIZE AND PROPORTION of a whole rest?"""
    return (height_spaces <= WHOLE_REST_INK_MAX_HEIGHT_SPACES
            and WHOLE_REST_INK_MIN_ASPECT <= aspect
            <= WHOLE_REST_INK_MAX_ASPECT)


@decision(
    quantity=Q.NOTEHEAD_IS_A_WHOLE_REST,
    composed_from=(Q.GLYPH_BOX, Q.STAFF_LINES, Q.STAFF_SPACING, Q.REST),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_BOX, Q.STAFF_LINES, Q.STAFF_SPACING, Q.REST),
    subjects_from=Q.NOTEHEAD_CLASS,
    reasons=("shape_and_position_agree", "not_rest_shaped",
             "not_where_a_whole_rest_can_hang", "no_page_frame",
             ABSTAIN.NO_STAFF_GEOMETRY),
    mode=Mode.ADDITIVE,
)
def adjudicate_notehead_is_a_whole_rest(ev: Evidence) -> Ruling:
    """Is this glyph the detector called a notehead actually a WHOLE REST?

    ⚠️⚠️ SEAN, 2026-09-11, reading the first cleanup artefact against the
    print: *"in bars where it should be just whole note rest in two four. It's
    showing an actual quarter note, not a quarter note rest."* On a bitonal
    1870 plate a whole rest is a small filled RECTANGLE hanging under a line
    and a notehead is a small filled OVAL, and the detector confuses them.

    ⚠️ THE MIRROR OF THIS IS ALREADY ON THE RECORD, which is what says the
    confusion runs both ways rather than being one page's bad luck: the arc
    work found a `restWhole` read at 0.56 in a bar of this same document where
    the print shows no whole rest at all.

    ⚠️ TWO WITNESSES, AND THE RULE IS THEIR AGREEMENT -- see
    `Q.NOTEHEAD_IS_A_WHOLE_REST` for the measurement that says neither is
    admissible alone (SHAPE alone 148 of 2,347, POSITION alone 310, together
    25, and all 25 hand-adjudicated against the print).

    ⚠️ POSITION IS ESTABLISHED TWO WAYS, and the second is not decoration.
    The absolute slot is measured against `Q.STAFF_LINES`, which models a staff
    as five ideal rows; a scanned staff tilts and bows, and this document's own
    correctly-read whole rests spread over steps 2.5-5.9 as a result. So a
    NEIGHBOURING BAR of the SAME STAFF holding a detected `restWhole` at nearly
    the same height counts as well -- a tacet part prints one in every bar, and
    a shared registration error cancels between two rows of one staff. It is
    what catches `P1 m85`, one of the instances Sean named, which the absolute
    slot misses at step 4.21.

    ⚠️ CONFIDENCE IS NOT A WITNESS, deliberately. The flagged glyphs do sit low
    (median 0.36 against 0.66 for noteheads generally) and CLAUDE.md records a
    confidence filter measured and REFUSED one family over, at 233 good dynamic
    letters lost to remove half of 35 bad ones. A tier that is a proxy for ink
    quality is not evidence about what a glyph IS.

    ⚠️ IT DOES NOT RECLASSIFY, and the stage boundary is the reason. What ink
    is on the page is a GATHER fact; this is ADJUDICATE answering *what does
    this ONE thing mean*. A `True` verdict is consumed by the exporter as a
    refusal to write a NOTE; nothing manufactures a `Q.REST` row, so the bar
    falls to the existing padded measure rest -- *we read nothing here*, which
    is weaker than *we read silence* and is the statement the record can
    support.

    ⚠️ FALSE IS A DECISION AND ITS REASON NAMES WHICH WITNESS REFUSED.
    *"the ink is not rest-shaped"* and *"it is rest-shaped but stands where no
    whole rest can hang"* are different facts about the page, and folding them
    together would hide that the second names the population a shape-only rule
    would have deleted.
    """
    box_rows = ev.rows(Q.GLYPH_BOX)
    page_box = None
    for r in box_rows:
        page_box = (r.detail or {}).get("bbox_page_px") or page_box
    if not page_box:
        # ⚠️ DECLINED, NOT DEFAULTED. `gather_detections` carries the page box
        # beside the canonical one and OMITS it rather than inventing one, and
        # the canonical frame cannot answer a question about a staff's lines.
        return Ruling.abstain("no_page_frame")

    staff = ev.subject.at(Kind.STAFF)
    lines = ev.rows(Q.STAFF_LINES, scope=Scope.SELF_AND_ANCESTORS, subject=staff)
    space = ev.rows(Q.STAFF_SPACING, scope=Scope.SELF_AND_ANCESTORS,
                    subject=staff)
    if not lines or not space:
        return Ruling.abstain(ABSTAIN.NO_STAFF_GEOMETRY)
    step = _staff_step(page_box, lines[-1].value, space[-1].value)
    if step is None:
        return Ruling.abstain(ABSTAIN.NO_STAFF_GEOMETRY)
    try:
        spacing = float(space[-1].value)
        w = (float(page_box[2]) - float(page_box[0])) / spacing
        h = (float(page_box[3]) - float(page_box[1])) / spacing
    except (TypeError, ValueError, ZeroDivisionError):
        return Ruling.abstain(ABSTAIN.NO_STAFF_GEOMETRY)
    if h <= 0:
        return Ruling.abstain(ABSTAIN.NO_STAFF_GEOMETRY)
    aspect = w / h

    used = [box_rows[-1].id, lines[-1].id, space[-1].id]
    detail: Dict[str, Any] = {"height_spaces": round(h, 3),
                              "aspect": round(aspect, 3),
                              "staff_step": round(step, 3)}

    if not _rest_shaped(h, aspect):
        return Ruling(value=False, reason="not_rest_shaped",
                      used=tuple(used), detail=detail)

    at_the_slot = abs(step - WHOLE_REST_STEP) <= WHOLE_REST_STEP_TOLERANCE
    neighbour = None
    if not at_the_slot:
        # ⚠️ THE SAME STAFF'S OTHER BARS, never another staff's. A staff two
        # rows down is a different part with its own registration error and
        # its own music, so its rests say nothing about this one.
        my_index = getattr(ev.subject.at(Kind.CELL), "cell", None)
        # ⚠️ THE NEIGHBOUR'S PAGE BOX IS ON ITS `Q.GLYPH_BOX` ROW, NOT ON ITS
        # `Q.REST` ROW. `gather_glyph_families` files the KIND of rest under
        # `Q.REST` and the geometry under `Q.GLYPH_BOX`, so reading
        # `detail.bbox_page_px` off the rest row finds nothing -- silently, and
        # the witness would simply never fire. A test caught it; no count
        # would have, because "no neighbour on this staff" and "the witness is
        # dead" are the same number.
        near = {r.subject for r in ev.rows(Q.REST,
                                           scope=Scope.SELF_AND_DESCENDANTS,
                                           subject=staff)
                if str(r.value).lower().startswith("restwhole")
                and my_index is not None
                and getattr(r.subject.at(Kind.CELL), "cell", None) is not None
                and abs(r.subject.at(Kind.CELL).cell - my_index)
                <= WHOLE_REST_NEIGHBOUR_BARS}
        for b in (ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                          subject=staff) if near else ()):
            if b.subject not in near:
                continue
            other_step = _staff_step((b.detail or {}).get("bbox_page_px"),
                                     lines[-1].value, space[-1].value)
            if (other_step is not None
                    and abs(other_step - step) <= WHOLE_REST_NEIGHBOUR_STEPS):
                neighbour = {"cell": b.subject.at(Kind.CELL).cell,
                             "staff_step": round(other_step, 3)}
                used.append(b.id)
                break

    if at_the_slot or neighbour is not None:
        detail["witness"] = "slot" if at_the_slot else "neighbouring_bar"
        if neighbour is not None:
            detail["neighbour"] = neighbour
        return Ruling(value=True, reason="shape_and_position_agree",
                      used=tuple(used), detail=detail)
    return Ruling(value=False, reason="not_where_a_whole_rest_can_hang",
                  used=tuple(used), detail=detail)


#: ROADMAP 2.27c, Sean 2026-09-29 answering `PLACEMENT-CONVENTIONS.md`'s
#: Rests row question 1: "displaced rests in multi-voice bars DO occur in
#: this orchestral corpus" (two players sharing a staff, e.g. Fl. 1/2) --
#: ESTABLISHED practice, a rest pushed above the staff's own MIDDLE LINE
#: belongs to the upper (stem-up) voice, one pushed below to the lower
#: (stem-down) voice. `_staff_step`'s own frame puts the middle line at
#: step 4.0 (bottom line 0, top line 8).
STAFF_MIDDLE_LINE_STEP = 4.0

#: CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: Sean's answer
#: confirms displaced rests occur and should be wired, not a numeric
#: threshold -- no crop was adjudicated this pass (2026-09-29's process
#: decision: conceptual wiring, no crop batches). Falsified by a print crop
#: where a rest this close to the middle line is centred (not
#: voice-displaced), or one further out that is not. Set well inside the
#: "outside its own staff" bound `_rest_slot` already reports (step < 0 or
#: > 8), so a genuinely displaced rest is never confused with cross-staff
#: bleed -- CLAUDE.md's own rule that a displaced rest stays on its OWN
#: staff, never read as the neighbour's.
REST_VOICE_DISPLACEMENT_MIN_STEPS = 1.5


def _rest_voice_side(ev: Evidence, glyph_indices: Sequence[int]
                     ) -> Optional[str]:
    """"upper" or "lower" where this rest sits DECISIVELY off the staff's
    own middle line; `None` where it is centred (the ordinary, undisplaced
    case) or its geometry could not be read.

    ⚠️ `_rest_slot` IS CALLED, NOT COPIED -- the same reader `Q.NOTEHEAD_IS_
    A_WHOLE_REST` and `adjudicate_duration`'s own rest branch measure a
    rest's position with, so a rest's vertical reading cannot drift between
    consumers. `ev.subject.at(Kind.STAFF)` inside it resolves to THIS bar's
    own staff regardless of which rest glyph's box is passed in, because
    every rest considered here shares one cell and therefore one staff.
    """
    for gi in glyph_indices:
        sub = Subject(Kind.GLYPH, page=ev.subject.page,
                      system=ev.subject.system, staff=ev.subject.staff,
                      cell=ev.subject.cell, glyph=gi)
        box_rows = ev.rows(Q.GLYPH_BOX, subject=sub)
        if not box_rows:
            continue
        step, _detail, _used = _rest_slot(ev, box_rows)
        if step is None:
            continue
        if step >= STAFF_MIDDLE_LINE_STEP + REST_VOICE_DISPLACEMENT_MIN_STEPS:
            return "upper"
        if step <= STAFF_MIDDLE_LINE_STEP - REST_VOICE_DISPLACEMENT_MIN_STEPS:
            return "lower"
    return None


def _event_page_x(ev: Evidence, cell: Subject, glyphs) -> Optional[float]:
    """The PAGE-frame x centre of an event's glyphs, or `None`.

    ⚠️ PAGE FRAME ONLY, NEVER THE CANONICAL x `Q.EVENT` SORTS BY. That frame
    is rescaled PER CELL (CLAUDE.md SS10; `Q.ONSET_COLUMN`'s own history), so
    comparing it to a tolerance measured in staff spaces would silently
    compare two different units -- the exact fault `Q.ONSET_COLUMN`'s own
    `_page_x_of` exists to avoid. `Q.GLYPH_BOX.detail.bbox_page_px` is that
    same field.
    """
    xs = []
    for g in glyphs:
        sub = Subject(Kind.GLYPH, page=cell.page, system=cell.system,
                      staff=cell.staff, cell=cell.cell, glyph=g)
        for r in ev.rows(Q.GLYPH_BOX, subject=sub):
            bp = (r.detail or {}).get("bbox_page_px")
            if bp:
                xs.append((float(bp[0]) + float(bp[2])) / 2.0)
                break
    return sum(xs) / len(xs) if xs else None


def _voices_overlap_in_time(ev: Evidence, up_events, down_events
                            ) -> Tuple[Optional[bool], Dict[str, Any]]:
    """RULE (1) of Sean's convention (2026-09-29): does some up-stem event
    share an onset with some down-stem event -- notes on the SAME BEAT with
    stems in different directions are ALWAYS two voices.

    Returns `(True, detail)` (a shared onset was found -- rule 1 decides two
    voices OUTRIGHT), `(False, detail)` (both directions have a page frame
    and NEITHER shares one -- rule 1 does not fire, fall through to rules 2
    and 3), or `(None, detail)` -- the record cannot say either way, which is
    ALSO "rule 1 does not fire": the caller falls through rather than
    guessing, and only abstains if rules 2 and 3 fail too.

    ⚠️ PREFERS `Q.ONSET_COLUMN` WHEN IT IS DECIDED FOR THIS BAR -- the
    system's own measured, corroborated column list -- and falls back to
    THIS STAFF'S OWN page x under the SAME tolerance
    (`ONSET_COLUMN_TOLERANCE_SPACES`) only where that decision has nothing
    for this cell. The fallback needs no cross-staff corroboration: two of
    ONE staff's own events at the same page x are simultaneous regardless of
    what any other staff read. Neither path restates a new number.
    """
    cell = ev.subject
    up_x = [x for x in (_event_page_x(ev, cell, e["_glyphs"])
                        for e in up_events) if x is not None]
    down_x = [x for x in (_event_page_x(ev, cell, e["_glyphs"])
                          for e in down_events) if x is not None]
    if not up_x or not down_x:
        return None, {"why": "no_page_frame",
                      "up_with_frame": len(up_x), "down_with_frame": len(down_x)}

    staff_subj = cell.at(Kind.STAFF)
    space = ev.rows(Q.STAFF_SPACING, scope=Scope.SELF_AND_ANCESTORS,
                    subject=staff_subj)
    sp = None
    if space:
        try:
            sp = float(space[-1].value)
        except (TypeError, ValueError):
            sp = None
    if not sp or sp <= 0:
        return None, {"why": "no_staff_spacing"}
    tol_px = sp * ONSET_COLUMN_TOLERANCE_SPACES

    system_subj = cell.at(Kind.SYSTEM)
    onset = ev.verdict(Q.ONSET_COLUMN, subject=system_subj)
    if (onset is not None and onset.outcome is Outcome.DECIDED
            and isinstance(onset.value, dict)):
        bar = next((b for b in onset.value.get("bars", ())
                   if b.get("measure") == cell.cell), None)
        cols = [c["x_page"] for c in bar.get("columns", ())] if bar else []
        if cols:
            def _nearest(x):
                best = min(cols, key=lambda c: abs(c - x))
                return best if abs(best - x) <= tol_px else None
            up_cols = {_nearest(x) for x in up_x} - {None}
            down_cols = {_nearest(x) for x in down_x} - {None}
            if up_cols and down_cols:
                return bool(up_cols & down_cols), {
                    "source": "onset_column",
                    "tolerance_spaces": ONSET_COLUMN_TOLERANCE_SPACES,
                    "up_columns": sorted(up_cols),
                    "down_columns": sorted(down_cols)}

    # Fallback: this staff's own page x, same tolerance, no cross-staff
    # corroboration needed.
    overlap = any(abs(u - d) <= tol_px for u in up_x for d in down_x)
    return overlap, {"source": "raw_page_x",
                     "tolerance_spaces": ONSET_COLUMN_TOLERANCE_SPACES,
                     "up_x": [round(x, 1) for x in up_x],
                     "down_x": [round(x, 1) for x in down_x]}


#: A sum within this many quarter-notes of the meter's own length counts as
#: "the bar" -- floating rational arithmetic on dotted/tuplet beats, not a
#: musical tolerance. Microscopic tests are built with exact values, so this
#: only guards float accumulation error over a real bar's many events.
VOICE_SUM_EPSILON_QUARTERS = 1e-6


def _meter_in_force(ev: Evidence) -> Optional[Dict[str, Any]]:
    """The `Q.METER` segment covering this cell, or `None`.

    Read at the SYSTEM ancestor, DECIDED under ANY reason -- `voted` or
    `carried` are both *"the meter is in force"*, Sean's own phrase (2026-09-
    29). Resolved to the right segment with `meter_at` because a system may
    print a change mid-system (CLAUDE.md SS10); the top-level `numerator`/
    `denominator` on a MULTI-segment value describe only the FIRST segment
    and would silently misjudge a bar past the change.

    `None` where no meter is in force at all -- Sean: *"no meter -> abstain"*,
    the same discipline `consequences.size_measure_rest` and `export.
    _bar_holds_out` both already use.
    """
    cell = ev.subject
    system_subj = cell.at(Kind.SYSTEM)
    v = ev.verdict(Q.METER, subject=system_subj)
    if v is None or v.outcome is not Outcome.DECIDED:
        return None
    return meter_at(v.value, cell.cell)


def _meter_quarters(segment: Optional[Dict[str, Any]]) -> Optional[float]:
    if not segment:
        return None
    num, den = segment.get("numerator"), segment.get("denominator")
    if not num or not den:
        return None
    try:
        return float(num) * 4.0 / float(den)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _sum_beats(ev: Evidence, cell: Subject, events) -> Optional[float]:
    """The sum, in QUARTER-NOTE beats, of these events' `Q.DURATION`
    verdicts -- ONE representative glyph per event (a chord's members share
    one physical duration by construction; a rest is its own event). `None`
    where any event's representative glyph has no DECIDED `Q.DURATION` --
    rule 8: a bar with an unread duration cannot be said to sum OR not to.
    """
    total = 0.0
    for e in events:
        glyphs = sorted(e.get("_glyphs") or ())
        if not glyphs:
            continue
        rep = glyphs[0]
        sub = Subject(Kind.GLYPH, page=cell.page, system=cell.system,
                      staff=cell.staff, cell=cell.cell, glyph=rep)
        d = ev.verdict(Q.DURATION, subject=sub)
        if d is None or d.outcome is not Outcome.DECIDED \
                or not isinstance(d.value, dict):
            return None
        beats = d.value.get("beats")
        if beats is None:
            return None
        total += float(beats)
    return total


def _sums_to(total: Optional[float], target: Optional[float]) -> bool:
    return (total is not None and target is not None
            and abs(total - target) <= VOICE_SUM_EPSILON_QUARTERS)


def _vertically_separated(ev: Evidence, cell: Subject, stream_a, stream_b
                          ) -> Tuple[Optional[bool], Dict[str, Any]]:
    """RULE (2)'s second test: are stream A and stream B in separate,
    non-overlapping bands on the staff -- EVERY note of one entirely above
    EVERY note of the other.

    ⚠️ THE RANGE TEST, NOT THE MEAN. Sean offered both ("every up-stem head
    higher than every down-stem head, or by mean position"); the range is
    the stricter of the two -- a mean can agree while individual heads
    interleave -- and 2.19/2.21's own history (a rung reading, a clef guess)
    is full of cases where an aggregate hid a real exception. `Q.NOTEHEAD_
    STAFF_POSITION` is the CLEF-FREE geometric measurement (staff steps from
    the top line) built for exactly this: a page fact, not a pitch.

    Rests carry no position and are skipped -- they are not evidence for or
    against separation, only for or against the SUM (`_sum_beats`). `None`
    where either stream has no positioned notehead to test at all.
    """
    def _range(stream):
        vals = []
        for e in stream:
            if e.get("kind") != "chord":
                continue
            for g in e.get("_glyphs") or ():
                sub = Subject(Kind.GLYPH, page=cell.page, system=cell.system,
                              staff=cell.staff, cell=cell.cell, glyph=g)
                for r in ev.rows(Q.NOTEHEAD_STAFF_POSITION, subject=sub):
                    try:
                        vals.append(float(r.value))
                    except (TypeError, ValueError):
                        pass
        return (min(vals), max(vals)) if vals else None

    ra, rb = _range(stream_a), _range(stream_b)
    if ra is None or rb is None:
        return None, {"why": "no_position"}
    separated = ra[1] < rb[0] or rb[1] < ra[0]
    return separated, {"a_range": [round(ra[0], 3), round(ra[1], 3)],
                       "b_range": [round(rb[0], 3), round(rb[1], 3)]}


@decision(
    quantity=Q.VOICES,
    # ⚠️ 2.27c (displaced rests: `Q.STAFF_LINES` via `_rest_slot`) merged
    # with 2.21b (Sean's voice convention: onsets, meter, durations,
    # head positions).
    composed_from=(Q.STEM_DIRECTION, Q.EVENT, Q.GLYPH_BOX, Q.STAFF_LINES,
                   Q.STAFF_SPACING, Q.ONSET_COLUMN, Q.METER, Q.DURATION,
                   Q.NOTEHEAD_STAFF_POSITION),
    scope=Kind.CELL,
    wants=(Q.STEM_DIRECTION, Q.EVENT, Q.GLYPH_BOX, Q.STAFF_LINES,
           Q.STAFF_SPACING, Q.ONSET_COLUMN, Q.METER, Q.DURATION,
           Q.NOTEHEAD_STAFF_POSITION),
    reasons=("one_voice", "two_voices_same_beat", "one_voice_sums",
             "two_voices_separated_and_full", "no_voice_convention_fits",
             "nothing_to_split"),
    mode=Mode.ADDITIVE,
)
def adjudicate_voices(ev: Evidence) -> Ruling:
    """How many voice streams this bar holds, and which glyph is in each --
    Sean's convention, `docs/DECISIONS.md` 2026-09-29, answering
    `benchmarks/omr-voice-split-2026-09/QUESTION.md`'s 8 crops (all ONE
    voice): *"those crops would obviously be 1 voice because the measure
    math adds up to 1 measure."*

    Three rules, in this order, over the candidate `voicing.
    split_events_into_voices` would make from the up/down stem streams
    (CALLED, not restated -- the same arithmetic the exporter's `<backup>`
    depends on):

    1. **Same beat, opposite stems, is ALWAYS two voices** (`_voices_
       overlap_in_time`, unchanged from ROADMAP 2.21 -- some up-stem event
       and some down-stem event share an onset column). Decides outright.
    2. **One line whose durations sum to the METER IN FORCE is one voice**
       (*"the measure math adds up to 1 measure"*) -- tried next because it
       is the simpler, more committal claim: a bar that reads as ONE
       complete measure has no unexplained second voice to posit.
    3. **Two streams that are NOT lined up are still two voices where a
       human would recognise them another way: EACH stream on its own sums
       to a full measure AND the two sit in separate, vertically
       non-overlapping bands on the staff** (`_vertically_separated`) --
       *"two voices ... each line ... has a full measure of durations and
       the two are spaced apart on the staff, one above and one below."*

    Where none of the three fits -- no meter, an unread duration, sums that
    do not close, or two full streams that interleave in height (Sean's own
    positive control for "this is NOT two voices even though both sides are
    full") -- this ABSTAINS (`no_voice_convention_fits`, rule 8) rather than
    picking a side. `export._voice_split` already treats a non-decided
    `Q.VOICES` verdict as one stream, so nothing downstream is left without
    a fallback.

    ⚠️ ROADMAP 2.27c (a separate, concurrent lane) adds displaced-rest
    placement WITHIN an already-decided voice, in `export.py`. This decision
    is confined to the voice COUNT, upstream of that; no file overlap is
    expected, but both touch `voicing`-adjacent code and whichever lane
    lands second should re-read the other's FINDINGS.

    ⚠️ A COVER, NOT A PARTITION, once two voices ARE decided. A rest is in
    both streams and is written twice, so the exporter's note-accounting
    control has to know the duplicate is deliberate -- an equality that did
    not would raise `Unbalanced` for correct behaviour.

    ⚠️ IT NAMES GLYPHS AND NOT EVENTS. The exporter re-derives its own events
    from the detections it actually wrote, and a glyph key is the one address
    both sides agree on -- the same join `_place_articulations` and
    `_place_fermatas` use. It is also exactly the map `_paired_spans` wants:
    MusicXML pairs `<slur>` WITHIN a `<voice>`, and the staged exporter has
    been passing that test an EMPTY dict, so the rule was inert and
    indistinguishable from one that had run and found nothing.
    """
    grouping = ev.verdict(Q.EVENT)
    if grouping is None or grouping.outcome != "decided":
        # ⚠️ NOT "there are no voices" -- "nobody grouped this bar". The
        # exporter withholds a split rather than inventing one glyph per
        # stream, which is what building shim events out of glyph boxes here
        # would quietly have done.
        return Ruling.abstain("nothing_to_split",
                              event_outcome=(grouping.outcome if grouping
                                             else None))
    raw = (grouping.value or {}).get("events") or []
    if not raw:
        return Ruling.abstain("nothing_to_split", n_events=0)

    # ⚠️ ONE SHIM PER RECORDED EVENT, carrying only what the legacy splitter
    # reads. The record has already decided which glyphs sound together;
    # re-clustering them here would be a second grouping rule nothing forces
    # to agree with the first.
    events, read = [], 0
    for e in raw:
        glyphs = list(e.get("glyphs") or ())
        kind = e.get("kind") or "chord"
        direction = None
        if kind == "chord":
            # ⚠️ THE MAJORITY OVER THE CHORD, which is what
            # `group_chords_in_measure` puts on its own event. A chord whose
            # members genuinely disagree has already been SPLIT by the divisi
            # guard, so a disagreement surviving to here is one head whose
            # stem was missed, not two voices.
            votes = Counter()
            for g in glyphs:
                sub = Subject(Kind.GLYPH, page=ev.subject.page,
                              system=ev.subject.system,
                              staff=ev.subject.staff, cell=ev.subject.cell,
                              glyph=g)
                d = ev.verdict(Q.STEM_DIRECTION, subject=sub)
                if d is not None and d.outcome == "decided":
                    votes[d.value] += 1
            if votes:
                direction = votes.most_common(1)[0][0]
                read += 1
        events.append({"kind": kind, "x_position": float(e.get("x") or 0.0),
                       "stem_direction": direction, "_glyphs": glyphs})

    rests = sorted(g for e in events if e["kind"] == "rest"
                   for g in e["_glyphs"])
    up_events = [e for e in events if e["kind"] == "chord"
                and e["stem_direction"] == "up"]
    down_events = [e for e in events if e["kind"] == "chord"
                  and e["stem_direction"] == "down"]

    if not up_events or not down_events:
        # ⚠️ NO CANDIDATE TO GATE. `split_events_into_voices` would return
        # `[events]` here too (its own guard, restated nowhere) -- this is
        # the ordinary one-voice bar, not the convention question at all.
        streams, reason, rule_detail = [events], "one_voice", {}
    else:
        cell = ev.subject
        overlap, overlap_detail = _voices_overlap_in_time(ev, up_events,
                                                           down_events)
        rule_detail: Dict[str, Any] = {"rule_1_same_beat": overlap_detail}
        if overlap:
            # RULE (1): same beat, opposite stems -- ALWAYS two voices.
            streams = _legacy_voicing.split_events_into_voices(events)
            reason = "two_voices_same_beat"
        else:
            meter_segment = _meter_in_force(ev)
            target = _meter_quarters(meter_segment)
            rule_detail["meter"] = meter_segment
            if target is None:
                # No meter in force: rules (2)/(3) both need one to sum
                # against, and rule (1) already did not fire.
                return Ruling.abstain("no_voice_convention_fits",
                                      why="no_meter", **rule_detail)

            merged_sum = _sum_beats(ev, cell, events)
            rule_detail["merged_quarters"] = merged_sum
            rule_detail["target_quarters"] = target
            if _sums_to(merged_sum, target):
                # RULE (3): one line, and it sums to a full measure.
                streams, reason = [events], "one_voice_sums"
            else:
                # RULE (2): two streams NOT lined up, each its own full
                # measure, vertically separated.
                candidate = _legacy_voicing.split_events_into_voices(events)
                fits = False
                if len(candidate) == 2:
                    s0, s1 = candidate
                    sum0 = _sum_beats(ev, cell, s0)
                    sum1 = _sum_beats(ev, cell, s1)
                    rule_detail["stream_quarters"] = [sum0, sum1]
                    if _sums_to(sum0, target) and _sums_to(sum1, target):
                        sep, sep_detail = _vertically_separated(
                            ev, cell, s0, s1)
                        rule_detail["separation"] = sep_detail
                        fits = bool(sep)
                if fits:
                    streams = candidate
                    reason = "two_voices_separated_and_full"
                else:
                    return Ruling.abstain("no_voice_convention_fits",
                                          **rule_detail)

    # ⚠️ ROADMAP 2.27c: `split_events_into_voices` puts every rest in BOTH
    # streams unconditionally (its own docstring: "so each voice's bar can
    # sum"). Where exactly TWO streams exist and a rest's own ink sits
    # DECISIVELY off the staff's middle line, it is pulled OUT of the
    # stream it does not belong to -- the displaced rest joins ONE voice,
    # never both, and never the neighbour STAFF (this stays entirely within
    # `ev.subject`'s own cell; `Q.GLYPH_OWNER` is never read here). A
    # centred rest, or one whose geometry could not be read, is left exactly
    # as the legacy rule already had it.
    displaced: Dict[int, str] = {}
    if len(streams) > 1:
        for e in events:
            if e["kind"] != "rest":
                continue
            side = _rest_voice_side(ev, e["_glyphs"])
            if side == "upper":
                streams[1] = [o for o in streams[1] if o is not e]
                for g in e["_glyphs"]:
                    displaced[g] = "upper"
            elif side == "lower":
                streams[0] = [o for o in streams[0] if o is not e]
                for g in e["_glyphs"]:
                    displaced[g] = "lower"
    voices = [sorted(g for e in s for g in e["_glyphs"]) for s in streams]
    n = len(voices)
    # ⚠️ A DISPLACED REST HAS LEFT THE COVER: it is now in exactly one of
    # `voices`, not both, so it is no longer named here -- a consumer
    # counting glyphs across `voices` would otherwise double it AND find it
    # in `rests_in_every_voice`, over-reporting the duplication this field
    # exists to declare.
    covering = sorted(g for g in rests if g not in displaced)
    return Ruling(
        value={"n_voices": n, "voices": voices,
               # ⚠️ NAMED, because a rest in EVERY stream is the one place this
               # value is not a partition and a consumer counting glyphs would
               # otherwise report a loss. Empty in the one-voice case, where
               # there is no duplication to declare.
               "rests_in_every_voice": covering if n > 1 else [],
               "rests_displaced_by_position": displaced},
        reason=reason,
        used=(grouping.id,),
        detail={"n_events": len(events), "n_rests": len(rests),
                "directions_read": read, "n_rests_displaced": len(displaced),
                **rule_detail})
