"""ROADMAP 2.159 (STAGED GATHER `gather.head_interior_white_located` + ADJUDICATE `rhythm.adjudicate_duration` first step),
flag `OMR_HEAD_FILL_LOCATED_BOX`, default ON (Sean 2026-10-17).

Sean 2026-10-17: "I'm not sure why it doesn't see simple half notes". Measured on the 20261016-night records: the heads left
narrowed by `head_fill_from_ink` sat, 95/114 (Litolff) and 223/231 (Brahms), in a detector box that is not one head's size --
most often only PART of the head -- so 2.148's first step never read them. Where an earlier reader located the head, the slit
is read on that head box; white there, on the head's own stem, is a half. Each positive has a control that differs only in
the evidence (CLAUDE.md rule 7)."""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.gather import head_interior_white_located
from tools.omr.staged.record import READERS, Log, Outcome, Q
from tools.omr.tests.test_staged_bare_stem_2_81 import CELL, _stem, _two_staff
from tools.omr.tests.test_staged_head_fill_first_2_148 import _raster, _run

FLAG = rhythm.HEAD_FILL_LOCATED_ENV
#: the fixture head sits at x 100..120, y 90..106 (space 16); this box holds only its lower part (0.62 sp tall)
PART_BOX = ("noteheadBlack", 100, 96, 20, 10)
#: the standard head box (1.4 x 1.1 sp) centred on the located head -- it holds the detector box's centre (110, 101)
LOCATED = [98.8, 89.2, 22.4, 17.6]


def _part_boxed(log, *, located_share, located_box=LOCATED, stem=True, head_sized=False, detector_share=0.0,
                window_hollow=True):
    g = _two_staff(log)
    if stem:
        _stem(log, x=105, y=60, h=40)
    if not head_sized:
        log.observe(g, Q.GLYPH_BOX, PART_BOX, reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                    bbox_page_px=[1100, 996, 1120, 1006])
    extra = {}
    if located_share is not None:
        extra["interior_white_located"] = {"rows_share": located_share, "hole_share": 0.0, "rows_read": 12,
                                           "box": [0, 0, 1, 1], "frame": "page", "box_cell": list(located_box),
                                           "located_by": "part_boxed_recentre"}
    log.observe(g, Q.NOTEHEAD_INK, 1.0, reader=READERS.CV_NOTEHEAD_INK, frame="cell:0",
                ink_raw=({"best": 0.8, "best_window": "ring", "windows": {"center": 0.3, "ring": 0.8}} if window_hollow
                         else {"best": 1.0, "best_window": "center", "windows": {"center": 1.0, "ring": 0.8}}),
                interior_white={"rows_share": detector_share, "hole_share": 0.0, "rows_read": 8,
                                "box": [100, 96, 20, 10]}, **extra)
    return g


def _decide(log, g, *, located_on=True):
    with mock.patch.dict(os.environ, {FLAG: "1" if located_on else "0"}):
        _run(log)
    return log.verdict(Q.DURATION, g)


def _written(v):
    return (v.value or {}).get("written")


