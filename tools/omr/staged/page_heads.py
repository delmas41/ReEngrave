"""ROADMAP 2.260e M6a -- EVERY HEAD IS A PAGE FACT OF ITS OWN (STAGED GATHER; flag `OMR_PAGE_HEADS`, default OFF; M6b `OMR_PAGE_HEAD_VIEWS`, M6c `OMR_PAGE_HEAD_CLAIM`).

    docs/plan-2026-11-04-page-heads-m6.md; Sean 2026-11-05: "I want an actual fix that reads and claims all note heads individually."

CAUSE. A head was a subject only if the detector boxed it, and everything about it -- position, extent, the ledger job, the claim -- hung off that box in ONE
cell's padded crop. So (1) the same head boxed by two cells (or twice in one) was two heads that could disagree; (2) the far-head ledger read ran only when the
BOX's rounded position was outside -1..9, so a box drawn half a step off its ink (Litolff p10 tile 9: box 9.38, rounds 9; truth 10, a head on the first ledger
below) never asked the ledger lines; (3) the head claimed ink by "a box holds half of a cell stroke" -- Sean called it arbitrary -- and a head the detector never
boxed owned nothing. LESSON: each head reader was added to repair its predecessor's miss, and every one of them asks the BOX; none asks the INK once.

WHAT. One reader per page, on the page stroke map (M2) and the detector's notehead boxes, in page px, deciding nothing:

  * the notehead boxes of every cell are FOLDED: two boxes (same cell or two cells) whose IoU is at least `FOLD_IOU` are ONE head (union-find). Two real heads a
    unison or a second apart stand side by side (IoU near 0) and never fold.
  * a head's INK is the page strokes at least `stroke_map.COVER_SHARE_MIN` of which lies inside its box (the register's one cut; share read off the page map's
    masks, candidates by box overlap first -- the 2.262 lesson), and its EXTENT is the union of the blob strokes among them; beside it the existing
    `head_extent.ink_extent` (the 2.220 trim on `page.binary`, which keeps the ink the staff eraser thinned) is read, and the position is taken from the trimmed
    extent where it is one head, else from the strokes.
  * the POSITION is the extent's centre against the staff lines of the head's OWN bar (`gather._cell_grid` of the member cell nearest the head -- measured
    locally, page-facts), in half steps from the top line. It is a TRIGGER and a candidate, never a placement outside the staff: a head outside -1..9 is placed by
    its ledger lines only (page-facts, Sean 2026-10-27).
  * the LEDGER-READ TRIGGER (`far_trigger`): the box rounds outside -1..9 (today's rule), OR the ink centre does, OR a level thin stroke (a ledger stub the page
    map joined to the head) touches a head whose ink rounds to the first space either side (-1 or 9; page-facts: a head in the first space with no ledger touching
    it is on-staff).
  * INK-ONLY HEADS (census only; no Glyph, no note): head-shaped blobs (>= `HEAD_MIN_AREA_SP2`, <= `HEAD_MAX_W_SP` x `HEAD_MAX_H_SP`) no detector box of ANY class
    stands on, that touch a stem stroke a boxed head also touches. Counted for M6d; filed on the page head list with `source: ink_only`.

WHAT IT FILES (`gather_page_heads` reads and returns; `file_page_heads` files, after the page-wide claim names so a claim an earlier owner holds is marked
contested, never taken -- CLAUDE §3):
  * `Q.PAGE_HEAD`, one row per head on the page subject: value `box` | `ink_only` | `census`; `detail`: members, boxes, strokes, extents, both position
    candidates, the trigger, the rung strokes, and the members' current `Q.NOTEHEAD_STAFF_POSITION` rows.
  * `Q.CLAIMED_AREA`, `unit: page_ink`, `source: page_heads`, owner `head` (blob strokes) and `ledger` (level thin strokes touching the head), value = the page stroke
    ordinals, `contested` = [[stroke, holder owner]], `members` = the glyph keys, `stroke_boxes` = their page boxes (what M6c's `_head_claims` reads).
M6a files and nothing reads: the exported file is byte-identical with the flag on (the proof is the lane gate).

CONVENTION ASSUMED: a head's printed ink centre is its position; a twin box is the same head; a stub touching a head either side is its ledger. WHAT WOULD FALSIFY
IT: the control that plants a half-head (Brahms p0 black heads must fall) and the tile 9 control (box 9.38 against ink near 10). NOT CONFIRMED beyond two plates.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

DERIVED_CHECK = False
ENV = "OMR_PAGE_HEADS"
VIEWS_ENV = "OMR_PAGE_HEAD_VIEWS"
CLAIM_ENV = "OMR_PAGE_HEAD_CLAIM"
SOURCE = "page_heads"
UNIT = "page_ink"
HEAD_PREFIX = "notehead"
#: two notehead boxes are one head at this IoU (unison / second neighbours are ~0; a double box is >0.5)
FOLD_IOU = 0.5
#: the register's one cover cut (`stroke_map.COVER_SHARE_MIN`)
COVER_SHARE_MIN = 0.5
#: a head-shaped blob (`stroke_owner` HEAD_*): area at least this (sp^2) and at most this wide / tall (sp)
HEAD_MIN_AREA_SP2 = 0.25
HEAD_MAX_W_SP = 3.0
HEAD_MAX_H_SP = 1.6
#: a ledger stub: level, thin, short (`stroke_owner.LEDGER_MAX_*`)
LEDGER_MAX_THICK_SP = 0.35
LEDGER_MAX_LEN_SP = 3.5
#: first space either side of the staff; farther out is a far head
FAR_LOW, FAR_HIGH = -1, 9
#: a ledger stub's centre is at least this many half steps beyond the outer staff line (the first ledger is 2 half steps out; residue of the line itself is 0)
RUNG_OUTSIDE_STEPS = 1.5
#: a stem stroke: vertical, at least this long (sp)
STEM_MIN_LEN_SP = 1.5


def enabled() -> bool:
    """`OMR_PAGE_HEADS` (ROADMAP 2.260e M6a), default OFF: allow-list, so an empty value or a typo cannot switch a document onto an unpriced change."""
    return os.environ.get(ENV, "0").strip().lower() in ("1", "true", "yes", "on")


def _flag(name: str) -> bool:
    return os.environ.get(name, "0").strip().lower() in ("1", "true", "yes", "on")


def views_enabled() -> bool:
    """`OMR_PAGE_HEAD_VIEWS` (M6b), default OFF; needs `OMR_PAGE_HEADS`."""
    return enabled() and _flag(VIEWS_ENV)


def claim_enabled() -> bool:
    """`OMR_PAGE_HEAD_CLAIM` (M6c), default OFF; needs `OMR_PAGE_HEADS`."""
    return enabled() and _flag(CLAIM_ENV)


# ───────────────────────────── the pure core ─────────────────────────────

def iou(a: Sequence[float], b: Sequence[float]) -> float:
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def fold(boxes: Sequence[Sequence[float]], staff_ids: Sequence[Any], min_iou: float = FOLD_IOU) -> List[List[int]]:
    """Groups of indices: boxes on the same staff whose IoU is at least `min_iou`, joined transitively. Sorted by left edge, so a box meets only its
    neighbours in x."""
    n = len(boxes)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    order = sorted(range(n), key=lambda i: boxes[i][0])
    for a, i in enumerate(order):
        for j in order[a + 1:]:
            if boxes[j][0] > boxes[i][2]:
                break
            if staff_ids[i] == staff_ids[j] and iou(boxes[i], boxes[j]) >= min_iou:
                parent[find(i)] = find(j)
    groups: Dict[int, List[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return sorted((sorted(g) for g in groups.values()), key=lambda g: (boxes[g[0]][0], boxes[g[0]][1]))


def position_of(y_page: float, top_page: float, half_step_page: float) -> float:
    """Half steps below the top line (0 = top line, 8 = bottom line) of a page y against ONE bar's grid."""
    return (float(y_page) - float(top_page)) / float(half_step_page)


