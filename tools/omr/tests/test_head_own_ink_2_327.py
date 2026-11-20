"""ROADMAP 2.327 -- a notehead is measured on its own ink, not its box. STAGED GATHER (`head_ink.trim_head`) + ADJUDICATE
(`rhythm._head_ink_reads_hollow_unread_black`).

The rule, as a musician says it: a head is hollow where paper runs between its own ink across its middle -- read on the head's own
ink, never its box. NEVER from paper beside or below the head; never from one speck in a black head; never a head from a box that
is not one (Sean 2026-11-19; measure the mark, not its box, and join and separate by ink: Sean 2026-11-18).

Real fixtures (`data_head_own_ink_2_327.npz`): page crops (600 dpi, `render_page(...).binary`, nothing erased) around the detector
box of marks Sean judged, with the page space. Keys `<page>_<system>_<staff>_<cell>_<glyph>_<l|b>` (Litolff / Brahms).
  * Litolff p2 `glyph/2/1/0/11/2`, a half (2.83 tiles), written a quarter: the slash guard read the BOX's ledger stubs crossing the stem.
  * Litolff p2 `glyph/2/0/7/4/5`, Sean 2026-11-19 "a sharp sign blending into the barline": the NEVER. On its own ink it is one
    head-sized hollow shape, so nothing here may write it plain (the detector-box size gate keeps it GUESSED).
  * Litolff p6 `glyph/6/1/5/11/1`, a half whose own ink is wider than the one-head cap: kept refused (the cap also keeps paper
    between two black heads, Litolff p2 `glyph/2/1/7/13/1`, an eighth, from reading hollow).
  * six Litolff halves Sean judged that are written blue because their detector box is not one head's size: still hollow.
  * Brahms p0 / p11 heads Sean judged solid that read hollow on the trimmed head on main: the trim took in paper below the head.
Each positive has a control that fails on main or differs only in the evidence (CLAUDE.md rule 7)."""
from __future__ import annotations

import os
import pathlib
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import head_ink as HI
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.gather import head_interior_white, notehead_ink_under
from tools.omr.staged.record import READERS, Log, Q
from tools.omr.tests.test_head_ink_consumer_2_220 import _decide, _guess, _w
from tools.omr.tests.test_staged_bare_stem_2_81 import CELL
from tools.omr.tests.test_staged_head_fill_located_2_159 import _part_boxed

HERE = pathlib.Path(__file__).parent
FX = np.load(HERE / "data_head_own_ink_2_327.npz")


def _tile(key):
    shape = tuple(int(v) for v in FX[key + "_shape"])
    ink = np.unpackbits(FX[key + "_ink"])[: shape[0] * shape[1]].reshape(shape).astype(bool)
    return np.where(ink, 0, 255).astype(np.uint8), [float(v) for v in FX[key + "_box"]], float(FX[key + "_sp"])


def _read(key):
    page, box, sp = _tile(key)
    return HI.read_head_ink(page, box, sp, [], head_interior_white, notehead_ink_under)


def _keys(doc, answer):
    return sorted(k[: -len("_answer")] for k in FX.files
                  if k.endswith("_answer") and str(FX[k]) == answer and k[: -len("_answer")].endswith("_" + doc[0]))


class _Trim(unittest.TestCase):
    def setUp(self):
        self._env = {k: os.environ.get(k) for k in (HI.TRIM_ENV, HI.TRIM_V2_ENV, HI.OWN_ROWS_ENV)}
        os.environ[HI.TRIM_ENV] = "1"
        os.environ[HI.TRIM_V2_ENV] = "1"
        os.environ[HI.OWN_ROWS_ENV] = "1"

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class OwnInkOnSeansLitolffMarks(_Trim):

    def test_the_halves_written_blue_for_their_box_read_hollow_on_their_own_ink(self):
        keys = [k for k in _keys("litolff", "half") if k not in ("6_1_5_11_1_l",)]
        self.assertGreaterEqual(len(keys), 7)
        for k in keys:
            r = _read(k)
            self.assertEqual(r["value"], "hollow", (k, r["why"], r["not_one_head"], r["extent_sp"], r["slit"]))

    def test_NEVER_the_sharp_at_the_barline_is_one_head_sized_hollow_ink(self):
        """Why the detector-box gate stays: on its own ink Sean's sharp reads as one hollow head-sized shape (no measure of the head's
        own ink tells it from a half on both plates), so it is written GUESSED, never plain (see the ADJUDICATE never below)."""
        r = _read("2_0_7_4_5_l")
        self.assertEqual(str(FX["2_0_7_4_5_l_answer"]), "sharp")
        self.assertEqual((r["value"], r["not_one_head"]), ("hollow", None), r)

    def test_paper_between_two_black_heads_is_not_one_head(self):
        """The one-head width cap keeps the paper BESIDE a head from reading hollow: Sean's eighth, a box between two black heads."""
        r = _read("2_1_7_13_1_l")
        self.assertEqual(str(FX["2_1_7_13_1_l_answer"]), "eighth")
        self.assertIsNone(r["value"])
        self.assertEqual(r["not_one_head"], "too_wide", r)

    def test_the_wide_heavy_half_stays_refused_by_the_cap(self):
        """A boundary, both sides judged: this half's own ink is wider than the cap, like the eighth's paper-between-two-heads above."""
        r = _read("6_1_5_11_1_l")
        self.assertEqual(r["not_one_head"], "too_wide", r)

    def test_an_eighth_whose_trim_reached_past_its_rim_now_reads_filled(self):
        r = _read("10_1_8_8_10_l")
        self.assertEqual(str(FX["10_1_8_8_10_l_answer"]), "eighth")
        self.assertEqual(r["value"], "filled", r)

    def test_CONTROL_flag_off_the_trim_reaches_past_the_rim_and_the_eighth_is_unread(self):
        os.environ[HI.OWN_ROWS_ENV] = "0"
        r = _read("10_1_8_8_10_l")
        self.assertNotEqual(r["value"], "filled", r)


