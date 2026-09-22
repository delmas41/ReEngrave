"""Identity — the instrument, its slot, and what a `<part>` IS.

⚠️ THIS FILE HOLDS THE DECISION A PRE-REGISTERED GATE ALREADY FALSIFIED ONCE,
and the whole reason it is safe to express here is that the refusal is
mechanical rather than remembered.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Set, Tuple

from ..adjudicate import Checkable, Evidence, Mode, Ruling, Term, decision, tally
from ..record import ABSTAIN, Candidate, Kind, Q, Scope, State


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
             "no_evidence", "vetoed_by_the_work_roster"),
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
    must therefore read the clef THROUGH `Evidence` -- never by reaching
    around it -- or the basis will not record the dependency and the
    circularity filter will admit a deduced identity into the clef decision,
    which is the precise failure `clef_correction.py:566` exists to prevent
    and which the partition-truth gate caught costing 3 of 27 staves.

    ⚠️⚠️ AND THIS PARAGRAPH NAMED THE WRONG OBJECT UNTIL 2026-09-21: it said
    `Q.CLEF`, which is a VERDICT AT `ORDER` 9 while this decision runs at
    `ORDER` 5 -- so the instruction as written could never be carried out, and
    a session following it would reach for a quantity that does not exist yet.
    The reachable objects are `Q.CLEF_GLYPH` and `Q.CLEF_POSITION`, GATHER
    facts available at every ORDER, and reading THOSE cannot close the loop:
    the hazard is admitting a DEDUCED identity into the clef decision, and a
    glyph is a reading of ink rather than a deduction. That is CLAUDE.md's
    *a circularity fear resting on the wrong object*, and Sean's own words on
    it -- "we should know what these are regardless of clef, and having a clef
    would only reinforce the finding." The gap is still a gap; what changed is
    that it is now stated in terms that can be acted on. See
    `docs/NEXT-2026-09-22-instrument-identification.md`.
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
    from ... import work_roster as WR

    text = str(labels[-1].value)
    match = lookup(text)

    # ⚠️⚠️ `Scope.SELF_AND_ANCESTORS`, AND AN `EXACT` READ HERE WOULD HAVE
    # RETURNED NOTHING FOREVER. `Q.ROSTER_ENTRY` is filed on the DOCUMENT —
    # it is a fact about the WORK, not about this staff — and this decision
    # runs at `Kind.STAFF`, where `Evidence.rows`' default `Scope.EXACT`
    # reaches only the staff's own rows. The declaration would have been
    # present, the quantity gathered, the `wants` entry satisfied, and the
    # answer empty: the FRAME fault CLAUDE.md records four instances of and
    # states neither `inventory --check` nor `gather_coverage` can see.
    # `staged.wiring` flagged it as LATENT before this line existed.
    roster_rows = ev.rows(Q.ROSTER_ENTRY, scope=Scope.SELF_AND_ANCESTORS)
    roster = _work_roster(roster_rows[-1].value) if roster_rows else None

    # ⚠️ THE RULE IS IMPORTED, NOT RESTATED, and this project has paid to
    # learn why. `work_roster.decide` is the measured one: 28 firings over
    # 1,422 real margin labels, every one hand-adjudicated correct, with four
    # outcomes whose risks differ and an ORDER between them that was MEASURED
    # (recovery before disambiguation — the other order reads `mbone Basso`
    # as a Contrabass, confidently and wrongly). Restating any of that here
    # would give this repo two copies of numbers it paid to measure once, and
    # the copies would drift.
    decided = WR.decide(text, roster, hit=match)
    used = tuple(r.id for r in labels) + tuple(r.id for r in roster_rows)

    if decided.kind == "vetoed":
        # ⚠️ A VETO REMOVES A NAME; IT NEVER INSTALLS ONE. `Decision.
        # names_a_staff` is False here by construction, which is what makes
        # this the safe half of the layer: the lexicon had already got this
        # staff wrong (a SINGER on a work with no singers), and the answer is
        # to stop saying so — not to guess what it is instead.
        #
        # ⚠️ CONSTRUCTED RATHER THAN `Ruling.abstain`, AND THE DIFFERENCE IS
        # THE BASIS. `Ruling.abstain` takes no `used`, so an abstention it
        # builds names NOTHING it looked at — and an abstention CAUSED by a
        # roster row that cannot name that row is a refusal with no
        # provenance, which is exactly what the circularity filter and every
        # later reader need. `abstained` is `value is None and not
        # candidates`, so this is an abstention by the same definition.
        return Ruling(value=None, reason="vetoed_by_the_work_roster",
                      used=used,
                      detail={"reader_text": text,
                              "lexicon_said": decided.before,
                              "why": decided.reason})
    if decided.match is None:
        # ⚠️ NOT a fallback to position. A label we cannot spell is a
        # different state from a staff with no label, and guessing here would
        # destroy the distinction the row was kept for.
        return Ruling.abstain("not_in_lexicon", text=text)

    match = decided.match
    inst = match.instrument
    return Ruling(
        value={"name": inst.name, "family": inst.family,
               "expected_clef": inst.default_clef,
               "written_range": list(inst.written_range),
               "unpitched": inst.unpitched},
        # ⚠️ THE REASON IS THE PROVENANCE AND THE VOCABULARY ALREADY HELD THE
        # WORD. `roster` was a declared reason of this decision from the day
        # it was written, and nothing could ever return it — the tier was
        # reserved and never wired, which is the same fault one layer up from
        # the parameter with no producer.
        reason="roster" if decided.kind != "unchanged" else "label",
        used=used,
        detail={"alias": match.alias, "coverage": match.coverage,
                "reader_text": text, "roster_decision": decided.kind,
                "roster_reason": decided.reason or None,
                "lexicon_said": decided.before or None})


def _work_roster(value):
    """The `WorkRoster` a `Q.ROSTER_ENTRY` row stands for, or None.

    ⚠️ The row carries a plain dict so the RECORD is readable (`gather_
    external` says why); the rule that consumes it wants the dataclass. The
    reconstruction is here rather than in GATHER because GATHER decides
    nothing — and it REFUSES a row whose `source_kind` is not `catalog`, a
    second time, at the point of use.

    ⚠️⚠️ THE SECOND REFUSAL IS NOT BELT-AND-BRACES. `work_roster()` enforces
    the tier when it BUILDS a roster from the catalog; nothing enforces it on
    a row that arrived some other way, and the `editions` tier is
    `source_kind: "page"` — an OMR output of the same raster. A witness read
    off the ink it is arbitrating falls silent exactly when it is needed,
    which is this file's own recorded hazard. The check is cheap; the failure
    is silent.
    """
    from ... import work_roster as WR
    if isinstance(value, WR.WorkRoster):
        return value if value.source_kind == "catalog" else None
    if not isinstance(value, dict):
        return None
    if value.get("source_kind") != "catalog":
        return None
    return WR.WorkRoster(
        work_id=str(value.get("work_id") or ""),
        instruments=frozenset(value.get("instruments") or ()),
        families=frozenset(value.get("families") or ()),
        complete=bool(value.get("complete")),
        source_kind="catalog")


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
    staves of one system land in one part.

    ⚠️⚠️ AND THIS DOCSTRING CLAIMED THAT CASE IS COMMON -- *"exactly the one an
    orchestral page prints (two horn staves), so this is the common case and
    not a corner"* -- WHICH A MEASUREMENT REFUTED. Over 7 systems and 75 staves
    of Beethoven 5 / Litolff, condition (b) fires **0 times** and the
    `cands != 1` branch fires **0 times**; deleting the latter outright changes
    the measured result by nothing. The reason is structural rather than luck:
    the only name repeated in that reference is `Violin`, and no short system
    ever reads a violin label, because the strings are the family this edition
    stops labelling on continuation systems -- so the guard is dormant BY THE
    SAME MECHANISM that makes 25 staves abstain. Both conditions are still
    right and are pinned by tests that go red without them; what is corrected
    is the claim that real pages exercise them.
    `benchmarks/omr-slot-index-2026-09/FINDINGS.md` §3a.

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
    composed_from=(Q.INSTRUMENT, Q.STAFF_ORDINAL, Q.SYSTEM_STAFF_COUNT,
                   Q.STAFF_GROUP, Q.CLEF_GLYPH, Q.CLEF_LOCATED),
    scope=Kind.STAFF,
    wants=(Q.INSTRUMENT, Q.STAFF_ORDINAL, Q.SYSTEM_STAFF_COUNT,
           Q.STAFF_GROUP, Q.CLEF_GLYPH, Q.CLEF_LOCATED),
    reasons=("full_lineup", "named", "paired_by_name", "no_reference",
             "no_ordinal", "reference_names_nothing", "unnamed_in_short_system",
             "not_in_reference", "ambiguous_pairing",
             "family_block", "family_block_not_forced",
             "forced_by_constraints"),
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
    pairing = _forced_pairing(mine, ref_names)
    if here >= len(mine) or mine[here] is None:
        # ⚠️⚠️ THE BLANKET ABSTENTION HERE WAS A BRAKE WHOSE PREMISE EXPIRED.
        # It read as *"a staff with no name cannot be placed"*, and it was
        # written when the only options were ANSWER or DISCARD -- so refusing
        # was the only honest thing to do with a staff the reference could
        # not be pinned to. The record now holds a PARTIAL answer
        # (`Ruling.narrow`) and a fourth stage exists for best-rather-than-
        # forced, so the question is no longer *"name it or not"* but *"how
        # much does the page force"*. See `_place_in_family_block`.
        placed = _place_in_family_block(
            ev, here, mine, pairing, ref_system, ref_names,
            n_staves=int(count.value), used=(ordinal.id, count.id))
        if slot_constraints_enabled():
            narrowed = _apply_constraints(
                ev, placed, here, mine, ref_system, ref_names,
                n_staves=int(count.value), used=(ordinal.id, count.id))
            if narrowed is not None:
                return narrowed
        if placed is not None:
            return placed
        return Ruling.abstain("unnamed_in_short_system",
                              reference=ref_system.to_key())

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


# ─────────────────────────────────────────────────────────────────────────────
# The unnamed block at the foot of a system
# ─────────────────────────────────────────────────────────────────────────────

#: How many reference slots the block may fall short of and still be placed at
#: all.
#:
#: ⚠️⚠️ THIS IS NOT SEAN'S "4 OR 5" AS A CONSTANT -- IT IS THE STRUCTURE THAT
#: PRODUCES IT. Sean's rule is *"4 or 5 staves that showed up last in the
#: system without a name in the margin are almost surely strings"*, and on a
#: document whose reference string run is FIVE slots long a deficit of at most
#: one admits exactly a block of four or five. Written as a deficit it carries
#: to a plate whose string run is a different length, and it says WHY the
#: window is where it is: at a deficit of one the block is short by a single
#: slot, which on an orchestral page is the condensed `Violoncello e Basso`.
#: At two or more, front-aligning is a guess about WHICH slots went missing
#: and the rule refuses rather than picking.
#:
#: ⚠️ A block of 1-2 staves is refused by this same number rather than by a
#: separate floor, which matters because that case is UNMEASURED -- this plate
#: never prints one.
FAMILY_BLOCK_MAX_DEFICIT = 1


def _reference_instruments(ev: Evidence, ref_system) -> List[Optional[dict]]:
    """`[the instrument verdict's value or None, by staff ordinal]`.

    ⚠️ THE FAMILY IS READ OFF THE VERDICT, NEVER RE-DERIVED FROM THE NAME.
    `adjudicate_instrument` already puts `family` on the value it returns, so
    asking `instruments.lookup` again here would be a second resolution of a
    question this pipeline has already answered -- two copies of one rule,
    free to drift, which is the fault `work_roster.decide` is imported rather
    than restated to avoid.
    """
    out: List[Optional[dict]] = []
    for v in ev.verdicts(Q.INSTRUMENT, scope=Scope.SELF_AND_DESCENDANTS,
                         subject=ref_system):
        sub = v.subject
        if sub.kind is not Kind.STAFF or not isinstance(v.value, dict):
            continue
        while len(out) <= sub.staff:
            out.append(None)
        out[sub.staff] = dict(v.value)
    return out


def _trailing_family_run(families: List[Optional[str]]) -> Tuple[Optional[int],
                                                                Optional[str]]:
    """`(first index, family)` of the reference's TRAILING same-family run.

    ⚠️⚠️ THIS IS WHERE "THE STRINGS" COMES FROM, AND IT IS NOT A WORD LIST.
    The probe that measured this rule found the string slots with a tuple of
    spellings (`Violino`, `Viola`, ...), which is the hand-list antipattern
    and would also have been WRONG here: the lexicon reads a printed `Basso.`
    as a BASS VOICE, so a family test over the printed strings drops the
    bottom slot and the whole block slides. What the reference actually says
    is that its last five slots are `string`, `string`, `string`, `string`,
    `string` -- a run this walks off the end of the lineup, naming no
    instrument and no publisher.
    #
    ⚠️ IT CLAIMS NOTHING ABOUT WHICH FAMILY. On an orchestral score the
    trailing run is the strings because that is where an engraver puts them;
    on a wind band it would be something else and the rule would still be
    asking the same question -- *what is the block of like instruments at the
    bottom of this lineup* -- rather than looking for a word it knows.
    """
    i = len(families)
    fam = None
    while i > 0 and families[i - 1] is not None and \
            (fam is None or families[i - 1] == fam):
        fam = families[i - 1]
        i -= 1
    if fam is None or i >= len(families):
        return None, None
    return i, fam


def _place_in_family_block(ev: Evidence, here: int,
                           mine: List[Optional[str]],
                           pairing: List[Optional[int]],
                           ref_system, ref_names: List[Optional[str]],
                           n_staves: int,
                           used: Tuple[str, ...]) -> Optional[Ruling]:
    """Place an unnamed staff by the BLOCK it stands in, or return None.

    Sean, 2026-09-17, on a plate whose strings are labelled on the opening
    system and nowhere else: *"If we had 4 or 5 staves that showed up last in
    the system without a name in the margin they are almost surely strings."*
    That is a claim about a SUFFIX, and the suffix is what makes it safe: the
    rule never looks above the block, so whatever is wrong up there -- a
    tacet trumpet, an unread horn -- cannot move it.

    **What this returns, and the difference is the whole point.**

    * a DECIDED slot, where the block exactly fills the reference's trailing
      family run and position is therefore FORCED by counting alone. Nothing
      is being guessed: there is one order-preserving map and this is it;
    * a NARROWED verdict naming every slot the staff could still be, where
      the block is SHORT of the run. That is *"it is one of these"*, and
      until `Ruling.narrow` existed it had nowhere to live -- which is why
      this decision abstained on all 25 of them;
    * `None`, where the block is not a suffix, or is longer than the run, or
      falls short by more than `FAMILY_BLOCK_MAX_DEFICIT`. The caller
      abstains exactly as it did before.

    ⚠️⚠️ THE CONVENTION THAT CHOOSES AMONG A NARROWING IS NOT HERE, AND MUST
    NOT COME HERE. Front-aligning a short block -- *"the missing slot is the
    condensed pair at the BOTTOM"* -- is true of every system of this
    document and is a claim about ENGRAVING PRACTICE, not about anything the
    page forces. It is BEST rather than FORCED, so it belongs in INFER, where
    it is labelled and where the clef may argue with it. See
    `inferences.collapse_slot_index_to_family_block`.

    ⚠️ NO CLEF IS READ HERE, and that is what dissolves the circularity this
    rule has been blocked on. `adjudicate_clef` weights the instrument at 1.0
    in the other direction and is ORDER 9 against this decision's 6, so
    reading `Q.CLEF` would close a cycle and read `None` besides. The raw
    `Q.CLEF_GLYPH` observation is not the verdict and carries no such
    dependency -- and even that is left to INFER, so that ADJUDICATE's answer
    here rests on POSITION and nothing else.

    ⚠️ THE RUN IS TRIMMED BY WHAT THE NAMED STAVES ALREADY TOOK. A system
    that labels its Violino I puts a named staff inside the trailing run, and
    the block below it is then not the whole section. Slots at or below the
    highest FORCED named pairing are removed before anything is counted.
    """
    # ⚠️⚠️ `mine` STOPS AT THE LAST NAMED STAFF, AND THE FIRST VERSION OF
    # THIS RULE REACHED NOTHING BECAUSE OF IT. `_names_by_system` grows its
    # row only when it has a name to put in one, so a system of eleven staves
    # whose last four are unnamed hands back a list of SEVEN -- and a list
    # that ends early is indistinguishable from a system that ends early.
    # That is the ABSENT/DECLINED collapse `record.py` exists to prevent,
    # happening in a local variable: the unnamed suffix this rule is entirely
    # about is exactly the part the structure cannot represent. The system's
    # own staff count is the only thing that says how long the row really is.
    n = int(n_staves)
    mine = list(mine[:n]) + [None] * max(0, n - len(mine))
    if here >= n or mine[here] is not None:
        return None

    # The block: the trailing run of staves this system did not name.
    b0 = n
    while b0 > 0 and mine[b0 - 1] is None:
        b0 -= 1
    if here < b0:
        # ⚠️ AN INTERIOR UNNAMED STAFF IS A DIFFERENT QUESTION AND GETS NO
        # ANSWER HERE. The claim is about a block at the FOOT of the system;
        # a staff with names both above and below it is bounded on both
        # sides and wants the name pairing, which already refused it.
        return None

    ref_instruments = _reference_instruments(ev, ref_system)
    families = [(d or {}).get("family") for d in ref_instruments]
    start, family = _trailing_family_run(families)
    if start is None:
        return None

    # ⚠️ Slots the named staves above have already been FORCED onto are not
    # available to the block. `pairing` is `_forced_pairing`'s answer, so an
    # unforced name removes nothing -- which is the conservative direction:
    # it leaves the run wider and the answer less forced, never more.
    taken = [p for p in pairing[:b0] if p is not None]
    floor = max(taken) if taken else -1
    run = [s for s in range(start, len(ref_names)) if s > floor]

    k = n - b0
    if not run or k > len(run):
        return None
    deficit = len(run) - k
    if deficit > FAMILY_BLOCK_MAX_DEFICIT:
        return None

    i = here - b0
    def _expected_clef(slot):
        d = ref_instruments[slot] if slot < len(ref_instruments) else None
        return (d or {}).get("expected_clef")

    shared = {"block_size": k, "block_first_ordinal": b0, "block_index": i,
              "deficit": deficit, "family": family,
              "run": list(run), "front_aligned": run[i],
              # ⚠️ CARRIED HERE SO THAT INFER NEED NOT RE-READ THE REFERENCE.
              # The clef a slot's instrument is WRITTEN IN is a fact about
              # that instrument (`Instrument.default_clef`) and is already on
              # the verdict this function is reading; a rule that went back
              # for it would be a second traversal free to disagree with this
              # one about which system the reference is.
              "run_clefs": [_expected_clef(s) for s in run],
              "reference": ref_system.to_key(),
              "instrument": ref_names[run[i]] if run[i] < len(ref_names) else None}

    if deficit == 0:
        return Ruling(value=int(run[i]), reason="family_block",
                      used=used, detail=shared)

    # ⚠️⚠️ EVERY CANDIDATE CARRIES THE SAME SUPPORT, DELIBERATELY. The reader
    # genuinely cannot choose between them -- `Candidate.support`'s own
    # docstring says *"the ORDER is the claim"*, so ordering these would be
    # this decision asserting the very convention it is handing on. An equal
    # support is the honest statement that position alone has run out.
    cands = [Candidate(value=int(run[i + j]), support=1.0)
             for j in range(deficit + 1)]
    return Ruling.narrow(cands, "family_block_not_forced",
                         used=used, **shared)

# ─────────────────────────────────────────────────────────────────────────────
# The three channels, as CONSTRAINTS on the order-preserving map
#
# Sean, 2026-09-22: *"margin names, instrumentation lists from the doc or a
# dossier, Order, family brackets should all come first in determining what the
# instrument is"* -- and the clef only where we are sure of it, because *"the
# clef is a small part of deciding what the instrument is and we would need to
# be sure of the clef to have it impact the instrument."*
#
# REACH, measured before this was written
# (`benchmarks/omr-instrument-channels-2026-09/FINDINGS.md`), on the staves
# whose instrument ABSTAINED, with ZERO GRAFTS in every arm on both documents:
#
#   channel added            Litolff /25      Breitkopf /40
#   order alone                   0                38
#   + family block                5                38
#   + clef                       18                38
#
# ⚠️⚠️ ORDER ALONE FORCES NOTHING ON THE DOCUMENT THAT NEEDS IT, and the
# reason is structural: Litolff's unnamed staves are a TRAILING block, so no
# named neighbour stands below them and the whole block slides. Breitkopf
# INVERTS it -- 38 of 40 from order alone, because its unnamed staves are
# interleaved among named ones and bounded on both sides. Neither document
# could have shown that on its own.
# ─────────────────────────────────────────────────────────────────────────────

#: Which clefs a slot's part may be PRINTED in, where that is not the one the
#: lexicon calls default.
#:
#: ⚠️⚠️ THIS IS MEASURED, NOT ASSUMED, AND IT IS WHAT MAKES THE CLEF CHANNEL
#: SURVIVE A SECOND PUBLISHER. `probe_clef_stability.py` asks both shared
#: records whether a slot's clef is a constant of that slot, over staves the
#: shipped reader had already placed: Litolff 37 agree / 1 disagree, Breitkopf
#: 70 / 4 -- and EVERY disagreement is a Cello or a Bassoon. Breitkopf's
#: reference system reads its cello slot `tenor` while three later systems read
#: the same slot `bass`, ALL FOUR AT MARGIN 4.5, i.e. four confident readings
#: of a part that genuinely changes clef.
#:
#: ⚠️ So the obvious rule -- *a staff may take a slot whose own staff on the
#: REFERENCE system read the same clef* -- is REFUTED: it makes 5 of
#: Breitkopf's 6 systems unsatisfiable and the clef channel is discarded on
#: every one of them. Taking each slot's admissible clefs from the INSTRUMENT
#: instead reaches the same 18 on Litolff and is refused on no system of
#: either document.
ALTERNATING_CLEFS: Dict[str, Tuple[str, ...]] = {
    "Cello": ("bass", "tenor"),
    "Bassoon": ("bass", "tenor"),
    "Contrabassoon": ("bass", "tenor"),
    "Trombone": ("bass", "tenor"),
}

#: A system this ambiguous is a "cannot tell", not a slow one.
_MAX_ASSIGNMENTS = 200000


def slot_constraints_enabled() -> bool:
    """⚠️ A DENY-LIST, because the default is ON. An allow-list would let an
    empty value or a typo silently restore the previous behaviour, which is
    the hazard `test_flag_default_direction.py` exists for."""
    import os
    return os.environ.get("OMR_SLOT_CONSTRAINTS", "1").strip().lower() \
        not in ("0", "", "false", "no", "off")


def _admissible_clefs(instrument: Optional[dict]) -> Optional[Tuple[str, ...]]:
    """Every clef this slot's part may be printed in, or None for no opinion."""
    if not isinstance(instrument, dict):
        return None
    name = instrument.get("name")
    alt = ALTERNATING_CLEFS.get(str(name)) if name else None
    if alt is not None:
        return alt
    expected = instrument.get("expected_clef")
    return (str(expected),) if expected else None


