"""ROADMAP 2.204 -- the shared ink map, STEP 4: a head's STEM from the stroke map (flag `OMR_STEMS_FROM_STROKES`, requires `OMR_STROKE_MAP`).

STAGED ADJUDICATE, PURE: this module imports nothing from the pipeline except the pure `beam_strokes` (the stroke view and the one
"longest stem" cut 2.202 measured). `adjudicators/rhythm.py::_stem_reading` is the only caller: it builds `StemView`s from `Q.STROKE` rows
and hands them here together with the head's detector box. Nothing in this file decides a duration or a direction: it says which vertical
stroke(s), if any, are THIS head's stem, with the stroke's own length, tip and the tip's place against the staff measured at the stroke's
own x (the map filed it: `end_steps_from_top`), and, where it cannot tell, why (CLAUDE §3: the answer follows -> decided; it does not ->
the caller abstains with the candidates).

THE RULE (page-facts / CLAUDE §5: stems up -> right, down -> left; every note on one stem shares one value; a whole note has no stem) --

  a head's stem is the vertical stroke its blob touches on the ENGRAVING SIDE: an up-stem stands flush with the head's RIGHT edge and
  rises from it, a down-stem flush with its LEFT edge and hangs from it. A stroke that touches the head on the other side, or runs
  through its middle, is not this head's stem and is never invented into one (rule 6): it is `wrong_side` / `through_head`, a CANDIDATE
  the caller may show, nothing more. A whole note has no stem: `whole_head` reads no stem at all, whatever stands beside it.

THE OLD RULES, RE-EXPRESSED ON STROKES (each had a reader of its own on the raster; the map already separates the strokes) --

  2.161 bridge  the head's ink runs into a stem standing a hair beside its detector box (box stops short of the head's stem side). On
                strokes: a vertical stroke whose near edge is `<= BRIDGE_MAX_GAP_SPACES` from the box side, on the engraving side, with
                no other head between (`bridged`). It is returned apart from `stem`: 2.161 lets it speak at the first step only.
  2.169 pair    two stems at one head, one each side, each ENDING in the head, are two notes (`two_stems`: unison, two voices).
                Two strokes on the SAME side that are one stem cut by a crossing (a beam, a ledger rung) are ONE stem (`merge_collinear`).
  2.155 edge    a vertical stroke at the cell's edge is a barline, not a stem -- unless one of its ENDS stands in a head box, then it is
                that head's stem. A stroke longer than any stem (`beam_strokes.STEM_MAX_SPACES`, measured 2.202) is a barline always.

THE CUTS. `BRIDGE_MAX_GAP_SPACES` 0.35 is the 2.161 gap (0.13-0.27 sp on ONE plate) plus 0.08: it may only NARROW until another
publisher confirms it (CLAUDE §4), which is why `bridged` is its own state. `END_IN_HEAD_SLACK_SPACES` 0.3 is the head box's own slop
(detector boxes are loose by about a quarter space). `COLLINEAR_X_SPACES` 0.3 / `BREAK_MAX_GAP_SPACES` 0.6 join the two halves of a stem
a beam or ledger rung cut; a join also needs both halves to be vertical strokes of ONE x-column. `FLUSH_SPACES` 0.45 puts a
stem's outer edge within that of the head box's side edge; deeper inside it runs THROUGH the head. None of them was tuned to a count.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .beam_strokes import STEM_MAX_SPACES, StrokeView

BRIDGE_MAX_GAP_SPACES = 0.35
END_IN_HEAD_SLACK_SPACES = 0.3
COLLINEAR_X_SPACES = 0.3
BREAK_MAX_GAP_SPACES = 0.6
#: A "vertical" stroke wider than this has head ink fused to it; its stem stands at the tip end (median error 0.09 sp against the finder's
#: stem on the 446 fused strokes, against 0.41 for the box centre).
FUSED_MIN_WIDTH_SPACES = 0.6
#: A stem's outer edge stands at most this far INSIDE the detector box's side edge (boxes are loose by a quarter space on one side).
#: Measured 2.204, Litolff, the finder's own stems: 0 to 0.32 sp inside; the interior strokes it must refuse: 0.51-0.58 sp in.
FLUSH_SPACES = 0.45
#: A stroke must share at least this share of the head box's height to be beside the head at all.
MIN_VERTICAL_OVERLAP_SHARE = 0.4
#: A vertical stroke whose edge is within this of the cell's edge is "at the bar's edge" (2.155).
CELL_EDGE_SPACES = 0.3


@dataclass(frozen=True)
class StemView(StrokeView):
    """A `StrokeView` plus where its ENDS stand against the staff (steps from the top line, 0..8 -- measured by the map at the stroke's own
    x). `end_steps` is `(top end, bottom end)` or None."""
    end_steps: Optional[Tuple[float, float]] = None
    #: the two extreme pixels along the axis, flat `(x0, y0, x1, y1)` canonical px (the row's `ends`). A "vertical" stroke on Litolff keeps the
    #: head ink fused to the stem (measured 2.204: boxes 1.2 sp wide), so its BOX is not the stem; the stem stands at the end far from the head.
    ends: Optional[Tuple[float, float, float, float]] = None


@dataclass(frozen=True)
class StemCand:
    """One vertical stroke (or the merge of collinear halves) considered as this head's stem, with why it was or was not accepted."""
    ordinals: Tuple[int, ...]
    row_ids: Tuple[str, ...]
    box: Tuple[float, float, float, float]       # x, y, w, h -- the stem as one box (merged halves)
    side: str                                    # "right" | "left" | "through"   (the head side it stands on)
    direction: Optional[str]                     # "up" | "down" | None (unread)
    tip_end: Optional[str]                       # "top" | "bottom"
    tip_y: Optional[float]
    tip_step: Optional[float]                    # tip against the staff, steps from the top line, locally measured by the map
    length_sp: float                             # the stroke's own length (merged halves: the union box)
    from_head_sp: Optional[float]                # tip distance from the head's centre
    gap_sp: float                                # horizontal gap to the box side (0: touching)
    ends_in_head: bool
    anchored: bool                               # an end of it stands in SOME head box of the cell (a barline's does not)
    merged: bool = False
    displaced: bool = False                      # a second's displaced head: the stem touches it on the far side, its anchor head sees it right
    why: str = ""                                # "" = accepted; "bridged"; else the reason it is not this head's stem


