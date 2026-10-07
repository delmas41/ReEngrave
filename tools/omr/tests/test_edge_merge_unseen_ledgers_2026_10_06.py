"""lane-edge-merge-unseen-ledgers (2026-10-06): three causes that lost a ledger the print shows plainly (STAGED far-head
reader; the legacy readers pass none of the three switches and are unchanged).

  1. `collapse_head_edge_rungs_to_middle(keep_edge_juts=True)`: a rung at the head's edge that shows a thin flat jut past
     the head is a ledger and stays; only the rows of the head's own outline (no jut) collapse.
  2. `_band_centers(split_welded=True)`: when the head body is itself wider than the rung length floor, two ledgers
     share ONE region of long rows; every thin plateau that stands out from the body by two stubs is a band.
  3. `_walk_ladder(tol_px=...)`: the window is widened by half a line thickness at both ends.

Each switch has a control in the same class: the same picture without the evidence must still be refused.
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate import far_head_reader as FH  # noqa: E402
from tools.omr.annotate.ledger_grid import (  # noqa: E402
    _band_centers,
    _walk_ladder,
    collapse_head_edge_rungs_to_middle,
)

pytestmark = pytest.mark.omr_annotate

SPACING = 100.0
HEAD_BOX = (120.0, 100.0, 180.0, 200.0)


def _page():
    img = np.full((400, 320), 255, dtype=np.uint8)
    img[100:200, 120:180] = 0   # the head's own black body
    return img


# -- 1. the edge collapse ----------------------------------------------------

def test_ledger_at_the_head_edge_with_a_jut_is_kept_and_the_outline_row_goes() -> None:
    img = _page()
    img[198:203, 60:241] = 0    # a printed ledger under the head: juts 60 px each side
    rungs = [200.0, 100.0]      # the ledger, and the head's own top row
    off = collapse_head_edge_rungs_to_middle(rungs, -1.0, HEAD_BOX, img, SPACING)
    on = collapse_head_edge_rungs_to_middle(rungs, -1.0, HEAD_BOX, img, SPACING, keep_edge_juts=True)
    assert off == []                              # the old rule: both are 'the outline'
    assert on == pytest.approx([200.0])           # the ledger stays, the outline row goes


def test_two_ledgers_flanking_a_head_in_a_space_both_stay() -> None:
    img = _page()
    img[98:103, 60:241] = 0
    img[198:203, 60:241] = 0
    rungs = [200.0, 100.0]
    on = collapse_head_edge_rungs_to_middle(rungs, -1.0, HEAD_BOX, img, SPACING, keep_edge_juts=True)
    assert on == rungs
    assert collapse_head_edge_rungs_to_middle(rungs, -1.0, HEAD_BOX, img, SPACING) == []


def test_control_outline_rows_with_no_jut_still_collapse() -> None:
    """Same class: the head alone, rows at its own edges and no ink past it: dropped with the switch on, as before."""
    img = _page()
    rungs = [200.0, 100.0]
    assert collapse_head_edge_rungs_to_middle(rungs, -1.0, HEAD_BOX, img, SPACING, keep_edge_juts=True) == []


def test_control_a_slur_under_the_head_has_no_jut_and_goes_with_the_outline() -> None:
    """A row with no ink past the head's own columns (what a slur under it is, at the head's edge) is not a jut: the real ledger stays, that row does not."""
    img = _page()
    img[198:203, 60:241] = 0     # the real ledger at the bottom edge
    rungs = [200.0, 102.0]   # the ledger at the bottom edge, the stroke row at the top edge
    on = collapse_head_edge_rungs_to_middle(rungs, -1.0, HEAD_BOX, img, SPACING, keep_edge_juts=True)
    assert on == pytest.approx([200.0])


# -- 2. two ledgers welded into one region by a wide head body ---------------

def _welded_ink(bulge: int = 0):
    """spacing 20: head body 28 px (1.4 sp, above the 26 px floor) rows 0..40, two ledgers 40 px wide (rows 5-8, 31-34)."""
    h, w, cx = 41, 80, 40
    ink = np.zeros((h, w), dtype=bool)
    for r in range(h):
        half = 14
        ink[r, cx - half:cx + half] = True
    for r0 in (5, 31):
        ink[r0:r0 + 4, cx - 20:cx + 20] = True
    if bulge:
        ink[18:21, cx - 14 - bulge:cx + 14 + bulge] = True
    return ink, cx


def test_a_head_body_wider_than_the_floor_welds_two_ledgers_into_one_band_unless_split() -> None:
    ink, cx = _welded_ink()
    assert len(_band_centers(ink, cx, 20.0, 0)) == 1
    on = _band_centers(ink, cx, 20.0, 0, split_welded=True)
    assert len(on) == 2
    assert on[0] == pytest.approx(6.5, abs=1.0) and on[1] == pytest.approx(32.5, abs=1.0)


def test_control_the_head_s_own_bulge_is_not_a_second_ledger() -> None:
    """A body that merely swells by 2 px each side (less than two stubs) gives no second band."""
    ink, cx = _welded_ink(bulge=2)
    ink[5:9, :] = False
    ink[31:35, :] = False
    ink[5:9, cx - 14:cx + 14] = True
    ink[31:35, cx - 14:cx + 14] = True
    a = _band_centers(ink, cx, 20.0, 0)
    b = _band_centers(ink, cx, 20.0, 0, split_welded=True)
    assert a == b


# -- 3. the walk window ------------------------------------------------------

def test_walk_window_tolerance_catches_a_gap_that_misses_by_a_fraction_of_a_pixel() -> None:
    # Litolff p5 `glyph/5/0/5/9/0`: staff top 1449.0, ledgers 1428 (gap 21.0), 1414.5 (13.5: 0.643 of 21.0), 1397.
    bands = [1397.0, 1414.5, 1428.0]
    # 13.5 < 0.65 x 21.0 = 13.65 by 0.15 px, and 1397 is then out of reach
    assert _walk_ladder(1449.0, -1.0, bands, 15.62) == [1428.0]
    assert _walk_ladder(1449.0, -1.0, bands, 15.62, tol_px=0.5) == [1428.0, 1414.5, 1397.0]


def test_control_a_half_pitch_cap_fake_is_still_refused_with_the_tolerance() -> None:
    bands = [1417.5, 1428.0]       # 10.5 px = half of the 21.0 pitch
    assert _walk_ladder(1449.0, -1.0, bands, 15.62, tol_px=0.5) == [1428.0]
    # Litolff p5 `glyph/5/0/5/4/2`: the head's own middle row, 9.5 px past a ledger that is 16.8 px from the staff line
    # (0.57 of it) is not a rung; a tolerance of half a line thickness (2.5 px) would have admitted it
    assert _walk_ladder(1447.8, -1.0, [1421.5, 1431.0], 15.62, tol_px=0.5) == [1431.0]
    assert _walk_ladder(1447.8, -1.0, [1421.5, 1431.0], 15.62, tol_px=2.5) == [1431.0, 1421.5]


def test_the_three_switches_are_on_in_the_far_head_reader_and_off_in_the_legacy_default() -> None:
    for k in ("edge_jut_kept", "split_welded_bands", "rows_clear_of_box"):
        assert FH.READER_KEYWORDS[k] is True
    assert FH.READER_KEYWORDS["walk_tol"] is False      # measured and refused: see the FINDINGS
    from tools.omr.annotate.ledger_grid import measure_ledger_rungs
    import inspect
    d = inspect.signature(measure_ledger_rungs).parameters
    assert d["keep_edge_juts"].default is False and d["split_welded_bands"].default is False
    assert d["walk_tol_px"].default == 0.0 and d["outline_margin_px"].default == 0.0


def test_a_short_ledger_clear_of_the_head_s_rows_needs_no_extra_width_but_the_head_s_own_row_does() -> None:
    """Litolff p5 `glyph/5/0/5/9/0`: a hand-drawn bar 27 px wide under a 25.5 px box (needs 27.08 with 0.05 sp each side) is
    a ledger because it sits 6 px below the box's rows; the same width AT the box's rows is the head's own widest row."""
    from tools.omr.annotate.ledger_grid import _rung_row_clears_box as clears
    sp = 15.62
    img = np.full((120, 200), 255, dtype=np.uint8)
    img[40:60, 80:106] = 0                 # the head: x 80..106 (box 80.0..105.5), rows 40..60
    img[66:71, 79:106] = 0                 # a bar 27 px wide, 6 px below the box (rows 66..70)
    img[52:57, 79:106] = 0                 # the same width inside the head's rows
    bx = (80.0, 105.5)
    assert clears(img, 68.0, 92.0, bx, sp) is False                                   # old: the width test refuses it
    assert clears(img, 68.0, 92.0, bx, sp, None, (40.0, 60.0), 2.5, -1.0) is True     # staff side, clear of the box's rows: a ledger
    assert clears(img, 68.0, 92.0, bx, sp, None, (40.0, 60.0), 2.5, 1.0) is False      # control: the same bar on the FAR side of the head (a slur, a flag)
    assert clears(img, 54.0, 92.0, bx, sp, None, (40.0, 60.0), 2.5, -1.0) is False   # control: the head's own row still refused
    assert clears(img, 62.0, 92.0, bx, sp, None, (40.0, 60.0), 2.5, -1.0) is False   # control: no ink at the row at all