def _clef_read_at(ev: Evidence, subject) -> Optional[str]:
    """This staff's clef as GATHER saw it, or None -- CONSERVATIVELY.

    ⚠️⚠️ IT MAY NOT READ `Q.CLEF`, AND THE DOCSTRING OF THIS FILE USED TO SAY
    IT SHOULD. `Q.CLEF` is a VERDICT at `ORDER` 9 while this decision runs at
    6, so reading it returns None and would close a cycle besides
    (`adjudicate_clef` weighs `Q.INSTRUMENT`, which this decision's own input
    is). The reachable objects are the GATHER facts, available at every ORDER
    and carrying no deduced identity: a glyph is a reading of ink.

    ⚠️ THE LOCATOR IS ASKED FIRST because it is the only reader that names
    WHICH C clef -- `_GLYPH_TO_CLEF` maps no C clef at all, on purpose, since
    a C clef is one glyph on five different lines and the CLASS can never say
    which. Measured on Litolff: the detector fires on ZERO C clefs across the
    whole record (74 `clefG`, 17 `clefF`, 0 `clefC`) and the CV locator names
    4 of the 7 printed violas.

    ⚠️ DISAGREEMENT IS NO OPINION, NEVER A VOTE. A measure cell is the staff
    plus four staff spaces of air, so a neighbour's clef lands in it and
    `gather_clef` emits EVERY candidate -- 101 glyph rows over 75 staves on
    one record. Picking between them is `adjudicate_clef`'s job, with its own
    weights and its own right to abstain; a second, cheaper copy of that
    contest here is exactly the drift this file imports `work_roster.decide`
    to avoid. So: all the rows agree, or this says nothing.
    """
    from .clef import _GLYPH_TO_CLEF

    located = {str(r.value) for r in ev.rows(Q.CLEF_LOCATED, subject=subject)
               if r.value}
    if len(located) == 1:
        return located.pop()
    if located:
        return None

    named = set()
    for row in ev.rows(Q.CLEF_GLYPH, subject=subject):
        clef = _GLYPH_TO_CLEF.get(str(row.value))
        if clef is None:
            # a C-clef class names a FAMILY and not a clef; it cannot speak
            # here and must not be counted as a disagreement either.
            continue
        named.add(clef)
    return named.pop() if len(named) == 1 else None


