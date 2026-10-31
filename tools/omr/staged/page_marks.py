"""ROADMAP 2.240 step 1 -- PAGE-MARK IDS: one id per mark on the PAGE, however many padded cells boxed it (STAGED GATHER; decides nothing).

    python3 -m tools.omr.staged.page_marks readout REC [--pages 0,4] [--out DIR] [--tiles DIR]   # twin ink before/after, merged pairs
    python3 -m tools.omr.staged.page_marks controls REC --page N                                 # the controls that can fail

WHY (benchmarks/page-ledger-2026-10/FINDINGS.md). The detector reads padded per-staff cells and was trained on them, so that VIEW stays.
But the cell also became the unit of OWNERSHIP: 17-19% of stroke ink is seen by two cells, all of it between neighbouring staves of one
system, and one head in the gap is boxed once per staff (1,653 Litolff / 3,541 Brahms same-class pairs from two staves' crops). Sean's
crops (2026-10-30): a head boxed from two staves is ONE note. CLAUDE §4: two readings of one raster count once.

WHAT IT FILES (flag `OMR_PAGE_MARKS`, default OFF). One `Q.PAGE_MARK` row per detector box of every pass (the box's glyph subject):
`value` = the page-mark ordinal (per page; boxes with the same ordinal are ONE mark); `detail` = `family`, `members` (glyph keys of the
mark), `cells` ([system, staff, cell] of each member), `ink_px` (this box's ink), `why` (`shared_ink` merged | `alone` no candidate |
`refused` every candidate refused | `no_ink` | `not_a_mark`), `pairs` (each same-family box of ANOTHER cell whose page box overlaps this one:
[glyph key, shared share, rect IoU, merged?, reason]). NOTHING READS IT: no verdict, no exported byte changes (byte identity with it ON is
the proof). A box whose cell has no stroke map, or no page box, ABSTAINS (rule 8: no mark id is invented for ink we cannot see).

HOW TWO BOXES ARE ONE MARK. A box's INK is the page pixels that are dark on the page render (`pws.page.binary`), lie on a stroke of the
box's own cell (the cell's `stroke_map` labels sampled onto its page rectangle exactly as `claim_readout.PageInk.add_cell` does: one
reduced pixel of fill, centre-aligned nearest), and lie inside the box's page rectangle. Two boxes of ONE family (`stroke_owner.family_of`)
from TWO cells are one page mark when the ink they share is at least `SHARE_MIN` of the smaller one's ink -- the same ink, not a near box:
  * not IoU: a box over blank paper shares nothing; a stacked third shares only the band where the boxes overlap;
  * the share is measured INSIDE each box, so a fused chord blob (Sean 2026-10-30: heads + stems + beams are one stroke) does not make two
    heads of it one mark;
  * greedy by share, biggest first, and no mark may hold two boxes of ONE cell unless those two share the ink themselves (a same-cell
    twin that both match one box of the other cell); two boxes one cell saw APART stay apart. So a stacked third seen by two cells stays
    two marks. Same-cell twins with no second cell are `one_ink`'s question (2.186), never this step's.
A unison on two staves is two heads at two page places: no shared ink, two marks.

CONVENTION ASSUMED: `SHARE_MIN` = 0.5 is the register's one cut (`stroke_map.COVER_SHARE_MIN`, "a mark's own piece is wholly inside, ~1.0;
a neighbour shares a sliver"), not tuned here. WHAT WOULD FALSIFY IT: a merge Sean calls two marks, or a refusal he calls one (the tiles).
NOT CONFIRMED beyond the two plates. Horizontal (same staff, two bars) cells do not overlap, so a slur cut at a barline is NOT joined here
(steps 4/6).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

DERIVED_CHECK = False
ENV = "OMR_PAGE_MARKS"
#: the share of the smaller box's ink the two boxes must share (module doc: the register's one cut, not tuned)
SHARE_MIN = 0.5
#: a refused pair this close under the cut is a NEAR MISS, recorded as a margin only (step 2: never tuned on two plates)
NEAR_MISS = 0.05


def enabled() -> bool:
    return os.environ.get(ENV, "0").strip().lower() in ("1", "true", "yes", "on")


#: ROADMAP 2.240 step 2 (default OFF, allow-list): one owner per page mark, arcs/hairpins page-wide (`page_owner.py`), and the step-1 rule
#: fix from Sean's tiles (`link(pieces=...)`). Needs `OMR_PAGE_MARKS`.
OWNER_ENV = "OMR_PAGE_OWNER"


#: The families one cell may box in two PIECES (step 2 (a)): long or lettered marks -- Sean's tiles 2 (a p) and 7 (a beam). A head, rest,
#: accidental or dot is one compact glyph: two boxes of it in one cell are two marks (a box holding two heads is a chord, not one head).
PIECE_FAMILIES = frozenset(("dynamic", "beam", "arc", "hairpin", "flag", "text"))


def owner_enabled() -> bool:
    return enabled() and os.environ.get(OWNER_ENV, "0").strip().lower() in ("1", "true", "yes", "on")


# ───────────────────────────── 1. the core (pure) ─────────────────────────────

@dataclass
class BoxInk:
    key: str                                  # the box's glyph subject key
    cell: Tuple[int, int, int, int]           # (page, system, staff, cell)
    gi: int                                   # glyph ordinal in its cell
    family: Optional[str]
    cls: str
    page_box: Tuple[float, float, float, float]
    pix: np.ndarray = field(repr=False)       # flat page indices of the box's ink, sorted unique


def _centre_index(n_dst: int, n_src: int) -> np.ndarray:
    return np.minimum(((np.arange(n_dst) + 0.5) * n_src / float(n_dst)).astype(np.int64), n_src - 1)


def label_image(res: Any, img_shape: Tuple[int, int]) -> np.ndarray:
    """A cell's stroke labels in the REDUCED frame (0 none, i = stroke ordinal + 1) -- `claim_readout.build_page`'s construction."""
    s = res.scale
    hr, wr = int(round(img_shape[0] * s)), int(round(img_shape[1] * s))
    lab = np.zeros((max(1, hr), max(1, wr)), np.int16)
    for i, (m, x0, y0) in enumerate(res.masks):
        mh, mw = m.shape
        y1, x1 = min(hr, y0 + mh), min(wr, x0 + mw)
        if y1 > y0 and x1 > x0:
            sub = lab[y0:y1, x0:x1]
            sub[m[:y1 - y0, :x1 - x0]] = i + 1
    return lab


def seen_on_page(rect: Sequence[float], labels: np.ndarray) -> Tuple[Tuple[int, int, int, int], np.ndarray]:
    """(int page rect, bool image of 'a stroke of this cell stands here') -- the labels filled one reduced pixel and sampled centre-aligned
    nearest onto the cell's page rectangle (`claim_readout.fill_labels` + `sample_to_rect`)."""
    from .claim_readout import fill_labels
    x0, y0, x1, y1 = (int(v) for v in rect)
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    lab = fill_labels(labels) if labels.size > 1 else labels
    seen = lab[np.ix_(_centre_index(h, lab.shape[0]), _centre_index(w, lab.shape[1]))] > 0
    return (x0, y0, x0 + w, y0 + h), seen


