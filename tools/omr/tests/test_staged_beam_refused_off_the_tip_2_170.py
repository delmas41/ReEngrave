"""ROADMAP 2.170 (STAGED ADJUDICATE `rhythm.adjudicate_duration`), flag `OMR_BEAM_REFUSED_OFF_THE_TIP`, default OFF.

Where every stroke over a stemmed head was refused (`beam_discounted_uncertain`) and the 2.146 clean-tip rule could not decide
because the FLAG window at the tip was unread, the head is read as any unmarked head is -- IF no beam stroke of the cell
(either reader; kept, refused, or a detector box `_kept_beams` dropped) stands at its own stem tip AND the tip's beam-run
reader read that tip and found no run. A beam joins its stems at their ends. Each positive has a control beside it that
differs only in the evidence (CLAUDE.md rule 7)."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import ABSTAIN, READERS, Log, Outcome, Q
from tools.omr.staged.record import Scope
from tools.omr.tests.test_staged_stem_tip_decides_beam_2_146 import CELL, _discounted

FLAG = rhythm.BEAM_REFUSED_OFF_THE_TIP_ENV
ARC = rhythm.BEAM_NOT_ON_SYSTEM_ARC_ENV
HEAD = "glyph/0/0/0/0/0"


def _run(log, on=True, arc=False):
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0", ARC: "1" if arc else "0"}):
        adjudicate.run(log)


def _filled(log, g, share=0.0):
    """2.148's first-step head-fill reading: interior white `share` of the head's rows (0 -> DECIDED black)."""
    log.observe(g, Q.NOTEHEAD_INK, 1.0, reader=READERS.CV_NOTEHEAD_INK, frame="cell:0",
                interior_white={"rows_share": share, "hole_share": 0.0, "rows_read": 12, "box": [100, 90, 20, 16]})


def _arc_through(log, glyph, stroke_only=True):
    """A 2.166 system arc whose traced stroke runs through the detector box `glyph` (class beam)."""
    from tools.omr.staged import record as R
    log.observe(R.glyph(0, 0, 0, 0, 7), Q.SYSTEM_ARC, "two_positions", reader=READERS.CV_SYSTEM_ARC, frame="page",
                pieces=["glyph/0/0/0/0/7"], through_boxes=[{"glyph": glyph, "class": "beam", "residual_spaces2": 0.01,
                                                            "stroke_only": stroke_only}])


def _unread(log, why="ink_not_flag_shaped", end="top"):
    """The flag window's cannot-tell at the head's own stem tip (as `gather._observe_stem_tip_ink` files it)."""
    stem = [r for r in log.rows(Q.STEM, CELL, scope=Scope.EXACT) if r.value[0] == 105][0]
    log.abstain(CELL, Q.STEM_TIP_INK, reader=READERS.CV_STEM_TIP, frame="cell:0", reason=ABSTAIN.AMBIGUOUS,
                stem_row_id=stem.id, end=end, why=why)


def _off_tip(log, runs=(), why="ink_not_flag_shaped", levels_row=True, fill=0.0):
    g = _discounted(log, tip_found=None, runs=runs, levels_row=levels_row)
    _unread(log, why)
    if fill is not None:
        _filled(log, g, fill)
    return g


def _box_at_the_tip(log, reader=READERS.DETECTOR):
    """A stroke box at the up-stem's tip (stem x 105-109, tip y 80). As a DETECTOR box it overlaps the CV neighbour stroke
    (x 90-130) in x, so `_kept_beams` drops it -- the shattered-beam case: the CV piece stops short, the box reaches."""
    log.observe(CELL, Q.BEAM_STROKE, (100, 76, 30, 6), reader=reader, frame="cell:0", x0=100, x1=130, y_center=79,
                image="original", staff_lines_erased=False)


class TestOffTheTip(unittest.TestCase):

    def test_unread_flag_window_nothing_at_the_tip_decides_the_head(self):
        log = Log()
        g = _off_tip(log)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertEqual(v.value["beam_levels"], 0)
        self.assertIn("beam_refused_off_the_tip", v.detail)

    def test_control_flag_off_keeps_the_narrowing(self):
        log = Log()
        g = _off_tip(log)
        _run(log, on=False)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beam_discounted_uncertain")

    def test_a_dropped_detector_box_at_the_tip_keeps_the_narrowing(self):
        log = Log()
        g = _off_tip(log)
        _box_at_the_tip(log)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotIn("beam_refused_off_the_tip", v.detail or {})
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_beam_runs_at_the_tip_keep_the_narrowing(self):
        log = Log()
        g = _off_tip(log, runs=[(70, 80, 0.5, 2.0)])
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beam_discounted_uncertain")

    def test_no_tip_levels_row_keeps_the_narrowing(self):
        log = Log()
        g = _off_tip(log, levels_row=False)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_other_cannot_tell_reasons_keep_the_narrowing(self):
        """`runs_on` (ink runs off the tip: a beam to the right), `crosses_both_sides` (a mid-group stem), `occupied`,
        `head_at_this_end` (the side may be wrong): Litolff p2/p6 beamed eighths the first build decided as quarters."""
        for why in ("runs_on", "crosses_both_sides", "occupied", "head_at_this_end", "no_room"):
            log = Log()
            g = _off_tip(log, why=why)
            _run(log)
            v = log.verdict(Q.DURATION, g)
            self.assertEqual(v.outcome, Outcome.NARROWED, why)
            self.assertEqual(v.reason, "beam_discounted_uncertain", why)

    def test_no_flag_window_row_at_all_keeps_the_narrowing(self):
        log = Log()
        g = _discounted(log, tip_found=None, runs=())
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_a_stroke_at_the_HEAD_end_keeps_the_narrowing(self):
        """the side is a reading too: a beam box at the stem's other end (stem 80-100, box at y 96) keeps it."""
        log = Log()
        g = _off_tip(log)
        log.observe(CELL, Q.BEAM_STROKE, (100, 96, 30, 6), reader=READERS.DETECTOR, frame="cell:0", x0=100, x1=130,
                    y_center=99, image="original", staff_lines_erased=False)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotIn("beam_refused_off_the_tip", v.detail or {})

    def test_no_head_fill_reading_keeps_the_narrowing(self):
        """Addition 1 (Sean 2026-10-19; tile 2 was a half): the detector class alone never lets the rule decide."""
        log = Log()
        g = _off_tip(log, fill=None)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_an_undecided_head_fill_keeps_the_narrowing(self):
        log = Log()
        g = _off_tip(log, fill=0.15)          # between FILLED_MAX and HOLLOW_MIN: the fill reader did not decide
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotIn("beam_refused_off_the_tip", v.detail or {})

    def test_a_low_confidence_rescue_box_keeps_the_narrowing(self):
        """2.170 tile 2's box came from `yolo_rescue_lowconf` (score 0.19); its ink read solid on that box."""
        from tools.omr.staged import record as R
        log = Log()
        g = _discounted(log, tip_found=None, runs=())
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 100, 90, 20, 16), reader=READERS.RESCUE_LOWCONF, frame="cell:0",
                    score=0.19, bbox_page_px=[1100, 990, 1120, 1006])
        _unread(log)
        _filled(log, g)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotIn("beam_refused_off_the_tip", v.detail or {})

    def test_a_hook_at_the_tip_is_never_read_as_a_quarter(self):
        log = Log()
        g = _discounted(log, tip_found=True, runs=())
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotIn("beam_refused_off_the_tip", v.detail or {})
        self.assertFalse(v.outcome is Outcome.DECIDED and (v.value or {}).get("beam_levels") == 0)


