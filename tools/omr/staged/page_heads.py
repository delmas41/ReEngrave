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

import collections
import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

DERIVED_CHECK = False
ENV = "OMR_PAGE_HEADS"
VIEWS_ENV = "OMR_PAGE_HEAD_VIEWS"
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


# ═════════════════════════════ ROADMAP 2.290 build: ONE HEAD, ONE IDENTITY, ONE CLAIM ═════════════════════════════
#
# docs/plan-2026-11-10-page-heads-on-the-ledger.md steps 1, 2 and 4. Sean 2026-11-05: "I want an actual fix that reads and claims all note heads
# individually"; 2026-11-11: "I want the rest of the ink claimed especially note heads"; DECISIONS 2026-11-10 RETIRE AS YOU LAND.
#
# THE CAUSE. Three answers to "which boxes are one head" stood side by side -- `Q.MARK_GROUP` (box IoU > 0.3 in one system, `gather.cluster_marks`),
# `Q.PAGE_MARK` (two CELLS' boxes sharing half the smaller box's ink, `page_marks.link`) and M6a's `fold` above (IoU 0.5, one staff, read by nothing) --
# none of them asked the INK whether the two boxes stand on one printed head, and each consumer read a different one. And a head's ink was claimed per
# padded cell by "a box covers half a cell stroke" (`stroke_owner` head tier), so the same page ink was a head in one cell and a twin in the next.
#
# STEP 1+2, ONE IDENTITY (flag `OMR_PAGE_HEAD_ONE`, default OFF). A notehead box's HEAD INK is the page-map pixels inside its rectangle that lie on a
# head-shaped stroke (`is_head_ink`: no stem, no ledger rung or line residue, no beam piece, no long curve). Two notehead boxes of one system are ONE
# HEAD when (a) both hold head ink, (b) they share at least `SHARE_MIN` of the smaller one's head ink (the same pixels, not a near box) and (c) the
# centres of their head ink lie within one oval (`OVAL_DX_SP` across, `OVAL_DY_SP` along: a third stands two steps away, a second's two heads stand
# either side of the stem; page-facts: stacked heads of a chord stay separate, a unison is one head with two stems and two notes, `export_unison`).
# A tall box GATHER already read for the heads inside it (`box_kind` tall read) joins nothing (as `cluster_marks`). A box that holds no head ink
# (`HEAD_INK_MIN_SP2`; the phantom doubleWhole over a beam, a barline sliver) makes NO head: it joins the head whose box it overlaps at the old
# twin rule (`gather.MARK_GROUP_IOU`) so nothing written once today is written twice, else it stands alone -- and it is COUNTED (`no_head_ink`).
# The partition is filed as the notehead `Q.MARK_GROUP` rows (the same quantity and fields, so every reader -- export write-once, `export_unison`,
# `glyph_owner` once per group, `rhythm`'s twin -- reads it unchanged) and as the head `Q.PAGE_MARK` ids (so the page owner, 2.240, rules once per
# head). `cluster_marks` for noteheads, `page_marks.link` for heads and M6a's `fold` are then not consulted for heads.
#
# STEP 4, ONE CLAIM (flag `OMR_PAGE_HEAD_LEDGER`, needs `OMR_PAGE_HEAD_ONE`, default OFF). Each head claims the PAGE STROKES of its own oval: the
# head's ink extent grown from its representative box on the page raster (`head_extent.ink_extent`, the 2.220 trim; never the detector rectangle),
# and a stroke is the head's when at least `CLAIM_SHARE_MIN` of the stroke's ink lies inside that oval, the stroke is head-shaped and no bigger than a
# head (`stroke_owner.HEAD_MAX_*`), and no OTHER head's oval holds `OTHER_HEAD_MAX` of it. A stroke fused with another mark (a slash, a stem, a
# letter, a rest: the stroke is bigger than a head) or with another head is NOT claimed -- splitting merged ink is plan step 5 -- and stays with the
# cell boxes as today. Filed as ONE `Q.CLAIMED_AREA` row per head on the page (owner `head`, unit `page_ink`, source `page_head_one`, `page_strokes`,
# `members`); ADJUDICATE's stroke owner hands each cell the claim on the cell strokes LINKED to those page strokes (`page_ledger`'s link rule) at the
# HEAD tier, so every earlier claim (staff, barline, clef/key/meter, words, dynamics, arcs, tremolo, accidental ink, whole rests; tier 0 / 1) keeps
# its ink and the stems / beams / flags read after it; the head's member boxes are ONE owner with it (`stroke_owner._settle`: decided, never a twin).
# Claim order: `claim_order.LAYERS` layer `head`.
#
# CONVENTION ASSUMED: a printed head is one oval of ink; two boxes on the same pixels whose ink centres lie within one oval are one head; a stroke
# bigger than a head is fused and not the head's alone. WHAT WOULD FALSIFY IT: a tile Sean calls two heads that this joins (a chord drawn tight), one
# head this keeps apart (a twin box drawn off its ink by more than the oval), or claimed ink that is not the head's. NOT CONFIRMED beyond two plates.

