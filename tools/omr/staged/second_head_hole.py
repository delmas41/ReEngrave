"""ROADMAP 2.364 (flag `OMR_SECOND_HEAD_HOLE`, default OFF, allow-list) -- the second head of a hollow third, read by its HOLE.
STAGED GATHER; decides nothing. Every head it files is written GUESSED (blue): ADJUDICATE narrows it {a notehead, not one}
(`notehead_precision`, reason `second_head_hole`) and EXPORT marks it blue with both readings.

CAUSE (ROADMAP 2.364 step 0, DECISIONS 2026-11-26 "2.364 STEP 0 AND THE WIDTH CUT-OFF"): on Litolff two half notes a third apart on one
stem were written as one half. The dyad rescue drew a box on the lost head and its ink test refused it for the SHAPE of the ink -- too
tall where the other head of the chord touches it (directly or through the staff line between them), too wide where the head itself is
1.78-1.84 spaces. Width is the wrong axis for "is this one head" (judged heads and judged non-heads overlap on it), so this reader
does not measure the ink's size at all: it reads what a hollow head IS -- a white hole inside its own ring of ink.

THE RULE (Sean 2026-11-26, approved in his words): the second head of a hollow third is a white hole of head size, a third from the
head already written, on the same stem. The ring round the hole is the head's OWN ink -- never paper boxed in by staff lines and stems;
the stem is a straight stem (a CV stem, never a clef's curl). NEVER a staff line, a ledger line, a dynamic letter, an arc piece or a
clef alone; NEVER a second head on a single or unison stem.

  * The written head is placed by ITS OWN hole (`box_kind.head_holes`, the 2.252 hole reader, staff lines in): of the holes inside
    its box, the one nearest the box's middle. A box with no hole is not read here (no evidence the head is hollow). Sean's v2 tile 6,
    a unison: the record placed the head a third low from a box drawn down its second stem, and the prototype, starting from that
    position, read the head's OWN hole as a second head "a third away"; read from its own hole, nothing stands a third from it.
  * A unison (one head on two stems, one up on its right, one down on its left) has no guard of its own: a two-stem guard was tried
    and dropped -- no judged unison needed it, and it refused real thirds (the right walls of two fused heads read as a short stem).
  * The stem: the written head's stem from the pipeline's own CV stem reader (`line_detection.detect_lines`, staged finder, the
    production call's notehead and mark boxes), at the head's edge, through its height, at least two spaces long.
  * The second hole stands in the SAME COLUMN as the written head's hole (centres within `COLUMN_SP` across: heads of one stem are
    one column; a second is displaced a head's width) and ONE SPACE from it (`THIRD_SP`: a second is half a space; a piece of the
    written head's own hatched slit stands ~0.7 across and ~0.7 along). Measured between the two holes, not on a staff grid, so a
    far head between Litolff's unevenly spaced ledger lines is still read; its PITCH is not read here.
  * Head-sized (the prototype's floors), the stem beside it over its height, the ring's ink running into the stem with no paper.
  * Own ink, not boxed paper: a hole whose paper fills its own box as tall as a staff space is the space between two lines closed
    by two strokes (Sean's first-sheet tile 19, "a box around a space in the staff") -- a head's slit or oval never fills its box.
  * Not already a head: a hole another head box of the cell already stands on gets no second box (that head's fate is ADJUDICATE's).

The box filed is the ring's own ink (`ring_box`), its height read on the side AWAY from the written head and stood symmetric about
its own hole (never past half-way to the written head's hole), so it never takes the written head's ink and its centre is its hole's. Position, value and owner are not read here: the box is appended to `detections` and `gather_notehead_positions`
places it like any head (page-facts: a far head is placed by its ledger lines only); its value is shared from its stem downstream.

CONVENTION ASSUMED: a hollow head's hole is at its centre; heads of one chord share a stem, a third apart (2.252). WHAT WOULD FALSIFY
IT: Sean's tiles on newly written heads showing paper between stems and lines, a clef's curl, or a unison read as a third. NOT
CONFIRMED beyond the judged Litolff/Brahms tiles. Known misses (left as misses): hatched holes broken into slits off the grid, a hole
opened by a slur, a fifth, a written head sitting between two holes.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

ENV = "OMR_SECOND_HEAD_HOLE"
SOURCE = "second_head_hole"
REASON = "second_head_hole"

# ---- the prototype's numbers (/private/tmp/claude-501/second-head-hole/proto.py v2), controls not decisions ----
#: the written head's stem is looked for this far either side of its box's left / right edge (sp)
STEM_SIDE_SP = 0.45
#: a stem runs at least this long (sp) through the written head's height
STEM_MIN_SP = 2.0
#: the hole reader's window reaches this far across either side of the written hole (sp; the whole ring must be inside it)
HEAD_COL_SP = 1.7
#: head-sized: the hole at least this wide (sp) ...
HOLE_MIN_W_SP = 0.35
#: ... and this much paper (sp^2)
HOLE_MIN_AREA_SP2 = 0.06
#: the stem stands beside the hole over this share of the hole's height
STEM_COVER = 0.8
#: the ring's ink is read outward from the hole at most this far (sp)
RING_MAX_SP = 0.5
#: the hole reader's window round the written head's box (sp): its ring must be enclosed in it; the hole's CENTRE must be inside the box
OWN_REACH_SP = 0.25
#: ... and the written head's hole's centre this far past its box at most (sp): none -- a hole outside the head's box is not its hole
OWN_CENTRE_SLACK_SP = 0.0
#: heads of one stem stand in one column: the second hole's centre within this of the written hole's, across (sp). Both sides
#: measured on judged marks: real second heads to 0.74, judged inventions from 1.10 (`tests/data/second_head_hole`)
COLUMN_SP = 0.8
#: a third: the two holes one staff space apart, within these bounds (sp; a second is half a space, and the far lines' own spacing
#: varies -- Litolff's ledger lines stand up to 1.3 spaces apart, lost-chord tile 16)
THIRD_SP = (0.75, 1.45)
#: a staff space boxed in by lines and strokes: paper filling its own box this fully ...
BOXED_FILL = 0.8
#: ... and as tall as a space between two lines (sp)
BOXED_MIN_H_SP = 0.5


def enabled() -> bool:
    """`OMR_SECOND_HEAD_HOLE` (ROADMAP 2.364), default OFF; "1"/"true"/"yes"/"on" turns it on."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def is_second_head(detail: Optional[Dict[str, Any]]) -> bool:
    """A `Q.GLYPH_BOX` detail of a head this reader filed."""
    return bool(detail) and detail.get("source") == SOURCE


