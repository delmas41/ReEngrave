"""THE CONVENTION ANCHOR, and a thin seam onto the SHIPPED column reader.

⚠️⚠️ THIS FILE HELD ITS OWN COPY OF THE PROFILE AND THAT COPY WAS WRONG IN
TWO WAYS, SO EVERY FIGURE TAKEN BEFORE IT WAS DELETED IS SUPERSEDED. The
copy (a) read a column's FIRST-TO-LAST extent rather than its LONGEST RUN, so
a column holding two runs reported one stroke spanning both -- or, once its
own single-run guard fired, reported nothing at all; and (b) cut a band at
the width cap instead of applying the cap to the whole AGREEING REGION, so a
solid blob two staff spaces wide came out as three stems. **Both were found
by the shipped code's unit tests, not by review, and neither was visible in
any aggregate the arms printed.**

So there is no second copy any more: `read_strokes` calls
`tools.omr.line_detection._column_stroke_bands`, which is the code that
ships. A probe that re-implements its subject measures the re-implementation.

What stays here is the part that CANNOT ship in `line_detection.py`: the
convention anchor, which needs the NOTEHEADS, and `detect_stems` is handed a
cell and nothing else.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.omr.line_detection import (  # noqa: E402
    STEM_MAX_HEIGHT_LINES, STEM_STROKE_AGREE_SPACES, _column_stroke_bands)

AGREE_SPACES = STEM_STROKE_AGREE_SPACES


def read_strokes(ink, line_spacing: float, cell_w: int, *,
                 min_height_lines: float = 2.0,
                 max_height_lines: float | None = None,
                 max_width_lines: float = 0.6,
                 agree_spaces: float = AGREE_SPACES):
    """The SHIPPED reader, called by its own name. No logic of its own."""
    return _column_stroke_bands(
        ink, line_spacing, cell_w,
        min_height_lines=min_height_lines,
        max_height_lines=(STEM_MAX_HEIGHT_LINES if max_height_lines is None
                          else max_height_lines),
        max_width_lines=max_width_lines,
        agree_spaces=agree_spaces)


# ── THE ENGRAVING CONVENTION AS A CONSTRAINT, not as a score ────────────────
#
# `docs/engraving-conventions.md` [C9 + L10], status MEASURED HERE, RIGID,
# "one of the most reliable conventions in all of notation": a stem attaches
# on the RIGHT going UP or on the LEFT going DOWN, and Bravura makes the
# attachment explicit -- `stemUpSE` = [1.18, 0.168], `stemDownNW` = [0.0,
# -0.168], i.e. **x = 0 or x = notehead width**. So a stem stands at one
# VERTICAL EDGE of its head's box and never through its middle.
#
# ⚠️ A human does not scan columns; they look at the SIDE of a notehead.
# Reading every column of a cell finds every hairline on it -- a slur edge, a
# letter of `ff`, a beam fragment, a neighbour's stem -- and this is what
# separates the ones that can be a stem from the ones that cannot.
#
# ⚠️ How far from that edge the band's centre may stand, in NOTEHEAD WIDTHS --
# the head's own ruler, not the staff's, because the anchor is quoted in
# notehead widths and a detector box is documented as generous (CLAUDE.md:
# hand-drawn hollow heads measure 1.78 spaces against a click-placed 1.00).
SIDE_TOL_HEAD_WIDTHS = 0.35

#: How far a stem's near end may sit from its head's box, in staff spaces.
#: Bravura puts the attachment 0.168 sp off the pitch centre, i.e. INSIDE the
#: head; this only has to absorb the detector box and the plate's bleed.
ATTACH_GAP_SPACES = 0.25

# ⚠️⚠️ A STEM ENDS AT ITS HEAD RATHER THAN PASSING THROUGH IT — and this
# constraint is MEASURED AND DEAD, kept because the refutation is the finding.
#
# The crop pass found all 6 sampled Breitkopf disagreements to be one fault:
# the record's notehead box stands PART-WAY ALONG a neighbouring note's stem.
# `[C9 + L10]`'s anchor geometry says an up-stem's FOOT is at its head, so a
# stroke overshooting the head in BOTH directions is not that head's stem --
# which the geometry confirms (one band runs 6.58 spaces through a head,
# +3.75 above and +2.83 below).
#
# ⚠️⚠️ AND ENFORCING IT CHANGES NOTHING: 16 disagreements before and 16 after
# on Breitkopf, 41 and 41 on Litolff. The reason is a STAGE, not a
# tolerance -- `detect_stems` emits STROKES, not (stroke, head) pairs, so a
# band this rule refuses for head A is still in the cell's stroke list
# because head B admitted it, and the downstream overlap test hands it back.
# **The fault is in ATTRIBUTION and cannot be repaired in the reader.**
END_TOL_SPACES = 0.35


def anchor_to_heads(strokes, heads, line_spacing, *,
                    require_legal: bool = False,
                    end_tol: float | None = None,
                    side_tol: float = SIDE_TOL_HEAD_WIDTHS,
                    attach_gap: float = ATTACH_GAP_SPACES):
    """Keep only strokes standing at a notehead's LEFT or RIGHT EDGE.

    `heads` is an iterable of `(x, y, w, h)` in the same frame as `strokes`.
    Returns `[(stroke, head, side, direction)]`, one entry per (stroke, head)
    pair the convention admits -- a stroke may serve two heads of a chord,
    which is the convention's own "in a chord one stem serves every head".

    `require_legal` additionally demands the pair be RIGHT-and-UP or
    LEFT-and-DOWN. ⚠️⚠️ **TURNING IT ON MAKES ANY SCORE TAKEN WITH THE SAME
    CONVENTION CIRCULAR** -- the reader would then be graded on a rule it was
    built to satisfy, which is this repo's "a control that computes the wrong
    thing". It is a separate argument for exactly that reason, and the arm
    reports the two apart.
    """
    gap = attach_gap * line_spacing
    out = []
    for st in strokes:
        sx = st.x_canonical + st.width_canonical / 2.0
        sy0 = float(st.y_canonical)
        sy1 = float(st.y_canonical + st.height_canonical)
        for hx, hy, hw, hh in heads:
            if hw <= 0 or hh <= 0:
                continue
            tol = side_tol * hw
            left = abs(sx - hx) <= tol
            right = abs(sx - (hx + hw)) <= tol
            if not (left or right):
                continue
            # the stem must START at the head: overlap, or all but touching
            if sy0 > hy + hh + gap or sy1 < hy - gap:
                continue
            hcy = hy + hh / 2.0
            above = max(0.0, hcy - sy0)
            below = max(0.0, sy1 - hcy)
            direction = "up" if above > below else "down"
            if end_tol is not None:
                tol_y = end_tol * line_spacing
                if direction == "up":
                    if sy1 > hy + hh + tol_y:
                        continue
                elif sy0 < hy - tol_y:
                    continue
            side = "R" if (right and not left) else (
                "L" if (left and not right) else
                ("R" if abs(sx - (hx + hw)) <= abs(sx - hx) else "L"))
            if require_legal and not ((side == "R" and direction == "up")
                                      or (side == "L" and direction == "down")):
                continue
            out.append((st, (hx, hy, hw, hh), side, direction))
    return out
