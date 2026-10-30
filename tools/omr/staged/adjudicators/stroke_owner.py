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
        # ROADMAP 2.221: a page-wide claim (a word / dynamic / bracket, filed ONCE on its system, `scope` "system", `cell` None) holds in
        # every cell its area meets
        page_wide = d.get("scope") == "system" and d.get("cell") is None
        if (d.get("cell") != idx and not page_wide) or d.get("unit") != "area" or d.get("standing", "READ") != "READ":
            continue
        owner = str(d.get("owner") or "")
        v = r.value
        if owner not in SO.AREA_OWNERS or not (isinstance(v, (list, tuple)) and len(v) == 4):
            continue
        x0, y0, x1, y1 = (float(t) for t in v)
        if page_wide:
            # a page-wide claim owns a stroke only WHOLLY inside it (+1 px): a stem crossing a word's box keeps its ink
            inside = tuple(o for o, pb in sorted(page.items())
                           if x0 - 1 <= pb[0] and pb[2] <= x1 + 1 and y0 - 1 <= pb[1] and pb[3] <= y1 + 1)
        else:
            inside = tuple(o for o, pb in sorted(page.items()) if x0 <= (pb[0] + pb[2]) / 2.0 <= x1 and y0 <= (pb[1] + pb[3]) / 2.0 <= y1)
        if inside:
            out.append(SO.Claim(r.id, owner, owner, inside, (), r.id, area=True))
    return out


def _arc_claims(ev: Evidence, cell) -> List[SO.Claim]:
    """lane-arcs-claim-1029 (`OMR_ARC_CLAIM`): the strokes of THIS cell that a system arc's claim (ONE row per arc, value `[[cell, ordinal], ...]`,
    filed on the arc's staff) names. Tier 0: the traced curve runs along them, whatever box also stands on them. Reads the flag so the OFF arm of an A/B replay ignores the rows."""
    out: List[SO.Claim] = []
    from .. import arc_claim as _AC
    if not _AC.claim_enabled():          # the OFF arm of an A/B replays the same gathered rows and must not read the claim
        return out
    idx = getattr(cell, "cell", None)
    for r in ev.rows(Q.CLAIMED_AREA, scope=Scope.SELF_AND_ANCESTORS, subject=cell):
        d = r.detail or {}
        if d.get("owner") != "arc" or d.get("unit") != "ink" or not isinstance(r.value, (list, tuple)):
            continue
        mine = tuple(int(p[1]) for p in r.value if isinstance(p, (list, tuple)) and len(p) == 2 and p[0] == idx)
        if mine:
            out.append(SO.Claim(r.id, "arc_trace", "arc", mine, (), r.id, area=True))
    return out


