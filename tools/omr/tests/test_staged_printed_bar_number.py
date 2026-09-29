"""ROADMAP 2.13: the printed bar number, the gatherer, the decision, the
export-time check against the file's own count.

⚠️ THE CENTRAL TESTS ARE THE FOUR STATES ON THE GATHER SIDE (the same
contract `test_staged_direction.py` pins for `gather_direction_words`) and
the digit-parsing refusal on the ADJUDICATE side. A rehearsal LETTER printed
in the same spot as a bar number on some editions must never be coerced into
a number -- that is the one thing this item is not allowed to get wrong.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from tools.omr import bar_number_text as BNT
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import export as SX
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators.text import _bar_number_from_text
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS


# ─────────────────────────────────────────────────────────────────────────────
# 1. Digit crop -> number
# ─────────────────────────────────────────────────────────────────────────────


class TestBarNumberFromText(unittest.TestCase):

    def test_a_plain_number_reads(self):
        self.assertEqual(BNT.bar_number_from_text("49"), 49)

    def test_a_rehearsal_letter_is_refused(self):
        self.assertIsNone(BNT.bar_number_from_text("A"))
        self.assertIsNone(BNT.bar_number_from_text("Cl"))

    def test_empty_text_is_refused(self):
        self.assertIsNone(BNT.bar_number_from_text(""))

    def test_two_separate_digit_runs_are_refused_not_guessed(self):
        """CLAUDE.md rule 6: connect, never guess. Which of two runs is the
        bar number is not this function's decision to make."""
        self.assertIsNone(BNT.bar_number_from_text("12 3"))

    def test_zero_is_refused(self):
        self.assertIsNone(BNT.bar_number_from_text("0"))

    def test_an_implausibly_long_run_is_refused(self):
        self.assertIsNone(BNT.bar_number_from_text("123456"))

    def test_punctuation_around_the_digits_is_tolerated(self):
        self.assertEqual(BNT.bar_number_from_text("[49]"), 49)
        self.assertEqual(BNT.bar_number_from_text("-49-"), 49)

    def test_the_adjudicator_copy_agrees_with_the_module_on_every_case(self):
        """`adjudicators/text.py` keeps its OWN copy of this predicate
        because ADJUDICATE may import nothing that touches a raster or a
        subprocess (`bar_number_text.read_crop` imports `pytesseract`
        lazily); the two must never drift."""
        cases = ["49", "A", "", "12 3", "0", "123456", "[49]", "-49-",
                "1", "9999", "10000", "  7  ", "Cl."]
        for text in cases:
            self.assertEqual(
                BNT.bar_number_from_text(text), _bar_number_from_text(text),
                f"the two copies disagree on {text!r}")


# ─────────────────────────────────────────────────────────────────────────────
# 2. GATHER: the four states
# ─────────────────────────────────────────────────────────────────────────────


def _staff(system_index=0, top_y=100, x_start=80, spacing=10.0,
          staff_index=0):
    line_ys = [top_y + int(i * spacing) for i in range(5)]
    return SimpleNamespace(
        system_index=system_index, staff_index=staff_index,
        line_ys=line_ys, x_start=x_start, x_end=x_start + 400,
        top_y=top_y, line_spacing_px=spacing)


def _pws(staves, *, image=True):
    rgb = np.full((400, 600, 3), 255, dtype=np.uint8) if image else None
    return SimpleNamespace(page=SimpleNamespace(page_index=0, rgb=rgb),
                           staves=staves)


def _reasons(log):
    return {r.reason for r in log.all_rows()
            if getattr(r, "quantity", None) == Q.PRINTED_BAR_NUMBER
            and hasattr(r, "reason")}


