"""ROADMAP 2.205 -- `adjudicate_stroke_owner`: ONE OWNER PER STROKE, decided once per cell (flag `OMR_STROKE_OWNER`, default ON since 2026-10-26; needs the
`Q.STROKE` / `Q.GLYPH_STROKES` rows `OMR_STROKE_MAP` files in GATHER). STAGED ADJUDICATE.

The rule is `stroke_owner.py` (pure; read its module doc for the claim order, the shapes and the table). This file only gathers the cell's
evidence into `Ink` / `Claim` values, calls `own_strokes`, and records the result as one verdict on the CELL (a stroke is a measurement, not
a subject: 2.198 keeps strokes out of every decision's domain, so a verdict per stroke would put ~50k subjects into the walk):

  value   {"owned": [ordinals a mark owns], "contested": [ordinals two families claim and the shape cannot settle]}
  detail  "strokes": {ordinal: [state, family, owners, by, [[key, family, cls, fit, why, how], ...]]} for every stroke that is not plainly
          unclaimed; "boxes": {glyph key: [verdict, [[ordinal, state, family, why], ...]]} for each head / rest / accidental box that owns
          none of its ink (`stroke_owner.box_verdict`: refused / contested); "census": counts by state and owner family

CONSUMERS. 2.202 (`rhythm._stroke_views`) and 2.204 (`rhythm._stem_views`) MASK the owned and contested strokes when the flag is on: the
stroke stays in their views as ink (a slur at a stem tip is still ink there -- never a "clean tip"), but its kind becomes `owned` /
`contested`, so it is never a beam, a hook, a stub or a stem (rule 8: a contested stroke is no witness either way).

THE OLD PAIR RULES (plan section 3, for rests and heads) are NOT replaced here: this is the parity step (plan section 5: file, consult, prove
parity on the record, then delete). The box verdicts are on the record so the parity is a query (`benchmarks/shared-ink-map-2026-10/
multi_claim_census.py`, FINDINGS 2.205); no precision decision reads them yet, so with the consumers' flags off the exported file does not
change.

CROSS-STAFF. `glyph_owner` runs AFTER the precision rules this decision must stand before, so it cannot be read here. A neighbour staff's
box seen in this cell's padded crop still owns its ink in this cell (it is that mark's ink, never this staff's beam or stem), which is all
the consumers need; which staff the MARK belongs to stays `glyph_owner`'s question (page-facts section 3).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

from ..adjudicate import Evidence, Mode, Ruling, decision
from ..record import Kind, Q, Scope, STROKE_GLYPH_BASE
from .. import stroke_owner as SO


def enabled() -> bool:
    """`OMR_STROKE_OWNER`, default ON since 2026-10-26 (Sean "1. Yes"); an explicit 0/false/no/off disables."""
    return os.environ.get(SO.ENV, "1").strip().lower() not in ("0", "false", "no", "off")


def _inks(rows) -> Tuple[List[SO.Ink], Dict[int, Tuple[float, ...]]]:
    """The cell's `Q.STROKE` rows as `Ink`, and each stroke's page-px box (for the area claims)."""
    inks, page = [], {}
    for r in rows:
        g = getattr(r.subject, "glyph", None)
        d = r.detail or {}
        box = d.get("stroke_box")
        if g is None or not (STROKE_GLYPH_BASE <= g < 400_000) or not box or len(box) < 4:
            continue
        o = g - STROKE_GLYPH_BASE
        sp = float(d.get("staff_space_local_px") or 0.0)
        w, h = float(box[2]), float(box[3])
        area = float(d.get("fill") or 0.0) * w * h / (sp * sp) if sp > 0 else 0.0
        inks.append(SO.Ink(o, str(r.value), tuple(float(v) for v in box[:4]), float(d.get("length_spaces") or 0.0),
                           float(d.get("thickness_spaces") or 0.0), area, sp,
                           tuple((int(a), float(b)) for a, b in (d.get("touches") or ())), r.id, float(d.get("angle_deg") or 0.0)))
        pb = d.get("bbox_page_px")
        if isinstance(pb, (list, tuple)) and len(pb) == 4:
            page[o] = tuple(float(v) for v in pb)
    return inks, page


def _claims(ev: Evidence, cell) -> List[SO.Claim]:
    """Every detector box of the cell with its strokes (`Q.GLYPH_STROKES`), and the register's READ area claims for this cell."""
    gs_by = {}
    for r in ev.rows(Q.GLYPH_STROKES, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        if isinstance(r.value, (list, tuple)):
            gs_by[r.subject.to_key()] = r
    out: List[SO.Claim] = []
    for b in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        v = b.value
        if not (isinstance(v, (list, tuple)) and v):
            continue
        if str(b.reader or "").startswith("yolo_rescue"):
            continue                       # a rescue-only box is never written while RESCUE_SHIPS is off: it owns no ink
        fam = SO.family_of(str(v[0]), (b.detail or {}).get("category"))
        key = b.subject.to_key()
        g = gs_by.get(key)
        if fam is None or g is None:
            continue
        part = tuple((int(a), float(sh)) for a, sh in ((g.detail or {}).get("partial") or ()))
        out.append(SO.Claim(key, fam, str(v[0]), tuple(int(o) for o in g.value), part, g.id))
    return out


def _areas(ev: Evidence, cell, page: Dict[int, Tuple[float, ...]]) -> List[SO.Claim]:
    out: List[SO.Claim] = []
    idx = getattr(cell, "cell", None)
    for r in ev.rows(Q.CLAIMED_AREA, scope=Scope.SELF_AND_ANCESTORS, subject=cell):
        d = r.detail or {}
        if d.get("cell") != idx or d.get("unit") != "area" or d.get("standing", "READ") != "READ":
            continue
        owner = str(d.get("owner") or "")
        v = r.value
        if owner not in SO.AREA_OWNERS or not (isinstance(v, (list, tuple)) and len(v) == 4):
            continue
        x0, y0, x1, y1 = (float(t) for t in v)
        inside = tuple(o for o, pb in sorted(page.items()) if x0 <= (pb[0] + pb[2]) / 2.0 <= x1 and y0 <= (pb[1] + pb[3]) / 2.0 <= y1)
        if inside:
            out.append(SO.Claim(r.id, owner, owner, inside, (), r.id, area=True))
    return out


@decision(
    quantity=Q.STROKE_OWNER,
    scope=Kind.CELL,
    # GATHER rows only (the strokes, the boxes and what each stands on, the register's areas): it needs no verdict, so it stands ahead of
    # every precision rule and every consumer (adjudicate.ORDER).
    wants=(Q.STROKE, Q.GLYPH_STROKES, Q.GLYPH_BOX, Q.CLAIMED_AREA),
    subjects_from=Q.STROKE,
    reasons=("strokes_owned", "some_strokes_contested", "no_claimant", "no_strokes"),
    mode=Mode.ADDITIVE,
    composed_from=(Q.STROKE, Q.GLYPH_STROKES, Q.GLYPH_BOX, Q.CLAIMED_AREA),
)
def adjudicate_stroke_owner(ev: Evidence) -> Ruling:
    """Which mark owns each stroke of this cell (module doc; the rule is `stroke_owner.own_strokes`)."""
    cell = ev.subject
    inks, page = _inks(ev.rows(Q.STROKE, scope=Scope.SELF_AND_DESCENDANTS, subject=cell))
    if not inks:
        return Ruling.abstain("no_strokes")
    claims = _claims(ev, cell)
    claims += _areas(ev, cell, page)
    owned = SO.own_strokes(inks, claims, tiers=SO.TIERS)
    by_ord = {i.ordinal: i for i in inks}
    strokes: Dict[str, Any] = {}
    used: List[str] = []
    for o in sorted(owned):
        w = owned[o]
        if w.state == "unclaimed":
            continue
        strokes[str(o)] = [w.state, w.family, list(w.owners), w.by,
                           [[c["key"], c["family"], c["cls"], c["fit"], c["why"], c["how"]] for c in w.candidates]]
        used.extend(w.row_ids)
    boxes: Dict[str, Any] = {}
    for c in claims:
        if c.area or c.family not in ("head", "rest", "accidental"):
            continue
        bv = SO.box_verdict(c, owned, by_ord)
        if bv["verdict"] in ("refused", "contested"):
            boxes[c.key] = [bv["verdict"], [list(x) for x in bv["lost"]]]
    value = {"owned": sorted(o for o, w in owned.items() if w.state in ("decided", "merged")),
             "contested": sorted(o for o, w in owned.items() if w.state == "contested")}
    detail = {"strokes": strokes, "boxes": boxes, "census": SO.census(owned)}
    used_t = tuple(dict.fromkeys(u for u in used if u))
    if not strokes:
        return Ruling(value=value, reason="no_claimant", used=used_t, detail=detail)
    if value["contested"]:
        return Ruling(value=value, reason="some_strokes_contested", used=used_t, detail=detail)
    return Ruling(value=value, reason="strokes_owned", used=used_t, detail=detail)


def masked(verdict) -> Dict[int, str]:
    """`{ordinal: "owned" | "contested"}` from a cell's `Q.STROKE_OWNER` verdict (None, abstained or flag off: `{}`). For the consumers."""
    if not enabled() or verdict is None or not isinstance(getattr(verdict, "value", None), dict):
        return {}
    v = verdict.value
    out = {int(o): "owned" for o in v.get("owned") or ()}
    out.update({int(o): "contested" for o in v.get("contested") or ()})
    return out
