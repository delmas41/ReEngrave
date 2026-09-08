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

from ..adjudicate import Checkable, Evidence, Mode, Ruling, decision
from ..record import ABSTAIN, Kind, Q, Scope, State


@decision(
    quantity=Q.DURATION,
    checkable=Checkable.MIXED,
    checked_by=(
        "bar sum: the durations of one voice in one bar must equal the meter (rhythm_sum_warning -- 111 of 193 scan staves, UNCONSUMED)",
    ),
    implicates=(Q.DURATION, Q.METER, Q.GLYPH_OWNER, Q.MEASURE_PARTITION, Q.TUPLET_RATIO),
    composed_from=(Q.BEAM_STROKE, Q.FLAG, Q.AUG_DOT, Q.NOTEHEAD_CLASS, Q.STEM),
    scope=Kind.GLYPH,
    wants=(Q.BEAM_STROKE, Q.FLAG, Q.AUG_DOT, Q.NOTEHEAD_CLASS, Q.STEM),
    reasons=("beams_and_dots", "no_evidence"),
    mode=Mode.ADDITIVE,
    stub=True,
)
def adjudicate_duration(ev: Evidence) -> Ruling:
    """⚠️ DECLARED STUB. `rhythm.resolve_rhythms_for_cell`, moved.

    Two constants that must come across unchanged, because both were paid for:

      * the augmentation-dot window is ASYMMETRIC (0.75 spaces above, 0.25
        below). A dot goes above its note or level with it, never under, and
        a symmetric window ties on Brahms's double stops -- the upper note
        comes out double-dotted and the lower loses its dot.
      * a YOLO beam box bounds the STACK, not a stroke, so it is kept ONLY
        where no CV beam overlaps its x-range. Unioning them contributes a
        centre in the GAP between two strokes and three sixteenths read as
        three eighths.
    """
    return Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)


@decision(
    quantity=Q.TUPLET_RATIO,
    checkable=Checkable.MIXED,
    checked_by=(
        "bar sum: a wrong ratio breaks it",
        "the group must hold exactly as many notes as the digit claims",
    ),
    implicates=(Q.TUPLET_RATIO, Q.DURATION, Q.METER),
    composed_from=(Q.TUPLET_MARKER, Q.BEAM_STROKE, Q.NOTEHEAD_CLASS),
    scope=Kind.CELL,
    wants=(Q.TUPLET_MARKER, Q.BEAM_STROKE, Q.NOTEHEAD_CLASS),
    reasons=("digit", "bracket", "no_marker", "no_evidence"),
    mode=Mode.ADDITIVE,
    stub=True,
)
def adjudicate_tuplet(ev: Evidence) -> Ruling:
    """⚠️ DECLARED STUB. Two markers, read DIFFERENTLY because they sit
    differently: the DIGIT is printed over the middle of its group so its
    centre must fall inside the group's span; the BRACKET encloses the group
    so the group must fall inside the BRACKET's span. Testing a bracket's
    centre rejects every one of them.

    ⚠️ A GROUP IS A SET OF NOTES, NOT A BEAM STROKE. A sixteenth carries two
    strokes, and applying the ratio once per stroke gives a triplet sixteenth
    (1/4) x (2/3) x (2/3) = 1/9. Identical member sets must collapse.

    ⚠️ Read BOTH `tuplet3` and `fingering3`: DSv2's distinction is POSITIONAL
    and the detector reproduces it badly -- 33 `fingering3` against 16
    `tuplet3` over twelve works, and all 33 sit in a cell holding a real
    triplet.
    """
    return Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)


@decision(
    quantity=Q.METER,
    checkable=Checkable.MIXED,
    checked_by=(
        "bar sum, on every bar of every staff it governs",
        "a meter is a SYSTEM fact: a mid-staff change no other staff witnessed is a misread (21 fired on scans, 0 survive)",
    ),
    implicates=(Q.METER, Q.DURATION, Q.MEASURE_PARTITION),
    composed_from=(Q.METER_GLYPH, Q.METER_TEMPLATE, Q.DURATION),
    scope=Kind.SYSTEM,
    wants=(Q.METER_GLYPH, Q.METER_TEMPLATE, Q.DURATION, Q.DOSSIER_FACT),
    reasons=("read", "voted", "carried", "no_evidence"),
    mode=Mode.ADDITIVE,
    stub=True,
)
def adjudicate_meter(ev: Evidence) -> Ruling:
    """⚠️ DECLARED STUB. A meter is a fact of the SYSTEM, read per staff.

    Three rules that must survive the port:

      * ONE VOTE PER STAFF. A meter is carried onto every later measure of
        its staff, so counting measures counts one reading many times -- a
        single `timeSig4` at confidence 0.42 on one staff of nineteen once
        arrived at the page vote as eighteen unanimous votes for common time.
      * A MID-STAFF CHANGE NEEDS A SYSTEM-WIDE WITNESS. A change is printed
        on every staff at the same bar. 21 fired on scans, 0 survive.
      * A DERIVED METER MAY NOT VOTE FOR ITSELF. That is
        `rhythm._READING_SOURCES`, the best-enforced provenance tag in the
        tree, and under this design it is the circularity filter: a meter
        whose basis contains `Q.DURATION` cannot also be evidence for the
        duration that produced it.
    """
    return Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)
