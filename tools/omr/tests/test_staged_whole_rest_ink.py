"""`notehead_is_a_whole_rest`: a PITCHED NOTE where the page prints SILENCE.

⚠️ Sean, 2026-09-11, reading the cleanup artefact against the print: *"in bars
where it should be just whole note rest in two four. It's showing an actual
quarter note, not a quarter note rest."*

⚠️ THE REFUSALS ARE THE TESTS THAT MATTER AND THEY CARRY THEIR POSITIVE
CONTROL IN THE SAME CLASS. A battery of refusal tests passes by refusing
everything; every refusal below sits beside an input that is ACCEPTED, and
`TestOneWitnessIsNeverEnough` exists because the whole design claim is that
SHAPE alone and POSITION alone are each inadmissible.

⚠️ The staff geometry in these fixtures is chosen so a staff space is 20 page
px and the bottom line is y=400, i.e. lines at 400/380/360/340/320 going up.
Step 5.5 -- where a whole rest hangs -- is then y = 400 - 5.5*10 = 345.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm as RH
from tools.omr.staged.record import Log, Q, READERS

SPACING = 20.0
BOTTOM = 400.0


def _y_of_step(step):
    return BOTTOM - step * (SPACING / 2.0)


def _staff(log, staff_i=0, *, spacing=SPACING, lines=True):
    s = R.staff(0, 0, staff_i)
    if lines:
        log.observe(s, Q.STAFF_LINES, [BOTTOM - i * spacing for i in range(5)],
                    reader=READERS.GEOMETRY, frame=G.FRAME_PAGE)
    if spacing is not None:
        log.observe(s, Q.STAFF_SPACING, spacing,
                    reader=READERS.GEOMETRY, frame=G.FRAME_PAGE)
    return s


def _head(log, *, step, w_sp, h_sp, staff_i=0, cell=0, gi=0,
          cls="noteheadBlackInSpace", page=True, x=1000.0):
    """One notehead-classed glyph of a given SHAPE at a given STAFF STEP.

    ⚠️ `x` is 1000 and not 0 deliberately: at the origin a CORNER box and a
    WIDTH box agree in every coordinate, which is how a frame error walked
    past a whole mutation battery on the arc work.
    """
    g = R.glyph(0, 0, staff_i, cell, gi)
    w, h = w_sp * SPACING, h_sp * SPACING
    cy = _y_of_step(step)
    detail = dict(category="notehead")
    if page:
        detail.update(bbox_page_px=[x, cy - h / 2.0, x + w, cy + h / 2.0],
                      x_center_page=x + w / 2.0, y_center_page=cy)
    log.observe(g, Q.GLYPH_BOX, (cls, x, cy - h / 2.0, w, h),
                reader=READERS.DETECTOR, frame=f"cell:{cell}", score=0.3,
                **detail)
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR,
                frame=f"cell:{cell}", score=0.3)
    return g


def _decide(log, subject):
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.NOTEHEAD_IS_A_WHOLE_REST, subject)


# The measured whole rest of the artefact: 0.73-0.79 spaces tall,
# 1.49-1.75 wide, aspect ~2.0, hanging at step ~5.0-5.2.
REST_SHAPE = dict(w_sp=1.55, h_sp=0.75)
NOTE_SHAPE = dict(w_sp=1.50, h_sp=1.31)


class TestItDecides(unittest.TestCase):
    def test_the_registry_says_it_decides(self):
        self.assertFalse(adjudicate.REGISTRY[Q.NOTEHEAD_IS_A_WHOLE_REST].stub)

    def test_rest_shaped_ink_at_the_rest_slot_is_a_whole_rest(self):
        log = Log()
        _staff(log)
        g = _head(log, step=5.5, **REST_SHAPE)
        v = _decide(log, g)
        self.assertEqual(v.outcome, R.Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "shape_and_position_agree")

    def test_it_records_what_it_measured(self):
        """⚠️ A verdict that does not carry its own measurement cannot be
        audited against a crop, which is the only way this rule was checked."""
        log = Log()
        _staff(log)
        g = _head(log, step=5.5, **REST_SHAPE)
        d = _decide(log, g).detail
        self.assertAlmostEqual(d["height_spaces"], 0.75, places=2)
        self.assertAlmostEqual(d["aspect"], 1.55 / 0.75, places=2)
        self.assertAlmostEqual(d["staff_step"], 5.5, places=2)

    def test_an_ordinary_notehead_at_the_same_place_is_not(self):
        """The POSITIVE CONTROL for every refusal below: step 5.5 is C5/D5 in
        treble and perfectly ordinary music."""
        log = Log()
        _staff(log)
        g = _head(log, step=5.5, **NOTE_SHAPE)
        v = _decide(log, g)
        self.assertEqual(v.outcome, R.Outcome.DECIDED)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "not_rest_shaped")


class TestOneWitnessIsNeverEnough(unittest.TestCase):
    """⚠️ THE DESIGN CLAIM, asserted rather than described. Shape alone flags
    174 of 2,347 real noteheads on the measured pages and position alone 310;
    only the agreement is evidence."""

    def test_rest_shaped_ink_away_from_the_slot_is_refused(self):
        log = Log()
        _staff(log)
        # A beam fragment or a bled notehead in the middle of the staff.
        g = _head(log, step=2.0, **REST_SHAPE)
        v = _decide(log, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "not_at_the_rest_position")

    def test_rest_shaped_ink_above_the_staff_is_refused(self):
        log = Log()
        _staff(log)
        g = _head(log, step=15.0, **REST_SHAPE)
        self.assertIs(_decide(log, g).value, False)

    def test_the_half_rest_slot_is_outside_the_tolerance(self):
        """A HALF rest sits ON the middle line, centre step 4.5 -- one full
        step below the whole rest's 5.5 and just outside the window. This
        decision claims to name a WHOLE rest and may not quietly cover both."""
        log = Log()
        _staff(log)
        g = _head(log, step=4.4, **REST_SHAPE)
        self.assertIs(_decide(log, g).value, False)


class TestTheAspectIsBoundedBothWays(unittest.TestCase):
    def test_a_long_bar_of_ink_is_not_claimed_as_a_whole_rest(self):
        """⚠️ MEASURED, AND IT COSTS ONE REAL CATCH. One glyph on the artefact
        is squat, in the slot, and aspect 5.49 -- a beam or staff-line residue,
        certainly not a notehead and certainly not a whole rest either. It is
        refused rather than claimed: the 19 genuine catches top out at 2.352,
        so the bound stands in an empty interval."""
        log = Log()
        _staff(log)
        g = _head(log, step=5.5, w_sp=4.1, h_sp=0.75)   # aspect 5.47
        v = _decide(log, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "not_rest_shaped")

    def test_the_upper_bound_sits_above_every_real_catch(self):
        self.assertGreater(RH.WHOLE_REST_INK_MAX_ASPECT, 2.352)
        self.assertLess(RH.WHOLE_REST_INK_MAX_ASPECT, 5.49)

    def test_a_tall_glyph_is_refused_however_wide(self):
        log = Log()
        _staff(log)
        g = _head(log, step=5.5, w_sp=2.4, h_sp=1.2)   # aspect 2.0, too tall
        self.assertIs(_decide(log, g).value, False)


class TestItAbstainsRatherThanGuessing(unittest.TestCase):
    def test_no_page_frame_abstains(self):
        """⚠️ The CANONICAL frame cannot answer a question about the staff's
        own lines -- two staves' canonical frames coincide by construction,
        which is the fault `Q.ONSET_COLUMN` paid for."""
        log = Log()
        _staff(log)
        g = _head(log, step=5.5, page=False, **REST_SHAPE)
        v = _decide(log, g)
        self.assertEqual(v.outcome, R.Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_page_frame")

    def test_no_staff_lines_abstains(self):
        log = Log()
        _staff(log, lines=False)
        g = _head(log, step=5.5, **REST_SHAPE)
        v = _decide(log, g)
        self.assertEqual(v.outcome, R.Outcome.ABSTAINED)
        self.assertEqual(v.reason, R.ABSTAIN.NO_STAFF_GEOMETRY)

    def test_it_still_decides_when_the_geometry_is_there(self):
        """The positive control for the two abstentions above."""
        log = Log()
        _staff(log)
        g = _head(log, step=5.5, **REST_SHAPE)
        self.assertEqual(_decide(log, g).outcome, R.Outcome.DECIDED)


class TestItIsScaleInvariant(unittest.TestCase):
    """⚠️ STAFF SPACES, NEVER PIXELS. The staves of one plate differ in
    spacing and the DPI differs between runs, so the same ink at a different
    scale must give the same answer -- a pixel constant would make this rule a
    property of one render of one page."""

    def test_the_same_ink_at_half_the_scale_decides_the_same(self):
        answers = set()
        for spacing in (10.0, 20.0, 41.25):
            log = Log()
            s = R.staff(0, 0, 0)
            log.observe(s, Q.STAFF_LINES,
                        [BOTTOM - i * spacing for i in range(5)],
                        reader=READERS.GEOMETRY, frame=G.FRAME_PAGE)
            log.observe(s, Q.STAFF_SPACING, spacing,
                        reader=READERS.GEOMETRY, frame=G.FRAME_PAGE)
            g = R.glyph(0, 0, 0, 0, 0)
            w, h = 1.55 * spacing, 0.75 * spacing
            cy = BOTTOM - 5.5 * (spacing / 2.0)
            log.observe(g, Q.GLYPH_BOX,
                        ("noteheadBlackInSpace", 1000.0, cy - h / 2, w, h),
                        reader=READERS.DETECTOR, frame="cell:0", score=0.3,
                        category="notehead",
                        bbox_page_px=[1000.0, cy - h / 2, 1000.0 + w, cy + h / 2])
            log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlackInSpace",
                        reader=READERS.DETECTOR, frame="cell:0", score=0.3)
            answers.add(_decide(log, g).value)
        self.assertEqual(answers, {True})


class TestTheConstantsAreWhereTheMeasurementPutThem(unittest.TestCase):
    """⚠️ Not a restatement of the numbers -- an assertion of the ORDERING the
    measurement established, so a sweep that breaks it fails even when every
    behavioural test above still passes."""

    def test_the_rest_slot_is_the_engraving_convention(self):
        self.assertEqual(RH.WHOLE_REST_STEP, 5.5)

    def test_a_whole_rest_is_shorter_than_a_notehead(self):
        # measured medians: rest 0.67 spaces, notehead 1.31
        self.assertLess(RH.WHOLE_REST_INK_MAX_HEIGHT_SPACES, 1.31)
        self.assertGreater(RH.WHOLE_REST_INK_MAX_HEIGHT_SPACES, 0.67)

    def test_the_aspect_floor_is_above_a_noteheads_median(self):
        self.assertGreater(RH.WHOLE_REST_INK_MIN_ASPECT, 1.14)
        self.assertLess(RH.WHOLE_REST_INK_MIN_ASPECT, 2.17)

    def test_the_tolerance_is_scan_wander_not_a_free_parameter(self):
        """8-17 page px of tilt on this plate is 0.2-0.4 staff spaces, i.e.
        0.4-0.8 of a step. More than two steps would swallow the half-rest
        slot and the line below it."""
        self.assertLessEqual(RH.WHOLE_REST_STEP_TOLERANCE, 1.25)


if __name__ == "__main__":
    unittest.main()
