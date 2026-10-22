"""ROADMAP 2.177 (Sean 2026-10-20): the printed meter is ONE object; its area is claimed (`Q.CLAIMED_AREA`, owner `meter`) and a box whose ink
lies inside it is refused (`inside_the_meter`). Flag `OMR_METER_OBJECT`, default ON. Every CONTROL passes with the rule absent or present, so a
rule that refuses everything cannot pass.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate, adjudicators            # noqa: F401
from tools.omr.staged import meter_object as MO
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests.test_staged_duration import _staff_space

ON = {"OMR_METER_OBJECT": "1"}
OFF = {"OMR_METER_OBJECT": "0"}
SP = 16.0
LINES = [100.0 + SP * i for i in range(5)]


def _page(extra=()):
    img = np.full((400, 600), 255, np.uint8)
    for ly in LINES:
        img[int(ly) - 1:int(ly) + 2, 20:580] = 0
    # the meter: two bold numerals one above the other (upper two spaces, lower two spaces)
    img[int(LINES[0]) - 2:int(LINES[0]) + 28, 200:226] = 0
    img[int(LINES[2]) + 4:int(LINES[4]) + 2, 200:226] = 0
    for (x0, y0, x1, y1) in extra:
        img[y0:y1, x0:x1] = 0
    return img


class TestFinder(unittest.TestCase):
    def test_two_stacked_numerals_are_one_area_and_the_first_note_is_outside(self):
        img = _page(extra=[(260, int(LINES[1]) + 4, 280, int(LINES[1]) + 18)])      # a head, 34 px right of the numerals
        r = MO.find(img, LINES, SP, 100, 400)
        self.assertTrue(r["found"], r)
        a = r["area"]
        self.assertLessEqual(a[2], 235)                       # stops at the numerals' own ink (+1 stroke)
        self.assertGreaterEqual(a[0], 190)
        inside = MO.ink_inside(img, (260, int(LINES[1]) + 4, 280, int(LINES[1]) + 18), a, LINES, SP)
        self.assertTrue(inside is None or inside["ink_share_inside"] < 0.1, inside)      # CONTROL: the first note is kept
        loop = MO.ink_inside(img, (200, int(LINES[2]) + 4, 226, int(LINES[4]) + 2), a, LINES, SP)
        self.assertGreater(loop["ink_share_inside"], 0.9)

    def test_CONTROL_ink_just_right_of_the_numerals_is_outside_the_claim(self):
        """Sean 2026-10-20: "it is posible for there to be things in between the meter and the first notes but nothing that would overlap
        with the meter digits." A cautionary accidental / a rest printed right after the numerals is kept: the claim is the digits' own
        extent (one stroke of padding), never the gap after them."""
        mark = (232, int(LINES[1]) + 2, 244, int(LINES[3]) - 2)          # 6 px past the numerals' right edge (226), a mark's own ink
        img = _page(extra=[mark])
        r = MO.find(img, LINES, SP, 100, 400)
        self.assertTrue(r["found"], r)
        self.assertLessEqual(r["area"][2], 230)                      # 226 + 1 stroke (3 px), not a column or a gap
        got = MO.ink_inside(img, mark, r["area"], LINES, SP)
        self.assertTrue(got is None or got["ink_share_inside"] < 0.2, got)

    def test_no_numerals_no_object(self):
        img = _page()
        img[:, 190:240] = 255
        for ly in LINES:
            img[int(ly) - 1:int(ly) + 2, 20:580] = 0
        self.assertFalse(MO.find(img, LINES, SP, 100, 400)["found"])

    def test_a_pair_on_one_staff_only_is_not_a_column(self):
        img = _page()
        staves = [{"key": 0, "lines": LINES, "spacing": SP, "x_lo": 100, "x_hi": 400},
                  {"key": 1, "lines": [l + 200 for l in LINES], "spacing": SP, "x_lo": 100, "x_hi": 400}]
        img2 = np.full((700, 600), 255, np.uint8)
        img2[:400] = img
        for ly in [l + 200 for l in LINES]:
            img2[int(ly) - 1:int(ly) + 2, 20:580] = 0
        col = MO.find_column(img2, staves)
        self.assertIsNone(col["column_x"])        # 1 of 2 staves is under the share (0.4 of 2 -> 1, but COLUMN_MIN_STAVES is 2)

    def test_flag_default_on(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMR_METER_OBJECT", None)
            self.assertTrue(MO.enabled())
        for off in ("0", "false", "no", "off"):
            with mock.patch.dict(os.environ, {"OMR_METER_OBJECT": off}):
                self.assertFalse(MO.enabled())


def _box(log, gi, box, cls, cell=0, rest=False):
    g = R.glyph(0, 0, 0, cell, gi)
    if rest:
        log.observe(g, Q.REST, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    else:
        log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="rest" if rest else "notehead", bbox_page_px=[box[0], box[1], box[0] + box[2], box[1] + box[3]])
    return g


def _claim(log, glyph_key, share, cell=0):
    st = R.staff(0, 0, 0)
    log.observe(st, Q.CLAIMED_AREA, [30.0, 90.0, 130.0, 190.0], reader=READERS.CV_CLAIMED_AREA, frame="cell:0", cell=cell, owner="meter",
                owner_row=None, unit="area", standing="READ", boxes_inside={glyph_key: {"ink_px": 100, "inside_px": int(100 * share),
                                                                                       "ink_share_inside": share, "cls": "x"}})


def _nn(log, g, env=ON):
    with mock.patch.dict(os.environ, env):
        adjudicate.run(log)
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)


class TestRefusal(unittest.TestCase):
    def _fx(self, cls="noteheadBlackInSpace", share=0.95):
        log = Log()
        _staff_space(log, 100)
        g = _box(log, 0, (40, 120, 130, 100), cls)
        _claim(log, g.to_key(), share)
        return log, g

    def test_a_black_head_whose_ink_is_in_the_area_is_refused_RED(self):
        log, g = self._fx()
        v = _nn(log, g)
        self.assertTrue(v.value is True and v.reason == "inside_the_meter", (v.value, v.reason))

    def test_every_head_class_is_refused(self):
        for cls in ("noteheadBlackOnLine", "noteheadHalfInSpace", "noteheadWholeInSpace"):
            log, g = self._fx(cls=cls)
            v = _nn(log, g)
            self.assertEqual((v.value, v.reason), (True, "inside_the_meter"), cls)

    def test_FLAG_OFF_the_head_stands(self):
        log, g = self._fx()
        self.assertFalse(_nn(log, g, OFF).value)

    def test_CONTROL_a_box_that_only_touches_the_edge_is_kept(self):
        log, g = self._fx(share=0.12)
        self.assertFalse(_nn(log, g).value)

    def test_CONTROL_a_stemmed_head_is_a_note_and_is_kept(self):
        log, g = self._fx()
        log.observe(R.cell(0, 0, 0, 0), Q.STEM, (140, 20, 4, 110), reader=READERS.CV_INK, frame="cell:0", x0=140, x1=144, y_center=75)
        self.assertFalse(_nn(log, g).value)

    def test_CONTROL_no_claim_no_refusal(self):
        log = Log()
        _staff_space(log, 100)
        g = _box(log, 0, (40, 120, 130, 100), "noteheadBlackInSpace")
        self.assertFalse(_nn(log, g).value)

    def test_2_173_and_2_177_both_refuse_the_tile_8_kind(self):
        """Sean 2.176 tile 8: the top loop of a meter numeral 8 boxed as a head. 2.173 (a whole-class box on a READ meter's stacked pair)
        and 2.177 (the claimed area) both refuse a loop; neither refuses a real head far from the numerals."""
        from tools.omr.tests.test_staged_whole_rest_meter_2_173 import TestWholeOnAReadMeter as T
        log, h = T()._fx()
        with mock.patch.dict(os.environ, {"OMR_WHOLE_NEEDS_HOLLOW_NO_STEM": "1", "OMR_METER_OBJECT": "0"}):
            adjudicate.run(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h)
        self.assertTrue(v.value is True and v.reason == "on_a_read_meter", (v.value, v.reason))
        log2, g = self._fx(cls="noteheadWholeInSpace", share=1.0)
        v2 = _nn(log2, g)
        self.assertTrue(v2.value is True and v2.reason == "inside_the_meter", (v2.value, v2.reason))


class TestRest(unittest.TestCase):
    def _rn(self, log, g, env):
        with mock.patch.dict(os.environ, env):
            adjudicate.run(log)
        return log.verdict(Q.REST_IS_NOT_A_REST, g)

    def test_a_rest_whose_ink_is_in_the_area_is_refused_and_one_outside_is_kept(self):
        for share, want in ((0.9, True), (0.0, False)):
            log = Log()
            _staff_space(log, 100)
            g = _box(log, 0, (300, 100, 60, 100), "restQuarter", rest=True)
            if share:
                _claim(log, g.to_key(), share)
            v = self._rn(log, g, ON)
            self.assertEqual(bool(v.value) and v.reason == "inside_the_meter", want, (share, v.value, v.reason))


if __name__ == "__main__":
    unittest.main()


# ROADMAP 2.181 flipped OMR_CLAIMED_REGISTER ON; this file pins the pre-register path (flag OFF) it was written for.
import os as _os_2181
_PREV_2181 = None


def setUpModule():
    global _PREV_2181
    _PREV_2181 = _os_2181.environ.get("OMR_CLAIMED_REGISTER")
    _os_2181.environ["OMR_CLAIMED_REGISTER"] = "0"


def tearDownModule():
    if _PREV_2181 is None:
        _os_2181.environ.pop("OMR_CLAIMED_REGISTER", None)
    else:
        _os_2181.environ["OMR_CLAIMED_REGISTER"] = _PREV_2181