def box_pixels(cell_rect: Tuple[int, int, int, int], seen: np.ndarray, page_box: Sequence[float], ink: np.ndarray) -> np.ndarray:
    """Flat page indices of the box's INK: dark on the page, on a stroke of its cell, inside the box (module doc)."""
    H, W = ink.shape
    cx0, cy0, cx1, cy1 = cell_rect
    bx0, by0 = int(round(page_box[0])), int(round(page_box[1]))
    bx1, by1 = int(round(page_box[2])), int(round(page_box[3]))
    x0, y0 = max(bx0, cx0, 0), max(by0, cy0, 0)
    x1, y1 = min(bx1, cx1, W), min(by1, cy1, H)
    if x1 <= x0 or y1 <= y0:
        return np.zeros(0, np.int64)
    sel = seen[y0 - cy0:y1 - cy0, x0 - cx0:x1 - cx0] & ink[y0:y1, x0:x1]
    ys, xs = np.nonzero(sel)
    return np.sort((ys + y0).astype(np.int64) * W + (xs + x0))


def rect_iou(a: Sequence[float], b: Sequence[float]) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def _overlap(a: Sequence[float], b: Sequence[float]) -> bool:
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


@dataclass
class Marks:
    mark_of: Dict[str, int]                                   # box key -> page-mark ordinal
    members: Dict[int, List[str]]                             # ordinal -> box keys (sorted by cell, gi)
    pairs: Dict[str, List[list]]                              # box key -> [[other key, share, iou, merged, reason]]
    why: Dict[str, str]                                       # box key -> shared_ink | alone | refused | no_ink | not_a_mark
    merged_pairs: List[Tuple[str, str, float]] = field(default_factory=list)


