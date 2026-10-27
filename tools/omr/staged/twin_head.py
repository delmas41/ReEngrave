"""ONE PRINTED HEAD, ONE MEASUREMENT -- ROADMAP 2.212 (STAGED GATHER; flag `OMR_TWIN_HEAD_MERGE`, default OFF).

CAUSE (benchmarks/twin-heads-2026-10/FINDINGS.md): the detector often boxes one printed head twice (`noteheadBlack*` +
`noteheadHalf*`, or a head and a head-plus-stem). `gather_notehead_positions` reads a notehead's staff position off its OWN
box's centre, so two boxes on one head give two positions (half a staff space apart in a third of Litolff twin pairs) and
ADJUDICATE's keeper choice (`notehead_precision._stacked_head_duplicate_refusal`, the 2.30 same-mark rule) then chooses
the WRITTEN PITCH: anything that nudges one box's ink (the eraser) flips the keeper and the pitch.

CONVENTION: a notehead is one oval; its pitch is where its INK stands against the staff, not where a detector box happens
to be drawn. Two boxes whose centres are within half a staff space vertically and half a head width horizontally are one
head boxed twice (a second is on the other side of the stem, a third a whole space away: neither can be that close).
WHAT WOULD FALSIFY IT: a hand-labelled pair of distinct heads a half-space apart on one side of a stem (a unison written
as two heads) -- Sean's crops of the pairs this merges are the control. NOT CONFIRMED: the two cut-offs (0.5 sp, 0.5 hw)
are the existing `NOTEHEAD_DUPLICATE_MAX_DX_HEAD_WIDTHS` and the gap in the twin pairs' dy histogram (two plates).

PURE: boxes / a page raster in, numbers out; no log, no quantity named. `gather.gather_notehead_positions` is its stage
(it files the shared position and the `twin_head` detail), `gather.gather_notehead_ink` reads the same detail and reads the
head's fill ONCE, in a standard head box at the shared centre -- so both boxes agree on the class and no keeper choice can
change what is written. The ink centre is `gather.recentre_part_boxed`'s own estimator (stem columns and staff-line rows
left out, a centroid that must settle at four windows), restated for a group rather than called, so 2.115 is untouched.
"""
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

ENV = "OMR_TWIN_HEAD_MERGE"


def enabled() -> bool:
    """`OMR_TWIN_HEAD_MERGE` -- ROADMAP 2.212. **Default OFF**; `1/true/yes/on` turns it on."""
    return os.environ.get(ENV, "0").strip().lower() in ("1", "true", "yes", "on")


#: Two boxes are one head where their centres are strictly closer than this vertically (staff spaces) ...
TWIN_MAX_DY_SPACES = 0.5
#: ... and than this fraction of the mean box width horizontally (`NOTEHEAD_DUPLICATE_MAX_DX_HEAD_WIDTHS`, restated: the
#: adjudicator imports `gather`, so the reverse import would be a cycle).
TWIN_MAX_DX_HEAD_WIDTHS = 0.5
#: A whole group's centres span less than this vertically (staff spaces): a chain of pairs is not one head.
TWIN_MAX_SPREAD_SPACES = 0.6
#: The measured centre must lie within this of the group's mean centre (staff spaces); farther is another mark's ink.
TWIN_MAX_SHIFT_SPACES = 0.6
#: A HOLE of a hollow head: an enclosed white region this big (staff spaces squared; a head's hole is ~0.1-0.3, a line-cut
#: head shows two halves of ~0.1-0.17 each, `gather.HEAD_CUT_HOLE_AREA_SPACES2` is the sibling band) ...
TWIN_HOLE_AREA_SPACES2 = (0.04, 0.45)
#: ... read in the group's union box widened by this (staff spaces) either side.
TWIN_HOLE_PAD_SPACES = (0.3, 0.4)


