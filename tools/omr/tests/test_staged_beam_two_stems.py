"""ROADMAP 2.74 -- a BEAM is thick, straight, and stands on two stems.

Sean, 2026-10-09 (DECISIONS), on 2.65 tiles 1, 4, 15 and 21 (Brahms 1,
Breitkopf, p1): *"A beam must not only connect to its note but also to another
note."* / *"A beam never has an arc."* / *"The thickness on a beam is always
more than a hairpin."* Tile 21: a slur's two tapering arcs, boxed as `beam`
and joined to the head's stem by box overlap, made an eighth read a
SIXTEENTH.

⚠️ RUN RED FIRST (the commit says so): every test here fails on the tree
without `Q.BEAM_STROKE_INK` / `gather.beam_stroke_ink` / the `rhythm` tier --
the measurement tests on the missing function, the adjudication tests on the
missing quantity, and the tile-15 tests (`TestACountedHookSettlesTwoFlagBoxes`)
on the behaviour itself (they use only quantities that already exist).

⚠️ EVERY TEST IS READ FROM INK. A test that cannot be read ABSTAINS and the
stroke stays (rule 8): `test_an_UNREAD_*` pin that, with a control that the
same stroke is dropped once its ink reads thin.
"""

from __future__ import annotations

import unittest

import numpy as np

from tools.omr.staged import adjudicate, evaluate                # noqa: F401
from tools.omr.staged import adjudicators, consequences          # noqa: F401
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

from tools.omr.tests.test_staged_duration import (
    CELL, X, _beam, _flag, _note, _staff_space, _stem, _stem_tip_ink)

SP = 20.0                                   # one staff space, canonical px
LINES = [100, 120, 140, 160, 180]           # five staff lines, SP apart


# ─────────────────────────────────────────────────────────────────────────────
# Part 1 -- the measurement, on synthetic rasters (255 paper, 0 ink)
# ─────────────────────────────────────────────────────────────────────────────

def _page(line_thickness=3, right_line_thickness=None, w=400, h=320):
    img = np.full((h, w), 255, dtype=np.uint8)
    for y in LINES:
        img[y:y + line_thickness, :] = 0
        if right_line_thickness:
            img[y:y + right_line_thickness, 200:] = 0
    return img


def _bar(img, x0, x1, y0, thickness):
    img[y0:y0 + thickness, x0:x1] = 0


def _stem_down(img, x, y0, y1, w=3):
    img[y0:y1, x:x + w] = 0


def _arc(img, x0, x1, y_ends, sag, thickness):
    """A parabolic arc, `sag` px deeper in the middle than at its ends."""
    mid = (x0 + x1) / 2.0
    half = (x1 - x0) / 2.0
    for x in range(x0, x1):
        yc = y_ends + sag * (1.0 - ((x - mid) / half) ** 2)
        t = int(thickness)
        img[int(yc - t / 2): int(yc - t / 2) + t, x] = 0


def _line(img, x0, x1, y_a, y_b, thickness):
    for x in range(x0, x1):
        yc = y_a + (y_b - y_a) * (x - x0) / float(x1 - x0)
        t = int(thickness)
        img[int(yc - t / 2): int(yc - t / 2) + t, x] = 0


def _measure(img, box):
    return gather.beam_stroke_ink(img, box, SP, LINES)


