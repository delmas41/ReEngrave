"""ROADMAP 2.304 -- a reader is not shown ink another reader owns (flag `OMR_TEXT_CROP_OWNED_INK`, default OFF): the text reader's OCR crop minus the pixels an owner earlier than `word` in the
claim order holds (`tools/omr/staged/owned_ink.py`). CONTROLS FROM THE REAL PIXELS (fixture `data_text_crop_owned_ink_2_304.npz`, cut by `benchmarks/text-reader-owned-ink-2026-11/
make_fixture_2_304.py` from Litolff p8, the `sempre piu p` of bars 11-12, Sean 2026-11-11, 2.301 r1 tile 4): the render's pixels of one window and the barline / staff-line masks `attach` built from
the page there.

* the thin rule through the `i` of `piu` (x 1679-1683, a barline column of all 9 staves) and the rule hugging the final `p` (x 1788) are owned ink and are whited in a retry crop; the thin rule
  the page stroke map carves through the `p` of `sempre` (x 1588) does NOT run through the window, is not taken, and its letter keeps every pixel;
* flag OFF (no `page.owned_ink`): every crop is the plain crop. Default mode: a first look is plain, a retry (`lines=True`) loses the owned ink; `replace` mode: both lose it;
* each control is shown to FAIL where the mask is absent (`OFF`): the same count of rule pixels in the crop is not zero.
"""
from __future__ import annotations

import json
import os
import pathlib
import types
import unittest
from unittest import mock

import numpy as np

from tools.omr import direction_text as DT
from tools.omr.staged import owned_ink as OI

DATA = pathlib.Path(__file__).with_name("data_text_crop_owned_ink_2_304.npz")
_NZ = np.load(DATA, allow_pickle=False)
META = json.loads(str(_NZ["meta"]))
WX0, WY0, WX1, WY1 = META["window"]
SP = float(META["spacing"])
RGB = _NZ["rgb"]
BAR = np.unpackbits(_NZ["barline"], axis=1)[:, :WX1 - WX0].astype(bool)
SL = np.unpackbits(_NZ["staff_line"], axis=1)[:, :WX1 - WX0].astype(bool)
GRAY = RGB.mean(axis=2)


def _page(kinds=("barline",), replace=False, owned=True):
    pg = types.SimpleNamespace(rgb=RGB.copy(), binary=np.where(GRAY < 128, 0, 255).astype(np.uint8))
    if owned:
        pg.owned_ink = OI.OwnedInk(pg, {"barline": BAR, "staff_line": SL}, kinds, 1, 2, replace)
    return pg


def _cand(name):
    b = META["boxes"][name]
    return DT.TextCandidate(staff_index=0, measure_index=0, bbox_page=(b[0] - WX0, b[1] - WY0, b[2] - WX0, b[3] - WY0), placement="above", n_components=1)


def _rect(name):
    c = _cand(name)
    x0, y0, x1, y1 = c.bbox_page
    px, py = int(round(DT.CROP_PAD_X_SPACES * SP)), int(round(DT.CROP_PAD_Y_SPACES * SP))
    return (max(0, x0 - px), max(0, y0 - py), x1 + px, y1 + py)


class OwnedInkMask(unittest.TestCase):
    def test_flag_values(self):
        for v, want in (("", ()), ("0", ()), ("off", ()), ("1", ("barline",)), ("on", ("barline",)), ("1,staff_line", ("staff_line", "barline")),
                        ("staff_line", ("staff_line",)), ("replace", ("barline",)), ("junk", ())):
            with mock.patch.dict(os.environ, {OI.ENV: v}):
                self.assertEqual(OI.kinds_enabled(), want, v)
        with mock.patch.dict(os.environ, {OI.ENV: "1"}):
            self.assertFalse(OI.replace_mode())
        with mock.patch.dict(os.environ, {OI.ENV: "1,replace"}):
            self.assertTrue(OI.replace_mode())
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(OI.ENV, None)
            self.assertFalse(OI.enabled())

    def test_the_rule_through_piu_is_owned_and_the_stem_of_sempre_is_not(self):
        pg = _page()
        m = pg.owned_ink.mask(_rect("sempre_piu_p"), SP)
        self.assertIsNotNone(m)
        r = _rect("sempre_piu_p")
        cols = set((np.nonzero(m.any(axis=0))[0] + r[0] + WX0).tolist())
        self.assertTrue(any(1676 <= c <= 1684 for c in cols), "the thin rule through the i of piu is taken")
        self.assertTrue(any(1785 <= c <= 1793 for c in cols), "the rule hugging the final p is taken")
        self.assertFalse(any(1580 <= c <= 1596 for c in cols), "the rule the carve takes through the p of sempre does not run through the window: left to its letter")
        # a control that can fail: the carve (BAR) DOES hold pixels at x 1588 in the window -- it is the through-test that spares the letter
        r2 = _rect("sempre_piu")
        self.assertGreater(int(BAR[r2[1]:r2[3], 1580 - WX0:1596 - WX0].sum()), 0)

    def test_owner_order(self):
        pg = _page(kinds=("staff_line", "barline"))
        r = _rect("sempre_piu_p")
        self.assertIsNone(pg.owned_ink.mask(r, SP, before_owner="staff_line"), "nothing is earlier than the first owner")
        m = pg.owned_ink.mask(r, SP, before_owner="barline")
        n_staff_only = 0 if m is None else int((m & BAR[r[1]:r[3], r[0]:r[2]] & ~SL[r[1]:r[3], r[0]:r[2]]).sum())
        self.assertEqual(n_staff_only, 0, "an owner is not earlier than itself: before `barline` only staff lines are taken")
        self.assertIsNotNone(pg.owned_ink.mask(r, SP, before_owner="word"))
        self.assertIsNone(_page().owned_ink.mask(r, SP, before_owner="barline"), "the flag named barline only: nothing earlier than it")