ONE_ENV = "OMR_PAGE_HEAD_ONE"
LEDGER_ENV = "OMR_PAGE_HEAD_LEDGER"
ONE_SOURCE = "page_head_one"
ONE_OWNER = "head"
#: a notehead box holding less head ink than this (sp^2) stands on no head: a tenth of a filled head (~1.0 sp^2, `stroke_owner.HEAD_MIN_AREA_SP2` doc)
HEAD_INK_MIN_SP2 = 0.1
#: two boxes share a head when the pixels they share are at least this share of the smaller one's head ink (the register's one cut, `page_marks.SHARE_MIN`)
SHARE_MIN = 0.5
#: ... and the centres of their head ink lie inside one oval (staff spaces): across, half a head's width (~1.3 sp); along, under a THIRD (1 sp). A
#: convention, not a cut tuned here: on one side of a stem two heads stand at least a third apart -- a second's two heads stand EITHER side of the
#: stem (page-facts), so they differ across by a head's width -- and nothing is printed a step apart at one x. Round 1 had 0.4 (half a step): 6 heads
#: on Litolff p2/p8/p11 were written TWICE at one pitch (twin boxes 0.45-0.6 sp apart by their clipped ink).
OVAL_DX_SP = 0.65
OVAL_DY_SP = 0.75
#: two boxes on one head-sized stroke are one head unless their ink centres stand a third apart (then the stroke holds two heads' pieces)
ANCHOR_MAX_DY_SP = 0.9
#: a horizontal piece at least this wide and this flat is a beam piece, not head ink (2.284 r7's bar test, `rhythm._head_owned_bar`)
BEAM_MIN_W_SP = 1.8
BEAM_MIN_ASPECT = 2.5
#: a curve longer than this is an arc piece, not a head's outline (`stroke_owner.shape_fit` head_outline_piece)
CURVE_MAX_LEN_SP = 2.0
#: a printed head's size (sp), for the oval where the trim cannot cut one head out (`stroke_owner`: "a notehead ~1.3 x 1.0")
OVAL_W_SP = 1.3
OVAL_H_SP = 1.0
#: a THIN horizontal no longer than this is a hollow head's top or bottom (a head ~1.3 sp wide; a ledger rung sticks out both sides, ~2 sp)
HOLLOW_PIECE_MAX_LEN_SP = 1.6
#: ... and its box no wider than a head can print (`head_ink.MAX_WIDTH_SPACES` 1.75, plus the anti-alias edge)
HOLLOW_PIECE_MAX_W_SP = 1.9
#: a blob's shorter side must be at least this (sp): thinner is a stem piece
BLOB_MIN_SIDE_SP = 0.3
#: a stroke is the head's claimed ink when this share of it lies in the head's oval ...
CLAIM_SHARE_MIN = 0.5
#: ... it is no bigger than a head (`stroke_owner.HEAD_MAX_W_SP` / `HEAD_MAX_H_SP`) ...
CLAIM_MAX_W_SP = 3.0
CLAIM_MAX_H_SP = 1.6
#: ... and no other head's oval holds this share of it (fused with another head: plan step 5)
OTHER_HEAD_MAX = 0.2
#: ROUND 2 (Sean's 2.290 build r1 tiles 8, 9, 10, 12; his correction to 12: the claim lay BETWEEN two half notes a third apart).
#: (1) Two HEAD-SIZED boxes (neither taller than `CLAIM_MAX_H_SP`: a tall box covers two heads and says nothing) whose centres stand this far apart (sp) are TWO
#: heads, never one, whatever ink each clips. A printed head is ~1.0 sp tall; on one side of a stem two heads stand a third (1.0 sp) apart at least, a second's
#: heads stand either side of the stem (page-facts, Sean 2026-10-26); a twin box is the detector's second drawing of ONE head and is off it by less (measured: the
#: farthest twin pair on the five sample pages is 0.85 sp, round 1's p11 case; every joined head-sized pair at or above 0.9 is this tile). Cause of tile 12: the ink
#: each box CLIPS lies toward the other's (centres 0.53 sp apart for boxes 0.99 apart; the lower half note's head ink in its box is only 88 px) -- the ink centres
#: were the only witness to where a head is, and a biased one. NOT CONFIRMED beyond two plates.
BOX_CENTRES_A_THIRD_SP = 0.9
#: (2) A head's CLAIM is a WHOLE head's ink: the union of the page strokes it claims is at least `CLAIM_UNION_MIN_SP` (`head_ink.MIN_SPACES`, 0.6 sp: "the width
#: floor costs 0 of 103 confirmed heads", page-facts) on each side and at most `CLAIM_UNION_MAX_H_SP` (`head_ink.MAX_HEIGHT_SPACES`, 1.5) tall. A smaller union is a
#: SLIVER of a head or of another mark (Sean: "a small sliver that just touches part of a half note" 1.59 x 0.19 sp; "a long, thin sliver that covers part of a
#: quarter note" 0.38 x 1.52 sp); a taller one is more than one head's ink ("half of a quarter note rest", 1.02 x 1.59 sp: the detector boxed the rest as a notehead
#: and no rest box named it, so nothing claimed its ink before the head tier). It is REFUSED WHOLE and COUNTED (`claim_size`); the ink stays with the cell boxes.
#: Not a WIDTH cut: a head fused to its ledger line is ~2.8 wide and is still the head's (`stroke_owner.HEAD_MAX_W_SP` 3.0; Brahms 2.282 tile 1). A hollow head that
#: shows on the page as two thin rims only (2.289 r1 tile 9) is a pair of slivers by this rule and stays with the cell boxes (plan step 5).
CLAIM_UNION_MIN_SP = 0.6
CLAIM_UNION_MAX_H_SP = 2.0
#: ROUND 3: the height cut judges what a head's claim CAN carry: one head 1.0-1.6 sp (a hollow half up to 1.62: head_ink FINDINGS) plus a fat stem's stub each side
#: (a head with a stem each way: a unison; 0.9-1.0 sp each side on Litolff p2 glyph/2/0/8/12/0, 1.65 x 1.78 sp). Round 2's 1.5 refused three real heads Sean named
#: (a unison half 1.52, a quarter 1.78, a quarter 1.59); 2.0 is a head and a stub each way, no more.
#: ROUND 3: two heads' claimed strokes that TOUCH with a contact between these (sp) are two pieces of ONE ink the stroke map cut (a quarter rest's zigzag: 1.27 sp
#: between the stroke claimed by the head box above and the one claimed by the box below), neither is a whole head. Two heads a third apart touch TANGENTLY along
#: their whole width: contact 2.2-2.5 sp in all 15 touching pairs on the five pages that are chords (Litolff 2.29-2.54, Brahms 2.38-2.5). Both claims are refused.
CUT_THROUGH_CONTACT_MIN_SP = 0.9
CUT_THROUGH_CONTACT_MAX_SP = 1.7


def one_enabled() -> bool:
    """`OMR_PAGE_HEAD_ONE` (ROADMAP 2.290 steps 1-2), default OFF: allow-list."""
    return _flag(ONE_ENV)


def ledger_enabled() -> bool:
    """`OMR_PAGE_HEAD_LEDGER` (ROADMAP 2.290 step 4), default OFF; needs `OMR_PAGE_HEAD_ONE`."""
    return one_enabled() and _flag(LEDGER_ENV)