def link(boxes: Sequence[BoxInk], share_min: float = SHARE_MIN, guard: bool = True, pieces: Optional[bool] = None) -> Marks:
    """The page marks of one page's boxes (module doc). `guard=False` is the CONTROL's broken arm: every overlapping pair over the share
    merges, and a mark may then hold two boxes of one cell that share no ink. `pieces` (default: `OMR_PAGE_OWNER`) admits two ink-disjoint
    boxes of one cell that both lie inside one box of the other cell (step 2 (a), Sean's step-1 tiles 2 and 7)."""
    if pieces is None:
        pieces = owner_enabled()
    by_fam: Dict[str, List[int]] = collections.defaultdict(list)
    for i, b in enumerate(boxes):
        if b.family is not None:
            by_fam[b.family].append(i)

    def shared(x: int, y: int) -> float:
        n = min(boxes[x].pix.size, boxes[y].pix.size)
        if not n:
            return 0.0
        return round(int(np.intersect1d(boxes[x].pix, boxes[y].pix, assume_unique=True).size) / float(n), 3)

    cands: List[Tuple[float, int, int, float]] = []          # (share, i, j, iou), i < j, different cells
    pairs: Dict[str, List[list]] = collections.defaultdict(list)
    for fam, idx in by_fam.items():
        idx = sorted(idx, key=lambda i: boxes[i].page_box[0])
        for a_pos, i in enumerate(idx):
            bi = boxes[i]
            for j in idx[a_pos + 1:]:
                bj = boxes[j]
                if bj.page_box[0] >= bi.page_box[2]:
                    break
                if bj.cell == bi.cell or not _overlap(bi.page_box, bj.page_box):
                    continue
                cands.append((shared(i, j), min(i, j), max(i, j), round(rect_iou(bi.page_box, bj.page_box), 3)))
    # greedy by share, biggest first; ties broken by box order (deterministic)
    cands.sort(key=lambda t: (-t[0], t[1], t[2]))
    parent = list(range(len(boxes)))
    comp: Dict[int, List[int]] = {i: [i] for i in range(len(boxes))}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def inside(x: int, z: int) -> bool:
        """Box x's ink lies (by `share_min` of it) inside box z's ink."""
        n = boxes[x].pix.size
        return bool(n) and np.intersect1d(boxes[x].pix, boxes[z].pix, assume_unique=True).size >= share_min * n

    def pieces_of_one(x: int, y: int, members: Sequence[int]) -> bool:
        """ROADMAP 2.240 step 2 (a), Sean's step-1 tiles 2 (one p) and 7 (one beam): ONE cell boxed one mark in two PIECES -- the two boxes
        share no ink at all -- and both pieces lie inside ONE box of the other cell. A stacked third is not this: its two boxes overlap."""
        if boxes[x].family not in PIECE_FAMILIES or shared(x, y) > 0.0:
            return False
        return any(boxes[z].cell != boxes[x].cell and inside(x, z) and inside(y, z) for z in members)

    def cell_twice(ri: int, rj: int) -> bool:
        """Joining would put two boxes of ONE cell in one mark that do not themselves share the ink: two marks that cell saw apart --
        unless they are two pieces of one mark the other cell boxed whole (`pieces_of_one`, flag `OMR_PAGE_OWNER`)."""
        allm = comp[ri] + comp[rj]
        for x in comp[ri]:
            for y in comp[rj]:
                if boxes[x].cell == boxes[y].cell and shared(x, y) < share_min:
                    if pieces and pieces_of_one(x, y, allm):
                        via_pieces[0] = True
                        continue
                    return True
        return False

    merged_pairs: List[Tuple[str, str, float]] = []
    via_pieces = [False]
    for share, i, j, iou in cands:
        bi, bj = boxes[i], boxes[j]
        ri, rj = find(i), find(j)
        via_pieces[0] = False
        reason = None
        if not guard:
            reason = None if share >= share_min else "share_below"
        elif not (bi.pix.size and bj.pix.size):
            reason = "no_ink"
        elif share == 0.0:
            reason = "no_shared_ink"
        elif share < share_min:
            reason = "share_below"
        elif ri != rj and cell_twice(ri, rj):
            reason = "cell_twice_in_mark"
        merged = reason is None
        if merged:
            if ri != rj:
                parent[rj] = ri
                comp[ri] += comp.pop(rj)
            merged_pairs.append((bi.key, bj.key, share))
        ok = "pieces_in_one_box" if via_pieces[0] else "shared_ink"
        pairs[bi.key].append([bj.key, share, iou, merged, reason or ok])
        pairs[bj.key].append([bi.key, share, iou, merged, reason or ok])
    comps: Dict[int, List[int]] = collections.defaultdict(list)
    for i in range(len(boxes)):
        comps[find(i)].append(i)
    order = sorted(comps.values(), key=lambda m: min((boxes[i].cell, boxes[i].gi) for i in m))
    mark_of: Dict[str, int] = {}
    members: Dict[int, List[str]] = {}
    why: Dict[str, str] = {}
    for n, m in enumerate(order):
        m = sorted(m, key=lambda i: (boxes[i].cell, boxes[i].gi))
        members[n] = [boxes[i].key for i in m]
        for i in m:
            b = boxes[i]
            mark_of[b.key] = n
            ps = pairs.get(b.key, [])
            if b.family is None:
                why[b.key] = "not_a_mark"
            elif len(m) > 1:
                why[b.key] = "shared_ink"
            elif not b.pix.size:
                why[b.key] = "no_ink"
            elif ps:
                why[b.key] = "refused"
            else:
                why[b.key] = "alone"
    return Marks(mark_of, members, dict(pairs), why, merged_pairs)


# ───────────────────────────── 2. the GATHER step ─────────────────────────────

