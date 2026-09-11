"""`fermata_owner`: a pause hangs over whatever is SOUNDING beneath it.

⚠️ THE FAMILY THAT LOOKS LIKE AN ARTICULATION AND IS NOT. Every test here that
places a fermata over a REST is guarding against the obvious wrong fix, which
is to route `fermata*` through the articulation attach rule -- both classes
carry the detector's `ornament` CATEGORY, so the mistake costs one line. An
articulation names a notehead on the side its class states; a `fermataAbove`
over a whole-bar rest stands above ink it belongs to, and on a conductor's
page that rest is the commonest carrier there is.

⚠️ THE REFUSALS CARRY THEIR OWN POSITIVE CONTROL, the standard this suite
already holds: a battery of refusal tests passes by refusing EVERYTHING, so
each one sets up a case differing in ONE fact and asserts the deciding version
too.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS


def _carrier(log, gi, x, w=20.0, *, category="notehead", y=40.0,
             cls="noteheadBlackOnLine"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.GLYPH_BOX, (cls, x, y, w, 20.0),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category=category)
    return g


def _mark(log, gi, x, *, w=14.0, cls="fermataAbove", y=0.0):
    g = R.glyph(0, 0, 0, 0, gi)
    side = ("above" if cls.endswith("Above")
            else "below" if cls.endswith("Below") else None)
    log.observe(g, Q.FERMATA_MARK, cls, reader=READERS.DETECTOR,
                frame="cell:0", score=0.8,
                x0=x, x1=x + w, y0=y, y1=y + 10.0,
                x_center=x + w / 2.0, y_center=y + 5.0, side=side)
    return g


def _decide(log, gi=0):
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.FERMATA_OWNER, R.glyph(0, 0, 0, 0, gi))


class TestItIsWiredAtAllThreeLegs(unittest.TestCase):
    """⚠️ ADJUDICATOR, EMISSION AND COUNTER, because an adjudicator landing
    alone is this project's recorded trap: `articulation_owner`'s stub called
    the repair "write the adjudicator" and the tree said three, and both
    `adjudicate_dynamic` and `arc_kind` spent a day deciding into no file."""

    def test_the_registry_says_it_decides(self):
        self.assertFalse(adjudicate.REGISTRY[Q.FERMATA_OWNER].stub)

    def test_the_exporter_reads_the_verdict(self):
        import inspect
        from tools.omr.staged import export
        self.assertIn("Q.FERMATA_OWNER",
                      inspect.getsource(export._place_fermatas))

    def test_the_families_table_names_a_counter(self):
        """Without one, `coverage()` reports `decided_uncounted` -- "the
        report cannot tell" -- which is a different fact from "wrote zero"."""
        from tools.omr.staged.export import FAMILIES
        quantity, _classes, counters = FAMILIES["fermata"]
        self.assertEqual(quantity, Q.FERMATA_OWNER)
        self.assertEqual(counters, ("fermatas",))


class TestWhatItHangsOver(unittest.TestCase):

    def test_a_mark_over_a_notehead_takes_it(self):
        log = Log()
        _mark(log, 0, 100.0)                 # centre 107
        head = _carrier(log, 1, 100.0)       # spans 100-120
        v = _decide(log)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, head.to_key())
        self.assertEqual(v.reason, "contains_the_mark")
        self.assertEqual(v.detail["carrier"], "notehead")

    def test_a_mark_over_a_REST_takes_it(self):
        """⚠️ THE CASE AN ARTICULATION RULE CANNOT REACH, and the commonest
        carrier of a pause on a conductor's page."""
        log = Log()
        _mark(log, 0, 100.0)
        rest = _carrier(log, 1, 100.0, category="rest", cls="restWhole")
        v = _decide(log)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, rest.to_key())
        self.assertEqual(v.detail["carrier"], "rest")

    def test_the_SIDE_is_not_a_constraint(self):
        """⚠️ A `fermataAbove` stands ABOVE the ink it belongs to, so applying
        the articulation side test would refuse every real fermata. Here the
        mark sits above and the carrier below, which is the ORDINARY case."""
        log = Log()
        _mark(log, 0, 100.0, cls="fermataAbove", y=0.0)
        rest = _carrier(log, 1, 100.0, category="rest", y=400.0,
                        cls="restWhole")
        self.assertEqual(_decide(log).value, rest.to_key())

    def test_a_fermataBelow_is_read_and_its_side_recorded(self):
        """The renderer writes `type="upright"` unconditionally, so the side
        goes onto the record and is read by nothing -- written down rather
        than dropped at the gather site."""
        log = Log()
        _mark(log, 0, 100.0, cls="fermataBelow")
        _carrier(log, 1, 100.0)
        v = _decide(log)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.detail["side"], "below")
        self.assertEqual(v.detail["detector_class"], "fermataBelow")