def twin_groups(boxes: Sequence[Tuple[float, float, float, float]], spacing: float) -> List[List[int]]:
    """Index groups (size >= 2) of `boxes` ((x, y, w, h), one frame, `spacing` in the same unit) that are one head boxed
    more than once. Connected pairs under the two cut-offs; a group whose centres span `TWIN_MAX_SPREAD_SPACES` or more
    is dropped whole (nothing is merged that is not clearly one head)."""
    n = len(boxes)
    if n < 2 or not spacing or spacing <= 0:
        return []
    cx = [b[0] + b[2] / 2.0 for b in boxes]
    cy = [b[1] + b[3] / 2.0 for b in boxes]
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            head_w = (boxes[i][2] + boxes[j][2]) / 2.0
            if head_w <= 0:
                continue
            if abs(cy[i] - cy[j]) < TWIN_MAX_DY_SPACES * spacing \
                    and abs(cx[i] - cx[j]) < TWIN_MAX_DX_HEAD_WIDTHS * head_w:
                parent[find(i)] = find(j)
    comps: Dict[int, List[int]] = {}
    for i in range(n):
        comps.setdefault(find(i), []).append(i)
    out = []
    for members in comps.values():
        if len(members) < 2:
            continue
        ys = [cy[i] for i in members]
        if (max(ys) - min(ys)) >= TWIN_MAX_SPREAD_SPACES * spacing:
            continue
        out.append(sorted(members))
    return sorted(out)


def head_ink_centre(raw: Any, cx: float, cy: float, spacing: float) -> Optional[Dict[str, Any]]:
    """Where one head's ink stands vertically. `raw` is a raster (0 == ink, staff lines IN), `(cx, cy)` a point on or near
    the head and `spacing` the staff space, all in the raster's frame. Returns `{"cy", "shift_sp", "spread_sp",
    "ink_spaces2", "reason"}`; `reason` is `None` where the estimate settled at all four windows and agrees to
    `RECENTRE_PART_MAX_SPREAD_SPACES`, else why not (`no_ink`, `not_converged`, `unstable`, `off_raster`). The estimator is
    `gather.recentre_part_boxed`'s: stem columns (vertical ink runs longer than `RECENTRE_PART_STEM_RUN_SPACES`) and
    staff/ledger LINE rows (ink past the head on both sides) are left out, then the centroid of what remains inside a
    window of half-size `h` is iterated to its fixed point."""
    import numpy as np
    from . import gather as G
    if raw is None or getattr(raw, "ndim", 0) != 2 or not spacing or spacing <= 0:
        return {"reason": "off_raster"}
    ink = (np.asarray(raw) == 0)
    H, W = ink.shape
    rad = int(3.2 * spacing)
    X0, X1 = max(0, int(cx - rad)), min(W, int(cx + rad))
    Y0, Y1 = max(0, int(cy - rad)), min(H, int(cy + rad))
    if X1 <= X0 or Y1 <= Y0:
        return {"reason": "off_raster"}
    sub = ink[Y0:Y1, X0:X1]
    stem = np.zeros(sub.shape, dtype=bool)
    cut = G.RECENTRE_PART_STEM_RUN_SPACES * spacing
    for xi in range(sub.shape[1]):
        col = sub[:, xi]
        if not col.any():
            continue
        d = np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))
        for s0, e0 in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            if e0 - s0 > cut:
                stem[s0:e0, xi] = True
    lo_l = int(round(cx - G.HEAD_LINE_ROW_BAND_SPACES[1] * spacing)) - X0
    hi_l = int(round(cx - G.HEAD_LINE_ROW_BAND_SPACES[0] * spacing)) - X0
    lo_r = int(round(cx + G.HEAD_LINE_ROW_BAND_SPACES[0] * spacing)) - X0
    hi_r = int(round(cx + G.HEAD_LINE_ROW_BAND_SPACES[1] * spacing)) - X0
    left = sub[:, max(0, lo_l):max(0, hi_l)]
    right = sub[:, max(0, lo_r):max(0, hi_r)]
    if left.shape[1] and right.shape[1]:
        line_rows = (left.mean(axis=1) >= G.HEAD_LINE_ROW_FILL) & (right.mean(axis=1) >= G.HEAD_LINE_ROW_FILL)
    else:
        line_rows = np.zeros(sub.shape[0], dtype=bool)
    ys, xs = np.mgrid[0:sub.shape[0], 0:sub.shape[1]]

    def settle(half_sp: float):
        half = half_sp * spacing
        keep = sub & ~stem & ~line_rows[:, None] & (np.abs(xs + X0 - cx) <= half)
        ey, n = cy, 0
        for _ in range(G.RECENTRE_PART_ITERATIONS):
            pts = keep & (np.abs(ys + Y0 - ey) <= half)
            n = int(pts.sum())
            if n < G.RECENTRE_PART_MIN_INK_SPACES2 * spacing * spacing:
                return None, n / (spacing * spacing), "no_ink"
            ny = float(ys[pts].mean() + Y0)
            step = abs(ny - ey) / spacing
            ey = ny
            if step < G.RECENTRE_PART_CONVERGED_SPACES:
                return ey, n / (spacing * spacing), None
        return None, n / (spacing * spacing), "not_converged"

    results = [settle(hw) for hw in G.RECENTRE_PART_WINDOWS]
    main = results[G.RECENTRE_PART_WINDOWS.index(G.RECENTRE_PART_HALF_WINDOW_SPACES)]
    if main[2] is not None:
        return {"reason": main[2], "ink_spaces2": round(main[1], 3)}
    centres = [r[0] for r in results if r[0] is not None]
    spread = ((max(centres) - min(centres)) / spacing) if len(centres) == len(results) else float("inf")
    out = {"cy": main[0], "shift_sp": round((main[0] - cy) / spacing, 3), "ink_spaces2": round(main[1], 3),
           "spread_sp": round(spread, 3) if spread != float("inf") else None, "reason": None}
    if spread > G.RECENTRE_PART_MAX_SPREAD_SPACES:
        out["reason"] = "unstable"
    return out


