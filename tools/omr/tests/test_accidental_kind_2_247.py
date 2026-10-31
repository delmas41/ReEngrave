"""ROADMAP 2.247: accidentals labelled by their SHAPE (flag `OMR_ACCIDENTAL_KIND`, default OFF). Sean 2026-10-31: "Sometimes the line that goes
off the bottom of the natural is hard to see." A natural whose right upright's lower stroke is faint leaves one stem + a square, which 2.201's
flat test called a flat. Synthetic marks of KNOWN shape through the real stroke map; each control can FAIL (the flag OFF reproduces the fault)."""
import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import accidental_family as AF
from tools.omr.staged import stroke_map as SM
from tools.omr.tests.test_accidental_family_2_201 import LINES, SP, _bar, _cell, _flat, _natural, _stem


def _natural_faint(img, x=400, top=400, keep=0):
    """a natural whose right upright stops `keep` px below the lower bar (its lower stroke faint or lost)"""
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
    return AF.family_row(cls, box, res.strokes, SM.strokes_in_box(res, box), float(SP), masks=res.masks, scale=res.scale)


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


class FaintNatural(unittest.TestCase):
    def test_off_the_faint_natural_is_a_flat__the_fault(self):
        with mock.patch.dict(os.environ, {AF.KIND_ENV: "0"}):
            for keep in (0, 30, 60):
                fam = _row(_natural_faint, keep=keep)
                self.assertEqual(fam["type"], "flat", keep)

    def test_on_a_faint_natural_is_never_a_flat(self):
        with mock.patch.dict(os.environ, {AF.KIND_ENV: "1"}):
            for keep in (0, 30, 60):
                for cls in ("accidentalFlat", "accidentalNatural"):
                    fam = _row(_natural_faint, cls=cls, keep=keep)
                    self.assertEqual(fam["type"], "unclear", (keep, cls))
                    self.assertEqual(fam["why"], "stem_and_square")
                    self.assertLess(fam["features"]["shoulder_sp"], AF.FLAT_SHOULDER_MIN_SP)
                    # written GUESSED with BOTH kinds, whatever the detector called it
                    self.assertEqual(set(_cands(fam)), {"natural", "flat"})
                    self.assertEqual(AF.guess_of(fam)["chosen"]["value"], AF.type_of_class(cls))

    def test_on_a_flat_with_its_bowl_stays_a_flat(self):
        with mock.patch.dict(os.environ, {AF.KIND_ENV: "1"}):
            fam = _row(_flat)
            self.assertEqual(fam["type"], "flat")
            self.assertGreaterEqual(fam["features"]["shoulder_sp"], AF.FLAT_SHOULDER_MIN_SP)
            self.assertIsNone(AF.guess_of(fam))          # agrees with a lone flat class: unchanged, READ as before

    def test_on_a_whole_natural_still_reads_natural(self):
        with mock.patch.dict(os.environ, {AF.KIND_ENV: "1"}):
            for cls in ("accidentalFlat", "accidentalNatural"):
                self.assertEqual(_row(_natural, cls=cls)["type"], "natural")
            self.assertEqual(_row(_natural_faint, keep=100)["type"], "natural")

    def test_on_right_stem_lower_but_short_at_the_bottom_is_unclear_never_sharp(self):
        with mock.patch.dict(os.environ, {AF.KIND_ENV: "0"}):
            off = _row(_natural_short_right, cls="accidentalSharp")
        with mock.patch.dict(os.environ, {AF.KIND_ENV: "1"}):
            on = _row(_natural_short_right, cls="accidentalSharp")
        self.assertEqual(on["features"]["n_stems"], 2)
        self.assertEqual(on["why"], "right_stem_lower_bottom_short")
        self.assertEqual(on["type"], "unclear")
        self.assertEqual(set(_cands(on)), {"sharp", "natural", "flat"})   # the class stays a candidate; the shape adds its two
        self.assertNotEqual(off["why"], "right_stem_lower_bottom_short")

    def test_no_mask_cannot_tell_is_not_a_flat(self):
        with mock.patch.dict(os.environ, {AF.KIND_ENV: "1"}):
            img, raw = _cell()
            _flat(img)
            res = SM.map_strokes(img, SP, LINES, raw)
            ys, xs = np.nonzero(img == 0)
            box = (float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1))
            fam = AF.family_row("accidentalFlat", box, res.strokes, SM.strokes_in_box(res, box), float(SP))
            self.assertEqual((fam["type"], fam["why"]), ("unclear", "bowl_unmeasured"))


if __name__ == "__main__":
    unittest.main()