class TestGatherFourStates(unittest.TestCase):

    def test_tesseract_not_installed_is_READER_UNAVAILABLE(self):
        old = BNT.available
        try:
            BNT.available = lambda: False
            log = Log()
            G.gather_printed_bar_numbers(log, _pws([_staff()]))
        finally:
            BNT.available = old
        self.assertIn(ABSTAIN.READER_UNAVAILABLE, _reasons(log))

    def test_no_staff_geometry_is_NO_STAFF_GEOMETRY(self):
        old = BNT.available
        try:
            BNT.available = lambda: True
            log = Log()
            # no image at all -- nothing to crop
            G.gather_printed_bar_numbers(log, _pws([_staff()], image=False))
        finally:
            BNT.available = old
        self.assertIn(ABSTAIN.NO_STAFF_GEOMETRY, _reasons(log))

    def test_the_rung_ran_and_read_nothing_is_NO_INK(self):
        old_avail, old_read = BNT.available, BNT.read_crop
        try:
            BNT.available = lambda: True
            BNT.read_crop = lambda image: None
            log = Log()
            G.gather_printed_bar_numbers(log, _pws([_staff()]))
        finally:
            BNT.available, BNT.read_crop = old_avail, old_read
        self.assertIn(ABSTAIN.NO_INK, _reasons(log))

    def test_a_read_numeral_is_an_OBSERVATION(self):
        old_avail, old_read = BNT.available, BNT.read_crop
        try:
            BNT.available = lambda: True
            BNT.read_crop = lambda image: ("49", 91.0)
            log = Log()
            G.gather_printed_bar_numbers(log, _pws([_staff()]))
        finally:
            BNT.available, BNT.read_crop = old_avail, old_read
        obs = [o for o in log.all_rows()
               if getattr(o, "quantity", None) == Q.PRINTED_BAR_NUMBER
               and not hasattr(o, "reason")]
        self.assertEqual([o.value for o in obs], ["49"])
        self.assertEqual(obs[0].reader, READERS.TESSERACT)
        self.assertAlmostEqual(obs[0].score, 0.91)

    def test_it_is_filed_on_the_SYSTEM_not_the_staff(self):
        old_avail, old_read = BNT.available, BNT.read_crop
        try:
            BNT.available = lambda: True
            BNT.read_crop = lambda image: ("49", 91.0)
            log = Log()
            G.gather_printed_bar_numbers(
                log, _pws([_staff(), _staff(top_y=250, staff_index=1)]))
        finally:
            BNT.available, BNT.read_crop = old_avail, old_read
        obs = [o for o in log.all_rows()
               if getattr(o, "quantity", None) == Q.PRINTED_BAR_NUMBER
               and not hasattr(o, "reason")]
        self.assertEqual(len(obs), 1, "one numeral per SYSTEM, not per staff")
        self.assertEqual(obs[0].subject, R.system(0, 0))

    def test_one_row_per_system_when_two_systems_are_on_the_page(self):
        old_avail, old_read = BNT.available, BNT.read_crop
        try:
            BNT.available = lambda: True
            BNT.read_crop = lambda image: ("49", 91.0)
            log = Log()
            staves = [_staff(system_index=0, top_y=100, staff_index=0),
                     _staff(system_index=1, top_y=300, staff_index=1)]
            G.gather_printed_bar_numbers(log, _pws(staves))
        finally:
            BNT.available, BNT.read_crop = old_avail, old_read
        obs = [o for o in log.all_rows()
               if getattr(o, "quantity", None) == Q.PRINTED_BAR_NUMBER
               and not hasattr(o, "reason")]
        self.assertEqual({o.subject.to_key() for o in obs},
                         {"system/0/0", "system/0/1"})


# ─────────────────────────────────────────────────────────────────────────────
# 3. ADJUDICATE: what the numeral means
# ─────────────────────────────────────────────────────────────────────────────


class TestTheDecision(unittest.TestCase):

    def _decide(self, log, sub=None):
        sub = sub if sub is not None else R.system(0, 0)
        log.freeze()
        adjudicate.run(log)
        return log.verdict(Q.PRINTED_BAR_NUMBER, sub)

    def test_a_digit_reading_is_DECIDED(self):
        log = Log()
        log.observe(R.system(0, 0), Q.PRINTED_BAR_NUMBER, "49",
                   reader=READERS.TESSERACT, frame=G.FRAME_BAR_NUMBER)
        v = self._decide(log)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, 49)
        self.assertEqual(v.reason, "read")

    def test_a_rehearsal_letter_ABSTAINS_not_numeric(self):
        log = Log()
        log.observe(R.system(0, 0), Q.PRINTED_BAR_NUMBER, "A",
                   reader=READERS.TESSERACT, frame=G.FRAME_BAR_NUMBER)
        v = self._decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "not_numeric")

    def test_no_rung_ran_is_ABSTAIN_no_reading(self):
        log = Log()
        log.abstain(R.system(0, 0), Q.PRINTED_BAR_NUMBER,
                   reader=READERS.TESSERACT, frame=G.FRAME_BAR_NUMBER,
                   reason=ABSTAIN.READER_UNAVAILABLE)
        v = self._decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_reading")

    def test_two_disagreeing_readings_NARROW_not_pick_one(self):
        log = Log()
        sub = R.system(0, 0)
        log.observe(sub, Q.PRINTED_BAR_NUMBER, "49",
                   reader=READERS.TESSERACT, frame=G.FRAME_BAR_NUMBER)
        log.observe(sub, Q.PRINTED_BAR_NUMBER, "48",
                   reader=READERS.TESSERACT, frame="a_second_crop")
        v = self._decide(log)
        self.assertIs(v.outcome, Outcome.NARROWED)
        self.assertEqual(sorted(c.value for c in v.candidates), [48, 49])

    def test_it_is_not_a_stub(self):
        spec = adjudicate.REGISTRY[Q.PRINTED_BAR_NUMBER]
        self.assertFalse(spec.stub)