def _welded_page(row: int = 160):
    img = np.full((260, 300), 255, dtype=np.uint8)
    for y in (200, 220, 240, 259):       # staff lines (only the top one matters here)
        img[y - 1:y + 2, 20:280] = 0
    img[130:176, 136:164] = 0            # the head's body, 28 px wide (1.4 sp, above the 26 px rung floor), x 136..164
    img[176:180, 100:200] = 0            # a real ledger under it (juts far)
    img[row:row + 4, 130:170] = 0        # a plateau in the head's rows, 40 px wide
    return img


def test_a_plateau_found_only_by_splitting_must_jut_past_the_head_on_the_staff_side_to_be_a_rung() -> None:
    from tools.omr.annotate.ledger_grid import measure_ledger_rungs
    ys = [200.0, 220.0, 240.0, 260.0, 280.0]
    wide = (128.0, 128.0, 172.0, 178.0)    # a box 44 px wide: the plateau lies inside its columns (no jut)
    narrow = (136.0, 128.0, 164.0, 178.0)  # the head's own 28 columns: the plateau juts 6 px each side
    run = lambda page, box: measure_ledger_rungs(page, ys, 150.0, head_y=150.0, head_box_x=(box[0], box[2]),
                                                 collapse_edges_box=box, split_welded_bands=True)["above"]
    on = run(_welded_page(), wide)
    assert len(on) == 1 and on[0] == pytest.approx(177.5, abs=1.5)
    # control: the same plateau against the head's own columns is a printed line through the head -> found
    on2 = run(_welded_page(), narrow)
    assert len(on2) == 2 and on2[1] == pytest.approx(161.5, abs=1.5)
    # control: a jutting plateau on the FAR side of the head's middle (its brim, a flag) is not a ledger
    on3 = run(_welded_page(row=136), narrow)
    assert len(on3) == 1
