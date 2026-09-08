"""Ownership — and the test of the architecture's central ordering claim.

⚠️ A-ORDER-2 SAYS: identity is adjudicated BEFORE ownership, and that is what
the whole gather/adjudicate split is for. The existing pipeline cannot do it.
`_dedupe_cross_staff_detections` runs 309 lines before identity, so the
instrument's written range -- its strongest tier -- is structurally
unavailable when it decides; on a scan the tier is vacuous anyway, because
`_staff_written_ranges` returns `{}` with no dossier and the scan gate is
dossier-free by protocol. All 4,256 duplicates there resolve on ladder or
DISTANCE, 94.1% on distance alone.

The case below is the documented failure shape with the numbers made exact: a
glyph nearer the WRONG staff, where the right staff is identifiable only from
the instrument. Distance alone gets it wrong; identity-first gets it right.

⚠️ COHERENCE, NOT ACCURACY. This asserts the mechanism can express the
arbitration, not that it is right about any real page.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import (ABSTAIN, Log, Outcome, Q, READERS, Scope,
                                     State)

UPPER = R.staff(0, 0, 0)      # nearer the glyph
LOWER = R.staff(0, 0, 1)      # further, and the true owner
GLYPH = R.glyph(0, 0, 0, 0, 0)

#: Under the UPPER staff's treble clef the glyph reads G2 = MIDI 43, which is
#: below a Violin's written range (55, 100) -- IMPOSSIBLE.
POS_IN_UPPER = 20.0
#: Under the LOWER staff's bass clef it reads D3 = MIDI 50, inside a
#: Contrabass's (28, 67) -- possible.
POS_IN_LOWER = 4.0


def _contested(with_identity: bool, ladder_for=None) -> Log:
    log = Log()
    for i, (sub, name) in enumerate(((UPPER, "Violin"), (LOWER, "Contrabass"))):
        log.observe(sub, Q.STAFF_ORDINAL, i, reader=READERS.GEOMETRY,
                    frame="system")
        if with_identity:
            log.observe(sub, Q.MARGIN_LABEL, name, reader=READERS.TEXT_LAYER,
                        frame="system_margin")
        else:
            # ⚠️ Not "no label" as a convenience -- this IS the scan case.
            # Measured: 29 of 29 unresolved non-treble staves print no label
            # at all, so ownership on a scan really does run without identity.
            log.abstain(sub, Q.MARGIN_LABEL, reader=READERS.TEXT_LAYER,
                        frame="system_margin", reason=ABSTAIN.NO_INK)
    log.observe(R.system(0, 0), Q.SYSTEM_STAFF_COUNT, 2,
                reader=READERS.GEOMETRY, frame="system")

    # the contest: NEARER the upper staff, but belonging to the lower one
    log.observe(GLYPH, Q.GLYPH_BAND_DISTANCE, 1.0, reader=READERS.GEOMETRY,
                frame="page", candidate=UPPER.to_key(), own=True,
                position_in_candidate=POS_IN_UPPER)
    log.observe(GLYPH, Q.GLYPH_BAND_DISTANCE, 3.0, reader=READERS.GEOMETRY,
                frame="page", candidate=LOWER.to_key(), own=False,
                position_in_candidate=POS_IN_LOWER)
    log.observe(GLYPH, Q.GLYPH_CONF, 0.81, reader=READERS.DETECTOR,
                frame="cell:0", score=0.81)
    if ladder_for is not None:
        log.observe(GLYPH, Q.GLYPH_LADDER, True, reader=READERS.DETECTOR,
                    frame="page", candidate=ladder_for, expected=2, found=2)
    return log


class TestIdentityBeforeOwnership(unittest.TestCase):
    """⚠️ THE ARCHITECTURE'S CENTRAL CLAIM, made falsifiable."""

    def test_without_identity_DISTANCE_wins_and_gets_it_wrong(self):
        """This is today's pipeline, reproduced: nearer band takes the glyph."""
        log = _contested(with_identity=False)
        adjudicate.run(log)
        v = log.verdict(Q.GLYPH_OWNER, GLYPH)
        self.assertEqual(v.value, UPPER.to_key())
        self.assertEqual(v.reason, "distance")

    def test_with_identity_the_RANGE_VETO_overturns_it(self):
        """A veto on the IMPOSSIBLE, never on the unlikely: under the upper
        staff's clef the glyph reads MIDI 43, below a Violin's written range.
        The tier is reachable only because identity ran first."""
        log = _contested(with_identity=True)
        adjudicate.run(log)
        v = log.verdict(Q.GLYPH_OWNER, GLYPH)
        self.assertEqual(v.value, LOWER.to_key())
        self.assertEqual(v.reason, "range_veto")

    def test_the_veto_records_its_three_ancestors(self):
        """instrument + clef + the position it was computed from -- so the
        basis says what the veto rested on, and a later loop through any of
        them would be visible."""
        log = _contested(with_identity=True)
        adjudicate.run(log)
        v = log.verdict(Q.GLYPH_OWNER, GLYPH)
        kinds = {log.row(b).quantity for b in v.basis if log.row(b) is not None}
        self.assertIn(Q.INSTRUMENT, kinds)
        self.assertIn(Q.CLEF, kinds)
        self.assertIn(Q.GLYPH_BAND_DISTANCE, kinds)


