"""ROADMAP 2.148 (STAGED GATHER `gather.head_interior_white` + ADJUDICATE `rhythm.adjudicate_duration`), flag
`OMR_HEAD_FILL_FIRST`, default OFF.

Sean 2026-10-16: "The notehead should be determined first as either black or hollow (containing white) THEN determine if it
has a stem and then if there is anything on the stem." / "The rule should be applied at the first step." A BLACK-classed head
whose own ink holds white inside (even a thin slit that opens out of a broken rim) is HOLLOW; on a stem, a half -- before any
stroke or flag is read. Each positive has a control that differs only in the evidence (CLAUDE.md rule 7)."""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.gather import head_interior_white
from tools.omr.staged.record import READERS, Log, Outcome, Q
from tools.omr.tests.test_staged_bare_stem_2_81 import CELL, _stem, _two_staff

FLAG = rhythm.HEAD_FILL_FIRST_ENV


def _raster(kind, w=44, h=36):
    """0 = ink. A filled ellipse, a ring (closed hollow), or a slit (hollow whose white opens at one end)."""
    img = np.full((h + 10, w + 10), 255, np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    e = ((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2 <= 1.0
    head = e.copy()
    if kind in ("ring", "slit"):
        inner = ((xx - w / 2) / (w / 2 - 7)) ** 2 + ((yy - h / 2) / (h / 2 - 9)) ** 2 <= 1.0
        head &= ~inner
        if kind == "slit":   # cut the rim open on the right
            head[h // 2 - 2:h // 2 + 2, w - 9:] = False
    img[5:5 + h, 5:5 + w][head] = 0
    return img, (5.0, 5.0, float(w), float(h))


class TestTheReader(unittest.TestCase):

    def test_filled_head_holds_no_white(self):
        img, box = _raster("filled")
        r = head_interior_white(img, box)
        self.assertEqual(r["rows_share"], 0.0)
        self.assertEqual(r["hole_share"], 0.0)

    def test_ring_holds_white_and_a_hole(self):
        img, box = _raster("ring")
        r = head_interior_white(img, box)
        self.assertGreaterEqual(r["rows_share"], 0.5)
        self.assertGreater(r["hole_share"], 0.0)

    def test_open_slit_still_reads_white_in_its_rows(self):
        img, box = _raster("slit")
        r = head_interior_white(img, box)
        self.assertGreaterEqual(r["rows_share"], rhythm.HEAD_INTERIOR_WHITE_HOLLOW_MIN)

    def test_off_the_raster_is_none(self):
        img, _ = _raster("filled")
        self.assertIsNone(head_interior_white(img, (-5.0, 0.0, 10.0, 10.0)))


def _head(log, *, share, stem=True, rows_read=20, with_reading=True, beam=False):
    g = _two_staff(log)
    if stem:
        _stem(log, x=105, y=60, h=40)
    if with_reading:
        log.observe(g, Q.NOTEHEAD_INK, 1.0, reader=READERS.CV_NOTEHEAD_INK, frame="cell:0",
                    ink_raw={"best": 1.0, "best_window": "center", "windows": {"center": 1.0, "ring": 0.8}},
                    interior_white={"rows_share": share, "hole_share": 0.0, "rows_read": rows_read, "box": [100, 90, 20, 16]})
    if beam:
        log.observe(CELL, Q.BEAM_STROKE, (100, 58, 40, 6), reader=READERS.CV_LINES, frame="cell:0", x0=100, x1=140,
                    y_center=61, image="no_staff", staff_lines_erased=True)
    return g


def _run(log, on=True):
    with mock.patch.dict(os.environ, {FLAG: "1" if on else ""}):
        adjudicate.run(log)


class TestTheHeadIsReadFirst(unittest.TestCase):

    def test_white_inside_on_a_stem_is_a_half(self):
        log = Log()
        g = _head(log, share=0.4)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["written"], 2.0)
        self.assertEqual(v.detail["head_fill_first"]["settled"], "half_on_a_stem")

    def test_control_flag_off_keeps_the_quarter(self):
        log = Log()
        g = _head(log, share=0.4)
        _run(log, on=False)
        v = log.verdict(Q.DURATION, g)
        self.assertNotEqual((v.value or {}).get("written"), 2.0)

    def test_control_solid_head_stays_black(self):
        log = Log()
        g = _head(log, share=0.0)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotEqual((v.value or {}).get("written"), 2.0)

    def test_between_the_populations_is_not_decided_hollow(self):
        log = Log()
        g = _head(log, share=0.12)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotEqual((v.value or {}).get("written"), 2.0)

    def test_no_stem_is_not_decided_here(self):
        log = Log()
        g = _head(log, share=0.4, stem=False)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotIn("settled", (v.detail or {}).get("head_fill_first") or {})

    def test_an_older_record_without_the_reading_is_unchanged(self):
        log_on, log_off = Log(), Log()
        g1 = _head(log_on, share=0.4, with_reading=False)
        g2 = _head(log_off, share=0.4, with_reading=False)
        _run(log_on)
        _run(log_off, on=False)
        self.assertEqual(log_on.verdict(Q.DURATION, g1).value, log_off.verdict(Q.DURATION, g2).value)

    def test_a_stroke_at_the_stem_cannot_make_the_hollow_head_shorter(self):
        log = Log()
        g = _head(log, share=0.4, beam=True)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        cands = [v.value] if v.value else [c.value for c in v.candidates]
        self.assertTrue(all(c["written"] >= 2.0 for c in cands), cands)


class TestTheLateRuleDefers(unittest.TestCase):
    """Sean 2026-10-16: the previous application of the rule is amended -- a head read SOLID first is not turned hollow by
    the late centred window (2.23)."""

    def _late_window_says_hollow(self, log, g):
        log.observe(g, Q.NOTEHEAD_INK, 0.2, reader=READERS.CV_NOTEHEAD_INK, frame="cell:0",
                    ink_raw={"best": 0.9, "best_window": "ring", "windows": {"center": 0.2, "ring": 0.9}},
                    interior_white={"rows_share": 0.0, "hole_share": 0.0, "rows_read": 20, "box": [100, 90, 20, 16]})

    def test_solid_first_reading_wins_over_the_late_window(self):
        log = Log()
        g = _two_staff(log)
        _stem(log, x=105, y=60, h=40)
        self._late_window_says_hollow(log, g)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        cands = [v.value] if v.value else [c.value for c in v.candidates]
        self.assertTrue(all(c.get("head_fill") != "half" and c["written"] < 2.0 for c in cands), cands)
        self.assertFalse(v.detail["head_is_open"])

    def test_control_flag_off_the_late_window_still_acts(self):
        log = Log()
        g = _two_staff(log)
        _stem(log, x=105, y=60, h=40)
        self._late_window_says_hollow(log, g)
        _run(log, on=False)
        v = log.verdict(Q.DURATION, g)
        self.assertTrue(v.detail["head_is_open"])


class TestTheFlag(unittest.TestCase):

    def test_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG, None)
            self.assertFalse(rhythm.head_fill_first_enabled())


if __name__ == "__main__":
    unittest.main()