def far_trigger(box_rounded: Sequence[int], ink_pos: Optional[float], rung_touch: bool) -> Optional[str]:
    """Why the ledger lines must be asked about this head (None = nobody asks): the box rounds outside -1..9 (`box`), the ink centre does (`ink`), or a ledger
    stub touches a head whose ink is in the first space either side of the staff (`rung_first_space`)."""
    if any(p < FAR_LOW or p > FAR_HIGH for p in box_rounded):
        return "box"
    if ink_pos is None:
        return None
    r = int(round(float(ink_pos)))
    if r < FAR_LOW or r > FAR_HIGH:
        return "ink"
    # A ledger stub touching a first-space head is recorded (`rung_strokes`) but does NOT ask the ledger lines: measured on the Litolff sample (2.260e r2), the
    # stub trigger asked about ONE end of a tie and not the other (-2 against -1), so five ties read as slurs. Only a box or ink centre outside the first space asks.
    return None


# ───────────────────────────── the reader ─────────────────────────────

class PageHeads:
    """What `read` found on one page: `heads` (dicts, one per folded head, `ordinal` = index), `ink_only`, `census`, `stroke_owner_names` (the head / ledger claims
    in filing order), `seconds`."""

    def __init__(self) -> None:
        self.heads: List[Dict[str, Any]] = []
        self.ink_only: List[Dict[str, Any]] = []
        self.census: Dict[str, Any] = {}
        self.seconds: Dict[str, float] = {}
        self.by_member: Dict[str, int] = {}


