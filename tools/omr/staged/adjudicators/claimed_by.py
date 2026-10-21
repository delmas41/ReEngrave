"""The ONE consult of the claimed-area register -- ROADMAP 2.181 (flag `OMR_CLAIMED_REGISTER`, default ON).

PATH: STAGED, ADJUDICATE (notehead precision, rest precision). It reads `Q.CLAIMED_AREA` (every owner: `clef`, `leading_column`,
2.177's `meter`), `Q.STEM` and `Q.GLYPH_CONF`; it measures nothing (GATHER measured the ink shares, `claims.covering` lists them).

The plan's EVALUATE question, per box: does a refusal FOLLOW from the claims that hold this box's ink?

* REFUSE (`claimed_by:<owner>`) where one holding claim is strong enough on its own:
  - `meter`, READ (2.177: the numerals' own area) -- not for a head a stem touches (a note; rule 8, as 2.177);
  - `clef` NAMING the box (the located clef overrode it: 2.11's `is_a_clef`, carried over unchanged);
  - `clef`, READ (a located clef's box, or a clef-sized detector box at a bar's start) -- not for a head a stem touches, and not
    where the detector scored the head above the clef box (two readings of one ink disagree: that NARROWS, never an argmax);
  - `leading_column` (a PRIOR, Sean 2026-10-20) only where the box's OWN ink is a line running on past it (barline / bracket /
    brace stroke, `claims.through_stroke`) and no stem touches it.
* NARROW (both readings carried, written blue) where a claim holds the box but is not strong enough: a NARROWED clef (a detector
  `clef*` box away from a bar's start, 2.144's case), a clef the detector voted under the head, the header column on a box whose ink
  is not a line or that a stem touches.
* nothing where no claim holds the box (the shape rules judge it as before).

Every overlapping owner is a non-note mark, so where any of them refuses, the box is not a note whichever is right: the refusal
cites every holding claim in `used`. Nothing picks between two owners by confidence.
"""
from __future__ import annotations

from typing import Any, Dict, NamedTuple, Optional

from .. import claims as _claims
from .. import geometry as _geom
from ..record import Kind, Q, Scope

#: which owner names a refusal when several refuse (the most specific mark first; the header column, a prior, last)
_ORDER = (_claims.OWNER_METER, _claims.OWNER_KEY, _claims.OWNER_CLEF, _claims.OWNER_COLUMN)


def enabled() -> bool:
    return _claims.enabled()


def key_active() -> bool:
    """ROADMAP 2.183: the key signature is a claim in the register (`OMR_KEY_SIGNATURE_CLAIM` and `OMR_CLAIMED_REGISTER` both on)."""
    return _claims.key_active()


class Finding(NamedTuple):
    refuse: bool          # True: refuse; False: narrow
    by: str               # the claiming owner (`clef`, `leading_column`, `meter`)
    used: tuple
    margin: float
    detail: Dict[str, Any]


def _stemmed(ev: Any, box_row: Any) -> bool:
    v = box_row.value
    cell = ev.subject.at(Kind.CELL)
    if not (isinstance(v, (list, tuple)) and len(v) == 5) or cell is None:
        return False
    hb = tuple(float(x) for x in v[1:5])
    for st in ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell):
        sv = st.value
        if isinstance(sv, (list, tuple)) and len(sv) >= 4 and _geom.stem_touches_head(tuple(float(x) for x in sv[:4]), hb):
            return True
    return False


