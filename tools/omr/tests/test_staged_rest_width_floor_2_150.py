"""ROADMAP 2.150 -- a rest is as wide as its glyph: a `restQuarter` box far narrower than a quarter rest is not one.

STAGED ADJUDICATE `family_precision.adjudicate_rest_is_not_a_rest`, reason `rest_narrower_than_its_class`, flag
`OMR_REST_WIDTH_FLOOR` (default OFF; only `1/true/yes/on` enables).

CONVENTION ASSUMED: a quarter rest is printed about one staff space wide (SMuFL Bravura `restQuarter` 1.08 spaces;
Brahms 317803 kept boxes median 1.14, Litolff 984073 1.16); a stem is ~0.1-0.15 of a space. WHAT WOULD FALSIFY IT: a
print-confirmed quarter rest whose box is under 0.7 spaces wide. NOT CONFIRMED: by Sean (blind tiles
`out/print/2.150-review/`).

RED first: on main the reason is undeclared and the rule does not exist, so the refusal tests come back
`value=False, reason="rest"`. Every refusal test has a control in the same class that can fail.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import margins
from tools.omr.staged.record import Log, Outcome, Q
from tools.omr.tests.test_staged_family_refusals import _box, _page_box_at_step, _staff_geometry
from tools.omr.tests.test_staged_rest_placement_2_33 import _run

ON = {"OMR_REST_WIDTH_FLOOR": "1"}


def _decide(cls, w_c, env, *, geometry=True):
    """One rest box of canonical width `w_c` (the cell's staff space is 100 canonical px), 300 tall, centred on
    the middle line, alone in its cell."""
    log = Log()
    if geometry:
        _staff_geometry(log)
    g = _box(log, 0, cls, quantity=Q.REST, page_box=_page_box_at_step(4.0, x0=500.0, x1=500.0 + w_c / 5.0,
                                                                         thickness=60.0),
             w_c=w_c, h_c=300.0, x_c=200.0, y_c=100.0)
    with mock.patch.dict(os.environ, env, clear=False):
        if not env:
            os.environ.pop("OMR_REST_WIDTH_FLOOR", None)
        _run(log, Q.REST_IS_NOT_A_REST)
    return log.verdict(Q.REST_IS_NOT_A_REST, g)


class TestRestWidthFloor(unittest.TestCase):

    def test_a_stem_wide_quarter_rest_box_is_refused(self):
        v = _decide("restQuarter", 45.0, ON)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_narrower_than_its_class")
        # margin = floor - width (staff spaces), positive inside the refusal (2.106)
        self.assertAlmostEqual(v.margin, 0.7 - 0.45, places=3)
        self.assertEqual(v.detail["width_floor"]["width_spaces"], 0.45)

    def test_CONTROL_a_quarter_rest_wide_box_is_kept(self):
        v = _decide("restQuarter", 110.0, ON)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")
        # the measurement rides on the kept verdict too (a refusal says how close it came)
        self.assertAlmostEqual(v.detail["width_floor"]["margin"], 0.7 - 1.1, places=3)

    def test_CONTROL_just_above_the_floor_is_kept(self):
        v = _decide("restQuarter", 72.0, ON)
        self.assertIs(v.value, False)

    def test_CONTROL_flag_off_keeps_the_narrow_box(self):
        v = _decide("restQuarter", 45.0, {})
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_CONTROL_an_off_word_keeps_the_narrow_box(self):
        v = _decide("restQuarter", 45.0, {"OMR_REST_WIDTH_FLOOR": "off"})
        self.assertIs(v.value, False)

    def test_CONTROL_eighth_rests_have_no_floor(self):
        """Measured: Breitkopf prints eighth rests whose boxes are 0.6 spaces wide (2 of 13 narrow `rest8th` boxes
        on Brahms are real rests), so width does not separate them from wedges/stems; no floor is set."""
        v = _decide("rest8th", 45.0, ON)
        self.assertIs(v.value, False)

    def test_CONTROL_no_staff_space_declines(self):
        """No cell staff space: no width in spaces can be measured; the rule declines (rule 8), never refuses."""
        v = _decide("restQuarter", 45.0, ON, geometry=False)
        self.assertNotEqual(v.reason, "rest_narrower_than_its_class")

    def test_the_reason_is_classified_in_the_margin_registry(self):
        problems, _notes = margins.check_margins()
        self.assertFalse([p for p in problems if "rest_narrower_than_its_class" in str(p)], problems)
        self.assertIn("rest_narrower_than_its_class", margins.PARTIAL["adjudicate_rest_is_not_a_rest"])


if __name__ == "__main__":
    unittest.main()
