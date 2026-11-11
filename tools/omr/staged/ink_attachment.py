"""Two questions any reader of the PAGE STROKE MAP asks of a piece of ink, answered once (ROADMAP 2.288 round 4; Sean 2026-11-10: "make the fix universal enough to help
us avoid missing or dropping tests like this"). Pure functions of the page stroke map and the page raster; no flag, no record, no decision. A reader that claims a mark's
ink (a rest, a dynamic, a repeat dot, an accidental, a flag) CALLS these and decides what the answer means for its own mark: the rest reader is the first caller.

WHY HERE: they are statements about ink geometry and attachment on the stroke map (`stroke_map`), not about any one mark, and `page_claim_names` (which names strokes for
area / box claims) is where a reader meets them. Keeping them out of the rest functions is the point: round 3's rest-only test ("a notehead fused to the line stays refused")
passed on a synthetic case while a real notehead on a line was claimed as a whole rest (Sean, Brahms p14 tile 4, 2026-11-10).

1. `attachment(page_map, own)` -- WHAT DOES THIS INK HANG FROM? Ink is attached when
     * its stroke touches a STEM (a vertical of at least the map's own vertical cut) that carries a head -- the head being another stroke OR THE INK ITSELF
       (a notehead is the stem's own head: round 2 asked only for a head OUTSIDE the ink, so a notehead with its stem was never "attached");
     * its stroke touches a head-shaped stroke directly;
   and a stroke that is only a vertical is a bare stem. (Engraving: a stem carries a head; a flag hangs from a stem; a rest stands free, Sean 2.150b.)
2. `line_sides(page_map, i, raw)` -- WHICH SIDE OF ITS STAFF LINE DOES THIS BLOCK LIE ON, and how many staff lines does it touch? Rows of the stroke that are staff line
   (the raw raster dark just beside the stroke on both sides, measured on the page locally -- a scanned staff tilts) are set aside; what is left lies ABOVE the line,
   BELOW it, BETWEEN two lines, or any mix. A whole rest HANGS from a line (ink below only), a half rest SITS on one (ink above only), and neither touches two lines
   (Sean 2026-09-29: "The rest should never touch 2 different staff lines"); a notehead on a line is CENTRED on it (ink on both sides) and a head in a space touches two.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

#: a pixel row of a stroke is a STAFF-LINE row when the raw raster is dark in this many columns just left AND just right of the stroke (>= LINE_FLANK_SHARE of them)
LINE_FLANK_PX = 5
LINE_FLANK_SHARE = 0.8
#: ink on a side of the line counts as a SIDE when it is at least this tall (staff spaces): half of a rest block's own height (a block is at most half a space,
#: `stroke_owner.BLOCK_MAX_H_SP` / the printed rest), so a block cannot have a side on both sides of its line; below it is the roughness of the scanned edge or the
#: line's own tilt (measured, Brahms p14 real whole rests: 0.00-0.12 sp on the far side; a notehead on a line: 0.44-0.50 sp each side)
SIDE_MIN_SP = 0.25


def head_shaped(page_map: Any, j: int) -> bool:
    """Is page stroke `j` a notehead's own piece: the register's head shape (`stroke_owner.shape_fit` family `head`, CLEAR only), a blob or a thick lens, never a dot's
    "could". The same shape rule the head tier claims by, not a new cut."""
    from . import stroke_owner as SO
    if not (0 <= j < len(page_map.strokes)):
        return False
    st = page_map.strokes[j]
    if st.kind not in ("blob", "horizontal"):
        return False
    sp = float(getattr(st, "staff_space_local", None) or getattr(page_map, "sp", 0.0) or 0.0)
    if sp <= 0:
        return False
    ink = SO.Ink(ordinal=j, kind=st.kind, box=tuple(float(v) for v in st.box), length=float(st.length_sp), thickness=float(st.thickness_sp),
                 area=float(st.area_sp2), space_px=sp, angle=float(st.angle_deg))
    return SO.shape_fit("head", ink)[0] == "clear"


def neighbours(page_map: Any, i: int) -> List[int]:
    st = page_map.strokes[i]
    return [int(j) for j, _c in (getattr(st, "touches", None) or ())] + [int(j) for j, _h in (getattr(st, "joined_to", None) or ())]


def attachment(page_map: Any, own: Sequence[int]) -> Optional[Dict[str, Any]]:
    """WHAT DOES THIS INK HANG FROM (module doc, 1). `own` = the page strokes of the ink in question. None when nothing can be read, else
      stem_with_head   strokes outside `own` that TOUCH it and are a stem (a vertical at least the map's own vertical cut) which carries a head: a head-shaped stroke outside
                       `own` (the flag / beam hook / stem-end of a note) OR a head-shaped stroke of `own` itself (the ink IS the stem's head: Brahms p14, 2.288 r3 tile 4)
      touches_a_head   head-shaped strokes outside `own` touching it directly (a rest never touches a note, 2.150b)
      bare_stroke      `own` holds nothing but vertical strokes: a stem or a flat's vertical, a rest has a body (curl, block, dot)."""
    if not own or not getattr(page_map, "strokes", None):
        return None
    from . import stroke_map as SM
    n = len(page_map.strokes)
    own_set = {int(i) for i in own if 0 <= int(i) < n}
    if not own_set:
        return None
    stems: Dict[int, int] = {}
    heads: List[int] = []
    for i in sorted(own_set):
        for j in neighbours(page_map, i):
            if j in own_set or not (0 <= j < n):
                continue
            sj = page_map.strokes[j]
            sp = float(getattr(sj, "staff_space_local", None) or getattr(page_map, "sp", 0.0) or 0.0)
            if sj.kind == "vertical" and float(sj.length_sp) >= SM.V_MIN_SPACES and sp > 0:
                carried = [k for k in neighbours(page_map, j) if head_shaped(page_map, k)]      # a head of the stem: outside the ink OR the ink's own
                if carried:
                    stems[j] = carried[0]
            elif head_shaped(page_map, j):
                heads.append(j)
    return dict(stem_with_head=sorted(stems), touches_a_head=sorted(set(heads)),
                bare_stroke=all(page_map.strokes[i].kind == "vertical" for i in own_set))


#: two long verticals are "side by side" when their vertical extents overlap by at least this share of the shorter one (a sharp's two verticals overlap ~1.0; a natural's
#: staggered pair ~0.6) and the gap between them is at most `PAIR_GAP_SP` staff spaces (the pair of one accidental, never two marks)
PAIR_OVERLAP_MIN = 0.5
PAIR_GAP_SP = 1.0
#: ... and CROSSED: an accidental's verticals are joined by two bars (a sharp's two slanted bars, a natural's two), which the stroke map keeps as the pieces lying in the gap
#: between the verticals. Two verticals with fewer than this many strokes between them are only two verticals (a quarter rest the map shattered, Breitkopf: Brahms p14).
PAIR_BARS_MIN = 2
#: ... and DRAWN: each vertical is a pen stroke, at least this thick (staff spaces). Measured on the 17 real accidentals Sean named with two long verticals on the four pages:
#: 0.19-0.32 sp (one natural 0.13, missed); the 2 px (0.06 sp) edge slivers the map leaves beside a shattered Breitkopf quarter rest (Brahms p14) are not strokes.
PAIR_THICK_MIN_SP = 0.15
GAP_SLACK_PX = 2.0


def parallel_verticals(page_map: Any, own: Sequence[int]) -> List[Dict[str, Any]]:
    """THREE: DOES THIS INK HOLD TWO LONG VERTICALS SIDE BY SIDE? (Sean 2026-11-10: the 2.285 sharp on Litolff p8 was claimed as a 16th rest.) Pure, from the stroke map alone
    (kind, box, length: no raster). The rule, in the piece's own strokes: a sharp is TWO long parallel verticals crossed by two bars and a natural is two STAGGERED verticals
    joined by two bars (engraving: they are one accidental's pair); a rest is ONE mark whose body is one stroke (a quarter rest's slanted stroke, an eighth / 16th rest's one
    slanted stem with its curls, a whole / half rest's one block) and so holds at most ONE long vertical; a stem beside a barline is not one ink either. A "long vertical" is a
    stroke of kind `vertical` at least `stroke_map.V_MIN_SPACES` long (the map's own cut, the same one `attachment` uses for a stem), at its own staff's local space.
    REFUSAL ONLY (CLAUDE §4: a cut-off found on our plates may only narrow, never decide): the numbers here (`PAIR_THICK_MIN_SP` 0.15, `PAIR_GAP_SP` 1.0, `PAIR_OVERLAP_MIN` 0.5, `PAIR_BARS_MIN`
    2) were MEASURED ON LITOLFF + BRAHMS, NOT CONFIRMED ON ANOTHER PUBLISHER. A pair here means "do not claim this ink as a single mark of another kind"; it never says the ink IS an
    accidental (the accidental reader reads that from the ink itself) and no caller may use it to decide a kind.
    Returns one dict per pair (`a`, `b`, `overlap` = share of the shorter's height, `gap_sp`); empty = none. A reader of ANY mark that is not an accidental, a bracket or a barline
    may refuse ink that returns a pair.
    WHAT WOULD FALSIFY IT: a real rest (or other single mark) whose own strokes include two long verticals side by side -- e.g. a quarter rest the map cut into two long overlapping
    slivers. The real judged rest tiles (`benchmarks/rests-claim-first-2026-11/real_cases.json`, 25 rests) are replayed in `test_rests_real_cases_2_288_r4.py`: none holds a pair."""
    if not own or not getattr(page_map, "strokes", None):
        return []
    from . import stroke_map as SM
    n = len(page_map.strokes)
    longs = []
    for i in sorted({int(i) for i in own if 0 <= int(i) < n}):
        st = page_map.strokes[i]
        sp = float(getattr(st, "staff_space_local", None) or getattr(page_map, "sp", 0.0) or 0.0)
        if (st.kind == "vertical" and float(st.length_sp) >= SM.V_MIN_SPACES and sp > 0
                and float(getattr(st, "thickness_sp", PAIR_THICK_MIN_SP) or 0.0) >= PAIR_THICK_MIN_SP):
            x, y, w, h = (float(v) for v in st.box)
            longs.append((i, x, y, x + w, y + h, sp))
    out = []
    for a in range(len(longs)):
        for b in range(a + 1, len(longs)):
            ia, xa0, ya0, xa1, ya1, sp = longs[a]
            ib, xb0, yb0, xb1, yb1, _sp = longs[b]
            overlap = (min(ya1, yb1) - max(ya0, yb0)) / max(1.0, min(ya1 - ya0, yb1 - yb0))
            gap = (max(xa0, xb0) - min(xa1, xb1)) / sp
            if overlap >= PAIR_OVERLAP_MIN and gap <= PAIR_GAP_SP:
                # the crossbars: the OTHER strokes of the ink that sit in the gap between the two verticals (the map cuts a sharp's two slanted bars into the pieces between its verticals)
                lo_x, hi_x = min(xa1, xb1) - GAP_SLACK_PX, max(xa0, xb0) + GAP_SLACK_PX
                lo_y, hi_y = max(ya0, yb0), min(ya1, yb1)
                bars = []
                for k in sorted({int(i) for i in own if 0 <= int(i) < n}):
                    if k in (ia, ib):
                        continue
                    kx, ky, kw, kh = (float(v) for v in page_map.strokes[k].box)
                    if kx + kw >= lo_x and kx <= hi_x and lo_y <= ky + kh / 2.0 <= hi_y:
                        bars.append(k)
                if len(bars) >= PAIR_BARS_MIN:
                    out.append(dict(a=ia, b=ib, overlap=round(overlap, 3), gap_sp=round(gap, 3), bars=bars))
    return out


def line_row_flags(raw: Any, m: Any, x0: int, y0: int, scale: float) -> List[bool]:
    """Per row of a stroke mask (reduced frame, offset `x0, y0`): True = the block's OWN row, False = a staff-line row. No raster: all True."""
    h, w = m.shape
    keep = [True] * h
    if raw is None:
        return keep
    fx0, fx1 = int(round(x0 / scale)), int(round((x0 + w) / scale))
    for r in range(h):
        y = int((y0 + r + 0.5) / scale)
        if not (0 <= y < raw.shape[0]):
            continue
        left, right = raw[y, max(0, fx0 - 1 - LINE_FLANK_PX):max(0, fx0 - 1)], raw[y, min(raw.shape[1], fx1 + 1):min(raw.shape[1], fx1 + 1 + LINE_FLANK_PX)]
        if len(left) >= LINE_FLANK_PX - 1 and len(right) >= LINE_FLANK_PX - 1 and float((left == 0).mean()) >= LINE_FLANK_SHARE and float((right == 0).mean()) >= LINE_FLANK_SHARE:
            keep[r] = False
    return keep


def line_sides(page_map: Any, i: int, raw: Any) -> Optional[Dict[str, Any]]:
    """WHICH SIDE OF ITS STAFF LINE, and how many lines (module doc, 2), for page stroke `i`. None where it cannot be measured (no raster, no unit, no line row: a block
    that touches no staff line has no side). Else, in staff spaces at the stroke's own staff:
      above / below / between   height of the stroke's OWN rows (line rows set aside) above the first line row, below the last, and between two line runs
      line_runs                 how many separate runs of line rows the stroke holds (1 = one line; 2 = it reaches across a space to a second line)
      both_sides                own ink above AND below the line (centred on it), each at least `SIDE_MIN_SP`
      two_lines                 two line runs with own ink between them (a head in a space, a beam piece between two lines)
    A block lies on ONE side of ONE line when neither flag is set."""
    if raw is None or i >= len(page_map.masks) or i >= len(page_map.strokes):
        return None
    st = page_map.strokes[i]
    sp = float(getattr(st, "staff_space_local", None) or getattr(page_map, "sp", 0.0) or 0.0)
    if sp <= 0:
        return None
    s = float(page_map.scale)
    m, x0, y0 = page_map.masks[i]
    keep = line_row_flags(raw, m, x0, y0, s)
    inked = [bool(m[r].any()) for r in range(m.shape[0])]
    line = [r for r in range(m.shape[0]) if inked[r] and not keep[r]]
    if not line:
        return None
    first, last = line[0], line[-1]
    runs = 1 + sum(1 for a, b in zip(line, line[1:]) if b - a > 1 and any(inked[r] and keep[r] for r in range(a + 1, b)))
    px = 1.0 / s / sp
    above = sum(1 for r in range(first) if inked[r] and keep[r]) * px
    below = sum(1 for r in range(last + 1, m.shape[0]) if inked[r] and keep[r]) * px
    between = sum(1 for r in range(first + 1, last) if inked[r] and keep[r]) * px
    return dict(above_sp=round(above, 3), below_sp=round(below, 3), between_sp=round(between, 3), line_runs=runs,
                both_sides=bool(above >= SIDE_MIN_SP and below >= SIDE_MIN_SP), two_lines=bool(runs >= 2 and between >= SIDE_MIN_SP))
