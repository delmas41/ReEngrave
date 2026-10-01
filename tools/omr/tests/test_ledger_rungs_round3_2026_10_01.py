"""lane-ledger-rungs round 3 (2026-10-01), from Sean's reading of the
round-2 review crops (DECISIONS 2026-10-01, newest line):

  1. OFF-BY-ONE: `glyph/3/0/0/2/3` (his C6, ref -4) found both ledgers,
     the last one passing through the head itself, and still wrote -5.
     "Fix the one line change that allowed the code to step further
     out." Cause: `derive_far_head_step` RE-MEASURED the last rung's own
     step from its raw pixel distance to the edge, rounding against the
     nominal half-step -- but hand-drawn ledgers are not evenly spaced,
     so a rung the walk correctly placed as the 2nd one out could
     measure 4.9 half-steps and round up to 5. The walk already KNOWS
     each rung's step (2 half-steps per rung found, by the ladder's own
     construction); the fix trusts the COUNT, never a re-measurement.
  2. A HEAD'S OWN INK IS NOT A RUNG: `glyph/3/0/9/2/0` (ref 11) --
     (a) the reader read the head's own widest row as a through-head
         rung; a real one needs stubs extending BEYOND the head's own
         box on both sides, not merely past the probe column.
     (b) the real ledger between two heads was erased by `exclude_boxes`
         blanking the WHOLE neighbouring box -- a ledger that continues
         past that box on both sides must survive the exclusion.
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate.ledger_grid import (  # noqa: E402
    derive_far_head_step,
    measure_ledger_rungs,
)

YS = [300, 400, 500, 600, 700]  # spacing 100, "above" edge = 300


# ─────────────────────────────────────────────────────────────────────────
# (1) off-by-one: trust the rung COUNT, never a re-measurement
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_real_shape_glyph_3_0_0_2_3() -> None:
    """The exact numbers from `glyph/3/0/0/2/3` (DECISIONS 2026-10-01):
    rungs at [431.5, 412.0], edge 450.0, spacing 15.5, near edge 424.58.
    Reference position -4. Round 2 wrote -5."""
    out = derive_far_head_step(
        [431.5, 412.0], edge_y=450.0, sign=-1.0, head_near_y=424.58,
        spacing=15.5,
    )
    assert out["kind"] == "line"
    assert out["offset"] == 4  # 0 - 4 = -4, matching the reference


@pytest.mark.omr_annotate
def test_evenly_spaced_control_unchanged() -> None:
    """Control: when the rungs ARE evenly spaced, count-based and
    distance-based arithmetic agree -- this must not regress. Two rungs
    at the walk's own 2-half-steps-per-rung spacing (200, 100 -- 1st and
    2nd out from edge 300), near edge at 125 (25px/0.25sp beyond the 2nd
    rung -- through-head zone)."""
    out = derive_far_head_step(
        [200.0, 100.0], edge_y=300.0, sign=-1.0, head_near_y=125.0,
        spacing=100.0,
    )
    assert out["kind"] == "line"
    assert out["offset"] == 4


# ─────────────────────────────────────────────────────────────────────────
# (2a) a through-head rung's stub must clear the SUBJECT's own box
# ─────────────────────────────────────────────────────────────────────────


def _wide_head_no_real_ledger(head_box_x=(120, 180)) -> "np.ndarray":
    """A 2-line staff; a notehead-shaped blob whose widest row spans
    exactly its own detector box (120..180, i.e. a 60px / 0.6-space-ish
    blob at spacing 100) and nothing more -- no real ledger anywhere."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for ly in YS[:2]:
        img[ly - 2: ly + 3, 10:290] = 0
    # The head's own ink: a tall-ish blob, widest row exactly its box.
    img[190:211, 120:180] = 0
    return img


@pytest.mark.omr_annotate
def test_heads_own_widest_row_is_not_a_rung() -> None:
    """RED before this round: the probe-column-relative stub test
    (+-0.15 spaces from x=150) was easily satisfied by ink that never
    reaches past the box's own edges at all."""
    img = _wide_head_no_real_ledger()
    out = measure_ledger_rungs(
        img, [300, 400], 150.0, head_box_x=(120.0, 180.0)
    )
    assert out["above"] == []


@pytest.mark.omr_annotate
def test_real_through_head_ledger_with_box_stubs_still_counts() -> None:
    """Control: a REAL ledger, with stubs that clear the box on both
    sides, must still be found even when `head_box_x` is supplied."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for ly in YS[:2]:
        img[ly - 2: ly + 3, 10:290] = 0
    # A real rung clearing the box (120..180) by a generous margin.
    img[198:203, 70:231] = 0
    out = measure_ledger_rungs(
        img, [300, 400], 150.0, head_box_x=(120.0, 180.0)
    )
    assert out["above"] == pytest.approx([200.0], abs=3)


# ─────────────────────────────────────────────────────────────────────────
# (2b) exclusion must not erase a ledger continuing past the other box
# ─────────────────────────────────────────────────────────────────────────


def _ledger_through_neighbor() -> "np.ndarray":
    """A 2-line staff; ONE real ledger spanning well past BOTH the
    subject's own box (135..165) and a neighbour's box (100..140) on
    either side of it."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for ly in YS[:2]:
        img[ly - 2: ly + 3, 10:290] = 0
    img[198:203, 60:240] = 0  # one continuous rung, clearing both boxes
    return img


@pytest.mark.omr_annotate
def test_excluding_a_neighbor_keeps_a_ledger_continuing_both_sides() -> None:
    """RED before this round: blanking the WHOLE neighbour box erased
    the middle of this real ledger, leaving two short, disconnected
    stubs that (after the box-relative stub fix above) no longer reach
    past the SUBJECT's own box and so the rung vanished entirely."""
    img = _ledger_through_neighbor()
    out = measure_ledger_rungs(
        img, [300, 400], 150.0, exclude_boxes=[(100.0, 190.0, 140.0, 215.0)],
        head_box_x=(135.0, 165.0),
    )
    assert out["above"] == pytest.approx([200.0], abs=3)


@pytest.mark.omr_annotate
def test_excluding_a_neighbors_own_ink_with_no_continuation_still_removed() -> None:
    """Control: a neighbour's own notehead ink (NOT a continuing ledger
    -- no ink immediately outside its box) is still removed as before."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for ly in YS[:2]:
        img[ly - 2: ly + 3, 10:290] = 0
    # Neighbour's own blob only -- ink stops at its own edges.
    img[198:203, 100:140] = 0
    out = measure_ledger_rungs(
        img, [300, 400], 150.0, exclude_boxes=[(100.0, 190.0, 140.0, 215.0)],
    )
    assert out["above"] == []