def gather_page_marks(log: Any, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]],
                      stroke_cells: Dict[Tuple[int, int, int, int], Any], *, progress: bool = False) -> Optional[Marks]:
    """ROADMAP 2.240 step 1 (flag `OMR_PAGE_MARKS`, default OFF), STAGED GATHER: `Q.PAGE_MARK` per detector box (module doc). Reads the
    page render, the cells' stroke maps and the final box set; files rows only and decides nothing. Returns the page's `Marks` (probes)."""
    if not enabled() or not stroke_cells:
        return None
    from . import record as R
    from .record import ABSTAIN, Q, READERS
    from .gather import FRAME_PAGE, _page_box
    from .stroke_owner import family_of
    binary = getattr(getattr(pws, "page", None), "binary", None)
    if binary is None:
        return None
    ink = binary == 0
    boxes: List[BoxInk] = []
    page = None
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        ck = (c.page_index, key[0], key[1], c.measure_index)
        page = c.page_index
        dets = detections.get(R.cell(*ck).to_key(), ())
        if not dets:
            continue
        res = stroke_cells.get(ck)
        img = getattr(c, "image_no_staff", None)
        rect = getattr(c, "bbox_page_px", None)
        view = None
        if res is not None and not isinstance(res, str) and img is not None and rect:
            view = seen_on_page(rect, label_image(res, img.shape))
        for gi, d in enumerate(dets):
            g = R.glyph(*ck, gi)
            pb = _page_box(c, d)
            if view is None or pb is None:
                log.abstain(g, Q.PAGE_MARK, reader=READERS.CV_PAGE_MARKS, frame=FRAME_PAGE,
                            reason=(res if isinstance(res, str) else ABSTAIN.NO_STAFF_GEOMETRY))
                continue
            boxes.append(BoxInk(g.to_key(), ck, gi, family_of(d.smufl_name, getattr(d, "category", None)), d.smufl_name,
                                tuple(float(v) for v in pb), box_pixels(view[0], view[1], pb, ink)))
    if not boxes:
        return None
    marks = link(boxes)
    for b in boxes:
        n = marks.mark_of[b.key]
        mem = marks.members[n]
        cells_of = sorted({tuple(int(t) for t in m.split("/")[2:5]) for m in mem})
        extra: Dict[str, Any] = {}
        if marks.pairs.get(b.key):
            extra["pairs"] = marks.pairs[b.key]
        log.observe(R.glyph(*b.cell, b.gi), Q.PAGE_MARK, n,
                    reader=READERS.CV_PAGE_MARKS, frame=FRAME_PAGE, family=b.family, members=mem,
                    cells=[list(t) for t in cells_of], ink_px=int(b.pix.size), why=marks.why[b.key], share_min=SHARE_MIN, **extra)
    if progress:
        print("  gather page marks p%s: %d boxes -> %d marks, %d merged pairs" % (page, len(boxes), len(marks.members), len(marks.merged_pairs)))
    return marks


# ───────────────────────────── 3. the readout (from a record / slice) ─────────────────────────────

def boxes_from_rows(rows: Dict[str, List[dict]], page: int, cells: Sequence[Any], local: Dict[int, Tuple[int, int]],
                    views: Dict[Tuple[int, int, int, int], Tuple[Tuple[int, int, int, int], np.ndarray]], ink: np.ndarray) -> List[BoxInk]:
    """The page's detector boxes from its `Q.GLYPH_BOX` rows (page box = `bbox_page_px`, the gather's `_page_box`), on the re-cut cells' views."""
    from .claim_readout import cell_key
    from .stroke_owner import family_of
    out = []
    for o in rows["observations"]:
        if o.get("quantity") != "glyph_box":
            continue
        ck = cell_key(o["subject"])
        if ck is None or ck[0] != page:
            continue
        d = o.get("detail") or {}
        pb = d.get("bbox_page_px")
        v = views.get(ck)
        if not pb or v is None:
            continue
        gi = int(o["subject"].split("/")[5])
        out.append(BoxInk(o["subject"], ck, gi, family_of(str(o["value"][0]), d.get("category")), str(o["value"][0]),
                          tuple(float(t) for t in pb), box_pixels(v[0], v[1], pb, ink)))
    return out


def page_views(rows: Dict[str, List[dict]], pdf: pathlib.Path, page: int, cm_root: pathlib.Path):
    """Re-cut master cells, stroke map re-run and matched box-for-box to the record's `Q.STROKE` rows (`claim_readout.build_page`'s check)."""
    from . import cell_map as CM
    from . import gather as G
    from . import stroke_map as SM
    from .claim_readout import STROKE_BASE, cell_key
    rec_boxes: Dict[Tuple, Dict[int, list]] = collections.defaultdict(dict)
    for o in rows["observations"]:
        if o.get("quantity") == "stroke" and cell_key(o["subject"]) and cell_key(o["subject"])[0] == page:
            g = int(o["subject"].split("/")[5])
            if g >= STROKE_BASE:
                rec_boxes[cell_key(o["subject"])][g - STROKE_BASE] = (o.get("detail") or {}).get("stroke_box")
    (pws, cells), = CM.load_prepared(pdf, [page], root=cm_root)
    local = G._system_local(pws.staves)
    views = {}
    verify = collections.Counter()
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        ck = (c.page_index, key[0], key[1], c.measure_index)
        grid = G._cell_grid(c)
        img = getattr(c, "image_no_staff", None)
        if grid is None or img is None:
            verify["cell_no_grid"] += 1
            continue
        res = SM.map_strokes(img, grid[1] * 2.0, list(getattr(c, "staff_line_ys_canonical", None) or []), getattr(c, "binary", None))
        mine = {i: list(s.box) for i, s in enumerate(res.strokes)} if res else {}
        if mine != {i: list(b) for i, b in rec_boxes.get(ck, {}).items()}:
            verify["cells_mismatch"] += 1
            continue
        verify["cells_ok"] += 1
        if not mine:
            continue
        views[ck] = seen_on_page(c.bbox_page_px, label_image(res, img.shape))
    return pws, cells, local, views, verify


