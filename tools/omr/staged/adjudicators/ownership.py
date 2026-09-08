"""Ownership — which staff a contested glyph belongs to, and the arcs.

⚠️ THE CHANGE HERE IS NOT A BETTER RULE. IT IS THAT THE DECISION MOVES.

Today `_dedupe_cross_staff_detections` runs 309 lines BEFORE identity, so its
strongest tier -- the instrument's written range -- is unavailable when it
decides. On a scan the tier is additionally vacuous: `_staff_written_ranges`
returns `{}` with no dossier and the scan gate runs dossier-free by protocol,
so all 4,256 duplicates resolve on ladder or distance. Under the split,
ownership is adjudicated AFTER identity and that costs nothing, because
adjudication reads a frozen record.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..adjudicate import Evidence, Mode, Ruling, Term, decision, tally
from ..record import ABSTAIN, Kind, Q, Scope, State

# ⚠️ ASSUMED WEIGHTS (A-OWN-1). Ordered to match the tiers the existing code
# already applies in this order; none is measured.
W_LADDER_COMPLETE = 4.0     # an unbroken run of ledger rungs
W_RANGE_IMPOSSIBLE = -6.0   # a veto on the IMPOSSIBLE, never on the unlikely
W_DISTANCE = 0.5            # the tie-break, and only that


@decision(
    quantity=Q.GLYPH_OWNER,
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_LADDER, Q.GLYPH_BAND_DISTANCE, Q.GLYPH_CONF,
           Q.NOTEHEAD_STAFF_POSITION, Q.INSTRUMENT, Q.CLEF),
    reasons=("ladder", "range_veto", "distance", "no_contest", "no_evidence"),
    mode=Mode.ADDITIVE,
    stub=True,
)
def adjudicate_glyph_owner(ev: Evidence) -> Ruling:
    """⚠️ DECLARED STUB — the arbitration, moved but not yet ported.

    The tiers, in the order a reader uses them, and the constraints on each:

    1. LADDER COMPLETENESS -- an unbroken run of ledger rungs joining the
       glyph to a staff. ⚠️ COMPLETENESS ONLY, NEVER COUNT. Two broken
       ladders are not evidence either way, because a found rung can belong
       to the other staff's note exactly as a gap can: on the Beethoven
       bassoon pair the ghost's one rung WAS the real C4's own ledger, and
       counting it beat the real note.
    2. WRITTEN RANGE -- a veto on the IMPOSSIBLE, never on the unlikely. Now
       reachable, because identity is already adjudicated.
       ⚠️ Its input must be `Q.NOTEHEAD_STAFF_POSITION` plus the `Q.CLEF`
       verdict, NOT a resolved pitch. Today it reads `det["pitch"]`
       (`transcribe.py:3153-3154`), an interpretation, which is not a cycle
       today but becomes one the moment a clef adjudicator reads ownership.
       Declaring both here means the basis records it and the harness can see
       the loop if anyone ever closes it.
    3. DISTANCE -- the tie-break, unchanged.

    ⚠️ CONFIDENCE IS DECLARED AND MUST NOT BE WEIGHTED. Measured over 4,521
    contested pairs: P(winner conf > loser conf) = 0.545 against a 0.500
    null, and a |Δconf| > 0 tie-break would OVERTURN DISTANCE ON 45.5% OF
    CONTESTS. It is in `wants` so that a future hand has to decline it
    deliberately rather than never see it. Ownership's missing evidence is
    identity, not confidence.
    """
    return Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)


@decision(
    quantity=Q.ARC_OWNER,
    scope=Kind.GLYPH,
    wants=(Q.ARC_BOX, Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_OWNER),
    reasons=("hugs_noteheads", "no_better_staff", "no_evidence"),
    mode=Mode.ADDITIVE,
    stub=True,
)
def adjudicate_arc_owner(ev: Evidence) -> Ruling:
    """⚠️ DECLARED STUB. `OMR_ARC_ATTRIBUTION`'s rule, moved.

    The evidence is the arc's own job: an arc binds a run of noteheads and is
    drawn just clear of them, so it belongs to the staff whose NOTEHEADS IT
    HUGS -- asked of every staff in the system, including ones that never
    detected it. ⚠️ Distance to the staff LINES is the trap: an engraver
    opens the gap above a staff precisely so its ledger notes and their slurs
    can live there. The rule must stay COMPARATIVE -- an arc leaves only
    where another staff explains it better.
    """
    return Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)


@decision(
    quantity=Q.ARC_KIND,
    scope=Kind.GLYPH,
    wants=(Q.ARC_BOX, Q.NOTEHEAD_STAFF_POSITION),
    reasons=("tie", "slur", "no_evidence"),
    mode=Mode.ADDITIVE,
    stub=True,
)
def adjudicate_arc_kind(ev: Evidence) -> Ruling:
    """⚠️ DECLARED STUB, and one with a measured REFUSAL attached.

    The position-grammar veto exists (`OMR_ARC_RECLASS`) and is default-off
    for a measured reason: engraved 0.1306 -> 0.1306 (+2 edits) but scan
    0.8387 -> 0.8391, +130 edits, ALL of them in the tie->slur half. Compare
    STAFF STEPS, never spelled pitches -- the far head of a cross-barline tie
    does not restate its accidental, so a spelled-pitch key breaks
    truth-matched ties. If any half ever defaults on it is slur->tie.
    """
    return Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)


@decision(
    quantity=Q.ARTICULATION_OWNER,
    scope=Kind.GLYPH,
    wants=(Q.ARTICULATION_MARK, Q.GLYPH_BOX),
    reasons=("nearest_on_declared_side", "no_notehead", "no_evidence"),
    mode=Mode.ADDITIVE,
    stub=True,
)
def adjudicate_articulation_owner(ev: Evidence) -> Ruling:
    """⚠️ DECLARED STUB. Give each mark to the notehead nearest it in x on
    the side ITS OWN CLASS NAMES, within 0.75 notehead WIDTHS -- the unit,
    not the mark's own bounding box, which is the mistake the augmentation-dot
    gate made. A mark with no notehead on the correct side stays unattached.
    """
    return Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)


@decision(
    quantity=Q.WEDGE_ANCHOR,
    scope=Kind.GLYPH,
    wants=(Q.WEDGE_BOX, Q.GLYPH_BOX),
    reasons=("nearest_either_side", "no_anchor", "no_evidence"),
    mode=Mode.ADDITIVE,
    stub=True,
)
def adjudicate_wedge_anchor(ev: Evidence) -> Ruling:
    """⚠️ DECLARED STUB. A slur is drawn OVER its notes; a hairpin BETWEEN
    them, so an overlap test scores 0 of 4 and the edges must be read as
    POINTERS. Nearest-either-side pairs 4 of 8 truth hairpins and gets all 4
    right; "the last note at or before the edge" pairs 1, because the ink
    begins slightly BEFORE the note it starts on.
    """
    return Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)
