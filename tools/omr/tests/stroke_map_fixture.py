"""A head's ink as the stroke map files it (`Q.STROKE` rows), for tests of rules OTHER than the beam count that need a note's beam
count to be READ (ROADMAP 2.319 r2). The one beam count (`rhythm._one_beam_count`) is the only beam reader; it reads a note's beams where its
stem's ink meets the beams' ink, so a fixture that wants "this head carries N beams" (or "a bare stem: no beam") files the head's blob, its
stem and N beams joining the stem to a second stem -- the shape a printed beamed pair has. The beam count itself is pinned on REAL stroke rows
(`test_one_beam_reader_2_319*.py`, `test_staged_one_beam_count_2_318.py`); these synthetic strokes only stand in for it elsewhere.

Rows are filed in the cell's own frame, one ordinal per stroke (glyph `STROKE_GLYPH_BASE + ordinal`), lengths and thicknesses in staff spaces."""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from tools.omr.staged import record as R
from tools.omr.staged.record import Q, READERS, STROKE_GLYPH_BASE

Stroke = Tuple[str, Tuple[float, float, float, float], float, float, List[int]]      # kind, box, length (sp), thickness (sp), touches


def file_strokes(log, strokes: Sequence[Stroke], *, sp: float, cell=(0, 0, 0, 0), first: int = 0) -> None:
    """File `strokes` as `Q.STROKE` rows of `cell`, ordinals `first`, `first + 1`, ... (touches name ordinals)."""
    for i, (kind, box, length, thick, touches) in enumerate(strokes):
        log.observe(R.glyph(*cell, STROKE_GLYPH_BASE + first + i), Q.STROKE, kind, reader=READERS.CV_STROKE, frame="cell:%d" % cell[3],
                    stroke_box=[float(v) for v in box], length_spaces=float(length),
                    angle_deg=0.0 if kind == "horizontal" else 90.0, thickness_spaces=float(thick), thickness_spread_spaces=0.02, fill=0.9,
                    sagitta_spaces=0.0, touches=[[int(j), 1.0] for j in touches], staff_space_local_px=float(sp), ends=[0, 0, 0, 0],
                    end_steps_from_top=[0.0, 0.0], component=0)


def note_ink(head_box: Sequence[float], *, sp: float, side: str = "down", beams: int = 0, first: int = 0, stem_spaces: float = 3.5,
             hook: bool = False, beam_thick: float = 0.55, stub: bool = False) -> List[Stroke]:
    """The strokes of one note: the head's blob, its stem on the engraving side (up -> right, down -> left) running `stem_spaces` past the
    head, and `beams` beams at the stem's tip, each joining it to a second stem three spaces to the right (a beamed pair). `hook`: a short
    curve at a bare tip (a flag's ink), touching only this stem. `beam_thick`: the beams' thickness in spaces (0.4375-0.5 is the band where a
    stroke joining two stems is only POSSIBLY a beam, `beam_strokes.BEAM_DOUBT_MIN_THICKNESS_SP`). Ordinals start at `first`: blob, stem, beams...,
    second stem / hook. `stub`: with `beams`, a short beam-thick bar one level further in touching only this stem (a possible further level: the
    count reads `beams` certain, one more possible)."""
    hx, hy, hw, hh = (float(v) for v in head_box)
    w = 0.25 * sp
    blob, stem = first, first + 1
    if side == "down":
        sx, y0, y1 = hx, hy + hh / 2.0, hy + hh + stem_spaces * sp
        tip = y1
    else:
        sx, y0, y1 = hx + hw - w, hy - stem_spaces * sp, hy + hh / 2.0
        tip = y0
    beam_ords = [first + 2 + k for k in range(beams)]
    other = first + 2 + beams
    stub_ord = [other + 1] if (stub and beams) else []
    out: List[Stroke] = [("blob", (hx, hy, hw, hh), max(hw, hh) / sp, 0.9, [stem]),
                         ("vertical", (sx, y0, w, y1 - y0), (y1 - y0) / sp, 0.25, [blob] + beam_ords + ([other] if hook else []) + stub_ord)]
    span = 3.0 * sp
    for k in range(beams):
        if side == "down":
            by = tip - 0.5 * sp - k * 0.75 * sp
        else:
            by = tip + k * 0.75 * sp
        out.append(("horizontal", (sx, by, span, 0.5 * sp), span / sp, beam_thick, [stem, other]))
    if beams:
        ox = sx + span - w
        oy0, oy1 = (tip - stem_spaces * sp, tip) if side == "down" else (tip, tip + stem_spaces * sp)
        out.append(("vertical", (ox, oy0, w, oy1 - oy0), stem_spaces, 0.25, beam_ords))
        if stub_ord:
            by = tip - 0.5 * sp - beams * 0.75 * sp if side == "down" else tip + beams * 0.75 * sp
            out.append(("horizontal", (sx, by, 1.0 * sp, 0.5 * sp), 1.0, 0.55, [stem]))
    elif hook:
        hy0 = tip - 1.2 * sp if side == "down" else tip
        out.append(("curve", (sx + w, hy0, 0.8 * sp, 1.2 * sp), 1.2, 0.3, [stem]))
    return out


def strokes_from_boxes(*, heads: Sequence[Sequence[float]] = (), stems: Sequence[Sequence[float]] = (), lines: Sequence[Sequence[float]] = (),
                       sp: float, touch_px: float = 2.0, max_thick: float = 0.9) -> List[Stroke]:
    """A tile's marks given as boxes (cell frame) -> the strokes the map would file: each head a blob, each stem a vertical, each line a
    horizontal (thickness its box height, capped at `max_thick` spaces -- a sloped beam's box is taller than its ink -- or a measured
    thickness given as the line's fifth number, in spaces); touches where two boxes meet within `touch_px`. Order: heads, stems, lines
    (ordinals in that order)."""
    items = [("blob", h) for h in heads] + [("vertical", s) for s in stems] + [("horizontal", b) for b in lines]

    def meet(a, b):
        a, b = a[:4], b[:4]
        return (a[0] - touch_px <= b[0] + b[2] and b[0] - touch_px <= a[0] + a[2]
                and a[1] - touch_px <= b[1] + b[3] and b[1] - touch_px <= a[1] + a[3])
    out: List[Stroke] = []
    for i, (kind, box) in enumerate(items):
        touches = [j for j, (k2, b2) in enumerate(items) if j != i and meet(box, b2) and not (kind == k2 == "blob")]
        x, y, w, h = (float(v) for v in box[:4])
        if kind == "vertical":
            length, thick = h / sp, w / sp
        elif kind == "horizontal":
            length, thick = w / sp, (float(box[4]) if len(box) > 4 else min(h / sp, max_thick))
        else:
            length, thick = max(w, h) / sp, 0.9
        out.append((kind, (x, y, w, h), length, thick, touches))
    return out


def file_note_ink(log, head_box: Sequence[float], *, sp: float, side: str = "down", beams: int = 0, cell=(0, 0, 0, 0),
                  first: Optional[int] = None, **kw) -> int:
    """`note_ink` filed on `log`; ordinals continue after the strokes this helper already filed on the log for `cell`. Returns the next free
    ordinal."""
    used = getattr(log, "_note_ink_next", {})
    start = used.get(tuple(cell), 0) if first is None else first
    strokes = note_ink(head_box, sp=sp, side=side, beams=beams, first=start, **kw)
    file_strokes(log, strokes, sp=sp, cell=tuple(cell), first=start)
    used[tuple(cell)] = start + len(strokes)
    try:
        setattr(log, "_note_ink_next", used)
    except AttributeError:
        pass
    return start + len(strokes)