def _block_map(system_blocks: List[Optional[int]],
               reference_blocks: List[Optional[int]]) -> Optional[Dict[int, int]]:
    """`{this system's family block -> the reference's}`, or None.

    ⚠️ ORDER-PRESERVING AND EQUAL-COUNT ONLY. A system printing FEWER family
    blocks than the reference has had a whole section go tacet, and WHICH
    section is precisely what this would then be guessing. It returns None and
    the caller drops the channel rather than aligning anyway.
    """
    a, b = _block_runs(system_blocks), _block_runs(reference_blocks)
    if not a or not b or len(a) != len(b):
        return None
    return dict(zip(a, b))


def _block_runs(seq: Sequence[Optional[int]]) -> List[int]:
    out: List[int] = []
    for x in seq:
        if x is None:
            return []
        if not out or out[-1] != x:
            out.append(x)
    return out


def _admissible(staff_index: int, names: List[Optional[str]],
                blocks: List[Optional[int]], clefs: List[Optional[str]],
                ref_names: List[Optional[str]],
                ref_blocks: List[Optional[int]],
                ref_clefs: List[Optional[Tuple[str, ...]]],
                block_map: Optional[Dict[int, int]],
                use_clef: bool, use_block: bool) -> Optional[Set[int]]:
    """The slots this staff may take, or None where no channel has an opinion.

    ⚠️⚠️ A REFERENCE SLOT THE DOCUMENT COULD NOT READ MUST WIDEN THE CANDIDATE
    SET, NEVER EMPTY IT, and the probe that measured this got it wrong first
    and was caught by its own no-solution counter. Breitkopf's reference lineup
    has THREE slots whose margin the reader could not resolve -- one of them
    the horn staff whose label truncates to `'(C)'` -- and requiring a named
    staff to match a slot NAME made every system holding them unsatisfiable.
    `None` on the reference side means *we do not know what this slot is*, and
    it excludes nobody.
    """
    sets: List[Set[int]] = []
    mine = names[staff_index] if staff_index < len(names) else None
    if mine is not None:
        sets.append({i for i, nm in enumerate(ref_names)
                     if nm is None or nm == mine})
    if use_block and block_map is not None:
        block = blocks[staff_index] if staff_index < len(blocks) else None
        if block is not None and block in block_map:
            want = block_map[block]
            sets.append({i for i, b in enumerate(ref_blocks)
                         if b is None or b == want})
    # ⚠️⚠️ THE CLEF SPEAKS ABOUT UNNAMED STAVES ONLY, AND THAT IS MEASURED
    # RATHER THAN TIDY. A named staff is already pinned by its name, so a clef
    # constraint on it can add nothing -- and it can subtract everything: on
    # Litolff p2/s1 the Fagotti's FALSE `tenor` (the CV locator firing
    # unopposed on one crop, which `adjudicate_clef` then decides at a margin
    # of exactly its floor) names a clef NO reference slot admits, the system
    # goes unsatisfiable and the whole channel is dropped for it. FOUR forced
    # staves, lost to one wrong reading on a staff the clef was never needed
    # for.
    if use_clef and mine is None:
        clef = clefs[staff_index] if staff_index < len(clefs) else None
        if clef is not None:
            sets.append({i for i, adm in enumerate(ref_clefs)
                         if adm is None or clef in adm})
    if not sets:
        return None
    out: Set[int] = set(range(len(ref_names)))
    for one in sets:
        out &= one
    return out


