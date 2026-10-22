"""A box whose ink lies inside the printed meter's claimed area -- ROADMAP 2.177 (flag `OMR_METER_OBJECT`, default OFF).

PATH: STAGED, ADJUDICATE (notehead precision, rest precision). It reads ONE GATHER fact, `Q.CLAIMED_AREA` (owner `meter`, unit `area`),
filed on the staff by `gather.gather_meter_object` off the page raster, and nothing else is measured here.

Sean, 2026-10-20: the meter is two numerals, read once as ONE object; its area is claimed and "doesnt allow anything else to box that
area". The area is the numerals' own measured box on THIS staff (never a column read off sibling staves: `key_slots.meter_column` was 18
spaces wide and swallowed real eighth rests, the loose sibling-column test hit 24 real stemmed chord notes). The claim row carries, for
every other box of the cell (and of the bar before it, whose padded crop reaches the numerals), the share of THAT BOX'S OWN INK
(staff-line runs left out) that lies inside the area; this module refuses a box whose share is at least `INSIDE_SHARE_MIN`.

REFUSED, never re-valued; the box stays a `Q.GLYPH_BOX` row and export counts it under `not_a_notehead:inside_the_meter`.

PROTECTED: the first note after the meter (its ink lies outside the area; a box that only touches the edge has a small share and is kept);
a head a stem touches (a note: rule 8, no refusal on a guess); anything with no measured share (not listed = not refused).

CONVENTION ASSUMED: nothing but the two numerals is printed inside the numerals' own box. WHAT WOULD FALSIFY IT: a print-confirmed head
standing on numeral ink. NOT CONFIRMED beyond the two plates; blind tiles `out/print/2.177-review/`.
"""
from __future__ import annotations

from typing import Any, Dict, NamedTuple, Optional

from .. import geometry as _geom
from .. import meter_object as _mo
from ..record import Kind, Q, Scope

REASON = "inside_the_meter"
#: share of the box's own ink that must lie inside the area (stated before the count: a digit loop is wholly inside, ~1.0; a head beside
#: the numerals shares at most a sliver)
INSIDE_SHARE_MIN = 0.5


def enabled() -> bool:
    return _mo.enabled()


class Finding(NamedTuple):
    used: tuple
    margin: float
    detail: Dict[str, Any]


def read(ev: Any, box_row: Any, claims: Any, *, head: bool) -> Optional[Finding]:
    """A `Finding` where this box's ink lies inside a claimed meter area on its staff, else None (a missing row declines). `claims`: the
    caller's `ev.rows(Q.CLAIMED_AREA, scope=Scope.SELF_AND_ANCESTORS)` (the row is filed on the STAFF; the decision declares the read)."""
    if not enabled() or box_row is None:
        return None
    if ev.subject.at(Kind.STAFF) is None:
        return None
    key = ev.subject.to_key()
    best = None
    for r in claims:
        d = r.detail or {}
        if d.get("owner") != "meter" or d.get("unit") != "area" or d.get("standing") != "READ":
            continue
        got = (d.get("boxes_inside") or {}).get(key)
        if not got:
            continue
        share = float(got.get("ink_share_inside", 0.0))
        if share >= INSIDE_SHARE_MIN and (best is None or share > best[0]):
            best = (share, r, got)
    if best is None:
        return None
    share, r, got = best
    if head:
        v = box_row.value
        cell = ev.subject.at(Kind.CELL)
        if isinstance(v, (list, tuple)) and len(v) == 5 and cell is not None:
            hb = tuple(float(x) for x in v[1:5])
            for st in ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell):
                sv = st.value
                if isinstance(sv, (list, tuple)) and len(sv) >= 4 and _geom.stem_touches_head(tuple(float(x) for x in sv[:4]), hb):
                    return None
    owner_row = (r.detail or {}).get("owner_row")
    detail = {"claimed_area": {"row": r.id, "area_page_px": (r.value if isinstance(r.value, list) else None),
                               "owner": "meter", "owner_row": owner_row, "ink_share_inside": round(share, 3), "cut": INSIDE_SHARE_MIN,
                               "inside_px": got.get("inside_px"), "ink_px": got.get("ink_px")}}
    return Finding(used=(box_row.id, r.id), margin=share - INSIDE_SHARE_MIN, detail=detail)