@dataclass(frozen=True)
class StemReading:
    """`state`: stem | two_stems | bridged | no_stem | whole_head | wrong_side | through_head | barline | unanchored | ambiguous.
    `stems`: the accepted candidate(s) (for `bridged`: the bridged one). `candidates`: everything considered, accepted or not."""
    state: str
    stems: Tuple[StemCand, ...] = ()
    candidates: Tuple[StemCand, ...] = ()
    reason: str = ""
    margins: Dict[str, float] = field(default_factory=dict)

    @property
    def direction(self) -> Optional[str]:
        ds = {s.direction for s in self.stems if s.direction}
        return next(iter(ds)) if len(ds) == 1 else None


def engraving_side_ok(direction: Optional[str], side: str) -> bool:
    """THE SIDE RULE (CLAUDE §5): an up-stem stands on the head's RIGHT, a down-stem on its LEFT."""
    return (direction == "up" and side == "right") or (direction == "down" and side == "left")


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return min(a1, b1) - max(a0, b0)


def axis_x(v: StemView, head_ys: Sequence[float] = ()) -> float:
    """The x of THIS stroke's stem: the x of the end farthest (in y) from every head (the tip, where no head ink is fused), else the box
    centre. Measured 2.204 on Litolff: 'vertical' strokes are up to 1.2 sp wide because head ink is fused to the stem."""
    e = v.ends
    sp = v.space_px if v.space_px > 0 else 1.0
    if not e or len(e) != 4 or v.box[2] <= FUSED_MIN_WIDTH_SPACES * sp:
        return v.box[0] + v.box[2] / 2.0           # a thin stroke: its box IS the stem (box centre: median error 0.03 sp, measured)
    if not head_ys:
        return (e[0] + e[2]) / 2.0
    def near(x: float, y: float) -> float:
        # A head is "near" an end only if it STANDS at that end's x (a head is a tuple `(cy, x0, x1)`); a bare number is a y alone (old spelling).
        # 2.204 (Litolff p4): a head in the cell at the far end's height but a different x made the TIP read as a head end, and the stem was
        # placed at the head end of a tilted stroke -> `wrong_side`.
        ds = [abs(y - h) if not isinstance(h, (tuple, list)) else abs(y - h[0]) for h in head_ys
              if not isinstance(h, (tuple, list)) or h[1] - 0.6 * sp <= x <= h[2] + 0.6 * sp]
        return min(ds) if ds else 1e9
    d0, d1 = near(e[0], e[1]), near(e[2], e[3])
    return float(e[0] if d0 >= d1 else e[2])


