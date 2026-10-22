"""lane-ledger-r7 (2026-10-01) -- one-sided ledgers re-validated by
FLATNESS, the two-edges-of-one-ledger merge, the duplicate-half-spacing
fault, and a wide-gap "look here" search.

Sean's verdicts on round 6's three diagnostic crops
(`out/print/ledgers/r6/`), DECISIONS 2026-10-01:

  (a) `glyph/3/0/0/2/4`+`/2/9`: a real ledger extends on ONE side only,
      past a "weird ink blotch" -- the blotch (measured directly off the
      real page: a 53px continuous ink column at the probe x, against a
      4-5px measured line thickness on the same raster) must not count
      as a "through" rung and block the stacked-thirds guard.
  (b) `glyph/3/0/0/2/1`+`/2/3`: already correct -- stays a CONTROL.
  (c) `glyph/3/0/0/6/1`+`/6/2`: two rungs 3px apart (under the measured
      4-5px thickness) are the top/bottom edge of ONE ledger -- merge.

Plus: a rung ~half a spacing from its neighbour is a duplicate edge, and
a wide gap (~2 spacings) between two found rungs is a place to LOOK (a
relaxed one-sided search), never a place to assume -- a clean gap implies
nothing; only two heads of one chord a third apart (round 6) do.
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate.ledger_grid import (  # noqa: E402
    DUPLICATE_HALF_SPACING_RANGE,
    GAP_FILL_RANGE_SPACINGS,
    LEDGER_THICKNESS_MAX_SPACES,
    drop_duplicate_half_spacing_rung,
    find_rung_in_gap,
    has_through_head_rung,
    merge_close_rungs,
    rung_is_thin_and_flat,
)

SPACING = 16.0


def _blank(h=400, w=300):
    return np.full((h, w), 255, dtype=np.uint8)


# ─────────────────────────────────────────────────────────────────────────
# rung_is_thin_and_flat -- RED before round 7 (no function existed)
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_real_thin_flat_line_passes():
    """A plain 4px horizontal band (measured real-page thickness) over a
    span wide enough to cover every sampled offset -- a genuine ledger."""
    img = _blank()
    img[100:104, 40:160] = 0
    assert rung_is_thin_and_flat(img, 102.0, 100.0, SPACING) is True


@pytest.mark.omr_annotate
def test_rounded_head_edge_fails_flatness_control():
    """A curved cap (like a notehead's own rounded top): thin enough at
    EACH sampled column individually (both under the 5.6px cap on
    SPACING=16), but the thickness varies from 5px at the centre to 1px
    at the +-5.6px sampled wings -- a 4px spread, over the 2.8px flatness
    tolerance -- fails FLATNESS, never a real (constant-thickness) line."""
    img = _blank()
    cx = 100
    for x in range(70, 131):
        dx = abs(x - cx)
        thick = max(3, 6 - dx)  # 6px at centre, 3px at the +-5.6px wings --
        img[100:100 + thick, x] = 0  # row 102 stays inked at every x
    assert rung_is_thin_and_flat(img, 102.0, cx, SPACING) is False


@pytest.mark.omr_annotate
def test_flag_ink_fails_thinness_control():
    """A flag's own ink: thick well past the cap everywhere it is
    sampled -- fails on THINNESS alone, same as round 6's confound (a
    53px continuous blob measured on the real page)."""
    img = _blank()
    img[85:130, 85:115] = 0  # a tall, thick blotch -- not a thin line
    assert rung_is_thin_and_flat(img, 102.0, 100.0, SPACING) is False


@pytest.mark.omr_annotate
def test_no_ink_at_all_fails_control():
    img = _blank()
    assert rung_is_thin_and_flat(img, 102.0, 100.0, SPACING) is False


# ─────────────────────────────────────────────────────────────────────────
# has_through_head_rung, round-7 ink-validated variant
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_proximity_only_unaffected_when_no_image_given():
    """Control: every pre-round-7 caller (img_gray=None) keeps the exact
    old proximity-only behaviour -- round 6's own tests must still pass
    unmodified."""
    box = (100.0, 190.0, 130.0, 210.0)
    assert has_through_head_rung([201.0], box) is True


@pytest.mark.omr_annotate
def test_blob_confound_rejected_with_image():
    """Round 6's exact confound: a rung sits inside the head's own box
    range by proximity, but the ink there is a tall continuous blob (a
    flag/merged-box artefact), not a thin flat line -- must NOT count as
    'through' once an image is supplied."""
    box = (100.0, 190.0, 130.0, 210.0)
    img = _blank()
    img[160:230, 100:131] = 0  # a 70px solid blob spanning the box
    assert has_through_head_rung([201.0], box, img_gray=img,
                                 spacing=SPACING) is False


@pytest.mark.omr_annotate
def test_real_through_rung_still_detected_with_image():
    """Control: a genuine thin flat ledger through the head's own box
    still counts as 'through' once ink-validated."""
    box = (100.0, 190.0, 130.0, 210.0)
    img = _blank()
    img[199:203, 80:150] = 0  # thin, flat, through the box
    assert has_through_head_rung([201.0], box, img_gray=img,
                                 spacing=SPACING) is True


# ─────────────────────────────────────────────────────────────────────────
# merge_close_rungs
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_two_edges_of_one_thick_ledger_merge():
    """`glyph/3/0/0/6/1`'s own measured case: 417.5 and 414.5 (3px apart)
    against a ~4.5px measured thickness -- merges to one at the centre."""
    out = merge_close_rungs([417.5, 414.5], sign=-1.0, thickness_px=4.5)
    assert out == pytest.approx([416.0])


@pytest.mark.omr_annotate
def test_two_real_ledgers_a_space_apart_stay_two_control():
    """Control: two genuine rungs a full staff space apart (16px) must
    never merge."""
    out = merge_close_rungs([450.0, 434.0], sign=-1.0, thickness_px=4.5)
    assert out == [450.0, 434.0]


@pytest.mark.omr_annotate
def test_merge_respects_nearest_edge_first_order():
    out = merge_close_rungs([434.5, 417.5, 414.5], sign=-1.0, thickness_px=4.5)
    assert out == pytest.approx([434.5, 416.0])


# ─────────────────────────────────────────────────────────────────────────
# drop_duplicate_half_spacing_rung
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_half_spacing_rung_dropped_as_duplicate_edge():
    # Above the staff (sign=-1), nearest-edge-first is DESCENDING y, so
    # 408.0 is the nearer rung and 400.0 (8px further out -- 0.5 x 16
    # spacing) is a duplicate of IT, never a ledger a half-step out.
    out = drop_duplicate_half_spacing_rung([408.0, 400.0], sign=-1.0,
                                           spacing=SPACING)
    assert out == [408.0]


@pytest.mark.omr_annotate
def test_uneven_but_complete_hand_drawn_spacing_untouched_control():
    """Control: real hand-drawn ledgers are not perfectly even (gaps
    0.9x-1.3x the nominal spacing per the module's own WALK_WINDOW) --
    none of that variance is a half-spacing duplicate and nothing here
    may be dropped."""
    # gaps of 14.5px (0.906x) and 20px (1.25x) on SPACING=16, already in
    # nearest-edge-first (descending) order for sign=-1 -- both well
    # inside WALK_WINDOW, nowhere near DUPLICATE_HALF_SPACING_RANGE.
    out = drop_duplicate_half_spacing_rung([434.5, 414.5], sign=-1.0,
                                           spacing=SPACING)
    assert out == [434.5, 414.5]


@pytest.mark.omr_annotate
def test_duplicate_of_the_staff_edge_itself_dropped():
    """A rung ~half a spacing OUT FROM THE EDGE (never found by the
    normal walk, which starts its search 0.30 spacing clear of the edge
    line) is a duplicate of the edge's own ink, not a ledger -- caught
    only when the caller supplies `edge`."""
    out = drop_duplicate_half_spacing_rung([408.0], sign=-1.0,
                                           spacing=SPACING, edge=416.0)
    assert out == []


@pytest.mark.omr_annotate
def test_duplicate_half_spacing_range_is_centred_on_half():
    assert DUPLICATE_HALF_SPACING_RANGE[0] < 0.5 < DUPLICATE_HALF_SPACING_RANGE[1]


# ─────────────────────────────────────────────────────────────────────────
# find_rung_in_gap -- a wide gap is a place to LOOK, not to assume
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_gap_with_a_faint_one_sided_ledger_is_found():
    """A thin, flat stub extending past the probe column on ONE side
    only (x=100..140, nothing to the left of x=100 -- so the -0.35-
    spacing sample at x~94 is unlit) strictly between y_lo=400 and
    y_hi=432 (a ~2-spacing gap on SPACING=16) -- the relaxed,
    one-sided-OK search must still find it."""
    img = _blank(h=460)
    img[314:318, 100:140] = 0
    y = find_rung_in_gap(img, 300.0, 332.0, 100.0, SPACING,
                         head_box_x=(90.0, 110.0))
    assert y is not None and 313.0 <= y <= 318.0  # somewhere in the 4px band


@pytest.mark.omr_annotate
def test_clean_gap_implies_nothing_control():
    """Sean: 'it is possible for it not to be there due to hand drawn
    spacing' -- a clean (ink-free) gap must return None, never a
    guessed midpoint."""
    img = _blank(h=460)
    y = find_rung_in_gap(img, 300.0, 332.0, 100.0, SPACING,
                         head_box_x=(90.0, 110.0))
    assert y is None


@pytest.mark.omr_annotate
def test_gap_fill_range_brackets_two_spacings():
    assert GAP_FILL_RANGE_SPACINGS[0] < 2.0 < GAP_FILL_RANGE_SPACINGS[1]


# ─────────────────────────────────────────────────────────────────────────
# end-to-end: the blob confound no longer blocks the stacked-thirds guard
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_stacked_third_with_no_ink_still_implied_control():
    """Sean's final wording: a ledger between two heads of ONE CHORD a
    third apart is counted with NO ink required -- round 6's own
    behaviour, unaffected by round 7 (re-stated here as a control against
    the new gap-fill rule, which must NOT be required for this case)."""
    from tools.omr.annotate.ledger_grid import third_stack_rung
    img = _blank()
    box_outer = (100.0, 150.0, 140.0, 175.0)
    box_inner = (100.0, 190.0, 140.0, 215.0)
    img[150:176, 100:141] = 0
    img[190:216, 100:141] = 0
    out = third_stack_rung(img, box_outer, box_inner, spacing=SPACING)
    assert out["confirmed"] is False
    assert out["y"] == pytest.approx(182.5, abs=0.5)