def _assignments(n_staves: int, allowed: Dict[int, Optional[Set[int]]],
                 n_slots: int) -> List[Tuple[int, ...]]:
    """Every STRICTLY INCREASING staff->slot map the channels still permit.

    ⚠️ The strictness is `[C62]` and nothing else: *a printed score may OMIT a
    tacet part; it may never REORDER one.*
    """
    out: List[Tuple[int, ...]] = []

    def walk(ordinal: int, lo: int, acc: List[int]) -> None:
        if len(out) > _MAX_ASSIGNMENTS:
            return
        if ordinal == n_staves:
            out.append(tuple(acc))
            return
        hi = n_slots - (n_staves - ordinal)
        for slot in range(lo, hi + 1):
            ok = allowed.get(ordinal)
            if ok is not None and slot not in ok:
                continue
            acc.append(slot)
            walk(ordinal + 1, slot + 1, acc)
            acc.pop()

    walk(0, 0, [])
    return out


def _solve(n_staves: int, names, blocks, clefs, ref_names, ref_blocks,
           ref_clefs, block_map) -> Tuple[List[Tuple[int, ...]], List[str]]:
    """`(assignments, channels dropped)`.

    ⚠️⚠️ A CHANNEL MAY NARROW OR ABSTAIN; IT MAY NEVER EMPTY THE SOLUTION SET.
    Where one makes a system unsatisfiable it is DROPPED for that system and
    the fact is recorded, because a constraint that deletes the right answer is
    worse than one that never spoke. That is Sean's *evidence contributes, it
    never gates* made mechanical, and the WEAKEST channel goes first -- his
    ordering, with the clef last.
    """
    dropped: List[str] = []
    use_clef, use_block = True, True
    while True:
        allowed = {i: _admissible(i, names, blocks, clefs, ref_names,
                                  ref_blocks, ref_clefs, block_map,
                                  use_clef, use_block)
                   for i in range(n_staves)}
        sols = _assignments(n_staves, allowed, len(ref_names))
        if sols:
            return sols, dropped
        if use_clef:
            use_clef = False
            dropped.append("clef")
            continue
        if use_block:
            use_block = False
            dropped.append("family_block")
            continue
        return [], dropped


