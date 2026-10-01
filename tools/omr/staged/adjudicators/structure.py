"""Structure — systems, families, bars, ordinals.

Everything here rests on MEASUREMENTS whose only ancestor is the raster, so
no provenance question can arise and the circularity filter has nothing to
do. That is exactly why the design put grouping first.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..adjudicate import Checkable, Evidence, Mode, Ruling, Term, decision, tally
from ..record import ABSTAIN, Kind, Q, Scope, State, Subject

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


def _trailing_cell_is_cautionary_only(
    ev: Evidence, system_sub: Subject, last_cell_index: int,
) -> bool:
    """ROADMAP 2.47b (CLAUDE.md section 10): "a cautionary meter after a
    system's last barline governs no bar" -- generalised from the meter
    reading to the PARTITION itself. `measure_extractor._measure_x_
    boundaries` decides, on WIDTH alone, whether the strip after a system's
    own final barline becomes its own bar or is absorbed into the one
    before it (`benchmarks/omr-measure-partition-2026-09/FINDINGS.md` §0a,
    §3: a human reads that strip by what is PRINTED in it, which the width
    rule cannot see and this does, after the detector has run).

    True only when `Q.GLYPH_BOX` has at least one row filed in that exact
    cell, ACROSS EVERY STAFF OF THE SYSTEM (not just the staff being
    decided -- a pickup or a short final bar on one staff while its
    neighbours have already finished still makes it a real bar for the
    whole system, CLAUDE.md section 10's "printed at one bar on every staff
    of the system" shape), and every one of those rows is a clef/key/time
    class with nothing else beside it -- no notehead, no rest, no other
    musical event, on any staff.

    An EMPTY cell -- the detector found nothing there at all -- answers
    False. "We found nothing" is not evidence either way (rule 8: a
    fallback never converts "cannot tell" into an answer), so today's
    geometry-only count stands, unchanged, exactly as the brief's third
    control requires.
    """
    rows = ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                    subject=system_sub)
    in_cell = [r for r in rows
               if r.subject.cell == last_cell_index
               and isinstance(r.value, (list, tuple)) and r.value]
    if not in_cell:
        return False
    return all(_is_signature_glyph_class(r.value[0]) for r in in_cell)


@decision(
    quantity=Q.MEASURE_PARTITION,
    checkable=Checkable.MIXED,
    checked_by=(
        "cross-staff measure count agreement (measure_count_warning)",
        "a merged bar sums to a MULTIPLE of the meter; a split bar to a fraction (rhythm_sum_warning)",
    ),
    implicates=(Q.MEASURE_PARTITION, Q.BARLINE_COLUMN, Q.SYSTEM_MEMBERSHIP, Q.DURATION),
    composed_from=(Q.BARLINE_COLUMN, Q.GLYPH_BOX),
    scope=Kind.STAFF,
    wants=(Q.BARLINE_COLUMN, Q.GLYPH_BOX),
    reasons=("read", "no_barline", "cautionary_tail_not_a_bar"),
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
        if _trailing_cell_is_cautionary_only(ev, system_sub, last_cell_index):
            return Ruling(
                value=n_cells - 1, reason="cautionary_tail_not_a_bar",
                used=tuple(r.id for r in rows),
                detail={"cautionary_cell": last_cell_index})
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
