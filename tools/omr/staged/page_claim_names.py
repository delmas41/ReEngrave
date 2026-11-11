"""ROADMAP 2.269 step 1 -- THE PAGE-WIDE CLAIMS NAME THEIR PAGE STROKES, ONCE (STAGED GATHER; flag `OMR_PAGE_CLAIM_NAMES`, default OFF).

    docs/plan-2026-11-04-page-claims.md §3, §4 "Step 1"; CLAUDE §3 claim order ("a later reader may mark claimed ink but never take it").

CAUSE. The claims were built before the page map: their ids are cell ordinals or area boxes, so a reader standing on the page map cannot ask "whose is
this stroke?". M3 translated ARCS only; M4a's crops then showed a C clef, a ledger, "cresc." and a staff-line residue filed as beams. LESSON: when a
new frame arrives, every claim that sits before the new reader is re-expressed in that frame first.

WHAT. One translation, once per page, right after `gather_page_claims`: each claim that already stands on the log is expressed as the PAGE strokes it
owns --

  * an AREA claim (barline, bracket / brace / leading column, clef, key signature, meter, word / dynamic): the SAME predicate `adjudicators/stroke_owner.
    _areas` applies to a cell's strokes, applied to the page strokes' boxes -- a page-wide claim (`scope` "system", no cell: a word, a bracket) owns a
    stroke only WHOLLY inside it (+1 px); a cell claim owns a stroke whose CENTRE is inside it. No pixel is read.
    A barline claim also names the carved `barline` stroke through its column (`StrokeIndex.rule_through`): M1 carves ONE stroke per column, the
    height of the whole system, so the centre rule -- right for every other mark, whose stroke the claim's area holds -- can never name it.
  * a CV HAIRPIN read (`Q.WEDGE_BOX`, `reach`): the page strokes at least `hairpin_reach.ON_ARMS_SHARE_MIN` along its two arms -- the page-frame call of the
    cell claim's own share (`arc_claim.page_strokes_along` does the same for arcs). The 2.261 beam guard is upstream: a find standing on a stem at each end
    never becomes a reach read, so it names nothing here.
  * an ARC claim already carries its page ids (M3, `page_strokes` on its `unit: ink` row); they take part in the order, they are not filed again.

THE ORDER is `claim_order.LAYERS` (barline / bracket, then clef / key / meter, then word / dynamic, then arc / hairpin), within a layer the order the rows
stand on the log; FIRST CLAIM WINS. A later claim on a named stroke is recorded CONTESTED on its own row (`contested`: [[stroke, holder owner]]), never
taken. The same owner naming a stroke again (a barline is claimed by the cell on each side of it) is a TWIN, counted, not a contest.

WHAT IT FILES. One `Q.CLAIMED_AREA` row per claim that wins at least one stroke, on the source row's subject: value = the page stroke ordinals,
`detail`: `owner`, `owner_row` (the source row), `unit` "page_ink", `frame` page, `source` "page_names", `page_strokes` (the same ids: `page_beams` reads
claimed ink from that field), `contested`. A census row (unit "page_ink_census") says how many claims named nothing, by owner. WHY `page_ink` AND NOT
`ink` (the plan's word): `claims.covering` and `stem_end_heads.claims_holding` read EVERY `unit: ink` row as `[[cell, ordinal]]` / cell ordinals of the
box's own cell; ids of the page map in that field would be taken for ordinals of a cell. Only `stroke_owner._arc_claims` / `_hairpin_claims` are meant to
read `ink`, and they read their own owners; a distinct unit is the companion the plan asks for, and every existing reader filters on `unit`.

It reads NO raster, never maps a cell ordinal to a page id, and decides nothing: NOTHING READS THESE ROWS but `page_beams` (file-only, M4a), so the exported
file is byte-identical with the flag on (the proof is the lane gate).

COST (the 2.262 lesson: pieces x boxes explodes page-wide). The strokes are sorted by left edge and by centre x once; a claim finds its candidates by
bisect and tests the cheap box predicate on them. The hairpin share, the only mask test, runs after a bounding-box test on the few strokes near the arms.

CONVENTION ASSUMED: the register's own predicates (`stroke_owner._areas`) say which ink an area owns; the page map's strokes are the units. WHAT WOULD
FALSIFY IT: a page stroke the claim names that is another mark's (a stem crossing a word is NOT named: wholly-inside leaves it unnamed, as in `_areas`).
NOT CONFIRMED beyond the two plates.
"""
from __future__ import annotations

import bisect
import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

DERIVED_CHECK = False
ENV = "OMR_PAGE_CLAIM_NAMES"
SOURCE = "page_names"
UNIT = "page_ink"
UNIT_CENSUS = "page_ink_census"
#: a page-wide claim owns a stroke only wholly inside it, this many px of slack (`adjudicators/stroke_owner._areas`: "+1 px")
WHOLLY_INSIDE_SLACK_PX = 1.0
#: the page map's kind for a carved barline column (`page_strokes.carve_columns`)
BARLINE_KIND = "barline"


