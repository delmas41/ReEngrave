"""Identity — the instrument, its slot, and what a `<part>` IS.

⚠️ THIS FILE HOLDS THE DECISION A PRE-REGISTERED GATE ALREADY FALSIFIED ONCE,
and the whole reason it is safe to express here is that the refusal is
mechanical rather than remembered.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..adjudicate import Evidence, Mode, Ruling, Term, decision, tally
from ..record import ABSTAIN, Kind, Q, Scope, State


@decision(
    quantity=Q.INSTRUMENT,
    scope=Kind.STAFF,
    wants=(Q.MARGIN_LABEL, Q.ROSTER_ENTRY, Q.STAFF_ORDINAL, Q.STAFF_GROUP),
    reasons=("label", "roster", "score_order", "no_evidence"),
    mode=Mode.ADDITIVE,
    stub=True,
)
def adjudicate_instrument(ev: Evidence) -> Ruling:
    """⚠️ DECLARED STUB, and the most consequential one in the build.

    What it must do when wired: consume `Q.MARGIN_LABEL` (the STRING, before
    the lexicon), run `instruments.lookup`, and fall back to the score-order
    layout prior. Its `Ruling.value` is a dict carrying at least
    `{"name", "family", "expected_clef"}` -- `adjudicators.clef` and
    `adjudicators.structure.adjudicate_group_symbol` both read those keys.

    ⚠️ THE PROVENANCE IS NOT A FIELD IT WRITES. Today identity records
    `instrument_source` and four consumers gate on it, and the tag is read at
    `contextual.py:1298` and `:1451` through `.get(slot, "label")` -- with
    the MOST PERMISSIVE tier as the default, which is the one value the three
    circularity refusals admit. Under this design the provenance is
    `Verdict.basis`, which cannot be defaulted because it is not a lookup.

    ⚠️ AND THE CIRCULARITY IT MUST NOT INTRODUCE: the score-order prior
    consumes clefs (`contextual.py:1208-1209`, `fit_layouts(..., clefs=
    clef_by_slot)`). That is what makes a `score_order` identity ineligible
    to anchor a clef decision, and the harness derives it from the basis --
    provided this decision actually records the clef verdicts it consumed.
    Wire the prior by READING `Q.CLEF` through `Evidence`, never by reaching
    around it, or the basis will lie.
    """
    return Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)


@decision(
    quantity=Q.SLOT_INDEX,
    scope=Kind.STAFF,
    wants=(Q.INSTRUMENT, Q.STAFF_ORDINAL, Q.SYSTEM_STAFF_COUNT),
    reasons=("aligned", "no_reference"),
    mode=Mode.ADDITIVE,
    stub=True,
)
def adjudicate_slot_index(ev: Evidence) -> Ruling:
    """⚠️ DECLARED STUB. `slots.assign_slots`' monotone alignment, moved.

    ⚠️ A SECOND HAZARD LIVES HERE THAT NO PROVENANCE TAG FIXES: a BAD
    ANCESTOR. `slots.align` inherits `build_reference`'s single-system pick,
    which once named 149 Brahms staves an instrument the work has not got.
    That is not circularity -- the evidence chain is perfectly acyclic and
    simply wrong -- so the filter will not catch it and neither will the
    basis. Its guard is a replay under `OMR_SPAN_REFERENCE_FIT=off`, and that
    is a TEST, not a mechanism.
    """
    return Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)


@decision(
    quantity=Q.PART_PARTITION,
    scope=Kind.DOCUMENT,
    wants=(Q.SLOT_INDEX, Q.STAFF_ORDINAL, Q.SYSTEM_STAFF_COUNT, Q.INSTRUMENT),
    reasons=("ordinal", "slot", "deduced_anchor", "no_evidence"),
    mode=Mode.ADDITIVE,
)
def adjudicate_part_partition(ev: Evidence) -> Ruling:
    """What a `<part>` IS.

    ⚠️ THE GATE THAT FALSIFIED THIS, AND HOW THE DESIGN ANSWERS IT.

    `export._stitch_slots` joins by staff ORDINAL and refuses when systems
    disagree about staff count; `_stitch_slots_by_slot` is the stronger join,
    reachable only behind a default-off flag. A pre-registered probe measured
    both against hand truth:

      * where ordinal SUCCEEDS (2 of 3 documents): slot and ordinal both
        match truth EXACTLY, 100% per-staff.
      * where ordinal REFUSES (1 of 3) -- the only population a change would
        newly touch: the slot join succeeds and is WRONG ON 3 OF 27 STAVES.
        It fails to continue "4 Hörner in Es" across a tacet break and grafts
        the genuinely-tacet "2 Trompeten in C" slot onto the horn.

    The root cause is a provenance-chain violation: all four contested staves
    carry `instrument_source: "score_order"` -- no margin label was read --
    and contextual is already wrong there, calling both horn staves Trumpet.
    The exporter would have consumed a DEDUCED identity as though it were a
    READ one. So the gate did not falsify the architecture; it exhibited it.

    ⚠️ THIS FUNCTION CONTAINS NO PROVENANCE CHECK, and that is the design
    working. `ev.verdict(Q.SLOT_INDEX)` returns `None` when the harness has
    excluded it as circular, and this falls through to the ordinal join and
    records `deduced_anchor`. On Brahms 1 p.2 that means the measured 3-of-27
    error NEVER SHIPS -- the row abstains from the slot join and behaves
    exactly as today.

    ⚠️ AND A THIRD FAILURE SHAPE NEITHER THIS NOR THE GATE ADDRESSES:
    `beethoven-sym5-mvt1-984073-p4` prints 11 staves in BOTH systems with
    DIFFERENT lineups (one suppresses Timpani and splits the bottom staff,
    the other keeps Timpani and condenses it). The equal-count check SUCCEEDS
    there and is still wrong. What this design contributes is only that
    `Verdict.considered` makes "decided on zero corroborating observations"
    visible -- an equal-count check is a constraint satisfiable by accident.
    """
    counts = ev.verdicts(Q.SYSTEM_STAFF_COUNT, scope=Scope.SELF_AND_DESCENDANTS)
    sizes = {v.value for v in counts if v.value is not None}

    if not sizes:
        return Ruling.abstain("no_evidence")

    if len(sizes) == 1:
        # The ordinal join succeeds. Measured identical to truth and to the
        # slot join on 3 documents -- so this is a deliberate no-op.
        return Ruling(value={"join": "ordinal", "staves_per_system": sizes.pop()},
                      reason="ordinal", used=tuple(v.id for v in counts))

    # The ordinal join REFUSES. This is the only population the change
    # touches, and it is where the slot join was measured wrong.
    slots = ev.verdicts(Q.SLOT_INDEX, scope=Scope.SELF_AND_DESCENDANTS)
    usable = [v for v in slots if v.value is not None]
    if not usable:
        # Either no slot was decided, or every one that was is a deduced
        # identity the harness refused. Both land here; the verdict's
        # `excluded` list says which, and it says so without this function
        # asking.
        return Ruling(value={"join": "ordinal", "reason": "slots_unusable"},
                      reason="deduced_anchor",
                      used=tuple(v.id for v in counts))

    return Ruling(value={"join": "slot",
                         "slots": sorted({v.value for v in usable
                                          if isinstance(v.value, int)})},
                  reason="slot", used=tuple(v.id for v in usable))