def _constrained_slots(ev: Evidence, here: int,
                       mine: List[Optional[str]], ref_system,
                       ref_names: List[Optional[str]],
                       ref_instruments: List[Optional[dict]],
                       n_staves: int,
                       clefs: List[Optional[str]]) -> Tuple[Optional[Set[int]],
                                                            List[str]]:
    """`(the slots every surviving assignment allows this staff, dropped)`.

    A SET, not a Ruling, and the difference is what keeps the shipped path
    intact: the caller FILTERS `_place_in_family_block`'s narrowing with this
    rather than replacing it, so the block keeps its shape, its reason and its
    detail and `inferences.collapse_slot_index_to_family_block` still sees the
    members it reasons about.

    ⚠️⚠️ THE FIRST CUT RETURNED A RULING AND DECIDED DIRECTLY, AND THE ARM
    CAUGHT WHAT THAT COST. Deciding two members of a block REMOVED them from
    `_block_members`, which requires the narrowings to cover `0..k-1`; the
    block then had holes, INFER skipped it whole, and TWO Violas that the
    shipped path places correctly came out narrowed instead. A branch that is
    additive in its own terms can still subtract through a rule downstream of
    it, and only a per-staff base-vs-arm control shows it.

    ⚠️ IT NAMES NOTHING. The value is a SLOT; whether that slot has a name is
    the reference system's business, and on Breitkopf 10 of 38 placed staves
    land on slots the reader itself could not name. Placement reach and naming
    reach are different numbers and this is the first.
    """
    system = ev.subject.at(Kind.SYSTEM)

    # ⚠️ `mine` STOPS AT THE LAST NAMED STAFF -- `_names_by_system` grows its
    # row only when it has a name to put in one, so a system whose last four
    # staves are unnamed hands back a short list and the unnamed SUFFIX this
    # rule is about is exactly the part the structure cannot represent. The
    # system's own staff count is the only thing that says how long it is.
    names = list(mine[:n_staves]) + [None] * max(0, n_staves - len(mine))

    blocks: List[Optional[int]] = [None] * n_staves
    for v in ev.verdicts(Q.STAFF_GROUP, scope=Scope.SELF_AND_DESCENDANTS,
                         subject=system):
        if v.subject.kind is Kind.STAFF and v.value is not None \
                and v.subject.staff < n_staves:
            blocks[v.subject.staff] = int(v.value)

    ref_blocks: List[Optional[int]] = [None] * len(ref_names)
    for v in ev.verdicts(Q.STAFF_GROUP, scope=Scope.SELF_AND_DESCENDANTS,
                         subject=ref_system):
        if v.subject.kind is Kind.STAFF and v.value is not None \
                and v.subject.staff < len(ref_names):
            ref_blocks[v.subject.staff] = int(v.value)

    ref_clefs = [_admissible_clefs(d) for d in ref_instruments]
    while len(ref_clefs) < len(ref_names):
        ref_clefs.append(None)

    block_map = _block_map(blocks, ref_blocks)
    sols, dropped = _solve(n_staves, names, blocks, clefs, ref_names,
                           ref_blocks, ref_clefs, block_map)
    if not sols or here >= n_staves:
        return None, dropped
    return {sol[here] for sol in sols}, dropped


