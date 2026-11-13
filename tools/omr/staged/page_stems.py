"""ROADMAP 2.306 -- STEMS READ ONCE ON THE PAGE (flag `OMR_PAGE_STEMS`, default OFF). STAGED GATHER (the read, the claim, the views) + ADJUDICATE
(`stem_value.adjudicate_head_stem` reads the page's answer first).

    Sean 2026-11-12 "Start the stem work" (step 0: benchmarks/page-ledger-2026-11/FINDINGS.md "2.306 step 0"). CLAUDE §3 claim order (heads -> stems ->
    beams/flags), §5 (stems: up -> right, down -> left; every head on one stem shares one value; measure against the staff LOCALLY).

WHAT. A head's stem is the page map's VERTICAL stroke (`page_strokes.PageMap`, read once for the page, `Q.PAGE_STROKE`) that stands at the head's
ENGRAVING SIDE: its centre line within `EDGE_SP` of the head's RIGHT edge and reaching at least `REACH_SP` ABOVE the head's centre (stem up), or within
`EDGE_SP` of its LEFT edge and reaching `REACH_SP` BELOW (stem down). Distances are in the stroke's OWN local staff space (`staff_space_local`). The
head is the 2.290 page head (`page_heads.OneHeads`: twin boxes are one head; its oval where it has one, else its strongest box). Every head the stroke
holds is one chord on it (they share one written value -- read later, by the flag / beam readers; NOTHING here decides a value).

A head no stroke stands beside on its engraving side may be the displaced head of a SECOND: it stands on the stroke's OTHER side, within
`SECOND_DY_SP` of a head the stroke holds on its engraving side (page-facts: the stem of a second sits on the partner; 2.300 one chord one event).

WHAT IS NOT A STEM. A stroke an earlier page-wide claim holds (CLAUDE §3: barlines, clef / key / meter, words, arcs, rests, tremolo slashes, own-ink
accidentals claim first): the page-stroke claims on the log (`page_strokes` ids), the READ area claims (`page_claim_names.area_names`, the register's
own predicate, as 2.288 rests use it) and the detector's boxed accidentals (`strokes_by_share`, the register's one cut). Such a stroke is MARKED
(`held`, with its owner), never taken.

ABSTAIN, NEVER GUESS. No free stroke: `no_stroke` (the nearest held / near-miss strokes are recorded). Two free strokes of the same side: `two_candidates`
with both and the signed margin (`fit` = EDGE_SP - |dx| in spaces; margin = best - second). One up at the right and one down at the left: `two_voices`
(a unison of two voices, page-facts; the old join's own rule then decides). Each head's reading is filed on each of its glyph keys (`Q.PAGE_STEM`).

THE CUT-OFFS ARE MEASUREMENTS, so they only NARROW (CLAUDE §4): measured on the 2306 step-0 gathers (Brahms p0+p5, Litolff p6+p16) against the
cell reader A's joined stems: the stem centre stands -0.22..+0.05 sp past a head's right edge (5-95%, Brahms), +0.03..+0.20 past its left; the page
map splits a stem at its head (the head's oval claim takes the stub), so the stroke's head-side end lies up to ~1.8 sp past the head's centre
(`GAP_SP`). Against Sean's Brahms p0 stem labels (277): 275 found, 31 page stems not his (prototype; the lane's tiles are the evidence).
CONVENTION ASSUMED: a stem is a vertical stroke at the head's engraving side. WHAT WOULD FALSIFY IT: a head whose stem the page map fused into
another stroke (Litolff merges: no free vertical; counted as `no_stroke`). NOT CONFIRMED by Sean beyond his p0 labels.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

DERIVED_CHECK = False
ENV = "OMR_PAGE_STEMS"
SOURCE = "page_stems"
OWNER = "stem"
UNIT = "page_ink"
#: the stem's centre line stands within this many local spaces of the head's side edge (measured, module doc)
EDGE_SP = 0.4
#: a stem reaches at least this far past the head's centre, away from the head (a stem is ~3.5 spaces; a sharp's vertical ~1.5 each way)
REACH_SP = 1.5
#: the stroke's head-side end may stop this far past the head's centre (the page map splits the stem at the head; measured, module doc)
GAP_SP = 2.0
#: a second's displaced head stands within this many spaces (vertically) of a head the stroke holds on its engraving side
SECOND_DY_SP = 1.2
#: where a head meets two strokes, a stroke whose head end stops more than this past the head's centre ends at ANOTHER head (Brahms p0 staff 11:
#: the divisi third's partner stem ends 0.65-0.84 sp away, the head's own at 0.0-0.24); measured, so it only narrows
HEAD_END_SP = 0.5
#: a stroke this far (spaces) from a head edge is reported as a near miss when a head reads no stroke
NEAR_SP = 1.0


def enabled() -> bool:
    """`OMR_PAGE_STEMS` (ROADMAP 2.306), default OFF: allow-list, so an empty value or a typo cannot switch a document onto an unpriced change."""
    return os.environ.get(ENV, "0").strip().lower() in ("1", "true", "yes", "on")


# ───────────────────────────── the read (pure) ─────────────────────────────

def _fits(h: Dict[str, Any], st: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The ways stroke `st` can be head `h`'s stem: `[{side, direction, dx, reach, gap, fit}]` (spaces), engraving side only."""
    x0, y0, x1, y1 = h["box"]
    cy = (y0 + y1) / 2.0
    sx0, sy0, sx1, sy1 = st["box"]
    sp = float(st.get("sp") or h.get("sp") or 1.0)
    sxc = (sx0 + sx1) / 2.0
    out = []
    # stem up: at the RIGHT edge, reaching up; its bottom end no further than GAP above the centre
    dx = (sxc - x1) / sp
    up_reach, up_gap = (cy - sy0) / sp, (cy - sy1) / sp
    if abs(dx) <= EDGE_SP and up_reach >= REACH_SP and up_gap <= GAP_SP:
        out.append(dict(side="right", direction="up", dx=round(dx, 3), reach=round(up_reach, 2), gap=round(max(0.0, up_gap), 2), fit=round(EDGE_SP - abs(dx), 3)))
    dx = (sxc - x0) / sp
    dn_reach, dn_gap = (sy1 - cy) / sp, (sy0 - cy) / sp
    if abs(dx) <= EDGE_SP and dn_reach >= REACH_SP and dn_gap <= GAP_SP:
        out.append(dict(side="left", direction="down", dx=round(dx, 3), reach=round(dn_reach, 2), gap=round(max(0.0, dn_gap), 2), fit=round(EDGE_SP - abs(dx), 3)))
    return out


