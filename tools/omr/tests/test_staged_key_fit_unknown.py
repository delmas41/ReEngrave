"""ROADMAP 2.61d -- the key signature reads a THROWN clef fit as unknown.

The 2.61c pattern, in `header._staff_reading`: GATHER files an Abstention on
`Q.KEYSIG_CLEF_FIT` for a candidate clef whose fit raised
(`READER_UNAVAILABLE`, `detail.candidate`). The key signature read only the
OBSERVATIONS of that quantity, so when the SETTLED clef's fit threw it said
`run_fits_no_slot_table` -- a CONTRADICTION implicating the clef -- or
`no_run` / `no_evidence`, each a claim about a fit nobody read (CLAUDE.md
rule 8). The rule under test: the settled clef's fit being unknown is its own
abstention, `keysig_fit_unknown`; no key value moves.

STAGED, ADJUDICATE. Row shapes are those of `test_staged_clef_candidate_
abstained.py` and `test_staged_header_rhythm.py`.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Outcome, Q, READERS
from tools.omr.tests._staged_fixtures import fresh_log as _log

SUB = R.staff(0, 0, 0)


def _detector(log, glyph="clefG", score=0.95):
    log.observe(SUB, Q.CLEF_GLYPH, glyph, reader=READERS.DETECTOR,
                frame="cell:0", score=score)


def _fit(log, clef, n=3, fifths=-3):
    log.observe(SUB, Q.KEYSIG_CLEF_FIT, clef, reader=READERS.CV_HEADER,
                frame="header_window", n_accidentals=n, fifths=fifths)


def _threw(log, clef, error="ValueError"):
    log.abstain(SUB, Q.KEYSIG_CLEF_FIT, reader=READERS.CV_HEADER,
                frame="header_window", reason=ABSTAIN.READER_UNAVAILABLE,
                error=error, candidate=clef)


def _run(test, log):
    """Run, and assert the PRECONDITION: the clef is settled on treble.
    Without it every key verdict below is `needs_clef` and proves nothing."""
    adjudicate.run(log)
    clef = log.verdict(Q.CLEF, SUB)
    test.assertIs(clef.outcome, Outcome.DECIDED)
    test.assertEqual(str(clef.value), "treble")
    return log.verdict(Q.KEY_SIGNATURE, SUB)


class TestTheSettledClefsFitThrew(unittest.TestCase):
    def test_another_clefs_fit_is_not_a_contradiction_when_ours_threw(self):
        """Bass's fit was READ; treble's THREW. Treble might have fitted, so
        the run does not 'fit no slot table of the settled clef'."""
        log = _log()
        _detector(log)
        _threw(log, "treble")
        _fit(log, "bass")
        v = _run(self, log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "keysig_fit_unknown")
        self.assertIn("treble", v.detail["keysig_fit_unknown"])

    def test_the_only_fit_threw_is_unknown_not_no_evidence(self):
        log = _log()
        _detector(log)
        _threw(log, "treble")
        v = _run(self, log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "keysig_fit_unknown")


class TestControls(unittest.TestCase):
    """Each passes on the unrepaired tree and must still pass: the change is
    confined to a settled clef whose own fit THREW."""

    def test_our_fit_ran_and_found_nothing_is_still_a_contradiction(self):
        """Treble's fit RAN (no row, no refusal) and alto's threw: the run
        still fits no slot table of the settled clef."""
        log = _log()
        _detector(log)
        _threw(log, "alto")
        _fit(log, "bass")
        v = _run(self, log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "run_fits_no_slot_table")

    def test_a_template_for_the_settled_clef_still_answers(self):
        """A second reader that DID answer for treble is not overruled by the
        first reader's failure."""
        log = _log()
        _detector(log)
        _threw(log, "treble")
        log.observe(SUB, Q.KEYSIG_TEMPLATE_FIT, "treble",
                    reader=READERS.CV_HEADER, frame="header_window",
                    fifths=-2, n_accidentals=2)
        v = _run(self, log)
        self.assertEqual(v.value, -2)
        self.assertEqual(v.reason, "fitted_no_markers")

    def test_the_settled_clefs_own_fit_still_answers(self):
        log = _log()
        _detector(log)
        _threw(log, "alto")
        _fit(log, "treble", n=2, fifths=2)
        v = _run(self, log)
        self.assertEqual(v.value, 2)


if __name__ == "__main__":
    unittest.main()
