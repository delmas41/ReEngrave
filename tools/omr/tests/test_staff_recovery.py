"""Unit tests for the comb pass that recovers lightly printed staves.

These build synthetic ink profiles rather than reading PDFs, so they run in
CI and pin the BEHAVIOUR rather than any particular page's numbers. The shapes
tested are the ones that actually occurred on Beethoven 5 p.10 — a page whose
wind staves print lightly enough to fall through the per-row ink gates while
the string staves below them clear those gates easily.
"""

from __future__ import annotations

import numpy as np
import pytest

from tools.omr.staff_detector import (
    STAFF_SPACING_OUTLIER_FACTOR,
    _comb_match_staves,
    _merge_staff_groups,
    _page_line_spacing,
    _reject_spacing_outliers,
)


def _profile(length: int, staves: list[tuple[int, float]], spacing: float = 16.0,
             baseline: float = 50.0) -> np.ndarray:
    """An ink profile with a 5-line staff at each (top_y, line_ink)."""
    prof = np.full(length, baseline, dtype=float)
    for top, ink in staves:
        for k in range(5):
            y = int(round(top + k * spacing))
            prof[y] = ink
    return prof


class TestPageLineSpacing:

    def test_median_of_group_spacings(self):
        groups = [[0, 16, 32, 48, 64], [100, 116, 132, 148, 164]]
        assert _page_line_spacing(groups) == pytest.approx(16.0)

    def test_empty_is_zero(self):
        assert _page_line_spacing([]) == 0.0

    def test_a_phantom_does_not_move_the_median(self):
        """The whole approach relies on phantoms being a minority."""
        real = [[i * 100, i * 100 + 16, i * 100 + 32, i * 100 + 48, i * 100 + 64]
                for i in range(6)]
        phantom = [0, 140, 280, 420, 560]
        assert _page_line_spacing(real + [phantom]) == pytest.approx(16.0)


class TestRejectSpacingOutliers:

    def test_drops_a_group_whose_spacing_is_a_multiple_of_the_page_s(self):
        real = [[0, 16, 32, 48, 64], [100, 116, 132, 148, 164]]
        phantom = [[0, 140, 280, 420, 560]]  # one line from each of five staves
        kept = _reject_spacing_outliers(real + phantom, 16.0)
        assert kept == real

    def test_keeps_smaller_staves(self):
        """Ossia and cue staves are smaller than the page's; only the HIGH side
        is a phantom signature."""
        main = [0, 16, 32, 48, 64]
        ossia = [200, 211, 222, 233, 244]  # spacing 11 — a real, smaller staff
        kept = _reject_spacing_outliers([main, ossia], 16.0)
        assert kept == [main, ossia]

    def test_boundary_is_the_documented_factor(self):
        main = [0, 16, 32, 48, 64]
        just_under = [200, 200 + 25, 200 + 50, 200 + 75, 200 + 100]  # 25 = 1.5625x
        just_over = [400, 400 + 26, 400 + 52, 400 + 78, 400 + 104]   # 26 = 1.625x
        kept = _reject_spacing_outliers([main, just_under, just_over], 16.0)
        assert just_under in kept
        assert just_over not in kept
        assert STAFF_SPACING_OUTLIER_FACTOR == 1.6

    def test_unknown_spacing_is_a_passthrough(self):
        groups = [[0, 140, 280, 420, 560]]
        assert _reject_spacing_outliers(groups, 0.0) == groups


class TestCombMatchStaves:

    def test_finds_a_lightly_printed_staff_beside_a_strong_one(self):
        """The Beethoven 5 shape: a faint staff the strict gates would miss,
        sitting above a strong one, at the same spacing."""
        prof = _profile(600, [(50, 300.0), (300, 1000.0)])
        found = _comb_match_staves(prof, page_width=1000, spacing=16.0,
                                   reference_ink=1000.0)
        tops = [g[0] for g in found]
        assert 50 in tops, "the faint staff should be recovered"
        assert 300 in tops

    def test_ink_far_below_the_gate_is_still_refused(self):
        """Recovery is not unconditional — the pool gate is a real floor."""
        prof = _profile(600, [(50, 100.0), (300, 1000.0)])
        found = _comb_match_staves(prof, page_width=1000, spacing=16.0,
                                   reference_ink=1000.0)
        assert [g[0] for g in found] == [300]

    def test_rows_not_at_the_page_spacing_are_not_a_staff(self):
        """Five evenly spaced rows at the WRONG pitch must not be accepted —
        this is what stops the comb from re-inventing the phantom."""
        prof = np.full(1000, 50.0)
        for k in range(5):
            prof[100 + k * 140] = 1000.0  # spacing 140, page spacing is 16
        found = _comb_match_staves(prof, page_width=1000, spacing=16.0,
                                   reference_ink=1000.0)
        assert found == []

    def test_staves_do_not_overlap_each_other(self):
        prof = _profile(900, [(50, 900.0), (200, 900.0), (350, 900.0)])
        found = _comb_match_staves(prof, page_width=1000, spacing=16.0,
                                   reference_ink=1000.0)
        for a, b in zip(found, found[1:]):
            assert a[-1] < b[0]

    def test_abstains_without_a_spacing(self):
        prof = _profile(600, [(50, 900.0)])
        assert _comb_match_staves(prof, 1000, 0.0, 1000.0) == []
        assert _comb_match_staves(prof, 1000, 16.0, 0.0) == []

    def test_tolerates_a_line_off_its_predicted_row(self):
        """Rasterisation and scan skew move lines a pixel or two."""
        prof = np.full(600, 50.0)
        for y in (100, 117, 132, 149, 164):  # nominal 16, wobbling +-1
            prof[y] = 900.0
        found = _comb_match_staves(prof, 1000, 16.0, 1000.0)
        assert len(found) == 1
        assert found[0][0] == 100


class TestMergeStaffGroups:

    def test_strict_wins_where_both_passes_see_a_staff(self):
        """The comb must not churn pages that already work."""
        strict = [[100, 116, 132, 148, 164]]
        comb = [[101, 117, 133, 149, 165]]  # same staff, one pixel off
        assert _merge_staff_groups(strict, comb) == strict

    def test_comb_is_added_where_strict_found_nothing(self):
        strict = [[300, 316, 332, 348, 364]]
        comb = [[50, 66, 82, 98, 114], [300, 316, 332, 348, 364]]
        merged = _merge_staff_groups(strict, comb)
        assert [g[0] for g in merged] == [50, 300]

    def test_result_is_sorted_down_the_page(self):
        strict = [[300, 316, 332, 348, 364]]
        comb = [[50, 66, 82, 98, 114], [600, 616, 632, 648, 664]]
        merged = _merge_staff_groups(strict, comb)
        assert [g[0] for g in merged] == sorted(g[0] for g in merged)