def inv_step(ll: Sequence[float], y: float) -> float:
    """Staff step of page y against the LOCAL lines `ll` (0 = top line, +1 per half space down); ledger steps extrapolate."""
    sp = (ll[-1] - ll[0]) / 4.0
    if y < ll[0]:
        return (y - ll[0]) / (sp / 2.0)
    if y > ll[-1]:
        return 8 + (y - ll[-1]) / (sp / 2.0)
    for i in range(4):
        if ll[i] <= y <= ll[i + 1]:
            return 2 * i + 2 * (y - ll[i]) / (ll[i + 1] - ll[i])
    return 8.0


def _hole_mask(ink: Any, h: Dict[str, Any], sp: float, region: Sequence[float]):
    """The paper pixels of hole `h` (its pieces: `head_holes`' own filter, centre in `region`, inside its y0..y1 span), as
    `(x0, y0, x1, y1, mask)`; None when lost."""
    import numpy as np
    from scipy import ndimage as ndi
    from . import box_kind as K
    x0, y0, x1, y1 = region
    m = 0.3 * sp
    rx0, ry0 = max(0, int(x0 - m)), max(0, int(y0 - m))
    rx1, ry1 = min(ink.shape[1], int(x1 + m)), min(ink.shape[0], int(y1 + m))
    reg = ink[ry0:ry1, rx0:rx1]
    holes = ndi.binary_fill_holes(reg) & ~reg
    lab, _n = ndi.label(holes)
    keep = np.zeros_like(holes)
    hy0, hy1 = h["cy"] - h["span_sp"] * sp, h["cy"] + h["span_sp"] * sp
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        if sl is None:
            continue
        hh, ww = (sl[0].stop - sl[0].start) / sp, (sl[1].stop - sl[1].start) / sp
        area = float((lab[sl] == i).sum()) / (sp * sp)
        if ww > K.HOLE_W_MAX_SP or hh > K.HOLE_H_MAX_SP or not (K.HOLE_AREA_SP2[0] <= area <= K.HOLE_AREA_SP2[1]):
            continue
        yy, xx = np.nonzero(lab[sl] == i)
        cx, cy = rx0 + sl[1].start + xx.mean() + 0.5, ry0 + sl[0].start + yy.mean() + 0.5
        if not (x0 <= cx <= x1 and y0 <= cy <= y1):
            continue
        if hy0 - 0.5 <= ry0 + sl[0].start and ry0 + sl[0].stop <= hy1 + 0.5:
            keep |= (lab == i)
    ys, xs = np.nonzero(keep)
    if not len(ys):
        return None
    a0, a1, b0, b1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    return (rx0 + a0, ry0 + b0, rx0 + a1, ry0 + b1, keep[b0:b1, a0:a1])


