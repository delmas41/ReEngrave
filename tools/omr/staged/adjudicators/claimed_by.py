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
_ORDER = (_claims.OWNER_METER, _claims.OWNER_KEY, _claims.OWNER_CLEF, _claims.OWNER_BRACKET, _claims.OWNER_WORD, _claims.OWNER_COLUMN)


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


def _stem_inside_claim(box_row: Any, sv: Any, area: Any) -> bool:
    """ROADMAP 2.208: True where the stem `sv` (cell canonical px) has its CENTRE in the page-px `area` (2.205's tier-0 rule for a stroke), mapped through the head box's own
    two frames (its canonical box and its `bbox_page_px`). The clef slot claim owns every stroke in it (2.205's tier 0), so a "stem" the
    line finder drew on the clef's own curl is the clef's ink, not a note's stem."""
    v, bp = box_row.value, (box_row.detail or {}).get("bbox_page_px")
    if not (isinstance(v, (list, tuple)) and len(v) == 5 and isinstance(bp, (list, tuple)) and len(bp) == 4 and float(v[3]) > 0):
        return False
    k = (float(bp[2]) - float(bp[0])) / float(v[3])
    x0, y0 = float(bp[0]) + (float(sv[0]) - float(v[1])) * k, float(bp[1]) + (float(sv[1]) - float(v[2])) * k
    cx, cy = x0 + float(sv[2]) * k / 2.0, y0 + float(sv[3]) * k / 2.0
    return area[0] <= cx <= area[2] and area[1] <= cy <= area[3]


def _stemmed(ev: Any, box_row: Any, inside: Any = None) -> bool:
    """A stem touches the head. `inside` (ROADMAP 2.208, a clef slot claim's page-px area): a stem whose centre stands in it is the claimant's ink
    and does not count -- the stem finder is blind to claims, the consult is not."""
    v = box_row.value
    cell = ev.subject.at(Kind.CELL)
    if not (isinstance(v, (list, tuple)) and len(v) == 5) or cell is None:
        return False
    hb = tuple(float(x) for x in v[1:5])
    for st in ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell):
        sv = st.value
        if isinstance(sv, (list, tuple)) and len(sv) >= 4 and _geom.stem_touches_head(tuple(float(x) for x in sv[:4]), hb):
            if inside is not None and _stem_inside_claim(box_row, sv, inside):
                continue
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


def consult(ev: Any, box_row: Any, *, head: bool, family: str = "note", rows: Any = None, tail_reads: Any = None) -> Optional[Finding]:
    """REFUSE / NARROW / None for this box (see the module docstring). A missing row declines (rule 8). `family` is "note" (a head or
    a rest: a claim that cannot refuse NARROWS) or "mark" (a flag, an arpeggiato, an arc: only the key signature's NAMED box refuses
    -- those families have no blue reading, so nothing else is consulted). `rows`: the decision's own read of `Q.CLAIMED_AREA`, if it made one.
    `tail_reads`: a callable returning `header.key_tail_reads(ev)` -- the deciding module READS the four verdicts its key tail needs in its own
    body (so its `wants` are visibly live, `inventory --check`); None = the decision declares none of them: the tail's written key is unknown."""
    if not enabled() or box_row is None or ev.subject.at(Kind.STAFF) is None:
        return None
    key = box_row.subject.to_key() if family == "mark" else ev.subject.to_key()
    held = _claims.covering(rows if rows is not None else ev.rows(Q.CLAIMED_AREA, scope=Scope.SELF_AND_ANCESTORS), key)
    if not held:
        return None
    stemmed = _stemmed(ev, box_row) if head else False
    confs = None
    tail_ctx, tail_j = None, None
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
            if e.get("tail") is not None and d.get("part") in ("placed", "none_read") and standing != "READ":
                # 2.187b: a box in the TAIL (a slot the staff did not read) is narrowed only if it could be this staff's own next key
                # accidental -- shape, fixed-order staff step, slot x, written count (`key_object.judge_tail_box`). Else it is LEFT ALONE.
                from .. import key_object as _ko
                from .header import key_tail_context_from
                ti = d.get("tail_info") or {}
                ko_d = d.get("key_object") or {}
                args = (e["tail"], ti.get("slot_cx") or {}, float(ti.get("spacing") or 0.0))
                kw = dict(own=int(ti.get("own") or 0), system_n=int(ti.get("N") or 0))
                # the cheap look first, with NO verdict read: the clef the detector's box names (GATHER's measurement, `clef_measured`), on the
                # loosest run (either type, every slot to 7, any order index, naturals). A box that cannot be an accidental there is left alone
                # WITHOUT reading the clef, slot, part key and labels verdicts: a verdict read puts its whole ancestry in this verdict's basis,
                # and every notehead verdict near the signature would carry it (measured: Litolff's record grew 47-62%).
                tail_j = _ko.judge_tail_box(*args, **dict(kw, system_n=_ko.MAX_SLOTS), written=None, previous=None,
                                            clef=ko_d.get("clef_measured"), loose=True)
                if tail_j["narrow"]:
                    if tail_ctx is None:
                        tail_ctx = key_tail_context_from(tail_reads() if tail_reads is not None else {"staff": None},
                                                         system_count=ko_d.get("system_count"),
                                                         read_shapes=[(q or {}).get("shape") for q in ko_d.get("read_pieces") or ()])
                    tail_j = _ko.judge_tail_box(*args, **kw, written=tail_ctx["written"], previous=tail_ctx["previous"], clef=tail_ctx["clef"])
                if tail_j["narrow"]:
                    narrowing.append((owner, r, 0.0, "key_tail_" + tail_j["why"]))
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
            clef_stemmed = stemmed
            if stemmed and head and d.get("source") == "clef_slot" and isinstance(r.value, (list, tuple)) and len(r.value) == 4:
                clef_stemmed = _stemmed(ev, box_row, inside=r.value)   # 2.208: a stem standing in the clef's slot is the clef's ink
            if clef_stemmed:
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
        if owner in (_claims.OWNER_WORD, _claims.OWNER_BRACKET):
            # ROADMAP 2.221 (flags OMR_CLAIM_WORDS_FIRST / OMR_CLAIM_BRACKETS_FIRST): a READ word (lexicon-accepted, outside the staves) or a
            # bracket / brace rule claims its ink BEFORE the heads (Sean 2026-10-28). A box holding >= INSIDE_SHARE_MIN of its own ink inside
            # the claim does not take it: REFUSED -- but a head a stem stands on is a note (as the meter, rule 8): NARROWED, written blue.
            if standing != "READ":
                continue
            if stemmed:
                narrowing.append((owner, r, margin, owner + "_over_a_stemmed_head"))
            else:
                refusing.append((owner, r, margin, owner + "_read"))
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
                             "right_edge": d0.get("right_edge"), "key_object": d0.get("key_object"), "part": d0.get("part"), "locator_frame": d0.get("locator_frame"), "prior": d0.get("prior"),
                             "holding": [{"owner": o, "row": r.id, "why": w, "margin": round(m, 3)} for o, r, m, w in refusing + narrowing],
                             "entry": (r0.detail or {}).get("boxes_inside", {}).get(key),
                             "tail": ({"context": tail_ctx, "judged": tail_j} if tail_j is not None else None)}}
    return Finding(bool(refusing), owner, used, margin, detail)
