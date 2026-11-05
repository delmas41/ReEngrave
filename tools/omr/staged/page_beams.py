"""ROADMAP 2.260c M4a -- ONE BEAM READER ON THE PAGE STROKE MAP, filed beside the cell beam reads and read by NOTHING (STAGED GATHER; flag
`OMR_PAGE_BEAMS`, default OFF).

    docs/plan-2026-11-04-page-beams-m4.md §3, §4 "M4a"; docs/plan-2026-11-03-page-ledger.md §C M4.

WHAT. The page stroke map (`page_strokes.PageMap`, in memory, `Q.PAGE_STROKE` rows) already holds every beam, stem, hook and slur of the page as ONE
stroke each, whole, in page px. This reader reads NO RASTER: it walks outward from each `Q.STEM` (moved to page px) over those strokes, with the
landed cut-offs and nothing new --

  * a stroke's ROLE is `beam_strokes.role_of(..., face_join=True, trough=True)` -- the 2.202/2.202f function `adjudicate_duration` already calls on the
    cell's strokes (BEAM_MIN_THICKNESS_SP 0.5, the trough 0.4375, HOOK_MAX_SPACES 1.6, FACE_JOIN_MAX_SPACES 1.0), only handed the strokes NEAR this
    one (a position grid) instead of the whole cell;
  * a stem END's reading is `beam_strokes.tip_reading` over TIP_OUTWARD_SPACES / TIP_INWARD_SPACES, the same function, once per end of each stem stroke,
    plus the not-touching join `JOIN_MAX_GAP_SPACES` (the box-gap join of 2.202b, `face_join=False`) so the two joins can be compared;
  * a BEAMED GROUP is the stems joined through beam-role strokes (union-find), so a beam the cell edge cut in two is one beam here. Every beam is within a bar (Sean 2026-11-04); this reader joins stems only through a beam stroke and does not check bars (not built, Sean 2026-11-04 'don't add more work').

WHAT IT FILES (a SIBLING of `Q.PAGE_STROKE`, not columns added to it: `Q.PAGE_STROKE` is filed by `page_strokes.gather_page_strokes` BEFORE the arcs
are traced -- and before the stems exist -- and is referenced by the arc claims' `page_strokes` ids; the stems are read later, so a row about them
cannot be on the stroke's row. Rows are append-only):

  Q.PAGE_BEAM       one row per horizontal / curve page stroke with a role other than `other`. value = the role; detail: `ordinal` (the
                    `Q.PAGE_STROKE` ordinal), `stems` (ordinals of the vertical strokes it joins, by touch or face), `stems_by_face`, `group`, thickness
                    with its margin to BEAM_MIN_THICKNESS_SP, `head_fused`, `claimed_by`, and `cells` (the cell crops that hold its stems: ONE reading, ONE page-stroke id, handed to every cell view).
  Q.PAGE_BEAM_TIP   one row per END of each stem stroke a `Q.STEM` row lands on. value = the number of beam levels at the tip; detail: `stem` (ordinal),
                    `stem_rows` (the `Q.STEM` row ids, twins from two cells), `end` ("top" / "bottom"), `beams`, `fused`, `joined`, `joined_gap`, `hooks`,
                    `stubs`, `doubt`, `stem_beamed`, `tip_clean`.
  Q.PAGE_BEAM  value "census": role counts (including `other`), groups, cross-barline groups.

It decides nothing. Duration stays in `adjudicate_duration` (an eighth stands only on a flag or beam read on its stem, CLAUDE §4); NOTHING READS THESE
ROWS in M4a, so the exported file is byte-identical with the flag on.

CONVENTION ASSUMED: the page stroke map holds a beam whole (a beam never has its ink cut by a cell edge), so the cell reads' guards for a cut beam
are not needed here. WHAT WOULD FALSIFY IT: a beam the carved barline column cuts in two (a beam crossing a rule loses the rule's width of ink);
that case is counted as `cut_by_column`, not guessed whole. NOT CONFIRMED beyond the two plates.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import beam_strokes as BS
from .beam_strokes import StrokeView

DERIVED_CHECK = False
ENV = "OMR_PAGE_BEAMS"
#: A position grid: strokes are registered in every bin their box touches, bins this many staff spaces on a side.
GRID_SPACES = 8.0
#: The strokes a role is judged against: those whose box meets this stroke's box grown by this many spaces (a stem hangs up to FACE_JOIN_MAX_SPACES
#: = 1.0 below a beam's face, so 1.5 holds the stem and the paper between).
NEIGHBOUR_SPACES = 1.5
#: The strokes a stem end is read against: its box grown by this many spaces (the tip window reaches 0.5 out and 3.3 in; the face join 1.0 + a beam).
TIP_REACH_SPACES = 2.5

def enabled() -> bool:
    """`OMR_PAGE_BEAMS` (ROADMAP 2.260c M4a), default OFF: allow-list, so an empty value or a typo cannot switch a document onto an unpriced change."""
    return os.environ.get(ENV, "0").strip().lower() in ("1", "true", "yes", "on")


# ───────────────────────────── a position index ─────────────────────────────

class Grid:
    """Boxes (x, y, w, h) indexed by position: `query(box)` returns the indices of the boxes that meet `box`, in index order. A box is registered in
    every bin it touches, so a long slur or a barline costs its length in bins once and a query costs the bins it covers."""

    def __init__(self, boxes: Sequence[Sequence[float]], bin_px: float):
        self.bin = max(1.0, float(bin_px))
        self.boxes = boxes
        self.bins: Dict[Tuple[int, int], List[int]] = {}
        for i, b in enumerate(boxes):
            for key in self._keys(b[0], b[1], b[0] + b[2], b[1] + b[3]):
                self.bins.setdefault(key, []).append(i)

    def _keys(self, x0: float, y0: float, x1: float, y1: float):
        s = self.bin
        for ix in range(int(x0 // s), int(x1 // s) + 1):
            for iy in range(int(y0 // s), int(y1 // s) + 1):
                yield (ix, iy)

    def query(self, box: Sequence[float], grow: float = 0.0) -> List[int]:
        x0, y0, x1, y1 = box[0] - grow, box[1] - grow, box[0] + box[2] + grow, box[1] + box[3] + grow
        got = set()
        for key in self._keys(x0, y0, x1, y1):
            for i in self.bins.get(key, ()):
                if i in got:
                    continue
                b = self.boxes[i]
                if b[0] <= x1 and b[0] + b[2] >= x0 and b[1] <= y1 and b[1] + b[3] >= y0:
                    got.add(i)
        return sorted(got)


def _covers(box: Sequence[float], head: Sequence[float]) -> bool:
    """`beam_strokes._covers_head` on plain boxes: the stroke's box holds at least half of the head's box."""
    ix = min(box[0] + box[2], head[0] + head[2]) - max(box[0], head[0])
    iy = min(box[1] + box[3], head[1] + head[3]) - max(box[1], head[1])
    return ix > 0 and iy > 0 and ix * iy >= 0.5 * head[2] * head[3]


# ───────────────────────────── the reader ─────────────────────────────

def read_page(views: Sequence[StrokeView], stems: Sequence[Dict[str, Any]], sp: float, *, heads: Sequence[Sequence[float]] = (),
              claimed: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    """The page's beams (module doc). Pure: `views` are the page strokes in page px (`ordinal` = index in the list), `stems` the `Q.STEM` rows in page px
    (`{"box": (x, y, w, h), "row": id}`), `sp` the page's staff space in px, `heads` page-px head boxes, `claimed` {stroke ordinal: owner} of ink an
    earlier owner claimed. Each stem may name its `cell` (the cell crop whose `Q.STEM` row it is); a beam and a tip carry the cells that hold their
    stems, so every cell view gets the ONE page reading. Returns `{"beams": [...], "tips": [...], "census": {...}}`."""
    claimed = claimed or {}
    t0 = time.time()
    by_ord = {v.ordinal: v for v in views}
    grid = Grid([v.box for v in views], GRID_SPACES * sp)
    head_grid = Grid([tuple(h[:4]) for h in heads], GRID_SPACES * sp) if heads else None
    cache: Dict[int, Dict[str, object]] = {}

    def role(o: int) -> Dict[str, object]:
        r = cache.get(o)
        if r is None:
            s = by_ord[o]
            if s.kind not in ("horizontal", "curve"):
                r = {"role": "other", "why": "kind:" + s.kind}
            elif o in claimed:
                # ROADMAP 2.269 step 0 (CLAUDE §3 claim order: a later reader may mark claimed ink, never take it): a stroke an earlier claim names
                # (an arc's page ids since M3; the page-wide claims' with `OMR_PAGE_CLAIM_NAMES`) is that owner's ink, not a beam. It files no row;
                # the census counts it by owner.
                r = {"role": "other", "why": "claimed:" + str(claimed[o])}
            else:
                near = {views[i].ordinal: views[i] for i in grid.query(s.box, NEIGHBOUR_SPACES * sp)}
                for j, _c in s.touches:
                    if j in by_ord:
                        near.setdefault(j, by_ord[j])
                r = BS.role_of(s, near, face_join=True, trough=True)
            cache[o] = r
        return r

    # 1. the stem strokes the Q.STEM rows land on
    stem_rows: Dict[int, List[str]] = {}
    stem_cells: Dict[int, set] = {}
    unmatched = 0
    for st in stems:
        near = [views[i] for i in grid.query(st["box"])]
        sv = BS.find_stem_stroke(near, st["box"])
        if sv is None:
            unmatched += 1
            continue
        stem_rows.setdefault(sv.ordinal, []).append(str(st.get("row") or ""))
        if st.get("cell"):
            stem_cells.setdefault(sv.ordinal, set()).add(str(st["cell"]))

    # 2. every stroke's role, the beam-role ones' stems
    horiz = [v for v in views if v.kind in ("horizontal", "curve")]
    roles = {v.ordinal: role(v.ordinal) for v in horiz}
    beam_ords = [o for o, r in roles.items() if r["role"] == "beam"]

    parent: Dict[int, int] = {}

    def find(a: int) -> int:
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for o in beam_ords:
        ss = list(roles[o]["stem_ordinals"])
        for s in ss:
            find(s)
        for s in ss[1:]:
            union(ss[0], s)

    # 3. rows: one per horizontal / curve stroke with a role
    beams: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    for v in horiz:
        r = roles[v.ordinal]
        counts[str(r["role"])] = counts.get(str(r["role"]), 0) + 1
        if r["role"] == "other":
            continue
        ss = list(r["stem_ordinals"])
        grp = find(ss[0]) if ss and r["role"] == "beam" else None
        head_fused = bool(head_grid is not None and any(_covers(v.box, heads[i]) for i in head_grid.query(v.box)))
        beams.append(dict(ordinal=v.ordinal, role=str(r["role"]), stems=ss, stems_by_face=list(r["stems_by_face"]), group=grp,
                          thickness_spaces=v.thickness, thickness_margin=r["thickness_margin"], length_spaces=v.length,
                          kind=v.kind, head_fused=head_fused, claimed_by=claimed.get(v.ordinal),
                          cells=sorted(set().union(*[stem_cells.get(x, set()) for x in ss])) if ss else [], box=list(v.box)))

    # 4. the tips: both ends of each stem stroke
    tips: List[Dict[str, Any]] = []
    for so in sorted(stem_rows):
        sv = by_ord[so]
        near = [views[i] for i in grid.query(sv.box, TIP_REACH_SPACES * sp)]
        for o in (v.ordinal for v in near):
            role(o)
        rb = {o: cache[o] for o in (v.ordinal for v in near)}
        for side, end in (("up", "top"), ("down", "bottom")):
            tr = BS.tip_reading(near, rb, sv, side, face_join=True)
            gap = BS.tip_reading(near, rb, sv, side, face_join=False)
            tips.append(dict(stem=so, stem_rows=stem_rows[so], end=end, side=side, tip_y=tr["tip_y"], beams=list(tr["beams"]), fused=list(tr["fused"]),
                             joined=list(tr["joined"]), joined_gap=list(gap["joined"]), hooks=list(tr["hooks"]), stubs=list(tr["stubs"]),
                             doubt=list(tr["doubt"]), stem_beamed=bool(tr["stem_beamed"]), tip_clean=BS.tip_clean(near, sv, side),
                             group=find(so) if so in parent else None, cells=sorted(stem_cells.get(so, ()))))

    groups: Dict[int, set] = {}
    for s_ in parent:
        groups.setdefault(find(s_), set()).add(s_)
    multi = {g: m for g, m in groups.items() if len(m) >= 2}
    skipped: Dict[str, int] = {}
    for v in horiz:
        w = str(roles[v.ordinal].get("why") or "")
        if w.startswith("claimed:"):
            skipped[w[8:]] = skipped.get(w[8:], 0) + 1
    census = dict(roles=dict(sorted(counts.items())), claimed_not_read=skipped, beam_strokes=len(beam_ords), stem_strokes=len(stem_rows), stem_rows_unmatched=unmatched,
                  groups=len(multi), seconds=round(time.time() - t0, 2))
    return dict(beams=beams, tips=tips, census=census)


# ───────────────────────────── the page, as rows ─────────────────────────────

def views_of(page_map: Any) -> List[StrokeView]:
    """The page map's strokes as `StrokeView`s (page px; ordinal = the `Q.PAGE_STROKE` ordinal)."""
    out = []
    for i, st in enumerate(page_map.strokes):
        out.append(StrokeView(ordinal=i, kind=st.kind, box=tuple(float(v) for v in st.box), length=float(st.length_sp), thickness=float(st.thickness_sp),
                              sagitta=st.sagitta_sp, angle=float(st.angle_deg), touches=tuple((int(j), float(c)) for j, c in st.touches),
                              space_px=float(st.staff_space_local or page_map.sp), profile=tuple(int(v) for v in (st.profile or ())),
                              ends=(float(st.ends[0][0]), float(st.ends[0][1]), float(st.ends[1][0]), float(st.ends[1][1]))))
    return out


