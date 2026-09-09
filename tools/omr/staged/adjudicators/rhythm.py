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
from typing import Any, Dict, List, Optional, Tuple

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

METER_FROM_BARS_ENV = "OMR_METER_FROM_BARS"


def meter_from_bars_enabled() -> bool:
    """Read the flag. Anything but an explicit "1" is off."""
    return os.environ.get(METER_FROM_BARS_ENV, "0").strip() == "1"


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

    whole_rests = {r.subject for r in
                   ev.rows(Q.REST, scope=Scope.SELF_AND_DESCENDANTS)
                   if r.value == "restWhole"}

    bars = _bar_lengths_for(ev)
    agree = disagree = 0
    observed = Counter()
    return _score_bars(bars, expected)


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


def _meter_changes(ev: Evidence, opening: dict, bars: dict,
                   last_cell: dict) -> tuple:
    """Every mid-system meter change this system's own evidence supports.

    Takes its facts as arguments — `opening`, `bars` and `last_cell` — rather
    than reaching for them, which is how `bars` already worked. ⚠️ The
    inconsistency was surfaced by `inventory._never_read`, which follows a
    decision's own helpers to depth 3: with `last_cell` fetched HERE the read
    sat one level too deep and `measure_partition` was reported as an inert
    `wants` entry. The check was right that the call chain was one link longer
    than the others, and moving the fetch beside `_bar_lengths_for` is the fix
    the report was pointing at — not a workaround for it.

    Returns `(changes, cautionaries)` — segment dicts in bar order, each with
    `from_cell` and the terms that carried it. The GLYPH opens each candidate;
    the bar math confirms it, refuses it, or chooses between two staves that
    read it differently.

    ⚠️ A CAUTIONARY IS SEPARATED OUT RATHER THAN DROPPED — see `A-METER-5`
    above. It is a statement about the NEXT system and governs nothing here.
    """
    rows = ev.rows(Q.METER_GLYPH, scope=Scope.SELF_AND_DESCENDANTS)
    cautionaries: list = []
    by_cell: dict = {}
    for r in rows:
        cell = (r.detail or {}).get("cell")
        if cell is None or int(cell) == 0:
            continue                      # cell 0 states the staff's OPENING
        by_cell.setdefault(int(cell), []).append(r)

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
    for cell in sorted(by_cell):
        per_staff = {}
        for r in by_cell[cell]:
            per_staff.setdefault(r.subject.staff, []).append(r)

        # ⚠️ THE STAVES MAY DISAGREE, AND THE MATH IS WHAT SETTLES IT. On p.62
        # cell 8 one staff reads 3 over 4 and another reads four 4s; a vote
        # alone would tie. Each distinct reading is scored on its own, and the
        # bars that follow decide -- which is the layering working rather than
        # a tie-break rule.
        readings: dict = {}
        loose = 0
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
        if not readings:
            continue

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
                    "bars_fit": fits, "bars_contradict": misses,
                    "loose_digits": loose}
            if best is None or support > best["support"]:
                best = cand
        if best is None or best["support"] < METER_CHANGE_FLOOR:
            continue
        # ⚠️ THE CAUTIONARY TEST COMES BEFORE THE RESTATEMENT ONE, because a
        # courtesy signature is not a restatement of anything on THIS system —
        # it names the next one, and calling it a restatement would lose it.
        reading = best["staves_reading_it"]
        if (reading and all(last_cell.get(st) == cell for st in reading)
                and not best["bars_fit"]):
            cautionaries.append(dict(best, cautionary=True))
            continue
        if (best["numerator"], best["denominator"]) == in_force:
            continue                      # a RESTATEMENT, not a change
        out.append(best)
        in_force = (best["numerator"], best["denominator"])
    return out, cautionaries


def _with_segments(ev: Evidence, opening: dict) -> dict:
    """The system's meter, plus any change its own evidence supports.

    ⚠️ ONE FACT, NOT TWO. `segments` always exists -- a one-entry list where
    nothing changes -- so a consumer never has to ask whether this system is
    the special case. `record.meter_at` is how a bar's meter is read.
    """
    changes, cautionaries = _meter_changes(ev, opening, _bar_lengths_for(ev),
                                          _last_cell_per_staff(ev))
    segments = [dict(opening, from_cell=0)]
    for c in changes:
        segments.append({"from_cell": c["from_cell"],
                         "numerator": c["numerator"],
                         "denominator": c["denominator"],
                         "raw": c["raw"], "support": c["support"],
                         "staves_reading_it": c["staves_reading_it"],
                         "bars_fit": c["bars_fit"],
                         "bars_contradict": c["bars_contradict"]})
    out = dict(opening, segments=segments)
    if cautionaries:
        # ⚠️ ON THE VALUE, NOT IN `detail`, because it is a fact about the
        # music the next system opens with — a consumer reading this system's
        # meter is exactly who needs to find it.
        out["cautionary"] = cautionaries[-1]
    return out


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
        # ⚠️ A CARRIED METER IS STILL SUBJECT TO A CHANGE PRINTED ON THIS
        # SYSTEM. The carry says what the music was doing; a time signature
        # standing at bar N says it stopped doing it there.
        carried = {k: v for k, v in found.value.items() if k != "segments"}
        return Ruling(value=_with_segments(ev, carried), reason="carried",
                      used=(found.id,), margin=support, detail=detail)
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
    """
    here = ev.subject
    for src in reversed([s for s in ev.subjects(Kind.SYSTEM) if s < here]):
        found = ev.verdict(Q.METER, subject=src)
        if found is None or found.outcome is not Outcome.DECIDED:
            continue
        if found.reason != "voted":
            continue
        num, den = (found.value or {}).get("numerator"), \
                   (found.value or {}).get("denominator")
        if not num or not den:
            continue
        if abs(float(num) * 4.0 / float(den) - length) > 1e-6:
            continue
        return {"numerator": int(num), "denominator": int(den),
                "source": src.to_key(), "source_raw": (found.value or {}).get("raw"),
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
    if not meter_from_bars_enabled():
        return None
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
    changes, cautionaries = _meter_changes(ev, {}, _bar_lengths_for(ev),
                                          _last_cell_per_staff(ev))
    if cautionaries:
        detail = dict(detail, cautionary=cautionaries[-1])
    if not changes:
        return Ruling.abstain(why, **detail)
    first = changes[0]
    segments = [{"from_cell": c["from_cell"], "numerator": c["numerator"],
                 "denominator": c["denominator"], "raw": c["raw"],
                 "support": c["support"],
                 "staves_reading_it": c["staves_reading_it"],
                 "bars_fit": c["bars_fit"],
                 "bars_contradict": c["bars_contradict"]} for c in changes]
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
           Q.SYSTEM_STAFF_COUNT, Q.METER, Q.EVENT, Q.REST,
           Q.MEASURE_PARTITION),
    reasons=("voted", "no_agreement", "no_evidence",
             "too_few_staves_read_it", "carried",
             "carry_not_corroborated", "carry_outweighed_by_the_bars",
             "change_only", "derived_from_bars",
             "bars_name_a_length_without_a_form"),
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
        return _meter_fallbacks(ev, "no_evidence")

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
    return Ruling(value=_with_segments(ev, opening),
                  reason="voted", margin=share,
                  used=tuple(r.id for r in witnesses),
                  detail={"share": round(share, 3),
                          "n_staves_spoke": len(rows)})





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
