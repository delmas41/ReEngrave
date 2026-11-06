"""ROADMAP 2.273 -- A STAFF-ROW READ OF THE ARCS A BARLINE CUTS (flag `OMR_ARC_STRIP`, default OFF). STAGED GATHER; decides nothing.

Sean 2026-11-06 ("Yes build"): *"the cutoff of the orange boxes is with the barlines. That goes against the page wide read."* Standing rules:
arcs are read ONCE at page level and never re-read or broken up (2.260, 2.271); *"Often arcs stop short"*; the kind is page-facts' (two adjacent
same-position notes make a tie, anything else a slur) -- nothing here names a kind.

THE CAUSE. The detector runs per CELL, barline to barline (`gather.gather_detections`), so an arc a barline crosses is shown to the model as two
halves, each with its other end cut off: it boxes the far half of only 8% (Litolff) / 25% (Brahms) of such arcs (`benchmarks/omr-arc-binding-2026-10/
barline-crop-trial-2026-11/VERDICT.md`). The same production detector run once on the whole STAFF ROW at the same scale (16 px per staff space,
`max_det` raised so a row is not truncated at 300) boxes the far half of 70-75%.

WHAT THIS DOES, per staff row that holds at least one arc box cut at an interior cell edge (nothing else is run):
1. The strip is cut (`measure_extractor._build_measure_cell`, the cells' own rule) and the detector run once on it; only its tie/slur boxes are kept.
2. A strip box is a CANDIDATE only where it continues a cell-cut arc box across the barline (`continues`): same staff, y bands overlap, it starts
   before the barline and reaches back over half of the cut box, and ends at least `FAR_MIN_SPACES` past it. A strip box that continues nothing
   is dropped without a trace: the 20+ false boxes a page the unguarded strip adds all sit there.
3. Two guards, each recorded on the candidate with its measurement (the numbers are read off the record, never off a lane's own table):
   (a) `several_arcs_inside`: the candidate holds two or more cell arc boxes that are each a whole arc (cut at neither end);
   (b) `not_one_stroke`: the candidate's ink along its length is not ONE continuous arc stroke -- the existing thin-stroke follower
       (`arcs_system.trace_arc`) must cover at least `arcs_system.MIN_COVER` of its columns AND the traced centre line may turn at most
       `MAX_TURNS` times (one apex; three or more is a chain of arcs meeting at notes).
4. A kept candidate is FILED as detector boxes: for every cell the box reaches beyond the cut box's, a piece clipped to that cell is APPENDED to
   the cell's `detections` (every glyph index already filed is unchanged; the reader is the detector's, `source` `arc_strip`), unless a cell arc
   box already stands on it (the far half was boxed: nothing is added). `arcs_system.gather_system_arcs` then traces each piece, and
   `join_traces` makes the cut box and its far-half piece ONE curve -- the fold is the existing page trace's, not a new one.
Nothing replaces a cell box, so an arc the cells read whole is untouched.

CONVENTION ASSUMED: an arc the cell cut is the same arc the strip box continues where the strip box starts at the cut box's start. WHAT WOULD FALSIFY IT: a
tile where the box does not start and end on the notes it shows. NOT CONFIRMED: every cut-off below is set on Litolff 984073 and Brahms 317803 only.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

ENV = "OMR_ARC_STRIP"
ARC_CLASSES = ("tie", "slur")
#: The strip box must end at least this many spaces past the barline (the trial's rule).
FAR_MIN_SPACES = 0.75
#: ... and reach back over at least this share of the cut box's width.
REACH_BACK_SHARE = 0.5
#: y bands overlap by at least this share of the shorter.
Y_OVERLAP_MIN = 0.5
#: A cell arc box is inside the candidate where this share of its area is.
INSIDE_SHARE = 0.8
#: ... and a whole arc (cut at neither end) counts for guard (a); two of them make the candidate several arcs.
MAX_WHOLE_ARCS_INSIDE = 1
#: Guard (b): the traced centre line may turn (apex or cusp) at most this many times; each turn needs this much rise (spaces).
MAX_TURNS = 1
TURN_PROMINENCE_SPACES = 0.35
#: The detector's box cap for a row (ultralytics' default 300 truncates a whole row; the trial's rows reached 230).
MAX_DET = 3000
#: A clipped piece narrower than this (spaces) is not filed.
PIECE_MIN_SPACES = 0.75


def enabled() -> bool:
    """`OMR_ARC_STRIP` (ROADMAP 2.273), default OFF: only an explicit 1/true/yes/on enables it."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def _y_overlap(a: Sequence[float], b: Sequence[float]) -> float:
    o = min(a[3], b[3]) - max(a[1], b[1])
    return o / max(1e-9, min(a[3] - a[1], b[3] - b[1]))