# ─────────────────────────────────────────────────────────────────────────────
# 4. EXPORT: the numeral against the file's own count, never merged
# ─────────────────────────────────────────────────────────────────────────────


class _FakeRecord:
    """Just enough of `export.Record` for `_printed_bar_number_check`."""

    def __init__(self, verdicts):
        self._v = verdicts

    def verdict(self, quantity, subject):
        return self._v.get((quantity, subject))


def _numbering(rows):
    return {"scheme": "document", "systems": rows}


class TestPrintedBarNumberCheck(unittest.TestCase):

    def test_agreement(self):
        rec = _FakeRecord({
            (Q.PRINTED_BAR_NUMBER, "system/0/0"):
                {"outcome": "decided", "value": 1},
        })
        rows = [{"system": "0/0", "page": 0, "system_index": 0, "offset": 0}]
        rep = SX._printed_bar_number_check(rec, _numbering(rows))
        self.assertEqual(rep["agree"], 1)
        self.assertEqual(rep["disagree"], 0)
        self.assertEqual(rep["systems"][0]["state"], "agree")

    def test_disagreement_carries_the_signed_delta(self):
        """Litolff p2 drops a barline: the viewer shows 48 where the plate
        prints 49 -- the shape this item exists to surface."""
        rec = _FakeRecord({
            (Q.PRINTED_BAR_NUMBER, "system/0/1"):
                {"outcome": "decided", "value": 49},
        })
        rows = [{"system": "0/1", "page": 0, "system_index": 1, "offset": 47}]
        rep = SX._printed_bar_number_check(rec, _numbering(rows))
        self.assertEqual(rep["disagree"], 1)
        row = rep["systems"][0]
        self.assertEqual(row["file_number"], 48)
        self.assertEqual(row["printed"], 49)
        self.assertEqual(row["delta"], 1)

    def test_no_reading_ABSTAINS_and_is_never_treated_as_agreement(self):
        rec = _FakeRecord({})
        rows = [{"system": "0/0", "page": 0, "system_index": 0, "offset": 0}]
        rep = SX._printed_bar_number_check(rec, _numbering(rows))
        self.assertEqual(rep["abstained"], 1)
        self.assertEqual(rep["agree"], 0)
        self.assertEqual(rep["disagree"], 0)

    def test_a_refused_document_wide_numbering_never_gets_a_partial_compare(self):
        """`_document_bar_offsets` refuses WHOLE-FILE; the check must honour
        that rather than comparing the systems that happened to come before
        the break."""
        rec = _FakeRecord({
            (Q.PRINTED_BAR_NUMBER, "system/0/0"):
                {"outcome": "decided", "value": 1},
        })
        rows = [{"system": "0/0", "page": 0, "system_index": 0, "offset": 0}]
        numbering = {"scheme": "per_part", "systems": rows}
        rep = SX._printed_bar_number_check(rec, numbering)
        self.assertEqual(rep["agree"], 0)
        self.assertEqual(rep["abstained"], 1)
        self.assertEqual(rep["systems"][0]["reason"],
                         "document_numbering_undetermined")

    def test_it_never_writes_a_number_into_the_numbering_it_checks(self):
        """Roadmap 2.13: never renumber or insert a bar from it."""
        rec = _FakeRecord({
            (Q.PRINTED_BAR_NUMBER, "system/0/0"):
                {"outcome": "decided", "value": 5},
        })
        rows = [{"system": "0/0", "page": 0, "system_index": 0, "offset": 0}]
        numbering = _numbering(rows)
        SX._printed_bar_number_check(rec, numbering)
        self.assertEqual(numbering["systems"][0]["offset"], 0,
                         "the check must not mutate the numbering it reads")


if __name__ == "__main__":
    unittest.main()