def is_head_ink(kind: str, w_sp: float, h_sp: float, thick_sp: float, length_sp: float) -> bool:
    """PURE. Can a page stroke of this shape be a head's ink? Never a stem (vertical), a ledger rung or staff-line residue (a thin horizontal,
    `LEDGER_MAX_THICK_SP`), a beam piece (`BEAM_MIN_W_SP` wide and `BEAM_MIN_ASPECT` flat) or an arc piece (a curve longer than `CURVE_MAX_LEN_SP`).
    A blob of any size can (Litolff fuses heads: only the part inside the box counts toward identity)."""
    if kind == "vertical":
        return False
    if kind == "horizontal":
        if thick_sp <= LEDGER_MAX_THICK_SP:
            # thin: a ledger rung (~2 sp long) or line residue -- unless it is no longer than a head is wide: the top / bottom of a HOLLOW head the staff-line
            # erase cut in two (Litolff p2, Sean's unison half note 2.289 tile 9: every box on it held no head ink by the old test)
            return length_sp <= HOLLOW_PIECE_MAX_LEN_SP and w_sp <= HOLLOW_PIECE_MAX_W_SP
        if w_sp >= BEAM_MIN_W_SP and h_sp > 0 and w_sp / h_sp >= BEAM_MIN_ASPECT:
            return False
        return True
    if kind == "curve":
        return length_sp <= CURVE_MAX_LEN_SP
    # a blob thinner than a stem's double is a stem / sharp-stem piece the finders left a blob (Litolff p2, Sean's sharp 2.285 r2 tile 12: 0.13 x 1.15 sp)
    return min(w_sp, h_sp) >= BLOB_MIN_SIDE_SP


def same_head(a: Dict[str, Any], b: Dict[str, Any], shared_px: float, sp: float) -> Optional[str]:
    """PURE. None when boxes `a` and `b` (dicts: `ink_px`, `cx`, `cy` = their head ink's pixel count and centre, page px; `tall`) are ONE head, else the
    reason they are not: `tall_read`, `no_head_ink`, `no_shared_ink`, `share_below`, `two_ovals`."""
    if a.get("tall") or b.get("tall"):
        return "tall_read"
    if not a["ink_px"] or not b["ink_px"]:
        return "no_head_ink"
    if shared_px <= 0:
        return "no_shared_ink"
    if shared_px < SHARE_MIN * min(a["ink_px"], b["ink_px"]):
        return "share_below"
    if boxes_a_third_apart(a, b, sp):
        return "boxes_a_third_apart"
    if one_head_stroke(a, b) and abs(a["cy"] - b["cy"]) < ANCHOR_MAX_DY_SP * sp:
        return None
    if abs(a["cx"] - b["cx"]) > OVAL_DX_SP * sp or abs(a["cy"] - b["cy"]) > OVAL_DY_SP * sp:
        return "two_ovals"
    return None


def boxes_a_third_apart(a: Dict[str, Any], b: Dict[str, Any], sp: float) -> bool:
    """PURE (ROUND 2). Two head-sized boxes whose centres stand `BOX_CENTRES_A_THIRD_SP` or more apart (vertically) hold two heads, never one."""
    ba, bb = a.get("box"), b.get("box")
    if not ba or not bb:
        return False
    if (ba[3] - ba[1]) > CLAIM_MAX_H_SP * sp or (bb[3] - bb[1]) > CLAIM_MAX_H_SP * sp:
        return False
    return abs((ba[1] + ba[3]) / 2.0 - (bb[1] + bb[3]) / 2.0) >= BOX_CENTRES_A_THIRD_SP * sp


