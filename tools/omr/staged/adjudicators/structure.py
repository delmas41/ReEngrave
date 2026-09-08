"""Structure — systems, families, bars, ordinals.

Everything here rests on MEASUREMENTS whose only ancestor is the raster, so
no provenance question can arise and the circularity filter has nothing to
do. That is exactly why the design put grouping first.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..adjudicate import Evidence, Mode, Ruling, Term, decision, tally
from ..record import ABSTAIN, Kind, Q, Scope, State

# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ ASSUMED CONSTANTS. None of these is measured. See ASSUMPTIONS.md.
# ─────────────────────────────────────────────────────────────────────────────

#: A brace means ONE PLAYER reading two staves. These are the families that
#: do that. (A-GROUP-2)
BRACE_FAMILIES = frozenset({"keyboard", "harp"})


@decision(
    quantity=Q.SYSTEM_MEMBERSHIP,
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


@decision(
    quantity=Q.MEASURE_PARTITION,
    scope=Kind.STAFF,
    wants=(Q.BARLINE_COLUMN,),
    reasons=("read", "no_barline"),
)
def adjudicate_measure_partition(ev: Evidence) -> Ruling:
    rows = ev.rows(Q.BARLINE_COLUMN)
    if not rows:
        return Ruling.abstain("no_barline")
    return Ruling(value=int(rows[-1].value), reason="read",
                  used=tuple(r.id for r in rows))


# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ THE TWO-QUESTION SPLIT. Conflating these is a shipped-bug shape.
# ─────────────────────────────────────────────────────────────────────────────


@decision(
    quantity=Q.STAFF_GROUP,
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