def _stroke_arrays(pm: Any) -> Tuple[np.ndarray, np.ndarray]:
    n = len(pm.strokes)
    kinds = np.array([s.kind for s in pm.strokes], dtype=object) if n else np.array([], dtype=object)
    boxes = np.zeros((n, 4), np.float64)
    for i, s in enumerate(pm.strokes):
        x, y, w, h = s.box
        boxes[i] = (x, y, x + w, y + h)
    return boxes, kinds


def _share(pm: Any, i: int, box: Sequence[float], totals: Dict[int, int]) -> float:
    """Share of page stroke `i`'s ink inside `box` (page px), off the map's reduced mask."""
    if i >= len(pm.masks):
        return 0.0
    m, x0, y0 = pm.masks[i]
    h, w = m.shape
    s = pm.scale
    lx0, ly0 = max(0, int(round(box[0] * s)) - x0), max(0, int(round(box[1] * s)) - y0)
    lx1, ly1 = min(w, int(round(box[2] * s)) - x0), min(h, int(round(box[3] * s)) - y0)
    if lx1 <= lx0 or ly1 <= ly0:
        return 0.0
    if i not in totals:
        totals[i] = int(m.sum())
    if totals[i] <= 0:
        return 0.0
    return float(m[ly0:ly1, lx0:lx1].sum()) / totals[i]