def stem_box(v: StemView, cx: float) -> Tuple[float, float, float, float]:
    """The stem alone: the stroke's y-range, `thickness` wide (the median run width the map measured) about `cx`."""
    sp = v.space_px if v.space_px > 0 else 1.0
    w = min(v.box[2], max(v.thickness * sp, 0.12 * sp))
    return (cx - w / 2.0, v.box[1], w, v.box[3])


def merge_collinear(verts: Sequence[StemView], head_ys: Sequence[float] = ()) -> List[Tuple[Tuple[StemView, ...], Tuple[float, float, float, float]]]:
    """Group vertical strokes that are ONE stem cut by a crossing. Two verticals join when their x-centres are within `COLLINEAR_X_SPACES`
    and the vertical gap between them is at most `BREAK_MAX_GAP_SPACES` (or they overlap), or twice that when one horizontal stroke touches
    both (the caller lists it in `touches`). Returns `[(members, union box)]`. Pure; never joins across x-columns."""
    xs = {s.ordinal: axis_x(s, head_ys) for s in verts}
    items = sorted(verts, key=lambda s: (xs[s.ordinal], s.box[1]))
    groups: List[List[StemView]] = []
    for s in items:
        sp = s.space_px if s.space_px > 0 else 1.0
        placed = False
        for g in groups:
            for m in g:
                cx_s, cx_m = xs[s.ordinal], xs[m.ordinal]
                if abs(cx_s - cx_m) > COLLINEAR_X_SPACES * sp:
                    continue
                gap = -_overlap(s.box[1], s.box[1] + s.box[3], m.box[1], m.box[1] + m.box[3])
                shared_h = {j for j, _c in s.touches} & {j for j, _c in m.touches}
                if gap <= BREAK_MAX_GAP_SPACES * sp or (shared_h and gap <= 2.0 * BREAK_MAX_GAP_SPACES * sp):
                    g.append(s)
                    placed = True
                    break
            if placed:
                break
        if not placed:
            groups.append([s])
    out = []
    for g in groups:
        cx = sum(xs[m.ordinal] for m in g) / len(g)
        y0 = min(m.box[1] for m in g)
        y1 = max(m.box[1] + m.box[3] for m in g)
        w = max(stem_box(m, cx)[2] for m in g)
        out.append((tuple(g), (cx - w / 2.0, y0, w, y1 - y0)))
    return out


def _tip_step(members: Sequence[StemView], end: str) -> Optional[float]:
    """The map's own reading of where the stem's tip stands against the staff (steps from the top line at the stroke's own x)."""
    pick = min(members, key=lambda m: m.box[1]) if end == "top" else max(members, key=lambda m: m.box[1] + m.box[3])
    if pick.end_steps is None or len(pick.end_steps) != 2:
        return None
    return float(pick.end_steps[0] if end == "top" else pick.end_steps[1])


