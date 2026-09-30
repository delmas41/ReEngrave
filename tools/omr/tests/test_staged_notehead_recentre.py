"""ROADMAP 2.39b -- re-centre a notehead on its own ink.

⚠️ WHY THIS EXISTS. `benchmarks/omr-notehead-width-2026-09/FINDINGS.md`
§15/§18: the first half of 2.39 gave every regular notehead a STANDARD box
(`geometry.standard_head_box`) sized from the staff's own spacing, centred
on the DETECTOR's own centre. That is sound where the box is merely the
WRONG SIZE (a Litolff merge) and unsound where it is a SLIVER (a Breitkopf
shattered fragment): a sliver's own centre sits on the head's EDGE, not its
middle, so a standard box built around it covers mostly blank paper. The
manager caught it on one measured head (`brahms-notehead-ink-swing.png`,
fill 0.914 -> 0.185) and the reconnection was reverted (`c8bbd3a5`).

This file tests the RE-CENTRE this brief asks for: a bounded MATCHED-WINDOW
search on `cell.image_no_staff` for the offset with the highest ink fill,
declining (never guessing, CLAUDE.md rule 8) where the winner is not
clearly a head or not clearly ahead of a rival window.

⚠️ RUN RED FIRST: `gather.recentre_notehead` / `gather.gather_notehead_
recentre` / `Q.NOTEHEAD_RECENTRE` do not exist on the tree before this
round -- every import and every `Q.NOTEHEAD_RECENTRE` reference below
raises `AttributeError`.
"""
from __future__ import annotations

import unittest

import types

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q, READERS, State
from tools.omr.types import MeasureCell


def _paper(h=300, w=300):
    return np.full((h, w), 255, dtype=np.uint8)