def read(pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]], pm: Any) -> Optional[PageHeads]:
    """The page head list (module doc). None where there is no page map. Pure of the log: positions of the members' own rows are attached by `file_page_heads`."""
    if pm is None or not getattr(pm, "strokes", None):
        return None
    from . import record as R
    from .record import Subject
    from . import head_extent, head_ink
    from .gather import _cell_grid, _page_box
    t0 = time.time()
    out = PageHeads()
    cell_by_key: Dict[Tuple[int, int, int, int], Any] = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c
    page_binary = getattr(getattr(pws, "page", None), "binary", None)
    sp = float(pm.sp)
    boxes_all: List[Tuple[float, float, float, float]] = []       # every detector box of every class, page px
    foreign: List[Tuple[float, float, float, float]] = []
    hb: List[Dict[str, Any]] = []                                   # notehead boxes
    for ck, dets in detections.items():
        sub = Subject.from_key(ck)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        if c is None:
            continue
        for gi, d in enumerate(dets):
            pb = _page_box(c, d)
            if pb is None:
                continue
            boxes_all.append(pb)
            name = str(d.smufl_name)
            if head_ink.is_foreign_class(name):
                foreign.append(pb)
            if name.startswith(HEAD_PREFIX):
                hb.append(dict(key=R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi).to_key(), cell=(sub.page, sub.system, sub.staff, sub.cell),
                               glyph=gi, box=pb, cls=name, conf=float(getattr(d, "confidence", 0.0) or 0.0), staff_index=int(c.staff_index), c=c))
    stroke_boxes, kinds = _stroke_arrays(pm)
    totals: Dict[int, int] = {}
    groups = fold([h["box"] for h in hb], [h["staff_index"] for h in hb])
    stem_ids = {i for i, s in enumerate(pm.strokes) if s.kind == "vertical" and s.length_sp >= STEM_MIN_LEN_SP}
    head_stems: set = set()
    taken = np.zeros(len(pm.strokes), bool)
    cen = dict(boxes=len(hb), heads=len(groups), folded_boxes=len(hb) - len(groups), heads_with_ink=0, heads_no_ink=0, far_trigger={}, ink_position_known=0,
               ink_vs_box_ge_half_step=0, trim_not_one_head=0, twins_disagree_ge_half_step=0)
    for gi_, g in enumerate(groups):
        mem = [hb[i] for i in g]
        # the box the head is read from: the member whose cell centre is nearest the head's (its own bar), highest confidence on a tie
        ux0, uy0 = min(m["box"][0] for m in mem), min(m["box"][1] for m in mem)
        ux1, uy1 = max(m["box"][2] for m in mem), max(m["box"][3] for m in mem)
        cx = (ux0 + ux1) / 2.0

        def cell_dist(m: Dict[str, Any]) -> Tuple[float, float]:
            bb = m["c"].bbox_page_px
            return (abs((bb[0] + bb[2]) / 2.0 - cx), -m["conf"])
        rep = min(mem, key=cell_dist)
        grid = _cell_grid(rep["c"])
        up = getattr(rep["c"], "upscale_factor", None)
        bb = rep["c"].bbox_page_px
        top_page = hs_page = None
        if grid is not None and up:
            top_page, hs_page = bb[1] + grid[0] / up, grid[1] / up
        sp_head = (2.0 * hs_page) if hs_page else sp
        box = rep["box"]
        # the page strokes that stand on the head: candidates by box overlap, then the ink share
        near = np.nonzero((stroke_boxes[:, 2] > box[0]) & (stroke_boxes[:, 0] < box[2]) & (stroke_boxes[:, 3] > box[1]) & (stroke_boxes[:, 1] < box[3]))[0] if len(pm.strokes) else []
        covered: List[Tuple[int, float]] = []
        for i in near:
            sh = _share(pm, int(i), box, totals)
            if sh >= COVER_SHARE_MIN:
                covered.append((int(i), round(sh, 3)))
        blobs = [i for i, _ in covered if kinds[i] == "blob"]
        for i in blobs:
            for j, _ct in pm.strokes[i].touches:
                if j in stem_ids:
                    head_stems.add(int(j))
        rung_ids = []
        for i, _ in covered:
            for j, _ct in pm.strokes[i].touches:
                s = pm.strokes[j]
                if s.kind == "horizontal" and s.thickness_sp <= LEDGER_MAX_THICK_SP and s.length_sp <= LEDGER_MAX_LEN_SP and j not in rung_ids:
                    # a ledger stub stands OUTSIDE the staff body: the staff line a head overlaps leaves residue beyond the eraser's band (Litolff p2 2/1/1/10: a head
                    # above the top line, no ledger printed, a "rung" at the top line read as one) -- a stub within `RUNG_OUTSIDE_STEPS` of the lines is not a ledger
                    if top_page is not None:
                        sp_pos = position_of(float(s.box[1]) + float(s.box[3]) / 2.0, top_page, hs_page)
                        if not (sp_pos <= -RUNG_OUTSIDE_STEPS or sp_pos >= 8 + RUNG_OUTSIDE_STEPS):
                            continue
                    rung_ids.append(int(j))
        ext_s = None
        use = blobs or [i for i, _ in covered if kinds[i] != "vertical"]
        if use:
            ext_s = [float(stroke_boxes[use, 0].min()), float(stroke_boxes[use, 1].min()), float(stroke_boxes[use, 2].max()), float(stroke_boxes[use, 3].max())]
        for i, _ in covered:
            taken[i] = True
        trim = None
        trim_why = "no_raster"
        if page_binary is not None:
            others = [hb[h2[0]]["box"] for h2 in groups if h2 is not g
                      and abs(hb[h2[0]]["box"][0] - box[0]) < 4 * sp and abs(hb[h2[0]]["box"][1] - box[1]) < 4 * sp]
            got = head_extent.ink_extent(page_binary, box, sp_head, [f for f in foreign if abs(f[0] - box[0]) < 4 * sp and abs(f[1] - box[1]) < 4 * sp], others)
            trim_why = got["why"]
            trim = got["extent"] if got["why"] is None else None
            if got["why"] is not None and str(got["why"]).startswith("not_one_head"):
                cen["trim_not_one_head"] += 1
        ext = trim or ext_s
        member_pos = []
        for m in mem:
            gr = _cell_grid(m["c"])
            u = getattr(m["c"], "upscale_factor", None)
            if gr is not None and u:
                bbm = m["c"].bbox_page_px
                member_pos.append(position_of((m["box"][1] + m["box"][3]) / 2.0, bbm[1] + gr[0] / u, gr[1] / u))
            else:
                member_pos.append(None)
        box_pos = None if top_page is None else position_of((box[1] + box[3]) / 2.0, top_page, hs_page)
        ink_pos = None if (ext is None or top_page is None) else position_of((ext[1] + ext[3]) / 2.0, top_page, hs_page)
        ink_pos_strokes = None if (ext_s is None or top_page is None) else position_of((ext_s[1] + ext_s[3]) / 2.0, top_page, hs_page)
        rounded = [int(round(p)) for p in member_pos if p is not None]
        trig = far_trigger(rounded, ink_pos, bool(rung_ids))
        if covered:
            cen["heads_with_ink"] += 1
        else:
            cen["heads_no_ink"] += 1
        if trig:
            cen["far_trigger"][trig] = cen["far_trigger"].get(trig, 0) + 1
        if ink_pos is not None and box_pos is not None:
            cen["ink_position_known"] += 1
            if abs(ink_pos - box_pos) >= 0.5:
                cen["ink_vs_box_ge_half_step"] += 1
        known = [p for p in member_pos if p is not None]
        if len(known) > 1 and max(known) - min(known) >= 0.5:
            cen["twins_disagree_ge_half_step"] += 1
        h = dict(ordinal=len(out.heads), source="box", members=[m["key"] for m in mem], boxes=[[round(v, 1) for v in m["box"]] for m in mem],
                 box=[round(v, 1) for v in box], rep=rep["key"], cell=list(rep["cell"]), strokes=[[i, sh] for i, sh in covered], blob_strokes=blobs,
                 rung_strokes=rung_ids, stroke_extent=None if ext_s is None else [round(v, 1) for v in ext_s],
                 trim_extent=None if trim is None else [round(float(v), 1) for v in trim], trim_why=trim_why,
                 box_position_float=None if box_pos is None else round(box_pos, 3), ink_position_float=None if ink_pos is None else round(ink_pos, 3),
                 ink_position_strokes_float=None if ink_pos_strokes is None else round(ink_pos_strokes, 3),
                 member_box_positions=[None if p is None else round(p, 3) for p in member_pos], far_trigger=trig,
                 staff=[rep["cell"][1], rep["cell"][2]], cls=rep["cls"])
        for m in mem:
            out.by_member[m["key"]] = h["ordinal"]
        out.heads.append(h)
    t1 = time.time()
    # ink-only heads: head-shaped blobs no detector box of any class stands on, on a stem a boxed head also touches
    ab = np.array(boxes_all, np.float64) if boxes_all else np.zeros((0, 4))
    n_shaped = n_unboxed = 0
    for i, s in enumerate(pm.strokes):
        if s.kind != "blob" or taken[i]:
            continue
        spl = float(s.staff_space_local or sp)
        x, y, w, hh = s.box
        if not (s.area_sp2 >= HEAD_MIN_AREA_SP2 and w <= HEAD_MAX_W_SP * spl and hh <= HEAD_MAX_H_SP * spl):
            continue
        n_shaped += 1
        cxs, cys = x + w / 2.0, y + hh / 2.0
        if len(ab) and bool(((ab[:, 0] <= cxs) & (cxs <= ab[:, 2]) & (ab[:, 1] <= cys) & (cys <= ab[:, 3])).any()):
            continue
        n_unboxed += 1
        stems = [int(j) for j, _ in s.touches if j in head_stems]
        if not stems:
            continue
        rung = [int(j) for j, _ in s.touches if pm.strokes[j].kind == "horizontal" and pm.strokes[j].thickness_sp <= LEDGER_MAX_THICK_SP]
        out.ink_only.append(dict(ordinal=len(out.heads) + len(out.ink_only), source="ink_only", strokes=[[i, 1.0]], blob_strokes=[i], stems=stems, rung_strokes=rung,
                                 stroke_extent=[round(float(x), 1), round(float(y), 1), round(float(x + w), 1), round(float(y + hh), 1)],
                                 stem_side=("left" if cxs < float(pm.strokes[stems[0]].box[0] + pm.strokes[stems[0]].box[2] / 2.0) else "right")))
    cen.update(blobs_head_shaped_unclaimed=n_shaped, blobs_head_shaped_unboxed=n_unboxed, ink_only_on_a_boxed_heads_stem=len(out.ink_only),
               ink_only_on_a_rung=sum(1 for h in out.ink_only if h["rung_strokes"]))
    out.census = cen
    out.seconds = dict(heads=round(t1 - t0, 2), ink_only=round(time.time() - t1, 2))
    return out


