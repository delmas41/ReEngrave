"""lane-ledger-rungs round 5 (2026-10-0x) -- three faults Sean named in
the rung READ itself, each modelled on a real Litolff p3 example found by
walking `measure_ledger_rungs` against the actual record before writing
any fix (see FINDINGS.md "lane-ledger-rungs round 5" for the full
per-fault writeup with the real subjects and what the code did on them):

  1. CLEAN MIDDLE LEDGER MISSED. Two real cases, same root cause:
     (a) `glyph/3/0/9/2/0` (truth -2 half-steps... no, truth=11 outward):
         a chord stacks a neighbouring head (`glyph/3/0/9/2/9`) at nearly
         the SAME x as the subject; its own box is almost as wide as the
         `WINDOW_HALF_WIDTH_SPACES` candidate window, leaving only a
         couple of px of margin -- the OLD fixed `check_px` (0.10
         spacing) could not reach the real ledger's own ink just past
         that margin, so a genuine middle rung between two stacked heads
         was dropped as "the neighbour's own ink" (abstain, `no_rungs`).
     (b) `glyph/1/0/10/8/1` (truth -2): the walk's widen trigger only
         fired when the TARGET itself sat beyond `base_upper` -- here the
         target sat WITHIN it by a hair (21.24 vs 21.26 px) while the
         only real candidate band sat just OUTSIDE it (22.5 px): the
         widen never attempted at all and the walk found nothing.
  2. ONE-SIDED LEDGERS BESIDE A HEAD IN A SPACE (Sean's stated
     convention; no case in the two-document truth-set population
     currently flips on it -- see FINDINGS -- modelled here synthetically
     per his own description).
  3. HORIZONTAL DRIFT: a rung's x-centre is followed into the NEXT step's
     probe column rather than staying at the original fixed `x` (modelled
     synthetically -- measured real drift in this corpus was a few px,
     well inside the existing window's own reach; Sean's description is
     a general hand-drawn-ledger fact, not something this corpus's two
     count pages demonstrate at a scale large enough to flip a verdict).
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate.ledger_grid import (  # noqa: E402
    WALK_WINDOW,
    WINDOW_HALF_WIDTH_SPACES,
    _band_centers,
    _exclude_other_heads_ink,
    _select_next_candidate,
    _walk_ladder,
    derive_far_head_step,
    measure_ledger_rungs,
)

YS = [300, 400, 500, 600, 700]  # spacing 100, "above" edge = 300


# ─────────────────────────────────────────────────────────────────────────
# FAULT 1a: a stacked neighbour's box nearly fills the candidate window
# ─────────────────────────────────────────────────────────────────────────


def _stacked_chord_hides_middle_ledger() -> "np.ndarray":
    """A 2-line staff at spacing 100 (window for cx=150 is x=[40, 260]).
    A neighbouring chord-mate's box (36..256) is clipped by the window on
    BOTH sides (its own true left edge, 36, sits before the window's own
    left edge, 40) -- exactly `glyph/3/0/9/2/9`'s shape against
    `glyph/3/0/9/2/0`'s own probe window. The real ledger (one continuous
    run) extends from x=10 to x=286, i.e. genuinely past the neighbour's
    box on both sides -- but the part proving that (x=10..36 on the left)
    lies OUTSIDE the window entirely and can only be seen by reading the
    full page image, never the window's own crop."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for ly in YS[:2]:
        img[ly - 2: ly + 3, 10:290] = 0
    img[198:203, 10:287] = 0  # the one real ledger row
    return img


@pytest.mark.omr_annotate
def test_window_too_narrow_locally_recovered_by_full_image_read() -> None:
    """RED before round 5: the old fixed `check_px` (0.10 spacing, and
    clipped to the window's own crop regardless) could not see the real
    continuation, which sits entirely outside the window -- the rung was
    dropped as "the neighbour's own ink" and the walk abstained."""
    img = _stacked_chord_hides_middle_ledger()
    out = measure_ledger_rungs(
        img, YS[:2], 150.0,
        exclude_boxes=[(36.0, 190.0, 256.0, 215.0)],
    )
    assert out["above"] == pytest.approx([200.0], abs=3)