def one_head_stroke(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """PURE. Both boxes stand mostly on the SAME page stroke (`anchor`) and that stroke is no bigger than one head (`anchor_head`): a head-sized stroke is one
    printed head, so the two boxes are one head wherever each was drawn on it (a box drawn half a step off its head puts the ink it CLIPS off-centre --
    measured, Litolff p2/p8/p11 round 1: 56 twin pairs read as two ovals). The oval test is for a stroke bigger than a head (fused heads)."""
    return a.get("anchor") is not None and a.get("anchor") == b.get("anchor") and bool(a.get("anchor_head"))


def partition(items: Sequence[Dict[str, Any]], shared: Any, sp: float, no_ink_iou: float) -> Tuple[List[List[int]], Dict[int, str], List[list]]:
    """PURE. The one-head partition of a page's notehead boxes. `items`: dicts with `scope` (page, system), `box` (page corners), `ink_px`, `cx`, `cy`,
    `tall`, `has_ink`; `shared(i, j)` = head-ink pixels the two boxes share. Returns (groups of indices -- each sorted, ordered by the group's leftmost x
    then index, as `gather.cluster_marks` --, `how` per index: `ink` | `alone` | `no_head_ink_twin` | `no_head_ink` | `tall_read`, and the decided
    pairs [i, j, reason or None] for the comparison census)."""
    from .gather import _iou as _box_iou
    parent = list(range(len(items)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    buckets: Dict[Any, List[int]] = {}
    for i, it in enumerate(items):
        buckets.setdefault(it["scope"], []).append(i)
    pairs: List[list] = []
    how: Dict[int, str] = {}
    comp: Dict[int, List[int]] = {i: [i] for i in range(len(items))}

    def one_oval(x: int, y: int) -> bool:
        if boxes_a_third_apart(items[x], items[y], sp):
            return False
        if one_head_stroke(items[x], items[y]) and abs(items[x]["cy"] - items[y]["cy"]) < ANCHOR_MAX_DY_SP * sp:
            return True
        return abs(items[x]["cx"] - items[y]["cx"]) <= OVAL_DX_SP * sp and abs(items[x]["cy"] - items[y]["cy"]) <= OVAL_DY_SP * sp
    for members in buckets.values():
        members.sort(key=lambda i: (items[i]["box"][0], i))
        joins: List[Tuple[float, int, int]] = []
        for a in range(len(members)):
            i = members[a]
            bi = items[i]["box"]
            for b in range(a + 1, len(members)):
                j = members[b]
                bj = items[j]["box"]
                if bj[0] >= bi[2]:
                    break
                if bj[1] >= bi[3] or bi[1] >= bj[3]:
                    continue
                sh = float(shared(i, j))
                why = same_head(items[i], items[j], sh, sp)
                small = min(items[i]["ink_px"], items[j]["ink_px"])
                pairs.append([i, j, why, round(sh / small, 3) if small else 0.0])
                if why is None:
                    joins.append((abs(items[i]["cx"] - items[j]["cx"]) + abs(items[i]["cy"] - items[j]["cy"]), i, j))
        # nearest pairs first; two groups join only if EVERY member of one lies in one oval with every member of the other (no chain: a box drawn
        # over both heads of a chord, its ink centre between them, never joins the two heads -- Litolff p2, 2.291 tile 10)
        for _d, i, j in sorted(joins):
            ri, rj = find(i), find(j)
            if ri == rj:
                continue
            if not all(one_oval(x, y) for x in comp[ri] for y in comp[rj]):
                for p in pairs:
                    if p[0] in (i, j) and p[1] in (i, j):
                        p[2] = "chain_across_two_ovals"
                continue
            parent[rj] = ri
            comp[ri] += comp.pop(rj)
        # a box on no head ink joins the INK head whose box it overlaps most at the old twin rule (one mark written once stays written once), else alone
        for i in members:
            if items[i]["ink_px"] or items[i].get("tall"):
                continue
            best = None
            for j in members:
                if j == i or not items[j]["ink_px"] or items[j].get("tall"):
                    continue
                v = _box_iou(items[i]["box"], items[j]["box"])
                if v > no_ink_iou and (best is None or (v, -j) > (best[0], -best[1])):
                    best = (v, j)
            if best is None:
                # no ink box twins it: another box on no head ink may (two cells' copies of one phantom) -- the old twin rule, so it is not written twice
                for j in members:
                    if j == i or items[j]["ink_px"] or items[j].get("tall"):
                        continue
                    v = _box_iou(items[i]["box"], items[j]["box"])
                    if v > no_ink_iou and (best is None or (v, -j) > (best[0], -best[1])):
                        best = (v, j)
            if best is not None:
                ri, rj = find(i), find(best[1])
                if ri != rj:
                    parent[ri] = rj
                    comp[rj] += comp.pop(ri)
                how[i] = "no_head_ink_twin"
            else:
                how[i] = "no_head_ink"
    groups: Dict[int, List[int]] = {}
    for i in range(len(items)):
        groups.setdefault(find(i), []).append(i)
    out = sorted((sorted(g) for g in groups.values()), key=lambda g: (min(items[i]["box"][0] for i in g), g[0]))
    for g in out:
        for i in g:
            if i in how:
                continue
            how[i] = "tall_read" if items[i].get("tall") else ("ink" if len(g) > 1 else "alone")
    return out, how, pairs


def choose_claims(ovals: Dict[int, Dict[int, int]], totals: Dict[int, int], ok: Dict[int, bool]) -> Tuple[Dict[int, List[int]], Dict[str, int]]:
    """PURE. `ovals` = {head: {stroke: its pixels inside the head's oval}}; `totals` = {stroke: its pixels}; `ok` = {stroke: head-shaped and no bigger
    than a head}. Returns ({head: [claimed strokes]}, census of strokes NOT claimed by reason). A stroke is claimed by the ONE head whose oval holds
    `CLAIM_SHARE_MIN` of it, when no other head's oval holds `OTHER_HEAD_MAX` of it."""
    by_stroke: Dict[int, List[Tuple[int, float]]] = {}
    for h, d in ovals.items():
        for s, n in d.items():
            t = totals.get(s) or 0
            if t > 0:
                by_stroke.setdefault(s, []).append((h, n / float(t)))
    out: Dict[int, List[int]] = {h: [] for h in ovals}
    cen: Dict[str, int] = {}
    for s in sorted(by_stroke):
        hs = sorted(by_stroke[s], key=lambda t: (-t[1], t[0]))
        top_h, top = hs[0]
        if top < CLAIM_SHARE_MIN:
            continue                                   # a sliver of a neighbouring stroke inside the oval: not this head's ink
        if not ok.get(s, False):
            cen["not_head_shaped_or_fused"] = cen.get("not_head_shaped_or_fused", 0) + 1
            continue
        if len(hs) > 1 and hs[1][1] >= OTHER_HEAD_MAX:
            cen["shared_by_two_heads"] = cen.get("shared_by_two_heads", 0) + 1
            continue
        out[top_h].append(int(s))
    return out, cen


def claim_size_reason(w_sp: float, h_sp: float) -> Optional[str]:
    """PURE (ROUND 2). None when a union of claimed strokes `w_sp` x `h_sp` staff spaces (the head's own bar's) is ONE head's ink, else why not: `too_small` (a
    sliver: a side under `CLAIM_UNION_MIN_SP`) or `too_tall` (more than one head: over `CLAIM_UNION_MAX_H_SP`)."""
    if min(w_sp, h_sp) < CLAIM_UNION_MIN_SP:
        return "too_small"
    if h_sp > CLAIM_UNION_MAX_H_SP:
        return "too_tall"
    return None


class OneHeads:
    """What `read_one` found on one page: `items` (one per notehead box: key, cell, gi, box, cls, conf, ink_px, cx, cy, tall), `groups` (index lists),
    `how` (per index), `heads` (one dict per group with ink: ordinal, members, rep, oval, oval_why, strokes), `census`."""

    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []
        self.groups: List[List[int]] = []
        self.how: Dict[int, str] = {}
        self.heads: List[Dict[str, Any]] = []
        self.census: Dict[str, Any] = {}
        self.group_of_key: Dict[str, int] = {}
        self.apart: Dict[int, List[list]] = {}


def _label_image(pm: Any, shape_px: Sequence[int]) -> np.ndarray:
    """The page map's strokes painted into one label image in the map's reduced frame (0 = none, i + 1 = stroke i), no dilation (every pixel counted
    once, exactly)."""
    s = float(pm.scale)
    h, w = int(np.ceil(shape_px[0] * s)) + 2, int(np.ceil(shape_px[1] * s)) + 2
    lab = np.zeros((h, w), np.int32)
    for i, (m, x0, y0) in enumerate(pm.masks):
        if getattr(m, "size", 0) == 0:
            continue
        mh, mw = m.shape
        y1, x1 = min(h, y0 + mh), min(w, x0 + mw)
        if y1 <= y0 or x1 <= x0 or x0 < 0 or y0 < 0:
            continue
        sub = lab[y0:y1, x0:x1]
        sub[m[:y1 - y0, :x1 - x0].astype(bool)] = i + 1
    return lab


def read_one(pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]], pm: Any) -> Optional[OneHeads]:
    """ROADMAP 2.290 (flag `OMR_PAGE_HEAD_ONE`), STAGED GATHER, decides nothing: the page's notehead boxes partitioned into heads by their ink (section
    doc), each head's oval and the page strokes it claims. None where there is no page map or raster (the old identities then stand). The work is
    `core` (the same function the real-case fixtures replay on their crops)."""
    if pm is None or not getattr(pm, "strokes", None) or not getattr(pm, "masks", None):
        return None
    binary = getattr(getattr(pws, "page", None), "binary", None)
    if binary is None:
        return None
    from . import record as R
    from .record import Subject
    from . import head_ink
    from . import box_kind as _box_kind
    from .gather import _cell_grid, _page_box
    t0 = time.time()
    sp = float(pm.sp)
    cell_by_key: Dict[Tuple[int, int, int, int], Any] = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c
    foreign: List[Tuple[float, float, float, float]] = []
    items: List[Dict[str, Any]] = []
    for ck, dets in detections.items():
        sub = Subject.from_key(ck)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        if c is None:
            continue
        grid = _cell_grid(c)
        up = getattr(c, "upscale_factor", None)
        sp_cell = (2.0 * grid[1] / up) if (grid is not None and up) else sp      # the head's OWN bar's space (page-facts: measure locally)
        for gi, d in enumerate(dets):
            pb = _page_box(c, d)
            if pb is None:
                continue
            if head_ink.is_foreign_class(str(d.smufl_name)):
                foreign.append(tuple(float(v) for v in pb))
            if getattr(d, "category", None) != "notehead":
                continue
            items.append(dict(key=R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi).to_key(), cell=(sub.page, sub.system, sub.staff, sub.cell),
                              gi=gi, box=tuple(float(v) for v in pb), cls=str(d.smufl_name), conf=float(getattr(d, "confidence", 0.0) or 0.0),
                              scope=(sub.page, sub.system), sp_head=float(sp_cell), tall=bool(getattr(d, _box_kind.TALL_READ_ATTR, False))))
    lab = _label_image(pm, binary.shape)
    props = []
    for st in pm.strokes:
        spl = float(getattr(st, "staff_space_local", None) or sp) or sp
        props.append((str(st.kind), float(st.box[2]) / spl, float(st.box[3]) / spl, float(st.thickness_sp), float(st.length_sp)))
    touches = {i: [(int(j), float(c)) for j, c in (getattr(st, "touches", None) or ())] for i, st in enumerate(pm.strokes)}
    out = core(items, foreign, lab, props, binary, float(pm.scale), sp, touches=touches)
    out.census["seconds"] = round(time.time() - t0, 2)
    _dump_cases(out, items, foreign, lab, props, binary, float(pm.scale), sp, int(getattr(pws.page, "page_index", 0)), touches)
    return out


