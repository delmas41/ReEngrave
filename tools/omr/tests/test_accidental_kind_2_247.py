"""ROADMAP 2.247: accidentals labelled by their SHAPE (flag `OMR_ACCIDENTAL_KIND`, default OFF). Sean 2026-10-31: "Sometimes the line that goes
off the bottom of the natural is hard to see." 2.201's flat test ("one stem + a piece low to its right") calls a STUB of a natural (a short piece
of its left upright + a bit of a bar, its right upright faint or cut away) a flat. With the flag a one-stem flat must be FLAT-SIZED (SMuFL glyph,
0.7 share); a smaller reading is `unclear`, written GUESSED with natural AND flat. Synthetic marks of KNOWN shape through the real stroke map;
each control can FAIL (the flag OFF reproduces the fault)."""
import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import accidental_family as AF
from tools.omr.staged import stroke_map as SM
from tools.omr.tests.test_accidental_family_2_201 import LINES, SP, _bar, _cell, _flat, _natural, _stem


def _natural_stub(img, x=400, top=400):
    """the lower-left of a natural: 1.5 sp of its left upright and its lower bar; the right upright faint (not printed)"""
    _stem(img, x, top + 100, top + 250)
    _bar(img, (x, top + 230), (x + 60, top + 200), 22)


def _natural_faint(img, x=400, top=400, keep=0):
    """a FULL natural whose right upright stops `keep` px below the lower bar"""
    _stem(img, x, top, top + 240)
    _stem(img, x + 60, top + 140, top + 215 + keep)
    _bar(img, (x, top + 170), (x + 60, top + 140), 22)
    _bar(img, (x, top + 245), (x + 60, top + 215), 22)


def _natural_short_right(img, x=400, top=400):
    """two stems, the right one's top a space lower (a natural's offset) but its bottom far above the left's"""
    _stem(img, x, top, top + 360)
    _stem(img, x + 60, top + 100, top + 260)
    _bar(img, (x, top + 170), (x + 60, top + 140), 22)
    _bar(img, (x, top + 235), (x + 60, top + 205), 22)


def _row(draw, cls="accidentalFlat", **kw):
    img, raw = _cell()
    draw(img, **kw)
    res = SM.map_strokes(img, SP, LINES, raw)
    ys, xs = np.nonzero(img == 0)
    box = (float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1))
    return AF.family_row(cls, box, res.strokes, SM.strokes_in_box(res, box), float(SP))


def _cands(fam):
    g = AF.guess_of(fam)
    return [c["value"] for c in g["candidates"]] if g else []


class KindFlag(unittest.TestCase):
    def test_default_off_deny_list(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(AF.KIND_ENV, None)
            self.assertFalse(AF.kind_enabled())
        for v, on in (("1", True), ("true", True), ("on", True), ("0", False), ("off", False), ("", False)):
            with mock.patch.dict(os.environ, {AF.KIND_ENV: v}):
                self.assertEqual(AF.kind_enabled(), on, v)

    def test_floors_are_the_glyph_share(self):
        self.assertAlmostEqual(AF.FLAT_STEM_MIN_SP, 0.7 * 2.456, places=2)
        self.assertAlmostEqual(AF.FLAT_BOWL_MIN_SP, 0.84, places=2)


class NaturalStub(unittest.TestCase):
    def test_off_a_natural_stub_is_a_flat__the_fault(self):
        with mock.patch.dict(os.environ, {AF.KIND_ENV: "0"}):
            self.assertEqual(_row(_natural_stub)["type"], "flat")

    def test_on_a_natural_stub_is_never_a_flat(self):
        with mock.patch.dict(os.environ, {AF.KIND_ENV: "1"}):
            for cls in ("accidentalFlat", "accidentalNatural", "accidentalSharp"):
                fam = _row(_natural_stub, cls=cls)
                self.assertEqual((fam["type"], fam["why"]), ("unclear", "flat_too_small"), cls)
                self.assertLess(fam["margin"], 0)
                cands = _cands(fam)
                self.assertTrue({"natural", "flat"} <= set(cands), cls)     # written GUESSED with both, whatever the class
                self.assertEqual(AF.guess_of(fam)["chosen"]["value"], AF.type_of_class(cls))

    def test_on_a_flat_stays_a_flat_and_unchanged(self):
        with mock.patch.dict(os.environ, {AF.KIND_ENV: "1"}):
            fam = _row(_flat)
            self.assertEqual(fam["type"], "flat")
            self.assertGreaterEqual(fam["features"]["bowl_h_sp"], AF.FLAT_BOWL_MIN_SP)
            self.assertIsNone(AF.guess_of(fam))          # agrees with a lone flat class: READ as before

    def test_on_a_whole_natural_still_reads_natural(self):
        with mock.patch.dict(os.environ, {AF.KIND_ENV: "1"}):
            for cls in ("accidentalFlat", "accidentalNatural"):
                self.assertEqual(_row(_natural, cls=cls)["type"], "natural")
            self.assertEqual(_row(_natural_faint, keep=100)["type"], "natural")

    def test_known_limit_a_full_size_natural_with_its_lower_stroke_lost_still_reads_flat(self):
        # NOT fixed (benchmarks/accidental-kind-2026-10): a glyph-sized left upright + square passes the size floor, and the bowl-shoulder
        # cue that would separate it failed on Sean's hand-box flats. Kept as a test so a later fix is seen.
        with mock.patch.dict(os.environ, {AF.KIND_ENV: "1"}):
            self.assertEqual(_row(_natural_faint, keep=0)["type"], "flat")

    def test_on_right_stem_lower_but_short_at_the_bottom_is_unclear_never_sharp(self):
        with mock.patch.dict(os.environ, {AF.KIND_ENV: "0"}):
            off = _row(_natural_short_right, cls="accidentalSharp")
        with mock.patch.dict(os.environ, {AF.KIND_ENV: "1"}):
            on = _row(_natural_short_right, cls="accidentalSharp")
        self.assertEqual(on["features"]["n_stems"], 2)
        self.assertEqual((on["type"], on["why"]), ("unclear", "right_stem_lower_bottom_short"))
        self.assertEqual(set(_cands(on)), {"sharp", "natural", "flat"})   # the class stays a candidate; the shape adds its two
        self.assertNotEqual(off["why"], "right_stem_lower_bottom_short")


if __name__ == "__main__":
    unittest.main()