class TestTheLocatedHeadIsRead(unittest.TestCase):

    def test_white_on_the_located_box_on_a_stem_is_a_half(self):
        log = Log()
        g = _part_boxed(log, located_share=0.4)
        v = _decide(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(_written(v), 2.0)
        hf = v.detail["head_fill_first"]
        self.assertEqual(hf["settled"], "half_on_a_stem")
        self.assertEqual(hf["located_by"], "part_boxed_recentre")
        self.assertEqual(hf["detector_box_rows_share"], 0.0)

    def test_control_flag_off_the_part_box_is_not_read(self):
        log = Log()
        g = _part_boxed(log, located_share=0.4)
        v = _decide(log, g, located_on=False)
        self.assertNotEqual(_written(v), 2.0)
        self.assertTrue(v.detail["head_fill_first"]["not_head_sized"])

    def test_control_solid_located_head_is_not_a_half(self):
        log = Log()
        g = _part_boxed(log, located_share=0.0)
        self.assertNotEqual(_written(_decide(log, g)), 2.0)

    def test_control_the_2_23_window_reading_solid_keeps_the_head(self):
        """White on the located box alone is not enough: the 2.23 window on that same box must also read hollow (a white
        speck in a beamed cluster, an `ff` boxed as a head -- the first Litolff replay)."""
        log = Log()
        g = _part_boxed(log, located_share=0.4, window_hollow=False)
        self.assertNotEqual(_written(_decide(log, g)), 2.0)

    def test_between_the_populations_is_not_a_half(self):
        log = Log()
        g = _part_boxed(log, located_share=0.12)
        self.assertNotEqual(_written(_decide(log, g)), 2.0)

    def test_a_located_black_reading_never_settles_the_head_black(self):
        """Only HOLLOW is taken from the located box: a solid reading there changes nothing (the verdict is the one the flag
        OFF gives), so it can never overrule the 2.23 window."""
        on, off = Log(), Log()
        g1 = _part_boxed(on, located_share=0.0)
        g2 = _part_boxed(off, located_share=0.0)
        v1, v2 = _decide(on, g1), _decide(off, g2, located_on=False)
        self.assertEqual((v1.outcome, v1.reason, v1.value), (v2.outcome, v2.reason, v2.value))

    def test_a_box_that_moved_onto_another_head_is_not_read(self):
        log = Log()
        g = _part_boxed(log, located_share=0.4, located_box=[98.8, 70.0, 22.4, 17.6])   # does not hold (110, 101)
        self.assertNotEqual(_written(_decide(log, g)), 2.0)

    def test_no_stem_is_not_decided_here(self):
        log = Log()
        g = _part_boxed(log, located_share=0.4, stem=False)
        v = _decide(log, g)
        self.assertNotIn("settled", (v.detail or {}).get("head_fill_first") or {})

    def test_a_head_sized_box_keeps_its_own_reading(self):
        """The located reading is asked only where the detector's box is NOT one head's size."""
        log = Log()
        g = _part_boxed(log, located_share=0.4, head_sized=True, detector_share=0.0)
        v = _decide(log, g)
        self.assertNotEqual(_written(v), 2.0)
        self.assertEqual(v.detail["head_fill_first"].get("settled"), "black")

    def test_a_record_without_the_located_reading_is_unchanged(self):
        on, off = Log(), Log()
        g1 = _part_boxed(on, located_share=None)
        g2 = _part_boxed(off, located_share=None)
        v1, v2 = _decide(on, g1), _decide(off, g2, located_on=False)
        self.assertEqual((v1.outcome, v1.reason, v1.value), (v2.outcome, v2.reason, v2.value))


class TestNeverOnInkThatIsNotAHead(unittest.TestCase):
    """Sean's 2.159 tiles (2026-10-17): tile 1 "Ff" and tile 4 "trem slashes" were decided halves. Their own readings from
    the Brahms night record are reproduced; the existing readers saw both but did not refuse the box."""

    def test_tile_1_a_head_lying_on_a_dynamic_letter_is_not_read(self):
        log = Log()
        g = _part_boxed(log, located_share=0.4)
        # Brahms glyph/18/1/9/6/15: the hook of an `f` above the detector's dynamicF box (on 0.264 < the 0.4 refusal cut)
        log.observe(g, Q.NOTEHEAD_LETTER_INK, 0.683, reader=READERS.CV_NOTEHEAD_INK, frame="cell:0",
                    letter_ink_share=0.0, head_in_letter=0.264, letter="glyph/0/0/0/0/9", letter_class="dynamicF",
                    letter_w_spaces=2.367, letter_h_spaces=2.024)
        v = _decide(log, g)
        self.assertNotEqual(_written(v), 2.0)
        refusal = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertNotEqual(getattr(refusal, "value", None), True)   # the box is still a head to the refusal reader

    def test_tile_4_ink_that_straddles_the_stem_is_not_read(self):
        log = Log()
        g = _part_boxed(log, located_share=0.4)
        stem = log.rows(Q.STEM, CELL)[-1]
        # Brahms glyph/16/1/10/0/7: a slash at 8.8 degrees (under 2.137's 10-degree floor), ink on both sides of the stem
        log.observe(g, Q.NOTEHEAD_STEM_CROSS_INK, [0.9416, 0.7143], reader="cv_notehead_stem_cross_ink", frame="cell:0",
                    stem=stem.id, left=0.9416, right=0.7143, left_share=0.3525, right_share=0.6475, total_ink_px=3248,
                    angle_deg=8.8, elongation=1.76, fill=0.5767, ink_px=3248)
        v = _decide(log, g)
        sig = (log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g).detail or {}).get("tremolo_slash_signal") or {}
        self.assertTrue(sig.get("crossing_ok"))
        self.assertNotEqual(_written(v), 2.0)

    def test_control_crossing_ink_on_one_side_only_still_reads(self):
        log = Log()
        g = _part_boxed(log, located_share=0.4)
        stem = log.rows(Q.STEM, CELL)[-1]
        log.observe(g, Q.NOTEHEAD_STEM_CROSS_INK, [0.9, 0.02], reader="cv_notehead_stem_cross_ink", frame="cell:0",
                    stem=stem.id, left=0.9, right=0.02, left_share=0.98, right_share=0.02, total_ink_px=3000,
                    angle_deg=30.0, elongation=1.3, fill=0.6, ink_px=3000)
        v = _decide(log, g)
        self.assertEqual(_written(v), 2.0)


