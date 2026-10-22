"""A far head's staff position -- ROADMAP 2.56.

A notehead outside its staff's first space ALWAYS has ledger lines toward its
own staff (Sean, 2026-09-29: *"there is no such thing as a far note with no
ledger line"*), so its position is not the geometry's extrapolation of the
staff grid -- it is counted off the printed ledgers. `gather.gather_far_head_
ledger_positions` files that reading (`Q.FAR_HEAD_LEDGER_POSITION`, under its
own reader, as a second witness beside the geometry row); this decision turns
it into the head's position.

## Stage

ADJUDICATE: the answer is the one reader's own, so the decision adds no
geometry. It reads the ledger row and names the head's position; where the
reader could not say, it ABSTAINS -- the geometry position is NOT substituted
for a head that needed a ledger read (CLAUDE.md §2 rule 8). The geometry
position the reader saw rides on its own row (`geometry_position`) and is
copied to `detail`, so the verdict says whether the two witnesses agree.

Only far heads are in the domain (`subjects_from` is the ledger row, which
GATHER files on far heads alone). `restate_pitch` (EVALUATE) reads this
verdict ahead of the geometry row where one is DECIDED.
"""
from __future__ import annotations

from ..adjudicate import Evidence, Mode, Ruling, decision
from ..record import ABSTAIN, Kind, Q

@decision(
    quantity=Q.NOTEHEAD_POSITION,
    scope=Kind.GLYPH,
    wants=(Q.FAR_HEAD_LEDGER_POSITION,),
    subjects_from=Q.FAR_HEAD_LEDGER_POSITION,
    reasons=("ledger_position", ABSTAIN.LEDGER_NOT_READ, ABSTAIN.NO_PAGE_SHAPE,
             ABSTAIN.NO_STAFF_GEOMETRY, ABSTAIN.NO_MASK),
    mode=Mode.ADDITIVE,
    composed_from=(Q.FAR_HEAD_LEDGER_POSITION,),
)
def adjudicate_notehead_position(ev: Evidence) -> Ruling:
    """Where does this far head sit, counted off its printed ledgers?"""
    rows = ev.rows(Q.FAR_HEAD_LEDGER_POSITION)
    if rows:
        row = rows[-1]
        detail = row.detail or {}
        pos = int(round(float(row.value)))
        geo = detail.get("geometry_position")
        return Ruling(value=pos, reason="ledger_position", used=(row.id,),
                      detail=dict(
                          geometry_position=geo,
                          agrees_with_geometry=(None if geo is None
                                                else int(geo) == pos),
                          ledger_reason=detail.get("ledger_reason"),
                          box_source=detail.get("box_source"),
                          shape_source=detail.get("shape_source")))
    refusals = ev.refusals(Q.FAR_HEAD_LEDGER_POSITION)
    if refusals:
        why = (refusals[-1].detail or {}).get("ledger_reason")
        reason = refusals[-1].reason
        if reason == ABSTAIN.NO_PAGE_SHAPE:
            return Ruling.abstain(ABSTAIN.NO_PAGE_SHAPE, ledger_reason=why)
        if reason == ABSTAIN.NO_STAFF_GEOMETRY:
            return Ruling.abstain(ABSTAIN.NO_STAFF_GEOMETRY, ledger_reason=why)
        if reason == ABSTAIN.NO_MASK:
            return Ruling.abstain(ABSTAIN.NO_MASK, ledger_reason=why)
        return Ruling.abstain(ABSTAIN.LEDGER_NOT_READ, ledger_reason=why)
    return Ruling.abstain(ABSTAIN.LEDGER_NOT_READ)
