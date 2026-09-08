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

from ..adjudicate import Checkable, Evidence, Mode, Ruling, Term, decision, tally
from ..record import ABSTAIN, Kind, Q, Scope, State

# ⚠️ ASSUMED WEIGHTS (A-OWN-1). Ordered to match the tiers the existing code
# already applies in this order; none is measured.
W_LADDER_COMPLETE = 4.0     # an unbroken run of ledger rungs
W_RANGE_IMPOSSIBLE = -6.0   # a veto on the IMPOSSIBLE, never on the unlikely
W_DISTANCE = 0.5            # the tie-break, and only that


@decision(
    quantity=Q.GLYPH_OWNER,
    checkable=Checkable.MIXED,
    checked_by=(
        "a spurious or missing notehead breaks the OWNING bar's duration sum -- so rhythm_sum_warning's group includes OWNERSHIP, not only duration and meter",
        "the owned glyph's implied pitch must fall in the owner's written range",
    ),
    implicates=(Q.GLYPH_OWNER, Q.DURATION, Q.METER, Q.INSTRUMENT),
    composed_from=(Q.GLYPH_BAND_DISTANCE, Q.GLYPH_LADDER, Q.INSTRUMENT, Q.CLEF),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_LADDER, Q.GLYPH_BAND_DISTANCE, Q.GLYPH_CONF,
           Q.NOTEHEAD_STAFF_POSITION, Q.INSTRUMENT, Q.CLEF),
    reasons=("ladder", "range_veto", "distance", "no_contest", "no_evidence",
             "tied"),
    mode=Mode.ADDITIVE,
    # ⚠️ The domain is the CONTESTED population. A glyph nobody disputes has
    # nothing to arbitrate, and a verdict per detection would bury 4,521 real
    # contests under tens of thousands of no-ops.
    subjects_from=Q.GLYPH_BAND_DISTANCE,
)
def adjudicate_glyph_owner(ev: Evidence) -> Ruling:
    """Which staff owns a contested glyph.

    ⚠️ THE CHANGE IS NOT A BETTER RULE. IT IS THAT THE DECISION MOVES. Today
    this runs 309 lines BEFORE identity, so its strongest tier -- the
    instrument's written range -- is structurally unavailable; on a scan it is
    doubly so, because `_staff_written_ranges` returns `{}` with no dossier
    and the scan gate is dossier-free by protocol. All 4,256 duplicates
    resolve on ladder or distance, 94.1% of them on distance alone.

    Here identity is ALREADY DECIDED when this runs, and that costs nothing,
    because adjudication reads a frozen record. This function is the test of
    the architecture's central ordering claim (A-ORDER-2).
    """
    bands = ev.rows(Q.GLYPH_BAND_DISTANCE)
    if not bands:
        # Uncontested: the glyph belongs to the staff whose cell it was cut
        # from, and there is nothing to arbitrate.
        own = ev.subject.at(Kind.STAFF)
        return Ruling(value=own.to_key(), reason="no_contest")

    ladders = {r.detail.get("candidate"): r for r in ev.rows(Q.GLYPH_LADDER)}

    scored = []
    for row in bands:
        cand_key = row.detail.get("candidate")
        if cand_key is None:
            continue
        terms = []

        # ── tier 1: the ledger ladder ───────────────────────────────────────
        lad = ladders.get(cand_key)
        if lad is not None and bool(lad.value):
            terms.append(Term("ladder_complete", W_LADDER_COMPLETE, (lad.id,)))
        # ⚠️ A BROKEN ladder contributes NOTHING -- not a negative. Two broken
        # ladders are not evidence either way: a found rung can belong to the
        # other staff's note exactly as a gap can, and on the Beethoven
        # bassoon pair the ghost's one rung WAS the real C4's own ledger.

        # ── tier 2: the written range, a veto on the IMPOSSIBLE ────────────
        veto = _range_veto(ev, cand_key, row)
        if veto is not None:
            terms.append(veto)

        # ── tier 3: distance, and ONLY as the tie-break ────────────────────
        try:
            spaces = float(row.value)
        except (TypeError, ValueError):
            spaces = 0.0
        terms.append(Term("distance", -W_DISTANCE * spaces, (row.id,)))

        # ⚠️ CONFIDENCE IS DECLARED AND DELIBERATELY NOT WEIGHTED. Measured
        # over 4,521 contested pairs: P(winner conf > loser conf) = 0.545
        # against a 0.500 null, and a |Δconf| > 0 tie-break would OVERTURN
        # DISTANCE ON 45.5% OF CONTESTS. It is in `wants` so a future hand has
        # to decline it deliberately rather than never see it.

        distance_only = [t for t in terms if t.name == "distance"]
        scored.append((tally(terms, correlated=ev.correlated_groups()),
                       cand_key, terms, tally(distance_only)))

    if not scored:
        return Ruling.abstain("no_evidence")

    scored.sort(key=lambda t: (-t[0], t[1]))
    top_score, top_key, top_terms, _d = scored[0]
    runner = scored[1][0] if len(scored) > 1 else None

    # ⚠️ THE REASON MUST NAME WHAT MADE THE DIFFERENCE, NOT WHAT THE WINNER
    # HAPPENS TO CARRY. A veto acts on the LOSER, so the winning candidate
    # holds no veto term -- reading the reason off the winner's own terms
    # reported "distance" for a contest that distance would have lost. The
    # honest test is whether the distance-only ranking disagrees with the
    # final one.
    by_distance = max(scored, key=lambda t: (t[3], [-ord(c) for c in t[1]]))
    vetoed = any(t.name == "range_impossible"
                 for _s, _k, ts, _d2 in scored for t in ts)

    if runner is not None and top_score == runner:
        # ⚠️ Two equal-cost mappings that disagree carry literally zero
        # information. Saying so beats breaking the tie on something measured
        # to be a coin flip.
        return Ruling.abstain("tied")

    if any(t.name == "ladder_complete" for t in top_terms):
        reason = "ladder"
    elif vetoed and by_distance[1] != top_key:
        reason = "range_veto"
    else:
        reason = "distance"

    return Ruling(value=top_key, reason=reason,
                  margin=(top_score - runner) if runner is not None else None,
                  used=tuple(r.id for r in bands),
                  detail={"scores": {k: sc for sc, k, _t, _d2 in scored},
                          "would_win_on_distance": by_distance[1]})


