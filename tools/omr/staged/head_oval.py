"""Does a notehead box hold a head-shaped OVAL of ink? -- ROADMAP 2.164 (STAGED GATHER measurement; decides nothing).

Sean 2026-10-17, on the 2.160 sheets of head boxes at a bar's left edge: *"almost entirely tie ends ... or a bar line"*.
The detector reads one bar's crop at a time (a measure cell has no horizontal padding), so a tie that crosses a barline
is cut in two: the left piece is boxed as the tie, ending at the barline, and the right piece -- a short stroke at the
crop's left edge, with no context -- is boxed as a notehead. Its box is head-sized and its ink fraction can be as high
as a real head's (a short thick stroke fills a small box), so no existing size or ink gate refuses it.

CONVENTION: a notehead is an oval about one staff space tall -- filled, or an outline whose top and bottom edges are a
space apart -- and about one and a quarter spaces wide. So across the middle of a head, column after column, the
head's ink reaches from near its top to near its bottom. A tie's end is ONE thin curved stroke: in any column its ink
is only the stroke's own thickness. A barline is tall but only a hair wide. WHAT WOULD FALSIFY IT: a head Sean values
whose columns read as thin as a tie's stroke.

PURE: a page raster (0 == ink, staff lines in) and a page box in, numbers out; no log, no cell, no quantity named --
`gather.gather_head_oval` is its stage, `notehead_precision` reads its row and constants.

The measure (`oval_width`): in the box (widened by `SLACK_SPACES`), each pixel column's ink rows -- a run of ink lying
wholly on a staff or ledger line's rows left out, a line THICKENED by other ink kept (a row is a line where ink crosses
most of a window `LINE_WINDOW_SPACES` either side of the box) -- give a vertical SPAN: the largest top-to-bottom distance between two of its ink pixels no more than
`SPAN_WINDOW_SPACES` apart. A column is HEAD-TALL when its span is at least `HEAD_TALL_SPACES`. `oval_width` is the
widest run of consecutive head-tall columns, in staff spaces: a head gives most of its own width (~0.7-1.3 sp), a
tie's tail ~0 (its stroke is thin), a barline its own hair width (~0.1-0.2 sp).
"""
import os
from typing import Any, Dict, Optional, Sequence

#: ROADMAP 2.164 flag, default OFF: GATHER files `Q.HEAD_OVAL` and ADJUDICATE refuses an arc's tail boxed as a head.
ENV = "OMR_ARC_TAIL_NOT_A_HEAD"


def enabled() -> bool:
    """`OMR_ARC_TAIL_NOT_A_HEAD`, default OFF (ROADMAP 2.164); `1/true/yes/on` enables."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


#: A head's top and bottom edges stand ~0.9-1.0 sp apart; a column across its middle spans at least half a space.
#: A tie stroke is ~0.1-0.3 sp thick. (The head's own size, halved; swept 0.5-0.7 on both plates, FINDINGS 2.164.)
HEAD_TALL_SPACES = 0.5
#: Two ink pixels count toward one column's span only when no more than this apart (a head is ~1 sp tall: an
#: unrelated mark further off in the same column is not the head's other edge).
SPAN_WINDOW_SPACES = 1.3
#: How far past the detector's box the columns and rows are read (a box drawn a little off its own head).
SLACK_SPACES = 0.25
#: A row is a staff/ledger line where ink covers this share of a window `LINE_WINDOW_SPACES` either side of the box.
LINE_ROW_SHARE = 0.80
LINE_WINDOW_SPACES = 3.0
#: The box at a bar's left edge: it starts within this many staff spaces of the cell's left edge (2.160's geometry).
LEFT_EDGE_SPACES = 0.5


def _line_rows(ink_wide: Any) -> Any:
    """Boolean per row: a line row (ink over most of the wide window), dilated by one pixel either way."""
    w = max(1, ink_wide.shape[1])
    rows = ink_wide.sum(axis=1) / float(w) >= LINE_ROW_SHARE
    out = rows.copy()
    out[1:] |= rows[:-1]
    out[:-1] |= rows[1:]
    return out


def _kept_rows(col: Any, line: Any) -> Any:
    """The ink rows of one column, with every run of ink that lies WHOLLY on a staff/ledger line's rows left out: a
    bare line is not a head's edge, but a line THICKENED by a head's outline (or a stroke crossing it) is kept whole --
    a hollow head in a space has its top and bottom edges merged into the two lines around it."""
    import numpy as np
    ys = np.nonzero(col)[0]
    if len(ys) == 0:
        return ys
    keep = []
    start = prev = int(ys[0])
    for y in list(ys[1:]) + [None]:
        if y is not None and int(y) == prev + 1:
            prev = int(y)
            continue
        if not bool(line[start:prev + 1].all()):
            keep.extend(range(start, prev + 1))
        if y is not None:
            start = prev = int(y)
    return np.array(keep, dtype=int)


def _column_span(ys: Any, window: float) -> float:
    """Largest y-distance between two sorted ink rows no more than `window` apart (0.0 for fewer than two)."""
    if len(ys) < 2:
        return 0.0
    best = 0.0
    j = 0
    for i in range(len(ys)):
        while ys[i] - ys[j] > window:
            j += 1
        best = max(best, float(ys[i] - ys[j]))
    return best


def oval_width(page_binary: Any, box: Sequence[float], space_px: float) -> Optional[Dict[str, Any]]:
    """`{"oval_width_sp", "head_tall_columns", "columns", "max_span_sp", "line_rows"}`, or `None` off the raster or on a
    degenerate box (declined, never defaulted)."""
    import numpy as np
    if page_binary is None or getattr(page_binary, "ndim", 0) != 2 or not space_px or space_px <= 0:
        return None
    H, W = page_binary.shape
    sp = float(space_px)
    bx0, by0, bx1, by1 = (float(v) for v in box)
    if bx1 <= bx0 or by1 <= by0:
        return None
    x0, x1 = max(0, int(round(bx0 - SLACK_SPACES * sp))), min(W, int(round(bx1 + SLACK_SPACES * sp)))
    y0, y1 = max(0, int(round(by0 - SLACK_SPACES * sp))), min(H, int(round(by1 + SLACK_SPACES * sp)))
    if x1 - x0 < 1 or y1 - y0 < 2:
        return None
    lx0 = max(0, int(round(bx0 - LINE_WINDOW_SPACES * sp)))
    lx1 = min(W, int(round(bx1 + LINE_WINDOW_SPACES * sp)))
    line = _line_rows(page_binary[y0:y1, lx0:lx1] == 0)
    raw = (page_binary[y0:y1, x0:x1] == 0)
    window = SPAN_WINDOW_SPACES * sp
    tall = []
    spans = []
    for c in range(x1 - x0):
        ys = _kept_rows(raw[:, c], line)
        s = _column_span(ys, window)
        spans.append(s)
        tall.append(s >= HEAD_TALL_SPACES * sp)
    run = best = 0
    for t in tall:
        run = run + 1 if t else 0
        best = max(best, run)
    return {"oval_width_sp": round(best / sp, 3), "head_tall_columns": int(sum(tall)), "columns": len(tall),
            "max_span_sp": round(max(spans) / sp, 3) if spans else 0.0, "line_rows": int(line.sum())}


def box_at_left_edge(box: Sequence[float], cell_box: Sequence[float], space_px: float) -> bool:
    """The head box starts within `LEFT_EDGE_SPACES` of its bar's left edge (the barline the cell crop was cut at)."""
    return (float(box[0]) - float(cell_box[0])) / float(space_px) <= LEFT_EDGE_SPACES