def _other_side(h: Dict[str, Any], st: Dict[str, Any]) -> Optional[str]:
    """A second's displaced head: the stroke stands at the head's OTHER edge (`left` = the stroke is at the head's left edge, i.e. an up stem's
    displaced head sits to its right), within EDGE_SP. Returns the stem direction the stroke would have, or None."""
    x0, y0, x1, y1 = h["box"]
    cy = (y0 + y1) / 2.0
    sx0, sy0, sx1, sy1 = st["box"]
    sp = float(st.get("sp") or h.get("sp") or 1.0)
    sxc = (sx0 + sx1) / 2.0
    if not (sy0 - GAP_SP * sp <= cy <= sy1 + GAP_SP * sp):
        return None
    if abs(sxc - x0) / sp <= EDGE_SP and (cy - sy0) / sp >= REACH_SP:
        return "up"         # up stem on the head's left: the head is the right-hand head of a second on an up stem
    if abs(sxc - x1) / sp <= EDGE_SP and (sy1 - cy) / sp >= REACH_SP:
        return "down"       # down stem on the head's right: the left-hand head of a second on a down stem
    return None


def read(heads: Sequence[Dict[str, Any]], verticals: Sequence[Dict[str, Any]], held: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    """The page's stems (module doc). Pure. `heads`: `[{id, members, box (x0, y0, x1, y1) page px, sp}]`; `verticals`: `[{ord, box (x0, y0, x1, y1), sp}]`
    (the page map's vertical strokes); `held`: `{ord: owner}` of strokes an earlier claim holds. Returns `{"heads": {id: reading}, "stems": {ord: stem},
    "census": {...}}`; a reading is `{state, stroke, direction, side, candidates, held, near, margin, how}`."""
    held = held or {}
    t0 = time.time()
    vs = sorted(verticals, key=lambda v: v["box"][0])
    xs = [v["box"][0] for v in vs]
    import bisect
    maxw = max([v["box"][2] - v["box"][0] for v in vs] or [0.0])

    def near(h: Dict[str, Any], pad: float) -> List[Dict[str, Any]]:
        x0, x1 = h["box"][0] - pad, h["box"][2] + pad
        i = bisect.bisect_left(xs, x0 - maxw)
        j = bisect.bisect_right(xs, x1)
        return [v for v in vs[i:j] if v["box"][2] >= x0 and v["box"][0] <= x1]

    readings: Dict[Any, Dict[str, Any]] = {}
    for h in heads:
        sp = float(h.get("sp") or 1.0)
        cands, held_c, miss = [], [], []
        for st in near(h, NEAR_SP * sp):
            fs = _fits(h, st)
            for f in fs:
                f = dict(f, stroke=int(st["ord"]))
                if int(st["ord"]) in held:
                    held_c.append(dict(f, owner=held[int(st["ord"])]))
                else:
                    cands.append(f)
            if not fs:
                miss.append(int(st["ord"]))
        by_stroke: Dict[int, Dict[str, Any]] = {}
        for f in sorted(cands, key=lambda t: -t["fit"]):
            by_stroke.setdefault(f["stroke"], f)
        cs = sorted(by_stroke.values(), key=lambda t: -t["fit"])
        if len(cs) >= 2:
            # a stem's head end stands AT its head: where some candidates end at this head (gap <= HEAD_END_SP) and others end at a neighbour's
            # (the two voices of a divisi a third apart: each head also meets the other head's stem, ending ~0.7 sp away), the ones ending here stay
            at = [c for c in cs if c["gap"] <= HEAD_END_SP]
            if at and len(at) < len(cs):
                cs = at
        r: Dict[str, Any] = dict(candidates=cs, held=held_c, near=miss[:4])
        if len(cs) == 1:
            r.update(state="one", stroke=cs[0]["stroke"], direction=cs[0]["direction"], side=cs[0]["side"], margin=cs[0]["fit"], how="engraving_side")
        elif not cs:
            r.update(state="none", stroke=None, direction=None, side=None, margin=None, how="no_stroke")
        elif {c["direction"] for c in cs} == {"up", "down"} and len(cs) == 2:
            r.update(state="two_voices", stroke=None, direction=None, side=None, margin=round(cs[0]["fit"] - cs[1]["fit"], 3), how="two_voices")
        else:
            r.update(state="two", stroke=None, direction=None, side=None, margin=round(cs[0]["fit"] - cs[1]["fit"], 3), how="two_candidates")
        readings[h["id"]] = r
    # the stems: every stroke one head reads; direction = its heads' (one direction per stroke, else the stroke is two readings and abstains)
    stems: Dict[int, Dict[str, Any]] = {}
    for h in heads:
        r = readings[h["id"]]
        if r["state"] == "one":
            s = stems.setdefault(r["stroke"], dict(ord=r["stroke"], heads=[], directions=set()))
            s["heads"].append(h["id"])
            s["directions"].add(r["direction"])
    # one stroke read as an up stem by one head and a down stem by another: a stem has ONE head end. Where only one direction's heads have head ink
    # (the 2.290 oval: a box at the stem's far end with no head ink is a beam piece or a tip box, not a head), that direction holds the stroke and the
    # other heads read no stroke; else the stroke is two readings and every head on it abstains.
    hb0 = {h["id"]: h for h in heads}
    split = [o for o, s in stems.items() if len(s["directions"]) > 1]
    n_kept = 0
    for o in split:
        inked = {d for d in stems[o]["directions"] if any(hb0[k].get("ink") and readings[k]["direction"] == d for k in stems[o]["heads"])}
        keep = next(iter(inked)) if len(inked) == 1 else None
        for hid in list(stems[o]["heads"]):
            r = readings[hid]
            if keep is not None and r["direction"] == keep:
                continue
            r.update(state="none" if keep is not None else "two", stroke=None, direction=None, side=None,
                     how="stroke_held_by_inked_heads" if keep is not None else "stroke_read_both_ways", margin=0.0)
            stems[o]["heads"].remove(hid)
        if keep is None:
            del stems[o]
        else:
            stems[o]["directions"] = {keep}
            n_kept += 1
    # seconds: a head with no stroke, at the OTHER edge of a stem whose engraving-side head stands within SECOND_DY_SP
    hb = {h["id"]: h for h in heads}
    vby = {int(v["ord"]): v for v in vs}
    for h in heads:
        r = readings[h["id"]]
        if r["state"] != "none":
            continue
        sp = float(h.get("sp") or 1.0)
        cy = (h["box"][1] + h["box"][3]) / 2.0
        got = []
        for st in near(h, NEAR_SP * sp):
            o = int(st["ord"])
            if o not in stems or o in held:
                continue
            d = _other_side(h, st)
            if d is None or d not in stems[o]["directions"]:
                continue
            if any(abs(cy - (hb[k]["box"][1] + hb[k]["box"][3]) / 2.0) <= SECOND_DY_SP * sp for k in stems[o]["heads"]):
                got.append((o, d))
        if len(got) == 1:
            o, d = got[0]
            r.update(state="second", stroke=o, direction=d, side="other", margin=None, how="second_on_partner_stem")
            stems[o]["heads"].append(h["id"])
    for o, s in stems.items():
        st = vby[o]
        s["direction"] = next(iter(s["directions"]))
        s["box"] = [round(float(v), 1) for v in st["box"]]
        s["tip_y"] = round(float(st["box"][1] if s["direction"] == "up" else st["box"][3]), 1)
        s["directions"] = sorted(s["directions"])
    census: Dict[str, Any] = dict(heads=len(heads), verticals=len(verticals), held=len(held), stems=len(stems), split_both_ways=len(split),
                                  split_kept_by_head_ink=n_kept)
    for r in readings.values():
        census[r["how"]] = census.get(r["how"], 0) + 1
    census["seconds_read"] = round(time.time() - t0, 3)
    return dict(heads=readings, stems=stems, census=census)


# ───────────────────────────── GATHER ─────────────────────────────

def _page_heads_of(one_heads: Any) -> List[Dict[str, Any]]:
    """The 2.290 page heads as the reader's input: one per group of boxes (twins folded), the head's oval where it has one, else its strongest box."""
    oval_of = {}
    for h in getattr(one_heads, "heads", None) or ():
        if h.get("oval"):
            oval_of[int(h["group"])] = tuple(float(v) for v in h["oval"])
    out = []
    for gi, g in enumerate(getattr(one_heads, "groups", None) or ()):
        if not g:
            continue
        items = [one_heads.items[i] for i in g]
        rep = max(items, key=lambda t: float(t.get("conf") or 0.0))
        box = oval_of.get(gi) or tuple(float(v) for v in rep["box"])
        out.append(dict(id=gi, members=[t["key"] for t in items], box=box, sp=float(rep.get("sp_head") or 1.0), ink=gi in oval_of))
    return out


def held_strokes(log: Any, page_sub: Any, page_map: Any, detections: Optional[Dict[str, List[Any]]], cells: Sequence[Any],
                 local: Dict[int, Tuple[int, int]]) -> Dict[int, str]:
    """`{page stroke ordinal: owner}` an earlier claim holds (module doc): page-stroke claims (every owner but the heads' own ovals and this reader),
    the READ area claims by the register's own predicate, the boxed accidentals by ink share."""
    from .record import Q, Scope
    from . import page_claim_names as PCN
    from . import stroke_owner as SO
    from . import stroke_map as SM
    held: Dict[int, str] = {}
    for r in log.rows(Q.CLAIMED_AREA, page_sub, scope=Scope.SELF_AND_DESCENDANTS):
        d = r.detail or {}
        if d.get("page_strokes") and d.get("standing", "READ") == "READ" and d.get("source") not in (SOURCE,) and d.get("owner") not in ("head", OWNER):
            for i in d["page_strokes"]:
                held.setdefault(int(i), str(d.get("owner") or "?"))
    index = PCN.StrokeIndex(*PCN._boxes_of(page_map))
    for r in log.rows(Q.CLAIMED_AREA, page_sub, scope=Scope.SELF_AND_DESCENDANTS):
        d = r.detail or {}
        v = r.value
        owner = str(d.get("owner") or "")
        if (d.get("unit") != "area" or d.get("standing", "READ") != "READ" or owner not in SO.AREA_OWNERS
                or not (isinstance(v, (list, tuple)) and len(v) == 4)):
            continue
        for i in PCN.area_names(index, v, d.get("scope") == "system" and d.get("cell") is None, owner):
            held.setdefault(int(i), owner)
    if detections:
        from .gather import _page_box
        from .record import Subject
        cell_by_key = {}
        for c in cells:
            key = local.get(c.staff_index)
            if key is not None:
                cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c
        for ck, dets in detections.items():
            sub = Subject.from_key(ck)
            c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
            if c is None:
                continue
            for d in dets:
                if getattr(d, "category", None) != "accidental" and not str(getattr(d, "smufl_name", "")).lower().startswith("accidental"):
                    continue
                pb = _page_box(c, d)
                if pb is None:
                    continue
                for i in PCN.strokes_by_share(page_map, pb, index, SM.COVER_SHARE_MIN):
                    held.setdefault(int(i), "accidental")
    return held


def gather_page_stems(log: Any, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], page_map: Any, one_heads: Any,
                      detections: Optional[Dict[str, List[Any]]] = None, *, progress: bool = False) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.306 (flag `OMR_PAGE_STEMS`, default OFF), STAGED GATHER: read the page's stems once (`read`), claim each stem stroke once (`Q.CLAIMED_AREA`,
    owner `stem`, `page_strokes`), and file each head's reading on every glyph key of the head (`Q.PAGE_STEM`: value = the `Q.STEM` row of THAT key's cell
    the stem is -- the cell reader's row on the stroke, else a view of the page stroke filed here, reader CV_PAGE_STEMS, with its tip ink read as the cell
    reader's are -- or an abstention with the candidates and margin). AFTER every earlier page-wide claim (the head claims last), BEFORE the page beams."""
    if not enabled() or page_map is None or one_heads is None or not getattr(page_map, "strokes", None):
        return None
    from . import record as R
    from .record import Q, READERS, ABSTAIN, Subject
    from . import gather as G
    t0 = time.time()
    p = int(getattr(pws.page, "page_index", 0))
    page_sub = R.page(p)
    sp_page = float(page_map.sp)
    verticals = []
    for i, st in enumerate(page_map.strokes):
        if st.kind != "vertical":
            continue
        x, y, w, h = (float(v) for v in st.box)
        verticals.append(dict(ord=i, box=(x, y, x + w, y + h), sp=float(getattr(st, "staff_space_local", None) or sp_page)))
    heads = _page_heads_of(one_heads)
    held = held_strokes(log, page_sub, page_map, detections, cells, local)
    res = read(heads, verticals, held)
    cell_by_key: Dict[Tuple[int, int, int, int], Any] = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c
    vby = {v["ord"]: v for v in verticals}
    views: Dict[Tuple[str, int], str] = {}
    n_view = n_a = 0
    head_of = {h["id"]: h for h in heads}
    for hid, r in res["heads"].items():
        h = head_of[hid]
        for key in h["members"]:
            g = Subject.from_key(key)
            c = cell_by_key.get((g.page, g.system, g.staff, g.cell))
            csub = R.cell(g.page, g.system, g.staff, g.cell)
            gsub = R.glyph(g.page, g.system, g.staff, g.cell, g.glyph)
            common = dict(reader=READERS.CV_PAGE_STEMS, frame=G.frame_cell(g.cell), head=hid, how=r["how"], candidates=r["candidates"],
                          held=r["held"], near=r["near"], margin=r["margin"])
            if r["stroke"] is None or c is None:
                log.abstain(gsub, Q.PAGE_STEM, reason=(ABSTAIN.NO_LINE_ACCEPTED if r["stroke"] is None and r["state"] == "none" else ABSTAIN.AMBIGUOUS),
                            note=r["how"] if c is not None else "no_cell", **common)
                continue
            ck = (csub.to_key(), int(r["stroke"]))
            if ck not in views:
                views[ck], from_a = _cell_row_for(log, c, csub, vby[int(r["stroke"])]["box"])
                n_a += int(from_a)
                n_view += int(not from_a)
            log.observe(gsub, Q.PAGE_STEM, views[ck], page_stroke=int(r["stroke"]), direction=r["direction"], side=r["side"],
                        tip_y=res["stems"][int(r["stroke"])]["tip_y"], stem_box=res["stems"][int(r["stroke"])]["box"], **common)
    filed = 0
    for o, s in sorted(res["stems"].items()):
        log.observe(page_sub, Q.CLAIMED_AREA, int(o), reader=READERS.CV_PAGE_STEMS, frame=G.FRAME_PAGE, owner=OWNER, unit=UNIT, standing="READ",
                    source=SOURCE, how="head_engraving_side", page_strokes=[int(o)], direction=s["direction"], heads=list(s["heads"]),
                    tip_y=s["tip_y"], stem_box=s["box"])
        filed += 1
    cen = dict(res["census"], claims=filed, rows_from_cell_reader=n_a, views_filed=n_view, seconds=round(time.time() - t0, 2))
    log.observe(page_sub, Q.CLAIMED_AREA, "census", reader=READERS.CV_PAGE_STEMS, frame=G.FRAME_PAGE, owner=SOURCE, unit="page_ink_census",
                standing="READ", source=SOURCE, **cen)
    if progress:
        print("  gather page stems (2.306) p%s: %s" % (p, cen))
    return res