@pytest.mark.omr_annotate
def test_neighbor_with_no_real_continuation_still_excluded_control() -> None:
    """Control: the SAME nearly-window-filling neighbour box, but this
    time its own ink genuinely stops at its own edges (no real ledger
    continuing past it anywhere) -- must still be dropped, wide margin or
    not."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for ly in YS[:2]:
        img[ly - 2: ly + 3, 10:290] = 0
    img[198:203, 36:257] = 0  # the neighbour's own ink ONLY -- stops dead
    out = measure_ledger_rungs(
        img, YS[:2], 150.0,
        exclude_boxes=[(36.0, 190.0, 256.0, 215.0)],
    )
    assert out["above"] == []


# ─────────────────────────────────────────────────────────────────────────
# FAULT 1b: widen even when the target itself sits just within the window
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_widen_fires_when_candidate_sits_a_hair_past_base_upper() -> None:
    """RED before round 5: `glyph/1/0/10/8/1`'s own shape -- the target
    (`target_y`) sits WITHIN `base_upper` of the anchor, so the old
    `dist_to_target > base_upper` guard never widened at all, even though
    the only real candidate band sits a hair OUTSIDE `base_upper`. Anchor
    300, sign -1, pitch 100 -> base_upper = 135. Target at distance 134
    (just inside); the only band at distance 136 (just outside)."""
    anchor, sign, pitch, spacing = 300.0, -1.0, 100.0, 100.0
    target_y = anchor - 134.0
    bands = [anchor - 136.0]
    best, widened = _select_next_candidate(
        anchor, sign, bands, pitch, spacing, target_y
    )
    assert best == pytest.approx(anchor - 136.0)
    assert widened is True


@pytest.mark.omr_annotate
def test_widen_still_does_not_invent_past_the_target_plus_slack_control() -> None:
    """Control: a band far beyond even the widened reach must still be
    refused -- the fix only ever ADDS candidates within the existing
    target+slack bound, never removes that cap."""
    anchor, sign, pitch, spacing = 300.0, -1.0, 100.0, 100.0
    target_y = anchor - 134.0
    bands = [anchor - 400.0]  # way past target + TARGET_SLACK_SPACES*spacing
    best, widened = _select_next_candidate(
        anchor, sign, bands, pitch, spacing, target_y
    )
    assert best is None


@pytest.mark.omr_annotate
def test_strict_window_candidate_still_preferred_unwidened_control() -> None:
    """Control: when a candidate already sits inside the strict window,
    behaviour is exactly as before -- no widening, nearest-to-expected
    wins."""
    anchor, sign, pitch, spacing = 300.0, -1.0, 100.0, 100.0
    bands = [200.0, 50.0]
    best, widened = _select_next_candidate(
        anchor, sign, bands, pitch, spacing, target_y=50.0
    )
    assert best == pytest.approx(200.0)
    assert widened is False


@pytest.mark.omr_annotate
def test_real_shape_glyph_1_0_10_8_1_end_to_end() -> None:
    """End to end on a synthetic cell shaped like the real miss: a
    through-head rung sits just past the strict window's reach from the
    staff edge, with the head itself (`head_y`) sitting just inside it."""
    img = np.full((800, 300), 255, dtype=np.uint8)
    for ly in YS:
        img[ly - 2: ly + 3, 10:290] = 0
    # One rung, 136px above the edge (300) -- 1px past base_upper (135).
    img[162:167, 70:231] = 0
    out = measure_ledger_rungs(img, YS, 150.0, head_y=164.0)
    assert out["above"] == pytest.approx([164.0], abs=3)


# ─────────────────────────────────────────────────────────────────────────
# FAULT 2: one-sided ledgers beside a head sitting in a space
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_one_sided_ledger_beside_a_space_head_is_accepted() -> None:
    """A head's own box (120..180) sits in a SPACE; a ledger one line
    below the head (not through it) is drawn long on the RIGHT only --
    the left stub is absent entirely. `head_box_y` marks the row as
    outside the head's own box, so one real side is enough."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for ly in YS[:2]:
        img[ly - 2: ly + 3, 10:290] = 0
    # The head's own ink, in a space (not on this rung's row at all).
    img[150:171, 120:180] = 0
    # A ledger row (y~200, outside the head's box) with ink on the RIGHT
    # of the probe column (150) only, reaching well past the stub margin
    # (and past RUNG_MIN_LEN_SPACES*spacing=130px of overall length).
    img[198:203, 150:291] = 0
    out = measure_ledger_rungs(
        img, YS[:2], 150.0, head_box_y=(150.0, 171.0),
    )
    assert out["above"] == pytest.approx([200.0], abs=3)


@pytest.mark.omr_annotate
def test_one_sided_span_without_head_box_y_still_refused_control() -> None:
    """Control: the EXACT same one-sided ink, but `head_box_y` is not
    supplied (the old, pre-existing call shape) -- every existing caller
    keeps the old both-sides-always rule."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for ly in YS[:2]:
        img[ly - 2: ly + 3, 10:290] = 0
    img[198:203, 150:291] = 0
    out = measure_ledger_rungs(img, YS[:2], 150.0)
    assert out["above"] == []


@pytest.mark.omr_annotate
def test_one_sided_span_through_the_head_still_needs_both_sides_control() -> None:
    """Control: the SAME one-sided ink, but this time the row IS inside
    the head's own box (`head_box_y` covers it) -- a one-sided span
    through the head is indistinguishable from the head's own outline
    and must still be refused, exactly as round 3 shipped."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for ly in YS[:2]:
        img[ly - 2: ly + 3, 10:290] = 0
    img[198:203, 150:291] = 0
    out = measure_ledger_rungs(
        img, YS[:2], 150.0, head_box_y=(196.0, 205.0),
    )
    assert out["above"] == []