def group_centre(raw: Any, boxes: Sequence[Tuple[float, float, float, float]], spacing: float) -> Dict[str, Any]:
    """ONE vertical centre for the head these `boxes` (one group of `twin_groups`) all draw, in the raster's frame.

    HOLLOW head: the area-weighted centre of the enclosed white regions inside the group's union box (a line through the
    head splits its hole in two; both halves count) -- the hole is the head's own centre however the detector drew the
    box, and a stray black cap or slur above the ring cannot pull it (`head_ink_centre`'s centroid IS pulled by one; the
    two Litolff heads Sean read, FINDINGS 3). FILLED head (no hole of that size): `head_ink_centre`'s centroid. Neither:
    `{"reason": ...}` and the caller leaves every member's own position as it is (cannot tell, rule 8).
    Returns `{"cy", "cx", "by": "hole"|"ink", "holes", "reason": None}` or `{"reason": ...}`."""
    import numpy as np
    from . import gather as G
    if raw is None or getattr(raw, "ndim", 0) != 2 or not spacing or spacing <= 0 or not boxes:
        return {"reason": "off_raster"}
    mean_cx = sum(b[0] + b[2] / 2.0 for b in boxes) / len(boxes)
    mean_cy = sum(b[1] + b[3] / 2.0 for b in boxes) / len(boxes)
    ink = (np.asarray(raw) == 0)
    x0 = min(b[0] for b in boxes) - TWIN_HOLE_PAD_SPACES[0] * spacing
    x1 = max(b[0] + b[2] for b in boxes) + TWIN_HOLE_PAD_SPACES[0] * spacing
    y0 = min(b[1] for b in boxes) - TWIN_HOLE_PAD_SPACES[1] * spacing
    y1 = max(b[1] + b[3] for b in boxes) + TWIN_HOLE_PAD_SPACES[1] * spacing
    holes = [h for h in G._enclosed_holes(ink, x0, y0, x1, y1)
             if TWIN_HOLE_AREA_SPACES2[0] <= h["area"] / (spacing * spacing) <= TWIN_HOLE_AREA_SPACES2[1]
             and abs(h["cy"] - mean_cy) <= TWIN_MAX_SHIFT_SPACES * spacing
             and abs(h["cx"] - mean_cx) <= TWIN_MAX_SHIFT_SPACES * 2.0 * spacing]
    if holes:
        tot = sum(h["area"] for h in holes)
        return {"cy": sum(h["cy"] * h["area"] for h in holes) / tot, "cx": sum(h["cx"] * h["area"] for h in holes) / tot,
                "by": "hole", "holes": len(holes), "reason": None}
    r = head_ink_centre(raw, mean_cx, mean_cy, spacing)
    if r is None or r.get("reason"):
        return {"reason": (r or {}).get("reason") or "no_reading"}
    if abs(r["cy"] - mean_cy) > TWIN_MAX_SHIFT_SPACES * spacing:
        return {"reason": "too_far"}
    return {"cy": r["cy"], "cx": mean_cx, "by": "ink", "holes": 0, "reason": None, "spread_sp": r.get("spread_sp")}