# ───────────────────────────── filing ─────────────────────────────

def _settle(claims: List[Dict[str, Any]], held: Dict[int, str]) -> None:
    """First claim wins: `held` is {stroke: owner} (earlier page-wide claims, then these in order). A stroke another owner holds is CONTESTED on the claim; the same
    owner again is a twin (counted, not contested)."""
    for c in claims:
        won, contested, twins = [], [], 0
        for i in c["ids"]:
            h = held.get(i)
            if h is None:
                held[i] = c["owner"]
                won.append(i)
            elif h == c["owner"]:
                twins += 1
                won.append(i)
            else:
                contested.append([i, h])
        c["won"], c["contested"], c["twins"] = won, contested, twins


def head_claims(ph: PageHeads, pm: Any, held: Optional[Dict[int, str]] = None) -> List[Dict[str, Any]]:
    """The claims of a page head list, in claim order: every head's blob strokes (owner `head`), then every head's level thin stubs (owner `ledger`). `held` =
    {stroke: owner} already named by an earlier owner."""
    claims: List[Dict[str, Any]] = []
    for owner, field in (("head", "blob_strokes"), ("ledger", "rung_strokes")):
        for h in ph.heads + ph.ink_only:
            ids = [int(i) for i in h.get(field) or ()]
            if ids:
                claims.append(dict(owner=owner, ids=ids, head=h["ordinal"], members=h.get("members") or []))
    _settle(claims, dict(held or {}))
    # a second pass is unnecessary: `_settle` mutates a copy in claim order, so the result above is the order the claims stand in
    return claims