def enabled() -> bool:
    """`OMR_PAGE_CLAIM_NAMES` (ROADMAP 2.269 step 1), default OFF: allow-list, so an empty value or a typo cannot switch a document onto an unpriced change."""
    return os.environ.get(ENV, "0").strip().lower() in ("1", "true", "yes", "on")


# ───────────────────────────── the pure core ─────────────────────────────

class StrokeIndex:
    """Page-stroke boxes `(x0, y0, x1, y1)` sorted twice: by left edge (wholly-inside claims) and by centre x (centre-rule claims). A claim's
    candidates come by bisect on one of them; the other edges are the cheap box test. No stroke is visited that cannot qualify on x."""

    def __init__(self, boxes: Sequence[Sequence[float]], kinds: Optional[Sequence[str]] = None):
        self.boxes = [tuple(float(v) for v in b[:4]) for b in boxes]
        self.kinds = list(kinds) if kinds is not None else [""] * len(self.boxes)
        self.by_left = sorted(range(len(self.boxes)), key=lambda i: self.boxes[i][0])
        self.left_keys = [self.boxes[i][0] for i in self.by_left]
        self.by_centre = sorted(range(len(self.boxes)), key=lambda i: self.boxes[i][0] + self.boxes[i][2])
        self.centre_keys = [self.boxes[i][0] + self.boxes[i][2] for i in self.by_centre]     # 2 x centre x: no division

    def wholly_inside(self, area: Sequence[float], slack: float = WHOLLY_INSIDE_SLACK_PX) -> List[int]:
        """`stroke_owner._areas`, page-wide branch: `x0 - 1 <= bx0 and bx1 <= x1 + 1 and y0 - 1 <= by0 and by1 <= y1 + 1`."""
        x0, y0, x1, y1 = (float(v) for v in area)
        lo = bisect.bisect_left(self.left_keys, x0 - slack)
        hi = bisect.bisect_right(self.left_keys, x1 + slack)
        out = []
        for k in range(lo, hi):
            i = self.by_left[k]
            b = self.boxes[i]
            if b[2] <= x1 + slack and y0 - slack <= b[1] and b[3] <= y1 + slack:
                out.append(i)
        return sorted(out)

    def centre_in(self, area: Sequence[float]) -> List[int]:
        """`stroke_owner._areas`, cell branch: `x0 <= cx <= x1 and y0 <= cy <= y1`."""
        x0, y0, x1, y1 = (float(v) for v in area)
        lo = bisect.bisect_left(self.centre_keys, 2.0 * x0)
        hi = bisect.bisect_right(self.centre_keys, 2.0 * x1)
        out = []
        for k in range(lo, hi):
            i = self.by_centre[k]
            b = self.boxes[i]
            if y0 <= (b[1] + b[3]) / 2.0 <= y1:
                out.append(i)
        return sorted(out)

    def rule_through(self, area: Sequence[float], slack: float = WHOLLY_INSIDE_SLACK_PX) -> List[int]:
        """The carved `barline` strokes (M1: ONE stroke per barline column, the height of the whole system) that run through a barline claim's column:
        the stroke lies within the claim's x band (+ slack) and crosses its y range. The centre rule cannot name them -- a stroke that spans every
        staff of the system has its centre in at most one staff's area -- and the claim IS the column the stroke was carved from."""
        x0, y0, x1, y1 = (float(v) for v in area)
        lo = bisect.bisect_left(self.left_keys, x0 - slack)
        hi = bisect.bisect_right(self.left_keys, x1 + slack)
        out = []
        for k in range(lo, hi):
            i = self.by_left[k]
            b = self.boxes[i]
            if self.kinds[i] == BARLINE_KIND and b[2] <= x1 + slack and b[1] <= y1 and b[3] >= y0:
                out.append(i)
        return sorted(out)

    def meeting(self, box: Sequence[float], grow: float = 0.0) -> List[int]:
        """Strokes whose box meets `box` grown by `grow` (the cheap test before a mask test)."""
        x0, y0, x1, y1 = box[0] - grow, box[1] - grow, box[2] + grow, box[3] + grow
        hi = bisect.bisect_right(self.left_keys, x1)
        out = []
        for k in range(hi):
            i = self.by_left[k]
            b = self.boxes[i]
            if b[2] >= x0 and b[3] >= y0 and b[1] <= y1:
                out.append(i)
        return sorted(out)


def area_names(index: StrokeIndex, rect: Sequence[float], page_wide: bool, owner: str = "") -> List[int]:
    """The page strokes an AREA claim owns: the register's own predicate (module doc); a barline claim also names the carved rule through its column
    (`StrokeIndex.rule_through`: the one place the page map's unit, a system-tall stroke, is not the claim's, a staff-high area)."""
    got = index.wholly_inside(rect) if page_wide else index.centre_in(rect)
    if owner == "barline":
        got = sorted(set(got) | set(index.rule_through(rect)))
    return got