def _found_whole_rests(ev: Evidence, cell, page: Dict[int, Tuple[float, ...]], claims: List[SO.Claim]) -> List[SO.Claim]:
    """ROADMAP 2.230 m1 (flag `OMR_WHOLE_REST_HANGS`): the bar the 2.52 search FOUND a whole rest in (`Q.EMPTY_BAR_REST_SEARCH` found=True --
    the unboxed blob) claims the strokes inside its ink box as a `whole_rest`, exactly as a detector `restWhole` box does, so the stroke
    must fit the block shape and no later reader takes it. Only where no detector box of the cell already stands on the same strokes."""
    if not SO.whole_rest_claims():
        return []
    taken = {o for c in claims if c.family == "whole_rest" for o in c.covers}
    out: List[SO.Claim] = []
    for r in ev.rows(Q.EMPTY_BAR_REST_SEARCH, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        d = r.detail or {}
        pb = d.get("bbox_page_px")
        if not r.value or not (isinstance(pb, (list, tuple)) and len(pb) == 4):
            continue
        x0, y0, x1, y1 = (float(t) for t in pb)
        inside = tuple(o for o, b in sorted(page.items())
                       if x0 <= (b[0] + b[2]) / 2.0 <= x1 and y0 <= (b[1] + b[3]) / 2.0 <= y1 and o not in taken)
        if inside:
            out.append(SO.Claim("found_whole_rest/" + r.id, "whole_rest", "restWhole", inside, (), r.id))
    return out


# ── ROADMAP 2.238 (`OMR_OWNER_SHAPE`, default OFF): the old pair rules' SHAPE evidence, read off their own GATHER rows ───────────────────
#: The measured re-read noise on a verdict's own margin (2.232: ink re-read moves a median 0.0, p95 0.064, 6% over 0.05): a 2.150b
#: "stroke into a head" whose margin is under it is a near-tie, left to the stroke map's own touches.
REREAD_NOISE = 0.05


def _letter_vetoes(ev: Evidence, cell, heads: Dict[str, SO.Claim], rests: Dict[str, SO.Claim]) -> Dict[str, SO.Veto]:
    """Old `on_a_dynamic_letter` (detector letter, `Q.NOTEHEAD_LETTER_INK`, the old test verbatim) and the 2.107 second look
    (`Q.LETTER_LOOK_COVER`, heads and rests): the box's ink is the letter's."""
    from . import notehead_precision as NP
    from . import letter_cover as LC
    out: Dict[str, SO.Veto] = {}
    for r in ev.rows(Q.NOTEHEAD_LETTER_INK, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        k = r.subject.to_key()
        if k not in heads:
            continue
        d = r.detail or {}
        try:
            disc, share, on = float(r.value), float(d["letter_ink_share"]), float(d["head_in_letter"])
        except (TypeError, ValueError, KeyError):
            continue
        if on < NP.DYNAMIC_LETTER_HEAD_ON_MIN:
            continue
        w_sp = d.get("letter_w_spaces")
        if d.get("letter_class") == "dynamicF" and w_sp is not None and float(w_sp) < NP.DYNAMIC_F_MIN_W_SPACES:
            continue
        if disc < NP.DYNAMIC_LETTER_STROKE_DISC_SPACES or share >= NP.DYNAMIC_LETTER_BODY_SHARE:
            out[k] = SO.Veto("on_a_dynamic_letter", str(d.get("letter") or r.id), "dynamic", str(d.get("letter_class") or ""), r.id)
    for r in ev.rows(Q.LETTER_LOOK_COVER, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        k = r.subject.to_key()
        if (k not in heads and k not in rests) or k in out:
            continue
        try:
            share = float(r.value)
        except (TypeError, ValueError):
            continue
        if LC.refuses(share):
            letters = (r.detail or {}).get("letters") or ()
            out[k] = SO.Veto("letter_look_cover", str(letters[0]) if letters else r.id, "dynamic", "letter_look", r.id)
    return out


def _rest_shape_vetoes(ev: Evidence, cell, heads: Dict[str, SO.Claim]) -> Dict[str, SO.Veto]:
    """Old `is_a_rest_shape` (2.145): `head_rest_shape.read_head_ink` on the cell's `Q.UNBOXED_REST_SHAPE` clusters (GATHER) reads the
    head box's ink as an eighth / quarter rest; the cluster is the rival."""
    from . import head_rest_shape as HRS
    if not HRS.enabled():
        return {}
    clusters = ev.rows(Q.UNBOXED_REST_SHAPE, scope=Scope.SELF_AND_DESCENDANTS, subject=cell)
    if not clusters:
        return {}
    # `read_head_ink` reads the cell's stems (a rest owns none) and rest boxes (2.142's): declared here, read here
    _ = (ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell), ev.rows(Q.REST, scope=Scope.SELF_AND_DESCENDANTS, subject=cell))
    out: Dict[str, SO.Veto] = {}
    for b in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        k = b.subject.to_key()
        if k not in heads:
            continue
        got = HRS.read_head_ink(ev, cell, b, clusters)
        if got is not None:
            out[k] = SO.Veto("is_a_rest_shape", got.cluster.subject.to_key(), "rest", "rest_shape:" + str(got.value), got.cluster.id)
    return out


def _rest_into_head_vetoes(ev: Evidence, cell, rests: Dict[str, SO.Claim]) -> Dict[str, SO.Veto]:
    """Old `rest_stroke_into_a_head` (2.150b): `Q.REST_INK_CONTACT` (GATHER) past the old cuts by at least the re-read noise. No rival: the
    stroke is a note's stem, the consumers' to read."""
    from . import family_precision as FP
    from .. import rest_ink as _rest_ink
    if not _rest_ink.enabled():
        return {}
    out: Dict[str, SO.Veto] = {}
    for r in ev.rows(Q.REST_INK_CONTACT, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        k = r.subject.to_key()
        d = r.detail if isinstance(r.detail, dict) else {}
        if k not in rests or "thin_run_sp" not in d:
            continue
        m_stroke = float(d["thin_run_sp"]) / FP.REST_STROKE_MIN_SP - 1.0
        m_blob = float(d.get("blob_sp") or 0.0) / FP.REST_HEAD_BLOB_MIN_SP - 1.0
        m_ink = float(d.get("head_ink_sp2") or 0.0) / FP.REST_HEAD_INK_MIN_SP2 - 1.0
        if min(m_stroke, max(m_blob, m_ink)) >= REREAD_NOISE:
            out[k] = SO.Veto("rest_stroke_into_a_head", row_id=r.id)
    return out


def _acc_on_rest_vetoes(ev: Evidence, cell, accs: Dict[str, SO.Claim], rests: Dict[str, SO.Claim],
                        boxes: Dict[str, Tuple[str, Tuple[float, float, float, float]]]) -> Dict[str, SO.Veto]:
    """Old accidental `on_a_rest` (2.192): a double-sharp / double-flat box at IoU >= `ON_REST_IOU` with a rest box whose 2.190 corner shape
    (`Q.ACCIDENTAL_STAFF_POSITION` detail `shape`, GATHER) is not its class's family. The rest must have a clear rest piece (own_strokes)."""
    from .. import accidental_shape as AS
    from .. import one_ink as OI
    if not AS.on_rest_enabled():
        return {}
    out: Dict[str, SO.Veto] = {}
    for r in ev.rows(Q.ACCIDENTAL_STAFF_POSITION, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        k = r.subject.to_key()
        if k not in accs or k not in boxes:
            continue
        cls, mine = boxes[k]
        if cls.lower() not in AS.ON_REST_CLASSES:
            continue
        best = None
        for rk in sorted(rests):
            if rk in boxes:
                ov = OI.iou(mine, boxes[rk][1])
                if ov >= AS.ON_REST_IOU and (best is None or ov > best[0]):
                    best = (ov, rk)
        if best is None:
            continue
        srow = (r.detail or {}).get("shape")
        srow = srow if isinstance(srow, dict) else {}
        sh = AS.classify(srow if srow.get("bl") is not None else None)
        if not AS.on_rest_verdict(cls, sh)["keep"]:
            out[k] = SO.Veto("acc_on_a_rest", best[1], "rest", boxes[best[1]][0], r.id, rival_must_be_clear=True)
    return out


def shape_vetoes(ev: Evidence, cell, inks: List[SO.Ink], claims: List[SO.Claim]) -> Dict[str, SO.Veto]:
    """Every 2.238 veto of this cell, first rule first (one per box)."""
    heads = {c.key: c for c in claims if c.family == "head" and not c.area}
    rests = {c.key: c for c in claims if c.family == "rest" and not c.area}
    accs = {c.key: c for c in claims if c.family == "accidental" and not c.area}
    boxes: Dict[str, Tuple[str, Tuple[float, float, float, float]]] = {}
    for b in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        v = b.value
        if isinstance(v, (list, tuple)) and len(v) == 5:
            boxes[b.subject.to_key()] = (str(v[0]), tuple(float(t) for t in v[1:5]))
    out: Dict[str, SO.Veto] = {}
    for part in (_letter_vetoes(ev, cell, heads, rests), _rest_shape_vetoes(ev, cell, heads), _rest_into_head_vetoes(ev, cell, rests),
                 _acc_on_rest_vetoes(ev, cell, accs, rests, boxes), SO.structural_vetoes(inks, claims)):
        for k, v in part.items():
            out.setdefault(k, v)
    return out


@decision(
    quantity=Q.STROKE_OWNER,
    scope=Kind.CELL,
    # GATHER rows only (the strokes, the boxes and what each stands on, the register's areas): it needs no verdict, so it stands ahead of
    # every precision rule and every consumer (adjudicate.ORDER). 2.238 (`OMR_OWNER_SHAPE`): the old pair rules' own GATHER rows -- the
    # letter ink, the second look's cover, the rest-shaped clusters (+ the stems and rest boxes `read_head_ink` reads), the rest's ink
    # contact, the accidental's corner shape.
    wants=(Q.STROKE, Q.GLYPH_STROKES, Q.GLYPH_BOX, Q.CLAIMED_AREA, Q.EMPTY_BAR_REST_SEARCH,
           Q.NOTEHEAD_LETTER_INK, Q.LETTER_LOOK_COVER, Q.UNBOXED_REST_SHAPE, Q.STEM, Q.REST, Q.REST_INK_CONTACT,
           Q.ACCIDENTAL_STAFF_POSITION),
    subjects_from=Q.STROKE,
    reasons=("strokes_owned", "some_strokes_contested", "no_claimant", "no_strokes"),
    mode=Mode.ADDITIVE,
    composed_from=(Q.STROKE, Q.GLYPH_STROKES, Q.GLYPH_BOX, Q.CLAIMED_AREA, Q.EMPTY_BAR_REST_SEARCH,
                   Q.NOTEHEAD_LETTER_INK, Q.LETTER_LOOK_COVER, Q.UNBOXED_REST_SHAPE, Q.STEM, Q.REST, Q.REST_INK_CONTACT,
                   Q.ACCIDENTAL_STAFF_POSITION),
)
def adjudicate_stroke_owner(ev: Evidence) -> Ruling:
    """Which mark owns each stroke of this cell (module doc; the rule is `stroke_owner.own_strokes`)."""
    cell = ev.subject
    inks, page = _inks(ev.rows(Q.STROKE, scope=Scope.SELF_AND_DESCENDANTS, subject=cell))
    if not inks:
        return Ruling.abstain("no_strokes")
    claims = _claims(ev, cell)
    claims += _areas(ev, cell, page)
    arc_claims = _arc_claims(ev, cell)
    claims += arc_claims
    claims += _found_whole_rests(ev, cell, page, claims)
    from .rhythm import beams_from_strokes_enabled
    shaped = SO.owner_shape_enabled()
    vetoes = shape_vetoes(ev, cell, inks, claims) if shaped else None
    owned = SO.own_strokes(inks, claims, tiers=SO.TIERS, acc_bar_clear_of_note=beams_from_strokes_enabled(),   # 2.202f
                           vetoes=vetoes)
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
    box_owns: List[str] = []
    for c in claims:
        if c.area or c.family not in ("head", "rest", "accidental", "whole_rest"):
            continue
        bv = SO.box_verdict(c, owned, by_ord)
        if bv["verdict"] in ("refused", "contested"):
            boxes[c.key] = [bv["verdict"], [list(x) for x in bv["lost"]]]
        elif bv["verdict"] == "owns":
            box_owns.append(c.key)
    value = {"owned": sorted(o for o, w in owned.items() if w.state in ("decided", "merged")),
             "contested": sorted(o for o, w in owned.items() if w.state == "contested")}
    detail = {"strokes": strokes, "boxes": boxes, "census": SO.census(owned)}
    if shaped:
        # 2.238: which boxes own their ink (the precision rules' `owns`; flag OFF keeps the 2.205 detail byte-identical) and every veto
        detail["box_owns"] = sorted(box_owns)
        detail["vetoes"] = {k: [v.rule, v.rival_key, v.rival_family, v.row_id] for k, v in sorted((vetoes or {}).items())}
        used.extend(v.row_id for v in (vetoes or {}).values() if v.row_id)
    if arc_claims:
        # what the arc claim REFUSED, by kind: for each stroke the arc owns, the other families that also stood on it (a detector box of that
        # family claimed it) and the stroke's own kind (a horizontal / curve one is what a beam or hook reader would have taken)
        cen = detail["census"]
        for o, w in owned.items():
            if w.family != "arc_trace":
                continue
            cen["arc_claim:strokes"] = cen.get("arc_claim:strokes", 0) + 1
            cen["arc_claim:kind:" + by_ord[o].kind] = cen.get("arc_claim:kind:" + by_ord[o].kind, 0) + 1
            rivals = {c["family"] for c in w.candidates if c["family"] != "arc_trace"}
            if not rivals:
                cen["arc_claim:no_other_claimant"] = cen.get("arc_claim:no_other_claimant", 0) + 1
            for f in rivals:
                cen["arc_claim:from:" + str(f)] = cen.get("arc_claim:from:" + str(f), 0) + 1
    used_t = tuple(dict.fromkeys(u for u in used if u))
    if not strokes:
        return Ruling(value=value, reason="no_claimant", used=used_t, detail=detail)
    if value["contested"]:
        return Ruling(value=value, reason="some_strokes_contested", used=used_t, detail=detail)
    return Ruling(value=value, reason="strokes_owned", used=used_t, detail=detail)


#: the owner families whose claim is the REGISTER's (an area / page-wide claim): a box refused only by them is the register's to refuse
#: (`claimed_by.consult`), not the 2.238 consult's
REGISTER_FAMILIES = frozenset(SO.AREA_OWNERS) | {"whole_rest"}


def box_says(ev: Evidence, box_key: str) -> Tuple[str, Any, str]:
    """ROADMAP 2.238 (`OMR_OWNER_SHAPE`): what the reworked owner says of ONE head / rest / accidental box, for the precision rules:
    `("owns", None)`, `("refused", lost)` (its ink is another mark's, or not its class's shape, and not ONLY the register's), `("contested",
    lost)`, or `("silent", None)` (flag off, no verdict, no ink the owner can speak for, or refused by the register alone); third, the
    cell's `Q.STROKE_OWNER` verdict id (the decision's `used`)."""
    if not SO.owner_shape_enabled():
        return "silent", None, ""
    cell = ev.subject.at(Kind.CELL)
    v = ev.verdict(Q.STROKE_OWNER, subject=cell) if cell is not None else None
    d = getattr(v, "detail", None) or {}
    if "box_owns" not in d:
        return "silent", None, ""
    vid = str(getattr(v, "id", "") or "")
    if box_key in set(d.get("box_owns") or ()):
        return "owns", None, vid
    b = (d.get("boxes") or {}).get(box_key)
    if not b:
        return "silent", None, vid
    verdict, lost = b[0], b[1]
    if verdict == "refused":
        # Only a refusal the MOVED evidence made decides (the box carries a 2.238 veto). The 2.205 per-stroke fit alone refused 31 / 39
        # heads main keeps on the frozen sample, one of them a quarter Sean judged (Brahms glyph/5/0/2/3/2, "4"): it is no box-level shape
        # test, so it stays silent and the old rules decide (FINDINGS 2.238).
        if box_key not in (d.get("vetoes") or {}):
            return "silent", None, vid
        fams = {str(x[2]) for x in lost if x[1] in ("decided", "merged")}
        if fams and fams <= REGISTER_FAMILIES and not any(x[1] == "refused_claims" for x in lost):
            return "silent", None, vid
        return "refused", lost, vid
    return "contested", lost, vid


def veto_rule(ev: Evidence, box_key: str) -> str:
    """The 2.238 veto rule the owner applied to this box ("" none / flag off): a refusal the old rule's own consumer reads by its reason
    (2.145's rest written at the cluster reads `is_a_rest_shape`) is given that reason by the old rule, not `owner_refused`."""
    if not SO.owner_shape_enabled():
        return ""
    cell = ev.subject.at(Kind.CELL)
    v = ev.verdict(Q.STROKE_OWNER, subject=cell) if cell is not None else None
    e = ((getattr(v, "detail", None) or {}).get("vetoes") or {}).get(box_key)
    return str(e[0]) if e else ""


def masked(verdict) -> Dict[int, str]:
    """`{ordinal: "owned" | "contested"}` from a cell's `Q.STROKE_OWNER` verdict (None, abstained or flag off: `{}`). For the consumers."""
    if not enabled() or verdict is None or not isinstance(getattr(verdict, "value", None), dict):
        return {}
    v = verdict.value
    out = {int(o): "owned" for o in v.get("owned") or ()}
    out.update({int(o): "contested" for o in v.get("contested") or ()})
    return out