def _inside_share(a: Sequence[float], b: Sequence[float]) -> float:
    """Share of `a`'s area inside `b`."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    ar = (a[2] - a[0]) * (a[3] - a[1])
    return ix / ar if ar > 0 else 0.0


def continues(cut: Dict[str, Any], box: Sequence[float]) -> bool:
    """Does strip box `box` (page px) continue the cut cell arc box `cut` ({box, side 'r'|'l', bar, sp}) across its barline? The trial's rule."""
    k, bar, sp = cut["box"], cut["bar"], cut["sp"]
    if _y_overlap(k, box) < Y_OVERLAP_MIN:
        return False
    kw = k[2] - k[0]
    if cut["side"] == "r":
        return box[2] >= bar + FAR_MIN_SPACES * sp and box[0] < bar and box[0] <= k[2] - REACH_BACK_SHARE * kw
    return box[0] <= bar - FAR_MIN_SPACES * sp and box[2] > bar and box[2] >= k[0] + REACH_BACK_SHARE * kw


def turns(points: Dict[int, Tuple[int, int]], sp: float) -> int:
    """How many times the traced centre line turns: its extremes, each separated from the last by at least `TURN_PROMINENCE_SPACES`. One arc has one
    (its apex); a chain of arcs meeting at notes has apex, cusp, apex ... (three or more)."""
    xs = sorted(points)
    if len(xs) < 3:
        return 0
    ys = [(points[x][0] + points[x][1]) / 2.0 for x in xs]
    need = TURN_PROMINENCE_SPACES * sp
    count, direction, ext = 0, 0, ys[0]          # direction +1 rising (y grows), -1 falling; ext = the extreme reached so far
    for y in ys[1:]:
        if direction == 0:
            if y - ext >= need:
                direction, ext = 1, y
            elif ext - y >= need:
                direction, ext = -1, y
        elif direction == 1:
            if y > ext:
                ext = y
            elif ext - y >= need:
                count, direction, ext = count + 1, -1, y
        else:
            if y < ext:
                ext = y
            elif y - ext >= need:
                count, direction, ext = count + 1, 1, y
    return count


def whole_arcs_inside(box: Sequence[float], cell_arcs: Sequence[Dict[str, Any]], sp: float) -> Tuple[int, int]:
    """(whole arcs, all arcs) among the cell arc boxes inside `box`: boxes touching across a cell edge (gap <= 1 space) count as one arc; a 'whole'
    arc is cut at neither end."""
    ins = [a for a in cell_arcs if _inside_share(a["box"], box) >= INSIDE_SHARE and _y_overlap(a["box"], box) >= 0.3]
    ins.sort(key=lambda a: a["box"][0])
    groups: List[List[Dict[str, Any]]] = []
    for a in ins:
        prev = groups[-1][-1] if groups else None
        # two boxes are pieces of ONE arc only where the left one is cut at its right edge and the right one at its left edge, side by side
        if (prev is not None and prev["cut_r"] and a["cut_l"] and a["box"][0] - prev["box"][2] <= sp
                and _y_overlap(a["box"], prev["box"]) >= 0.5):
            groups[-1].append(a)
        else:
            groups.append([a])
    whole = sum(1 for g in groups if not g[0]["cut_l"] and not g[-1]["cut_r"])
    return whole, len(groups)


# ─────────────────────────────────────────────────────────────────────────────
# The GATHER step
# ─────────────────────────────────────────────────────────────────────────────

def _accepts_max_det(detector: Any) -> bool:
    import inspect
    try:
        return "max_det" in inspect.signature(detector.detect).parameters
    except (TypeError, ValueError):
        return False


