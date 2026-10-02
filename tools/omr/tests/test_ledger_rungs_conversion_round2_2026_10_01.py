"""lane-ledger-rungs round 2 (coordinator/manager, 2026-10-01): Sean
approved round 1's reader fixes, then a manager read two page-3 crops
against the print and found the ARITHMETIC that turns a rung count into a
step was still wrong, plus a stub detection gap:

  * `glyph/3/0/7/6/2` (ref 12): one clean rung found, the head's NEAR edge
    sits ~0.39 staff spaces beyond it -- Sean's rule says that is "about
    half a space", i.e. ON THE NEXT ledger (hidden under the head, offset
    = rung's own offset + 2), never "space beyond the rung" (offset + 1).
  * `glyph/3/0/9/2/5` (ref 11): the head's near edge TOUCHES the one real
    rung (gap ~0.12 sp) -> the space beyond it. A SECOND "rung" was
    wrongly accepted because its left stub was a NEIGHBOURING head's own
    ink, not a ledger -- stub ink inside another notehead's box must not
    count.

Two new reader-level pieces, both pure/synthetic here (no re-gather):

  1. `ledger_grid.derive_far_head_step` -- the gap-to-last-rung arithmetic,
     replacing "match the head to within a generic tolerance".
  2. `measure_ledger_rungs(..., exclude_boxes=...)` -- masks another
     notehead's own ink out of the window before any span is measured.
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate.ledger_grid import (  # noqa: E402
    derive_far_head_step,
    measure_ledger_rungs,
    TOUCH_TOL_SPACES,
    HALF_LEDGER_TOL_SPACES,
)

YS = [300, 400, 500, 600, 700]  # spacing 100, "above" edge = 300


# ─────────────────────────────────────────────────────────────────────────
# (2) gap-to-last-rung arithmetic
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_no_rungs_abstains() -> None:
    assert derive_far_head_step([], 300.0, -1.0, 150.0, 100.0) == dict(
        offset=None, kind=None, reason="no_rungs"
    )


@pytest.mark.omr_annotate
def test_touching_the_last_rung_is_the_space_beyond_it() -> None:
    """RED before this round: the old code matched a head to a rung by
    distance-from-edge within a generic +-1 half-step tolerance, which
    this case (gap 0.12 sp) also happened to call "space" -- but by
    coincidence, not by this rule. `glyph/3/0/9/2/5`-shaped numbers:
    one rung 12px above a near edge (spacing 100), i.e. a 0.12sp gap."""
    out = derive_far_head_step([188.0], 300.0, -1.0, 200.0, 100.0)
    assert out["kind"] == "space"
    assert out["offset"] == 3  # last rung at 2 half-steps + 1


@pytest.mark.omr_annotate
def test_half_space_beyond_with_no_evidence_is_now_the_space_beyond_it() -> None:
    """SUPERSEDED by cause D (DECISIONS 2026-10-01, "four causes"): a gap
    this size used to be read as "on the next ledger, hidden under the
    head" by distance alone -- that distance guess is exactly what put
    tiles 6-8 of the neither-right sheet one ledger too far out. With no
    image/box supplied (no evidence possible), the head is now the SPACE
    beyond the last clean rung, never a guessed further line.
    `glyph/3/0/7/6/2`-shaped numbers: one rung, head's near edge 39px
    (0.39 sp) beyond it."""
    out = derive_far_head_step([200.0], 300.0, -1.0, 161.0, 100.0)
    assert out["kind"] == "space"
    assert out["offset"] == 3  # last rung at 2 half-steps + 1


@pytest.mark.omr_annotate
def test_half_space_beyond_with_real_evidence_is_the_next_ledger() -> None:
    """Cause D's positive case: the SAME gap as above, but the page
    actually shows a thin, flat line with stubs on both sides at the
    head's own middle row -- now the head IS on that ledger. Head box
    (120, 140, 180, 161): near edge (bottom, closest to the staff) =
    161, matching `head_near_y` below; a 5px-thick band at the box's
    own middle row (150.5), spanning well past both edges, stands in
    for the printed ledger."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    head_box = (120.0, 140.0, 180.0, 161.0)
    mid_y = int(round((140.0 + 161.0) / 2.0))
    img[mid_y - 2: mid_y + 3, 60:241] = 0
    out = derive_far_head_step(
        [200.0], 300.0, -1.0, 161.0, 100.0,
        img_gray=img, head_box=head_box,
    )
    assert out["kind"] == "line"
    assert out["offset"] == 4  # last rung at 2 half-steps + 2


@pytest.mark.omr_annotate
def test_rung_passing_through_with_no_evidence_is_not_through() -> None:
    """SUPERSEDED by cause D governing the through decision itself
    (coordinator, DECISIONS 2026-10-0x): the last rung sitting beyond
    the near edge used to be accepted as "passes through" on distance
    alone -- that is exactly the false through-head reading tiles 4-8
    of the neither-right sheet show. With no image/box supplied (no
    evidence possible), this candidate is dropped as the head's own
    outline, not a ledger -- and since it was the ONLY rung, nothing is
    left before the head: abstain, never a guess."""
    out = derive_far_head_step([150.0], 300.0, -1.0, 200.0, 100.0)
    assert out["kind"] is None
    assert out["offset"] is None
    assert "no_rung_before_the_head" in out["reason"]