def _range_veto(ev: Evidence, cand_key: str, band_row):
    """A veto on the IMPOSSIBLE, never on the unlikely.

    ⚠️ ITS INPUT IS POSITION + CLEF, NOT A RESOLVED PITCH (A-OWN-2). Today the
    tier reads `det["pitch"]`, which is downstream of the clef -- fine while
    nothing feeds ownership back into the clef, and a cycle the moment
    anything does. Reading the position and the clef VERDICT separately means
    the basis records both, so the harness can SEE the loop if it is ever
    closed.
    """
    from ...pitch_resolver import _pitch_from_position, pitch_to_midi
    from ..record import Subject

    cand = Subject.from_key(cand_key)
    instrument = ev.verdict(Q.INSTRUMENT, subject=cand)
    if instrument is None or not isinstance(instrument.value, dict):
        return None                     # no identity: the tier cannot speak
    lo_hi = instrument.value.get("written_range")
    if not lo_hi or instrument.value.get("unpitched"):
        return None

    clef = ev.verdict(Q.CLEF, subject=cand)
    if clef is None or clef.value is None:
        # ⚠️ A staff whose clef abstained gets NO veto. Vetoing on a guessed
        # clef would be the "guessing twice" fault the key-signature reader
        # already refuses -- and it would be worse here, because a veto
        # DISCARDS ink.
        return None

    pos = band_row.detail.get("position_in_candidate")
    if pos is None:
        return None
    name = _pitch_from_position(int(round(float(pos))), str(clef.value))
    midi = pitch_to_midi(name) if name else None
    if midi is None:
        return None

    lo, hi = int(lo_hi[0]), int(lo_hi[1])
    if lo <= midi <= hi:
        return None                     # possible: the veto says nothing
    return Term("range_impossible", W_RANGE_IMPOSSIBLE,
                (instrument.id, clef.id, band_row.id))
@decision(
    quantity=Q.ARC_OWNER,
    composed_from=(Q.ARC_BOX, Q.NOTEHEAD_STAFF_POSITION),
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
    checkable=Checkable.MIXED,
    checked_by=(
        "a TIE joins two heads of the SAME staff step; an arc whose flanked heads sit on different steps is a SLUR",
    ),
    implicates=(Q.ARC_KIND, Q.NOTEHEAD_STAFF_POSITION, Q.CLEF),
    composed_from=(Q.ARC_BOX, Q.NOTEHEAD_STAFF_POSITION),
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
    composed_from=(Q.ARTICULATION_MARK, Q.GLYPH_BOX),
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
    composed_from=(Q.WEDGE_BOX, Q.GLYPH_BOX),
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