class _Cell:
    def __init__(self, bbox, up):
        self.bbox_page_px, self.upscale_factor = bbox, up


class TestTheGatherReading(unittest.TestCase):
    """The located box is read off the PAGE raster at its page position (canonical / upscale + the cell's page origin)."""

    def _page(self, kind):
        img, (x, y, w, h) = _raster(kind)
        page = np.full((200, 300), 255, np.uint8)
        page[50:50 + img.shape[0], 80:80 + img.shape[1]] = img
        return page, (80 + x, 50 + y, w, h)

    def test_a_ring_at_the_located_box_reads_white(self):
        page, (px, py, w, h) = self._page("ring")
        cell = _Cell([60.0, 40.0, 260.0, 160.0], 4.0)          # canonical = (page - origin) * 4
        box_cell = ((px - 60) * 4, (py - 40) * 4, w * 4, h * 4)
        r = head_interior_white_located(cell, box_cell, page, "notehead_recentre")
        self.assertGreaterEqual(r["rows_share"], rhythm.HEAD_INTERIOR_WHITE_HOLLOW_MIN)
        self.assertEqual(r["located_by"], "notehead_recentre")
        self.assertEqual(r["box_cell"], [round(v, 2) for v in box_cell])

    def test_control_a_filled_head_reads_no_white(self):
        page, (px, py, w, h) = self._page("filled")
        cell = _Cell([60.0, 40.0, 260.0, 160.0], 4.0)
        r = head_interior_white_located(cell, ((px - 60) * 4, (py - 40) * 4, w * 4, h * 4), page, "head_line_cut")
        self.assertEqual(r["rows_share"], 0.0)

    def test_no_page_raster_declines(self):
        cell = _Cell([60.0, 40.0, 260.0, 160.0], 4.0)
        self.assertIsNone(head_interior_white_located(cell, (0, 0, 40, 30), None, "notehead_recentre"))
        self.assertIsNone(head_interior_white_located(_Cell(None, None), (0, 0, 40, 30), np.zeros((9, 9), np.uint8),
                                                      "notehead_recentre"))


class TestTheFlag(unittest.TestCase):

    def test_default_on(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG, None)
            self.assertTrue(rhythm.head_fill_located_enabled())

    def test_on_word_enables(self):
        for w in ("1", "true", "yes", "on"):
            with mock.patch.dict(os.environ, {FLAG: w}):
                self.assertTrue(rhythm.head_fill_located_enabled())

    def test_off_word_or_empty_disables(self):
        for w in ("0", "false", "no", "off", "", " OFF "):
            with mock.patch.dict(os.environ, {FLAG: w}):
                self.assertFalse(rhythm.head_fill_located_enabled())

if __name__ == "__main__":
    unittest.main()