class TestContainmentThenNearest(unittest.TestCase):

    def test_containment_beats_a_nearer_centre(self):
        """⚠️ THE ORDER IS THE LEGACY RULE'S. A wide carrier containing the
        mark wins over a narrow one whose CENTRE is closer, and a
        nearest-centre-only rule gets this backwards."""
        log = Log()
        _mark(log, 0, 200.0)                        # centre 207
        wide = _carrier(log, 1, 100.0, w=200.0)     # 100-300, centre 200
        _carrier(log, 2, 400.0, w=20.0)             # centre 410
        self.assertEqual(_decide(log).value, wide.to_key())

    def test_the_nearest_centre_wins_when_nothing_contains_it(self):
        """⚠️ THE FALLBACK IS LOAD-BEARING: a fermata over a bar's only rest
        is engraved at the BAR's middle while the rest sits at its own centre,
        so containment alone misses the commonest case of all."""
        log = Log()
        _mark(log, 0, 300.0)                        # centre 307
        _carrier(log, 1, 0.0)                       # centre  10
        near = _carrier(log, 2, 500.0, category="rest", cls="restWhole")
        v = _decide(log)
        self.assertEqual(v.value, near.to_key())
        self.assertEqual(v.reason, "nearest_in_bar")

    def test_the_two_branches_are_reported_apart(self):
        """A single reason would destroy the distinction between a mark that
        stood OVER its carrier and one that merely stood NEAREST it -- which
        is exactly what a cleanup count needs to rank the family."""
        reasons = adjudicate.REGISTRY[Q.FERMATA_OWNER].reasons
        self.assertIn("contains_the_mark", reasons)
        self.assertIn("nearest_in_bar", reasons)


class TestTheRefusals(unittest.TestCase):

    def test_a_bar_with_no_notehead_and_no_rest_abstains(self):
        """⚠️ A REAL POPULATION: 9 of the 46 cells holding a fermata on
        Litolff `984073` p1-3 carry neither."""
        log = Log()
        _mark(log, 0, 100.0)
        _carrier(log, 1, 100.0, category="beam", cls="beam")
        v = _decide(log)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "no_carrier")

        log2 = Log()                     # positive control: give it a carrier
        _mark(log2, 0, 100.0)
        _carrier(log2, 1, 100.0)
        self.assertEqual(_decide(log2).outcome, "decided")

    def test_a_cell_with_nothing_in_it_at_all_abstains(self):
        log = Log()
        _mark(log, 0, 100.0)
        self.assertEqual(_decide(log).reason, "no_carrier")


class TestTheVerdictIsStable(unittest.TestCase):
    def test_a_chord_names_one_member_deterministically(self):
        """⚠️ A chord's members share an x by definition, so several carriers
        contain the mark. The exporter HOISTS to the event either way, but a
        verdict moving between runs makes every A/B on this family unreadable.
        """
        seen = set()
        for _ in range(5):
            log = Log()
            _mark(log, 0, 100.0)
            for gi in (3, 1, 2):
                _carrier(log, gi, 100.0)
            seen.add(_decide(log).value)
        self.assertEqual(len(seen), 1, seen)


if __name__ == "__main__":
    unittest.main()
