"""lane-ledger-rungs round 6 (2026-10-0x) -- stacked thirds imply a
ledger between them.

Sean, on round 5's flute chords (`glyph/3/0/0/2/1`, `/2/4`, `/2/9`,
`/6/2`, Litolff p3 -- the ledger hidden inside the merged blob between
two stacked heads was never found), DECISIONS 2026-10-0x: "when there
are multiple note heads stacked in thirds and neither of them has a line
through them then there must be a line between them and to go looking
for it."

Measured on the three real pairs this round names before any code
changed (`benchmarks/omr-local-staff-2026-09/FINDINGS.md` "round 6"):
centre-to-centre distance 0.81 (`glyph/3/0/0/6/1`+`/6/2`), 0.915
(`/2/4`+`/2/9`) and 1.12 (`/2/1`+`/2/3`) staff spaces -- a THIRD, with
slack for hand-drawn variance (`THIRD_STACK_SPACING_RANGE`).
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate.ledger_grid import (  # noqa: E402
    has_through_head_rung,
    heads_are_a_third_apart,
    insert_rung,
    third_stack_rung,
)


# ─────────────────────────────────────────────────────────────────────────
# the geometric guard: x-overlap + a third apart
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_real_shape_glyph_2_4_and_2_9() -> None:
    """The exact boxes from `glyph/3/0/0/2/4` and `glyph/3/0/0/2/9`
    (Litolff p3, spacing 15.5): centres 14.18px apart, 0.915 spacing."""
    box_far = (830.01, 382.73, 853.88, 404.585)
    box_near = (830.475, 397.92, 854.19, 417.76)
    assert heads_are_a_third_apart(box_far, box_near, 15.5) is True


@pytest.mark.omr_annotate
def test_a_second_apart_is_not_a_third_control() -> None:
    """Guard: a pair roughly HALF a space apart (a second, two heads a
    step apart -- an ordinary adjacent-note chord, not stacked thirds)
    must not qualify."""
    box_a = (100.0, 190.0, 130.0, 210.0)
    box_b = (100.0, 198.0, 130.0, 218.0)  # centres 8px apart, 0.5 spacing
    assert heads_are_a_third_apart(box_a, box_b, 16.0) is False


@pytest.mark.omr_annotate
def test_no_x_overlap_is_not_a_stack_control() -> None:
    """Guard: two heads a third apart in y but NOT overlapping in x (two
    different chords/stems, not one stack) must not qualify."""
    box_a = (100.0, 190.0, 130.0, 210.0)
    box_b = (200.0, 205.0, 230.0, 225.0)  # same y-gap, disjoint x
    assert heads_are_a_third_apart(box_a, box_b, 16.0) is False


@pytest.mark.omr_annotate
def test_too_far_apart_is_not_a_third_control() -> None:
    """Guard: two heads nearly TWO spaces apart (a fifth) must not
    qualify -- the range is specifically centred on one space."""
    box_a = (100.0, 150.0, 130.0, 170.0)
    box_b = (100.0, 180.0, 130.0, 200.0)  # centres 30px apart, ~1.9 spacing
    assert heads_are_a_third_apart(box_a, box_b, 16.0) is False


# ─────────────────────────────────────────────────────────────────────────
# the "neither has a line through it" guard
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_through_head_rung_detected() -> None:
    box = (100.0, 190.0, 130.0, 210.0)
    assert has_through_head_rung([201.0], box) is True


@pytest.mark.omr_annotate
def test_no_through_head_rung_control() -> None:
    box = (100.0, 190.0, 130.0, 210.0)
    assert has_through_head_rung([160.0, 230.0], box) is False


# ─────────────────────────────────────────────────────────────────────────
# third_stack_rung: ink-confirmed vs implied
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_implied_when_no_ink_at_the_midpoint() -> None:
    """RED before round 6: no function existed at all. A clean (ink-
    free) gap between the two heads -- the rung is IMPLIED at the exact
    midpoint, never guessed elsewhere."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    box_outer = (100.0, 150.0, 140.0, 175.0)   # centre y=162.5
    box_inner = (100.0, 190.0, 140.0, 215.0)   # centre y=202.5
    # Heads' own ink only -- nothing at all at the midpoint (182.5).
    img[150:176, 100:141] = 0
    img[190:216, 100:141] = 0
    out = third_stack_rung(img, box_outer, box_inner, spacing=16.0)
    assert out["confirmed"] is False
    assert out["y"] == pytest.approx(182.5, abs=0.5)