def core(items: List[Dict[str, Any]], foreign: Sequence[Sequence[float]], lab: np.ndarray, props: Sequence[Tuple[str, float, float, float, float]],
         binary: Any, s: float, sp: float, _no_ink: Optional[frozenset] = None,
         touches: Optional[Dict[int, Sequence[Tuple[int, float]]]] = None) -> OneHeads:
    """The one-head reading on one frame (a page, or a real-case crop): `items` = the notehead boxes (key, cell, gi, box, cls, conf, scope, sp_head,
    tall), `foreign` = boxes of the classes `head_ink` treats as another mark's, `lab` = the page map's label image (reduced frame, scale `s`, 0 = none,
    i + 1 = stroke i), `props` = per stroke (kind, w_sp, h_sp, thickness_sp, length_sp), `binary` = the page raster (0 = ink) in the same page-px frame."""
    from . import head_extent
    from .gather import MARK_GROUP_IOU
    out = OneHeads()
    out.items = list(items)
    n_st = len(props)
    head_lab = np.zeros(n_st + 1, bool)
    claim_ok: Dict[int, bool] = {}
    for i, (kind, w_sp, h_sp, thick, length) in enumerate(props):
        hi = is_head_ink(str(kind), float(w_sp), float(h_sp), float(thick), float(length))
        head_lab[i + 1] = hi
        claim_ok[i] = bool(hi and w_sp <= CLAIM_MAX_W_SP and h_sp <= CLAIM_MAX_H_SP)
    hmask = head_lab[lab]
    H, W = lab.shape

    def rrect(b: Sequence[float]) -> Tuple[int, int, int, int]:
        return (max(0, int(np.floor(b[0] * s))), max(0, int(np.floor(b[1] * s))), min(W, int(np.ceil(b[2] * s))), min(H, int(np.ceil(b[3] * s))))
    px_sp2 = 1.0 / (s * s * sp * sp)
    for it in out.items:
        x0, y0, x1, y1 = rrect(it["box"])
        m = hmask[y0:y1, x0:x1] if (x1 > x0 and y1 > y0) else np.zeros((0, 0), bool)
        n = int(m.sum())
        if n * px_sp2 < HEAD_INK_MIN_SP2 or (_no_ink and it["key"] in _no_ink):
            n = 0
        it["ink_px"] = n
        it["anchor"], it["anchor_head"] = None, False
        if n:
            lb = lab[y0:y1, x0:x1][m]
            cnt = np.bincount(lb)
            a = int(cnt.argmax())
            it["anchor"], it["anchor_head"] = a - 1, bool(claim_ok.get(a - 1, False))
            ys, xs = np.nonzero(m)
            it["cx"], it["cy"] = (x0 + float(xs.mean()) + 0.5) / s, (y0 + float(ys.mean()) + 0.5) / s
        else:
            it["cx"] = (it["box"][0] + it["box"][2]) / 2.0
            it["cy"] = (it["box"][1] + it["box"][3]) / 2.0

    def shared(i: int, j: int) -> int:
        a, b = out.items[i]["box"], out.items[j]["box"]
        x0, y0, x1, y1 = rrect((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))
        if x1 <= x0 or y1 <= y0:
            return 0
        return int(hmask[y0:y1, x0:x1].sum())
    groups, how, pairs = partition(out.items, shared, sp, MARK_GROUP_IOU)
    out.groups, out.how = groups, how
    out.apart = {}
    for i, j, why, sh in pairs:
        if why is not None:
            out.apart.setdefault(i, []).append([out.items[j]["key"], why, sh])
            out.apart.setdefault(j, []).append([out.items[i]["key"], why, sh])
    # each head with ink: its representative (the most confident member with ink, the export's own write-once choice), its oval, and the strokes in it
    totals = np.bincount(lab.ravel(), minlength=n_st + 1)
    ovals: Dict[int, Dict[int, int]] = {}
    oval_box: Dict[int, Any] = {}
    oval_why: Dict[int, Optional[str]] = {}
    oval_from: Dict[int, str] = {}
    reps: Dict[int, int] = {}
    for gi_, g in enumerate(groups):
        for i in g:
            out.group_of_key[out.items[i]["key"]] = gi_
        inked = [i for i in g if out.items[i]["ink_px"] and not out.items[i].get("tall")]
        if not inked:
            continue
        rep = min(inked, key=lambda i: (-out.items[i]["conf"], out.items[i]["key"]))
        reps[gi_] = rep
        it = out.items[rep]
        box = it["box"]
        others = [out.items[j]["box"] for g2 in groups if g2 is not g for j in g2[:1]
                  if abs(out.items[j]["box"][0] - box[0]) < 4 * sp and abs(out.items[j]["box"][1] - box[1]) < 4 * sp]
        got = head_extent.ink_extent(binary, box, float(it.get("sp_head") or sp),
                                     [f for f in foreign if abs(f[0] - box[0]) < 4 * sp and abs(f[1] - box[1]) < 4 * sp], others)
        oval_why[gi_] = got["why"]
        if got["why"] is not None or got["extent"] is None:
            # the trim could not cut one head out of the ink (a head fused with its stem or a chord neighbour: `too_tall`, `not_one_head`, ...): the oval is
            # a printed head's size (`OVAL_W_SP` x `OVAL_H_SP`, the engraving size `stroke_owner` names) centred on the head's OWN ink -- still the ink's
            # place, never the detector's rectangle; a stroke bigger than a head, or held by another head's oval, is still not claimed
            hs = float(it.get("sp_head") or sp)
            ext = [it["cx"] - OVAL_W_SP * hs / 2.0, it["cy"] - OVAL_H_SP * hs / 2.0, it["cx"] + OVAL_W_SP * hs / 2.0, it["cy"] + OVAL_H_SP * hs / 2.0]
            oval_from[gi_] = "ink_centre"
        else:
            ext = [float(v) for v in got["extent"]]
            oval_from[gi_] = "ink_extent"
        oval_box[gi_] = ext
        x0, y0, x1, y1 = rrect((ext[0] - 1.0 / s, ext[1] - 1.0 / s, ext[2] + 1.0 / s, ext[3] + 1.0 / s))
        if x1 <= x0 or y1 <= y0:
            continue
        cnt = np.bincount(lab[y0:y1, x0:x1].ravel(), minlength=n_st + 1)
        ovals[gi_] = {int(k) - 1: int(cnt[k]) for k in np.nonzero(cnt)[0] if k > 0}
    claims, ccen = choose_claims(ovals, {i: int(totals[i + 1]) for i in range(n_st)}, claim_ok)
    # ROUND 2: a head's claim is a WHOLE head -- the union of the strokes it claims lies inside one head's ink size (`claim_size_reason`); else it is refused
    # whole, counted, and its ink stays with the cell boxes (Sean's tiles 8, 9, 10: a sliver, half a rest, a thin sliver)
    refused_alone: List[str] = []
    if any(claims.values()):
        from scipy import ndimage
        objs = ndimage.find_objects(lab, max_label=n_st)
        for gi_, st_ in list(claims.items()):
            if not st_:
                continue
            sl = [objs[i] for i in st_ if i < len(objs) and objs[i] is not None]
            if not sl:
                continue
            hs = float(out.items[reps[gi_]].get("sp_head") or sp)
            w_sp = (max(t[1].stop for t in sl) - min(t[1].start for t in sl)) / s / hs
            h_sp = (max(t[0].stop for t in sl) - min(t[0].start for t in sl)) / s / hs
            why = claim_size_reason(w_sp, h_sp)
            if why:
                if len(groups[gi_]) == 1:
                    refused_alone.append(out.items[groups[gi_][0]]["key"])
                ccen["claim_size:" + why] = ccen.get("claim_size:" + why, 0) + 1
                ccen["claim_size_strokes"] = ccen.get("claim_size_strokes", 0) + len(st_)
                claims[gi_] = []
    if touches:
        owner_of = {i: g_ for g_, st_ in claims.items() for i in st_}
        cut: set = set()
        for i, g_ in owner_of.items():
            for j, c in touches.get(i, ()):
                h2 = owner_of.get(int(j))
                if h2 is not None and h2 != g_ and CUT_THROUGH_CONTACT_MIN_SP <= float(c) <= CUT_THROUGH_CONTACT_MAX_SP:
                    cut.add(g_)
                    cut.add(h2)
        for g_ in sorted(cut):
            if claims.get(g_):
                if len(groups[g_]) == 1:
                    refused_alone.append(out.items[groups[g_][0]]["key"])
                ccen["claim_size:cut_through_one_ink"] = ccen.get("claim_size:cut_through_one_ink", 0) + 1
                claims[g_] = []
    cen: Dict[str, Any] = dict(boxes=len(out.items), heads=sum(1 for g in groups if g), heads_with_ink=len(reps), oval=len(oval_box), claims=0,
                               claimed_strokes=0, oval_why={}, how={}, pairs_joined=sum(1 for p in pairs if p[2] is None), pairs_kept_apart={})
    for v in how.values():
        cen["how"][v] = cen["how"].get(v, 0) + 1
    for p in pairs:
        if p[2] is not None:
            cen["pairs_kept_apart"][p[2]] = cen["pairs_kept_apart"].get(p[2], 0) + 1
    for g_, w in oval_why.items():
        if w is not None:
            k = str(w).split(":")[0]
            cen["oval_why"][k] = cen["oval_why"].get(k, 0) + 1
    for gi_, rep in sorted(reps.items()):
        g = groups[gi_]
        st = claims.get(gi_, [])
        h = dict(ordinal=len(out.heads), group=gi_, members=[out.items[i]["key"] for i in g], rep=out.items[rep]["key"],
                 oval=None if gi_ not in oval_box else [round(v, 1) for v in oval_box[gi_]], oval_why=oval_why.get(gi_),
                 oval_from=oval_from.get(gi_), strokes=sorted(st),
                 staff=[out.items[rep]["cell"][1], out.items[rep]["cell"][2]])
        if st:
            cen["claims"] += 1
            cen["claimed_strokes"] += len(st)
        out.heads.append(h)
    cen["not_claimed"] = ccen
    cen["oval_from"] = dict(collections.Counter(oval_from.values()))
    out.census = cen
    if refused_alone and _no_ink is None:
        # a lone box whose claim was refused for its size stands on ink that is NOT one head's (a sliver, half a rest): it is no confirmed head. It is read again
        # as a box on no head ink -- the old twin rule (`gather.MARK_GROUP_IOU`) joins it to the head box it overlaps, else it stands alone, counted -- so what
        # the file writes there is what it wrote without the flag, never a new note from ink that is not a head (Litolff p11 m104: the quarter rest's box
        # gained a quarter C3 when its twin fold was undone and its claim refused)
        again = core(items, foreign, lab, props, binary, s, sp, _no_ink=frozenset(refused_alone), touches=touches)
        again.census["size_fallback"] = len(refused_alone)
        return again
    return out