def _cell_row_for(log: Any, c: Any, csub: Any, stroke_box: Sequence[float]) -> Tuple[str, bool]:
    """The `Q.STEM` row of cell `c` that IS this page stroke: the cell reader's row on it (its centre on the stroke's centre line, the longer on a tie),
    else a view of the stroke filed here (reader CV_PAGE_STEMS, A's row shape in cell-canonical px, not clipped to the cell) with its tip ink read as
    `gather_cv_lines` reads a stem's (`_observe_stem_tip_ink`). Returns `(row id, from the cell reader)`."""
    from .record import Q, READERS
    from . import gather as G
    rect, up = getattr(c, "bbox_page_px", None), getattr(c, "upscale_factor", None)
    x0, y0, x1, y1 = (float(v) for v in stroke_box)
    sxc = (x0 + x1) / 2.0
    best = None
    for r in log.rows(Q.STEM, csub):
        if r.reader != READERS.CV_LINES or not isinstance(r.value, (list, tuple)) or len(r.value) < 4 or not rect or not up:
            continue
        ax, ay, aw, ah = (float(v) for v in r.value[:4])
        px0, py0, px1, py1 = rect[0] + ax / up, rect[1] + ay / up, rect[0] + (ax + aw) / up, rect[1] + (ay + ah) / up
        ov = min(py1, y1) - max(py0, y0)
        if abs((px0 + px1) / 2.0 - sxc) <= max(3.0, (x1 - x0)) and ov >= 0.5 * min(py1 - py0, y1 - y0):
            if best is None or ah > best[1]:
                best = (r.id, ah)
    if best is not None:
        return best[0], True
    cx, cy, cw, ch = (x0 - rect[0]) * up, (y0 - rect[1]) * up, (x1 - x0) * up, (y1 - y0) * up
    frame = G.frame_cell(c.measure_index)
    row = log.observe(csub, Q.STEM, [cx, cy, cw, ch], reader=READERS.CV_PAGE_STEMS, frame=frame, image="page_strokes")
    grid = G._cell_grid(c)
    space = grid[1] * 2.0 if grid is not None else None
    try:
        G._observe_stem_tip_ink(log, csub, frame, c, row.id, (cx, cy, cw, ch), (), space)
    except Exception:          # noqa: BLE001 -- a raster the tip reader cannot read leaves the view with no tip row (`_beam_reader_looked`: never ran)
        pass
    return row.id, False


# ADJUDICATE reads `Q.PAGE_STEM` in `adjudicators.stem_value._page_stem_join` (the reader lives in the stage that reads it: `staged.reach`).
