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

import os
from typing import Optional, Tuple

from ..adjudicate import (Candidate, Checkable, Evidence, Mode, Ruling,
                          Term, decision, tally)
from collections import Counter

from ..record import (ABSTAIN, Kind, Outcome, Q, READERS, Scope, State,
                      Subject)


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


def _beam_levels(beams, x_center, width):
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
    """
    if x_center is None:
        return (0, 0)
    pad = (width or 0.0) * BEAM_EDGE_TOLERANCE_WIDTHS
    certain = possible = 0
    for b in beams:
        x0 = b.detail.get("x0", 0)
        x1 = b.detail.get("x1", 0)
        if x0 <= x_center <= x1:
            certain += 1
            possible += 1
        elif x0 - pad <= x_center <= x1 + pad:
            possible += 1
    return (certain, possible)

def _head_class(ev: Evidence) -> Optional[str]:
    rows = ev.rows(Q.NOTEHEAD_CLASS)
    if not rows:
        return None
    return max(rows, key=lambda r: (r.score or 0.0)).value


@decision(
    quantity=Q.DURATION,
    checkable=Checkable.MIXED,
    checked_by=(
        '"bar sum: the durations of one voice in one bar must equal the meter (rhythm_sum_warning -- 111 of 193 scan staves, UNCONSUMED)"',
    ),
    implicates=(Q.DURATION, Q.METER, Q.GLYPH_OWNER, Q.MEASURE_PARTITION,
                Q.TUPLET_RATIO),
    composed_from=(Q.BEAM_STROKE, Q.FLAG, Q.AUG_DOT, Q.NOTEHEAD_CLASS,
                   Q.STEM, Q.REST),
    scope=Kind.GLYPH,
    wants=(Q.BEAM_STROKE, Q.FLAG, Q.AUG_DOT, Q.NOTEHEAD_CLASS, Q.STEM,
           Q.TUPLET_RATIO, Q.GLYPH_BOX, Q.REST),
    reasons=("head_and_marks", "beams_ambiguous", "no_notehead",
             "unknown_head", "rest_class", "unreadable_rest"),
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

    base = None
    for name, beats in _HEAD_BEATS.items():
        if str(head).startswith(name):
            base = beats
            break
    if base is None:
        return Ruling.abstain("unknown_head", head=str(head))

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
    certain, possible = _beam_levels(kept, x_center, head_width)
    levels = certain
    used.extend(b.id for b in kept)

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

    flags = ev.rows(Q.FLAG)
    if flags and not levels:
        # A flag says the same thing a beam does for an unbeamed note.
        levels = len(flags)
        used.extend(r.id for r in flags)
        beam_evidence = "flag"
    beats = base / (2 ** levels) if levels else base

    # dots lengthen: each adds half of what stands so far.
    dots = ev.rows(Q.AUG_DOT)
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

    shared = {"head": str(head), "beam_evidence": beam_evidence,
              "cv_beams": len(cv), "yolo_beams": len(yolo),
              "yolo_kept": len(kept) - len(cv),
              "levels_certain": certain, "levels_possible": possible}

    # ⚠️ WHERE THE BEAM READING IS A RANGE, SO IS THE DURATION. Narrowing is
    # not a weaker answer than deciding -- it is the true one, and it is what
    # lets `reconcile_duration` search ADMITTED levels instead of arithmetic
    # +/-1. A note whose strokes are unambiguous still DECIDES.
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

    return Ruling(value={"beats": scaled, "written": total,
                         "dots": n_dots, "beam_levels": levels},
                  reason="head_and_marks", used=tuple(used), detail=shared)


def _rest_ruling(ev: Evidence, rest_rows) -> Ruling:
    """A rest's value is its CLASS, and almost nothing else.

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

    dots = ev.rows(Q.AUG_DOT)
    used = [row.id] + [r.id for r in dots]
    total, add = base, base
    for _ in range(len(dots)):
        add /= 2.0
        total += add

    ratio = ev.verdict(Q.TUPLET_RATIO, subject=ev.subject.at(Kind.CELL))
    return Ruling(
        value={"beats": total, "written": total, "dots": len(dots),
               "beam_levels": 0, "is_rest": True},
        reason="rest_class", used=tuple(used),
        detail={"rest": str(row.value), "written_type": written_type,
                "tuplet_in_cell": ratio is not None and ratio.value is not None})


def _scale(total: float, ratio, ev: Evidence) -> float:
    if ratio is not None and isinstance(ratio.value, dict):
        num, den = ratio.value.get("actual"), ratio.value.get("normal")
        if num and den and ev.subject.glyph in (ratio.value.get("members") or []):
            return total * den / num
    return total