class TestTheTiers(unittest.TestCase):
    def test_a_complete_ladder_outranks_distance(self):
        """⚠️ COMPLETENESS ONLY. An unbroken run of rungs joins a note to its
        staff and outranks anything broken."""
        log = _contested(with_identity=False, ladder_for=LOWER.to_key())
        adjudicate.run(log)
        v = log.verdict(Q.GLYPH_OWNER, GLYPH)
        self.assertEqual(v.value, LOWER.to_key())
        self.assertEqual(v.reason, "ladder")

    def test_a_broken_ladder_contributes_NOTHING_not_a_penalty(self):
        """Two broken ladders are not evidence either way: a found rung can
        belong to the other staff's note exactly as a gap can. On the
        Beethoven bassoon pair the ghost's one rung WAS the real C4's own
        ledger, and counting rungs beat the real note."""
        log = _contested(with_identity=False)
        log.observe(GLYPH, Q.GLYPH_LADDER, False, reader=READERS.DETECTOR,
                    frame="page", candidate=LOWER.to_key(),
                    expected=3, found=1)
        adjudicate.run(log)
        v = log.verdict(Q.GLYPH_OWNER, GLYPH)
        self.assertEqual(v.reason, "distance")   # unchanged by the broken run

    def test_confidence_is_declared_and_does_not_move_the_answer(self):
        """⚠️ P(winner conf > loser conf) = 0.545 against a 0.500 null, and a
        tie-break on it would overturn distance on 45.5% of contests. It is in
        `wants` so it must be declined DELIBERATELY, never merely unseen."""
        self.assertIn(Q.GLYPH_CONF,
                      adjudicate.REGISTRY[Q.GLYPH_OWNER].wants)
        a = _contested(with_identity=False)
        adjudicate.run(a)
        low = log_value(a)
        b = _contested(with_identity=False)
        # the same contest with the confidence inverted
        for row in list(b.rows(Q.GLYPH_CONF, GLYPH)):
            pass
        b.observe(GLYPH, Q.GLYPH_CONF, 0.02, reader=READERS.DETECTOR,
                  frame="cell:1", score=0.02)
        adjudicate.run(b)
        self.assertEqual(low, log_value(b))

    def test_an_exact_tie_ABSTAINS(self):
        """Two equal-cost mappings that disagree carry literally zero
        information; saying so beats breaking the tie on a coin flip."""
        log = Log()
        for i, sub in enumerate((UPPER, LOWER)):
            log.observe(sub, Q.STAFF_ORDINAL, i, reader=READERS.GEOMETRY,
                        frame="system")
            log.observe(GLYPH, Q.GLYPH_BAND_DISTANCE, 2.0,
                        reader=READERS.GEOMETRY, frame="page",
                        candidate=sub.to_key(), own=(i == 0),
                        position_in_candidate=4.0)
        adjudicate.run(log)
        v = log.verdict(Q.GLYPH_OWNER, GLYPH)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "tied")


class TestTheDomainIsTheContest(unittest.TestCase):
    def test_an_uncontested_glyph_gets_no_verdict_at_all(self):
        """⚠️ Not an optimisation. A glyph nobody disputes has nothing to
        arbitrate, and a verdict per detection would bury 4,521 real contests
        under tens of thousands of no-ops on a page carrying 67,000 glyphs."""
        log = Log()
        log.observe(UPPER, Q.STAFF_ORDINAL, 0, reader=READERS.GEOMETRY,
                    frame="system")
        log.observe(GLYPH, Q.GLYPH_CONF, 0.9, reader=READERS.DETECTOR,
                    frame="cell:0", score=0.9)
        adjudicate.run(log)
        self.assertIsNone(log.verdict(Q.GLYPH_OWNER, GLYPH))


def log_value(log):
    v = log.verdict(Q.GLYPH_OWNER, GLYPH)
    return None if v is None else v.value


if __name__ == "__main__":
    unittest.main()