#: ROADMAP 2.290 real-case fixtures (CLAUDE rule 7: a control for a page rule is built from the pixels of a mark Sean has named). A JSON file
#: {"out_dir", "plate", "cases": [{"id", "page", "box"}]}; when this names one, `read_one` writes, per case on the page, the crop `core` reads (label image,
#: raster, the notehead and foreign boxes, stroke props) to `out_dir/<id>.npz`. Benchmark tooling only: it changes nothing the reader decides or files.
CASES_DUMP_ENV = "OMR_PAGE_HEAD_CASES_DUMP"
#: the crop around a case's box, staff spaces each side
CASE_MARGIN_SP = 4.0


def _cases_for(spec: Dict[str, Any], sp: Optional[float]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """The spec's cases for this document: a one-plate spec (`plate`, `cases`), or `plates` = {name: {"sp": [lo, hi], "cases": [...]}} picked by the
    page's staff space (one run gathers both plates; the plate is not otherwise known in GATHER)."""
    if "plates" not in spec:
        return spec.get("plate"), list(spec.get("cases") or ())
    for name, d in spec["plates"].items():
        lo, hi = d["sp"]
        if sp is not None and lo <= float(sp) <= hi:
            return name, list(d.get("cases") or ())
    return None, []


_LAST_SP: Dict[str, float] = {}


def case_file_name(case_id: str) -> str:
    return "%s.npz" % "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(case_id))


def _dump_cases(out: OneHeads, items: Sequence[Dict[str, Any]], foreign: Sequence[Sequence[float]], lab: np.ndarray, props: Sequence[Any],
                binary: Any, s: float, sp: float, page: int, touches: Optional[Dict[int, Any]] = None) -> None:
    path = os.environ.get(CASES_DUMP_ENV, "").strip()
    if not path:
        return
    import json
    import pathlib
    spec = json.loads(pathlib.Path(path).read_text())
    od = pathlib.Path(spec["out_dir"])
    od.mkdir(parents=True, exist_ok=True)
    _LAST_SP["sp"] = sp
    plate, cases = _cases_for(spec, sp)
    for case in cases:
        if int(case["page"]) != page:
            continue
        b = [float(v) for v in case["box"]]
        m = CASE_MARGIN_SP * sp
        rx0, ry0 = max(0, int(np.floor((b[0] - m) * s))), max(0, int(np.floor((b[1] - m) * s)))
        rx1, ry1 = min(lab.shape[1], int(np.ceil((b[2] + m) * s))), min(lab.shape[0], int(np.ceil((b[3] + m) * s)))
        ox, oy = rx0 / s, ry0 / s                       # the crop's origin, page px (the label crop starts exactly there)
        px0, py0 = int(round(ox)), int(round(oy))
        px1, py1 = int(round(rx1 / s)), int(round(ry1 / s))
        sub_lab = lab[ry0:ry1, rx0:rx1]
        ids = sorted(int(v) for v in np.unique(sub_lab) if v > 0)
        remap = np.zeros(int(lab.max()) + 1, np.int32)
        for n, v in enumerate(ids):
            remap[v] = n + 1
        cx0, cy0, cx1, cy1 = ox, oy, rx1 / s, ry1 / s

        def inside(bx: Sequence[float]) -> bool:
            return bx[2] > cx0 and bx[0] < cx1 and bx[3] > cy0 and bx[1] < cy1
        mine = [it for it in items if inside(it["box"])]
        its = [dict(key=it["key"], cell=list(it["cell"]), gi=it["gi"], box=[it["box"][0] - ox, it["box"][1] - oy, it["box"][2] - ox, it["box"][3] - oy],
                    cls=it["cls"], conf=it["conf"], scope=list(it["scope"]), sp_head=it.get("sp_head"), tall=it.get("tall")) for it in mine]
        fg = [[f[0] - ox, f[1] - oy, f[2] - ox, f[3] - oy] for f in foreign if inside(f)]
        keys = {it["key"] for it in mine}
        meta = dict(case=case, plate=plate, page=page, origin=[ox, oy], raster_origin=[px0, py0], scale=s, sp=sp, items=its, foreign=fg,
                    props=[list(props[v - 1]) for v in ids], stroke_ids=[v - 1 for v in ids],
                    touches={str(n): [[int(remap[int(j) + 1]) - 1, float(c)] for j, c in (touches or {}).get(v - 1, ()) if int(j) + 1 < len(remap) and remap[int(j) + 1] > 0] for n, v in enumerate(ids)},
                    page_reading=dict(groups={k: out.group_of_key.get(k) for k in sorted(keys)},
                                      heads=[h for h in out.heads if any(k in keys for k in h["members"])]))
        np.savez_compressed(od / case_file_name(case["id"]), lab=remap[sub_lab], binary=binary[py0:py1, px0:px1],
                            meta=np.array(json.dumps(meta, default=str)))


def mark_group_partition(oh: Optional[OneHeads]) -> Optional[Tuple[Dict[str, int], Dict[str, str]]]:
    """For `gather.gather_mark_groups`: ({notehead box key: page-head group index}, {box key: how}). None without a page head list."""
    if oh is None:
        return None
    return dict(oh.group_of_key), {oh.items[i]["key"]: oh.how.get(i, "") for i in range(len(oh.items))}


def mark_group_detail(oh: OneHeads) -> Dict[str, Dict[str, Any]]:
    """The fields the notehead `Q.MARK_GROUP` rows carry under the flag: `identity` page_head, `head_how`, the box's head ink (px of the page map's
    frame) and its centre (page px), and `apart` -- every overlapping box of its system it was NOT joined with, [key, reason, shared share] (step 1's
    comparison reads them; the one identity is the group id itself)."""
    out: Dict[str, Dict[str, Any]] = {}
    for i, it in enumerate(oh.items):
        d: Dict[str, Any] = {"identity": "page_head", "head_how": oh.how.get(i, ""), "head_ink_px": int(it.get("ink_px") or 0),
                             "ink_centre": [round(float(it["cx"]), 1), round(float(it["cy"]), 1)]}
        if getattr(oh, "apart", None) and oh.apart.get(i):
            d["apart"] = oh.apart[i]
        out[it["key"]] = d
    return out


def apply_to_page_marks(marks: Any, oh: Optional[OneHeads]) -> Any:
    """ROADMAP 2.290 step 2: the head boxes' `Q.PAGE_MARK` ids ARE the page heads (one identity; the page owner, 2.240, then rules once per head).
    Every other family's marks are kept. Ordinals renumbered as `page_marks.link` numbers them (by the smallest (cell, glyph) of each mark)."""
    if oh is None or marks is None:
        return marks
    keys = set(oh.group_of_key)
    groups: List[List[str]] = []
    for n in sorted(marks.members):
        rest = [k for k in marks.members[n] if k not in keys]
        if rest:
            groups.append(rest)
    by_g: Dict[int, List[str]] = {}
    for k, g in oh.group_of_key.items():
        if k in marks.mark_of:
            by_g.setdefault(g, []).append(k)
    head_of: Dict[str, str] = {}
    for g, ks in by_g.items():
        groups.append(ks)
        for k in ks:
            head_of[k] = "page_head" if len(ks) > 1 else "page_head_alone"

    def order_key(k: str) -> Tuple[int, ...]:
        return tuple(int(t) for t in k.split("/")[1:6])
    groups = [sorted(g, key=order_key) for g in groups]
    groups.sort(key=lambda g: min(order_key(k) for k in g))
    marks.mark_of, marks.members = {}, {}
    for n, g in enumerate(groups):
        marks.members[n] = g
        for k in g:
            marks.mark_of[k] = n
    for k, w in head_of.items():
        marks.why[k] = w
    return marks


def _dump_held(held: Dict[int, str], page: int) -> None:
    """Benchmark tooling (`OMR_PAGE_HEAD_CASES_DUMP`): add to each real-case crop of this page which of its page strokes an earlier page-wide claim holds
    (so a fixture replays the claim exactly as `file_one_claims` files it)."""
    path = os.environ.get(CASES_DUMP_ENV, "").strip()
    if not path:
        return
    import json
    import pathlib
    spec = json.loads(pathlib.Path(path).read_text())
    od = pathlib.Path(spec["out_dir"])
    for case in _cases_for(spec, _LAST_SP.get("sp"))[1]:
        f = od / case_file_name(case["id"])
        if int(case["page"]) != page or not f.exists():
            continue
        z = dict(np.load(f, allow_pickle=False))
        meta = json.loads(str(z["meta"]))
        meta["held"] = {str(i): held[i] for i in meta["stroke_ids"] if i in held}
        z["meta"] = np.array(json.dumps(meta, default=str))
        np.savez_compressed(f, **z)


def file_one_claims(log: Any, pws: Any, oh: Optional[OneHeads], *, progress: bool = False) -> None:
    """ROADMAP 2.290 step 4 (flag `OMR_PAGE_HEAD_LEDGER`): one `Q.CLAIMED_AREA` row per head that claims a stroke (section doc), and one census row.
    AFTER every earlier page-wide claim (accidental ink, 2.285, is the last before the heads); the ledger's one settle in ADJUDICATE keeps every earlier
    claim's ink (tier 0 / 1), so nothing here re-reads them."""
    if oh is None or not ledger_enabled():
        return
    from . import record as R
    from .record import Q, READERS
    from .gather import FRAME_PAGE
    from .record import Scope
    p = int(getattr(pws.page, "page_index", 0))
    sub = R.page(p)
    # claimed ink is final (2.277): a page stroke an EARLIER page-wide READ claim names by id (tremolo, accidental ink, the claim names) is MARKED on the head's
    # row, never claimed again (the ledger's tier-0 settle would keep it the earlier claim's anyway; this keeps the head's own row honest)
    held: Dict[int, str] = {}
    for r in log.rows(Q.CLAIMED_AREA, sub, scope=Scope.SELF_AND_DESCENDANTS):
        d = r.detail or {}
        if d.get("unit") == UNIT and d.get("source") != ONE_SOURCE and d.get("standing", "READ") == "READ":
            for i in (d.get("page_strokes") or ()):
                held.setdefault(int(i), str(d.get("owner") or ""))
    filed = marked = 0
    for h in oh.heads:
        mine = [i for i in h["strokes"] if i not in held]
        h["marked"] = [[i, held[i]] for i in h["strokes"] if i in held]
        marked += len(h["marked"])
        h["strokes"] = mine
        if not mine:
            continue
        log.observe(sub, Q.CLAIMED_AREA, int(h["ordinal"]), reader=READERS.CV_PAGE_HEADS, frame=FRAME_PAGE, owner=ONE_OWNER, unit=UNIT, standing="READ",
                    source=ONE_SOURCE, how="page_head_oval", page_strokes=list(mine), members=list(h["members"]), rep=h["rep"],
                    oval=h["oval"], staff=h["staff"], marked=h["marked"])
        filed += 1
    _dump_held(held, p)
    cen = dict(oh.census, rows=filed, marked_earlier_claim=marked)
    log.observe(sub, Q.CLAIMED_AREA, "census", reader=READERS.CV_PAGE_HEADS, frame=FRAME_PAGE, owner=ONE_SOURCE, unit="page_ink_census", standing="READ",
                source=ONE_SOURCE, **cen)
    if progress:
        print("  gather page heads (2.290) p%s: %d heads, %d claims (%s)" % (p, len(oh.heads), filed, {k: cen[k] for k in ("boxes", "heads", "oval", "claimed_strokes")}))


def gather_one_heads(pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]], pm: Any, *,
                     progress: bool = False) -> Optional[OneHeads]:
    """ROADMAP 2.290 (flag `OMR_PAGE_HEAD_ONE`), STAGED GATHER: read the page's heads once (decides nothing, files nothing). Placed AFTER the final box
    set, the page map and the glyph strokes, BEFORE `page_marks` and `gather_mark_groups` (both file this partition for heads)."""
    if not one_enabled():
        return None
    oh = read_one(pws, cells, local, detections, pm)
    if oh is not None and progress:
        print("  gather page heads (2.290) p%s: %d boxes -> %d heads (%s s)" % (getattr(pws.page, "page_index", 0), len(oh.items), len(oh.groups),
                                                                                  oh.census.get("seconds")))
    return oh