@pytest.mark.omr_annotate
def test_one_sided_span_both_sides_still_counted_control() -> None:
    """Control: a real both-sides rung beside a space-sitting head reads
    identically whether or not `head_box_y` is supplied."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for ly in YS[:2]:
        img[ly - 2: ly + 3, 10:290] = 0
    img[150:171, 120:180] = 0
    img[198:203, 70:231] = 0
    out = measure_ledger_rungs(
        img, YS[:2], 150.0, head_box_y=(150.0, 171.0),
    )
    assert out["above"] == pytest.approx([200.0], abs=3)


@pytest.mark.omr_annotate
def test_one_sided_band_centers_unit() -> None:
    """Unit-level: `_band_centers` itself accepts a one-sided span only
    outside `head_box_y`, directly (no window/candidate-finding noise)."""
    ink = np.zeros((10, 300), dtype=bool)
    ink[4, 150:291] = True  # one-sided span at y_offset+4, >=130px long
    through = _band_centers(ink, 150.0, 100.0, y_offset=0, head_box_y=(0, 9))
    beside = _band_centers(ink, 150.0, 100.0, y_offset=0, head_box_y=(20, 29))
    assert through == []
    assert beside == pytest.approx([4.0], abs=0.5)


# ─────────────────────────────────────────────────────────────────────────
# FAULT 3: horizontal drift -- follow the previous rung's own x
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_drift_follow_recovers_a_rung_shifted_out_of_the_fixed_column() -> None:
    """The first rung is asymmetric around the fixed probe column
    (x=150) -- long enough on the right to still pass the both-sides
    stub test there, but its own measured ink-centre (`_row_ink_center`)
    sits well to the right of 150. The SECOND, farther rung has drifted
    further in that same direction: its span never reaches back to
    x=150's own stub margin at all (invisible to the fixed-column walk
    entirely), but it DOES straddle the first rung's drifted centre.
    Round 5 re-probes the next step there and recovers it; RED before
    round 5 (no drift-follow at all): only the first rung is found."""
    img = np.full((800, 400), 255, dtype=np.uint8)
    for ly in YS:
        img[ly - 2: ly + 3, 10:390] = 0
    # Rung 1: reaches the x=150 stub margin on the left (barely) and
    # continues far to the right -- both-sides-at-150 still holds, but
    # its measured centre (clipped to the probe window) sits near x=195.
    img[198:203, 130:400] = 0
    # Rung 2: centred near x=240 -- its near edge (165) never reaches
    # x=150's own stub margin (135) at all, so the fixed-column walk
    # cannot find it; it DOES straddle rung 1's drifted centre (~195).
    img[98:103, 165:321] = 0
    out = measure_ledger_rungs(img, YS, 150.0, head_y=100.0)
    assert len(out["above"]) == 2
    assert out["above"][0] == pytest.approx(200.0, abs=3)
    assert out["above"][1] == pytest.approx(100.0, abs=3)


@pytest.mark.omr_annotate
def test_drift_follow_inert_when_no_drift_control() -> None:
    """Control: an evenly-aligned ladder (no x-drift at all) reads
    identically with or without the drift-follow step -- it only adds a
    rung the fixed column could not already see."""
    img = np.full((800, 300), 255, dtype=np.uint8)
    for ly in YS:
        img[ly - 2: ly + 3, 10:290] = 0
    img[198:203, 70:231] = 0
    img[98:103, 70:231] = 0
    out = measure_ledger_rungs(img, YS, 150.0, head_y=100.0)
    assert out["above"] == pytest.approx([200.0, 100.0], abs=2)


@pytest.mark.omr_annotate
def test_drift_follow_never_invents_a_rung_with_no_ink_control() -> None:
    """Control: with only ONE rung present and nothing beyond it at any
    x, the drift-follow step must not invent a second one."""
    img = np.full((800, 300), 255, dtype=np.uint8)
    for ly in YS:
        img[ly - 2: ly + 3, 10:290] = 0
    img[198:203, 70:231] = 0
    out = measure_ledger_rungs(img, YS, 150.0, head_y=100.0)
    assert out["above"] == pytest.approx([200.0], abs=3)