def file_page_heads(log: Any, pws: Any, ph: Optional[PageHeads], pm: Any, *, progress: bool = False) -> None:
    """`Q.PAGE_HEAD` rows and the `unit: page_ink` head / ledger claims (module doc). AFTER the page-wide claim names (`page_claim_names`) so `held` is complete, and
    after `gather_notehead_positions` so the members' own position rows ride on the head."""
    if ph is None:
        return
    from . import record as R
    from .record import Q, READERS, Scope, Subject
    from .gather import FRAME_PAGE
    p = int(getattr(pws.page, "page_index", 0))
    sub = R.page(p)
    held: Dict[int, str] = {}
    for r in log.rows(Q.CLAIMED_AREA, sub, scope=Scope.SELF_AND_DESCENDANTS):
        d = r.detail or {}
        if d.get("unit") == UNIT and d.get("source") != SOURCE:
            for i in (d.get("page_strokes") or ()):
                held.setdefault(int(i), str(d.get("owner") or ""))
    claims = head_claims(ph, pm, held)
    for h in ph.heads:
        rows = []
        for k in h["members"]:
            for r in log.rows(Q.NOTEHEAD_STAFF_POSITION, Subject.from_key(k)):
                rows.append(round(float(r.value), 3))
                break
        h["member_row_positions"] = rows
    n = 0
    for h in ph.heads + ph.ink_only:
        log.observe(sub, Q.PAGE_HEAD, h["source"], reader=READERS.CV_PAGE_HEADS, frame=FRAME_PAGE, **h)
        n += 1
    filed = 0
    for c in claims:
        if not c["won"] and not c["contested"]:
            continue
        sb = [[round(float(pm.strokes[i].box[0]), 1), round(float(pm.strokes[i].box[1]), 1), round(float(pm.strokes[i].box[0] + pm.strokes[i].box[2]), 1),
               round(float(pm.strokes[i].box[1] + pm.strokes[i].box[3]), 1)] for i in c["won"]]
        log.observe(sub, Q.CLAIMED_AREA, list(c["won"]), reader=READERS.CV_PAGE_HEADS, frame=FRAME_PAGE, owner=c["owner"], unit=UNIT, standing="READ", source=SOURCE,
                    how="page_head", page_strokes=list(c["won"]), contested=c["contested"], head=c["head"], members=c["members"], stroke_boxes=sb)
        filed += 1
    cen = dict(ph.census, rows=n, claims=filed, claims_contested=sum(1 for c in claims if c["contested"]), seconds=ph.seconds)
    log.observe(sub, Q.PAGE_HEAD, "census", reader=READERS.CV_PAGE_HEADS, frame=FRAME_PAGE, **cen)
    if progress:
        print("  gather page heads p%s: %s" % (p, cen))


def gather_page_heads(log: Any, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]], pm: Any, *,
                      progress: bool = False) -> Optional[PageHeads]:
    """ROADMAP 2.260e M6a (flag `OMR_PAGE_HEADS`, default OFF), STAGED GATHER: read the page head list (decides nothing, files nothing yet). Placed AFTER the final
    box set and the page map, BEFORE `gather_notehead_positions`. `file_page_heads` files it later."""
    if not enabled():
        return None
    ph = read(pws, cells, local, detections, pm)
    if ph is not None and progress:
        print("  gather page heads p%s: read %d heads (%s)" % (getattr(pws.page, "page_index", 0), len(ph.heads), ph.seconds))
    return ph
