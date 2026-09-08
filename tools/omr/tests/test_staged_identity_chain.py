"""The identity chain: a printed STRING becomes a name, and four decisions
downstream change because of it.

⚠️ COHERENCE, NOT ACCURACY. Nothing here asserts the lexicon is right about
any string. It asserts that the string reaches the adjudicator as a string,
that the name it produces reaches the decisions that declared it, and that
the provenance recorded is the provenance the circularity filter needs.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, evaluate
from tools.omr.staged import record as R
from tools.omr.staged import adjudicators  # noqa: F401  -- registers them
from tools.omr.staged.record import (ABSTAIN, Log, Outcome, Q, READERS, Scope,
                                     State)


def _page_with_labels(labels, blocks=(0, 0), system=0, page=0):
    """A system whose staves carry margin strings and bracket blocks."""
    log = Log()
    for i, (text, block) in enumerate(zip(labels, blocks)):
        sub = R.staff(page, system, i)
        log.observe(sub, Q.STAFF_ORDINAL, i, reader=READERS.GEOMETRY,
                    frame="system")
        if block is not None:
            log.observe(sub, Q.BRACKET_BLOCK, block, reader=READERS.GEOMETRY,
                        frame="system")
        if text is not None:
            log.observe(sub, Q.MARGIN_LABEL, text, reader=READERS.TEXT_LAYER,
                        frame="system_margin")
        else:
            log.abstain(sub, Q.MARGIN_LABEL, reader=READERS.TEXT_LAYER,
                        frame="system_margin", reason=ABSTAIN.NO_INK)
    log.observe(R.system(page, system), Q.SYSTEM_STAFF_COUNT, len(labels),
                reader=READERS.GEOMETRY, frame="system")
    return log


class TestStringToName(unittest.TestCase):
    def test_the_string_is_gathered_and_the_name_is_adjudicated(self):
        """⚠️ `StaffLabel` carries BOTH the text and a resolved instrument,
        because the reader runs the lexicon itself. GATHER must emit only the
        string -- that separation is what makes it re-interpretable, and its
        absence is what let `Tr. Alt.` become a singer at high confidence with
        the raw text sitting right beside it."""
        log = _page_with_labels(["Flauti", "Flauti"], blocks=(0, 0))
        adjudicate.run(log)
        v = log.verdict(Q.INSTRUMENT, R.staff(0, 0, 0))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["name"], "Flute")
        self.assertEqual(v.reason, "label")
        # the STRING is still on the record, unaltered
        (row,) = log.rows(Q.MARGIN_LABEL, R.staff(0, 0, 0))
        self.assertEqual(row.value, "Flauti")

    def test_an_unspellable_label_abstains_rather_than_guessing(self):
        """⚠️ Not a fallback to position. A label we cannot spell is a
        different state from a staff with no label, and guessing destroys the
        distinction the row was kept for."""
        log = _page_with_labels(["Zzzqqq", None], blocks=(0, 0))
        adjudicate.run(log)
        v = log.verdict(Q.INSTRUMENT, R.staff(0, 0, 0))
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "not_in_lexicon")

    def test_no_label_and_unreadable_label_are_different_states(self):
        """⚠️ On a scan this is the whole question: 29 of 29 unresolved
        non-treble staves print NO LABEL AT ALL -- not a lexicon refusal, not
        an OCR miss. "We could not read it" and "there was nothing to read"
        are different problems and only one is a reader problem."""
        log = _page_with_labels(["Zzzqqq", None], blocks=(0, 0))
        self.assertIs(log.state(Q.MARGIN_LABEL, R.staff(0, 0, 0)), State.READ)
        self.assertIs(log.state(Q.MARGIN_LABEL, R.staff(0, 0, 1)),
                      State.DECLINED)
        adjudicate.run(log)
        self.assertEqual(
            log.verdict(Q.INSTRUMENT, R.staff(0, 0, 0)).reason,
            "not_in_lexicon")
        self.assertEqual(
            log.verdict(Q.INSTRUMENT, R.staff(0, 0, 1)).reason, "no_evidence")


class TestTheTwoQuestionSplit(unittest.TestCase):
    """⚠️ THE SHIPPED-BUG SHAPE THIS SPLIT EXISTS TO PREVENT."""

    def test_a_two_staff_wind_pair_is_a_BRACKET_not_a_brace(self):
        """Brahms 1 p.1 reads bracket blocks `[2,2,2,2,2,7,1,3]` -- five PAIRS
        that are `2 Flöten`, `2 Oboen` and so on. All three incumbent sites
        decide the symbol by staff count (`export.py:681`, `:3523` on
        `len(staves) == 2`; `:3446` on `len(slots) == 2`), so consuming
        "block of 2" as a brace declares five wind pairs to be PIANOS."""
        log = _page_with_labels(["Flauti", "Flauti"], blocks=(0, 0))
        adjudicate.run(log)
        v = log.verdict(Q.GROUP_SYMBOL, R.system(0, 0))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "bracket")

    def test_a_real_keyboard_pair_IS_a_brace(self):
        """A brace means ONE PLAYER on two staves. The evidence is the
        instrument, not the count."""
        log = _page_with_labels(["Piano", "Piano"], blocks=(0, 0))
        adjudicate.run(log)
        v = log.verdict(Q.GROUP_SYMBOL, R.system(0, 0))
        self.assertEqual(v.value, "brace")

    def test_with_no_identity_the_symbol_ABSTAINS(self):
        """So the incumbent `len(staves) == 2` rule stands rather than being
        replaced by a guess. This is why the change is safe to land before
        identity is any good."""
        log = _page_with_labels([None, None], blocks=(0, 0))
        adjudicate.run(log)
        v = log.verdict(Q.GROUP_SYMBOL, R.system(0, 0))
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_identity")


class TestIdentityReachesTheClef(unittest.TestCase):
    def test_the_instrument_contributes_a_clef_term(self):
        """The arrow the existing pipeline cannot draw: today the instrument
        arrives 647 lines AFTER the note, so it is not available to the clef
        at all."""
        log = _page_with_labels(["Tr. Alt.", None], blocks=(0, 0))
        # no detector clef anywhere -- the instrument is the only candidate
        adjudicate.run(log)
        clef = log.verdict(Q.CLEF, R.staff(0, 0, 0))
        self.assertIs(clef.outcome, Outcome.DECIDED)
        self.assertEqual(clef.value, "bass")   # Trombone's default_clef
        self.assertIn(Q.INSTRUMENT,
                      {log.row(b).quantity for b in clef.basis
                       if log.row(b) is not None})

    def test_a_read_identity_is_admitted_into_the_clef(self):
        """⚠️ READ identity -> clef is permitted; DEDUCED identity -> clef is
        not. The asymmetry is deliberate in the codebase and the harness
        reproduces it from the basis alone -- `adjudicate_clef` contains no
        provenance code."""
        log = _page_with_labels(["Flauti", None], blocks=(0, 0))
        adjudicate.run(log)
        clef = log.verdict(Q.CLEF, R.staff(0, 0, 0))
        self.assertEqual(clef.excluded, ())

    def test_a_staff_with_no_evidence_at_all_abstains(self):
        log = _page_with_labels([None, None], blocks=(0, 0))
        adjudicate.run(log)
        clef = log.verdict(Q.CLEF, R.staff(0, 0, 0))
        self.assertIs(clef.outcome, Outcome.ABSTAINED)
        self.assertEqual(clef.reason, "no_candidates")


class TestPitchNeedsAClef(unittest.TestCase):
    def test_no_clef_means_no_pitch(self):
        """⚠️ A-EVAL-2, and the largest behavioural difference between the two
        paths. The alternative is the existing positional default -- measured
        right about half the time and INDISTINGUISHABLE ON THE RECORD from a
        reading."""
        log = _page_with_labels([None, None], blocks=(0, 0))
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 4.0,
                    reader=READERS.GEOMETRY, frame="cell:0")
        adjudicate.run(log)
        report = evaluate.run(log)
        self.assertEqual(
            [f for f in report.fired if f[0] == "restate_pitch"], [])
        skipped = [s for s in report.skipped if s[0] == "restate_pitch"]
        self.assertTrue(any(s[2] == "cause_abstained" for s in skipped))

    def test_a_clef_produces_a_pitch_carrying_both_ancestors(self):
        log = _page_with_labels(["Flauti", None], blocks=(0, 0))
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 4.0,
                    reader=READERS.GEOMETRY, frame="cell:0")
        adjudicate.run(log)
        evaluate.run(log)
        pitch = log.verdict(Q.PITCH, g)
        self.assertIsNotNone(pitch)
        quantities = {log.row(b).quantity for b in pitch.basis
                      if log.row(b) is not None}
        self.assertIn(Q.NOTEHEAD_STAFF_POSITION, quantities)
        self.assertIn(Q.CLEF, quantities)


if __name__ == "__main__":
    unittest.main()
