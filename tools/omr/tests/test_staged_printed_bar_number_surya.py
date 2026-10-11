"""ROADMAP 2.13b: the Surya rung for the printed bar number, Tesseract as the
`--no-surya` fallback.

The census behind it (`benchmarks/omr-bar-number-2026-09/FINDINGS.md` §6):
on the two acceptance movements, Tesseract on the 6-space crop decided 35
Breitkopf numerals and 22 of them were WRONG; Surya on an 8-space crop
decided 34 and none was wrong (Litolff: 7 wrong -> 0). So:

  * Surya is asked first, on its own 8-staff-space crop, filed under
    `READERS.SURYA`;
  * where Surya reads nothing, nothing else is asked -- Tesseract on exactly
    those systems was measured 5 right / 7 wrong, so a cascade would turn
    "cannot tell" into wrong numbers (CLAUDE.md rule 8);
  * Tesseract runs, exactly as before, only when Surya was not asked for
    (`--no-surya`) or cannot run here.

Positive control: a clean Surya read becomes a DECIDED verdict. Refusal
cases: an empty read is NO_INK (and Tesseract is never consulted), a read
with two digit runs reaches ADJUDICATE and abstains `not_numeric`.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from tools.omr import bar_number_text as BNT
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS

SPACING = 10.0
X_START = 80


def _staff(system_index=0, top_y=100, staff_index=0):
    line_ys = [top_y + int(i * SPACING) for i in range(5)]
    return SimpleNamespace(
        system_index=system_index, staff_index=staff_index,
        line_ys=line_ys, x_start=X_START, x_end=X_START + 400,
        top_y=top_y, line_spacing_px=SPACING)


def _pws(staves):
    rgb = np.full((400, 600, 3), 255, dtype=np.uint8)
    return SimpleNamespace(page=SimpleNamespace(page_index=0, rgb=rgb),
                           staves=staves)


class _Patched:
    """Stub both rungs; record which were asked and with which crops."""

    def __init__(self, *, surya_ok=True, surya_texts=None, surya_raises=None,
                 tess=("49", 91.0)):
        self.surya_ok = surya_ok
        self.surya_texts = surya_texts
        self.surya_raises = surya_raises
        self.tess = tess
        self.surya_crops = None
        self.tess_calls = 0

    def __enter__(self):
        self._saved = (BNT.available, BNT.read_crop,
                       BNT.surya_available, BNT.read_crops_surya)
        BNT.available = lambda: True

        def _tess(image):
            self.tess_calls += 1
            return self.tess
        BNT.read_crop = _tess
        BNT.surya_available = lambda: self.surya_ok

        def _surya(crops):
            self.surya_crops = list(crops)
            if self.surya_raises is not None:
                raise self.surya_raises
            return list(self.surya_texts[:len(crops)])
        BNT.read_crops_surya = _surya
        return self

    def __exit__(self, *exc):
        (BNT.available, BNT.read_crop,
         BNT.surya_available, BNT.read_crops_surya) = self._saved
        return False


def _rows(log):
    return [r for r in log.all_rows()
            if getattr(r, "quantity", None) == Q.PRINTED_BAR_NUMBER]


def _obs(log):
    return [r for r in _rows(log) if not hasattr(r, "reason")]


def _abs(log):
    return [r for r in _rows(log) if hasattr(r, "reason")]


def _decide(log, sub):
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.PRINTED_BAR_NUMBER, sub)


class TestSuryaFirst(unittest.TestCase):

    def test_a_surya_read_is_filed_under_SURYA_and_DECIDED(self):
        """POSITIVE CONTROL: the rung can produce an answer at all."""
        with _Patched(surya_texts=["149"]) as p:
            log = Log()
            G.gather_printed_bar_numbers(log, _pws([_staff()]), surya=True)
        obs = _obs(log)
        self.assertEqual([(o.value, o.reader) for o in obs],
                         [("149", READERS.SURYA)])
        self.assertEqual(p.tess_calls, 0, "Tesseract asked although Surya read")
        v = _decide(log, R.system(0, 0))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, 149)

    def test_the_surya_crop_is_eight_staff_spaces_wide(self):
        """The 6-space crop clipped the third digit of 3-digit numerals on
        Breitkopf (229, 263, 434 ...); 8 spaces is the measured width."""
        with _Patched(surya_texts=["149"]):
            log = Log()
            G.gather_printed_bar_numbers(log, _pws([_staff()]), surya=True)
        x0, _y0, x1, _y1 = _obs(log)[0].detail["bbox_page_px"]
        self.assertEqual(x0, X_START)
        self.assertEqual(x1 - x0, 8 * SPACING)

    def test_one_surya_call_per_page_for_every_system(self):
        staves = [_staff(system_index=0, top_y=100),
                  _staff(system_index=1, top_y=300, staff_index=1)]
        with _Patched(surya_texts=["49", "65"]) as p:
            log = Log()
            G.gather_printed_bar_numbers(log, _pws(staves), surya=True)
        self.assertEqual(len(p.surya_crops), 2)
        self.assertEqual({(o.subject.to_key(), o.value) for o in _obs(log)},
                         {("system/0/0", "49"), ("system/0/1", "65")})

    def test_an_empty_surya_read_is_NO_INK_and_tesseract_is_NOT_asked(self):
        """REFUSAL: no cascade. Tesseract where Surya was silent was
        measured 5 right / 7 wrong across both movements."""
        with _Patched(surya_texts=[""]) as p:
            log = Log()
            G.gather_printed_bar_numbers(log, _pws([_staff()]), surya=True)
        self.assertEqual(p.tess_calls, 0)
        self.assertEqual(_obs(log), [])
        self.assertEqual([(a.reason, a.reader) for a in _abs(log)],
                         [(ABSTAIN.NO_INK, READERS.SURYA)])
        v = _decide(log, R.system(0, 0))
        self.assertIs(v.outcome, Outcome.ABSTAINED)

    def test_two_digit_runs_reach_adjudicate_and_abstain_not_numeric(self):
        """REFUSAL: a stray stroke beside the numeral ("179 1", seen on
        Breitkopf at 8 spaces) is filed as read and refused as a number."""
        with _Patched(surya_texts=["179 1"]):
            log = Log()
            G.gather_printed_bar_numbers(log, _pws([_staff()]), surya=True)
        self.assertEqual([o.value for o in _obs(log)], ["179 1"])
        v = _decide(log, R.system(0, 0))
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "not_numeric")


class TestTesseractFallback(unittest.TestCase):

    def test_no_surya_reads_with_tesseract_exactly_as_before(self):
        with _Patched(surya_texts=["999"]) as p:
            log = Log()
            G.gather_printed_bar_numbers(log, _pws([_staff()]), surya=False)
        self.assertIsNone(p.surya_crops, "Surya asked under --no-surya")
        obs = _obs(log)
        self.assertEqual([(o.value, o.reader) for o in obs],
                         [("49", READERS.TESSERACT)])
        x0, _y0, x1, _y1 = obs[0].detail["bbox_page_px"]
        self.assertEqual(x1 - x0, 6 * SPACING, "the Tesseract crop changed")
        self.assertEqual([a for a in _abs(log)], [])

    def test_the_default_is_tesseract_only(self):
        with _Patched(surya_texts=["999"]) as p:
            log = Log()
            G.gather_printed_bar_numbers(log, _pws([_staff()]))
        self.assertIsNone(p.surya_crops)
        self.assertEqual([o.reader for o in _obs(log)], [READERS.TESSERACT])

    def test_surya_unavailable_falls_back_and_says_so(self):
        with _Patched(surya_ok=False, surya_texts=["999"]) as p:
            log = Log()
            G.gather_printed_bar_numbers(log, _pws([_staff()]), surya=True)
        self.assertIsNone(p.surya_crops)
        self.assertEqual([(o.value, o.reader) for o in _obs(log)],
                         [("49", READERS.TESSERACT)])
        self.assertEqual([(a.reason, a.reader) for a in _abs(log)],
                         [(ABSTAIN.READER_UNAVAILABLE, READERS.SURYA)])

    def test_surya_raising_falls_back_and_says_so(self):
        with _Patched(surya_raises=RuntimeError("server died")):
            log = Log()
            G.gather_printed_bar_numbers(log, _pws([_staff()]), surya=True)
        self.assertEqual([(o.value, o.reader) for o in _obs(log)],
                         [("49", READERS.TESSERACT)])
        self.assertEqual([(a.reason, a.reader) for a in _abs(log)],
                         [(ABSTAIN.READER_UNAVAILABLE, READERS.SURYA)])


class TestSuryaPreparation(unittest.TestCase):

    def test_the_crop_is_padded_white_and_upscaled_before_surya(self):
        """The recipe 2.85 found and this census kept: 60 px white pad,
        2x upscale, 16 tokens (8 returns empty)."""
        seen = {}
        from tools.omr import staff_labels_surya as SL
        saved = SL.read_crops_text

        def _fake(crops, **kw):
            seen["shape"] = crops[0].shape
            seen["corner"] = crops[0][0, 0].tolist()
            seen["max_tokens"] = kw.get("max_tokens")
            return ["7"]
        try:
            SL.read_crops_text = _fake
            out = BNT.read_crops_surya([np.zeros((10, 20, 3), np.uint8)])
        finally:
            SL.read_crops_text = saved
        self.assertEqual(out, ["7"])
        self.assertEqual(seen["shape"][:2], ((10 + 120) * 2, (20 + 120) * 2))
        self.assertEqual(seen["corner"], [255, 255, 255])
        self.assertEqual(seen["max_tokens"], 16)


if __name__ == "__main__":
    unittest.main()
