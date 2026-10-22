"""ROADMAP 2.29 — a SECOND, INDEPENDENT reader of the printed meter digits
(Tesseract, restricted to digits) is filed as `Q.METER_OCR` /
`Q.METER_OCR_AT_BAR` and WEIGHED against the template reader's own
`Q.METER_TEMPLATE` vote in `adjudicate_meter`, never silently.

Sean, 2026-09-29: wiring proved by MICROSCOPIC RED/GREEN tests, not pricing
runs — these are minimal, one per CONNECTION plus one CONTROL each, not a
fixture library. Each test's own docstring names which connection it proves.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tools.omr import meter_digit_ocr
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS


# ─────────────────────────────────────────────────────────────────────────────
# 1. THE READER ITSELF: split + parse + plausibility filter.
# ─────────────────────────────────────────────────────────────────────────────

class TestTheOCRReaderRefusesWhatItCannotRead(unittest.TestCase):
    """`read_meter_digits` never guesses (CLAUDE.md rule 6) — it decides
    ONLY when both halves parse as one run of digits AND the pair is a
    plausible meter. `_read_run` is monkeypatched so this proves the
    reader's OWN logic (split, parse, filter), independent of whether a
    real crop's ink is legible to Tesseract."""

    def _image(self):
        return np.zeros((40, 20), dtype=np.uint8)

    def test_a_plausible_pair_is_read(self):
        with mock.patch.object(meter_digit_ocr, "_read_run",
                               side_effect=[("9", 91.0), ("8", 87.0)]):
            found = meter_digit_ocr.read_meter_digits(self._image())
        self.assertIsNotNone(found)
        self.assertEqual((found.numerator, found.denominator), (9, 8))

    def test_CONTROL_an_impossible_denominator_is_refused(self):
        """The same reader, on ink that reads perfectly cleanly as digits,
        still abstains: "7" is not a denominator any engraver prints. A
        filter that can never refuse anything is not a filter."""
        with mock.patch.object(meter_digit_ocr, "_read_run",
                               side_effect=[("9", 91.0), ("7", 87.0)]):
            found = meter_digit_ocr.read_meter_digits(self._image())
        self.assertIsNone(found)

    def test_two_runs_of_digits_is_not_one_number(self):
        """Mirrors `bar_number_text.bar_number_from_text`'s own refusal —
        this module reuses that parser rather than re-deriving it."""
        with mock.patch.object(meter_digit_ocr, "_read_run",
                               side_effect=[("9", 91.0), ("1 2", 80.0)]):
            found = meter_digit_ocr.read_meter_digits(self._image())
        self.assertIsNone(found)


# ─────────────────────────────────────────────────────────────────────────────
# 2. GATHER: the reader is filed as Q.METER_OCR on the header crop
#    `Q.METER_TEMPLATE` already reads.
# ─────────────────────────────────────────────────────────────────────────────

class TestGatherFilesTheHeaderOCRReading(unittest.TestCase):
    """`gather._gather_meter_ocr_header` — the connection between the reader
    module and the record."""

    def _crop(self):
        return SimpleNamespace(image=np.zeros((40, 30, 3), dtype=np.uint8),
                               staff_line_ys_canonical=[4, 12, 20, 28, 36])

    def test_a_plausible_reading_is_filed(self):
        log = Log()
        sub = R.staff(0, 0, 0)
        found = meter_digit_ocr.LocatedMeterOCR(9, 8, 91.0, 87.0)
        with mock.patch.object(meter_digit_ocr, "available", return_value=True), \
             mock.patch.object(meter_digit_ocr, "read_meter_digits",
                              return_value=found):
            G._gather_meter_ocr_header(log, sub, self._crop())
        rows = log.rows(Q.METER_OCR, sub)
        self.assertEqual(len(rows), 1)
        self.assertEqual(tuple(rows[0].value), (9, 8))
        self.assertEqual(rows[0].reader, READERS.TESSERACT)

    def test_CONTROL_no_tesseract_abstains_rather_than_silently_skipping(self):
        """The abstention path can fire — a control that can never fail
        (CLAUDE.md rule 7) is not a control."""
        log = Log()
        sub = R.staff(0, 0, 0)
        with mock.patch.object(meter_digit_ocr, "available", return_value=False):
            G._gather_meter_ocr_header(log, sub, self._crop())
        self.assertEqual(len(log.rows(Q.METER_OCR, sub)), 0)
        refusals = log.refusals(Q.METER_OCR, sub)
        self.assertEqual(len(refusals), 1)
        self.assertEqual(refusals[0].reason, ABSTAIN.READER_UNAVAILABLE)


# ─────────────────────────────────────────────────────────────────────────────
# 3. ADJUDICATE: the two readers are WEIGHED, never one silently trusted.
#    This is the Brahms 1/i case the roadmap item names: the template reads
#    9/4 where the plate prints 9/8.
# ─────────────────────────────────────────────────────────────────────────────

class TestAdjudicateMeterWeighsBothReaders(unittest.TestCase):
    def _system(self, template_raw, ocr_pair, n_staves=4):
        log = Log()
        for i in range(n_staves):
            log.observe(R.staff(0, 0, i), Q.METER_TEMPLATE,
                        {"9/4": (9, 4), "9/8": (9, 8)}[template_raw],
                        reader=READERS.TEMPLATE, frame="header_window",
                        score=0.8, raw=template_raw)
            if ocr_pair is not None:
                log.observe(R.staff(0, 0, i), Q.METER_OCR, ocr_pair,
                            reader=READERS.TESSERACT, frame="header_window",
                            score=0.9)
        return log

    def test_agreement_cites_the_second_reader_but_does_not_re_decide(self):
        """Both readers say 9/8: DECIDED, exactly as a template-only vote
        would be, but the OCR rows are now named in `used` and the detail
        says so — a second witness, not a second vote."""
        log = self._system("9/8", (9, 8))
        adjudicate.run(log)
        v = log.verdict(Q.METER, R.system(0, 0))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["raw"], "9/8")
        self.assertTrue(v.detail.get("ocr_agrees"))

    def test_CONTROL_ocr_silent_leaves_the_template_vote_untouched(self):
        """No `Q.METER_OCR` rows at all: the system behaves exactly as it
        did before this item existed. Proves the new branch is INERT where
        there is nothing to weigh, not merely untested."""
        log = self._system("9/4", None)
        adjudicate.run(log)
        v = log.verdict(Q.METER, R.system(0, 0))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["raw"], "9/4")
        self.assertNotIn("ocr_agrees", v.detail)

    def test_disagreement_NARROWS_rather_than_argmaxing_a_readers_share(self):
        """The literal case ROADMAP 2.29 names: the template reads Brahms
        1/i's opening as 9/4 where OCR reads the same ink as 9/8. Neither
        reader's share may settle it by itself, and this system's bars have
        nothing to say either (no `Q.EVENT`/`Q.REST` gathered) — so the
        verdict is NARROWED, never a silent pick of either candidate."""
        log = self._system("9/4", (9, 8))
        adjudicate.run(log)
        v = log.verdict(Q.METER, R.system(0, 0))
        self.assertIs(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "template_ocr_disagree")
        seen = {(c.value["numerator"], c.value["denominator"]) for c in v.candidates}
        self.assertEqual(seen, {(9, 4), (9, 8)})


if __name__ == "__main__":
    unittest.main()
