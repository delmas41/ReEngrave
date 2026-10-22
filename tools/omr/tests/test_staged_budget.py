"""`tools/omr/staged/budget.py` — ROADMAP 1.2b's 2026-09-28 recalibration.

The module used to ship with ONE pre-1.2 Litolff data point
(~623 s/page post-GATHER, "the 09-22 run") that OVER-REFUSED: scaled to a
27-page Brahms job it priced ~21 hours against the 14-hour default budget,
and that job (`benchmarks/acceptance/manifest.json`) actually ran in
1 h 11 m alone and 2 h 29 m 30 s under heavy overnight contention.

These tests assert the NEW DERIVATION — the module's own named 2026-09-28
data points (driver-log brackets for the Litolff and Brahms whole-movement
re-gathers, commit `c19cbca7`) recomputed here independently and compared
against what the module exports — rather than pinning a magic number that
the next recalibration would have to hunt down and edit by hand (CLAUDE.md
rule 9: derive, don't restate). CLAUDE.md rule 7: a control must be able to
fail — `test_the_old_pre_1_2_constant_would_have_refused_this_job` is the
positive control proving the recalibration actually matters, not a test
that would have passed either way.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import budget


class TestGatherConstantsUnchanged(unittest.TestCase):
    """1.2's fixes targeted ADJUDICATE/EVALUATE/INFER, not GATHER — the
    recalibration must not have touched this half."""

    def test_with_gate_is_93_s_per_page(self):
        self.assertEqual(budget.GATHER_S_PER_PAGE_WITH_DIRECTION_GATE, 93.0)

    def test_without_gate_adds_the_measured_direction_reader_cost(self):
        self.assertEqual(
            budget.GATHER_S_PER_PAGE_WITHOUT_DIRECTION_GATE,
            budget.GATHER_S_PER_PAGE_WITH_DIRECTION_GATE
            + budget.DIRECTION_READER_S_PER_PAGE)


class TestPostGatherIsDerivedNotHardcoded(unittest.TestCase):
    """Recompute the 2026-09-28 derivation from the module's OWN named data
    points (driver-log wall brackets + page counts) and check the exported
    constant matches — so a future edit to the formula, or to a data point,
    that forgets to update the other is caught here rather than shipping
    silently."""

    def test_post_gather_upper_bound_is_the_slower_documents_own_rate(self):
        litolff_rate = ((budget._LITOLFF_20260928_WALL_S
                         / budget._LITOLFF_20260928_PAGES)
                        - budget.GATHER_S_PER_PAGE_WITH_DIRECTION_GATE)
        brahms_rate = ((budget._BRAHMS_20260928_WALL_S
                       / budget._BRAHMS_20260928_PAGES)
                      - budget.GATHER_S_PER_PAGE_WITH_DIRECTION_GATE)
        self.assertAlmostEqual(
            budget._LITOLFF_20260928_POST_GATHER_S_PER_PAGE, litolff_rate)
        self.assertAlmostEqual(
            budget._BRAHMS_20260928_POST_GATHER_S_PER_PAGE, brahms_rate)
        # Brahms is the denser, contention-slowed document -- it must be the
        # one the upper bound is taken from ("take the slower document per
        # page", this item's brief), not Litolff.
        self.assertGreater(brahms_rate, litolff_rate)
        self.assertAlmostEqual(
            budget.POST_GATHER_S_PER_PAGE_UPPER_BOUND, brahms_rate)

    def test_data_points_are_named_documents_not_bare_numbers(self):
        # The whole reason this module carries named constants instead of a
        # single opaque float: a reader (or a future recalibration) can see
        # WHICH runs it came from. Page counts must match the manifest.
        self.assertEqual(budget._LITOLFF_20260928_PAGES, 16)
        self.assertEqual(budget._BRAHMS_20260928_PAGES, 27)


class TestBrahmsWholeMovementNoLongerOverRefuses(unittest.TestCase):
    """The exact scenario this item's brief names: a 27-page Brahms
    whole-movement web job must come in under the 14 h default budget
    (`backend.core.config.Settings.omr_job_budget_s`, 50400 s) now."""

    def test_27_page_brahms_estimate_is_under_the_14h_default_budget(self):
        est = budget.estimate_job_budget_s(27)
        self.assertLess(est["total_s_expected"], 14 * 3600.0)
        # Not just barely -- the recalibrated expected figure should land
        # close to what the document actually measured (2 h 29 m 30 s),
        # not merely "somewhere under 14 h" by luck.
        self.assertLess(est["total_s_expected"], 4 * 3600.0)

    def test_the_old_pre_1_2_constant_would_have_refused_this_job(self):
        """CLAUDE.md rule 7 — a control must be able to fail. Recomputes
        the SUPERSEDED 09-22 Litolff-only figure (12.3 h post-GATHER over 16
        pages, single core, pre-1.2) the way the old module did, and checks
        it prices 27 Brahms pages OVER the 14 h budget -- proving this
        test suite would have caught the over-refusal this item's brief
        describes, not just rubber-stamped whatever number is in the file."""
        old_post_gather_s_per_page = (12.3 * 3600.0) / 16
        old_total_s = (27 * budget.GATHER_S_PER_PAGE_WITH_DIRECTION_GATE
                      + 27 * old_post_gather_s_per_page)
        self.assertGreater(old_total_s, 14 * 3600.0)


class TestEstimateJobBudgetSSanity(unittest.TestCase):
    """Behavioural properties any recalibration must preserve."""

    def test_zero_pages_is_zero_cost(self):
        est = budget.estimate_job_budget_s(0)
        self.assertEqual(est["total_s_expected"], 0.0)
        self.assertEqual(est["total_s_upper_bound"], 0.0)

    def test_more_pages_cost_more(self):
        small = budget.estimate_job_budget_s(1)
        large = budget.estimate_job_budget_s(100)
        self.assertGreater(large["total_s_expected"], small["total_s_expected"])

    def test_negative_pages_raises(self):
        with self.assertRaises(ValueError):
            budget.estimate_job_budget_s(-1)

    def test_caveat_and_data_point_are_always_present(self):
        est = budget.estimate_job_budget_s(5)
        self.assertIn("computation", est["caveat"])
        self.assertIn("c19cbca7", est["data_point"])


if __name__ == "__main__":
    unittest.main()