class TestTheMeasurement(unittest.TestCase):
    """`gather.beam_stroke_ink` -- three rulers over one stroke's own ink."""

    def _real_beam(self):
        img = _page()
        _bar(img, 60, 200, 40, 10)                    # 0.5 space thick
        _stem_down(img, 60, 40, 100)
        _stem_down(img, 197, 40, 100)
        return img, (60, 40, 140, 10)

    def test_a_real_two_stem_beam_is_thick_straight_and_stands_on_two_stems(
            self):
        img, box = self._real_beam()
        m = _measure(img, box)
        self.assertIsNotNone(m)
        self.assertGreaterEqual(m["thickness_ratio"], 3.0)
        self.assertLess(m["sagitta_spaces"], 0.05)
        self.assertEqual([e["found"] for e in m["end_stems"]], [True, True])

    def test_a_sloped_beam_is_still_straight(self):
        """⚠️ POSITIVE CONTROL for the bow test: a slope is not an arc."""
        img = _page()
        _line(img, 60, 200, 60, 40, 10)
        m = _measure(img, (60, 35, 140, 30))
        self.assertLess(m["sagitta_spaces"], 0.05)
        self.assertGreaterEqual(m["thickness_ratio"], 2.5)

    def test_a_hairpins_line_is_about_one_staff_line_thick(self):
        img = _page()
        _line(img, 60, 200, 45, 60, 3)
        m = _measure(img, (60, 45, 140, 15))
        self.assertLessEqual(m["thickness_ratio"], 1.5)

    def test_a_slur_is_thin_AND_bowed(self):
        img = _page()
        _arc(img, 60, 200, 40, 10, 5)
        m = _measure(img, (60, 40, 140, 16))
        self.assertLess(m["thickness_ratio"], 2.0)
        self.assertGreater(m["sagitta_spaces"], 0.3)
        self.assertEqual([e["found"] for e in m["end_stems"]], [False, False])

    def test_a_THICK_arc_is_bowed_even_where_it_is_not_thin(self):
        """⚠️ The second of Sean's tests stands on its own: thickness alone
        would pass this."""
        img = _page()
        _arc(img, 60, 200, 40, 20, 10)
        m = _measure(img, (60, 40, 140, 30))
        self.assertGreaterEqual(m["thickness_ratio"], 3.0)
        self.assertGreater(m["sagitta_spaces"], 0.6)

    def test_thickness_is_measured_against_the_staff_lines_AT_the_strokes_columns(
            self):
        """CLAUDE.md §10: measure against the staff LOCALLY. The same 10 px
        bar is 3.3 lines thick where the lines are 3 px and 1.4 where they
        are 7 px; a fixed pixel cut would call both the same."""
        img = _page(line_thickness=3, right_line_thickness=7, w=400)
        _bar(img, 40, 160, 40, 10)
        _bar(img, 220, 340, 40, 10)
        left = _measure(img, (40, 40, 120, 10))
        right = _measure(img, (220, 40, 120, 10))
        self.assertEqual(left["thickness_px"], right["thickness_px"])
        self.assertGreater(left["thickness_ratio"], 3.0)
        self.assertLess(right["thickness_ratio"], 1.6)

    def test_a_beam_lying_ON_two_staff_lines_does_not_set_their_thickness(self):
        """⚠️ A two-level beam standing on two of the staff's five lines
        merges with them; the pooled median of the lines' runs read 54 px
        against a true 23 on Brahms p1 and called a real beam a hairpin."""
        img = _page()
        _bar(img, 60, 200, LINES[2] - 2, 12)           # a beam level on line 3
        _bar(img, 60, 200, LINES[3] - 2, 12)           # and one on line 4
        m = _measure(img, (60, LINES[2] - 2, 140, 12))
        self.assertEqual(m["line_px"], 3.0)
        self.assertGreaterEqual(m["thickness_ratio"], 3.5)

    def test_a_stroke_over_paper_is_DECLINED_not_measured(self):
        self.assertIsNone(_measure(_page(), (60, 40, 140, 10)))

    def test_a_beam_with_one_stem_reads_one_end_without_a_stem(self):
        img = _page()
        _bar(img, 60, 200, 40, 10)
        _stem_down(img, 60, 40, 100)
        m = _measure(img, (60, 40, 140, 10))
        self.assertEqual([e["found"] for e in m["end_stems"]], [True, False])

    def test_without_staff_lines_the_ratio_is_UNREAD_not_defaulted(self):
        """No line measurable -> no ratio. A fixed pixel fallback would be a
        guess (rule 8); the thickness in spaces is still reported."""
        img = np.full((320, 400), 255, dtype=np.uint8)
        _bar(img, 60, 200, 40, 10)
        m = gather.beam_stroke_ink(img, (60, 40, 140, 10), SP, [])
        self.assertIsNone(m["thickness_ratio"])
        self.assertAlmostEqual(m["thickness_spaces"], 0.5, places=2)


# ─────────────────────────────────────────────────────────────────────────────
# Part 2 -- ADJUDICATE reads the rulers
# ─────────────────────────────────────────────────────────────────────────────