def ring_box(ink: Any, hm: Tuple[Any, ...], sp: float) -> List[int]:
    """The ring's own ink round a hole: from the hole outward along each row / column through it, the ink run (at most `RING_MAX_SP`).
    `[x0, y0, x1, y1]` (exclusive ends)."""
    import numpy as np
    hx0, hy0, _hx1, _hy1, mask = hm
    H, W = ink.shape
    cap = int(round(RING_MAX_SP * sp))
    L, Rr, T, B = [], [], [], []
    ys, xs = np.nonzero(mask)
    for yy in sorted(set(ys.tolist())):
        row = xs[ys == yy]
        a, b, Y = int(row.min()) + hx0, int(row.max()) + hx0, yy + hy0
        n = 0
        while n < cap and a - 1 - n >= 0 and ink[Y, a - 1 - n]:
            n += 1
        L.append(a - n)
        n = 0
        while n < cap and b + 1 + n < W and ink[Y, b + 1 + n]:
            n += 1
        Rr.append(b + 1 + n)
    for xx in sorted(set(xs.tolist())):
        col = ys[xs == xx]
        a, b, X = int(col.min()) + hy0, int(col.max()) + hy0, xx + hx0
        n = 0
        while n < cap and a - 1 - n >= 0 and ink[a - 1 - n, X]:
            n += 1
        T.append(a - n)
        n = 0
        while n < cap and b + 1 + n < H and ink[b + 1 + n, X]:
            n += 1
        B.append(b + 1 + n)
    return [int(min(L)), int(min(T)), int(max(Rr)), int(max(B))]


def find_stem(head: Sequence[float], stems: Sequence[Sequence[float]], sp: float, yc: float) -> Tuple[Optional[int], List[int]]:
    """The written head's stem among `stems` ([x0, y0, x1, y1], same frame): a stem at the head's left or right edge (within
    `STEM_SIDE_SP`), running through the head's height (within half a space of its centre), at least `STEM_MIN_SP` long. Returns
    (index of the longest, [every such index])."""
    x0, _y0, x1, _y1 = head
    found = []
    for i, s in enumerate(stems):
        sx = (s[0] + s[2]) / 2.0
        near = min(abs(sx - x0), abs(sx - x1)) <= STEM_SIDE_SP * sp
        through = s[1] <= yc + 0.5 * sp and s[3] >= yc - 0.5 * sp
        if near and through and (s[3] - s[1]) >= STEM_MIN_SP * sp:
            found.append(i)
    if not found:
        return None, []
    return max(found, key=lambda i: stems[i][3] - stems[i][1]), found


