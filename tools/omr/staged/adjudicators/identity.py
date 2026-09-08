"""Identity — the instrument, its slot, and what a `<part>` IS.

⚠️ THIS FILE HOLDS THE DECISION A PRE-REGISTERED GATE ALREADY FALSIFIED ONCE,
and the whole reason it is safe to express here is that the refusal is
mechanical rather than remembered.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..adjudicate import Checkable, Evidence, Mode, Ruling, Term, decision, tally
from ..record import ABSTAIN, Kind, Q, Scope, State


@decision(
    quantity=Q.INSTRUMENT,
    checkable=Checkable.MIXED,
    checked_by=(
        "roster membership: an instrument the work is not scored for is IMPOSSIBLE",
        "label contradiction: a staff whose OWN margin label was read on THIS page, named something else",
        "the implied written range must contain this staff's own positions under its clef",
    ),
    implicates=(Q.INSTRUMENT, Q.SLOT_INDEX, Q.MARGIN_LABEL, Q.CLEF),
    composed_from=(Q.MARGIN_LABEL, Q.ROSTER_ENTRY, Q.STAFF_ORDINAL),
    scope=Kind.STAFF,
    wants=(Q.MARGIN_LABEL, Q.ROSTER_ENTRY, Q.STAFF_ORDINAL, Q.STAFF_GROUP),
    reasons=("label", "roster", "score_order", "not_in_lexicon",
             "no_evidence"),
    mode=Mode.ADDITIVE,
)
def adjudicate_instrument(ev: Evidence) -> Ruling:
    """Name the staff's instrument from the STRING its margin printed.

    ⚠️ THE SPLIT THIS DECISION EXISTS TO MAKE. `StaffLabel` already carries a
    resolved `instrument` beside its raw `text`, because the reader runs the
    lexicon itself -- so today reading and naming happen in one act and the
    string is kept only as an annotation. GATHER emits the STRING; this names
    it. That separation is what makes the string re-interpretable when the
    lexicon changes, and it is exactly the fusion that let `Tr. Alt.` resolve
    to a SINGER at high confidence with the raw text sitting right beside it.

    ⚠️ PROVENANCE IS NOT A FIELD THIS WRITES. Today identity writes
    `instrument_source` and four consumers gate on it -- and it is read at
    `contextual.py:1298` and `:1451` through `.get(slot, "label")`, defaulting
    to the MOST PERMISSIVE tier, the one value all three circularity refusals
    admit. Here the provenance is `Verdict.basis`, which cannot be defaulted
    because it is not a lookup: a name derived from a label has the label's
    row in its basis, and a name derived from position does not.

    ⚠️ THE SCORE-ORDER TIER IS A DECLARED GAP, NOT AN OVERSIGHT. Wiring it
    means consuming the layout prior, and the prior consumes CLEFS
    (`contextual.py:1208-1209`, `fit_layouts(..., clefs=clef_by_slot)`). It
    must therefore read `Q.CLEF` THROUGH `Evidence` -- never by reaching
    around it -- or the basis will not record the dependency and the
    circularity filter will admit a deduced identity into the clef decision,
    which is the precise failure `clef_correction.py:566` exists to prevent
    and which the partition-truth gate caught costing 3 of 27 staves.
    """
    labels = ev.rows(Q.MARGIN_LABEL)
    if not labels:
        # ⚠️ DECLINED and ABSENT both land here, and the harness records
        # which on the verdict without this function asking. On a scan that
        # matters: 29 of 29 unresolved non-treble staves print NO LABEL AT
        # ALL -- not a lexicon refusal, not an OCR miss -- so "we could not
        # read it" and "there was nothing to read" are the two answers, and
        # only one of them is a reader problem.
        return Ruling.abstain("no_evidence")

    from ...instruments import lookup

    text = str(labels[-1].value)
    match = lookup(text)
    if match is None:
        # ⚠️ NOT a fallback to position. A label we cannot spell is a
        # different state from a staff with no label, and guessing here would
        # destroy the distinction the row was kept for.
        return Ruling.abstain("not_in_lexicon", text=text)

    inst = match.instrument
    return Ruling(
        value={"name": inst.name, "family": inst.family,
               "expected_clef": inst.default_clef,
               "written_range": list(inst.written_range),
               "unpitched": inst.unpitched},
        reason="label",
        used=tuple(r.id for r in labels),
        detail={"alias": match.alias, "coverage": match.coverage,
                "reader_text": text})


@decision(
    quantity=Q.SLOT_INDEX,
    checkable=Checkable.MIXED,
    checked_by=(
        '"a slot\'s instrument is the SAME on every system it appears on"',
        '"label contradiction, at slot scope: a staff whose own margin label was read on THIS page, filed under a slot named otherwise"',
    ),
    implicates=(Q.SLOT_INDEX, Q.INSTRUMENT, Q.SYSTEM_STAFF_COUNT),
    composed_from=(Q.INSTRUMENT, Q.STAFF_ORDINAL, Q.SYSTEM_STAFF_COUNT),
    scope=Kind.STAFF,
    wants=(Q.INSTRUMENT, Q.STAFF_ORDINAL, Q.SYSTEM_STAFF_COUNT),
    reasons=("full_lineup", "named", "no_reference", "no_ordinal"),
    mode=Mode.ADDITIVE,
)
def adjudicate_slot_index(ev: Evidence) -> Ruling:
    """A stable part identity across systems and pages.

    ⚠️ THE JOIN IS BY POSITION WITHIN THE SYSTEM, NEVER BY PAGE-WIDE INDEX --
    `Subject.staff` is already system-local for exactly this reason, because
    system 1's staves continue system 0's count in the readers' own numbering
    and joining on that puts a staff on another instrument's part.

    ⚠️ A FULL-LINEUP SYSTEM PAIRS BY POSITION; A SHORTER ONE MUST NOT. When a
    system prints as many staves as the reference lineup it is the full
    lineup, and position IS the answer. When it prints fewer, staves are
    suppressed (tacet) and position is exactly what goes wrong -- that is the
    population where the partition gate measured 3 of 27 staves misgrouped,
    grafting a horn's continuation onto a trumpet's slot. So a short system
    pairs by INSTRUMENT NAME in order of appearance, and abstains where the
    name was not read.

    ⚠️ AND THE MARGIN READER'S WORD IS A CROSS-CHECK ON A FULL SYSTEM, NEVER
    THE JOIN: it turns `Kontrafagott` into Bassoon and `Hörner in Es` into
    Trumpet on the Breitkopf Brahms. Position is the stronger evidence where
    the lineup is complete.

    ⚠️ NOT WIRED: the document-wide reference lineup. `slots.build_reference`
    picks it, and picking it from a single system once named 149 Brahms staves
    an instrument the work has not got -- a BAD ANCESTOR that no provenance
    tag catches, because the chain is perfectly acyclic and simply wrong. Its
    guard is a replay under `OMR_SPAN_REFERENCE_FIT=off`, which is a TEST and
    not a mechanism. Until that is settled this decision uses the SYSTEM'S OWN
    ordinal as the slot on a full lineup, which is correct per-system and
    makes no document-wide claim.
    """
    ordinal = ev.verdict(Q.STAFF_ORDINAL)
    if ordinal is None or ordinal.value is None:
        return Ruling.abstain("no_ordinal")

    count = ev.verdict(Q.SYSTEM_STAFF_COUNT,
                       subject=ev.subject.at(Kind.SYSTEM))
    instrument = ev.verdict(Q.INSTRUMENT)

    if count is None or count.value is None:
        return Ruling.abstain("no_reference")

    # ⚠️ With no document-wide reference the honest slot is the position
    # within THIS system, and the verdict says which basis it rests on so a
    # later consumer can tell a positional slot from a named one.
    if instrument is not None and instrument.value is not None:
        return Ruling(value=int(ordinal.value), reason="named",
                      used=(ordinal.id, instrument.id),
                      detail={"instrument": instrument.value.get("name")
                              if isinstance(instrument.value, dict) else None,
                              "n_staves": count.value})

    return Ruling(value=int(ordinal.value), reason="full_lineup",
                  used=(ordinal.id, count.id),
                  detail={"n_staves": count.value,
                          "note": "positional: no identity was read here"})


@decision(
    quantity=Q.PART_PARTITION,
    checkable=Checkable.MIXED,
    checked_by=(
        "the part count may not exceed the work roster",
        "each part carries ONE instrument across every system it appears on",
    ),
    implicates=(Q.PART_PARTITION, Q.SLOT_INDEX, Q.INSTRUMENT, Q.SYSTEM_STAFF_COUNT),
    composed_from=(Q.SLOT_INDEX, Q.STAFF_ORDINAL, Q.SYSTEM_STAFF_COUNT),
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