def _ink(log, stroke, *, ratio=3.0, sag=0.01, ends=(True, True),
         x0=None, x1=None):
    """One `Q.BEAM_STROKE_INK` row -- the real shape `gather.gather_beam_
    stroke_ink` files (`beam_row_id` names the exact `Q.BEAM_STROKE` row)."""
    sx0 = stroke.detail["x0"] if x0 is None else x0
    sx1 = stroke.detail["x1"] if x1 is None else x1
    ends_d = [{"found": e, "x": (sx0 if i == 0 else sx1) if e else None}
              for i, e in enumerate(ends)]
    return log.observe(CELL, Q.BEAM_STROKE_INK, 0.6,
                       reader=READERS.CV_BEAM_SHAPE, frame="cell:0",
                       beam_row_id=stroke.id,
                       thickness_px=12.0, line_px=3.0,
                       thickness_ratio=ratio, thickness_spaces=0.6,
                       sagitta_spaces=sag, end_stems=ends_d,
                       columns=100, cover=1.0, band=[40.0, 50.0])


def _head_with_stem(log, gi, x, *, y=90):
    """A black head whose stem rises 60 px to the beam line at y=38."""
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", x, y, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    s = _stem(log, x=x, y=38, h=60)
    return g, s


def _group(log, *, x0=65, x1=180, y=40):
    """Two stemmed heads under one stroke -- a real two-note beam."""
    _staff_space(log)
    g1, _ = _head_with_stem(log, 0, x0)
    g2, _ = _head_with_stem(log, 1, x1)
    stroke = _beam(log, y=y, x0=x0 - 5, x1=x1 + 20)
    return g1, g2, stroke


class TestASlurTieOrHairpinStrokeIsNotThisNotesBeam(unittest.TestCase):
    """2.65 tile 21: an eighth under a real beam with a slur over it read a
    SIXTEENTH -- the slur's tapering arc, boxed as `beam`, overlapped the
    head's stem and counted as a second level."""

    def _tile_21(self, log):
        g1, g2, beam = _group(log)
        slur = _beam(log, y=34, x0=40, x1=220)       # touches both stems' tips
        return g1, g2, beam, slur

class TestTheInksRefusalsNeverDecideTheHeadValueFromAbsence(unittest.TestCase):
    """Rule 8. Brahms p1 page 0 holds ~45 beamed eighths whose only 'beam' was
    a detector box lying on a staff line: the ink reads it thin and refuses
    it, and a head with nothing left must not fall to its head value (quarter)
    as if the beam had been looked for and found absent."""

    def _chord_head(self, log, *, with_ink):
        """A head with NO stem box of its own (a chord member: the stem is
        another head's) under one stroke."""
        _staff_space(log)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        stroke = _beam(log, y=90, x0=20, x1=300, reader=READERS.DETECTOR)
        if with_ink:
            _ink(log, stroke, ratio=1.0, sag=0.0, ends=(False, False))
        return g

class TestATestThatCannotBeReadAbstains(unittest.TestCase):
    """Rule 8: each test is READ or it does not judge. Every one of these
    strokes would be refused if the ink read thin, bowed or one-stemmed (the
    `*_control` halves), and none is refused where the ink was not read."""

    def _lone(self, log, **ink):
        _staff_space(log)
        g, _s = _head_with_stem(log, 0, 65)
        stroke = _beam(log, y=40, x0=60, x1=140, reader=READERS.DETECTOR)
        _ink(log, stroke, **ink)
        return g, stroke

class TestACountedHookSettlesTwoFlagBoxes(unittest.TestCase):
    """2.65 tile 15 (Brahms p1 `glyph/1/1/9/0/13`): ONE flag, boxed by the
    detector as both `flag8thUp` and `flag16thUp`. 2.69's stem-tip reader
    COUNTS the hooks at that stem (one). A counted hook that is one of the
    levels the boxes vote for breaks the tie; a count no box voted for, or no
    count, leaves the disagreement narrowed (never an argmax)."""

    def _head(self, log, **tip):
        _staff_space(log)
        _beam(log, y=2, x0=400, x1=460)       # a decoy: the reader RAN
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        s = _stem(log, x=135, y=38, h=60)
        _flag(log, gi=50, cls="flag8thUp", x=139, y=38)
        _flag(log, gi=51, cls="flag16thUp", x=139, y=36)
        if tip:
            _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True, **tip)
        return g

    def test_one_counted_hook_chooses_the_eighth(self):
        log = Log()
        g = self._head(log, hooks=1, hooks_min=1, hooks_max=1,
                       hooks_reason=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertTrue(v.detail["flags_disagree_settled_by_hooks"])

    def test_two_counted_hooks_choose_the_sixteenth(self):
        """Not a bias toward the eighth: the count decides, either way."""
        log = Log()
        g = self._head(log, hooks=2, hooks_min=2, hooks_max=2,
                       hooks_reason=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.25)

    def test_a_count_no_box_voted_for_leaves_it_narrowed(self):
        log = Log()
        g = self._head(log, hooks=3, hooks_min=3, hooks_max=3,
                       hooks_reason=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "flags_disagree")

    def test_an_UNCOUNTED_hook_leaves_it_narrowed(self):
        log = Log()
        g = self._head(log, hooks=None, hooks_min=1, hooks_max=2,
                       hooks_reason="unresolved")
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "flags_disagree")

    def test_no_stem_tip_reading_leaves_it_narrowed(self):
        log = Log()
        g = self._head(log)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "flags_disagree")