def settle(claims: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply the order. Each claim: `{"owner", "layer", "ids", "existing" (bool: already filed, e.g. an arc), "row" (anything)}`, in the order the rows stand.
    FIRST CLAIM WINS by (layer, position). Returns `{"claims": [... + "won", "contested", "twins"], "named": {stroke: owner}, "double": n}` where
    `double` counts strokes named by two DIFFERENT owners. A stroke named again by the SAME owner is a twin (counted on the claim), never a contest."""
    order = sorted(range(len(claims)), key=lambda k: (int(claims[k].get("layer", 99)), k))
    named: Dict[int, int] = {}
    out: List[Dict[str, Any]] = [dict(c, won=[], contested=[], twins=0) for c in claims]
    double = set()
    for k in order:
        c = out[k]
        for i in sorted(set(int(x) for x in c.get("ids") or ())):
            h = named.get(i)
            if h is None:
                named[i] = k
                c["won"].append(i)
            elif out[h]["owner"] == c["owner"]:
                c["twins"] += 1
            else:
                c["contested"].append([i, out[h]["owner"]])
                double.add(i)
    return dict(claims=out, named={i: out[k]["owner"] for i, k in named.items()}, double=len(double))


# ───────────────────────────── the page, as rows ─────────────────────────────

def _boxes_of(page_map: Any) -> Tuple[List[Tuple[float, float, float, float]], List[str]]:
    """Page-stroke boxes as `(x0, y0, x1, y1)` and their kinds, in the ordinals `Q.PAGE_STROKE` files: the map's strokes (it keeps `(x, y, w, h)`), then the
    carved barline rules (`page_map.barlines`, `box` already `(x0, y0, x1, y1)`), which `gather_page_strokes` numbers after the strokes."""
    out, kinds = [], []
    for st in page_map.strokes:
        x, y, w, h = (float(v) for v in st.box)
        out.append((x, y, x + w, y + h))
        kinds.append(str(getattr(st, "kind", "")))
    for b in getattr(page_map, "barlines", None) or ():
        out.append(tuple(float(v) for v in b["box"][:4]))
        kinds.append(BARLINE_KIND)
    return out, kinds


def gather_page_claim_names(log: Any, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], page_map: Any, *,
                            progress: bool = False) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.269 step 1 (flag `OMR_PAGE_CLAIM_NAMES`, default OFF), STAGED GATHER: the page-wide claims named on the page map's strokes (module doc).
    AFTER `gather_page_claims` (every area claim stands on the log) and the page map; reads rows and the in-memory map only. Returns the census."""
    if not enabled():
        return None
    from . import record as R
    from .record import Q, READERS, ABSTAIN, Scope
    from . import claim_order as CO
    from . import hairpin_reach as HR
    from . import stroke_owner as SO
    p = int(getattr(pws.page, "page_index", 0))
    page_sub = R.page(p)
    if page_map is None or not getattr(page_map, "strokes", None):
        log.abstain(page_sub, Q.CLAIMED_AREA, reader=READERS.CV_CLAIMED_REGISTER, frame="page", reason=ABSTAIN.NO_MASK, owner="page_names",
                    unit=UNIT_CENSUS, why="no_page_stroke_map", source=SOURCE)
        return None
    t0 = time.time()
    index = StrokeIndex(*_boxes_of(page_map))
    claims: List[Dict[str, Any]] = []
    census: Dict[str, Any] = dict(strokes=len(page_map.strokes), barline_rules=len(index.boxes) - len(page_map.strokes), area_claims=0, hairpin_reads=0, arc_claims=0, named_nothing={}, by_owner={})

    def _layer(owner: str) -> int:
        lay = CO.layer_of(owner)
        return 99 if lay is None else int(lay)

    for r in log.rows(Q.CLAIMED_AREA, page_sub, scope=Scope.SELF_AND_DESCENDANTS):
        d = r.detail or {}
        owner = str(d.get("owner") or "")
        unit = d.get("unit")
        if unit == "area":
            v = r.value
            if d.get("standing", "READ") != "READ" or owner not in SO.AREA_OWNERS or not (isinstance(v, (list, tuple)) and len(v) == 4):
                continue
            page_wide = d.get("scope") == "system" and d.get("cell") is None
            census["area_claims"] += 1
            claims.append(dict(owner=owner, layer=_layer(owner), ids=area_names(index, v, page_wide, owner), existing=False, row=r.id, subject=r.subject,
                               how="wholly_inside" if page_wide else "centre", page_wide=page_wide))
        elif unit == "ink" and d.get("page_strokes"):
            census["arc_claims"] += 1
            claims.append(dict(owner=owner, layer=_layer(owner), ids=[int(o) for o in d["page_strokes"]], existing=True, row=r.id, subject=r.subject,
                               how="filed_by_the_claim"))
    if HR.enabled():
        for r in log.rows(Q.WEDGE_BOX, page_sub, scope=Scope.SELF_AND_DESCENDANTS):
            d = r.detail or {}
            bb = d.get("bbox_page_px")
            if r.reader != READERS.CV_HAIRPINS or not d.get("reach") or not (isinstance(bb, (list, tuple)) and len(bb) == 4):
                continue
            census["hairpin_reads"] += 1
            segs = HR.arms(r.value, bb)
            band = HR.band_px(d.get("staff_spacing_px") or 0.0)
            ids = []
            for i in index.meeting([float(v) for v in bb], band):
                if i >= len(page_map.masks):          # a carved barline rule has no mask here
                    continue
                m, x0, y0 = page_map.masks[i]
                if getattr(m, "size", 0) == 0:
                    continue
                if HR.on_arms_share(m, x0, y0, page_map.scale, (0, 0, 0, 0), 1.0, segs, bb, band) >= HR.ON_ARMS_SHARE_MIN:
                    ids.append(i)
            claims.append(dict(owner=HR.OWNER, layer=_layer(HR.OWNER), ids=ids, existing=False, row=r.id, subject=r.subject, how="on_arms"))
    res = settle(claims)
    filed = 0
    for c in res["claims"]:
        census["by_owner"].setdefault(c["owner"], dict(claims=0, strokes=0, contested=0, twins=0))
        o = census["by_owner"][c["owner"]]
        o["claims"] += 1
        o["strokes"] += len(c["won"])
        o["contested"] += len(c["contested"])
        o["twins"] += c["twins"]
        if c["existing"]:
            continue
        if not c["won"]:
            if not c["ids"]:
                census["named_nothing"][c["owner"]] = census["named_nothing"].get(c["owner"], 0) + 1
            continue
        filed += 1
        log.observe(c["subject"], Q.CLAIMED_AREA, list(c["won"]), reader=READERS.CV_CLAIMED_REGISTER, frame="page", owner=c["owner"],
                    owner_row=c["row"], owner_glyph=None, unit=UNIT, standing="READ", source=SOURCE, how=c["how"], page_strokes=list(c["won"]),
                    contested=c["contested"])
    rules = [i for i, k in enumerate(index.kinds) if k == BARLINE_KIND]
    census.update(rows=filed, named=len(res["named"]), double_named=res["double"], rule_strokes=len(rules),
                  rule_strokes_named=sum(1 for i in rules if i in res["named"]), seconds=round(time.time() - t0, 3))
    log.observe(page_sub, Q.CLAIMED_AREA, "census", reader=READERS.CV_CLAIMED_REGISTER, frame="page", owner="page_names", unit=UNIT_CENSUS,
                standing="READ", source=SOURCE, **census)
    if progress:
        print("  gather page claim names p%s: %s" % (p, census))
    return dict(census, named_by=res["named"])


# ───────────────────────────── step 3: boxed marks, by ink share (ROADMAP 2.269 step 3) ─────────────────────────────

ENV_BOXES = "OMR_PAGE_CLAIM_BOXES"
SOURCE_BOXES = "page_boxes"
#: the detector classes step 3 names page strokes for, by the owner (claim-order family) they claim as. Ledgers and hollow-head ink are NOT here:
#: ROADMAP 2.260e M6 (`page_heads`) reads and claims every notehead and ledger stub on the page (manager, 2026-11-05).
BOX_FAMILIES = ("dynamic", "whole_rest")
BOX_CLASSES = ("repeatdot",)          # a `dot`-family class named by itself: the repeat dot, never an augmentation dot (a different mark, M6/rhythm's)


def boxes_enabled() -> bool:
    """`OMR_PAGE_CLAIM_BOXES` (ROADMAP 2.269 step 3), default OFF: allow-list, so an empty value or a typo cannot switch a document onto an unpriced change."""
    return os.environ.get(ENV_BOXES, "0").strip().lower() in ("1", "true", "yes", "on")


ENV_RESTS = "OMR_PAGE_CLAIM_RESTS"
#: ROADMAP 2.288 (flag `OMR_PAGE_CLAIM_RESTS`, default OFF): the REST families, switched on alone (never with the dynamics / repeat dots `OMR_PAGE_CLAIM_BOXES` names).
REST_FAMILIES = ("rest", "whole_rest")


def rests_enabled() -> bool:
    """`OMR_PAGE_CLAIM_RESTS` (ROADMAP 2.288), default OFF: allow-list, so an empty value or a typo cannot switch a document onto an unpriced change."""
    return os.environ.get(ENV_RESTS, "0").strip().lower() in ("1", "true", "yes", "on")


def box_owner(cls: str, category: Optional[str] = None, rests: bool = False) -> Optional[str]:
    """The claim-order owner a detector class names strokes as (module doc above); None = not step 3's. `rests`: the REST families are step 3's too
    (`OMR_PAGE_CLAIM_RESTS`, 2.288), and then ONLY they are, unless `OMR_PAGE_CLAIM_BOXES` is on as well (the caller passes `rests` and filters by `boxes_enabled()`)."""
    from . import stroke_owner as SO
    lc = str(cls or "").lower()
    if lc in BOX_CLASSES:
        return "dot"
    fam = SO.family_of(cls, category)
    return fam if (fam in BOX_FAMILIES or (rests and fam in REST_FAMILIES)) else None


def _contact_standing(detail: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    """The round-1 standing, off `Q.REST_INK_CONTACT` alone (the cell raster): kept as the second witness and the fallback where the page strokes cannot be read."""
    from .adjudicators import family_precision as FP
    if not isinstance(detail, dict) or "thin_run_sp" not in detail:
        return "weak", "no_ink_contact_row"
    m_stroke = float(detail["thin_run_sp"]) / FP.REST_STROKE_MIN_SP - 1.0
    m_blob = float(detail.get("blob_sp") or 0.0) / FP.REST_HEAD_BLOB_MIN_SP - 1.0
    m_ink = float(detail.get("head_ink_sp2") or 0.0) / FP.REST_HEAD_INK_MIN_SP2 - 1.0
    if min(m_stroke, max(m_blob, m_ink)) >= 0:
        return "weak", "stroke_into_a_head"
    if m_stroke >= 0:
        return "weak", "stem_like_stroke"          # a long thin stroke with no head found on it by the cell raster
    return "READ", "stands_free"


# 2.288 r4: the two questions any reader of the stroke map asks of ink -- WHAT DOES IT HANG FROM, WHICH SIDE OF ITS STAFF LINE -- live in `ink_attachment` (shared); the rest
# reader is the first caller. The old names stay as aliases (tests, tile scripts).
from . import ink_attachment as IA

_head_shaped = IA.head_shaped
_neighbours = IA.neighbours
rest_attachment = IA.attachment


def rest_standing(detail: Optional[Dict[str, Any]], attachment: Optional[Dict[str, Any]] = None, sides: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    """`("READ" | "weak", why)`: does a detector rest box STAND as a rest (ROADMAP 2.288)? Round 2: the question is attachment, not a stroke length. With the page
    strokes read (`attachment` from `rest_attachment`): a box whose ink hangs from a stem carrying a head, touches a head, or is a bare vertical is `weak`
    (a flag, a stem, a flat's vertical); otherwise it stands free and is READ -- unless the cell raster's own ink contact (`Q.REST_INK_CONTACT`, 2.150b, a second
    witness off a different raster) says the stroke runs into a head, or has no measurement (rule 8: "cannot tell" never becomes READ). A thin stroke of a rest's length
    is NOT a reason by itself any more (round 1's `stem_like_stroke` weakened 252 of 276 free-standing eighth rests on Brahms p19/p14; what it still caught there was a
    barline's sliver boxed as a quarter rest: no page stroke to stand on, `names_no_stroke`). A box that names no page stroke has no ink to claim: weak. A WEAK box files
    no claim, so it blocks nobody (the caller counts them). Pure."""
    old = _contact_standing(detail)
    if attachment is None:
        return "weak", "names_no_stroke"
    if attachment.get("stem_with_head"):
        return "weak", "hangs_from_a_stem_with_a_head"
    if attachment.get("touches_a_head"):
        return "weak", "touches_a_head"
    if attachment.get("bare_stroke"):
        return "weak", "bare_vertical_stroke"
    if sides and sides.get("two_lines"):
        return "weak", "touches_two_staff_lines"          # a block rest never touches two lines (Sean 2026-09-29); `ink_attachment.line_sides`
    if sides and sides.get("both_sides"):
        return "weak", "ink_on_both_sides_of_its_line"    # a whole rest hangs from a line, a half rest sits on one: a head is centred on it (2.288 r4, tile 4)
    if old[1] in ("no_ink_contact_row", "stroke_into_a_head"):
        return old
    return "READ", "stands_free"


def strokes_by_share(page_map: Any, box: Sequence[float], index: StrokeIndex, share_min: float) -> List[int]:
    """The page strokes with at least `share_min` of their ink inside `box` (page px): a bounding-box test on the index first (cheap), then the mask share
    (`stroke_map.strokes_in_box`'s own arithmetic, only on the few strokes the box meets). A carved barline rule has no mask here and is never named."""
    out = []
    s = float(page_map.scale)
    bx0, by0, bx1, by1 = (float(v) * s for v in box)
    for i in index.meeting(box):
        if i >= len(page_map.masks):
            continue
        m, x0, y0 = page_map.masks[i]
        h, w = m.shape
        lx0, ly0 = max(0, int(round(bx0)) - x0), max(0, int(round(by0)) - y0)
        lx1, ly1 = min(w, int(round(bx1)) - x0), min(h, int(round(by1)) - y0)
        if lx1 <= lx0 or ly1 <= ly0:
            continue
        total = int(m.sum())
        if total > 0 and int(m[ly0:ly1, lx0:lx1].sum()) / float(total) >= share_min:
            out.append(i)
    return out


#: ROADMAP 2.288 round 3: the block rests whose block hangs from (whole) or sits on (half) ONE staff line.
BLOCK_REST_CLASSES = ("restwhole", "resthalf")
LINE_FLANK_PX = IA.LINE_FLANK_PX
LINE_FLANK_SHARE = IA.LINE_FLANK_SHARE
_line_row_flags = IA.line_row_flags


def own_block_height_sp(page_map: Any, i: int, raw: Any) -> Optional[float]:
    """The stroke's height in staff spaces WITHOUT its staff-line rows (rows that have ink in the mask), at its own staff's local space; None where it cannot be measured."""
    if i >= len(page_map.masks) or i >= len(page_map.strokes):
        return None
    st = page_map.strokes[i]
    sp = float(getattr(st, "staff_space_local", None) or getattr(page_map, "sp", 0.0) or 0.0)
    if sp <= 0:
        return None
    s = float(page_map.scale)
    m, x0, y0 = page_map.masks[i]
    keep = _line_row_flags(raw, m, x0, y0, s)
    rows = sum(1 for r in range(m.shape[0]) if keep[r] and m[r].any())
    return rows / s / sp


def block_rest_strokes(page_map: Any, box: Sequence[float], index: StrokeIndex, raw: Any, share_min: float) -> List[int]:
    """ROADMAP 2.288 round 3, STAGED GATHER, pure: the page strokes a whole / half rest's box holds BY THE BLOCK'S OWN INK, the staff line it hangs from set aside.
    A whole rest hangs from a line and a half rest sits on one (Sean's convention, page-facts); the page stroke map erases a staff line only where nothing but the
    line crosses it, so where the block meets its line the stroke is the block PLUS a slab of the line (Brahms p14: 22 rows tall, 6-7 of them line), while the detector draws
    the box round the block alone. Asking "is half the STROKE in the box?" (`strokes_by_share`) then refuses the stroke for the line's share of it, not for anything the block is
    or is not. Here the same cut (`share_min`, the register's one) is asked of the stroke's ink WITHOUT its line rows: a row is a line row when the raw raster is dark just
    beside the stroke on both sides, the test the tile painter uses (measured on the page itself, locally: a scanned staff tilts). No raster (`raw` None) or no line row: this is
    `strokes_by_share` exactly, so it can only ADD a stroke whose block the box holds. A stroke the line merges into a note, or a beam piece, is still refused by `_rest_stroke_fits`
    and `rest_attachment`, which read the stroke's shape and what it touches, not this share."""
    out = []
    s = float(page_map.scale)
    bx0, by0, bx1, by1 = (float(v) * s for v in box)
    for i in index.meeting(box):
        if i >= len(page_map.masks):
            continue
        m, x0, y0 = page_map.masks[i]
        h, w = m.shape
        keep = _line_row_flags(raw, m, x0, y0, s)
        rows = [r for r in range(h) if keep[r]]
        if not rows:
            continue
        total = int(m[rows].sum())
        lx0, lx1 = max(0, int(round(bx0)) - x0), min(w, int(round(bx1)) - x0)
        inside = [r for r in rows if max(0, int(round(by0)) - y0) <= r < min(h, int(round(by1)) - y0)]
        if total > 0 and lx1 > lx0 and inside and int(m[inside, lx0:lx1].sum()) / float(total) >= share_min:
            out.append(i)
    return out


def _rest_stroke_fits(page_map: Any, i: int, owner: str, cls: str, raw: Any = None) -> bool:
    """A READ rest owns its OWN ink only: of the strokes the box names by ink share, the ones whose shape the rest's printed shape allows (`stroke_owner.shape_fit`, family
    `rest` / `whole_rest`: a stem longer than a rest, a beam, a block thicker than a rest's are "no"). `could` stays: a quarter rest's slanted stroke reads as a short vertical.
    A carved barline rule (no page stroke here) is never a rest's.
    ROADMAP 2.288 round 3 (with the page raster `raw`): a whole / half rest's BLOCK is measured on its own rows, the staff line it hangs from set aside. `shape_fit` measures the stroke
    whole, line slab included, against a width cut (`REST_BLOCK_MAX_W_SP` 1.6) and a height cut tuned on Brahms: it refused 49 of 165 READ whole rests on Litolff p8 and 18 of 117 on
    p2 (Litolff's block is wider, median 1.4 sp, a cluster at 1.9, and its slab taller), every one a whole rest on the print. The block's OWN height is the convention (half a space; a
    head fills a space): 0.38-0.85 sp on Litolff p8, and the same cut `BLOCK_MAX_H_SP` is applied to it. The map's own kind says it is not a beam (`blob`, not `horizontal`); the width cut
    stays for a `horizontal` piece, which is how a beam piece reads."""
    from . import stroke_owner as SO
    if i >= len(page_map.strokes):
        return False
    st = page_map.strokes[i]
    if raw is not None and cls.lower() in BLOCK_REST_CLASSES and st.kind == "blob":
        h_own = own_block_height_sp(page_map, i, raw)
        if h_own is not None:
            return h_own <= SO.BLOCK_MAX_H_SP
    sp = float(getattr(st, "staff_space_local", None) or getattr(page_map, "sp", 0.0) or 0.0)
    if sp <= 0:
        return True                      # no unit to measure in: the share named it, nothing here can refuse it (a fallback never narrows silently)
    ink = SO.Ink(ordinal=i, kind=st.kind, box=tuple(float(v) for v in st.box), length=float(st.length_sp), thickness=float(st.thickness_sp),
                 area=float(st.area_sp2), space_px=sp, angle=float(st.angle_deg))
    return SO.shape_fit(owner, ink, cls)[0] != "no"


def rest_box_verdict(page_map: Any, index: StrokeIndex, raw: Any, pb: Sequence[float], cls: str, owner: str, detail: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """ROADMAP 2.288, STAGED GATHER, pure: does ONE detector rest box (page px `pb`, class `cls`, family `owner`) STAND as a rest, and which page strokes are its ink?
    The per-box half of `gather_page_claim_boxes`, a function of its own so that a real page case (Sean's answered tiles, `benchmarks/rests-claim-first-2026-11/real_cases.json`)
    can be replayed through exactly the code the gather runs. Returns `standing` ("READ" | "weak"), `why`, `ids` (READ: only the strokes the printed rest's shape allows; weak: the
    strokes the box named), `block_extra` (the strokes added by the block's own rows, round 3), `attachment` and `sides` (the two shared questions of `ink_attachment`).
    Round 4: a whole / half rest's block must lie on ONE side of ONE staff line (`ink_attachment.line_sides`), and a stem that carries the claimed ink as ITS head attaches it."""
    from . import stroke_map as SM
    ids = strokes_by_share(page_map, pb, index, SM.COVER_SHARE_MIN)
    block_extra: List[int] = []
    block = cls.lower() in BLOCK_REST_CLASSES
    if block:
        # round 3: a block rest's box holds the BLOCK; the stroke is the block plus a slab of the staff line it hangs from / sits on
        # (a stroke the line merges into a note is no block: only strokes whose shape the printed rest allows are added, so a head boxed as a whole rest stays weak)
        block_extra = [i for i in block_rest_strokes(page_map, pb, index, raw, SM.COVER_SHARE_MIN) if i not in ids and _rest_stroke_fits(page_map, i, owner, cls, raw)]
        ids = sorted(set(ids) | set(block_extra))
    att = IA.attachment(page_map, ids)
    fit = [i for i in ids if _rest_stroke_fits(page_map, i, owner, cls, raw)]
    sides = None
    if block:
        per = [s_ for s_ in (IA.line_sides(page_map, i, raw) for i in fit) if s_]
        if per:
            sides = dict(both_sides=any(s_["both_sides"] for s_ in per), two_lines=any(s_["two_lines"] for s_ in per), strokes=per)
    standing, why = rest_standing(detail, att, sides)
    return dict(standing=standing, why=why, ids=fit if standing == "READ" else ids, block_extra=block_extra, attachment=att, sides=sides)


def gather_page_claim_boxes(log: Any, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Optional[Dict[str, List[Any]]],
                            page_map: Any, *, progress: bool = False) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.269 step 3 (flag `OMR_PAGE_CLAIM_BOXES`, default OFF), STAGED GATHER: the detector's boxed dynamics (the letters), whole rests and repeat dots name the
    page strokes they own BY INK SHARE (`stroke_map.COVER_SHARE_MIN`, the register's one cut), once, after the page-wide claims and before the page beams read.
    A box names a stroke when at least that share of the stroke's ink lies in it; a stroke an earlier claim names (the claims already on the log, by claim order)
    is recorded CONTESTED, never taken. Files `Q.CLAIMED_AREA` rows like step 1's (`unit: page_ink`, `source: page_boxes`, `page_strokes`) and a census row.
    Reads no raster beyond the page map's own masks; decides nothing: only `page_beams` reads the rows (export byte-identical on / off)."""
    rests = rests_enabled()
    if not (boxes_enabled() or rests) or detections is None:
        return None
    from . import record as R
    from .record import Q, READERS, Scope
    from . import claim_order as CO
    from . import stroke_map as SM
    p = int(getattr(pws.page, "page_index", 0))
    page_sub = R.page(p)
    if page_map is None or not getattr(page_map, "strokes", None):
        return None
    t0 = time.time()
    index = StrokeIndex(*_boxes_of(page_map))
    claims: List[Dict[str, Any]] = []
    for r in log.rows(Q.CLAIMED_AREA, page_sub, scope=Scope.SELF_AND_DESCENDANTS):          # what already holds page strokes, in the order the rows stand
        d = r.detail or {}
        if d.get("page_strokes"):
            lay = CO.layer_of(str(d.get("owner") or ""))
            claims.append(dict(owner=str(d.get("owner") or ""), layer=99 if lay is None else int(lay), ids=[int(o) for o in d["page_strokes"]], existing=True,
                               row=r.id, subject=r.subject))
    if rests and not enabled():
        # 2.288: with `OMR_PAGE_CLAIM_NAMES` OFF the READ area claims (word, clef, key, meter, header column, barline, bracket) stand on the log as rectangles and are NOT yet page
        # strokes; the rest claim must not take their ink ("cresc." claimed as a rest 8th, 2.288 first gather). Named here by step 1's own predicate (`area_names`), not filed.
        from . import stroke_owner as _SO
        n_area = 0
        for r in log.rows(Q.CLAIMED_AREA, page_sub, scope=Scope.SELF_AND_DESCENDANTS):
            d = r.detail or {}
            v = r.value
            owner = str(d.get("owner") or "")
            if (d.get("unit") != "area" or d.get("standing", "READ") != "READ" or owner not in _SO.AREA_OWNERS
                    or not (isinstance(v, (list, tuple)) and len(v) == 4)):
                continue
            n_area += 1
            lay = CO.layer_of(owner)
            claims.append(dict(owner=owner, layer=99 if lay is None else int(lay), existing=True, row=r.id, subject=r.subject,
                               ids=area_names(index, v, d.get("scope") == "system" and d.get("cell") is None, owner)))
    census: Dict[str, Any] = dict(boxes=0, twins_skipped=0, by_class={}, named_nothing={}, existing_claims=len(claims))
    if rests:
        census.update(rest_boxes=0, rest_read=0, rest_weak={}, rest_weak_boxes=[], rest_read_boxes=[], rest_changed={}, rest_changed_boxes=[], rest_block_named=0,
                      rest_block_named_boxes=[])
    raw = getattr(getattr(pws, "page", None), "binary", None)
    seen = set()
    for c in cells:
        key = local.get(c.staff_index)
        rect, up = getattr(c, "bbox_page_px", None), getattr(c, "upscale_factor", None)
        if key is None or not rect or not up:
            continue
        csub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        for gi, d in enumerate(detections.get(csub.to_key()) or ()):
            cls = str(getattr(d, "smufl_name", ""))
            owner = box_owner(cls, getattr(d, "category", None), rests)
            if owner is None or (owner not in REST_FAMILIES and not boxes_enabled()) or (owner in REST_FAMILIES and not (rests or boxes_enabled())):
                continue
            x, y, w, h = float(d.x_canonical), float(d.y_canonical), float(d.width_canonical), float(d.height_canonical)
            pb = (rect[0] + x / up, rect[1] + y / up, rect[0] + (x + w) / up, rect[1] + (y + h) / up)
            k = (owner, cls.lower()) + tuple(int(round(v / 2.0)) for v in pb)
            if k in seen:
                census["twins_skipped"] += 1
                continue
            seen.add(k)
            standing = None
            ids = strokes_by_share(page_map, pb, index, SM.COVER_SHARE_MIN)
            block_extra: List[int] = []
            if rests and owner in REST_FAMILIES:
                # 2.288: only a rest that STANDS as one (READ) claims; a weak box files nothing and blocks nobody (counted, with where it stands)
                rr = log.rows(Q.REST_INK_CONTACT, R.glyph(c.page_index, key[0], key[1], c.measure_index, gi))
                detail = rr[-1].detail if rr else None
                v = rest_box_verdict(page_map, index, raw, pb, cls, owner, detail)
                standing, why, ids, block_extra = v["standing"], v["why"], v["ids"], v["block_extra"]
                was, _ = _contact_standing(detail)                       # round 1's answer, for the census (what attachment freed / refused)
                census["rest_boxes"] += 1
                if standing != was:
                    k2 = ("freed_" if standing == "READ" else "refused_") + why
                    census["rest_changed"][k2] = census["rest_changed"].get(k2, 0) + 1
                    census["rest_changed_boxes"].append([cls, [round(v_, 1) for v_ in pb], k2, csub.to_key()])
                if standing != "READ":
                    census["rest_weak"][why] = census["rest_weak"].get(why, 0) + 1
                    census["rest_weak_boxes"].append([cls, [round(v_, 1) for v_ in pb], why, csub.to_key()])
                    continue
                census["rest_read"] += 1
                census["rest_read_boxes"].append([cls, [round(v_, 1) for v_ in pb], csub.to_key()])
                if block_extra and any(i in ids for i in block_extra):
                    census["rest_block_named"] += 1
                    census["rest_block_named_boxes"].append([cls, [round(v_, 1) for v_ in pb], [i for i in ids if i in block_extra], csub.to_key()])
            census["boxes"] += 1
            census["by_class"][cls] = census["by_class"].get(cls, 0) + 1
            lay = CO.layer_of(owner)
            claims.append(dict(owner=owner, layer=99 if lay is None else int(lay), ids=ids, existing=False, row=None, subject=csub, cls=cls, box=list(pb),
                               standing=standing))
    res = settle(claims)
    filed = 0
    for c in res["claims"]:
        if c["existing"]:
            continue
        if not c["won"]:
            if not c["ids"]:
                census["named_nothing"][c["owner"]] = census["named_nothing"].get(c["owner"], 0) + 1
            continue
        filed += 1
        log.observe(c["subject"], Q.CLAIMED_AREA, list(c["won"]), reader=READERS.CV_CLAIMED_REGISTER, frame="page", owner=c["owner"], owner_row=None,
                    owner_glyph=None, unit=UNIT, standing="READ", source=SOURCE_BOXES, how="ink_share", cls=c["cls"],
                    page_strokes=list(c["won"]), contested=c["contested"], **({"rest_standing": c["standing"]} if c.get("standing") else {}))
    census.update(rows=filed, named=sum(len(c["won"]) for c in res["claims"] if not c["existing"]),
                  contested=sum(len(c["contested"]) for c in res["claims"] if not c["existing"]), seconds=round(time.time() - t0, 3))
    log.observe(page_sub, Q.CLAIMED_AREA, "census", reader=READERS.CV_CLAIMED_REGISTER, frame="page", owner="page_boxes", unit=UNIT_CENSUS, standing="READ",
                source=SOURCE_BOXES, **census)
    if progress:
        print("  gather page claim boxes p%s: %s" % (p, census))
    return census