@pytest.mark.omr_annotate
def test_rung_passing_through_with_real_evidence_is_through() -> None:
    """Cause D's positive case for the through branch: the SAME numbers
    as above, but the page shows a genuine thin, flat line with stubs
    on both sides at the head's own middle row -- confirmed through,
    the rung's own COUNT in the walk (one rung found = 2 half-steps),
    never a re-measurement of its raw pixel position (round 3 fix -- a
    re-measurement is exactly what stepped one too far on real,
    unevenly-spaced ledgers)."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    head_box = (120.0, 160.0, 180.0, 200.0)  # near edge (bottom) = 200
    # The through check reads AT THE CANDIDATE'S OWN row (150, not the
    # head box's unrelated geometric centre) -- a continuous band there,
    # through the box's own column, reaching past the right edge.
    img[148:153, 60:241] = 0
    out = derive_far_head_step(
        [150.0], 300.0, -1.0, 200.0, 100.0,
        img_gray=img, head_box=head_box,
    )
    assert out["kind"] == "line"
    assert out["offset"] == 2  # the one found rung's own COUNT-based offset


@pytest.mark.omr_annotate
def test_formerly_ambiguous_gap_is_now_the_space_with_no_evidence() -> None:
    """SUPERSEDED by cause D: the old code abstained between the two
    retired tolerances. There is no "ambiguous" bucket any more -- with
    no image/box supplied (no evidence of a line possible), any positive
    gap resolves to the space beyond the last clean rung, never a
    guess and never an abstention."""
    mid = (TOUCH_TOL_SPACES + HALF_LEDGER_TOL_SPACES) / 2.0
    near_y = 200.0 - mid * 100.0
    out = derive_far_head_step([200.0], 300.0, -1.0, near_y, 100.0)
    assert out["kind"] == "space"
    assert out["offset"] == 3


@pytest.mark.omr_annotate
def test_below_side_same_arithmetic_mirrored_no_evidence_is_space() -> None:
    """Mirrored on the below side; SUPERSEDED the same way as the
    half-space-beyond test above (no evidence supplied -> space, not a
    guessed next ledger)."""
    out = derive_far_head_step([800.0], 700.0, 1.0, 839.0, 100.0)  # gap 0.39
    assert out["kind"] == "space"
    assert out["offset"] == 3


@pytest.mark.omr_annotate
def test_below_side_with_real_evidence_is_the_next_ledger() -> None:
    """Mirrored positive case: the below-staff side, with a genuine
    ledger band at the head's own middle row."""
    img = np.full((1000, 300), 255, dtype=np.uint8)
    head_box = (120.0, 839.0, 180.0, 860.0)  # near edge (top) = 839
    mid_y = int(round((839.0 + 860.0) / 2.0))
    img[mid_y - 2: mid_y + 3, 60:241] = 0
    out = derive_far_head_step(
        [800.0], 700.0, 1.0, 839.0, 100.0,
        img_gray=img, head_box=head_box,
    )
    assert out["kind"] == "line"
    assert out["offset"] == 4


# ─────────────────────────────────────────────────────────────────────────
# (3) a stub inside another notehead's box does not count
# ─────────────────────────────────────────────────────────────────────────


def _cell_with_neighbor_bleed() -> "np.ndarray":
    """A 2-line staff; a real, short rung-length span exists through the
    probe column (x=150) ONLY because a neighbouring notehead's own ink
    sits just to the left of it. With that box excluded, the remaining
    (right-only) ink must fail the both-sides stub test."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for ly in YS[:2]:
        img[ly - 2: ly + 3, 10:290] = 0
    # The "neighbour" notehead: a filled block standing in for a head,
    # whose right edge pokes just past the probe column on its own row --
    # long enough, combined with a short genuine stub to the right, to
    # pass BOTH the overall length and the both-sides-stub test.
    img[198:203, 30:156] = 0   # neighbour's ink, crossing x=150 from the left
    img[198:203, 150:175] = 0  # a short, genuine bit of ink to the right
    return img


@pytest.mark.omr_annotate
def test_without_exclusion_the_neighbor_ink_fakes_a_rung() -> None:
    img = _cell_with_neighbor_bleed()
    out = measure_ledger_rungs(img, [300, 400], 150.0)
    assert out["above"] == pytest.approx([200.0], abs=3)


@pytest.mark.omr_annotate
def test_excluding_the_neighbor_box_removes_the_fake_rung() -> None:
    """RED before this round: `exclude_boxes` did not exist. GREEN after:
    masking the neighbour's own box out of the window leaves only the
    short right-side stub, which fails the both-sides-stub test."""
    img = _cell_with_neighbor_bleed()
    out = measure_ledger_rungs(
        img, [300, 400], 150.0, exclude_boxes=[(25, 190, 156, 210)]
    )
    assert out["above"] == []


@pytest.mark.omr_annotate
def test_excluding_a_box_elsewhere_changes_nothing_control() -> None:
    """Control: excluding a box far from the rung must not affect a real,
    legitimate rung."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for ly in YS[:2]:
        img[ly - 2: ly + 3, 10:290] = 0
    img[198:203, 60:241] = 0  # a normal, real rung, both sides generous
    out = measure_ledger_rungs(
        img, [300, 400], 150.0, exclude_boxes=[(0, 0, 5, 5)]
    )
    assert out["above"] == pytest.approx([200.0], abs=3)
