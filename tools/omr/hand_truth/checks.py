"""Claude's double-check, step 1: FIXED consistency checks over a labeled page (plan C5).

Sean 2026-10-08: *"After I hand label a page I would want Claude to double
check my work."* These checks need no model and cannot hallucinate; each one
encodes a printed-page fact already in CLAUDE.md §10 or DECISIONS. They only
FLAG (rule 7): Sean accepts a flag (and fixes the page) or rejects it (the page
was right). A flag Sean resolved is never raised again — each one is keyed on
its kind and the boxes or region it names.

The scale is the page's own: one staff space, measured from the cells' staff
lines (or, with no measure cell, from the median notehead height — a notehead
is one space tall).

``unboxed_ink``        an ink component the ink-coverage control found in no box
``duplicate_box``      two boxes of one family on one mark (IoU >= 0.8)
``dot_without_head``   an augmentation dot with no notehead just to its left
``accidental_without_head`` an in-bar accidental with no notehead just to its right
``stem_without_head``  a stem touching no notehead
``beam_with_one_stem`` a beam that meets fewer than two stems
``far_head_no_ledger`` a head more than a space outside its staff with no ledger
                       line between it and the staff (Sean 2026-09-29: "there is
                       no such thing as a far note with no ledger line")
``tie_heads_differ``   a tie whose two end heads sit at different heights
                       (a tie's two heads are at one staff position, §10)
``staff_starts_without_clef`` a staff's first measure cell holds no clef box

Deliberately NOT checked: a missing KEY signature — C major prints none, so its
absence cannot be told from a miss (rule 8).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from tools.omr.hand_truth.completeness import InkReport, family_of
from tools.omr.hand_truth.store import Box, Flag, PageTruth, Rect

BY = "check:fixed"


def _cx(r: Rect) -> float:
    return (r[0] + r[2]) / 2


def _cy(r: Rect) -> float:
    return (r[1] + r[3]) / 2


def _iou(a: Rect, b: Rect) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    if inter <= 0:
        return 0.0
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)


def staff_lines_page(page: PageTruth) -> List[Tuple[Rect, List[float]]]:
    """(cell rect, the five line ys in PAGE pixels) for every measure cell."""
    out = []
    for c in page.cells:
        if c.kind == "measure" and c.staff_line_ys and len(c.staff_line_ys) >= 5:
            ys = [c.to_page((0, y, 1, y + 1))[1] for y in c.staff_line_ys]
            out.append((c.rect, sorted(ys)))
    return out


def staff_space(page: PageTruth) -> Optional[float]:
    gaps = [np.diff(ys).mean() for _, ys in staff_lines_page(page)]
    if gaps:
        return float(np.median(gaps))
    heads = [b.rect[3] - b.rect[1] for b in page.boxes if family_of(b.cls) == "notehead"]
    return float(np.median(heads)) if heads else None


def _fam(page: PageTruth, fam: str) -> List[Box]:
    return [b for b in page.boxes if family_of(b.cls) == fam]


def _key(kind: str, box_ids=(), rect: Optional[Rect] = None) -> Tuple:
    return (kind, tuple(sorted(box_ids)), tuple(int(round(v)) for v in rect) if rect else None)


def _known(page: PageTruth) -> set:
    return {_key(f.kind, f.box_ids, f.rect if not f.box_ids else None) for f in page.flags}


def _raise(page: PageTruth, known: set, out: List[Flag], kind: str, message: str, *,
           box_ids=(), rect: Optional[Rect] = None, cell_id: Optional[str] = None) -> None:
    k = _key(kind, box_ids, rect if not box_ids else None)
    if k in known:
        return
    known.add(k)
    out.append(page.raise_flag(kind, message, by=BY, box_ids=list(box_ids), rect=rect, cell_id=cell_id))


def run_all(page: PageTruth, ink: Optional[InkReport] = None) -> List[Flag]:
    """Run every fixed check; raise only flags not raised before. Returns the new ones."""
    known = _known(page)
    new: List[Flag] = []
    sp = staff_space(page)
    if ink is not None:
        for u in ink.uncovered:
            _raise(page, known, new, "unboxed_ink",
                   f"ink with no box ({u['area']} px, {int(u['covered_frac'] * 100)}% boxed)",
                   rect=tuple(float(v) for v in u["rect"]))
    boxes = page.boxes
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if family_of(a.cls) == family_of(b.cls) and _iou(a.rect, b.rect) >= 0.8:
                _raise(page, known, new, "duplicate_box",
                       f"{a.cls} {a.id} and {b.cls} {b.id} box the same mark", box_ids=(a.id, b.id))
    if sp is None:
        return new
    heads = _fam(page, "notehead")

    def near(r: Rect, x0: float, x1: float, dy: float) -> bool:
        """A notehead overlapping the band x0..x1, its centre within dy of r's."""
        return any(h.rect[2] >= x0 and h.rect[0] <= x1 and abs(_cy(h.rect) - _cy(r)) <= dy
                   for h in heads)

    for d in _fam(page, "augmentation_dot"):
        if not near(d.rect, d.rect[0] - 2.5 * sp, d.rect[0] + 0.2 * sp, 1.0 * sp):
            _raise(page, known, new, "dot_without_head", f"dot {d.id} has no notehead to its left",
                   box_ids=(d.id,), cell_id=d.cell_id)
    for a in _fam(page, "accidental"):
        if not near(a.rect, a.rect[2] - 0.2 * sp, a.rect[2] + 2.5 * sp, 1.0 * sp):
            _raise(page, known, new, "accidental_without_head",
                   f"{a.cls} {a.id} has no notehead to its right", box_ids=(a.id,), cell_id=a.cell_id)
    stems = _fam(page, "stem")
    for s in stems:
        ok = any(h.rect[2] >= s.rect[0] - 0.6 * sp and h.rect[0] <= s.rect[2] + 0.6 * sp
                 and h.rect[3] >= s.rect[1] - 0.5 * sp and h.rect[1] <= s.rect[3] + 0.5 * sp for h in heads)
        if not ok:
            _raise(page, known, new, "stem_without_head", f"stem {s.id} touches no notehead",
                   box_ids=(s.id,), cell_id=s.cell_id)
    if stems:
        for bm in _fam(page, "beam"):
            g = 0.3 * sp
            n = sum(1 for s in stems if s.rect[2] >= bm.rect[0] - g and s.rect[0] <= bm.rect[2] + g
                    and s.rect[3] >= bm.rect[1] - g and s.rect[1] <= bm.rect[3] + g)
            if n < 2:
                _raise(page, known, new, "beam_with_one_stem", f"beam {bm.id} meets {n} stem(s)",
                       box_ids=(bm.id,), cell_id=bm.cell_id)
    ledgers = _fam(page, "ledger_line")
    staves = staff_lines_page(page)
    for h in heads:
        y = _cy(h.rect)
        owners = [(rect, ys) for rect, ys in staves if rect[0] <= _cx(h.rect) <= rect[2]]
        if not owners:
            continue
        rect, ys = min(owners, key=lambda o: min(abs(y - o[1][0]), abs(y - o[1][-1])))
        top, bot = ys[0], ys[-1]
        if top - 1.0 * sp <= y <= bot + 1.0 * sp:
            continue
        lo, hi = (y, top) if y < top else (bot, y)
        if not any(l.rect[2] >= h.rect[0] and l.rect[0] <= h.rect[2]
                   and l.rect[3] >= lo - 0.5 * sp and l.rect[1] <= hi + 0.5 * sp for l in ledgers):
            _raise(page, known, new, "far_head_no_ledger",
                   f"{h.cls} {h.id} sits {abs(y - (top if y < top else bot)) / sp:.1f} spaces off its "
                   "staff with no ledger line", box_ids=(h.id,), cell_id=h.cell_id)
    for t in _fam(page, "tie"):
        ends = []
        for x in (t.rect[0], t.rect[2]):
            cand = [h for h in heads if abs(_cx(h.rect) - x) <= 1.0 * sp
                    and t.rect[1] - 1.5 * sp <= _cy(h.rect) <= t.rect[3] + 1.5 * sp]
            ends.append(min(cand, key=lambda h: abs(_cx(h.rect) - x)) if cand else None)
        if all(ends) and abs(_cy(ends[0].rect) - _cy(ends[1].rect)) > 0.5 * sp:
            _raise(page, known, new, "tie_heads_differ",
                   f"tie {t.id} joins heads {ends[0].id} and {ends[1].id} at different heights",
                   box_ids=(t.id, ends[0].id, ends[1].id), cell_id=t.cell_id)
    clefs = _fam(page, "clef")
    firsts: Dict[Tuple[int, int], Tuple[int, str, Rect]] = {}
    for c in page.cells:
        if c.kind == "measure" and c.system is not None:
            k = (c.system, c.staff)
            if k not in firsts or (c.measure or 0) < firsts[k][0]:
                firsts[k] = (c.measure or 0, c.id, c.rect)
    for (sy, st), (_, cid, r) in sorted(firsts.items()):
        if not any(r[0] <= _cx(b.rect) <= r[2] and r[1] <= _cy(b.rect) <= r[3] for b in clefs):
            _raise(page, known, new, "staff_starts_without_clef",
                   f"staff {sy}.{st} starts with no clef box in {cid}", rect=r, cell_id=cid)
    return new