# ─────────────────────────────────────────────────────────────────────────────
# Part 3 -- a beam FUSED to a hairpin's line is rescued (2.65 tile 1)
# ─────────────────────────────────────────────────────────────────────────────

import cv2                                                       # noqa: E402

from tools.omr import line_detection as LD                       # noqa: E402
from tools.omr.types import MeasureCell                          # noqa: E402

SPACING = 100
LINE_YS = [100, 200, 300, 400, 500]
BEAM_H = int(0.48 * SPACING)
#: ceiling that the beam ALONE (48) passes and the beam + two thin lines (62)
#: does not -- a stand-in for the real plate's 125 px against its 115 ceiling.
TALL_CEILING_LINES = 0.60


def _fused_cell(*, thickness=10.0, hairpin=True):
    img = np.full((800, 900), 255, dtype=np.uint8)
    y_top = 150
    for x in (300, 550):                              # two stems...
        img[y_top:y_top + int(3.5 * SPACING), x - 5:x + 5] = 0
    img[y_top:y_top + BEAM_H, 295:555] = 0            # ...and the beam
    if hairpin:                                       # two thin lines under it
        img[y_top + BEAM_H:y_top + BEAM_H + 7, 480:700] = 0
        img[y_top + BEAM_H + 7:y_top + BEAM_H + 14, 480:700] = 0
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img.copy(), bbox_page_px=(0, 0, 900, 800),
        staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0,
        staff_line_thickness_canonical=thickness)


class TestABeamFusedToAHairpinLineIsRescued(unittest.TestCase):
    """Brahms p1 `glyph/1/0/0/0/5`: a dim. hairpin drawn so close under a
    group's beam that the opening fused them into ONE component taller than
    the beam ceiling, so the group's beam was never read and an eighth read a
    quarter. Re-opened with a kernel thicker than a hairpin's line, the beam
    stays and the line goes."""

    def test_without_the_rescue_the_fused_component_is_refused_as_today(self):
        cell = _fused_cell()
        self.assertEqual(LD.detect_beams(
            cell, max_height_lines=TALL_CEILING_LINES), [])

    def test_with_the_rescue_the_beam_is_read_and_the_lines_are_not(self):
        cell = _fused_cell()
        beams = LD.detect_beams(cell, max_height_lines=TALL_CEILING_LINES,
                                rescue_tall=True)
        self.assertEqual(len(beams), 1)
        b = beams[0]
        self.assertLessEqual(abs(b.height_canonical - BEAM_H), 4)
        self.assertLessEqual(abs(b.width_canonical - 260), 8)

    def test_no_traced_line_thickness_means_no_rescue_not_a_guess(self):
        cell = _fused_cell(thickness=None)
        self.assertEqual(LD.detect_beams(
            cell, max_height_lines=TALL_CEILING_LINES, rescue_tall=True), [])

    def test_the_rescue_is_ADDITIVE_a_beam_read_anyway_is_the_same_beam(self):
        cell = _fused_cell(hairpin=False)
        a = LD.detect_beams(cell, max_height_lines=TALL_CEILING_LINES)
        b = LD.detect_beams(cell, max_height_lines=TALL_CEILING_LINES,
                            rescue_tall=True)
        self.assertEqual(len(a), 1)
        self.assertEqual([(x.x_canonical, x.y_canonical, x.width_canonical,
                           x.height_canonical) for x in a],
                         [(x.x_canonical, x.y_canonical, x.width_canonical,
                           x.height_canonical) for x in b])


if __name__ == "__main__":
    unittest.main()
