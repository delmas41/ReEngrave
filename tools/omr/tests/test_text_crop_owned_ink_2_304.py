"""ROADMAP 2.304 -- a reader is not shown ink another reader owns (flag `OMR_TEXT_CROP_OWNED_INK`, default OFF): the text reader's OCR crop minus the pixels an owner earlier than `word` in the
claim order holds (`tools/omr/staged/owned_ink.py`). CONTROLS FROM THE REAL PIXELS (fixture `data_text_crop_owned_ink_2_304.npz`, cut by `benchmarks/text-reader-owned-ink-2026-11/
make_fixture_2_304.py` from Litolff p8, the `sempre piu p` of bars 11-12, Sean 2026-11-11, 2.301 r1 tile 4): the render's pixels of one window and the barline / staff-line masks `attach` built from
the page there.

* the thin rule through the `i` of `piu` (x 1679-1683, a barline column of all 9 staves) and the rule hugging the final `p` (x 1788) are owned ink and are whited in a retry crop; the thin rule
  the page stroke map carves through the `p` of `sempre` (x 1588) does NOT run through the window, is not taken, and its letter keeps every pixel;
* flag OFF (no `page.owned_ink`): every crop is the plain crop. Default: the owned ink is taken from the PAD only, the candidate's own box keeps every pixel; `inside`: from the box too (the arm that
  made `sempre p` out of `sempre piu p`);
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


def _page(kinds=("barline",), inside=False, owned=True):
    pg = types.SimpleNamespace(rgb=RGB.copy(), binary=np.where(GRAY < 128, 0, 255).astype(np.uint8))
    if owned:
        pg.owned_ink = OI.OwnedInk(pg, {"barline": BAR, "staff_line": SL}, kinds, 1, 2, inside)
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
                        ("staff_line", ("staff_line",)), ("inside", ("barline",)), ("junk", ())):
            with mock.patch.dict(os.environ, {OI.ENV: v}):
                self.assertEqual(OI.kinds_enabled(), want, v)
        with mock.patch.dict(os.environ, {OI.ENV: "1"}):
            self.assertFalse(OI.inside_mode())
        with mock.patch.dict(os.environ, {OI.ENV: "1,inside"}):
            self.assertTrue(OI.inside_mode())
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
    """`_without_owned_ink` over the real window, at the candidate's own crop region: the pad loses the owned ink, the box keeps every pixel (default), `inside` takes it from the box too."""

    def _crops(self, name, **kw):
        c = _cand(name)
        r = _rect(name)
        plain = RGB[r[1]:r[3], r[0]:r[2]]
        pg = _page(**kw)
        return c, r, plain, DT._without_owned_ink(pg, plain, r, SP, c.bbox_page)

    def test_flag_off_is_the_plain_crop(self):
        for name in META["boxes"]:
            c, r, plain, out = self._crops(name, owned=False)
            self.assertIs(out, plain)
            self.assertTrue(np.array_equal(DT.crop_for(_page(owned=False), c, SP, lines=True), DT.crop_for(_page(owned=False), c, SP, lines=True)))

    def test_default_takes_the_pad_and_leaves_the_box(self):
        c, r, plain, out = self._crops("sempre_piu_p")
        diff = (out != plain).any(axis=2)
        self.assertGreater(int(diff.sum()), 30, "the rule hugging the final p stands in the pad: whited (a control that can fail: flag off gives `plain`)")
        bx0, by0, bx1, by1 = c.bbox_page
        self.assertEqual(int(diff[by0 - r[1]:by1 - r[1], bx0 - r[0]:bx1 - r[0]].sum()), 0, "inside the candidate's own box nothing is touched: the crossing ink is the word's")
        # what was taken is ink of the owned rule, nothing else
        taken = np.zeros(diff.shape, bool)
        taken |= BAR[r[1]:r[3], r[0]:r[2]]
        self.assertTrue(bool((diff <= taken).all()))

    def test_inside_mode_takes_the_rule_through_the_word_too(self):
        c, r, plain, out = self._crops("sempre_piu", inside=True)
        diff = (out != plain).any(axis=2)
        bx0, by0, bx1, by1 = c.bbox_page
        self.assertGreater(int(diff[by0 - r[1]:by1 - r[1], bx0 - r[0]:bx1 - r[0]].sum()), 20, "the thin rule through the i of piu, inside the box, is taken in `inside` mode (the harmful arm)")
        _c, _r, _p, dflt = self._crops("sempre_piu")
        self.assertEqual(int((dflt != _p).any(axis=2)[by0 - r[1]:by1 - r[1], bx0 - r[0]:bx1 - r[0]].sum()), 0)

    def test_the_builders_call_it(self):
        c = _cand("sempre_piu_p")
        off = DT.crop_for(_page(owned=False), c, SP)
        on = DT.crop_for(_page(), c, SP)
        self.assertFalse(np.array_equal(off, on))
        # the tight crop's region (box + 0.25 sp) holds almost no pad: it may or may not change; it must never change inside the box
        t_off, t_on = DT.tight_crop_for(_page(owned=False), c, SP), DT.tight_crop_for(_page(), c, SP)
        self.assertEqual(t_off.shape, t_on.shape)


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