def _apply_constraints(ev: Evidence, placed: Optional[Ruling], here: int,
                       mine: List[Optional[str]], ref_system,
                       ref_names: List[Optional[str]], n_staves: int,
                       used: Tuple[str, ...]) -> Optional[Ruling]:
    """`placed`, narrowed by the three channels -- or None to keep `placed`.

    Three outcomes, and each is strictly stronger than what it replaces:

    * a DECISION, where exactly one slot survives. It carries `placed`'s own
      block detail unchanged, so the block is still reconstructible by
      `inferences._block_members`, plus which channels spoke;
    * a SMALLER NARROWING, with `placed`'s reason and detail kept verbatim so
      the INFER rule that reads them behaves exactly as before;
    * None -- nothing survived that was not already there.

    ⚠️ IT MAY ONLY REMOVE CANDIDATES `placed` ALREADY ADMITTED. Where the
    constraints and the family block disagree outright -- every surviving slot
    excluded by the other -- this returns None and the shipped answer stands,
    because a branch that can overturn the rule it filters is not a filter.
    """
    # ⚠️ THE CLEF IS COLLECTED HERE, ONE LEVEL UP FROM THE SOLVER, AND THE
    # REASON IS A DERIVED CHECK RATHER THAN TASTE. `inventory --check` follows
    # a decision's own helpers THREE deep to decide whether a `wants` entry is
    # actually read; with the read a fourth helper down it reported
    # `slot_index declares 'clef_glyph' ... and never reads it`, which is a
    # measure of code STYLE and not of inertness -- the exact confusion that
    # check's own docstring records repairing once already. Collected where it
    # is visible, and the solver stays a pure function of what it is handed.
    clefs: List[Optional[str]] = [None] * n_staves
    system = ev.subject.at(Kind.SYSTEM)
    names = list(mine[:n_staves]) + [None] * max(0, n_staves - len(mine))
    for v in ev.verdicts(Q.INSTRUMENT, scope=Scope.SELF_AND_DESCENDANTS,
                         subject=system):
        sub = v.subject
        if sub.kind is not Kind.STAFF or sub.staff >= n_staves:
            continue
        # ⚠️ UNNAMED STAVES ONLY, and this is the site the mutation battery
        # reaches. A named staff is already pinned by its name, so its clef
        # can add nothing and can subtract everything.
        if names[sub.staff] is None:
            clefs[sub.staff] = _clef_read_at(ev, sub)

    surviving, dropped = _constrained_slots(
        ev, here, mine, ref_system, ref_names,
        _reference_instruments(ev, ref_system), n_staves, clefs)
    if surviving is None:
        return None
    spoke = [c for c in ("order", "family_block", "clef") if c not in dropped]
    shared = {"channels": spoke, "channels_dropped": dropped}

    if placed is None:
        if len(surviving) != 1:
            return None
        slot = int(next(iter(surviving)))
        return Ruling(value=slot, reason="forced_by_constraints", used=used,
                      detail=dict(shared, reference=ref_system.to_key(),
                                  instrument=(ref_names[slot]
                                              if slot < len(ref_names) else None),
                                  note="no family block; the slot every "
                                       "order-preserving assignment agrees on"))
    if placed.value is not None or not placed.candidates:
        # already decided, or an abstention with nothing to filter
        return None

    kept = [c for c in placed.candidates if int(c.value) in surviving]
    if not kept or len(kept) == len(placed.candidates):
        return None
    if len(kept) == 1:
        slot = int(kept[0].value)
        return Ruling(value=slot, reason="forced_by_constraints", used=used,
                      detail=dict(placed.detail, **shared,
                                  narrowed_from=[int(c.value)
                                                 for c in placed.candidates],
                                  instrument=(ref_names[slot]
                                              if slot < len(ref_names) else None)))
    return Ruling.narrow(kept, placed.reason, used=placed.used,
                         **dict(placed.detail, **shared,
                                narrowed_from=[int(c.value)
                                               for c in placed.candidates]))


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