def _confs(ev: Any) -> Dict[str, float]:
    cell = ev.subject.at(Kind.CELL)
    out: Dict[str, float] = {}
    if cell is None:
        return out
    for r in ev.rows(Q.GLYPH_CONF, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        try:
            out[r.subject.to_key()] = float(r.value)
        except (TypeError, ValueError):
            continue
    return out


def consult(ev: Any, box_row: Any, *, head: bool, family: str = "note", rows: Any = None) -> Optional[Finding]:
    """REFUSE / NARROW / None for this box (see the module docstring). A missing row declines (rule 8). `family` is "note" (a head or
    a rest: a claim that cannot refuse NARROWS) or "mark" (a flag, an arpeggiato, an arc: only the key signature's NAMED box refuses
    -- those families have no blue reading, so nothing else is consulted). `rows`: the decision's own read of `Q.CLAIMED_AREA`, if it made one."""
    if not enabled() or box_row is None or ev.subject.at(Kind.STAFF) is None:
        return None
    key = box_row.subject.to_key() if family == "mark" else ev.subject.to_key()
    held = _claims.covering(rows if rows is not None else ev.rows(Q.CLAIMED_AREA, scope=Scope.SELF_AND_ANCESTORS), key)
    if not held:
        return None
    stemmed = _stemmed(ev, box_row) if head else False
    confs = None
    refusing, narrowing = [], []
    for r, e in held:
        d = r.detail or {}
        owner, standing = d.get("owner"), d.get("standing")
        if family == "mark" and owner != _claims.OWNER_KEY:
            continue
        share = float(e.get("ink_share_inside", 1.0 if e.get("named") else 0.0))
        margin = share - _claims.INSIDE_SHARE_MIN
        why = None
        if owner == _claims.OWNER_METER:
            if standing != "READ" or stemmed:
                continue                                   # 2.177: a stemmed head is a note; an unread meter files no claim
            refusing.append((owner, r, margin, "meter_read"))
            continue
        if owner == _claims.OWNER_KEY:
            # 2.183: the key run's own ink. A box that STANDS in the window (the 2.100 rule, Sean 2026-10-12 "only clefs appear before
            # key accidentals") is the signature's ink boxed under another name: refused, a head with a stem on it included (2.100
            # refused them all). A box merely holding >= `INSIDE_SHARE_MIN` of its own ink inside the area, or any box of a window one
            # staff alone drew away from the header (a key change with no second staff), is NARROWED -- never refused on that.
            if family == "mark":
                if e.get("named") and standing == "READ":
                    refusing.append((owner, r, float(e.get("stand_margin_spaces") or 0.0), "stands_in_the_key_run"))
                continue
            if e.get("named"):
                m = float(e.get("stand_margin_spaces") or 0.0)
                if standing == "READ":
                    refusing.append((owner, r, m, "stands_in_the_key_run"))
                else:
                    narrowing.append((owner, r, m, "key_run_seen_on_one_staff"))
            else:
                narrowing.append((owner, r, margin, "ink_inside_the_key_run"))
            continue
        if owner == _claims.OWNER_CLEF:
            if e.get("named"):
                refusing.append((owner, r, 1.0, "named_by_the_located_clef"))
                continue
            if stemmed:
                continue                                   # 2.176 / 2.144: a stem stands on it: a note
            voted_under = False
            if head and d.get("owner_glyph"):
                if confs is None:
                    confs = _confs(ev)
                head_conf, clef_conf = confs.get(key), confs.get(d.get("owner_glyph"))
                voted_under = head_conf is not None and clef_conf is not None and clef_conf < head_conf
            # 2.176 `on_another_symbols_box`, kept a REFUSAL (Sean-confirmed 9/9): a stemless head box >= 0.9 inside a clef box that
            # starts within 6 sp of its bar's left edge, the clef scored at least as high
            bar_start = d.get("start_spaces") is not None and float(d["start_spaces"]) <= _claims.CLEF_WINDOW_SPACES
            if head and bar_start and not voted_under and float(e.get("box_cover", 0.0)) >= _claims.CLEF_BOX_COVER_MIN \
                    and d.get("owner_glyph"):
                why = None
            elif standing != "READ":
                why = "clef_away_from_a_bar_start"
            elif voted_under:
                why = "detector_scored_the_head_above_the_clef"
            (narrowing if why else refusing).append((owner, r, margin, why or "clef_read"))
            continue
        if owner == _claims.OWNER_COLUMN:
            t = e.get("through") or {}
            edge = e.get("left_edge_spaces")
            if edge is not None and float(edge) <= _claims.LEADING_EDGE_SPACES:
                # 2.176 `on_the_staffs_leading_barline`, kept a REFUSAL (Sean-confirmed brackets / barlines)
                refusing.append((owner, r, _claims.LEADING_EDGE_SPACES - float(edge), "at_the_staffs_leading_edge"))
            elif t.get("through") and not stemmed:
                refusing.append((owner, r, margin, "line_shaped_ink"))
            else:
                narrowing.append((owner, r, margin, "stemmed" if stemmed else "ink_not_line_shaped"))
    pick = refusing or narrowing
    if not pick:
        return None
    pick.sort(key=lambda t: _ORDER.index(t[0]))
    owner, r0, margin, why = pick[0]
    used = (box_row.id,) + tuple(dict.fromkeys(r.id for _o, r, _m, _w in refusing + narrowing))
    d0 = r0.detail or {}
    detail = {"claimed_by": {"owner": owner, "row": r0.id, "why": why, "stemmed": stemmed,
                             # how the claim was drawn: the header column's right edge (own clef / the system's clefs), the locator's crop
                             "right_edge": d0.get("right_edge"), "locator_frame": d0.get("locator_frame"), "prior": d0.get("prior"),
                             "holding": [{"owner": o, "row": r.id, "why": w, "margin": round(m, 3)} for o, r, m, w in refusing + narrowing],
                             "entry": (r0.detail or {}).get("boxes_inside", {}).get(key)}}
    return Finding(bool(refusing), owner, used, margin, detail)
