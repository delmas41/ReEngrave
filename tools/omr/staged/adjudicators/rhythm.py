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

from typing import Optional

from ..adjudicate import Checkable, Evidence, Mode, Ruling, decision
from ..record import ABSTAIN, Kind, Q, READERS, Scope, State


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


def _beam_levels(beams, x_center: Optional[float]) -> int:
    """How many strokes cover this notehead's column.

    ⚠️ THE LEVEL IS AN INTERPRETATION OVER STROKES, WHICH IS WHY IT IS
    COMPUTED HERE AND NOT IN GATHER. Emitting a level as a measurement would
    put the arbitration in the gathering phase -- the fault the whole split
    exists to remove.
    """
    if x_center is None:
        return 0
    return sum(1 for b in beams
               if b.detail.get("x0", 0) <= x_center <= b.detail.get("x1", 0))


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
    composed_from=(Q.BEAM_STROKE, Q.FLAG, Q.AUG_DOT, Q.NOTEHEAD_CLASS, Q.STEM),
    scope=Kind.GLYPH,
    wants=(Q.BEAM_STROKE, Q.FLAG, Q.AUG_DOT, Q.NOTEHEAD_CLASS, Q.STEM,
           Q.TUPLET_RATIO, Q.GLYPH_BOX),
    reasons=("head_and_marks", "no_notehead", "unknown_head"),
    mode=Mode.ADDITIVE,
    subjects_from=Q.NOTEHEAD_CLASS,
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
    x_center = None
    if box:
        v = box[-1].value
        if isinstance(v, (list, tuple)) and len(v) >= 4:
            x_center = float(v[1]) + float(v[3]) / 2.0
        used.append(box[-1].id)

    cell = ev.subject.at(Kind.CELL)
    kept, cv, yolo = _kept_beams(ev, cell)
    levels = _beam_levels(kept, x_center)
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

    return Ruling(value={"beats": scaled, "written": total,
                         "dots": n_dots, "beam_levels": levels},
                  reason="head_and_marks", used=tuple(used),
                  detail={"head": str(head),
                          "beam_evidence": beam_evidence,
                          "cv_beams": len(cv), "yolo_beams": len(yolo),
                          "yolo_kept": len(kept) - len(cv)})


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


#: A meter must be agreed by this share of the staves that SPOKE. (A-METER-1)
#: ⚠️ Not tuned here, but not arbitrary either: over an 11-source corpus every
#: one of the 12 correct readings was agreed by 0.909 of its system or more,
#: and the single WRONG reading by exactly 0.500.
METER_AGREEMENT_FLOOR = 0.70


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
    wants=(Q.METER_GLYPH, Q.METER_TEMPLATE, Q.DURATION, Q.DOSSIER_FACT),
    reasons=("voted", "no_agreement", "no_evidence"),
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
        return Ruling.abstain("no_evidence")

    tally_: dict = {}
    for row in rows:
        raw = row.detail.get("raw") or str(row.value)
        tally_.setdefault(raw, []).append(row)

    best_raw, witnesses = max(tally_.items(), key=lambda kv: len(kv[1]))
    share = len(witnesses) / len(rows)
    if share < METER_AGREEMENT_FLOOR:
        # ⚠️ Recorded, not defaulted. A system whose staves disagree about the
        # meter is exactly the page a human should see.
        return Ruling.abstain("no_agreement",
                              share=round(share, 3),
                              readings={k: len(v) for k, v in tally_.items()})

    return Ruling(value={"numerator": witnesses[0].value[0],
                         "denominator": witnesses[0].value[1],
                         "raw": best_raw},
                  reason="voted", margin=share,
                  used=tuple(r.id for r in witnesses),
                  detail={"share": round(share, 3),
                          "n_staves_spoke": len(rows)})



