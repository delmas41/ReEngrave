"""A scoring instrument may not answer "I could not find that page" with a ZERO.

⚠️⚠️ THE DEFECT, found 2026-09-22 by the engraved-staged lane and confirmed
against the tree: `score_reading.report()` took a `page_index` and used it
POSITIONALLY on both sides, while `transcribe --pages 2` returns a ONE-element
`pages` list carrying `page_index: 2` INSIDE it. So `detections_in_page_px`
returned `[]`, `staff_space_px` returned **1.0**, and every family printed
truth N / pred 0 / F1 0.000 — **a complete table of zeros that reads as a
recognition catastrophe rather than as a lookup that missed.**

⚠️ It never showed because every fixture the reading lane uses is `--pages 0`,
where list position and page index coincide. That is *a test named for a hazard
it does not reach*, arriving as a whole benchmark's worth of fixtures.

This is the `A fallback must never convert "cannot tell" into a definite
answer` family, in its worst form: the definite answer is a SCORE.
"""
from __future__ import annotations

import unittest

from tools.omr import score_reading as SR


def _result(page_index, spacing=20.0, n_dets=1):
    """The shape `transcribe --pages N` actually returns: ONE page in the list,
    carrying its true `page_index` inside it."""
    # ⚠️ The keys are `detections_in_page_px`'s OWN, read off that function
    # rather than guessed: a detection carries `bbox` in the CELL frame, and
    # the measure carries `bbox_page_px` + `upscale_factor` to convert it. A
    # fixture that does not match the reader tests the fixture.
    dets = [{"class": "noteheadBlackOnLine", "category": "notehead",
             "bbox": [10.0, 20.0, 30.0, 40.0], "confidence": 0.9}
            for _ in range(n_dets)]
    return {"pages": [{
        "page_index": page_index,
        "systems": [{"staves": [{
            "staff_geometry": {"line_spacing_px": spacing},
            "measures": [{"bbox_page_px": [100.0, 200.0, 500.0, 400.0],
                          "upscale_factor": 4.0,
                          "detections": dets}],
        }]}],
    }]}


class TestThePageIsFoundByItsOwnIndexNotByListPosition(unittest.TestCase):

    def test_a_single_page_result_for_page_2_is_found(self):
        page = SR._page_of(_result(2), 2)
        self.assertEqual(page["page_index"], 2)

    def test_detections_are_returned_for_that_page(self):
        """⚠️ THE ASSERTION THAT WOULD HAVE CAUGHT IT. Under the old
        positional lookup this list was EMPTY and nothing raised."""
        dets = SR.detections_in_page_px(_result(2, n_dets=3), 2)
        self.assertEqual(len(dets), 3)

    def test_the_staff_space_is_the_measured_one_not_1_0(self):
        """⚠️ 1.0 px would silently rescale every staff-space tolerance by
        ~20x, so a tolerance of 0.5 spaces becomes half a PIXEL."""
        self.assertEqual(SR.staff_space_px(_result(2, spacing=20.0), 2), 20.0)


class TestItRefusesRatherThanScoringZero(unittest.TestCase):

    def test_an_absent_page_RAISES_in_detections(self):
        with self.assertRaises(KeyError):
            SR.detections_in_page_px(_result(2), 0)

    def test_an_absent_page_RAISES_in_staff_space(self):
        with self.assertRaises(KeyError):
            SR.staff_space_px(_result(2), 0)

    def test_the_refusal_NAMES_what_the_result_does_hold(self):
        """A refusal a reader cannot act on sends them to the wrong file."""
        with self.assertRaises(KeyError) as cm:
            SR._page_of(_result(2), 0)
        self.assertIn("[2]", str(cm.exception))

    def test_a_page_with_no_staff_spacing_RAISES_rather_than_returning_1_0(self):
        r = {"pages": [{"page_index": 0,
                        "systems": [{"staves": [{"staff_geometry": {}}]}]}]}
        with self.assertRaises(ValueError):
            SR.staff_space_px(r, 0)


class TestPageZeroIsUnchanged(unittest.TestCase):
    """⚠️ THE CONTROL. Every committed figure in
    `benchmarks/omr-reading-vs-reproduction-2026-09` was taken at `--pages 0`,
    where the two lookups agree — so the repair must leave that case alone, or
    it silently rewrites published numbers."""

    def test_page_zero_still_resolves_and_still_measures(self):
        r = _result(0, spacing=33.0, n_dets=2)
        self.assertEqual(len(SR.detections_in_page_px(r, 0)), 2)
        self.assertEqual(SR.staff_space_px(r, 0), 33.0)


if __name__ == "__main__":
    unittest.main()
