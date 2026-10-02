"""RED-first synthetic tests for the shape-trace step (ROADMAP lane
`lane-ledger-shape`, DECISIONS 2026-10-02: "trace the shape around far
heads (oval vs line)" and "an accidental can merge into a ledger; the
shape trace must still separate them").

Every image here is built by hand (no detector, no page, no weights) so
these tests are fast and fully synthetic -- the point of the lane is to
verify the TRACE/FIT/DECIDE primitives in isolation before touching the
real reader. Run: `pytest tools/omr/tests/test_ledger_shape_trace_2026_10_02.py`.
"""
from __future__ import annotations

import numpy as np
import pytest

from tools.omr.annotate import ledger_shape_trace as st

SPACING = 20.0  # px per staff space, a convenient round number


def _blank(h: int, w: int) -> np.ndarray:
    return np.full((h, w), 255, dtype=np.uint8)


def _draw_oval(img: np.ndarray, cx: float, cy: float, rx: float, ry: float,
                open_top: bool = False, open_bottom: bool = False) -> None:
    """Fills an ellipse with ink (0). `open_top`/`open_bottom` leave the
    extreme rows unfilled, simulating a half-note's open oval end."""
    h, w = img.shape
    y0, y1 = max(0, int(cy - ry) - 1), min(h, int(cy + ry) + 2)
    x0, x1 = max(0, int(cx - rx) - 1), min(w, int(cx + rx) + 2)
    for y in range(y0, y1):
        if open_top and y <= cy - ry * 0.85:
            continue
        if open_bottom and y >= cy + ry * 0.85:
            continue
        dy = (y - cy) / ry
        if abs(dy) > 1.0:
            continue
        dx = rx * (1.0 - dy * dy) ** 0.5
        lx, rxx = int(round(cx - dx)), int(round(cx + dx))
        img[y, max(0, lx):min(w, rxx + 1)] = 0


def _draw_hline(img: np.ndarray, y: float, x0: float, x1: float,
                 thickness: float = 2.0) -> None:
    h, w = img.shape
    t0, t1 = int(round(y - thickness / 2)), int(round(y + thickness / 2)) + 1
    t0, t1 = max(0, t0), min(h, t1)
    xi0, xi1 = max(0, int(round(x0))), min(w, int(round(x1)) + 1)
    img[t0:t1, xi0:xi1] = 0


def _draw_block(img: np.ndarray, x0, y0, x1, y1) -> None:
    h, w = img.shape
    img[max(0, int(y0)):min(h, int(y1)), max(0, int(x0)):min(w, int(x1))] = 0


def _head_box(cx, cy, rx=13.0, ry=11.0):
    return (cx - rx, cy - ry, cx + rx, cy + ry)


# ---------------------------------------------------------------------------
# trace_head_shape / the oval fit
# ---------------------------------------------------------------------------

def test_oval_alone_has_no_ledger_band():
    img = _blank(160, 160)
    cx, cy = 80.0, 80.0
    _draw_oval(img, cx, cy, rx=13, ry=11)
    box = _head_box(cx, cy)
    trace = st.trace_head_shape(img, box, SPACING)
    assert trace is not None
    assert trace.ledger_bands == []
    assert abs(trace.oval_center_y - cy) <= 2.0


def test_line_through_oval_middle_both_sides_reads_on():
    """Scenario 1: a line through the oval's own middle, shooting out on
    BOTH sides, must be read ON the line."""
    img = _blank(160, 160)
    cx, cy = 80.0, 80.0
    _draw_oval(img, cx, cy, rx=13, ry=11)
    _draw_hline(img, cy, cx - 30, cx + 30, thickness=2.0)
    box = _head_box(cx, cy)
    result = st.decide_head_position_from_shape(img, box, SPACING)
    assert result["decision"] == "on", result
    assert st.shape_trace_middle_rung_evidence(img, box, SPACING) is True


def test_line_through_oval_middle_one_side_reads_on():
    """Scenario 2: a jut on only ONE side is still a through-rung (Sean,
    DECISIONS 2026-10-0x: one side is enough)."""
    img = _blank(160, 160)
    cx, cy = 80.0, 80.0
    _draw_oval(img, cx, cy, rx=13, ry=11)
    # Only shoots out past the RIGHT edge of the oval, not the left.
    _draw_hline(img, cy, cx - 10, cx + 30, thickness=2.0)
    box = _head_box(cx, cy)
    result = st.decide_head_position_from_shape(img, box, SPACING)
    assert result["decision"] == "on", result