def _cross(log, g, **kw):
    stem = log.rows(Q.STEM, CELL)[-1]
    log.observe(g, Q.NOTEHEAD_STEM_CROSS_INK, [kw["left"], kw["right"]], reader="cv_notehead_stem_cross_ink", frame="cell:0",
                stem=stem.id, total_ink_px=3000, ink_px=3000, **kw)


def _own_ink(log, g, slit, extent):
    log.observe(g, Q.HEAD_INK, "hollow", reader=READERS.CV_HEAD_INK, frame="cell:0", margin=round(slit - HI.SLIT_HOLLOW_MIN, 4),
                slit=slit, extent_sp=extent)


class TheSlashGuardAsksTheHeadsOwnInk(unittest.TestCase):
    """2.159's guard read the slash test's "ink crosses the stem" on the DETECTOR BOX. Litolff p2 `glyph/2/1/0/11/2` (a half Sean
    judged): the box is wider than one head and its ledger-line stubs cross the stem; its own ink (ledgers out) is one hollow head."""

    def _half(self, log):
        g = _part_boxed(log, located_share=None)
        # the record's own readings of glyph/2/1/0/11/2 (20261117-night): cross ink on the box, and Q.HEAD_INK on the trimmed head
        _cross(log, g, left=0.6, right=0.4, left_share=0.6, right_share=0.4, angle_deg=8.7, elongation=1.85, fill=0.6127)
        _own_ink(log, g, 0.4, [1.651, 1.524])
        return g

    def test_the_half_is_written_a_half_GUESSED(self):
        log = Log()
        g = self._half(log)
        with mock.patch.dict(os.environ, {rhythm.SLASH_GUARD_OWN_INK_ENV: "1"}):
            v = _decide(log, g)
        sig = (log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g).detail or {}).get("tremolo_slash_signal") or {}
        self.assertTrue(sig.get("crossing_ok"))
        self.assertFalse(sig.get("would_fire"))
        self.assertEqual(_w(v), 2.0)
        self.assertEqual(_guess(v)["rule"], rhythm.HEAD_INK_RULE_HOLLOW)
        self.assertTrue(_guess(v)["marks_blue"])

    def test_CONTROL_flag_off_the_box_crossing_guard_drops_it(self):
        """The rule as main has it (the box's crossing alone) fails this half: the control can fail."""
        log = Log()
        g = self._half(log)
        with mock.patch.dict(os.environ, {rhythm.SLASH_GUARD_OWN_INK_ENV: "0"}):
            v = _decide(log, g)
        self.assertNotEqual(_w(v), 2.0)

    def test_control_own_ink_not_hollow_nothing_changes(self):
        log = Log()
        g = _part_boxed(log, located_share=None)
        _cross(log, g, left=0.6, right=0.4, left_share=0.6, right_share=0.4, angle_deg=8.7, elongation=1.85, fill=0.6127)
        log.observe(g, Q.HEAD_INK, "filled", reader=READERS.CV_HEAD_INK, frame="cell:0", margin=0.06, slit=0.0, extent_sp=[1.4, 1.1])
        with mock.patch.dict(os.environ, {rhythm.SLASH_GUARD_OWN_INK_ENV: "1"}):
            v = _decide(log, g)
        self.assertNotEqual(_w(v), 2.0)
        self.assertIsNone(_guess(v))


class NeverPlainFromABoxThatIsNotAHead(unittest.TestCase):

    def test_NEVER_the_sharp_is_written_plain(self):
        """Sean's sharp at the barline (`glyph/2/0/7/4/5`, own ink one hollow head-sized shape, slit 0.33): with its box not one head's
        size it stays GUESSED (blue), never a plain note."""
        log = Log()
        g = _part_boxed(log, located_share=None)
        _own_ink(log, g, 0.3333, [1.188, 1.25])
        with mock.patch.dict(os.environ, {rhythm.SLASH_GUARD_OWN_INK_ENV: "1"}):
            v = _decide(log, g)
        gs = _guess(v)
        self.assertIsNotNone(gs)
        self.assertTrue(gs["marks_blue"])


if __name__ == "__main__":
    unittest.main()