def _cell_to_page(c: Any, box: Sequence[float]) -> Optional[List[float]]:
    rect, up = getattr(c, "bbox_page_px", None), getattr(c, "upscale_factor", None)
    if not rect or not up or len(rect) != 4:
        return None
    x, y, w, h = (float(v) for v in box[:4])
    return [rect[0] + x / up, rect[1] + y / up, w / up, h / up]


def gather_page_beams(log: Any, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], page_map: Any,
                      detections: Optional[Dict[str, List[Any]]] = None, *, progress: bool = False) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.260c M4a (flag `OMR_PAGE_BEAMS`, default OFF), STAGED GATHER: `Q.PAGE_BEAM` / `Q.PAGE_BEAM_TIP` (module doc). Each beam is read ONCE on the page and filed once (one row per page stroke, so a beam two cells hold is one row naming both). AFTER `gather_cv_lines` (it
    reads the `Q.STEM` rows) and after `gather_page_strokes` (it reads the map). Reads rows and the in-memory map only; no raster. Returns the read."""
    if not enabled():
        return None
    from . import record as R
    from .record import Q, READERS, ABSTAIN, Scope
    from .gather import FRAME_PAGE, _notehead_boxes_for_cell
    p = int(getattr(pws.page, "page_index", 0))
    sub = R.page(p)
    if page_map is None or not getattr(page_map, "strokes", None):
        log.abstain(sub, Q.PAGE_BEAM, reader=READERS.CV_PAGE_BEAMS, frame=FRAME_PAGE, reason=ABSTAIN.NO_MASK, note="no page stroke map")
        return None
    t0 = time.time()
    views = views_of(page_map)
    stems: List[Dict[str, Any]] = []
    heads: List[List[float]] = []
    seen_heads = set()
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        csub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        for r in log.rows(Q.STEM, csub):
            if r.reader != READERS.CV_LINES or not isinstance(r.value, (list, tuple)) or len(r.value) < 4:
                continue
            b = _cell_to_page(c, r.value)
            if b is not None:
                stems.append(dict(box=tuple(b), row=r.id, cell=csub.to_key()))
        if detections is not None:
            for hb in _notehead_boxes_for_cell(detections, csub, c, log=log) or ():
                b = _cell_to_page(c, hb)
                if b is None:
                    continue
                k = tuple(int(round(v / 2.0)) for v in b)
                if k not in seen_heads:
                    seen_heads.add(k)
                    heads.append(b)
    claimed: Dict[int, str] = {}
    from . import claim_order as _CO
    named = []
    for r in log.rows(Q.CLAIMED_AREA, sub, scope=Scope.SELF_AND_DESCENDANTS):
        d = r.detail or {}
        if d.get("page_strokes"):
            named.append((_CO.layer_of(str(d.get("owner") or "")) if _CO.layer_of(str(d.get("owner") or "")) is not None else 99, len(named), d))
    for _lay, _k, d in sorted(named, key=lambda t: (t[0], t[1])):      # claim order (CLAUDE §3): the first claim names the owner
        for o in d.get("page_strokes") or ():
            claimed.setdefault(int(o), str(d.get("owner") or "?"))
    res = read_page(views, stems, page_map.sp, heads=heads, claimed=claimed)
    for b in res["beams"]:
        sidx, lidx = page_map.staff_of[b["ordinal"]]
        log.observe(sub, Q.PAGE_BEAM, b["role"], reader=READERS.CV_PAGE_BEAMS, frame=FRAME_PAGE, ordinal=b["ordinal"], stems=b["stems"],
                    stems_by_face=b["stems_by_face"], group=b["group"], thickness_spaces=b["thickness_spaces"], thickness_margin=b["thickness_margin"],
                    length_spaces=b["length_spaces"], stroke_kind=b["kind"], head_fused=b["head_fused"], claimed_by=b["claimed_by"],
                    cells=b["cells"], bbox_page_px=[b["box"][0], b["box"][1], b["box"][0] + b["box"][2], b["box"][1] + b["box"][3]],
                    staff=[local.get(sidx, (0, 0))[0], lidx])
    for t in res["tips"]:
        sidx, lidx = page_map.staff_of[t["stem"]]
        log.observe(sub, Q.PAGE_BEAM_TIP, len(t["beams"]), reader=READERS.CV_PAGE_BEAMS, frame=FRAME_PAGE, stem=t["stem"], stem_rows=t["stem_rows"], end=t["end"],
                    tip_y=t["tip_y"], beams=t["beams"], fused=t["fused"], joined=t["joined"], joined_gap=t["joined_gap"], hooks=t["hooks"], stubs=t["stubs"],
                    doubt=t["doubt"], stem_beamed=t["stem_beamed"], tip_clean=t["tip_clean"], group=t["group"], cells=t["cells"], staff=[local.get(sidx, (0, 0))[0], lidx])
    res["census"]["seconds"] = round(time.time() - t0, 2)
    res["census"]["claimed_strokes"] = len(claimed)
    res["census"]["heads"] = len(heads)
    log.observe(sub, Q.PAGE_BEAM, "census", reader=READERS.CV_PAGE_BEAMS, frame=FRAME_PAGE, **res["census"])
    if progress:
        print("  gather page beams p%s: %s" % (p, res["census"]))
    return res