def _fill_ellipse(img, cx, cy, w, h):
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    a, b = max(1.0, w / 2.0), max(1.0, h / 2.0)
    img[((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2 <= 1.0] = 0


def _ring(img, cx, cy, w, h, thickness):
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    a, b = w / 2.0, h / 2.0
    outer = ((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2 <= 1.0
    a2, b2 = max(1.0, a - thickness), max(1.0, b - thickness)
    inner = ((xx - cx) / a2) ** 2 + ((yy - cy) / b2) ** 2 <= 1.0
    img[outer & ~inner] = 0


def _stroke(img, x, y0, y1, w=6):
    img[int(y0):int(y1), int(x):int(x + w)] = 0


SPACING = 40.0  # px per staff space, canonical


class TestTheSearchMath(unittest.TestCase):
    """`gather.recentre_notehead` -- pure, on synthetic rasters."""

    def test_well_centred_head_returns_near_zero_shift_and_high_fill(self):
        """⚠️ THE FIRST CONTROL: a head already sitting on its own centre
        must not be moved off it by the search -- CLAUDE.md rule 7."""
        img = _paper()
        cx, cy = 150.0, 150.0
        _fill_ellipse(img, cx, cy, gather.STANDARD_HEAD_WIDTH_SPACES * SPACING,
                     gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING)
        r = gather.recentre_notehead(img, cx, cy, SPACING)
        self.assertIsNotNone(r)
        self.assertIsNone(r["decline_reason"])
        self.assertLess(abs(r["dx_sp"]), 0.15)
        self.assertLess(abs(r["dy_sp"]), 0.15)
        self.assertGreater(r["fill"], gather.RECENTRE_MIN_FILL)

    def test_off_centre_head_recentres_toward_its_own_ink(self):
        """A head painted 0.3 sp above and 0.2 sp left of the detector's
        assumed centre -- the shape a Litolff/Brahms mis-centred box is a
        symptom of -- is found, not merely tolerated."""
        img = _paper()
        detector_cx, detector_cy = 150.0, 150.0
        true_cx = detector_cx - 0.2 * SPACING
        true_cy = detector_cy - 0.3 * SPACING
        _fill_ellipse(img, true_cx, true_cy,
                     gather.STANDARD_HEAD_WIDTH_SPACES * SPACING,
                     gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING)
        r = gather.recentre_notehead(img, detector_cx, detector_cy, SPACING)
        self.assertIsNotNone(r)
        self.assertIsNone(r["decline_reason"])
        self.assertAlmostEqual(r["dx_sp"], -0.2, delta=0.11)
        self.assertAlmostEqual(r["dy_sp"], -0.3, delta=0.11)

    def test_a_stem_alone_declines_below_threshold(self):
        """⚠️⚠️ THE POSITIVE CONTROL THE BRIEF NAMES: 'a thin stem fills a
        head-sized window only ~15-20%, so it should not win.'"""
        img = _paper()
        _stroke(img, 148.0, 60.0, 240.0, w=6)
        r = gather.recentre_notehead(img, 150.0, 150.0, SPACING)
        self.assertIsNotNone(r)
        self.assertLess(r["fill"], gather.RECENTRE_MIN_FILL)
        self.assertEqual(r["decline_reason"], ABSTAIN.BELOW_THRESHOLD)

    def test_a_hollow_head_declines_below_threshold(self):
        """A half/whole head's own interior is sparse everywhere the search
        looks -- it must decline rather than pick the least-sparse window
        and call it a black head's true centre."""
        img = _paper()
        _ring(img, 150.0, 150.0, gather.STANDARD_HEAD_WIDTH_SPACES * SPACING,
             gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING, thickness=4.0)
        r = gather.recentre_notehead(img, 150.0, 150.0, SPACING)
        self.assertIsNotNone(r)
        self.assertLess(r["fill"], gather.RECENTRE_MIN_FILL)
        self.assertEqual(r["decline_reason"], ABSTAIN.BELOW_THRESHOLD)

    def test_a_tie_between_two_heads_declines_ambiguous(self):
        """⚠️ THE CHORD-SECOND CASE the brief names by name: two real,
        dense heads a third apart, both within the search radius and
        neither a clear winner over the other, must decline rather than
        picking one arbitrarily."""
        img = _paper()
        w = gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
        h = gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
        # 1.1 sp apart -- close enough that a THIRD window straddling both
        # (the detector's own centre) is not the winner (measured: at 1.0
        # sp apart it IS, at 1.1 the two single-head windows win instead
        # and tie), so this is genuinely the chord-second case, not the
        # "one window covers both" case.
        _fill_ellipse(img, 150.0, 150.0 - 0.55 * SPACING, w, h)
        _fill_ellipse(img, 150.0, 150.0 + 0.55 * SPACING, w, h)
        # The detector's own centre sits exactly between the two heads.
        r = gather.recentre_notehead(img, 150.0, 150.0, SPACING)
        self.assertIsNotNone(r)
        self.assertEqual(r["decline_reason"], ABSTAIN.AMBIGUOUS)

    def test_off_the_raster_returns_none(self):
        img = _paper(h=10, w=10)
        r = gather.recentre_notehead(img, 500.0, 500.0, SPACING)
        self.assertIsNone(r)

    def test_no_spacing_returns_none(self):
        img = _paper()
        self.assertIsNone(gather.recentre_notehead(img, 150.0, 150.0, 0.0))
        self.assertIsNone(gather.recentre_notehead(img, 150.0, 150.0, None))

    def test_no_image_returns_none(self):
        self.assertIsNone(gather.recentre_notehead(None, 150.0, 150.0, SPACING))


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


class TestGatherNoteheadRecentreWiring(unittest.TestCase):
    """`gather.gather_notehead_recentre` -- the reader wired into a Log."""

    def _run(self, img, name="noteheadBlackInSpace", cx=150.0, cy=150.0,
            staff_lines=(100.0, 140.0, 180.0, 220.0, 260.0)):
        cell = _cell(img, staff_lines=staff_lines)
        sub = R.cell(0, 0, 0, 0)
        d = _detection(name, cx, cy)
        log = Log()
        gather.gather_notehead_recentre(log, [cell], {0: (0, 0)},
                                        {sub.to_key(): [d]})
        g = R.glyph(0, 0, 0, 0, 0)
        return log, g

    def test_a_well_centred_regular_head_is_observed(self):
        img = _paper()
        _fill_ellipse(img, 150.0, 150.0, gather.STANDARD_HEAD_WIDTH_SPACES * 20,
                     gather.STANDARD_HEAD_HEIGHT_SPACES * 20)
        log, g = self._run(img, staff_lines=(50.0, 70.0, 90.0, 110.0, 130.0))
        self.assertEqual(log.state(Q.NOTEHEAD_RECENTRE, g), State.READ)
        row = log.rows(Q.NOTEHEAD_RECENTRE, g)[0]
        self.assertEqual(row.reader, READERS.CV_NOTEHEAD_RECENTRE)
        dx_sp, dy_sp = row.value
        self.assertLess(abs(dx_sp), 0.15)
        self.assertLess(abs(dy_sp), 0.15)

    def test_a_whole_note_gets_no_row_at_all(self):
        """ROADMAP 2.39's own gate: a class this round never measured is
        never guessed at either -- ABSENT, not DECLINED."""
        img = _paper()
        log, g = self._run(img, name="noteheadWhole")
        self.assertEqual(log.state(Q.NOTEHEAD_RECENTRE, g), State.ABSENT)

    def test_no_staff_geometry_abstains(self):
        img = _paper()
        log, g = self._run(img, staff_lines=())
        self.assertEqual(log.state(Q.NOTEHEAD_RECENTRE, g), State.DECLINED)
        reason = log.refusals(Q.NOTEHEAD_RECENTRE, g)[0].reason
        self.assertEqual(reason, ABSTAIN.NO_STAFF_GEOMETRY)

    def test_no_mask_abstains(self):
        cell = MeasureCell(
            page_index=0, system_index=0, staff_index=0, measure_index=0,
            image=None, image_no_staff=None, bbox_page_px=(0, 0, 300, 300),
            staff_line_ys_canonical=[100.0, 140.0, 180.0, 220.0, 260.0],
            upscale_factor=1.0)
        sub = R.cell(0, 0, 0, 0)
        d = _detection("noteheadBlackInSpace", 150.0, 150.0)
        log = Log()
        gather.gather_notehead_recentre(log, [cell], {0: (0, 0)},
                                        {sub.to_key(): [d]})
        g = R.glyph(0, 0, 0, 0, 0)
        self.assertEqual(log.state(Q.NOTEHEAD_RECENTRE, g), State.DECLINED)
        self.assertEqual(log.refusals(Q.NOTEHEAD_RECENTRE, g)[0].reason,
                        ABSTAIN.NO_MASK)


class TestReconnectedFillTest(unittest.TestCase):
    """ROADMAP 2.39b item 2 -- `gather_notehead_ink` reads the re-centred
    box, falling back to the raw detector box where the search declined.

    ⚠️ THE REGRESSION THIS FILE EXISTS TO CATCH: `benchmarks/omr-notehead-
    width-2026-09/FINDINGS.md` §18 measured the un-recentred standard box
    reading a solid BLACK head as HOLLOW (0.914 -> 0.185) because the raw
    detector box was a sliver on the head's own edge. The re-centre search
    must recover the correct high fill on the SAME shape of fixture.
    """

    def _cells_and_dets(self, img, x_canonical, y_canonical, w, h,
                        name="noteheadBlackInSpace"):
        cell = _cell(img, staff_lines=(50.0, 70.0, 90.0, 110.0, 130.0))
        sub = R.cell(0, 0, 0, 0)
        d = types.SimpleNamespace(
            smufl_name=name, x_canonical=x_canonical, y_canonical=y_canonical,
            width_canonical=w, height_canonical=h,
            x_center=x_canonical + w / 2.0, y_center=y_canonical + h / 2.0)
        return [cell], {0: (0, 0)}, {sub.to_key(): [d]}

    def test_a_sliver_box_recovers_the_true_high_fill_via_recentre(self):
        img = _paper()
        # A real BLACK head, correctly painted, whose true centre is 0.35
        # sp ABOVE where a sliver's own bbox centre would sit -- the exact
        # shape of `brahms-notehead-ink-swing.png` (FINDINGS §15/§18).
        head_w, head_h = gather.STANDARD_HEAD_WIDTH_SPACES * 20, \
            gather.STANDARD_HEAD_HEIGHT_SPACES * 20
        true_cx, true_cy = 150.0, 150.0
        _fill_ellipse(img, true_cx, true_cy, head_w, head_h)
        # The "sliver" detector box: 0.24 sp tall (FINDINGS' own number),
        # sitting across the head's TOP EDGE, so ITS centre is off the
        # head's true centre by 0.35 sp.
        sliver_h = 0.24 * 20
        sliver_cy = true_cy - 0.35 * 20 - sliver_h / 2.0
        sliver_x = true_cx - 5.0
        cells, local, dets = self._cells_and_dets(
            img, sliver_x, sliver_cy, 10.0, sliver_h)
        log = Log()
        gather.gather_notehead_recentre(log, cells, local, dets)
        gather.gather_notehead_ink(log, cells, local, dets)
        g = R.glyph(0, 0, 0, 0, 0)
        row = log.rows(Q.NOTEHEAD_INK, g)[0]
        self.assertGreater(row.value, 0.5,
                          "the reconnected fill test must read the real "
                          "BLACK head as filled, not hollow, once the "
                          "search has found its own true centre")

    def test_a_declined_recentre_falls_back_to_the_raw_box(self):
        """⚠️ THE CONTROL: where the search declines (or never runs), the
        fill test must use the RAW detector box, never the un-recentred
        standard box §18 refuted."""
        img = _paper()
        # A thin, off-centre stroke: the search declines (BELOW_THRESHOLD),
        # so the raw box (which the stroke itself fully occupies) must be
        # what gets measured.
        cells, local, dets = self._cells_and_dets(img, 148.0, 60.0, 6.0, 180.0)
        _stroke(img, 148.0, 60.0, 240.0, w=6)
        log = Log()
        gather.gather_notehead_recentre(log, cells, local, dets)
        g = R.glyph(0, 0, 0, 0, 0)
        self.assertEqual(log.state(Q.NOTEHEAD_RECENTRE, g), State.DECLINED)
        gather.gather_notehead_ink(log, cells, local, dets)
        row_ink = log.rows(Q.NOTEHEAD_INK, g)[0]
        expected = gather.notehead_ink_under(img, (148.0, 60.0, 6.0, 180.0))
        self.assertEqual(row_ink.value, round(expected["best"], 4))

    def test_a_well_centred_head_is_unmoved_by_the_reconnect(self):
        """⚠️ THE OTHER CONTROL: a head already on its own centre reads the
        SAME fill through the reconnect as it did on the raw box, because
        the search's own shift is ~0."""
        img = _paper()
        head_w, head_h = gather.STANDARD_HEAD_WIDTH_SPACES * 20, \
            gather.STANDARD_HEAD_HEIGHT_SPACES * 20
        _fill_ellipse(img, 150.0, 150.0, head_w, head_h)
        cells, local, dets = self._cells_and_dets(
            img, 150.0 - head_w / 2.0, 150.0 - head_h / 2.0, head_w, head_h)
        log = Log()
        gather.gather_notehead_recentre(log, cells, local, dets)
        gather.gather_notehead_ink(log, cells, local, dets)
        g = R.glyph(0, 0, 0, 0, 0)
        row = log.rows(Q.NOTEHEAD_INK, g)[0]
        self.assertGreater(row.value, 0.5)


class TestNoteheadBoxesForCellReadsRecentre(unittest.TestCase):
    """ROADMAP 2.39b item 2's 4th connection: `_notehead_boxes_for_cell`'s
    optional `log=` keyword re-centres the stem/beam gate's own box."""

    def test_log_none_is_unchanged(self):
        """⚠️ THE CONTROL: every pre-2.39b call site (`log` omitted) is
        byte-identical -- the reason every OTHER test in
        `test_stem_notehead_gate.py` still passes untouched."""
        from tools.omr.staged.gather import _notehead_boxes_for_cell

        sub = R.cell(0, 0, 0, 0)
        d = _detection("noteheadBlackOnLine", 125.0, 120.0, w=50.0, h=40.0)
        dets = {sub.to_key(): [d]}
        cell = _cell(_paper(), staff_lines=[100, 200, 300, 400, 500])
        without_log = gather._notehead_boxes_for_cell(dets, sub, cell)
        with_none = gather._notehead_boxes_for_cell(dets, sub, cell, log=None)
        self.assertEqual(without_log, with_none)

    def test_log_with_a_recentre_row_shifts_the_gate_box(self):
        from tools.omr.staged.gather import _notehead_boxes_for_cell

        sub = R.cell(0, 0, 0, 0)
        d = _detection("noteheadBlackOnLine", 125.0, 120.0, w=50.0, h=40.0)
        dets = {sub.to_key(): [d]}
        cell = _cell(_paper(), staff_lines=[100, 200, 300, 400, 500])
        log = Log()
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_RECENTRE, [0.2, -0.1],
                    reader=READERS.CV_NOTEHEAD_RECENTRE, frame="cell:0",
                    fill=0.9, margin=0.2, runner_up=0.6)
        baseline = gather._notehead_boxes_for_cell(dets, sub, cell)
        shifted = gather._notehead_boxes_for_cell(dets, sub, cell, log=log)
        self.assertNotEqual(baseline, shifted)
        bx, by, bw, bh = baseline[0]
        sx, sy, sw, sh = shifted[0]
        self.assertEqual(bw, sw)
        self.assertEqual(bh, sh)
        # 0.2 sp * 100 px/sp (staff spacing here is 100 px) = 20 px.
        self.assertAlmostEqual((sx + sw / 2.0) - (bx + bw / 2.0), 20.0,
                              delta=1e-6)
        self.assertAlmostEqual((sy + sh / 2.0) - (by + bh / 2.0), -10.0,
                              delta=1e-6)


if __name__ == "__main__":
    unittest.main()
