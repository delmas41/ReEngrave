"""ROADMAP 2.277 (flag `OMR_CLAIM_FINAL`, default ON) -- the ONE consult of "claimed ink is final", for the precision rules (STAGED ADJUDICATE).

It reads, never measures: the cell's `Q.STROKE_OWNER` verdict carries `detail.claim_final` (`adjudicators/stroke_owner._claim_final`, the pure rule in
`claim_final.py`): for every box held at least `NEAR_MIN` of its own ink by a claim of another kind, which claim, how much, which strokes. A box held
at least `CUT` is refused BY THAT CLAIM (`claimed_by:<kind>`), so the claim is the first cause, never a shape rule. The six owners
`claimed_by.consult` already judges (clef, meter, key signature, the header column, word, bracket) are left to it -- it has the stem exceptions and
a NARROW path -- and every other claim kind is taken here, generically: barline, an arc's or a hairpin's traced ink, a tremolo slash a later lane
files, anything else an area claim names.

A box that OWNS one of its strokes (`box_owns`: a head blob a shape test fitted) is never refused here: a real head touching a barline, a slur or a
dynamic keeps its blob, and a claim that holds most of the box's ink while the box owns a stroke of its own is a tile, not a refusal (rule 8).
"""
from __future__ import annotations

from typing import Any, Dict, NamedTuple, Optional, Tuple

from .. import claim_final as CF
from ..record import Kind, Q


class Finding(NamedTuple):
    kind: str            # the `<kind>` of `claimed_by:<kind>`: barline / arc / hairpin / page_claim
    by: str              # the claim family the stroke owner named
    share: float         # the share of the box's own ink the claim holds
    used: Tuple[str, ...]
    detail: Dict[str, Any]


def enabled() -> bool:
    return CF.enabled()


def entry(ev: Any, box_key: str, verdict: Any = None) -> Optional[Tuple[Dict[str, Any], Any]]:
    """`(held entry, the cell's stroke-owner verdict)` for this box, or None (flag off, no verdict, not held)."""
    if not CF.enabled():
        return None
    cell = ev.subject.at(Kind.CELL)
    if cell is None:
        return None
    v = verdict if verdict is not None else ev.verdict(Q.STROKE_OWNER, subject=cell)
    cf = (getattr(v, "detail", None) or {}).get("claim_final")
    if not isinstance(cf, dict):
        return None
    e = (cf.get("held") or {}).get(box_key)
    return (e, v) if e else None


def finding(ev: Any, box_row: Any, verdict: Any = None) -> Optional[Finding]:
    """The refusal this box earns from a claim it stands on, or None. Decides nothing else. `verdict`: the cell's `Q.STROKE_OWNER` verdict the deciding
    module READ in its own body (so its `wants` entry is visibly live); None reads it here."""
    got = entry(ev, ev.subject.to_key(), verdict)
    if got is None:
        return None
    e, v = got
    if e["by"] in CF.CONSULTED_ELSEWHERE or e["by"] in CF.MARK_ONLY or float(e["share"]) < CF.CUT:
        return None
    if ev.subject.to_key() in set((getattr(v, "detail", None) or {}).get("box_owns") or ()):
        return None
    detail = {"claim_final": {"by": e["by"], "share": e["share"], "cut": CF.CUT, "strokes": e["strokes"], "also": e.get("also") or [],
                              "verdict": getattr(v, "id", None)}}
    used = tuple(x for x in ((box_row.id if box_row is not None else None), getattr(v, "id", None)) if x)
    return Finding(CF.refusal_kind(e["by"]), e["by"], float(e["share"]), used, detail)
