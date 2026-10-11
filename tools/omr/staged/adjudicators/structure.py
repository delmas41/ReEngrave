"""Structure — systems, families, bars, ordinals.

Everything here rests on MEASUREMENTS whose only ancestor is the raster, so
no provenance question can arise and the circularity filter has nothing to
do. That is exactly why the design put grouping first.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..adjudicate import Checkable, Evidence, Mode, Ruling, decision
from .. import geometry as _geom
from ..record import Kind, Outcome, Q, Scope, State, Subject

# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ ASSUMED CONSTANTS. None of these is measured. See ASSUMPTIONS.md.
# ─────────────────────────────────────────────────────────────────────────────

#: A brace means ONE PLAYER reading two staves. These are the families that
#: do that. (A-GROUP-2)
BRACE_FAMILIES = frozenset({"keyboard", "harp"})


@decision(
    quantity=Q.SYSTEM_MEMBERSHIP,
    checkable=Checkable.MIXED,
    checked_by=(
        "cross-staff measure count: every staff of a system prints the SAME number of bars",
        "a systemic barline crosses every staff of the system at one x",
    ),
    implicates=(Q.SYSTEM_MEMBERSHIP, Q.MEASURE_PARTITION, Q.BARLINE_COLUMN),
    composed_from=(Q.GAP_BRIDGING, Q.SYSTEMIC_COLUMN),
    scope=Kind.SYSTEM,
    wants=(Q.SYSTEM_STAFF_COUNT, Q.GAP_BRIDGING),
    reasons=("counted", "no_evidence"),
)
def adjudicate_system_membership(ev: Evidence) -> Ruling:
    """Which staves belong to this system.

    Today's rule (connectivity veto over gap distance) already runs in GATHER
    -- `assign_systems` decides it while measuring. This records the result
    so the rest of the pipeline addresses a decided fact rather than a field.
    """
    rows = ev.rows(Q.SYSTEM_STAFF_COUNT)
    if not rows:
        return Ruling.abstain("no_evidence")
    return Ruling(value=int(rows[-1].value), reason="counted",
                  used=tuple(r.id for r in rows))


@decision(
    quantity=Q.SYSTEM_STAFF_COUNT,
    checkable=Checkable.MIXED,
    checked_by=(
        "the count may not EXCEED the work roster -- a page cannot print an instrument the work has not got",
        "across systems of one page the count is equal, or a subset explained by tacet staves",
    ),
    implicates=(Q.SYSTEM_STAFF_COUNT, Q.SYSTEM_MEMBERSHIP, Q.STAFF_LINES),
    composed_from=(Q.STAFF_LINES,),
    scope=Kind.SYSTEM,
    wants=(Q.SYSTEM_STAFF_COUNT,),
    reasons=("counted", "no_evidence"),
)
def adjudicate_system_staff_count(ev: Evidence) -> Ruling:
    rows = ev.rows(Q.SYSTEM_STAFF_COUNT)
    if not rows:
        return Ruling.abstain("no_evidence")
    return Ruling(value=int(rows[-1].value), reason="counted",
                  used=tuple(r.id for r in rows))


@decision(
    quantity=Q.STAFF_ORDINAL,
    composed_from=(Q.STAFF_LINES,),
    scope=Kind.STAFF,
    wants=(Q.STAFF_ORDINAL,),
    reasons=("read", "no_evidence"),
)
def adjudicate_staff_ordinal(ev: Evidence) -> Ruling:
    rows = ev.rows(Q.STAFF_ORDINAL)
    if not rows:
        return Ruling.abstain("no_evidence")
    return Ruling(value=int(rows[-1].value), reason="read",
                  used=tuple(r.id for r in rows))


def _is_signature_glyph_class(name: object) -> bool:
    """True only for a clef / key-signature / time-signature detector class
    (the 208-class taxonomy, `tools/omr/training/deepscoresv2_208_classes.
    json`: `clefG/clefF/clefC*/clef8/clef15/clefUnpitchedPercussion`,
    `keyFlat/keySharp/keyNatural`, `timeSig0`-`timeSig9`/`timeSigCommon`/
    `timeSigCutCommon`) -- the ink a cautionary strip (CLAUDE.md section 10)
    is printed from and nothing else. `"keyboard"` is excluded on purpose:
    it is the one prefix collision with `"key"` in that class space
    (`keyboardPedalPed`/`keyboardPedalUp`, a pedal mark, never a cautionary
    strip) and a false hit there would let a real pedal glyph sneak through
    as if it were a key signature.
    """
    s = str(name)
    if s.startswith("keyboard"):
        return False
    return s.startswith(("clef", "key", "timeSig"))


def _trailing_cell_signature_vote(
    ev: Evidence, system_sub: Subject, last_cell_index: int,
) -> Tuple[int, int]:
    """Per-staff vote behind ROADMAP 2.47b's MAJORITY rule (DECISIONS
    2026-10-01, Sean: "if most of the bars confirm the time signature then
    it should run on all of the staves"): for every staff of the system
    whose own trailing cell carries at least one `Q.GLYPH_BOX` row, decide
    whether THAT staff's cell is signature-only -- a clef/key/time class, or
    a notehead-classed box that is the same ink as a `timeSig*` box the
    detector also drew there (`geometry.is_timesig_digit_ink`, ROADMAP
    2.47bc), with nothing else beside it.

    Returns `(n_signature_only, n_with_trailing_cell)`. A staff whose
    trailing cell has NO `Q.GLYPH_BOX` row at all (the detector found
    nothing there) is counted in NEITHER number: rule 8, "we found nothing"
    is not evidence either for or against the system-wide vote, so an
    all-empty system still returns `(0, 0)` and the caller must treat that
    as no evidence, not as a unanimous vote of zero over zero.
    """
    rows = ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                    subject=system_sub)
    in_cell = [r for r in rows
               if r.subject.cell == last_cell_index
               and isinstance(r.value, (list, tuple)) and r.value]
    by_staff: Dict[Optional[int], List] = {}
    for r in in_cell:
        by_staff.setdefault(r.subject.staff, []).append(r)
    n_total = len(by_staff)
    n_signature_only = 0
    for staff_rows in by_staff.values():
        # ROADMAP 2.86: `timeSig*` boxes ONLY, as the docstring above and
        # `geometry.is_timesig_digit_ink`'s own contract say. Until 2.86 this
        # list held every clef and key box too, so a notehead box lying on a
        # `keyFlat` was excused as "the same ink" -- a pairing 2.47c's own
        # rule (`notehead_precision`, its section comment) records as NOT
        # CONFIRMED, and no crop has shown.
        timesig_values = [r.value for r in staff_rows
                           if str(r.value[0]).startswith("timeSig")]
        staff_is_signature_only = True
        for r in staff_rows:
            if _is_signature_glyph_class(r.value[0]):
                continue
            if _geom.is_timesig_digit_ink(r.value, timesig_values):
                continue
            staff_is_signature_only = False
            break
        if staff_is_signature_only:
            n_signature_only += 1
    return n_signature_only, n_total


def _trailing_cell_is_cautionary_only(
    ev: Evidence, system_sub: Subject, last_cell_index: int,
) -> Tuple[bool, int, int]:
    """ROADMAP 2.47b (CLAUDE.md section 10): "a cautionary meter after a
    system's last barline governs no bar" -- generalised from the meter
    reading to the PARTITION itself. `measure_extractor._measure_x_
    boundaries` decides, on WIDTH alone, whether the strip after a system's
    own final barline becomes its own bar or is absorbed into the one
    before it (`benchmarks/omr-measure-partition-2026-09/FINDINGS.md` §0a,
    §3: a human reads that strip by what is PRINTED in it, which the width
    rule cannot see and this does, after the detector has run).

    MAJORITY, not unanimity (DECISIONS 2026-10-01, superseding 2.47b's
    original "every staff" shape: Brahms p0 system 0 still read 8 bars
    after the 2.47b+2.47c merge because 4 of its 14 staves have no
    `timeSig` box in the tail at all -- a detector MISS, not a real bar --
    and the old all-or-nothing rule let those 4 block the other 10. Sean:
    "if most of the bars confirm the time signature then it should run on
    all of the staves"): demotes for the WHOLE system when STRICTLY MORE
    THAN HALF of the staves that have a trailing cell (`_trailing_cell_
    signature_vote`'s denominator; an empty cell counts in neither the
    numerator nor the denominator, rule 8) read that cell as signature-
    only. CLAUDE.md section 10 still grounds this: a meter/key change is
    printed at one bar on EVERY staff of the system, so once most staves
    show it, the few that don't are the readable failure, not a real short
    bar -- exactly a MAJORITY-voted fact, not a unanimous one.

    Returns `(demoted, n_signature_only, n_with_trailing_cell)` so the
    caller can file the vote in the verdict's own detail rather than
    re-deriving it.

    An ALL-empty tail (no staff has any row in the cell at all,
    `n_with_trailing_cell == 0`) answers `False` -- "we found nothing" is
    not evidence either way (rule 8), so today's geometry-only count
    stands, unchanged, exactly as the brief's control requires.

    ROADMAP 2.47bc: a notehead-classed box in a staff's cell no longer
    blocks THAT STAFF's own signature-only vote by itself when it is the
    SAME ink as a `timeSig*` box the detector also drew there (`geometry.
    is_timesig_digit_ink`, the shared helper ROADMAP 2.47c's own refusal
    rule uses, so the two decisions agree on what "the same ink" means
    without this module importing that one -- see `geometry.py`'s section
    comment on why that import would cycle). The comparison is done PER
    STAFF: `Q.GLYPH_BOX` values are in each cell's own canonical frame, so a
    `timeSig*` box on one staff says nothing about a notehead box on
    another, even at the same cell INDEX.
    """
    n_signature_only, n_total = _trailing_cell_signature_vote(
        ev, system_sub, last_cell_index)
    if n_total == 0:
        return False, n_signature_only, n_total
    return (2 * n_signature_only > n_total), n_signature_only, n_total


#: ROADMAP 2.86. Accidental-SHAPED detector classes that can stand in a key
#: signature: the detector boxes a key's flats as `accidentalFlat` as often
#: as `keyFlat` on the Breitkopf plate (the same widening `gather.
#: _gather_keysig_markers` makes for the header, by SHAPE not by role). The
#: small and double forms are left out: a key signature is never printed
#: with either ([C21]).
_KEY_SHAPE = {
    "keyFlat": "flat", "accidentalFlat": "flat",
    "keySharp": "sharp", "accidentalSharp": "sharp",
    "keyNatural": "natural", "accidentalNatural": "natural",
}

#: ROADMAP 2.86. A tie or slur END crossing the strip after the last barline
#: is the previous bar's arc running out to the margin: it says nothing about
#: whether the strip is a bar, so it votes for neither reading.
_NEUTRAL_IN_TAIL = frozenset({"tie", "slur"})


def _staff_tail_is_key_shaped(staff_rows) -> Optional[bool]:
    """One staff's vote for ROADMAP 2.86: is its trailing cell's ink the
    shape of a printed key (change), with nothing a bar would hold?

    True  -- every non-neutral box is a clef/time class, `timeSig*` digit
             ink, or a member of ONE key-shaped run: naturals (the
             cancellation) and then ONE kind of flat or sharp ([C21]: a
             signature carries one kind, and a change prints its naturals
             FIRST), with at least one key-shaped box.
    False -- anything else beside it (a notehead, a rest, a second
             accidental kind, a natural to the RIGHT of the flats): a note's
             accidental or a real bar.
    None  -- nothing but neutral ink (a tie/slur end): no vote (rule 8).
    """
    timesig_values = [r.value for r in staff_rows
                      if str(r.value[0]).startswith("timeSig")]
    run = []
    n_counted = 0
    for r in staff_rows:
        name = str(r.value[0])
        if name in _NEUTRAL_IN_TAIL:
            continue
        n_counted += 1
        if name in _KEY_SHAPE:
            try:
                xc = float(r.value[1]) + float(r.value[3]) / 2.0
            except (TypeError, ValueError, IndexError):
                return False
            run.append((xc, _KEY_SHAPE[name]))
            continue
        if _is_signature_glyph_class(name):
            continue
        if _geom.is_timesig_digit_ink(r.value, timesig_values):
            continue
        return False
    if n_counted == 0:
        return None
    if not run:
        return False
    kinds = {k for _, k in run if k != "natural"}
    if len(kinds) > 1:
        return False
    if kinds:
        first_signed = min(x for x, k in run if k != "natural")
        if any(k == "natural" and x > first_signed for x, k in run):
            return False
    return True


def _trailing_cell_key_shaped_vote(
    ev: Evidence, system_sub: Subject, last_cell_index: int,
) -> Tuple[int, int]:
    """`(n_key_shaped, n_voting)` over the system's staves, the 2.47b
    majority's shape: a staff whose tail is empty or holds only neutral ink
    counts in neither number."""
    rows = ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                    subject=system_sub)
    by_staff: Dict[Optional[int], List] = {}
    for r in rows:
        if (r.subject.cell == last_cell_index
                and isinstance(r.value, (list, tuple)) and len(r.value) == 5):
            by_staff.setdefault(r.subject.staff, []).append(r)
    n_yes = n_voting = 0
    for staff_rows in by_staff.values():
        vote = _staff_tail_is_key_shaped(staff_rows)
        if vote is None:
            continue
        n_voting += 1
        if vote:
            n_yes += 1
    return n_yes, n_voting


def _one_decided_system_key(ev: Evidence, system_sub: Subject) -> Optional[int]:
    """The ONE concert key `Q.SYSTEM_KEY` corroborated on `system_sub`, or
    None where it abstained, is absent, or corroborated none or several (a
    bitonal or half-misread system is not one decided key)."""
    v = ev.verdict(Q.SYSTEM_KEY, subject=system_sub)
    if v is None or v.outcome is not Outcome.DECIDED:
        return None
    value = v.value if isinstance(v.value, dict) else {}
    corroborated = value.get("corroborated") or []
    if len(corroborated) != 1:
        return None
    try:
        return int(corroborated[0])
    except (TypeError, ValueError):
        return None


def _mixed_tail_announces_next_key(
    ev: Evidence, system_sub: Subject, last_cell_index: int,
) -> Tuple[bool, Dict[str, object]]:
    """ROADMAP 2.86 (Sean 2026-10-11, on Brahms 317803 pdf p11 system 1: a
    double barline, then the new key on every staff, kept as a bar). A tail
    2.47b's PURE vote did not demote is demoted when BOTH hold:

    1. its ink is KEY-SHAPED on strictly more than half of the staves that
       vote (`_staff_tail_is_key_shaped`; ties and slur ends neutral); and
    2. CONNECT, NEVER GUESS -- the key changes at this boundary as an
       ALREADY-DECIDED fact: this system's and the NEXT system's
       `Q.SYSTEM_KEY` each corroborate ONE concert key, and they differ.
       A change printed at the head of the next system is announced at the
       end of this one (CLAUDE.md §10: a key change is printed at one bar on
       every staff of the system), so the key-shaped strip IS that
       announcement and governs no bar.

    Anything short of (2) keeps today's count and says why in
    `detail["mixed_tail_kept"]`: `this_key_not_decided`, `no_next_system`,
    `next_key_not_decided`, `next_key_unchanged`.

    ⚠️ KEY ONLY. A mixed CLEF tail is not connected: matching a staff to its
    own staff on the next system needs a part map ADJUDICATE does not hold
    at this point, and a pure clef tail is already 2.47b's. A mixed METER
    tail cannot be: `Q.METER` wants `Q.MEASURE_PARTITION`, so reading the
    meter verdict here would be a cycle.
    """
    n_yes, n_voting = _trailing_cell_key_shaped_vote(
        ev, system_sub, last_cell_index)
    detail: Dict[str, object] = {}
    if n_voting == 0 or not (2 * n_yes > n_voting):
        return False, detail
    detail["key_shaped_vote"] = "%d/%d" % (n_yes, n_voting)
    this_key = _one_decided_system_key(ev, system_sub)
    if this_key is None:
        detail["mixed_tail_kept"] = "this_key_not_decided"
        return False, detail
    later = [s for s in ev.subjects(Kind.SYSTEM) if s > system_sub]
    if not later:
        detail["mixed_tail_kept"] = "no_next_system"
        return False, detail
    next_sub = later[0]
    next_key = _one_decided_system_key(ev, next_sub)
    detail["this_system_key"] = this_key
    detail["next_system"] = next_sub.to_key()
    if next_key is None:
        detail["mixed_tail_kept"] = "next_key_not_decided"
        return False, detail
    detail["next_system_key"] = next_key
    if next_key == this_key:
        detail["mixed_tail_kept"] = "next_key_unchanged"
        return False, detail
    return True, detail


@decision(
    quantity=Q.MEASURE_PARTITION,
    checkable=Checkable.MIXED,
    checked_by=(
        "cross-staff measure count agreement (measure_count_warning)",
        "a merged bar sums to a MULTIPLE of the meter; a split bar to a fraction (rhythm_sum_warning)",
    ),
    implicates=(Q.MEASURE_PARTITION, Q.BARLINE_COLUMN, Q.SYSTEM_MEMBERSHIP,
                Q.DURATION, Q.SYSTEM_KEY),
    composed_from=(Q.BARLINE_COLUMN, Q.GLYPH_BOX, Q.SYSTEM_KEY),
    scope=Kind.STAFF,
    wants=(Q.BARLINE_COLUMN, Q.GLYPH_BOX, Q.SYSTEM_KEY),
    reasons=("read", "no_barline", "cautionary_tail_not_a_bar",
             "cautionary_key_tail_not_a_bar"),
)
def adjudicate_measure_partition(ev: Evidence) -> Ruling:
    rows = ev.rows(Q.BARLINE_COLUMN)
    if not rows:
        return Ruling.abstain("no_barline")
    n_cells = int(rows[-1].value)
    # A trailing cautionary strip can only exist past a REAL barline --
    # n_cells == 1 means `_measure_x_boundaries` read no barline at all for
    # this system, which is a different, already-handled shape (the
    # system's only cell, not a tail past its last rule) and is left alone.
    if n_cells >= 2:
        system_sub = ev.subject.at(Kind.SYSTEM)
        last_cell_index = n_cells - 1
        demoted, n_sig, n_total = _trailing_cell_is_cautionary_only(
            ev, system_sub, last_cell_index)
        if demoted:
            return Ruling(
                value=n_cells - 1, reason="cautionary_tail_not_a_bar",
                used=tuple(r.id for r in rows),
                detail={"cautionary_cell": last_cell_index,
                        "signature_only_vote": "%d/%d" % (n_sig, n_total)})
        # ROADMAP 2.86: a MIXED tail, demoted only where the next system's
        # decided key is the change it announces.
        announced, mixed = _mixed_tail_announces_next_key(
            ev, system_sub, last_cell_index)
        if announced:
            return Ruling(
                value=n_cells - 1, reason="cautionary_key_tail_not_a_bar",
                used=tuple(r.id for r in rows),
                detail={"cautionary_cell": last_cell_index,
                        "signature_only_vote": "%d/%d" % (n_sig, n_total),
                        **mixed})
        if mixed:
            return Ruling(value=n_cells, reason="read",
                          used=tuple(r.id for r in rows), detail=mixed)
    return Ruling(value=n_cells, reason="read", used=tuple(r.id for r in rows))


# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ THE TWO-QUESTION SPLIT. Conflating these is a shipped-bug shape.
# ─────────────────────────────────────────────────────────────────────────────


@decision(
    quantity=Q.STAFF_GROUP,
    checkable=Checkable.MIXED,
    checked_by=(
        "staves of one bracket group are one instrument FAMILY -- checkable only where identity came from a READ label",
    ),
    implicates=(Q.STAFF_GROUP, Q.INSTRUMENT),
    composed_from=(Q.BRACKET_BLOCK,),
    scope=Kind.STAFF,
    wants=(Q.BRACKET_BLOCK,),
    reasons=("bracket_block", "block_unavailable"),
    mode=Mode.ADDITIVE,
)
def adjudicate_staff_group(ev: Evidence) -> Ruling:
    """WHICH STAVES ARE ONE FAMILY. Says nothing about what symbol to draw.

    ⚠️ ADDITIVE by construction. Measured across 67 stored transcriptions,
    consuming this fact additively changed 20 exports, added 108 bracket
    groups, kept braces at 2 -> 2 with none lost, and made zero content
    differences outside the group lines. Letting it OVERRULE the incumbent
    rule would have declared five Brahms wind pairs to be pianos.

    ⚠️ THE ABSENT CASE IS ROUGHLY HALF THE POPULATION and is the whole reason
    this decision was chosen to go first: bracket blocks are 22/22 PRECISE
    and 22/39 RECALLED. It must ANCHOR a grouping where present and ABSTAIN
    where absent -- never assign.

    ⚠️ AND IT IS STRUCTURALLY SILENT ON THE POPULATION THE INCUMBENT RULE
    FIRES ON. `_assign_groups` refuses systems with fewer than 3 staves, so
    on a real two-staff page this measurement CANNOT SPEAK AT ALL. The two
    failure modes people cite -- a two-staff orchestral extract read as a
    piano, and a real piano on a crowded page -- are different problems and
    this can only ever address the second. `State.DECLINED` with reason
    `system_too_small` is what makes that visible instead of looking like a
    grouping of one.
    """
    state = ev.state(Q.BRACKET_BLOCK)
    if state is not State.READ:
        # DECLINED and ABSENT both abstain -- but they abstain for DIFFERENT
        # recorded reasons, and the harness puts the distinction on the
        # verdict (`declined` vs `missing`) without this function saying so.
        return Ruling.abstain("block_unavailable")
    rows = ev.rows(Q.BRACKET_BLOCK)
    return Ruling(value=int(rows[-1].value), reason="bracket_block",
                  used=tuple(r.id for r in rows))


@decision(
    quantity=Q.GROUP_SYMBOL,
    composed_from=(Q.STAFF_GROUP, Q.INSTRUMENT),
    scope=Kind.SYSTEM,
    wants=(Q.STAFF_GROUP, Q.INSTRUMENT, Q.SYSTEM_STAFF_COUNT),
    reasons=("brace_family", "bracket", "no_identity", "no_group"),
    mode=Mode.ADDITIVE,
)
def adjudicate_group_symbol(ev: Evidence) -> Ruling:
    """BRACE, BRACKET, OR NONE. A different question from who is grouped.

    ⚠️ A BRACKET BLOCK OF TWO STAVES IS NOT A GRAND STAFF. Brahms 1 p.1 reads
    blocks `[2,2,2,2,2,7,1,3]` -- five PAIRS that are `2 Flöten`, `2 Oboen`
    and so on. Consuming "block of 2" as a brace declares five wind pairs to
    be pianos. The block decides the GROUPING; the SYMBOL needs to know who
    is playing.

    ⚠️ ASSUMPTION (A-GROUP-2): a brace means ONE PLAYER on two staves, so the
    evidence for it is the INSTRUMENT being a keyboard or a harp -- not the
    staff count, which is what both incumbent sites use
    (`export.py:681` and `:3523` on `len(staves) == 2`, `:3446` on
    `len(slots) == 2`). With no identity this ABSTAINS and the consumer falls
    back to the incumbent rule, which is why the change is safe before
    identity is any good.
    """
    groups = ev.verdicts(Q.STAFF_GROUP, scope=Scope.SELF_AND_DESCENDANTS)
    if not groups:
        return Ruling.abstain("no_group")

    instruments = ev.verdicts(Q.INSTRUMENT, scope=Scope.SELF_AND_DESCENDANTS)
    named = [v for v in instruments if v.value is not None]
    if not named:
        # ⚠️ Not a failure. The honest answer with no identity is "I do not
        # know what symbol this is", and saying so lets the incumbent rule
        # stand rather than replacing it with a guess.
        return Ruling.abstain("no_identity")

    families = {str(v.value.get("family") if isinstance(v.value, dict)
                    else "") for v in named}
    if families & BRACE_FAMILIES:
        return Ruling(value="brace", reason="brace_family",
                      used=tuple(v.id for v in named))
    return Ruling(value="bracket", reason="bracket",
                  used=tuple(v.id for v in named))


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.27d — the grand-staff PAIR, as a fact other decisions can connect
# to (rule 6: connect, never guess). One helper, shared by every consumer
# that needs "is this staff one half of a decided piano/harp pair, and if so
# which staff is the other half" -- `adjudicators/text.py` (a dynamic BETWEEN
# the two staves belongs to the part), `adjudicators/rhythm.py` (a beam
# crossing into the OTHER staff of the SAME part is not "the neighbour's
# beam"), `adjudicators/ownership.py` (a pedal mark belongs to the pair, filed
# on the lower staff). A second copy of this query in each module would be
# the "derive it, don't re-list it" fault this project has already paid for.
# ─────────────────────────────────────────────────────────────────────────────


def grand_staff_partner_staff(ev: Evidence, home: str) -> Optional[str]:
    """The OTHER staff of a DECIDED brace pair `home` belongs to, or `None`.

    `home` is a `Kind.STAFF` subject key. Returns the partner's key only
    when ALL of these already-decided facts hold, none of them re-derived:

    1. `home`'s SYSTEM has a `Q.GROUP_SYMBOL` verdict DECIDED `"brace"`
       (`adjudicate_group_symbol`, above -- a brace means the group's own
       instrument family is `keyboard`/`harp`, `BRACE_FAMILIES`).
    2. `home` itself has a DECIDED `Q.STAFF_GROUP` block id.
    3. EXACTLY ONE other staff of the same system shares that block id.

    Any other shape -- no brace decided anywhere in the system, `home`'s
    own group undecided, a block of size 1 or >= 3 (an organ's pedal staff,
    say) -- returns `None` rather than guessing which staff is meant.
    Inert, by construction, on every orchestral system this project's
    acceptance set contains: none of them ever decides `Q.GROUP_SYMBOL`
    `"brace"` at all (`benchmarks/omr-owner-domain-2026-09/
    PLACEMENT-CONVENTIONS.md`, "Rules safe to wire", item B).

    ⚠️ `ev.verdict`/`ev.subjects` ARE THE CALLER'S OWN `Evidence`, so
    `Q.GROUP_SYMBOL` and `Q.STAFF_GROUP` must be in the CALLER's `wants` --
    this function declares nothing itself, exactly as `adjudicators.
    ownership._owned_by_a_different_staff` (ROADMAP 2.27) reads `Q.
    GLYPH_OWNER` through whichever decision calls it.
    """
    home_sub = home if isinstance(home, Subject) else Subject.from_key(home)
    system_sub = home_sub.at(Kind.SYSTEM)
    brace = ev.verdict(Q.GROUP_SYMBOL, subject=system_sub)
    if brace is None or brace.value != "brace":
        return None
    own_group = ev.verdict(Q.STAFF_GROUP, subject=home_sub)
    if own_group is None or own_group.value is None:
        return None
    partners: List[Subject] = []
    for st in ev.subjects(Kind.STAFF):
        if st == home_sub or st.at(Kind.SYSTEM) != system_sub:
            continue
        v = ev.verdict(Q.STAFF_GROUP, subject=st)
        if v is not None and v.value == own_group.value:
            partners.append(st)
    if len(partners) != 1:
        return None
    return partners[0].to_key()
