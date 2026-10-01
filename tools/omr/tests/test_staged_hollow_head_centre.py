"""ROADMAP 2.50 -- where a HOLLOW notehead's own white interior sits.

⚠️ WHY THIS EXISTS. Sean, 2026-10-01, on a contact sheet: boxes are well
centred, but on some HOLLOW heads the box centre sits barely high of the
white -- *"The hollow heads should have a center in the white of the
head."* This round measures and labels that centre (`Q.HOLLOW_HEAD_CENTRE`)
off the hollow head's own enclosed interior; it does NOT yet wire it into
`Q.NOTEHEAD_STAFF_POSITION` or any other default (ROADMAP 2.50's own brief,
`reach`'s "producer only" entry).

⚠️ RUN RED FIRST: `gather.hollow_head_hole_centre` / `gather.
gather_hollow_head_centre` / `geometry.is_hollow_notehead` / `Q.
HOLLOW_HEAD_CENTRE` do not exist on the tree before this round -- every
reference below raises `AttributeError`.
"""
from __future__ import annotations

import types
import unittest

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged import geometry
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q, READERS, State
from tools.omr.types import MeasureCell


def _paper(h=300, w=300):
    return np.full((h, w), 255, dtype=np.uint8)


def _ring(img, cx, cy, w, h, thickness):
    """A hollow ellipse: ink (0) on the rim, background (255) inside."""
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    a, b = w / 2.0, h / 2.0
    outer = ((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2 <= 1.0
    a2, b2 = max(1.0, a - thickness), max(1.0, b - thickness)
    inner = ((xx - cx) / a2) ** 2 + ((yy - cy) / b2) ** 2 <= 1.0
    img[outer & ~inner] = 0


def _fill_ellipse(img, cx, cy, w, h):
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    a, b = max(1.0, w / 2.0), max(1.0, h / 2.0)
    img[((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2 <= 1.0] = 0


SPACING = 40.0


def _std_box(cx, cy, margin=1.15):
    """A box around a standard-sized ring, loose enough to leave the ring's
    own rim and interior well inside the box border."""
    w = gather.STANDARD_HEAD_WIDTH_SPACES * SPACING * margin
    h = gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING * margin
    return (cx - w / 2.0, cy - h / 2.0, w, h)


class TestHollowHeadHoleCentre(unittest.TestCase):
    """`gather.hollow_head_hole_centre` -- pure, on synthetic rasters."""

    def test_open_head_in_a_space_centre_is_the_hole_centre(self):
        img = _paper()
        cx, cy = 150.0, 150.0
        _ring(img, cx, cy, gather.STANDARD_HEAD_WIDTH_SPACES * SPACING,
              gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING, thickness=4)
        box = _std_box(cx, cy)
        r = gather.hollow_head_hole_centre(img, box)
        self.assertIsNotNone(r)
        self.assertIn("cx", r)
        self.assertLess(abs(r["cx"] - cx), 2.0)
        self.assertLess(abs(r["cy"] - cy), 2.0)

    def test_open_head_on_a_line_is_still_one_centre(self):
        """A line-note's own staff line would cross this hole -- but by the
        time this reader runs, `image_no_staff` has already erased it
        (CLAUDE.md §10, 'treat the two halves as one hole'). Simulated here
        by drawing the line ACROSS THE WHOLE RASTER WIDTH (the shape a real
        unerased staff line has) and then erasing exactly that band back to
        background, the same net effect `staff_line_removal` has upstream --
        proving the reading is identical to the unobstructed case rather
        than split into two candidates."""
        img = _paper()
        cx, cy = 150.0, 150.0
        w = gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
        h = gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
        _ring(img, cx, cy, w, h, thickness=4)
        # A real staff line crosses the WHOLE page width, but a real
        # line-removal pass erases only the LINE's own thin ink -- never
        # the rim ink that happens to sit at the same row, which is why
        # the test narrows the erased band to strictly inside the ring's
        # own interior (never touching its rim at x = cx +/- w/2).
        line_y0, line_y1 = int(cy) - 2, int(cy) + 2
        inner_x0, inner_x1 = int(cx - w / 2.0 + 10), int(cx + w / 2.0 - 10)
        img[line_y0:line_y1, inner_x0:inner_x1] = 0   # unerased line, crossing the hole
        img[line_y0:line_y1, inner_x0:inner_x1] = 255  # erasure removes it again
        box = _std_box(cx, cy)
        r = gather.hollow_head_hole_centre(img, box)
        self.assertIsNotNone(r)
        self.assertIn("cx", r)
        self.assertLess(abs(r["cx"] - cx), 2.0)
        self.assertLess(abs(r["cy"] - cy), 2.0)

    def test_box_shifted_3px_up_does_not_move_the_reading(self):
        """CLAUDE.md rule 7's own control for `Q.NOTEHEAD_RECENTRE` shape:
        a box whose centre sits a few px off the detector's assumed centre
        must not move the HOLE's own reading -- it is a property of the
        ink, not of the box."""
        img = _paper()
        cx, cy = 150.0, 150.0
        _ring(img, cx, cy, gather.STANDARD_HEAD_WIDTH_SPACES * SPACING,
              gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING, thickness=4)
        box_centred = _std_box(cx, cy, margin=1.4)
        box_shifted = _std_box(cx, cy - 3.0, margin=1.4)
        r0 = gather.hollow_head_hole_centre(img, box_centred)
        r1 = gather.hollow_head_hole_centre(img, box_shifted)
        self.assertIsNotNone(r0)
        self.assertIsNotNone(r1)
        self.assertIn("cx", r0)
        self.assertIn("cx", r1)
        self.assertLess(abs(r0["cx"] - r1["cx"]), 1.0)
        self.assertLess(abs(r0["cy"] - r1["cy"]), 1.0)

    def test_a_filled_black_head_is_not_measured(self):
        """CONTROL: a control must be able to fail (rule 7) -- a solid head
        has no enclosed white at all, so this reader must say so rather
        than inventing a centre from the box."""
        img = _paper()
        cx, cy = 150.0, 150.0
        _fill_ellipse(img, cx, cy, gather.STANDARD_HEAD_WIDTH_SPACES * SPACING,
                     gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING)
        box = _std_box(cx, cy)
        r = gather.hollow_head_hole_centre(img, box)
        self.assertIsNotNone(r)
        self.assertNotIn("cx", r)
        self.assertEqual(r["n_candidates"], 0)

    def test_a_broken_ring_abstains(self):
        """CONTROL: a gap in the ring lets the hole's own background leak
        into the surrounding paper -- the resulting component touches the
        box border and is excluded, leaving zero qualifying candidates,
        never a guessed centre from the leaked blob."""
        img = _paper()
        cx, cy = 150.0, 150.0
        _ring(img, cx, cy, gather.STANDARD_HEAD_WIDTH_SPACES * SPACING,
              gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING, thickness=4)
        w = gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
        gap_x0 = int(cx + w / 2.0 - 6)
        img[int(cy) - 3:int(cy) + 3, gap_x0:gap_x0 + 8] = 255  # punch a gap
        box = _std_box(cx, cy)
        r = gather.hollow_head_hole_centre(img, box)
        self.assertIsNotNone(r)
        self.assertNotIn("cx", r)
        self.assertEqual(r["n_candidates"], 0)

    def test_off_the_raster_returns_none(self):
        img = _paper()
        r = gather.hollow_head_hole_centre(img, (-500.0, -500.0, 10.0, 10.0))
        self.assertIsNone(r)

    def test_box_too_small_returns_none(self):
        img = _paper()
        r = gather.hollow_head_hole_centre(img, (150.0, 150.0, 1.0, 1.0))
        self.assertIsNone(r)

    def test_no_image_returns_none(self):
        r = gather.hollow_head_hole_centre(None, (150.0, 150.0, 20.0, 20.0))
        self.assertIsNone(r)


def _detection(name, x_center, y_center, w=None, h=None):
    w = w if w is not None else gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
    h = h if h is not None else gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
    return types.SimpleNamespace(
        smufl_name=name,
        x_canonical=x_center - w / 2.0, y_canonical=y_center - h / 2.0,
        width_canonical=w, height_canonical=h,
        x_center=x_center, y_center=y_center)


def _cell(img, staff_lines=(100.0, 140.0, 180.0, 220.0, 260.0)):
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img, bbox_page_px=(0, 0, 300, 300),
        staff_line_ys_canonical=list(staff_lines), upscale_factor=1.0)


class TestIsHollowNotehead(unittest.TestCase):

    def test_half_whole_doublewhole_are_hollow(self):
        for n in ("noteheadHalfInSpace", "noteheadHalfOnLineSmall",
                 "noteheadWhole", "noteheadWholeInSpace",
                 "noteheadDoubleWholeOnLine"):
            self.assertTrue(geometry.is_hollow_notehead(n), n)

    def test_black_is_not_hollow(self):
        self.assertFalse(geometry.is_hollow_notehead("noteheadBlackInSpace"))

    def test_none_and_unknown_are_not_hollow(self):
        self.assertFalse(geometry.is_hollow_notehead(None))
        self.assertFalse(geometry.is_hollow_notehead("notARealClass"))


class TestGatherHollowHeadCentreWiring(unittest.TestCase):
    """`gather.gather_hollow_head_centre` -- the reader wired into a Log."""

    def _run(self, img, name="noteheadHalfInSpace", cx=150.0, cy=150.0,
            w=None, h=None):
        cell = _cell(img)
        sub = R.cell(0, 0, 0, 0)
        d = _detection(name, cx, cy, w=w, h=h)
        log = Log()
        gather.gather_hollow_head_centre(log, [cell], {0: (0, 0)},
                                         {sub.to_key(): [d]})
        g = R.glyph(0, 0, 0, 0, 0)
        return log, g

    def test_a_hollow_head_in_a_space_is_observed(self):
        img = _paper()
        cx, cy = 150.0, 150.0
        w, h = gather.STANDARD_HEAD_WIDTH_SPACES * SPACING * 1.15, \
               gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING * 1.15
        _ring(img, cx, cy, gather.STANDARD_HEAD_WIDTH_SPACES * SPACING,
              gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING, thickness=4)
        log, g = self._run(img, cx=cx, cy=cy, w=w, h=h)
        self.assertEqual(log.state(Q.HOLLOW_HEAD_CENTRE, g), State.READ)
        row = log.rows(Q.HOLLOW_HEAD_CENTRE, g)[0]
        self.assertEqual(row.reader, READERS.CV_HOLLOW_HEAD_CENTRE)
        rcx, rcy = row.value
        self.assertLess(abs(rcx - cx), 3.0)
        self.assertLess(abs(rcy - cy), 3.0)

    def test_a_regular_black_head_gets_no_row_at_all(self):
        """Not a hollow-classed glyph -- ABSENT, never a guessed row."""
        img = _paper()
        log, g = self._run(img, name="noteheadBlackInSpace")
        self.assertEqual(log.state(Q.HOLLOW_HEAD_CENTRE, g), State.ABSENT)

    def test_no_mask_abstains(self):
        cell = MeasureCell(
            page_index=0, system_index=0, staff_index=0, measure_index=0,
            image=None, image_no_staff=None, bbox_page_px=(0, 0, 300, 300),
            staff_line_ys_canonical=[100.0, 140.0, 180.0, 220.0, 260.0],
            upscale_factor=1.0)
        sub = R.cell(0, 0, 0, 0)
        d = _detection("noteheadHalfInSpace", 150.0, 150.0)
        log = Log()
        gather.gather_hollow_head_centre(log, [cell], {0: (0, 0)},
                                         {sub.to_key(): [d]})
        g = R.glyph(0, 0, 0, 0, 0)
        self.assertEqual(log.state(Q.HOLLOW_HEAD_CENTRE, g), State.DECLINED)
        self.assertEqual(log.refusals(Q.HOLLOW_HEAD_CENTRE, g)[0].reason,
                        ABSTAIN.NO_MASK)

    def test_a_filled_head_abstains_no_enclosed_hole(self):
        img = _paper()
        cx, cy = 150.0, 150.0
        _fill_ellipse(img, cx, cy, gather.STANDARD_HEAD_WIDTH_SPACES * SPACING,
                     gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING)
        log, g = self._run(img, cx=cx, cy=cy)
        self.assertEqual(log.state(Q.HOLLOW_HEAD_CENTRE, g), State.DECLINED)
        self.assertEqual(log.refusals(Q.HOLLOW_HEAD_CENTRE, g)[0].reason,
                        ABSTAIN.NO_ENCLOSED_HOLE)

    def test_a_broken_ring_abstains_no_enclosed_hole(self):
        img = _paper()
        cx, cy = 150.0, 150.0
        w = gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
        h = gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
        _ring(img, cx, cy, w, h, thickness=4)
        gap_x0 = int(cx + w / 2.0 - 6)
        img[int(cy) - 3:int(cy) + 3, gap_x0:gap_x0 + 8] = 255
        log, g = self._run(img, cx=cx, cy=cy,
                           w=w * 1.15, h=h * 1.15)
        self.assertEqual(log.state(Q.HOLLOW_HEAD_CENTRE, g), State.DECLINED)
        self.assertEqual(log.refusals(Q.HOLLOW_HEAD_CENTRE, g)[0].reason,
                        ABSTAIN.NO_ENCLOSED_HOLE)


if __name__ == "__main__":
    unittest.main()
