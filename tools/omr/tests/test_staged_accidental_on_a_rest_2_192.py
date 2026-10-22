"""ROADMAP 2.192 -- an accidental box on a kept rest's ink (flag `OMR_ACCIDENTAL_ON_A_REST`, default OFF). Every test that says the accidental is
refused has a twin that says it must stay (flag OFF, a rest that is only NEAR, a refused rest box, an accidental-shaped ink, a real accidental
that merely touches a rest); the control proves the refusal can fire."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import accidental_shape as AS
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests import test_staged_accidental as TA

FLAG = "OMR_ACCIDENTAL_ON_A_REST"
SHARPISH = {"bl": 0.8, "tr": 0.8, "shape": "sharp"}
FLATISH = {"bl": 0.8, "tr": 0.0, "shape": "flat"}      # what an eighth rest's bulb and stem reads as
UNCL = {"bl": 0.4, "tr": 0.4, "shape": "unclear"}


def _scene(cls="accidentalDoubleSharp", alt="##", shape=FLATISH, rest_dx=0.0, rest_refused=False, flag="1", rest_present=True):
    log = Log()
    TA._cell_unit(log)
    g = R.glyph(0, 0, 0, 0, 0)
    y0 = 4.0 * TA.HALF - TA.SPACE
    log.observe(g, Q.GLYPH_BOX, (cls, 88.0, y0, 12.0, TA.SPACE * 2), reader=READERS.DETECTOR, frame="cell:0", score=0.8, category="accidental")
    log.observe(g, Q.ACCIDENTAL_STAFF_POSITION, 4.0, reader=READERS.GEOMETRY, frame="cell:0", alteration=alt, detector_class=cls,
                anchor_fraction=0.5, box_centre_position=4.0, residual=0.0, rounded=4, x0=88.0, x1=100.0, y0=y0, y1=y0 + 2 * TA.SPACE,
                confidence=0.8, shape=shape)
    TA._head(log, 1, 106.0, 4.0)
    if rest_present:
        rg = R.glyph(0, 0, 0, 0, 2)
        log.observe(rg, Q.GLYPH_BOX, ("rest8th", 88.0 + rest_dx, y0, 12.0, TA.SPACE * 2), reader=READERS.DETECTOR, frame="cell:0", score=0.7,
                    category="rest")
        if rest_refused:
            TA._verdict(log, rg, Q.REST_IS_NOT_A_REST, True, reason="refused")
        else:
            TA._verdict(log, rg, Q.REST_IS_NOT_A_REST, False, reason="rest")
    with mock.patch.dict(os.environ, {FLAG: flag, "OMR_ONE_INK_ONE_MARK": "1", "OMR_ACCIDENTAL_SHAPE": "1"}):
        TA._decide(log)
    return log, g


class TestOnARest(unittest.TestCase):

    def test_a_double_sharp_on_a_rest_with_a_rest_shaped_ink_is_refused(self):
        log, g = _scene()
        v = log.verdict(Q.ACCIDENTAL_OWNER, g)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "on_a_rest")
        self.assertEqual(v.detail["why"], "shape_is_flat_not_sharp")
        self.assertGreaterEqual(v.detail["iou"], 0.5)
        self.assertEqual(v.detail["rest_class"], "rest8th")

    def test_CONTROL_same_scene_the_flag_off_the_head_is_owned(self):
        log, g = _scene(flag="0")
        v = log.verdict(Q.ACCIDENTAL_OWNER, g)
        self.assertEqual(v.outcome, "decided")

    def test_TWIN_an_accidental_shaped_ink_of_its_own_class_stays(self):
        log, g = _scene(shape=SHARPISH)
        self.assertEqual(log.verdict(Q.ACCIDENTAL_OWNER, g).outcome, "decided")

    def test_TWIN_a_real_flat_with_a_flat_shape_that_touches_a_rest_stays(self):
        log, g = _scene(cls="accidentalFlat", alt="b", shape=FLATISH)
        self.assertEqual(log.verdict(Q.ACCIDENTAL_OWNER, g).outcome, "decided")

    def test_TWIN_a_rest_that_is_only_near_is_not_one_ink(self):
        log, g = _scene(rest_dx=10.0)      # 2 of 12 px overlap: IoU well under .5
        self.assertEqual(log.verdict(Q.ACCIDENTAL_OWNER, g).outcome, "decided")

    def test_TWIN_a_refused_rest_box_is_not_a_rest(self):
        log, g = _scene(rest_refused=True)
        self.assertEqual(log.verdict(Q.ACCIDENTAL_OWNER, g).outcome, "decided")

    def test_TWIN_no_rest_box_at_all_nothing_changes(self):
        log, g = _scene(rest_present=False)
        self.assertEqual(log.verdict(Q.ACCIDENTAL_OWNER, g).outcome, "decided")

    def test_cannot_tell_is_not_applied_and_counted(self):
        log, g = _scene(shape=UNCL)
        v = log.verdict(Q.ACCIDENTAL_OWNER, g)
        self.assertEqual((v.outcome, v.reason, v.detail["why"]), ("abstained", "on_a_rest", "unclear"))
        log2, g2 = _scene(shape={})
        self.assertEqual(log2.verdict(Q.ACCIDENTAL_OWNER, g2).detail["why"], "unread")

    def test_the_rest_box_is_never_touched(self):
        log, _g = _scene()
        rg = R.glyph(0, 0, 0, 0, 2)
        v = log.verdict(Q.REST_IS_NOT_A_REST, rg)
        self.assertIs(v.value, False)

    def test_the_verdict_table(self):
        self.assertTrue(AS.on_rest_verdict("accidentalDoubleSharp", {"shape": "sharp"})["keep"])
        self.assertTrue(AS.on_rest_verdict("accidentalNatural", {"shape": "natural"})["keep"])
        self.assertFalse(AS.on_rest_verdict("accidentalNatural", {"shape": "flat"})["keep"])
        self.assertFalse(AS.on_rest_verdict("accidentalSharp", None)["keep"])
        self.assertFalse(AS.on_rest_verdict("keyFlat", {"shape": "flat"})["keep"])

    def test_default_is_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG, None)
            self.assertFalse(AS.on_rest_enabled())


if __name__ == "__main__":
    unittest.main()