def second_heads(ink: Any, lines: Sequence[float], heads: Sequence[Sequence[float]], stems: Sequence[Sequence[float]],
                 seen: Sequence[Sequence[float]] = ()) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """PURE. `ink`: boolean ink mask, staff lines IN (page raster, 0 = ink -> True). `lines`: the bar's five staff lines (same frame).
    `heads`: the written head boxes [x0, y0, x1, y1] to read from. `stems`: CV stem boxes. `seen`: every head box already filed (a hole
    one stands on is not added). Returns `(kept, refused)`: kept `{"partner", "box", "hole", "step", "written_step", "stem", "d"}`;
    refused `{"partner", "why", ...}` (a refusal says what it was)."""
    import numpy as np
    from . import box_kind as K
    from . import clef_pagewide as CP
    ink = np.asarray(ink, dtype=bool)
    kept: List[Dict[str, Any]] = []
    refused: List[Dict[str, Any]] = []
    if ink.ndim != 2 or len(lines) != 5:
        return kept, refused
    sp0 = (lines[-1] - lines[0]) / 4.0
    if sp0 <= 0:
        return kept, refused
    for hi, hb in enumerate(heads):
        x0, y0, x1, y1 = (float(v) for v in hb)
        ll = CP.local_lines(ink, lines, sp0, (x0 + x1) / 2.0)
        sp = (ll[-1] - ll[0]) / 4.0
        # the written head's hole stands INSIDE its box: a hole a little past the box is paper beside the head (a FILLED head's box with a
        # staff space just under it read as a hollow head's slit on the first page run, Litolff p8 8/1/0/15/8, p10 10/1/8/10/0 -- OUR look)
        inbox = [h for h in K.head_holes(ink, (x0, y0 - OWN_REACH_SP * sp, x1, y1 + OWN_REACH_SP * sp), sp, ll[0], ll)
                 if y0 - OWN_CENTRE_SLACK_SP * sp <= h["cy"] <= y1 + OWN_CENTRE_SLACK_SP * sp]
        if not inbox:
            refused.append({"partner": hi, "why": "written_head_has_no_hole"})
            continue
        # the written head is at the hole its box stands on most centrally; a box drawn over both heads of a third holds the other's
        # hole too, and that one is read below like any other hole a third away
        bcy = (y0 + y1) / 2.0
        own = [min(inbox, key=lambda h: abs(h["cy"] - bcy))]
        oc = own[0]
        yc = float(oc["cy"])
        si, all_st = find_stem((x0, y0, x1, y1), stems, sp, yc)
        if si is None:
            refused.append({"partner": hi, "why": "no_stem"})
            continue
        st = stems[si]
        side = "R" if (st[0] + st[2]) / 2.0 > (x0 + x1) / 2.0 else "L"
        sx0, sx1 = int(round(st[0])), max(int(round(st[0])) + 1, int(round(st[2])))
        # the hole reader needs the whole ring inside its window (a hole is paper the ink encloses); the column is checked on the centre
        reach = (THIRD_SP[1] + 0.6) * sp
        region = (oc["cx"] - HEAD_COL_SP * sp, yc - reach, oc["cx"] + HEAD_COL_SP * sp, yc + reach)
        for h in K.head_holes(ink, region, sp, ll[0], ll):
            dy, dx = (h["cy"] - yc) / sp, (h["cx"] - oc["cx"]) / sp
            if not (THIRD_SP[0] <= abs(dy) <= THIRD_SP[1]) or abs(dx) > COLUMN_SP:
                continue
            rec: Dict[str, Any] = {"partner": hi, "d": 1 if dy > 0 else -1, "dy_sp": round(dy, 3), "dx_sp": round(dx, 3),
                                   "step": round(inv_step(ll, h["cy"]), 2), "written_hole_step": round(inv_step(ll, yc), 2),
                                   "hole_c": [h["cx"], h["cy"]]}
            hm = _hole_mask(ink, h, sp, region)
            if hm is None:
                refused.append(dict(rec, why="hole_lost"))
                continue
            hx0, hy0, hx1, hy1, mk = hm
            wsp, hsp, asp = (hx1 - hx0) / sp, (hy1 - hy0) / sp, float(mk.sum()) / (sp * sp)
            fill = float(mk.sum()) / float(max(1, (hx1 - hx0) * (hy1 - hy0)))
            rec.update(hole=[int(hx0), int(hy0), int(hx1), int(hy1)], hole_w_sp=round(wsp, 3), hole_h_sp=round(hsp, 3),
                       hole_area_sp2=round(asp, 3), hole_fill=round(fill, 3))
            if wsp < HOLE_MIN_W_SP or asp < HOLE_MIN_AREA_SP2:
                refused.append(dict(rec, why="hole_not_head_sized"))
                continue
            if fill >= BOXED_FILL and hsp >= BOXED_MIN_H_SP:
                # paper filling the box between two straight lines and two straight strokes: a staff space, not a head's slit or oval
                refused.append(dict(rec, why="a_staff_space_boxed_in"))
                continue
            ys = range(int(hy0), int(hy1))
            cover = float(np.mean([ink[y, sx0:sx1].any() for y in ys])) if len(ys) else 0.0
            rec["stem_cover"] = round(cover, 2)
            if cover < STEM_COVER:
                refused.append(dict(rec, why="stem_not_beside_hole"))
                continue
            touch = 0
            yy, xx = np.nonzero(mk)
            for y in sorted(set(yy.tolist())):
                Y, row = y + hy0, xx[yy == y] + hx0
                seg = ink[Y, int(row.max()) + 1:sx0] if side == "R" else ink[Y, sx1:int(row.min())]
                if (seg.size == 0 or seg.all()) and ink[Y, sx0:sx1].any():
                    touch += 1
            rec["touch_rows"] = touch
            if touch < 1:
                refused.append(dict(rec, why="ring_does_not_reach_the_stem"))
                continue
            hcx, hcy = h["cx"], h["cy"]
            if any(sb[0] <= hcx <= sb[2] and sb[1] <= hcy <= sb[3] for sb in seen if list(sb) != list(hb)):
                refused.append(dict(rec, why="a_head_box_stands_on_it"))
                continue
            box = ring_box(ink, hm, sp)
            # the near side runs on into the written head's ink, so the head's height is read on its FAR side and the box stands
            # symmetric about its own hole: the position reader then reads the hole's step (the first page run cut the near side at the
            # midline and the box's centre stood up to a step off its hole, Litolff p10 10/1/2/4/6 -- OUR look)
            mid = (yc + hcy) / 2.0
            if dy < 0:
                half = max(hcy - box[1], 1.0)
                box[3] = int(round(min(hcy + half, max(mid, hcy + 1.0))))
                box[1] = int(round(hcy - half))
            else:
                half = max(box[3] - hcy, 1.0)
                box[1] = int(round(max(hcy - half, min(mid, hcy - 1.0))))
                box[3] = int(round(hcy + half))
            kept.append(dict(rec, box=box, stem=si, side=side))
    return kept, refused
