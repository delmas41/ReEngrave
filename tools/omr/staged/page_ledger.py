"""ROADMAP 2.284 -- THE PAGE LEDGER OWNS THE INK: one owner per PAGE stroke, resolved once; every cell view reads it (flag `OMR_PAGE_LEDGER_OWNS`,
default OFF). STAGED, GATHER (the link) + ADJUDICATE (the one settle).

    Sean 2026-11-09 ("Fix 2", after the 2.283 audit): "the page ledger owns the ink, one owner per page stroke, one consult for every box family ...".
    CLAUDE north star: all ink is accounted for ONE time. CLAUDE §3 claim order; docs/plan-2026-11-03-page-ledger.md §B (the page is the ledger, a
    cell is a view).

THE CAUSE (benchmarks/page-ledger-owns-2026-11/FINDINGS.md, step 1). Ownership is settled per PADDED CELL (`adjudicators/stroke_owner`): the same
page ink is a stroke in two cells' maps, and each cell settles it from the claims IT can see. A barline's area claim and an arc's traced ink
(`[[cell, ordinal]]`) are filed for ONE cell, so the neighbour cell's copy of the same ink stands unclaimed there, and that cell's stem / beam / flag
consumers may read it. Measured on fresh gathers (`disagree_probe.py`): two cells name different owners for the same page pixel on a few percent of
the non-staff ink, almost all of it "an owner in one cell, none in the other".

WHAT, in two halves.

  GATHER (`link_cell_strokes`, inside `gather.gather_stroke_map`): each cell stroke is LINKED to the page stroke (`Q.PAGE_STROKE`, the page map built
  before the arcs, 2.260b M3) that holds its ink: its pixels mapped into the page map's frame, the page stroke holding the most of them, and that
  share. Filed on the cell's `Q.STROKE` row as `page_stroke: [ordinal, share]`. Pure geometry; decides nothing. A carved barline rule
  (`page_strokes.carve_columns`, no mask) holds the carved rows of its column box.

  ADJUDICATE (`settle_page`, called once per page before the cells' `Q.STROKE_OWNER` verdicts are made): every cell's candidates (the same
  `stroke_owner.own_strokes`, unchanged: boxes, register areas, arc / hairpin traces, layers, vetoes, shapes) are pooled PER PAGE STROKE over the
  cells that see it -- a claimant counted once by its key -- and settled ONCE by the same table (`stroke_owner._settle`). Each cell's verdict then
  READS that one ownership for every linked stroke; it never re-derives it. Box verdicts, the claim-final census and every consumer read the cell
  verdict as before, so nothing downstream changes its code.

THE LINK RULE (`LINK_SHARE_MIN`). A cell stroke joins a page stroke only where at least this share of ITS ink lies on that one page stroke: a piece
the cell edge cut (all of its ink on the one page stroke) joins; a piece the cell fused from two page strokes (a head touching a barline the page map
carved) does not, and keeps its cell's own verdict -- a fused piece's claims would otherwise be given to the other mark's ink in another cell.
CONVENTION ASSUMED: one page stroke is one mark's ink (the page map's own split, the same finders as the cell map). WHAT WOULD FALSIFY IT: a page
stroke that is two marks fused while one cell cut them apart (then two owners pool on one stroke and it reads contested: counted, never chosen).
NOT CONFIRMED by Sean.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

DERIVED_CHECK = False
ENV = "OMR_PAGE_LEDGER_OWNS"
#: a cell stroke joins a page stroke when at least this share of its own ink lies on that one page stroke (module doc)
LINK_SHARE_MIN = 0.8


def enabled() -> bool:
    """`OMR_PAGE_LEDGER_OWNS` (ROADMAP 2.284), default OFF: allow-list, so an empty value or a typo cannot switch a document onto an unpriced change."""
    return os.environ.get(ENV, "0").strip().lower() in ("1", "true", "yes", "on")


# ───────────────────────────── GATHER: the link ─────────────────────────────

class PageLabels:
    """The page map's strokes painted into one label image in the map's reduced frame (0 = no stroke, i + 1 = `Q.PAGE_STROKE` ordinal i), the carved
    barline rules painted where no stroke stands inside their column box, and one pixel of dilation into the background (a stroke's edge in the cell's
    reduced frame lies a fraction of a pixel off the page's)."""

    def __init__(self, page_map: Any, shape_px: Sequence[int]):
        import cv2
        s = float(page_map.scale)
        h, w = int(np.ceil(shape_px[0] * s)) + 2, int(np.ceil(shape_px[1] * s)) + 2
        lab = np.zeros((h, w), np.int32)
        n = len(page_map.strokes)
        for i, (m, x0, y0) in enumerate(page_map.masks):
            if getattr(m, "size", 0) == 0:
                continue
            mh, mw = m.shape
            y1, x1 = min(h, y0 + mh), min(w, x0 + mw)
            if y1 <= y0 or x1 <= x0:
                continue
            sub = lab[y0:y1, x0:x1]
            sub[m[:y1 - y0, :x1 - x0].astype(bool)] = i + 1
        for k, b in enumerate(getattr(page_map, "barlines", None) or ()):
            bx0, by0, bx1, by1 = (float(v) for v in b["box"][:4])
            a0, a1 = max(0, int(np.floor(by0 * s))), min(h, int(np.ceil(by1 * s)) + 1)
            c0, c1 = max(0, int(np.floor(bx0 * s))), min(w, int(np.ceil(bx1 * s)) + 1)
            if a1 > a0 and c1 > c0:
                sub = lab[a0:a1, c0:c1]
                sub[sub == 0] = n + k + 1
        d = cv2.dilate(lab.astype(np.float32), np.ones((3, 3), np.uint8)).astype(np.int32)
        self.lab = np.where(lab == 0, d, lab)
        self.scale = s


def link_cell_strokes(res: Any, cell_rect: Sequence[float], upscale: float, labels: PageLabels) -> List[Optional[Tuple[int, float]]]:
    """Per cell stroke (ordinal = index of `res.strokes`): `(page stroke ordinal, share of the cell stroke's ink on it)` or None (no page stroke under
    it). `res` = the cell's `stroke_map.CellStrokes` (masks in its reduced frame, `res.scale` reduced / canonical); `cell_rect` / `upscale` = the
    cell's `bbox_page_px` and `upscale_factor` (canonical px = page px x upscale)."""
    out: List[Optional[Tuple[int, float]]] = []
    rs = float(res.scale)
    k = labels.scale / (rs * float(upscale))
    H, W = labels.lab.shape
    ox, oy = float(cell_rect[0]) * labels.scale, float(cell_rect[1]) * labels.scale
    for (m, x0, y0) in res.masks:
        ys, xs = np.nonzero(m)
        if xs.size == 0:
            out.append(None)
            continue
        px = np.clip(((x0 + xs + 0.5) * k + ox).astype(np.int64), 0, W - 1)
        py = np.clip(((y0 + ys + 0.5) * k + oy).astype(np.int64), 0, H - 1)
        ids = labels.lab[py, px]
        cnt = np.bincount(ids)
        cnt[0] = 0
        if cnt.size <= 1 or cnt.max() == 0:
            out.append(None)
            continue
        best = int(cnt.argmax())
        out.append((best - 1, round(float(cnt[best]) / float(xs.size), 3)))
    return out


# ───────────────────────────── ADJUDICATE: one settle per page ─────────────────────────────

def tier_index(tiers: Sequence[Sequence[str]]) -> Dict[str, int]:
    return {f: i for i, t in enumerate(tiers) for f in t}


def pool(cell_views: Dict[Any, Dict[int, Any]], links: Dict[Any, Dict[int, Tuple[int, float]]], tiers: Sequence[Sequence[str]]
         ) -> Tuple[Dict[int, Any], Dict[str, int]]:
    """PURE. `cell_views` = `{cell key: {ordinal: stroke_owner.Ownership}}` (each cell's own settle); `links` = `{cell key: {ordinal: (page id, share)}}`.
    Returns (`{page id: Ownership}` -- the one settle of the pooled candidates of every LINKED cell stroke, ordinal = the page id --, census).
    A claimant is pooled once per (key, how); candidates are ordered by claim tier, then key, as `own_strokes` lists them."""
    from . import stroke_owner as SO
    ti = tier_index(tiers)
    cands: Dict[int, List[Dict[str, Any]]] = {}
    seen: Dict[int, set] = {}
    members: Dict[int, int] = {}
    census: Dict[str, int] = {}
    for ck, view in cell_views.items():
        lk = links.get(ck) or {}
        for o, w in view.items():
            ln = lk.get(o)
            if ln is None or ln[1] < LINK_SHARE_MIN:
                census["unlinked_strokes"] = census.get("unlinked_strokes", 0) + 1
                continue
            pid = int(ln[0])
            members[pid] = members.get(pid, 0) + 1
            cs = cands.setdefault(pid, [])
            sn = seen.setdefault(pid, set())
            for c in w.candidates:
                key = (str(c["key"]), str(c.get("how", "")))
                if key in sn:
                    continue
                sn.add(key)
                cs.append(dict(c))
    out: Dict[int, Any] = {}
    for pid, cs in cands.items():
        cs.sort(key=lambda c: (ti.get(str(c["family"]), 0 if c.get("how") == "area" else 99), str(c["key"])))
        out[pid] = SO._settle(pid, {pid: cs}, {**ti, **{str(c["family"]): 0 for c in cs if str(c["family"]) not in ti}})
    census["page_strokes"] = len(members)
    census["page_strokes_seen_twice"] = sum(1 for n in members.values() if n > 1)
    return out, census


def apply(view: Dict[int, Any], link: Dict[int, Tuple[int, float]], page: Dict[int, Any]) -> Tuple[Dict[int, Any], Dict[str, int]]:
    """PURE. One cell's ownership with every LINKED stroke given the page's one settle (ordinal restored to the cell's). Returns (view, what changed)."""
    from dataclasses import replace
    out = dict(view)
    ch: Dict[str, int] = {}
    for o, w in view.items():
        ln = link.get(o)
        if ln is None or ln[1] < LINK_SHARE_MIN or int(ln[0]) not in page:
            continue
        p = page[int(ln[0])]
        nw = replace(p, ordinal=o)
        if (nw.state, nw.family) != (w.state, w.family):
            k = "%s:%s->%s:%s" % (w.state, w.family or "", nw.state, nw.family or "")
            ch[k] = ch.get(k, 0) + 1
        out[o] = nw
    return out, ch
