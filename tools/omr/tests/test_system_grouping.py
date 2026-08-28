"""System grouping from vertical connectivity (tools/omr/system_grouping.py).

Synthetic pages: staves are five horizontal rules; a "barline" is a vertical
rule drawn through a run of staves, which is what the grouping reads.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tools.omr.staff_detector import detect_staves
from tools.omr.system_grouping import (
    GROUP_BOUNDARY_RATIO,
    assign_systems,
    gap_bridging_counts,
    _robust_x_window,
)
from tools.omr.types import PageImage, Staff

W, H = 1200, 1400
X0, X1 = 100, 1100
LINE_SPACING = 12


def _blank() -> np.ndarray:
    return np.full((H, W), 255, np.uint8)


def _draw_staff(img: np.ndarray, top: int, x0: int = X0, x1: int = X1) -> list[int]:
    ys = [top + LINE_SPACING * i for i in range(5)]
    for y in ys:
        img[y:y + 2, x0:x1] = 0
    return ys


def _draw_vrule(img: np.ndarray, x: int, y_top: int, y_bot: int, width: int = 3) -> None:
    img[y_top:y_bot, x:x + width] = 0


def _staves_from(line_groups: list[list[int]], x0: int = X0, x1: int = X1) -> list[Staff]:
    return [
        Staff(page_index=0, staff_index=i, line_ys=ys, x_start=x0, x_end=x1)
        for i, ys in enumerate(line_groups)
    ]


def _page(img: np.ndarray) -> PageImage:
    return PageImage(pdf_path=Path("synthetic.pdf"), page_index=0, dpi=300,
                     rgb=np.dstack([img] * 3), binary=img)


def _build(tops: list[int], rules: list[tuple[int, int]], n_rules: int = 6):
    """Draw staves at `tops`; draw `n_rules` vertical rules through each
    (first_staff, last_staff) span in `rules`. Returns (binary, staves)."""
    img = _blank()
    groups = [_draw_staff(img, t) for t in tops]
    for first, last in rules:
        y_top, y_bot = groups[first][0], groups[last][-1]
        for k in range(n_rules):
            _draw_vrule(img, X0 + 60 + k * 150, y_top, y_bot)
    return img, _staves_from(groups)


# ── gap_bridging_counts ─────────────────────────────────────────────────────

def test_bridging_counts_are_zero_across_a_system_break():
    # Two 2-staff systems; rules run through each system but not between them.
    img, staves = _build([100, 200, 500, 600], rules=[(0, 1), (2, 3)])
    counts = gap_bridging_counts(img, staves)
    assert len(counts) == 3
    assert counts[0] > 0, "gap inside system 1 is crossed"
    assert counts[1] == 0, "gap between the two systems is crossed by nothing"
    assert counts[2] > 0, "gap inside system 2 is crossed"


def test_bridging_counts_flag_degenerate_gaps_as_no_evidence():
    # Second staff overlaps the first: no gap band at all.
    img = _blank()
    groups = [_draw_staff(img, 100), _draw_staff(img, 130)]
    staves = _staves_from(groups)
    assert gap_bridging_counts(img, staves) == [-1]


def test_robust_x_window_ignores_a_broken_x_start():
    # Staff.x_start is the longest unbroken ink run, so a degraded scan can put
    # it far right (Beethoven 9 p60 staff 3: 885 against ~275 for neighbours).
    # The window is the median extent widened by WINDOW_MARGIN_SPACINGS, so it
    # must sit near 275/2485 and nowhere near the outlier.
    staves = _staves_from([[100 + LINE_SPACING * i] * 5 for i in range(5)])
    for s in staves:
        s.x_start, s.x_end = 275, 2485
    staves[2].x_start, staves[2].x_end = 885, 1826
    x0, x1 = _robust_x_window(staves)
    assert 200 < x0 <= 275, "outlier x_start must not drag the window right"
    assert 2485 <= x1 < 2560, "outlier x_end must not drag the window left"


def test_robust_x_window_reaches_past_the_staff_extent():
    """The bracket sits left of where the staff lines start and the closing
    barline right of where they end; a window clipped to the staff extent
    misses both (Beethoven 5 p10 at 600 dpi)."""
    staves = _staves_from([[100 + LINE_SPACING * i for i in range(5)]])
    staves[0].x_start, staves[0].x_end = 1000, 2000
    x0, x1 = _robust_x_window(staves)
    assert x0 < 1000 and x1 > 2000


# ── assign_systems ──────────────────────────────────────────────────────────

def test_two_systems_are_split():
    img, staves = _build([100, 200, 500, 600], rules=[(0, 1), (2, 3)])
    out, used = assign_systems(img, staves)
    assert used
    assert [s.system_index for s in out] == [0, 0, 1, 1]


def test_wide_bracket_group_gap_does_not_split_a_system():
    """The regression this module exists for: one system whose winds/brass/
    strings blocks are separated by gaps far larger than the intra-block gaps.
    The gap-size heuristic reports three systems; connectivity reports one."""
    tops = [100, 160, 220,        # block 1
            400, 460, 520,        # block 2 — 180px gap above, vs 60px within
            700, 760, 820]        # block 3
    img, staves = _build(tops, rules=[(0, 8)])
    out, used = assign_systems(img, staves)
    assert used
    assert {s.system_index for s in out} == {0}, "one bracket spans all nine staves"


def test_bracket_groups_are_recovered_within_a_system():
    """Barlines are drawn through every staff of a block but only the bracket
    crosses between blocks — so the between-block gaps bridge much less."""
    tops = [100, 160, 220, 400, 460, 520, 700, 760, 820]
    img = _blank()
    groups = [_draw_staff(img, t) for t in tops]
    # one full-height bracket for the whole system
    _draw_vrule(img, X0 + 20, groups[0][0], groups[-1][-1], width=4)
    # six barlines per block, not crossing between blocks
    for first, last in ((0, 2), (3, 5), (6, 8)):
        for k in range(6):
            _draw_vrule(img, X0 + 120 + k * 150, groups[first][0], groups[last][-1])
    staves = _staves_from(groups)
    out, used = assign_systems(img, staves)
    assert used
    assert {s.system_index for s in out} == {0}
    assert [s.group_index for s in out] == [0, 0, 0, 1, 1, 1, 2, 2, 2]


def test_falls_back_when_nothing_bridges_anywhere():
    """A page whose bracket and barlines are invisible: trusting connectivity
    would make every staff its own system, so the caller must fall back."""
    img = _blank()
    groups = [_draw_staff(img, t) for t in (100, 200, 300)]
    out, used = assign_systems(img, _staves_from(groups))
    assert not used, "no connectivity anywhere -> caller falls back to gap sizes"


def test_multi_column_layout_splits_regardless_of_connectivity():
    img, staves = _build([100, 200], rules=[(0, 1)])
    # Side-by-side columns: the two staves barely share any x range.
    staves[0].x_start, staves[0].x_end = 100, 560
    staves[1].x_start, staves[1].x_end = 640, 1100
    out, used = assign_systems(img, staves)
    assert used
    assert [s.system_index for s in out] == [0, 1]


def test_single_staff_page_is_one_system():
    img = _blank()
    staves = _staves_from([_draw_staff(img, 100)])
    out, used = assign_systems(img, staves)
    assert used
    assert [s.system_index for s in out] == [0]
    assert [s.group_index for s in out] == [0]


def test_staves_are_returned_sorted_by_y():
    img, staves = _build([100, 200, 500, 600], rules=[(0, 1), (2, 3)])
    shuffled = [staves[2], staves[0], staves[3], staves[1]]
    out, _used = assign_systems(img, shuffled)
    assert [s.top_y for s in out] == sorted(s.top_y for s in staves)


def test_group_index_defaults_to_zero_for_small_systems():
    img, staves = _build([100, 200], rules=[(0, 1)])
    out, _used = assign_systems(img, staves)
    assert [s.group_index for s in out] == [0, 0]


# ── end-to-end through detect_staves ────────────────────────────────────────

def test_detect_staves_uses_connectivity_grouping():
    tops = [100, 160, 220, 400, 460, 520, 700, 760, 820]
    img, _ = _build(tops, rules=[(0, 8)])
    pws = detect_staves(_page(img))
    assert len(pws.staves) == 9
    assert {s.system_index for s in pws.staves} == {0}


def test_detect_staves_misses_a_single_line_percussion_staff():
    """Documents a known limitation feeding contextual analysis item #1:
    `_group_into_staves` only accepts five-peak windows, so a one-line
    percussion staff is invisible — and every staff below it then carries a
    staff_index one lower than its true slot."""
    img = _blank()
    _draw_staff(img, 100)
    _draw_staff(img, 260)
    img[420:422, X0:X1] = 0          # one-line percussion staff
    _draw_staff(img, 560)
    pws = detect_staves(_page(img))
    tops = sorted(s.top_y for s in pws.staves)
    assert len(pws.staves) == 3, "the one-line staff is not detected"
    assert 420 not in tops