@pytest.mark.omr_annotate
def test_confirmed_with_a_faint_stub_at_the_midpoint() -> None:
    """A faint ledger stub at the midpoint, clearing the blob's own
    width on the RIGHT only (Sean: one side is enough here) -- ink-
    CONFIRMED at that same midpoint y."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    box_outer = (100.0, 150.0, 140.0, 175.0)
    box_inner = (100.0, 190.0, 140.0, 215.0)
    img[150:176, 100:141] = 0
    img[190:216, 100:141] = 0
    # A thin stub at y=182-183, reaching past the blob's right edge
    # (140) by well over the stub margin (0.15*16=2.4px).
    img[181:184, 95:160] = 0
    out = third_stack_rung(img, box_outer, box_inner, spacing=16.0)
    assert out["confirmed"] is True
    assert out["y"] == pytest.approx(182.5, abs=0.5)


@pytest.mark.omr_annotate
def test_confirmed_stub_left_side_only_control() -> None:
    """Control: the SAME faint stub, but only on the LEFT this time --
    one side is still enough (Sean's own wording)."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    box_outer = (100.0, 150.0, 140.0, 175.0)
    box_inner = (100.0, 190.0, 140.0, 215.0)
    img[150:176, 100:141] = 0
    img[190:216, 100:141] = 0
    img[181:184, 80:145] = 0  # stub past the LEFT edge (100) only
    out = third_stack_rung(img, box_outer, box_inner, spacing=16.0)
    assert out["confirmed"] is True


@pytest.mark.omr_annotate
def test_another_heads_ink_never_confirms_control() -> None:
    """Control: ink at the midpoint that belongs to an UNRELATED,
    excluded notehead (lateral to the blob) must not be read as
    confirming the implied rung."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    box_outer = (100.0, 150.0, 140.0, 175.0)
    box_inner = (100.0, 190.0, 140.0, 215.0)
    img[150:176, 100:141] = 0
    img[190:216, 100:141] = 0
    # A neighbour's own blob, far to the right, bleeding slightly into
    # the probe band's row -- excluded.
    img[181:184, 150:200] = 0
    out = third_stack_rung(
        img, box_outer, box_inner, spacing=16.0,
        exclude_boxes=[(150.0, 179.0, 200.0, 186.0)],
    )
    assert out["confirmed"] is False


# ─────────────────────────────────────────────────────────────────────────
# insert_rung: feeding the result into the same walk/count
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_insert_rung_above_staff_sorts_nearest_edge_first() -> None:
    # Above the staff: nearest-edge-first is DESCENDING y.
    out = insert_rung([428.5, 395.0], sign=-1.0, new_y=410.0)
    assert out == [428.5, 410.0, 395.0]


@pytest.mark.omr_annotate
def test_insert_rung_below_staff_sorts_nearest_edge_first() -> None:
    # Below the staff: nearest-edge-first is ASCENDING y.
    out = insert_rung([600.0, 630.0], sign=1.0, new_y=615.0)
    assert out == [600.0, 615.0, 630.0]


@pytest.mark.omr_annotate
def test_insert_rung_skips_a_near_duplicate_control() -> None:
    """Control: inserting a y that already matches an existing rung
    (within tolerance) must not create a duplicate."""
    out = insert_rung([428.5, 395.0], sign=-1.0, new_y=396.0, tol_px=3.0)
    assert out == [428.5, 395.0]