class TestBeamsCannotHaveAnArc(unittest.TestCase):
    """Addition 2 (Sean: "beams cannot have an arc"): a stroke whose ink lies on a traced system arc is not a beam."""

    def _tip_box_on_arc(self, log, stroke_only=True):
        from tools.omr.staged import record as R
        _box_at_the_tip(log)
        bg = R.glyph(0, 0, 0, 0, 5)
        log.observe(bg, Q.GLYPH_BOX, ("beam", 100, 76, 30, 6), reader=READERS.DETECTOR, frame="cell:0", score=0.5,
                    bbox_page_px=[1100, 976, 1130, 982])
        _arc_through(log, bg.to_key(), stroke_only=stroke_only)

    def test_the_arc_witness_clears_a_slur_piece_at_the_tip(self):
        log = Log()
        g = _off_tip(log)
        self._tip_box_on_arc(log)
        _run(log, arc=True)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.detail["beam_refused_off_the_tip"]["arc_strokes_at_the_stem_ends"], 1)

    def test_control_arc_flag_off_the_box_still_blocks(self):
        log = Log()
        g = _off_tip(log)
        self._tip_box_on_arc(log)
        _run(log, arc=False)
        self.assertEqual(log.verdict(Q.DURATION, g).outcome, Outcome.NARROWED)

    def test_a_box_not_all_stroke_still_blocks(self):
        """a beam FUSED to a slur's tail: its box holds beam ink off the trace (not `stroke_only`) -- never refused."""
        log = Log()
        g = _off_tip(log)
        self._tip_box_on_arc(log, stroke_only=False)
        _run(log, arc=True)
        self.assertEqual(log.verdict(Q.DURATION, g).outcome, Outcome.NARROWED)

    def _counted(self, log):
        """the head's own stem tip carries a CV stroke (counted as one beam level) whose ink lies on a traced slur"""
        from tools.omr.staged import record as R
        g = _discounted(log, tip_found=None, runs=())
        log.observe(CELL, Q.BEAM_STROKE, (100, 74, 40, 6), reader=READERS.CV_LINES, frame="cell:0", x0=100, x1=140,
                    y_center=77, image="no_staff", staff_lines_erased=True)
        bg = R.glyph(0, 0, 0, 0, 5)
        log.observe(bg, Q.GLYPH_BOX, ("beam", 96, 70, 50, 14), reader=READERS.DETECTOR, frame="cell:0", score=0.5,
                    bbox_page_px=[1096, 970, 1146, 984])
        _arc_through(log, bg.to_key())
        return g

    def test_a_counted_stroke_on_the_arc_is_refused_as_a_beam(self):
        """on its own (tip rule OFF): the stroke at the tip is a slur piece -> refused `on_system_arc`, no beam level."""
        log = Log()
        g = self._counted(log)
        _run(log, on=False, arc=True)
        v = log.verdict(Q.DURATION, g)
        self.assertIn("on_system_arc", str(v.detail))
        self.assertNotEqual((v.value or {}).get("beam_levels"), 1)

    def test_control_arc_off_the_stroke_counts(self):
        log = Log()
        g = self._counted(log)
        _run(log, on=False, arc=False)
        v = log.verdict(Q.DURATION, g)
        self.assertNotIn("on_system_arc", str(v.detail))
        self.assertTrue(v.outcome is Outcome.NARROWED or (v.value or {}).get("beam_levels") == 1, (v.outcome, v.reason))


class TestTheFlag(unittest.TestCase):

    def test_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG, None)
            self.assertFalse(rhythm.beam_refused_off_the_tip_enabled())

    def test_on_words(self):
        for w in ("1", "true", "yes", "on"):
            with mock.patch.dict(os.environ, {FLAG: w}):
                self.assertTrue(rhythm.beam_refused_off_the_tip_enabled())
        for w in ("0", "false", "", "maybe"):
            with mock.patch.dict(os.environ, {FLAG: w}):
                self.assertFalse(rhythm.beam_refused_off_the_tip_enabled())


if __name__ == "__main__":
    unittest.main()