def twin_ink(boxes: Sequence[BoxInk], mark_of: Dict[str, int]) -> Dict[str, Dict[str, int]]:
    """Per family: `before` = ink px on which boxes of that family from two or more CELLS stand; `after` = of those, the px whose boxes are
    two or more distinct page marks. Exact (per-pixel min / max of cell and mark over the covering boxes)."""
    by_fam: Dict[str, List[BoxInk]] = collections.defaultdict(list)
    for b in boxes:
        if b.family is not None and b.pix.size:
            by_fam[b.family].append(b)
    cell_id: Dict[Tuple, int] = {}
    out: Dict[str, Dict[str, int]] = {}
    for fam, bs in sorted(by_fam.items()):
        px = np.concatenate([b.pix for b in bs])
        ce = np.concatenate([np.full(b.pix.size, cell_id.setdefault(b.cell, len(cell_id)), np.int64) for b in bs])
        mk = np.concatenate([np.full(b.pix.size, mark_of[b.key], np.int64) for b in bs])
        o = np.argsort(px, kind="stable")
        px, ce, mk = px[o], ce[o], mk[o]
        starts = np.flatnonzero(np.r_[True, px[1:] != px[:-1]])
        cmin, cmax = np.minimum.reduceat(ce, starts), np.maximum.reduceat(ce, starts)
        mmin, mmax = np.minimum.reduceat(mk, starts), np.maximum.reduceat(mk, starts)
        before = cmin != cmax
        out[fam] = {"ink_px": int(starts.size), "before": int(before.sum()), "after": int((before & (mmin != mmax)).sum())}
    return out


def page_report(boxes: Sequence[BoxInk], marks: Marks) -> Dict[str, Any]:
    """The page's counts: boxes, marks, merged pairs (by family), refused candidate pairs by reason, the 2.240 IoU control, twin ink."""
    fam = {b.key: b.family for b in boxes}
    cls = {b.key: b.cls for b in boxes}
    box_of = {b.key: b for b in boxes}
    merged_by_fam = collections.Counter(fam[a] for a, _b, _s in marks.merged_pairs)
    refused = collections.Counter()
    iou_pairs = 0
    iou_merged = 0
    merged_low_iou = 0
    near_miss = collections.Counter()
    via_pieces = 0
    seen = set()
    for k, ps in marks.pairs.items():
        for other, share, iou, merged, reason in ps:
            pk = tuple(sorted((k, other)))
            if pk in seen:
                continue
            seen.add(pk)
            if not merged:
                refused[reason] += 1
                if reason == "share_below" and share >= SHARE_MIN - NEAR_MISS:
                    near_miss[box_of[k].family] += 1
            elif reason == "pieces_in_one_box":
                via_pieces += 1
            two_staves = box_of[k].cell[1:3] != box_of[other].cell[1:3]
            if cls[k] == cls[other] and two_staves and iou >= 0.5:
                iou_pairs += 1
                iou_merged += int(merged)
            if merged and iou < 0.5:
                merged_low_iou += 1
    return {"boxes": len(boxes), "marks": len(marks.members), "merged_pairs": len(marks.merged_pairs),
            "merged_by_family": dict(merged_by_fam), "candidate_pairs": len(seen), "refused_by_reason": dict(refused),
            "iou05_same_class_two_staves": iou_pairs, "iou05_of_them_merged": iou_merged, "merged_with_iou_below_0.5": merged_low_iou,
            "twin_ink": twin_ink(boxes, marks.mark_of),
            "merged_as_pieces_in_one_box": via_pieces, "near_miss_share_below_by_family": dict(near_miss)}


def record_marks(rows: Dict[str, List[dict]], page: int) -> Dict[str, int]:
    """The record's own `Q.PAGE_MARK` rows of `page` (empty when the gather ran with the flag OFF)."""
    from .claim_readout import cell_key
    return {o["subject"]: int(o["value"]) for o in rows["observations"]
            if o.get("quantity") == "page_mark" and (cell_key(o["subject"]) or (None,))[0] == page}


def same_partition(a: Dict[str, int], b: Dict[str, int]) -> bool:
    """Two mark assignments group the same boxes together (ordinals may differ only by relabelling)."""
    if set(a) != set(b):
        return False
    ga, gb = collections.defaultdict(set), collections.defaultdict(set)
    for k, v in a.items():
        ga[v].add(k)
    for k, v in b.items():
        gb[v].add(k)
    return sorted(map(sorted, ga.values())) == sorted(map(sorted, gb.values()))


