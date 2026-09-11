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


def _slots_are_ordinals(slots) -> bool:
    """Is this slot table just the staff's position within its own system?

    True when EVERY system's slot values are exactly `0 .. n-1` for that
    system's own staff count -- i.e. the table expresses no suppression
    anywhere, and so carries no information the staff ordinal does not.

    ⚠️ WHAT MAKES A SLOT WORTH MORE THAN AN ORDINAL IS THE GAP. `slots.align`
    matches a system against a reference lineup with DELETIONS allowed, so a
    tacet staff shows up as a missing slot and the staves below it keep their
    identity. A contiguous table has made no such claim. This asks the VALUES,
    not the provenance, because the same values reach here under two different
    `reason`s and only one of them is about where they came from.

    ⚠️ A system whose slots repeat is not contiguous either, and falls out as
    False -- correctly: a repeat is a broken table, and `part_partition` has
    other evidence to weigh. Only a clean 0..n-1 is the ordinal.
    """
    # ⚠️ `sub.page` / `sub.system`, NOT `getattr(..., None)`. A `Q.SLOT_INDEX`
    # verdict is STAFF-scoped by declaration, so those fields are always
    # there; a defaulting read would bucket a wrongly-shaped subject under
    # `(None, None)` and SILENTLY MERGE two systems into one table, which is
    # this file's own rule that a fallback must never turn "cannot tell" into
    # a definite answer. Let it raise instead.
    by_system = {}
    for v in slots:
        key = (v.subject.page, v.subject.system)
        by_system.setdefault(key, []).append(v.value)
    if not by_system:
        return False
    return all(sorted(vals) == list(range(len(vals)))
               for vals in by_system.values())


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

    ⚠️⚠️ AND IT SHIPPED THE MEASURED 3-OF-27 ERROR ANYWAY, BY A ROUTE THE
    PARAGRAPH ABOVE DOES NOT COVER -- found 2026-09-11 on Litolff Beethoven 5
    mvt 1 p.1-4 (`benchmarks/omr-part-join-phase2-2026-09/`). The circularity
    filter excludes a DEDUCED identity; it has nothing to say about a slot
    that was never an identity at all. `adjudicate_slot_index` returns the
    staff's own ordinal when no name was read -- which it declares, in its own
    docstring and in its `detail` -- so `ev.verdicts(Q.SLOT_INDEX)` came back
    full, `usable` was non-empty, and this function reported `join: "slot"`
    over a table that was the position and nothing else. The exporter then
    joined systems of 12, 11 and 8 staves by ordinal: 12 of 75 staff-systems
    on the wrong instrument, a Timpani part carrying the Viola's key
    signature, and parts of 111 / 93 / 16 measures in one file.

    **A value can be honest at its own scope and a guess at the consumer's.**
    `_slots_are_ordinals` is the check that was missing, and it asks the
    VALUES rather than the provenance -- see the comment at its call site for
    why a reason string would not have held.

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
    if usable and _slots_are_ordinals(usable):
        # ⚠️⚠️ A SLOT TABLE THAT IS THE ORDINAL *IS* THE ORDINAL, AND JOINING
        # ON IT IS THE JOIN THIS BRANCH HAS JUST REFUSED.
        #
        # Reaching here means the systems disagree about staff count. The
        # only reason to prefer a slot over the ordinal is that a slot
        # EXPRESSES the tacet case -- a suppressed staff leaves a GAP, so
        # the staves below it keep their identity instead of shifting up.
        # A table that numbers every system 0..n-1 with no gap anywhere has
        # expressed no such thing: it is the position, relabelled, and
        # consuming it would graft one instrument's music onto another,
        # which is the exact failure `export._stitch_slots`' refusal exists
        # to prevent and which its own docstring calls "correct and stays".
        #
        # ⚠️ MEASURED, Litolff Beethoven 5 mvt 1 pdf p.1-4
        # (`benchmarks/omr-part-join-phase2-2026-09/`): all 75 slots came
        # back as the staff's own ordinal, `adjudicate_slot_index` having no
        # document-wide reference to pair against -- which its own docstring
        # declares ("NOT WIRED: the document-wide reference lineup ... uses
        # the SYSTEM'S OWN ordinal ... and makes no document-wide claim").
        # That value is honest AT STAFF SCOPE and was being consumed HERE as
        # a document-wide claim. The result was 12 of 75 staff-systems joined
        # to the wrong instrument, including a Timpani part carrying the
        # Viola's key signature, and parts of 111 / 93 / 16 measures in one
        # file.
        #
        # ⚠️ THE TEST IS STRUCTURAL, NOT A REASON STRING, and that is
        # deliberate: `adjudicate_slot_index` returns the ordinal under BOTH
        # its reasons -- `named` differs from `full_lineup` only in what it
        # cites, not in what it computes -- so filtering on the reason would
        # admit the identical graft the moment a margin label is read.
        #
        # ⚠️ IT IS ONE-SIDED AND THE COST IS REAL: a score that suppresses
        # only its LAST staves has a genuine slot table that is also
        # contiguous, and this refuses a join that would have been right.
        # That is abstention, not error, and the repair is a slot table that
        # can express a gap -- see `adjudicate_slot_index`.
        return Ruling(value={"join": "ordinal", "reason": "slots_are_ordinals"},
                      reason="deduced_anchor",
                      used=tuple(v.id for v in counts),
                      detail={"slots_are_ordinals": True,
                              "staves_per_system": sorted(sizes),
                              "note": "the slot table is the staff position, "
                                      "so joining on it is the ordinal join "
                                      "this branch refused"})
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