def gather_arc_strip(log: Any, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]],
                     detections: Dict[str, List[Any]], *, detector: Any = None, conf_threshold: float = 0.25,
                     progress: bool = False) -> Dict[str, Any]:
    """Run the staff-row strip pass (module doc) and APPEND the far-half pieces it keeps to `detections`. No-op (returns {}) unless `OMR_ARC_STRIP` is on.

    Every candidate leaves a row: a filed piece is a `Q.GLYPH_BOX` observation under `READERS.DETECTOR` (`source` `arc_strip`); a refused one is a
    `Q.GLYPH_BOX` abstention on the cell it would have gone to (`why` `arc_strip:<reason>`) carrying the measurements the guards read. Returns a summary."""
    import dataclasses
    import time
    from . import arcs_system as AS
    from . import record as R
    from .record import ABSTAIN, Q, READERS
    from .gather import frame_cell
    from . import one_ink as _one_ink
    from ..measure_extractor import _build_measure_cell
    from ..yolo_detector import TARGET_STAFF_SPACE_PX

    if not enabled():
        return {}
    summary: Dict[str, Any] = {"staff_rows_run": 0, "cut_boxes": 0, "strip_arc_boxes": 0, "candidates": 0, "kept": 0, "pieces_filed": 0,
                               "already_boxed": 0, "refused": {}, "seconds_detect": 0.0}
    if detector is None or not _accepts_max_det(detector):
        return summary
    staves = {s.staff_index: s for s in getattr(pws, "staves", None) or ()}
    by_staff: Dict[int, List[Any]] = {}
    for c in cells:
        if local.get(c.staff_index) is not None and getattr(c, "bbox_page_px", None) and getattr(c, "upscale_factor", None):
            by_staff.setdefault(c.staff_index, []).append(c)
    binary = getattr(getattr(pws, "page", None), "binary", None)
    ink = None
    raw = None

    def refuse(cell_sub: Any, frame: str, why: str, **detail: Any) -> None:
        summary["refused"][why] = summary["refused"].get(why, 0) + 1
        log.abstain(cell_sub, Q.GLYPH_BOX, reader=READERS.DETECTOR, frame=frame, reason=ABSTAIN.BELOW_THRESHOLD, why="arc_strip:" + why, **detail)

    for si, row_cells in sorted(by_staff.items()):
        row_cells.sort(key=lambda c: c.measure_index)
        staff = staves.get(si)
        if staff is None:
            continue
        sys_idx, st_idx = local[si]
        page = row_cells[0].page_index
        pos = {c.measure_index: i for i, c in enumerate(row_cells)}
        arcs: List[Dict[str, Any]] = []         # every cell arc box of this staff, page px
        for c in row_cells:
            sub = R.cell(c.page_index, sys_idx, st_idx, c.measure_index)
            sp = AS._space_page(c)
            cb = c.bbox_page_px
            for gi, d in enumerate(detections.get(sub.to_key()) or ()):
                if str(d.smufl_name) not in ARC_CLASSES:
                    continue
                pb = AS._page_box(c, d)
                if pb is None or not sp:
                    continue
                has_l = (c.measure_index - 1) in pos
                has_r = (c.measure_index + 1) in pos
                arcs.append({"cell": c, "gi": gi, "box": pb, "sp": sp, "cls": str(d.smufl_name),
                             "cut_l": has_l and (pb[0] - cb[0]) <= AS.CUT_EDGE_SPACES * sp,
                             "cut_r": has_r and (cb[2] - pb[2]) <= AS.CUT_EDGE_SPACES * sp})
        cuts: List[Dict[str, Any]] = []
        for a in arcs:
            cb = a["cell"].bbox_page_px
            if a["cut_r"]:
                cuts.append({**a, "side": "r", "bar": float(cb[2])})
            if a["cut_l"]:
                cuts.append({**a, "side": "l", "bar": float(cb[0])})
        summary["cut_boxes"] += len(cuts)
        if not cuts:
            continue
        x0 = int(min(c.bbox_page_px[0] for c in row_cells))
        x1 = int(max(c.bbox_page_px[2] for c in row_cells))
        strip = _build_measure_cell(pws, staff, row_cells[0].system_index, x0, x1, 9999)
        if strip is None or getattr(strip, "image", None) is None:
            continue
        ys = list(getattr(strip, "staff_line_ys_canonical", None) or ())
        if len(ys) < 2:
            continue
        space = (ys[-1] - ys[0]) / (len(ys) - 1)
        if space <= 0:
            continue
        # the SAME 16 px per staff space the cells are shown (`imgsz_for_cell` clamps a wide row at 2048, which would shrink the space)
        isz = int(round(float(TARGET_STAFF_SPACE_PX) * max(strip.image.shape[:2]) / space / 32.0)) * 32
        t0 = time.time()
        dets = detector.detect(strip, conf_threshold=conf_threshold, imgsz=isz, max_det=MAX_DET)
        if dets and _one_ink.enabled():
            dets = _one_ink.merge(dets)
        summary["seconds_detect"] += time.time() - t0
        summary["staff_rows_run"] += 1
        sboxes = []
        for d in dets or ():
            if str(d.smufl_name) in ARC_CLASSES and getattr(d, "one_ink_absorbed_by", None) is None:
                pb = AS._page_box(strip, d)
                if pb is not None:
                    sboxes.append((d, pb))
        summary["strip_arc_boxes"] += len(sboxes)
        for d, pb in sboxes:
            matched = [k for k in cuts if continues(k, pb)]
            if not matched:
                continue                                          # continues no cut arc: not this reader's business
            summary["candidates"] += 1
            k0 = matched[0]
            sp_row = float(k0["sp"])
            # which cells does the box reach beyond the cut box's own cell?
            reach: List[Any] = []
            for k in matched:
                step = 1 if k["side"] == "r" else -1
                j = pos[k["cell"].measure_index] + step
                while 0 <= j < len(row_cells):
                    rc = row_cells[j]
                    rb = rc.bbox_page_px
                    inside = (min(pb[2], rb[2]) - rb[0]) if step == 1 else (rb[2] - max(pb[0], rb[0]))
                    if inside < PIECE_MIN_SPACES * sp_row or abs(rc.measure_index - row_cells[j - step].measure_index) != 1:
                        break
                    if rc not in reach:
                        reach.append(rc)
                    j += step
            measure = {"strip_box": [round(float(v), 1) for v in pb], "strip_class": str(d.smufl_name), "strip_score": round(float(d.confidence), 4),
                       "cut_glyphs": [R.glyph(page, sys_idx, st_idx, k["cell"].measure_index, k["gi"]).to_key() for k in matched],
                       "cut_sides": [k["side"] for k in matched],
                       "cells_reached": [rc.measure_index for rc in reach]}
            home = reach[0] if reach else k0["cell"]
            fsub = R.cell(page, sys_idx, st_idx, home.measure_index)
            fframe = frame_cell(home.measure_index)
            if not reach:
                refuse(fsub, fframe, "no_cell_reached", **measure)
                continue
            whole, any_ = whole_arcs_inside(pb, arcs, sp_row)
            measure.update(whole_arcs_inside=whole, arcs_inside=any_)
            if whole > MAX_WHOLE_ARCS_INSIDE:
                refuse(fsub, fframe, "several_arcs_inside", **measure)
                continue
            if binary is not None and getattr(binary, "ndim", 0) == 2:
                if ink is None:
                    ink = AS.composite_ink(binary, [c for c in cells if local.get(c.staff_index) is not None])
                    raw = binary < 128
                tr = AS.trace_arc(ink, pb, sp_row, x_min=pb[0], x_max=pb[2], raw=raw)
                cov = float((tr or {}).get("coverage") or 0.0)
                nt = turns((tr or {}).get("points") or {}, sp_row) if tr else -1
                measure.update(stroke_coverage=round(cov, 3), stroke_turns=nt)
                if tr is None or cov < AS.MIN_COVER or nt > MAX_TURNS:
                    refuse(fsub, fframe, "not_one_stroke", **measure)
                    continue
            summary["kept"] += 1
            for rc in reach:
                rb = rc.bbox_page_px
                up = float(rc.upscale_factor)
                cx0, cx1 = max(pb[0], float(rb[0])), min(pb[2], float(rb[2]))
                cy0, cy1 = max(pb[1], float(rb[1])), min(pb[3], float(rb[3]))
                rsub = R.cell(page, sys_idx, st_idx, rc.measure_index)
                rframe = frame_cell(rc.measure_index)
                if cx1 - cx0 < PIECE_MIN_SPACES * sp_row or cy1 <= cy0:
                    continue
                clip = (cx0, cy0, cx1, cy1)
                lst = detections.get(rsub.to_key())
                if lst is None:
                    lst = []
                    detections[rsub.to_key()] = lst
                boxed = False
                for ld in lst:
                    if str(ld.smufl_name) in ARC_CLASSES:
                        lb = AS._page_box(rc, ld)
                        if lb is not None and _y_overlap(lb, clip) >= Y_OVERLAP_MIN and (
                                min(lb[2], clip[2]) - max(lb[0], clip[0])) >= 0.5 * (clip[2] - clip[0]):
                            boxed = True
                            break
                if boxed:
                    summary["already_boxed"] += 1
                    continue
                nd = dataclasses.replace(
                    d, cell=rc, x_canonical=int(round((cx0 - rb[0]) * up)), y_canonical=int(round((cy0 - rb[1]) * up)),
                    width_canonical=max(1, int(round((cx1 - cx0) * up))), height_canonical=max(1, int(round((cy1 - cy0) * up))))
                g = R.glyph(page, sys_idx, st_idx, rc.measure_index, len(lst))
                px0, py0, px1, py1 = AS._page_box(rc, nd)
                log.observe(g, Q.GLYPH_BOX, (nd.smufl_name, nd.x_canonical, nd.y_canonical, nd.width_canonical, nd.height_canonical),
                            reader=READERS.DETECTOR, frame=rframe, score=float(nd.confidence), category=nd.category, source="arc_strip",
                            bbox_page_px=[px0, py0, px1, py1], x_center_page=(px0 + px1) / 2.0, y_center_page=(py0 + py1) / 2.0, **measure)
                log.observe(g, Q.GLYPH_CONF, float(nd.confidence), reader=READERS.DETECTOR, frame=rframe, score=float(nd.confidence))
                lst.append(nd)
                summary["pieces_filed"] += 1
        if progress:
            print(f"  gather arc strip staff {si}: {len(sboxes)} strip arc box(es), {summary['kept']} kept so far")
    return summary