def test_line_touching_oval_top_only_reads_space_beyond():
    """Scenario 3: a line that touches only the oval's TOP (not its
    middle) is the ledger BEFORE/AFTER it -- the head sits in the space
    beyond that ledger, never ON it."""
    img = _blank(160, 160)
    cx, cy = 80.0, 80.0
    _draw_oval(img, cx, cy, rx=13, ry=11)
    _draw_hline(img, cy - 11, cx - 30, cx + 30, thickness=2.0)
    box = _head_box(cx, cy)
    result = st.decide_head_position_from_shape(img, box, SPACING)
    assert result["decision"] == "space_beyond", result
    assert st.shape_trace_middle_rung_evidence(img, box, SPACING) is False


def test_open_half_note_oval_with_line_through_reads_on_from_outline():
    """Scenario 4: an OPEN half-note oval (no closing ink at one end) with
    a line through its middle -- centre must come from the OUTLINE, and
    the decision is still ON."""
    img = _blank(160, 160)
    cx, cy = 80.0, 80.0
    _draw_oval(img, cx, cy, rx=13, ry=11, open_top=True)
    _draw_hline(img, cy, cx - 30, cx + 30, thickness=2.0)
    box = _head_box(cx, cy)
    trace = st.trace_head_shape(img, box, SPACING)
    assert trace is not None
    # The fitted centre must still land near the true geometric centre,
    # not be dragged off by the missing top rows.
    assert abs(trace.oval_center_y - cy) <= 3.0
    result = st.decide_head_position_from_shape(img, box, SPACING)
    assert result["decision"] == "on", result


def test_accidental_merged_into_ledger_still_reads_on_and_is_excluded():
    """Scenario 5 (DECISIONS 2026-10-02, "an accidental can merge into a
    ledger"): a through-rung with a TALL, non-thin shape (an accidental)
    fused onto its far end. The decision must still be ON, and the
    ledger band's own measured extent must stop before the accidental,
    not absorb it."""
    img = _blank(160, 200)
    cx, cy = 100.0, 80.0
    _draw_oval(img, cx, cy, rx=13, ry=11)
    _draw_hline(img, cy, cx - 30, cx + 40, thickness=2.0)
    # The "accidental": a tall block fused onto the far right end of the
    # ledger run, several times taller than the thin ledger band itself.
    _draw_block(img, cx + 36, cy - 14, cx + 50, cy + 14)
    box = _head_box(cx, cy)
    result = st.decide_head_position_from_shape(img, box, SPACING)
    assert result["decision"] == "on", result
    band = result["band"]
    # The measured right extent must stop well short of the accidental's
    # own far edge (cx+50) -- it must not have absorbed the tall block.
    assert band["right_x"] < cx + 36 + 4


def test_box_covering_only_top_half_of_head_still_centres_from_trace():
    """Scenario 6: a detector box that only covers the TOP half of the
    real head. The box's own naive centre is wrong by construction; the
    traced oval centre must still land near the true geometric centre and
    the decision must still be correct (ON, with a through line)."""
    img = _blank(160, 160)
    cx, cy = 80.0, 80.0
    _draw_oval(img, cx, cy, rx=13, ry=11)
    _draw_hline(img, cy, cx - 30, cx + 30, thickness=2.0)
    # Box covers only the top half of the real oval -- its own naive
    # centre is at cy - ry/2, far from the true centre cy.
    bad_box = (cx - 13, cy - 11, cx + 13, cy)
    naive_center = (bad_box[1] + bad_box[3]) / 2.0
    assert abs(naive_center - cy) > 4.0  # the premise: naive centre is wrong

    trace = st.trace_head_shape(img, bad_box, SPACING)
    assert trace is not None
    assert abs(trace.oval_center_y - cy) <= 3.0

    result = st.decide_head_position_from_shape(img, bad_box, SPACING)
    assert result["decision"] == "on", result


def test_no_image_abstains_never_guesses():
    """CLAUDE.md rule 8: no evidence possible -> `False`/`None`, never a
    guessed answer."""
    assert st.shape_trace_middle_rung_evidence(None, (0, 0, 10, 10), SPACING) is False
    assert st.trace_head_shape(None, (0, 0, 10, 10), SPACING) is None


def test_stem_column_is_excluded_from_oval_width():
    """A tall, narrow stem attached to the oval's side must not widen the
    oval's own fitted half-width or register as a protruding band."""
    img = _blank(200, 160)
    cx, cy = 80.0, 100.0
    _draw_oval(img, cx, cy, rx=13, ry=11)
    # A stem running up from the head's right edge, far taller than any
    # notehead or ledger band, and narrow.
    _draw_block(img, cx + 11, cy - 90, cx + 13, cy)
    box = _head_box(cx, cy)
    trace = st.trace_head_shape(img, box, SPACING)
    assert trace is not None
    assert trace.ledger_bands == []
