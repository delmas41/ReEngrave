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


def _lcs_table(a: List[Optional[str]], b: List[Optional[str]]) -> List[List[int]]:
    """`t[i][j]` = the most names of `a[:i]` that can be paired, in order, with
    names of `b[:j]`. A `None` entry names nothing and pairs with nothing."""
    m, n = len(a), len(b)
    t = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            best = max(t[i - 1][j], t[i][j - 1])
            if a[i - 1] is not None and a[i - 1] == b[j - 1]:
                best = max(best, t[i - 1][j - 1] + 1)
            t[i][j] = best
    return t


def _forced_pairing(system: List[Optional[str]],
                    reference: List[Optional[str]]) -> List[Optional[int]]:
    """The reference slot each staff takes under EVERY best name pairing.

    A monotone pairing of this system's read instrument names against the
    document's reference lineup, deletions allowed on the reference side --
    which is what a tacet staff IS. The answer for a staff is its reference
    index when that index is the same under every MAXIMUM-cardinality
    pairing, and `None` otherwise.

    ⚠️⚠️ UNIQUENESS IS THE WHOLE RULE, AND IT IS NOT A THRESHOLD. This is
    `_reconcile_measure_to_meter`'s condition arriving in the identity layer:
    *the answer must be UNIQUE, else nothing changes*. A staff placed by a
    pairing that merely scores best is a GUESS wearing a number, and a guess
    here puts one instrument's music on another's staff -- the graft the part
    join exists to refuse.

    ⚠️ TWO CONDITIONS, AND THE SECOND IS THE ONE A FIRST CUT MISSES. A staff
    is forced to slot `j` only when (a) `j` is its only candidate under any
    best pairing, AND (b) no best pairing leaves it UNPAIRED. Without (b),
    reference `[A]` against a system reading `[A, A]` gives both staves the
    single candidate 0 -- each uniquely, and mutually exclusively -- and two
    staves of one system land in one part. The repeated-name case is exactly
    the one an orchestral page prints (two horn staves), so this is the
    common case and not a corner.

    ⚠️ IT NEVER SCORES POSITION. `slots.align` adds a position term and a
    bracket-group term, which PLACE A STAFF WHOSE NAME WAS NEVER READ; that
    is where the whole-work run's off-by-three lives (12 staves against a
    17-slot reference, five deletions taken at 12/13/14 instead of 9/10/11).
    An unnamed staff comes back `None` here and its decision abstains.
    """
    m, n = len(system), len(reference)
    if m == 0 or n == 0:
        return [None] * m
    pre = _lcs_table(system, reference)
    # the same table read from the other end
    rev = _lcs_table(system[::-1], reference[::-1])
    suf = [[rev[m - i][n - j] for j in range(n + 1)] for i in range(m + 1)]
    best = pre[m][n]

    out: List[Optional[int]] = []
    for i in range(m):
        name = system[i]
        if name is None:
            out.append(None)
            continue
        cands = [j for j in range(n)
                 if reference[j] == name
                 and pre[i][j] + 1 + suf[i + 1][j + 1] == best]
        if len(cands) != 1:
            out.append(None)
            continue
        # (b) could a best pairing leave this staff unpaired?
        unpaired = max(pre[i][j] + suf[i + 1][j] for j in range(n + 1))
        out.append(None if unpaired == best else cands[0])
    return out


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
    reasons=("full_lineup", "named", "paired_by_name", "no_reference",
             "no_ordinal", "reference_names_nothing", "unnamed_in_short_system",
             "not_in_reference", "ambiguous_pairing"),
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

    ⚠️⚠️ THE SHORT-SYSTEM RULE IS NOW BUILT, AND THE PARAGRAPH ABOVE WAS A
    CLAIM ABOUT CODE THAT DID NOT EXIST. Until 2026-09-11 this function
    described the name pairing in bold and returned the staff's own ordinal on
    every path -- so `adjudicate_part_partition` consumed a table that was the
    position, and the exporter joined systems of 12, 11 and 8 staves by
    position: 12 of 75 staff-systems on the wrong instrument, a Timpani part
    carrying the Viola's key signature. *A rule described in a docstring and
    never built is worse than a stale claim, because it reads as a claim about
    the code in front of you.*

    ⚠️ THE REFERENCE LINEUP IS THE DOCUMENT'S LARGEST SYSTEM, and the choice
    is STRUCTURAL rather than a fit: **a system can omit a tacet part, it can
    never invent one**, so the largest system printed is a lower bound on the
    lineup and no system can overflow it. That is deliberately NOT
    `slots.build_reference`, whose recurring-shape rule picked a reference a
    document could not express and named 149 Brahms staves an instrument the
    work has not got -- a BAD ANCESTOR no provenance tag catches, because the
    chain is acyclic and simply wrong. Where several systems tie at the
    largest size, the one reading the most names wins, and where those TIE
    TOO their name sequences must agree or this abstains `no_reference`: a
    reference chosen arbitrarily between two readings is the same fault at a
    smaller scale.

    ⚠️ AND `slots.align` IS DELIBERATELY NOT CALLED -- see `_forced_pairing`.
    It needs `Staff` objects this record does not carry, its bracket-group
    term would have to be fabricated (a constant +1.5 per pair against a
    -1.0 gap penalty, which biases every alignment toward taking), and its
    position term PLACES a staff whose name was never read. This rule places
    only what is forced.
    """
    ordinal = ev.verdict(Q.STAFF_ORDINAL)
    if ordinal is None or ordinal.value is None:
        return Ruling.abstain("no_ordinal")

    count = ev.verdict(Q.SYSTEM_STAFF_COUNT,
                       subject=ev.subject.at(Kind.SYSTEM))
    instrument = ev.verdict(Q.INSTRUMENT)

    if count is None or count.value is None:
        return Ruling.abstain("no_reference")

    document = ev.subject.at(Kind.DOCUMENT)
    counts = ev.verdicts(Q.SYSTEM_STAFF_COUNT, scope=Scope.SELF_AND_DESCENDANTS,
                         subject=document)
    sizes = {v.subject.at(Kind.SYSTEM): v.value
             for v in counts if v.value is not None}
    if not sizes:
        return Ruling.abstain("no_reference")
    widest = max(sizes.values())

    # ── the full lineup: position IS the answer, and this branch is unchanged
    if int(count.value) >= widest:
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

    # ── a SHORT system: staves are suppressed and position is what goes wrong
    names = _names_by_system(ev, document)
    reference = _pick_reference(sizes, widest, names)
    if reference is None:
        return Ruling.abstain("no_reference", n_staves=count.value)
    ref_system, ref_names = reference
    if not any(n is not None for n in ref_names):
        return Ruling.abstain("reference_names_nothing",
                              reference=ref_system.to_key())

    mine = names.get(ev.subject.at(Kind.SYSTEM), [])
    here = int(ordinal.value)
    if here >= len(mine) or mine[here] is None:
        return Ruling.abstain("unnamed_in_short_system",
                              reference=ref_system.to_key())

    pairing = _forced_pairing(mine, ref_names)
    slot = pairing[here]
    if slot is None:
        # ⚠️ TWO ABSTENTIONS, NOT ONE. A name the reference never prints wants
        # a wider lexicon or a re-read; a name the reference prints TWICE
        # wants a tie-break this decision does not have. Collapsing them sends
        # the next person to the wrong module.
        reason = ("not_in_reference" if mine[here] not in ref_names
                  else "ambiguous_pairing")
        return Ruling.abstain(reason, instrument=mine[here],
                              reference=ref_system.to_key())

    return Ruling(value=int(slot), reason="paired_by_name",
                  used=(ordinal.id,) + ((instrument.id,) if instrument else ()),
                  detail={"instrument": mine[here], "ordinal": here,
                          "n_staves": count.value,
                          "reference": ref_system.to_key(),
                          "reference_size": len(ref_names)})


def _names_by_system(ev: Evidence, document) -> Dict[object, List[Optional[str]]]:
    """`{system subject: [instrument name or None, by staff ordinal]}`.

    ⚠️ INDEXED BY THE STAFF'S OWN ORDINAL WITHIN ITS SYSTEM, never by the
    verdict's arrival order: `Subject.staff` is system-local by construction
    and a system with a gap in its subject tree would otherwise slide every
    name up one, which is the failure this whole decision exists to refuse.
    """
    out: Dict[object, List[Optional[str]]] = {}
    for v in ev.verdicts(Q.INSTRUMENT, scope=Scope.SELF_AND_DESCENDANTS,
                         subject=document):
        sub = v.subject
        if sub.kind is not Kind.STAFF or not isinstance(v.value, dict):
            continue
        row = out.setdefault(sub.at(Kind.SYSTEM), [])
        while len(row) <= sub.staff:
            row.append(None)
        row[sub.staff] = v.value.get("name")
    return out


def _pick_reference(sizes, widest, names):
    """The document's reference lineup: a LARGEST system, the one naming most.

    Returns `(system subject, [name or None])`, or None where two equally
    large, equally well-named systems disagree about what they name -- which
    is a genuine "cannot tell" and must not be resolved by taking the first.
    """
    widest_systems = sorted(s for s, n in sizes.items() if n == widest)
    if not widest_systems:
        return None

    def named(sub):
        return sum(1 for n in names.get(sub, []) if n is not None)

    most = max(named(s) for s in widest_systems)
    best = [s for s in widest_systems if named(s) == most]

    def padded(sub):
        row = list(names.get(sub, []))
        while len(row) < widest:
            row.append(None)
        return row

    first = padded(best[0])
    if any(padded(s) != first for s in best[1:]):
        return None
    return best[0], first


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