@decision(
    quantity=Q.TUPLET_RATIO,
    checkable=Checkable.MIXED,
    checked_by=(
        '"bar sum: a wrong ratio breaks it"',
        '"the group must hold exactly as many notes as the digit claims"',
    ),
    implicates=(Q.TUPLET_RATIO, Q.DURATION, Q.METER),
    composed_from=(Q.TUPLET_MARKER, Q.BEAM_STROKE, Q.NOTEHEAD_CLASS),
    scope=Kind.CELL,
    wants=(Q.TUPLET_MARKER, Q.BEAM_STROKE, Q.NOTEHEAD_CLASS),
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
    marks = ev.rows(Q.TUPLET_MARKER, scope=Scope.SELF_AND_DESCENDANTS)
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
    wants=(Q.GLYPH_BOX, Q.NOTEHEAD_CLASS, Q.REST, Q.STEM),
    reasons=("x_clustered", "nothing_to_group"),
    mode=Mode.ADDITIVE,
    subjects_from=(Q.NOTEHEAD_CLASS, Q.REST),
)
def adjudicate_event(ev: Evidence) -> Ruling:
    """Which glyphs of this bar sound TOGETHER.

    ⚠️ THIS EXISTED ONLY AT SERIALISATION TIME UNTIL 2026-09-10.
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

    groups = []
    for g in sorted(head_ids, key=lambda i: boxes[i][0]):
        x = boxes[g][0]
        target = None
        # Backward scan: groups are created in non-decreasing x, so once one
        # is further than the tolerance every earlier one is too.
        for grp in reversed(groups):
            gx = sum(boxes[i][0] for i in grp) / len(grp)
            if abs(x - gx) > tol:
                break
            target = grp
            break
        if target is None:
            groups.append([g])
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
                # ⚠️ THE GUARD IS NOT BUILT, AND THIS FIELD MUST NOT IMPLY
                # IT IS. An earlier draft wrote `divisi_guard: "ran"` wherever
                # stem rows merely EXISTED -- a field claiming a check that
                # never happened, which is the failure this whole record
                # exists to make impossible. What is reported is the STATE OF
                # THE INPUT the guard would need. Where chords were formed and
                # this says anything but `read`, two divisi voices may have
                # been merged into one chord and nothing could have caught it.
                "divisi_guard": "not_implemented",
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


#: Carry a DECIDED meter forward onto systems that read none. Default OFF.
#:
#: ⚠️⚠️ IT IS OFF BECAUSE THE HAZARD IS MEASURED, NOT BECAUSE IT IS FEARED.
#: A meter is a fact of the MOVEMENT, so a carry is right until a movement
#: starts and catastrophic afterwards -- and on the very document the benefit
#: was measured on, THE MOVEMENT START READS NOTHING.
#:
#: Beethoven 5 / Litolff `984073`, one call each:
#:
#:   * BENEFIT -- p1/s0 decides `2/4` from **12 of 12** staves; p2/s0 reads
#:     nothing and p2/s1 reads 3 spurious `C`. Both want p1's answer.
#:   * HAZARD -- p17 is the *Andante con moto*, a NEW MOVEMENT printing `3/8`
#:     on every staff. All three of its systems abstain `no_evidence`: the
#:     template reader RAN on all 20 staves and declined `below_threshold`,
#:     because Litolff sets `3` over `8` as heavy nearly-touching digits that
#:     do not correlate with the Bravura templates. So an unconditional carry
#:     stamps movement 1's `2/4` onto the whole Andante.
#:
#: Four guards were looked for and each is REFUTED by measurement, not by
#: argument:
#:
#:   1. *"a movement start reads SOME meter, a continuation reads none"* --
#:      inverted. The continuations p14-p16 read 1-4 spurious `C`/`4/4`; the
#:      movement start reads 0.
#:   2. *the KEY SIGNATURE changes at a movement boundary* -- unusable on a
#:      scan. Only a handful of staves per system decide a key and they
#:      disagree with each other (p14/s1 reads {-5, -3, -1, 2}); the true -4
#:      of the Andante is never among them.
#:   3. *the printed TEMPO HEADING* -- p17 prints "Andante con moto." three
#:      times, and it is the right signal in principle. `direction` yields
#:      **0 decided verdicts** in the staged record today, so it cannot be
#:      asked.
#:   4. *a distance bound* -- DECISIVE. Movement 1 occupies pages 1-16, so a
#:      meter read on p1 legitimately governs 16 pages. Any bound under 16
#:      truncates a legitimate carry in this document and any bound of 16 or
#:      more reaches the Andante. No reach constant separates them.
#:
#: So the blocking input is named and it is a MOVEMENT-START signal, not a
#: tuning constant. Flip this the day one exists.
METER_CARRY_ENV = "OMR_METER_CARRY"


def meter_carry_enabled() -> bool:
    """Read the flag. Anything but an explicit "1" is off -- a typo must not
    switch a document onto a mechanism whose hazard is a whole wrong
    movement."""
    return os.environ.get(METER_CARRY_ENV, "0").strip() == "1"


# ─────────────────────────────────────────────────────────────────────────────
# A carried meter is WEIGHED, not gated. (A-METER-3)
#
# Sean, 2026-09-10: *"We need probability based decisions with layers of
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


def _carry_meter(ev: Evidence, instead_of: str) -> Optional[Ruling]:
    """The nearest preceding system whose meter was READ, or None.

    ⚠️ A CARRY NEVER CHAINS ONTO A CARRY. Only a `voted` verdict is a source,
    so `pages_since_read` is the true distance back to ink rather than the
    distance to whoever last repeated the answer. That is what makes the
    number in the record worth reading: a meter carried 16 pages is visibly
    suspect where a chain of 16 one-page hops would each look local.

    ⚠️ It is also why this needs no reach constant of its own -- see
    `METER_CARRY_ENV`, where the reach bound is refuted outright.
    """
    if not meter_carry_enabled():
        return None
    here = ev.subject
    for src in reversed([s for s in ev.subjects(Kind.SYSTEM) if s < here]):
        found = ev.verdict(Q.METER, subject=src)
        if found is None or found.outcome is not Outcome.DECIDED:
            continue
        if found.reason != "voted":
            continue
        pages = (here.page or 0) - (src.page or 0)
        # ⚠️⚠️ THE SECOND WITNESS, AND IT IS WHAT MAKES THE CARRY SAFE
        # WITHOUT A MOVEMENT DETECTOR. A carried meter is a CANDIDATE; this
        # system's own bars confirm or refuse it. A movement boundary needs no
        # detecting because the new movement's bars simply contradict the old
        # movement's meter -- measured 8 agree / 1 disagree on a continuation
        # page and 1 / 7 on the Andante.
        check = _corroborate(ev, found.value)
        if "terms" not in check:
            return Ruling.abstain("carry_not_corroborated",
                                  carried_from=src.to_key(),
                                  pages_since_read=pages,
                                  instead_of=instead_of, **check)
        # ⚠️ THE CARRY IS A TERM, NOT A DECISION. It enters the sum on the
        # same footing as the bars and can be outweighed by them.
        terms = [Term("carried_from_read_meter", W_METER_CARRIED,
                      (found.id,))] + check["terms"]
        support = tally(terms)
        detail = {"carried_from": src.to_key(),
                  "pages_since_read": pages,
                  "instead_of": instead_of,
                  "source_share": (found.detail or {}).get("share"),
                  "source_staves_spoke":
                      (found.detail or {}).get("n_staves_spoke"),
                  "support": round(support, 3),
                  "floor": METER_CARRY_FLOOR,
                  "bars_agree": check["bars_agree"],
                  "bars_disagree": check["bars_disagree"],
                  "bar_lengths_seen": check["bar_lengths_seen"]}
        if support < METER_CARRY_FLOOR:
            # ⚠️ Its own reason, and the SUPPORT is on the record beside it: a
            # carry the bars outweighed, a carry with nothing to check against
            # and a page with no carry available are three different pages,
            # and a reader must be able to tell them apart.
            return Ruling.abstain("carry_outweighed_by_the_bars", **detail)
        return Ruling(value=dict(found.value), reason="carried",
                      used=(found.id,), margin=support, detail=detail)
    return None


@decision(
    quantity=Q.METER,
    checkable=Checkable.MIXED,
    checked_by=(
        '"bar sum, on every bar of every staff it governs"',
        '"a meter is a SYSTEM fact: a mid-staff change no other staff witnessed is a misread (21 fired on scans, 0 survive)"',
    ),
    implicates=(Q.METER, Q.DURATION, Q.MEASURE_PARTITION),
    composed_from=(Q.METER_GLYPH, Q.METER_TEMPLATE, Q.DURATION),
    scope=Kind.SYSTEM,
    wants=(Q.METER_GLYPH, Q.METER_TEMPLATE, Q.DURATION, Q.DOSSIER_FACT,
           Q.SYSTEM_STAFF_COUNT, Q.METER, Q.EVENT, Q.REST),
    reasons=("voted", "no_agreement", "no_evidence",
             "too_few_staves_read_it", "carried",
             "carry_not_corroborated", "carry_outweighed_by_the_bars"),
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
    if not rows:
        # ⚠️ THE CARRY IS TRIED ONLY WHERE THIS SYSTEM'S OWN EVIDENCE FAILED,
        # so it can never overturn a reading. Off by default -- see
        # `METER_CARRY_ENV` for the movement-boundary hazard, measured.
        return _carry_meter(ev, "no_evidence") or Ruling.abstain("no_evidence")

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
        return _carry_meter(ev, "too_few_staves_read_it") or Ruling.abstain(
            "too_few_staves_read_it",
            coverage=round(coverage, 3),
            n_staves_spoke=len(rows),
            n_staves_on_system=total,
            would_have_been=best_raw)

    share = len(witnesses) / len(rows)
    if share < METER_AGREEMENT_FLOOR:
        # ⚠️ Recorded, not defaulted. A system whose staves disagree about the
        # meter is exactly the page a human should see.
        return _carry_meter(ev, "no_agreement") or Ruling.abstain(
            "no_agreement",
            share=round(share, 3),
            readings={k: len(v) for k, v in tally_.items()})

    return Ruling(value={"numerator": witnesses[0].value[0],
                         "denominator": witnesses[0].value[1],
                         "raw": best_raw},
                  reason="voted", margin=share,
                  used=tuple(r.id for r in witnesses),
                  detail={"share": round(share, 3),
                          "n_staves_spoke": len(rows)})