def _sum(dicts: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for d in dicts:
        for k, v in d.items():
            if isinstance(v, dict):
                out[k] = _sum([out.get(k, {}), v])
            else:
                out[k] = out.get(k, 0) + v
    return out


def run(rec: str, pages: Optional[Sequence[int]] = None, out: Optional[pathlib.Path] = None, tiles: Optional[pathlib.Path] = None,
        cm_root: Optional[pathlib.Path] = None, log=print, tile_pool: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """The readout of one REC. `tiles` cuts its 12 tiles; `tile_pool` (a list) instead COLLECTS the candidates, for one sheet over plates."""
    from . import cell_map as CM
    from . import claim_readout as CR
    src = CR.resolve_source(rec)
    pages = list(pages) if pages else CR.slice_pages(src)
    rows_all = CR.read_rows(src, pages)
    pdf = CR.LIB / CR.edition_info(rows_all)["edition_path"]
    cm_root = cm_root or CM.ROOT_DEFAULT
    man = CM.info(pdf, root=cm_root)
    per: Dict[str, Any] = {}
    pool: List[Dict[str, Any]] = []
    for pg in pages:
        t0 = time.time()
        prows = {k: [r for r in v if CR.page_of_subject(r.get("subject", "")) in (None, pg)] for k, v in rows_all.items()}
        pws, cells, local, views, verify = page_views(prows, pdf, pg, cm_root)
        ink = pws.page.binary == 0
        boxes = boxes_from_rows(prows, pg, cells, local, views, ink)
        marks = link(boxes)
        rep = page_report(boxes, marks)
        rep["verify"] = dict(verify)
        saved = record_marks(prows, pg)
        if saved:
            mine = {k: v for k, v in marks.mark_of.items()}
            rep["record_rows"] = len(saved)
            rep["record_partition_equal"] = same_partition({k: v for k, v in mine.items() if k in saved}, saved) and set(saved) <= set(mine)
        per[str(pg)] = rep
        if tiles is not None or tile_pool is not None:
            pool += [dict(t, pdf=str(pdf), cm_root=str(cm_root), cell_map=man["version"]) for t in tile_candidates(boxes, marks, pg, cells)]
        log("  page %d: %d boxes -> %d marks, %d merged, twin ink %s (%.0fs)" % (
            pg, rep["boxes"], rep["marks"], rep["merged_pairs"],
            {f: "%d->%d" % (t["before"], t["after"]) for f, t in rep["twin_ink"].items() if t["before"]}, time.time() - t0))
        del pws, cells, views, ink
    total = _sum([{k: v for k, v in r.items() if k not in ("record_partition_equal",)} for r in per.values()])
    report = {"record": str(src), "pages": pages, "master": man["version"], "share_min": SHARE_MIN, "total": total, "per_page": per}
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "page_marks.json").write_text(json.dumps(report, indent=1, sort_keys=True, default=str))
    tw = total.get("twin_ink", {})
    b = sum(t["before"] for t in tw.values())
    a = sum(t["after"] for t in tw.values())
    log("page_marks readout %s pages %s master %s" % (os.path.basename(str(src)), pages, man["version"]))
    log("  boxes %d -> marks %d; merged pairs %d %s" % (total["boxes"], total["marks"], total["merged_pairs"], total.get("merged_by_family", {})))
    log("  2.240 control: same-class two-staff pairs at IoU>=0.5 %d, of them merged %d; merges at IoU<0.5 %d" % (
        total["iou05_same_class_two_staves"], total["iou05_of_them_merged"], total["merged_with_iou_below_0.5"]))
    log("  refused candidate pairs by reason %s; near misses (share within %.2f under the cut) %s; merged as two pieces in one box %d" % (
        total.get("refused_by_reason", {}), NEAR_MISS, total.get("near_miss_share_below_by_family", {}), total.get("merged_as_pieces_in_one_box", 0)))
    log("  twin ink (one family, two cells): %d px before -> %d px after" % (b, a))
    if tile_pool is not None:
        tile_pool += pool
    elif tiles is not None:
        cut_mark_tiles(pool, tiles)
    return report


# ───────────────────────────── 4. tiles: "is this one mark?" ─────────────────────────────

def tile_candidates(boxes: Sequence[BoxInk], marks: Marks, page: int, cells: Sequence[Any]) -> List[Dict[str, Any]]:
    """Every merged pair and every refused pair with shared ink (the borderline), with the staff band nearest the pair (one staff a tile)."""
    from .claim_readout import staff_bands
    bands = staff_bands(cells)
    box_of = {b.key: b for b in boxes}
    out, seen = [], set()
    for k, ps in marks.pairs.items():
        for other, share, iou, merged, reason in ps:
            pk = tuple(sorted((k, other)))
            if pk in seen or (not merged and share <= 0.0):
                continue
            seen.add(pk)
            a, b = box_of[pk[0]], box_of[pk[1]]
            bb = [min(a.page_box[0], b.page_box[0]), min(a.page_box[1], b.page_box[1]),
                  max(a.page_box[2], b.page_box[2]), max(a.page_box[3], b.page_box[3])]
            cy = (bb[1] + bb[3]) / 2.0
            band = min(bands, key=lambda t: abs((t[0] + t[1]) / 2.0 - cy)) if bands else (cy - 40, cy + 40)
            in_gap = not (band[0] <= cy <= band[1])
            out.append({"page": page, "box": bb, "members": [a.key, b.key], "family": a.family, "classes": [a.cls, b.cls],
                        "share": share, "iou": iou, "merged": bool(merged), "reason": reason, "in_gap": in_gap,
                        "staff_y": band, "unit": (band[1] - band[0]) / 4.0})
    return out


def pick_tiles(pool: List[Dict[str, Any]], n: int = 12, seed: int = 2240) -> List[Dict[str, Any]]:
    """6 merges + 6 refusals (3 `cell_twice_in_mark`, 3 `share_below`, the nearest misses first), mostly in the gap between staves, families
    spread, plates alternated, seeded."""
    import random
    rnd = random.Random(seed)
    out: List[Dict[str, Any]] = []
    n_ref = n - n // 2
    for want_merged, reason, k in ((True, None, n // 2), (False, "cell_twice_in_mark", n_ref // 2), (False, "share_below", n_ref - n_ref // 2)):
        grp = [t for t in pool if t["merged"] == want_merged and (reason is None or t["reason"] == reason)]
        gap = [t for t in grp if t["in_gap"]]
        rest = [t for t in grp if not t["in_gap"]]
        rnd.shuffle(gap)
        rnd.shuffle(rest)
        if not want_merged:          # the refusals Sean can learn most from: the nearest misses first, in the gap
            gap.sort(key=lambda t: -t["share"])
        chosen: List[Dict[str, Any]] = []
        fams = collections.Counter()
        plates = collections.Counter()
        for t in gap + rest:
            if len(chosen) >= k:
                break
            if fams[t["family"]] >= max(1, k // 2) and len({x["family"] for x in grp}) > 1:
                continue
            if plates[t.get("pdf")] >= (k + 1) // 2 and len({x.get("pdf") for x in grp}) > 1:
                continue
            if any(c["page"] == t["page"] and abs(c["box"][0] - t["box"][0]) < 60 and abs(c["box"][1] - t["box"][1]) < 60 for c in out + chosen):
                continue
            chosen.append(t)
            fams[t["family"]] += 1
            plates[t.get("pdf")] += 1
        out += chosen
    rnd.shuffle(out)
    return out


def cut_mark_tiles(pool: List[Dict[str, Any]], out_dir: pathlib.Path, n: int = 12) -> None:
    """One tile each: the nearest staff and the pair, ONE thin orange box around both boxes, nothing else drawn; key.json BESIDE the
    tile folder (`out_dir/tiles/`, `out_dir/key.json`)."""
    from PIL import Image, ImageDraw
    from . import cell_map as CM
    chosen = pick_tiles(pool, n)
    tdir = out_dir / "tiles"
    tdir.mkdir(parents=True, exist_ok=True)
    for f in tdir.glob("*"):
        f.unlink()
    imgs: Dict[Tuple[str, int], Any] = {}
    key = []
    for i, it in enumerate(chosen, 1):
        ik = (it["pdf"], it["page"])
        if ik not in imgs:
            (pws, _cells), = CM.load_prepared(pathlib.Path(it["pdf"]), [it["page"]], root=pathlib.Path(it["cm_root"]))
            imgs[ik] = Image.fromarray(pws.page.rgb).convert("RGB")
        im = imgs[ik]
        u = it["unit"] or 20.0
        bb = [it["box"][0] - 3, it["box"][1] - 3, it["box"][2] + 3, it["box"][3] + 3]
        top, bot = it["staff_y"]
        cx = (bb[0] + bb[2]) / 2.0
        # the box is never wider than the tile: the crop always holds the whole box and 1.5 spaces round it
        x0, x1 = max(0, int(min(cx - 6 * u, bb[0] - 1.5 * u))), int(max(cx + 6 * u, bb[2] + 1.5 * u))
        y0, y1 = max(0, int(min(top - 1.5 * u, bb[1] - 1.5 * u))), int(max(bot + 1.5 * u, bb[3] + 1.5 * u))
        crop = im.crop((x0, y0, x1, y1)).copy()
        ImageDraw.Draw(crop).rectangle([round(bb[0] - x0), round(bb[1] - y0), round(bb[2] - x0), round(bb[3] - y0)],
                                       outline=(255, 140, 0), width=max(2, int(u / 10)))
        W = 520
        crop = crop.resize((W, max(1, int(W * crop.height / crop.width))))
        crop.save(tdir / ("tile_%02d.png" % i))
        key.append({**{k: v for k, v in it.items() if k not in ("staff_y", "cm_root")}, "tile": i, "crop_origin": [x0, y0]})
    (tdir / "README.md").write_text(
        "# Is this one mark?\n\nEach picture is a piece of a score page with ONE orange box on it and nothing else drawn. The box only says "
        "where to look.\n\n**Question, for every tile:** is the ink in the box ONE mark (one note, one rest, one accidental ...) or TWO "
        "marks? If you can, say what it is.\n\nAnswer by tile number.\n")
    (out_dir / "key.json").write_text(json.dumps(key, indent=1, default=str))


# ───────────────────────────── 5. controls that can fail ─────────────────────────────

def controls(rec: str, page: int, cm_root: Optional[pathlib.Path] = None, log=print) -> int:
    """(a) one real head seen from two cells, planted: a real head box in a cell's overlap is copied into the neighbour cell's view -> MUST
    merge; (b) a real stacked third (two head boxes of one cell, one space apart) copied into the neighbour cell -> must stay TWO marks, and
    the broken arm (`guard=False`, share 0) MUST fuse them (the control can fail); (c) the readout of an identical copy of the rows
    equals the first."""
    from . import cell_map as CM
    from . import claim_readout as CR
    src = CR.resolve_source(rec)
    rows = CR.read_rows(src, [page])
    pdf = CR.LIB / CR.edition_info(rows)["edition_path"]
    cm_root = cm_root or CM.ROOT_DEFAULT
    pws, cells, local, views, verify = page_views(rows, pdf, page, cm_root)
    ink = pws.page.binary == 0
    boxes = boxes_from_rows(rows, page, cells, local, views, ink)
    fails = 0
    # the neighbour view of a box: a cell of another staff of the same system whose page rect holds the whole box
    def neighbour(b: BoxInk):
        for ck, (rect, seen) in views.items():
            if ck[:2] == b.cell[:2] and ck[2] != b.cell[2] and rect[0] <= b.page_box[0] and rect[2] >= b.page_box[2] \
                    and rect[1] <= b.page_box[1] and rect[3] >= b.page_box[3]:
                return ck, rect, seen
        return None

    def planted(b: BoxInk, nb, gi: int) -> BoxInk:
        ck, rect, seen = nb
        return BoxInk("glyph/%d/%d/%d/%d/%d" % (*ck, gi), ck, gi, b.family, b.cls, b.page_box, box_pixels(rect, seen, b.page_box, ink))

    keys = {b.key for b in boxes}
    heads = [b for b in boxes if b.family == "head" and b.pix.size >= 20]
    # (a)
    one = None
    for b in heads:
        nb = neighbour(b)
        if nb is not None:
            p = planted(b, nb, 900_001)
            if p.pix.size >= 20:
                one = (b, p)
                break
    if one is None:
        log("  (a) no head in a cell overlap on page %d: control NOT RUN" % page)
        fails += 1
    else:
        m = link([x for x in boxes] + [one[1]])
        ok = m.mark_of[one[0].key] == m.mark_of[one[1].key] and len(m.members[m.mark_of[one[0].key]]) >= 2
        log("  (a) planted one head seen from two cells (%s): %s" % (one[0].key, "MERGED -- pass" if ok else "NOT merged -- FAIL"))
        fails += 0 if ok else 1
    # (b)
    third = None
    by_cell = collections.defaultdict(list)
    for b in heads:
        by_cell[b.cell].append(b)
    for ck, hs in sorted(by_cell.items()):
        for i in range(len(hs)):
            for j in range(len(hs)):
                a, c = hs[i], hs[j]
                if i == j:
                    continue
                ha, hc = a.page_box[3] - a.page_box[1], c.page_box[3] - c.page_box[1]
                dy = (c.page_box[1] + c.page_box[3] - a.page_box[1] - a.page_box[3]) / 2.0
                dx = abs((c.page_box[0] + c.page_box[2] - a.page_box[0] - a.page_box[2]) / 2.0)
                # two whole heads of one size (a box clipped at the cell edge is a fragment of ONE head, not a third)
                if min(ha, hc) < 0.8 * max(ha, hc):
                    continue
                if 0.7 * ha <= dy <= 1.3 * ha and dx < 0.5 * ha and _overlap(a.page_box, c.page_box):
                    na, nc = neighbour(a), neighbour(c)
                    if na is not None and nc is not None and na[0] == nc[0]:
                        third = (a, c, planted(a, na, 900_002), planted(c, nc, 900_003))
                        break
            if third:
                break
        if third:
            break
    if third is None:
        log("  (b) no real stacked third (two whole heads of one cell, one space apart, boxes overlapping) in a cell overlap on page %d: "
            "NOT RUN here -- run another page" % page)
    if third is not None:
        a, c, a2, c2 = third
        sub = [a, c, a2, c2]
        m = link(sub)
        ok = len({m.mark_of[x.key] for x in sub}) == 2 and m.mark_of[a.key] != m.mark_of[c.key]
        mb = link(sub, share_min=0.0, guard=False)
        broken_fuses = len({mb.mark_of[x.key] for x in sub}) == 1
        log("  (b) stacked third %s / %s seen from two cells: %d marks -- %s; broken arm fuses them: %s" % (
            a.key, c.key, len({m.mark_of[x.key] for x in sub}), "pass" if ok else "FAIL",
            "yes (the control can fail)" if broken_fuses else "NO -- the control cannot fail here"))
        fails += 0 if (ok and broken_fuses) else 1
    # (c)
    r1 = page_report(boxes, link(boxes))
    rows2 = json.loads(json.dumps(rows))
    boxes2 = boxes_from_rows(rows2, page, cells, local, views, ink)
    r2 = page_report(boxes2, link(boxes2))
    same = json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
    log("  (c) identical copy of the rows reads identically: %s" % ("pass" if same else "FAIL"))
    fails += 0 if same else 1
    log("  cells re-cut and matched stroke-for-stroke: %s; planted keys new: %s" % (dict(verify), "glyph/x/900001" not in keys))
    log("controls: %s%s" % ("ALL PASS" if fails == 0 else "%d FAILED" % fails, "" if third is not None else " ((b) NOT RUN on this page)"))
    return fails


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="page_marks")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("readout")
    r.add_argument("rec", nargs="+", help="one or more RECs; with --tiles, one sheet of 12 over all of them")
    r.add_argument("--pages", default=None, help="only with one REC")
    r.add_argument("--out", default=None)
    r.add_argument("--tiles", default=None)
    r.add_argument("--cell-map", default=None)
    c = sub.add_parser("controls")
    c.add_argument("rec")
    c.add_argument("--page", type=int, required=True)
    c.add_argument("--cell-map", default=None)
    a = ap.parse_args(argv)
    cm = pathlib.Path(a.cell_map) if a.cell_map else None
    if a.cmd == "readout":
        pages = [int(p) for p in a.pages.split(",")] if a.pages else None
        if pages and len(a.rec) > 1:
            raise SystemExit("--pages takes one REC")
        pool: List[Dict[str, Any]] = []
        for i, rec in enumerate(a.rec):
            out = pathlib.Path(a.out) / ("rec%d" % i) if (a.out and len(a.rec) > 1) else (pathlib.Path(a.out) if a.out else None)
            run(rec, pages, out, None, cm, tile_pool=pool if a.tiles else None)
        if a.tiles:
            cut_mark_tiles(pool, pathlib.Path(a.tiles))
            print("tiles: %s/tiles (key.json beside the folder)" % a.tiles)
        return 0
    return 1 if controls(a.rec, a.page, cm) else 0


if __name__ == "__main__":
    sys.exit(main())
