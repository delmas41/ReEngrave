"""ROADMAP 2.61c -- a clef candidate whose key-signature fit THREW is UNKNOWN.

GATHER (2.61) files an Abstention on `Q.KEYSIG_CLEF_FIT` for a candidate clef
whose fit raised (`READER_UNAVAILABLE`, `detail.candidate`). `adjudicate_clef`
read only the OBSERVATIONS of that quantity, so a candidate that threw read as
a candidate that did not fit -- an abstention read as a negative answer
(CLAUDE.md rule 8). The rule under test: an unknown candidate is neither
eliminated nor supported; it may still have fitted, so it is credited with the
most the fit could have given it (`W_KEYSIG_FIT`) and the winner must clear the
margin floor over THAT, or the verdict NARROWS to include it.

STAGED, ADJUDICATE. Row shapes are those of `test_staged_clef.py`.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import clef as clef_mod
from tools.omr.staged.record import ABSTAIN, Outcome, Q, READERS
from tools.omr.tests._staged_fixtures import fresh_log as _log

SUB = R.staff(0, 0, 0)


def _fit(log, clef, n=2):
    log.observe(SUB, Q.KEYSIG_CLEF_FIT, clef, reader=READERS.CV_HEADER,
                frame="header_window", n_accidentals=n)


def _threw(log, clef, error="ValueError"):
    log.abstain(SUB, Q.KEYSIG_CLEF_FIT, reader=READERS.CV_HEADER,
                frame="header_window", reason=ABSTAIN.READER_UNAVAILABLE,
                error=error, candidate=clef)


def _detector(log, glyph="clefG", score=0.95):
    log.observe(SUB, Q.CLEF_GLYPH, glyph, reader=READERS.DETECTOR,
                frame="cell:0", score=score)


def _verdict(log):
    adjudicate.run(log)
    return log.verdict(Q.CLEF, SUB)


class TestAnUnknownCandidateIsNotEliminated(unittest.TestCase):
    def test_the_fit_alone_cannot_decide_against_a_candidate_that_threw(self):
        """Only treble's fit was read; bass's THREW. The fit evidence is all
        there is, and bass might have fitted too -- so it is not ours to say
        treble."""
        log = _log()
        _fit(log, "treble")
        _threw(log, "bass")
        v = _verdict(log)
        self.assertIsNot(v.outcome, Outcome.DECIDED)
        self.assertIs(v.outcome, Outcome.NARROWED)
        self.assertIsNone(v.value)
        self.assertEqual({c.value for c in v.candidates}, {"treble", "bass"})

    def test_the_unknown_is_named_in_the_verdict_detail(self):
        log = _log()
        _fit(log, "treble")
        _threw(log, "bass")
        v = _verdict(log)
        self.assertEqual(v.detail.get("keysig_fit_unknown"), ["bass"])

    def test_a_fit_that_would_have_been_non_discriminating_does_not_stand(self):
        """treble, alto and tenor fit (3 of 4 discriminates). bass THREW: had
        it fitted, all four would, and the fit would have said nothing -- so
        treble's fit support (1.5) is not safe to count. Treble also has the
        locator (2.0): 3.5 beat alto's 1.5 by 2.0 before; without the fit
        support treble's 2.0 does not clear alto's 1.5 by the floor."""
        log = _log()
        for c in ("treble", "alto", "tenor"):
            _fit(log, c)
        _threw(log, "bass")
        log.observe(SUB, Q.CLEF_LOCATED, "treble", reader=READERS.CV_LOCATOR,
                    frame="header_window", score=0.9)
        v = _verdict(log)
        self.assertIsNot(v.outcome, Outcome.DECIDED)

    def test_nothing_else_named_means_abstain_with_the_existing_reason(self):
        """Every candidate threw and nothing else spoke: no candidates, and the
        unknowns are recorded -- never a clef."""
        log = _log()
        for c in ("treble", "bass", "alto", "tenor"):
            _threw(log, c)
        v = _verdict(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_candidates")
        self.assertEqual(sorted(v.detail.get("keysig_fit_unknown", [])),
                         ["alto", "bass", "tenor", "treble"])


class TestTheReadEvidenceStillDecidesWhenItCanAlone(unittest.TestCase):
    def test_a_strong_detector_clef_decides_despite_an_unknown_fit(self):
        """Detector 3.0 + fit 1.5 against the most bass could have had (1.5):
        the read evidence clears the floor alone, so the verdict stands."""
        log = _log()
        _detector(log)
        _fit(log, "treble")
        _threw(log, "bass")
        v = _verdict(log)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "treble")
        self.assertEqual(v.detail.get("keysig_fit_unknown"), ["bass"])

    def test_the_decided_margin_is_the_read_one(self):
        """The margin recorded is the margin of the READ scores, exactly as
        with no abstention -- the unknown does not rewrite a decided number."""
        base = _log()
        _detector(base)
        _fit(base, "treble")
        b = _verdict(base)
        with_unknown = _log()
        _detector(with_unknown)
        _fit(with_unknown, "treble")
        _threw(with_unknown, "bass")
        u = _verdict(with_unknown)
        self.assertEqual((u.value, u.margin), (b.value, b.margin))


class TestPositiveControl(unittest.TestCase):
    """No abstention anywhere: everything is as before."""

    def test_a_lone_read_fit_still_decides(self):
        log = _log()
        _fit(log, "treble")
        v = _verdict(log)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "treble")
        self.assertNotIn("keysig_fit_unknown", v.detail)

    def test_the_weights_the_tests_lean_on(self):
        """Fails loudly if a weight moves and the scenarios above stop meaning
        what their docstrings say."""
        self.assertEqual(clef_mod.W_KEYSIG_FIT, 1.5)
        self.assertEqual(clef_mod.W_DETECTOR_HIGH, 3.0)
        self.assertEqual(clef_mod.W_LOCATOR, 2.0)
        self.assertEqual(clef_mod.MARGIN_FLOOR, 1.0)
        self.assertEqual(len(clef_mod._SLOT_TABLE_CLEFS), 4)


if __name__ == "__main__":
    unittest.main()