#: The two join shapes `adjudicate_part_partition` can return. A part key is
#: whatever the chosen join says a `<part>` IS, so the check has to be asked
#: in the join's own terms or it measures a different partition than the one
#: that ships.
_JOIN_ORDINAL = "ordinal"
_JOIN_SLOT = "slot"


def _instrument_consistency(ev: Evidence, join: str) -> Dict:
    """PERFORM `part_partition`'s second declared check, and RECORD it.

    The decorator has declared *"each part carries ONE instrument across every
    system it appears on"* since the decision was written, and until
    2026-09-20 **the body read `Q.INSTRUMENT` on no path at all** -- found by
    `benchmarks/omr-convention-coverage-2026-09/`, which counted 16 of 32
    declared checks not performed. This is one of them, and the damage the
    check describes is already on this project's record: the Phase 2 part-join
    measurement (`benchmarks/omr-part-join-phase2-2026-09/`) found **12 of 75
    staff-systems filed under a part carrying a different instrument**,
    including a Timpani part holding the Viola's staff and its seven sharps.

    ⚠️⚠️ IT RECORDS AND IT DOES NOT ACT, DELIBERATELY. The wiring plan's one
    condition is that *a wiring pass may CONNECT a decision, it may not let one
    GUESS* -- and every way of acting on this result is a guess today. Failing
    the join over a contradiction would hand the document to the fragment
    fallback on the evidence of one misread margin label; repairing the join
    would need to know WHICH staff is misfiled, which this cannot say. What it
    can say is that the join it just chose is contradicted, and say it in the
    verdict, where the next reader and the next measurement can both see it.

    ⚠️ THE FRAME. `Q.INSTRUMENT` is filed on STAVES and this decision runs at
    DOCUMENT, so a bare `ev.verdicts(Q.INSTRUMENT)` returns nothing and the
    check would report a clean zero on every page -- the `wiring.py`
    SCOPE-LATENT entry for this exact declaration says so in terms, and it is
    why the read is `Scope.SELF_AND_DESCENDANTS`.

    ⚠️ ABSENT IS NOT CLEAN. A page where no instrument was read yields
    `checked: False`, never `contested: 0`. The distinction is this record's
    own reason for existing, and here it is load-bearing twice over: before
    `run_staged` forwarded `pdf_path`, `adjudicate_instrument` abstained
    `no_evidence` on 75 of 75 staves on every staged run this repo had ever
    made, so a check that read that silence as agreement would have reported
    the part join sound on precisely the documents where it was worst.

    ⚠️ `used` is NOT extended with these ids and that is not an oversight: the
    join was not decided from them. They arrive in `considered` because
    `ev.verdicts` records every hand-in, which is the honest place for the
    basis of a check that changed no value.
    """
    seen = ev.verdicts(Q.INSTRUMENT, scope=Scope.SELF_AND_DESCENDANTS)
    named: Dict[object, List[str]] = {}
    unkeyed = 0
    for v in seen:
        if v.value is None:
            continue
        name = v.value.get("name") if isinstance(v.value, dict) else v.value
        if name is None:
            continue
        if join == _JOIN_ORDINAL:
            key = v.subject.staff
        else:
            # The slot join files a staff under its SLOT, so the check must
            # ask the same table. A staff whose slot never decided belongs to
            # no part under this join and is counted apart rather than
            # dropped -- an unkeyed staff is a hole in the check's reach, not
            # a part that agrees with itself.
            slot = ev.verdict(Q.SLOT_INDEX, subject=v.subject)
            key = slot.value if slot is not None else None
        if key is None:
            unkeyed += 1
            continue
        named.setdefault(key, []).append(name)

    if not named:
        return {"checked": False,
                "why_not": "no_instrument_was_read",
                "staves_named": 0,
                "staves_unkeyed": unkeyed}

    contested = {k: sorted(set(v)) for k, v in named.items()
                 if len(set(v)) > 1}
    return {"checked": True,
            "join_checked": join,
            "staves_named": sum(len(v) for v in named.values()),
            "staves_unkeyed": unkeyed,
            "parts_named": len(named),
            # A part named on ONE system cannot disagree with itself, so it is
            # reported apart: it is the part of the population this check is
            # structurally unable to speak about.
            "parts_with_two_or_more_named_staves":
                sum(1 for v in named.values() if len(v) > 1),
            "parts_contested": len(contested),
            "contested": {str(k): v for k, v in sorted(contested.items(),
                                                       key=lambda kv: str(kv[0]))}}


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
        #
        # ⚠️ THE DECLARED INSTRUMENT CHECK IS PERFORMED HERE TOO, and this is
        # the branch where it can bite: "the systems all print the same NUMBER
        # of staves" is a constraint satisfiable by accident, as this
        # function's own docstring records for `beethoven-sym5-mvt1-984073-p4`
        # -- two 11-staff systems with DIFFERENT lineups. Counting agrees; the
        # instruments need not.
        return Ruling(value={"join": _JOIN_ORDINAL,
                             "staves_per_system": sizes.pop()},
                      reason="ordinal", used=tuple(v.id for v in counts),
                      detail={"instrument_consistency":
                              _instrument_consistency(ev, _JOIN_ORDINAL)})

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
        return Ruling(value={"join": _JOIN_ORDINAL,
                             "reason": "slots_are_ordinals"},
                      reason="deduced_anchor",
                      used=tuple(v.id for v in counts),
                      detail={"slots_are_ordinals": True,
                              "staves_per_system": sorted(sizes),
                              # Checked as an ORDINAL join, because that is
                              # what this branch has just decided the slot
                              # table amounts to. Asking it in slot terms
                              # would check a partition that does not ship.
                              "instrument_consistency":
                                  _instrument_consistency(ev, _JOIN_ORDINAL),
                              "note": "the slot table is the staff position, "
                                      "so joining on it is the ordinal join "
                                      "this branch refused"})
    if not usable:
        # Either no slot was decided, or every one that was is a deduced
        # identity the harness refused. Both land here; the verdict's
        # `excluded` list says which, and it says so without this function
        # asking.
        return Ruling(value={"join": _JOIN_ORDINAL,
                             "reason": "slots_unusable"},
                      reason="deduced_anchor",
                      used=tuple(v.id for v in counts),
                      detail={"instrument_consistency":
                              _instrument_consistency(ev, _JOIN_ORDINAL)})

    return Ruling(value={"join": _JOIN_SLOT,
                         "slots": sorted({v.value for v in usable
                                          if isinstance(v.value, int)})},
                  reason="slot", used=tuple(v.id for v in usable),
                  detail={"instrument_consistency":
                          _instrument_consistency(ev, _JOIN_SLOT)})