def head_stem(views: Sequence[StemView], head_box: Sequence[float], space_px: float, *, whole_head: bool = False,
              other_heads: Sequence[Sequence[float]] = (), cell_width: Optional[float] = None) -> StemReading:
    """Which vertical stroke is THIS head's stem. Pure. `head_box` and the strokes are canonical cell px (x, y, w, h); `space_px` the
    cell's staff space; `other_heads` the cell's other head boxes (they anchor a stem that passes this head, and block a bridge);
    `cell_width` the cell's canonical width for the bar-edge test (None: that test is not made)."""
    hx, hy, hw, hh = (float(v) for v in head_box)
    sp = space_px if space_px and space_px > 0 else 1.0
    if hw <= 0 or hh <= 0:
        return StemReading("no_stem", reason="no_head_box")
    hcy = hy + hh / 2.0
    slack = END_IN_HEAD_SLACK_SPACES * sp
    me = (hx, hy, hw, hh)
    others = [tuple(float(v) for v in b) for b in other_heads if tuple(float(v) for v in b) != me]
    heads = others + [me]

    def in_a_head(y: float, x0: float, x1: float) -> bool:
        return any(b[1] - slack <= y <= b[1] + b[3] + slack and _overlap(x0, x1, b[0] - slack, b[0] + b[2] + slack) > 0 for b in heads)

    verts = [s for s in views if s.kind == "vertical"]
    cands: List[StemCand] = []
    for members, box in merge_collinear(verts, [(b[1] + b[3] / 2.0, b[0], b[0] + b[2]) for b in heads]):
        sx, sy, sw, sh = box
        member_sp = max((m.space_px for m in members if m.space_px > 0), default=sp)
        length = members[0].length if len(members) == 1 else sh / member_sp
        if sx + sw >= hx and sx <= hx + hw:
            gap = 0.0
        elif sx > hx + hw:
            gap = (sx - (hx + hw)) / sp
        else:
            gap = (hx - (sx + sw)) / sp
        # how far INSIDE the box's side edge the stem's outer edge stands (negative: outside it). A stem is flush with its head; a vertical
        # stroke deeper inside the box than FLUSH_SPACES is the head's own ink or a neighbour's, not its stem (2.204: 12 px strokes 0.5 sp in).
        d_left, d_right = (sx - hx) / sp, ((hx + hw) - (sx + sw)) / sp
        if _overlap(sy, sy + sh, hy, hy + hh) < MIN_VERTICAL_OVERLAP_SHARE * hh or gap > BRIDGE_MAX_GAP_SPACES:
            continue                                   # not beside this head at all: not even a candidate
        top_in = hy - slack <= sy <= hy + hh + slack
        bot_in = hy - slack <= sy + sh <= hy + hh + slack
        side = ("left" if d_left <= FLUSH_SPACES and d_left <= d_right else "right" if d_right <= FLUSH_SPACES else "through")
        ends_in = top_in != bot_in
        if ends_in:
            # 2.204 (Litolff 8 pages, `wrong_side`): a chord's stem runs from its far head to the TOP head of the chord; its end stands in this
            # head only because this is the chord's end head, and its other end stands in ANOTHER head -- the stroke passes this head (the end
            # the other head holds tells the way: bottom in a head -> up), it does not hang from it.
            far_y = sy + sh if top_in else sy
            if any(b[1] - slack <= far_y <= b[1] + b[3] + slack and _overlap(sx, sx + sw, b[0] - slack, b[0] + b[2] + slack) > 0 for b in others):
                ends_in = False
        anchored = in_a_head(sy, sx, sx + sw) or in_a_head(sy + sh, sx, sx + sw)
        displaced = False
        anchor_box = None
        if ends_in:
            direction = "up" if bot_in else "down"
        else:
            # the stroke PASSES this head (a chord's middle or displaced head): which way it runs is told by the head its end stands in --
            # a bottom end in a head means the stem rises from it (up), a top end in a head that it hangs from it (down)
            hb_ = next((b for b in others if b[1] - slack <= sy + sh <= b[1] + b[3] + slack and _overlap(sx, sx + sw, b[0] - slack, b[0] + b[2] + slack) > 0), None)
            ht_ = next((b for b in others if b[1] - slack <= sy <= b[1] + b[3] + slack and _overlap(sx, sx + sw, b[0] - slack, b[0] + b[2] + slack) > 0), None)
            if (hb_ is None) == (ht_ is None):
                direction = None
            else:
                direction, anchor_box = ("up", hb_) if hb_ is not None else ("down", ht_)
        tip_end = "top" if direction == "up" else "bottom" if direction == "down" else None
        tip_y = (sy if direction == "up" else sy + sh) if direction else None
        common = dict(ordinals=tuple(m.ordinal for m in members), row_ids=tuple(m.row_id for m in members), box=box, side=side,
                      direction=direction, tip_end=tip_end, tip_y=tip_y, length_sp=round(length, 3), gap_sp=round(gap, 3),
                      from_head_sp=(round(abs(hcy - tip_y) / sp, 3) if tip_y is not None else None),
                      tip_step=_tip_step(members, tip_end) if tip_end else None, ends_in_head=ends_in, anchored=anchored,
                      merged=len(members) > 1)
        # the refusals, in the order a human would ask them
        if length > STEM_MAX_SPACES and len(members) > 1:
            # 2.204 (Litolff, 37 of the 8-page `barline` disagreements): collinear pieces joined across a crossing run past any stem's length
            # when a SECOND stem stands above/below the first. Nobody has shown this is a barline (one stroke drawn 12 sp tall is): the map
            # cannot tell -> the finder's stem stands (`map_cannot_tell`), never a refusal.
            why = "unanchored"
        elif length > STEM_MAX_SPACES:
            why = "barline"
        elif cell_width is not None and not ends_in and (sx <= CELL_EDGE_SPACES * sp or sx + sw >= cell_width - CELL_EDGE_SPACES * sp):
            why = "barline"
        elif not anchored or direction is None:
            why = "unanchored"
        elif side == "through":
            why = "through_head"
        elif not engraving_side_ok(direction, side):
            # a second's DISPLACED head stands on the far side of the chord's one stem: the stroke touches it on the wrong side, but the head
            # its end stands in sees it on the right one. Only a passing stem, and only then.
            a_l, a_r = (sx - anchor_box[0]) / sp if anchor_box else 9.0, ((anchor_box[0] + anchor_box[2]) - (sx + sw)) / sp if anchor_box else 9.0
            if anchor_box is not None and engraving_side_ok(
                    direction, "left" if a_l <= FLUSH_SPACES and a_l <= a_r else "right" if a_r <= FLUSH_SPACES else "through"):
                displaced = True
                why = "bridged" if gap > 0 else ""
            else:
                why = "wrong_side"
        else:
            why = "bridged" if gap > 0 else ""
        common["displaced"] = displaced
        cands.append(StemCand(**common, why=why))

    if whole_head:
        return StemReading("whole_head", candidates=tuple(cands), reason="a_whole_note_has_no_stem")
    good = [c for c in cands if c.why == ""]

    def blocked(c: StemCand) -> bool:        # a bridge is blocked by another head standing in the gap (2.161)
        gx0, gx1 = (hx + hw, c.box[0]) if c.side == "right" else (c.box[0] + c.box[2], hx)
        return any(b[0] < gx1 and b[0] + b[2] > gx0 and b[1] < hy + hh and b[1] + b[3] > hy for b in others)

    bridged = [c for c in cands if c.why == "bridged" and not blocked(c)]
    if len(good) == 1:
        return StemReading("stem", stems=(good[0],), candidates=tuple(cands))
    if len(good) == 2 and {g.direction for g in good} == {"up", "down"} and all(g.ends_in_head for g in good):
        return StemReading("two_stems", stems=tuple(sorted(good, key=lambda g: g.box[0])), candidates=tuple(cands), reason="pair_at_one_head")
    if len(good) >= 2:
        return StemReading("ambiguous", candidates=tuple(cands), reason="several_stems_on_the_engraving_side")
    if len(bridged) == 1:
        return StemReading("bridged", stems=(bridged[0],), candidates=tuple(cands))
    if len(bridged) > 1:
        return StemReading("ambiguous", candidates=tuple(cands), reason="several_bridged_stems")
    for why in ("wrong_side", "through_head", "barline", "unanchored"):
        if any(c.why == why for c in cands):
            return StemReading(why, candidates=tuple(cands), reason=why)
    return StemReading("no_stem", candidates=tuple(cands), reason="no_vertical_stroke_beside_the_head")
