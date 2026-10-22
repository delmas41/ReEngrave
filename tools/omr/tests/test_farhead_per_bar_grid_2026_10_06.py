"""lane-farhead-per-bar-grid (2026-10-06, Sean: staff lines recorded off the ink).

The far-head reader and the owner witness start from the staff's RAW lines, which sit off the ink by the
staff's tilt. The per-bar grid (what the in-staff positions use) is close to the ink. Synthetic page, spacing
20 px, five 4-px lines at rows 100-103, 120-123, ... 180-183 (centres 101.5 + 20k).
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate import far_head_owner as FO  # noqa: E402
from tools.omr.annotate import far_head_reader as FH  # noqa: E402

INK = [101.5 + 20 * k for k in range(5)]


def _page(lines=(0, 1, 2, 3, 4)):
    g = np.full((300, 400), 255, dtype=np.uint8)
    for k in lines:
        g[100 + 20 * k:104 + 20 * k, :] = 0
    return g


def _stats0():
    for k in FH.GRID_STATS:
        FH.GRID_STATS[k] = 0


def test_refinds_the_centre_of_the_run_not_its_top_row():
    _stats0()
    grid = [y + 2.0 for y in INK]                    # grid 2 px low of the ink
    out = FH.grid_lines_for_head(_page(), grid, 200, 227, 27)
    assert out == pytest.approx(INK, abs=0.01)       # the old reader returned the top row, 100.0 + 20k
    assert FH.GRID_STATS["refound"] == 5 and FH.GRID_STATS["from_grid_not_found"] == 0


def test_a_grid_line_farther_than_the_window_is_never_snapped_to_the_neighbour():
    _stats0()
    grid = [y + 13.0 for y in INK]                   # 0.65 sp off: the NEXT line is 7 px away, the own 13 px
    out = FH.grid_lines_for_head(_page(), grid, 200, 227, 27)
    assert out == pytest.approx(grid)                # kept at the grid, not moved one line over
    assert FH.GRID_STATS["from_grid_not_found"] == 5 and FH.GRID_STATS["refound"] == 0
    # the OLD re-find, handed the same lines, lands one line over (the failure this fixes)
    assert FH._darkest_row(_page(), 200, 227, int(grid[0] - 10), int(grid[0] + 10) + 1) == 120.0


def test_a_line_the_page_does_not_hold_uses_the_grid_and_is_counted():
    _stats0()
    page = _page(lines=(0, 1, 3, 4))                 # the middle line is not printed
    grid = [y + 1.0 for y in INK]
    out = FH.grid_lines_for_head(page, grid, 200, 227, 27)
    assert out[2] == pytest.approx(grid[2])
    assert out[0] == pytest.approx(INK[0], abs=0.01)
    assert FH.GRID_STATS["from_grid_not_found"] == 1 and FH.GRID_STATS["refound"] == 4


def test_two_found_lines_closer_than_half_a_space_go_back_to_the_grid():
    _stats0()
    g = np.full((300, 400), 255, dtype=np.uint8)
    g[100:104, :] = 0
    grid = [101.5, 106.0, 141.5, 161.5, 181.5]       # grid lines 0 and 1 only 0.2 sp apart: both windows hold line 0
    out = FH.grid_lines_for_head(g, grid, 200, 227, 27)
    assert out[0] == pytest.approx(grid[0]) and out[1] == pytest.approx(grid[1])
    assert FH.GRID_STATS["from_grid_pair"] == 2


def test_keyword_off_is_the_old_reader_bit_for_bit():
    page, lines = _page(), [y + 3.0 for y in INK]
    old = FH.local_staff_lines(page, lines, 200, 227, 27)
    FH.READER_KEYWORDS["per_bar_grid"] = False
    try:
        assert FH.frame_lines_for_head(page, lines, (200, 90, 227, 110)) == old
    finally:
        FH.READER_KEYWORDS["per_bar_grid"] = True


def test_cell_grid_page_lines_is_the_gather_grid_in_page_pixels():
    class C:
        staff_line_ys_canonical = [100, 200, 300, 400, 500]
        bbox_page_px = (50, 1000, 400, 1200)
        upscale_factor = 2.0
    assert FH.cell_grid_page_lines(C()) == [1050.0, 1100.0, 1150.0, 1200.0, 1250.0]
    C.staff_line_ys_canonical = []
    assert FH.cell_grid_page_lines(C()) is None


def test_owner_reads_the_neighbour_with_its_grid_in_the_heads_x_range():
    st = dict(key="n", lines=[0, 1, 2, 3, 4], x0=0, x1=100,
              grid=[(0, 50, [10, 11, 12, 13, 14]), (50, 100, [20, 21, 22, 23, 24])])
    assert list(FO.lines_at(st, 25.0)) == [10, 11, 12, 13, 14]
    assert list(FO.lines_at(st, 75.0)) == [20, 21, 22, 23, 24]
    assert list(FO.lines_at(st, 130.0)) == [20, 21, 22, 23, 24]      # nearest bar, never the raw lines
    assert list(FO.lines_at(dict(key="n", lines=[0, 1, 2, 3, 4]), 25.0)) == [0, 1, 2, 3, 4]


# --- the gather hands the reader the PER-BAR grid of the head's own bar --------------------------------------------
from tools.omr.tests import test_staged_far_head_ledger_2_56 as G  # noqa: E402


class _GridCell(G._Cell):
    """A cell whose stored grid is 3 px low of the staff-wide `line_ys` (the localized shift)."""
    def __init__(self):
        super().__init__()
        self.staff_line_ys_canonical = [y + 3.0 for y in G.LINES]


def _spy_run(cell, keyword):
    seen = {}

    class Spy(G._PooledPage):
        def read(self, subject, box, cls, global_lines):
            seen["lines"] = list(global_lines)
            return super().read(subject, box, cls, global_lines)

    gray, box = G._page(ledgers=True, head_pos=-4)
    log = G.Log()
    sub, g = G.R_cell(0, 0, 0, 0), G.R_glyph(0, 0, 0, 0, 0)
    log.observe(g, G.Q.NOTEHEAD_STAFF_POSITION, -4.0, reader="geometry", frame="cell:0", residual=0.0, rounded=-4)
    FH.READER_KEYWORDS["per_bar_grid"] = keyword
    try:
        with G.mock.patch.object(FH, "FarHeadPage", Spy):
            G.gather.gather_far_head_ledger_positions(log, G._Pws(gray), [cell], {0: (0, 0)},
                                                      {sub.to_key(): [G._Det(box)]}, None)
    finally:
        FH.READER_KEYWORDS["per_bar_grid"] = True
    return seen["lines"]


def test_gather_passes_the_bars_own_grid_not_the_staff_wide_lines():
    assert _spy_run(_GridCell(), True) == [y + 3.0 for y in G.LINES]


def test_gather_keyword_off_passes_the_raw_lines_as_before():
    assert _spy_run(_GridCell(), False) == [float(y) for y in G.LINES]


def test_a_cell_with_no_grid_falls_back_to_the_raw_lines_never_to_nothing():
    assert _spy_run(G._Cell(), True) == [float(y) for y in G.LINES]