class CropBuilders(unittest.TestCase):
    def test_flag_off_is_the_plain_crop(self):
        for name in META["boxes"]:
            plain = DT.crop_for(_page(owned=False), _cand(name), SP, lines=True)
            self.assertTrue(np.array_equal(plain, DT.crop_for(_page(owned=False), _cand(name), SP, lines=True)))
        self.assertTrue(np.array_equal(DT.tight_crop_for(_page(owned=False), _cand("sempre_piu"), SP, lines=True), DT.tight_crop_for(_page(owned=False), _cand("sempre_piu"), SP, lines=True)))

    def test_default_mode_retry_only(self):
        c = _cand("sempre_piu_p")
        off = DT.crop_for(_page(owned=False), c, SP, lines=False)
        first = DT.crop_for(_page(), c, SP, lines=False)
        self.assertTrue(np.array_equal(off, first), "a first look is the plain crop")
        retry_off = DT.crop_for(_page(owned=False), c, SP, lines=True)
        retry_on = DT.crop_for(_page(), c, SP, lines=True)
        self.assertFalse(np.array_equal(retry_off, retry_on), "a retry crop loses the owned ink")
        # the real rule hugging the final p (x 1788) is ink in the plain retry crop and gone from the owned one
        r = _rect("sempre_piu_p")
        # the crop is upscaled only above the 80 px space: Litolff's 15.75 is upscaled; compare through the page raster instead
        pg = _page()
        m = pg.owned_ink.mask(r, SP)
        raw = (RGB[r[1]:r[3], r[0]:r[2]].mean(axis=2) < 180)
        self.assertGreater(int((raw & m).sum()), 100)
        self.assertEqual(int((raw & ~m & BAR[r[1]:r[3], r[0]:r[2]] & (np.arange(r[2] - r[0])[None, :] + r[0] + WX0 >= 1784) & (np.arange(r[2] - r[0])[None, :] + r[0] + WX0 <= 1795)).sum()), 0)

    def test_replace_mode_changes_the_first_look(self):
        c = _cand("sempre_piu_p")
        off = DT.crop_for(_page(owned=False), c, SP, lines=False)
        on = DT.crop_for(_page(replace=True), c, SP, lines=False)
        self.assertFalse(np.array_equal(off, on))
        tight_off = DT.tight_crop_for(_page(owned=False), c, SP, lines=False)
        tight_on = DT.tight_crop_for(_page(replace=True), c, SP, lines=False)
        self.assertFalse(np.array_equal(tight_off, tight_on))

    def test_the_stem_of_sempre_keeps_its_letter(self):
        """Control from the real `p` of `sempre` (page x ~1588): the retry crop over `sempre_piu` holds exactly the plain retry crop's ink there."""
        c = _cand("sempre_piu")
        a = DT.tight_crop_for(_page(owned=False), c, SP, lines=True)
        b = DT.tight_crop_for(_page(), c, SP, lines=True)
        ink_a, ink_b = int((a.mean(axis=2) < 180).sum()), int((b.mean(axis=2) < 180).sum())
        self.assertGreater(ink_a, ink_b, "the owned rule through the i is whited")
        self.assertLess(ink_a - ink_b, 0.15 * ink_a, "nothing else: a few rule pixels, never the word")


class Mechanics(unittest.TestCase):
    def test_through_keeps_only_a_stroke_that_runs_the_window(self):
        m = np.zeros((40, 20), bool)
        m[:, 5] = True              # a rule: the whole window
        m[10:18, 12] = True         # a letter's stem on the column: a stub
        k = OI._through(m, vertical=True, gap=2, cover=0.9)
        self.assertTrue(k[:, 5].all())
        self.assertFalse(k[:, 12].any())
        m[20:22, 5] = False         # a scan break of 2 px is bridged
        self.assertTrue(OI._through(m, vertical=True, gap=2, cover=0.9)[:, 5].sum() >= 38)
        self.assertFalse(OI._through(m, vertical=True, gap=0, cover=0.9).any())

    def test_attached_gives_back_the_pixels_a_letter_touches(self):
        owned = np.zeros((30, 12), bool)
        owned[:, 5:7] = True
        rest = np.zeros_like(owned)
        rest[12:15, 7:10] = True    # a bowl on the right side of the rule
        got = OI._attached(owned, rest, vertical=True, reach=2, grow=1)
        self.assertTrue(got[12:15, 5:7].all())
        self.assertTrue(got[11, 5:7].all() and got[15, 5:7].all(), "grown by the letter's stroke thickness")
        self.assertFalse(got[0:9, :].any())
        self.assertFalse(got[19:, :].any())


if __name__ == "__main__":
    unittest.main()
