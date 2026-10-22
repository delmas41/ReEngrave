"""A HEAD WITH NO STEM, ANSWERED BY A HEAD THAT SHARES ITS BEAM.

⚠️ THE CLAIM IS PHYSICAL, NOT GEOMETRIC, AND THAT IS THE MEASURED RESULT. A
beam joins stem TIPS, so every stem hanging from one stroke points the same
way. Scored LEAVE-ONE-OUT on the 1,443 heads a stem already decided
(`benchmarks/omr-stem-direction-2026-09`):

    always the commoner direction (baseline)        0.506
    where the beam SITS relative to the head        0.829   <- REFUSED
    what a head on the SAME BEAM says, majority     0.938
    what a head on the SAME BEAM says, UNANIMOUS    0.984   <- shipped

⚠️ THE 0.829 RULE IS REFUSED RATHER THAN UNBUILT, and the reason is this
quantity's consumer: `adjudicate_event`'s divisi guard reasons that an UNKNOWN
is better than a confident wrong answer, and one head in six is not an
unknown.

⚠️ THE POSITIVE CONTROLS ARE IN THE SAME CLASS AS THE REFUSALS. Most of this
tier declines -- no beam, no mate, mates that disagree, a mate that cannot
answer for itself -- and a battery of refusals passes by refusing everything.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

CELL = R.cell(0, 0, 0, 0)


def _head(log, gi, x, y=0, w=20, h=16):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead")
    return g


def _stem(log, x, y, w=3, h=60):
    log.observe(CELL, Q.STEM, (x, y, w, h), reader=READERS.CV_LINES,
                frame="cell:0", x0=x, x1=x + w, y_center=y + h / 2,
                image="no_staff", staff_lines_erased=True)


def _beam(log, x, y, w=200, h=6):
    log.observe(CELL, Q.BEAM_STROKE, (x, y, w, h), reader=READERS.CV_LINES,
                frame="cell:0", x0=x, x1=x + w, y_center=y + h / 2,
                image="no_staff", staff_lines_erased=True)


def _run(log):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.STEM_DIRECTION,))
    return log


def _v(log, gi):
    return log.verdict(Q.STEM_DIRECTION, R.glyph(0, 0, 0, 0, gi))


def _stemmed_mate_up(log, gi, x):
    """A head at `x` whose own stem rises from its right side: stem UP."""
    _head(log, gi, x)
    _stem(log, x + 18, -60, h=62)


class TestTheBeamMateTier(unittest.TestCase):

    def test_a_stemless_head_takes_its_beam_mates_direction(self):
        """POSITIVE CONTROL: the tier fires, and it fires the right way."""
        log = Log()
        _stemmed_mate_up(log, 0, 10)
        _head(log, 1, 120)                       # no stem of its own
        _beam(log, 0, -62, w=200)
        _run(log)
        self.assertEqual(_v(log, 0).value, _v(log, 1).value)
        self.assertEqual(_v(log, 1).reason, "beam_mate")
        self.assertEqual(_v(log, 1).outcome, Outcome.DECIDED)

    def test_the_verdict_cites_the_beam_and_the_mates_stem(self):
        """A borrowed answer must SAY what it borrowed from."""
        log = Log()
        _stemmed_mate_up(log, 0, 10)
        _head(log, 1, 120)
        _beam(log, 0, -62, w=200)
        _run(log)
        v = _v(log, 1)
        self.assertGreaterEqual(len(v.used), 3)
        self.assertEqual(v.detail.get("mates"), 1)
        self.assertTrue(v.detail.get("unanimous"))

    def test_its_own_stem_still_wins(self):
        """⚠️ TIER ORDER. A head that CAN be read is never borrowed for."""
        log = Log()
        _stemmed_mate_up(log, 0, 10)
        _stemmed_mate_up(log, 1, 120)
        _beam(log, 0, -62, w=200)
        _run(log)
        self.assertEqual(_v(log, 1).reason, "stem_projection")

    def test_no_beam_no_answer(self):
        log = Log()
        _stemmed_mate_up(log, 0, 10)
        _head(log, 1, 120)
        _run(log)
        self.assertEqual(_v(log, 1).reason, "no_stem")

    def test_a_beam_with_no_stemmed_mate_answers_nothing(self):
        """A beam alone is not a witness — only a head ON it that can speak."""
        log = Log()
        _head(log, 0, 10)
        _head(log, 1, 120)
        _beam(log, 0, -62, w=200)
        _run(log)
        self.assertEqual(_v(log, 1).reason, "no_stem")

    def test_mates_that_disagree_answer_nothing(self):
        """⚠️ UNANIMITY, and it is what buys 0.938 -> 0.984.

        A head standing on two strokes whose mates point opposite ways is the
        two-voice bar this quantity exists to keep straight.
        """
        log = Log()
        _stemmed_mate_up(log, 0, 10)             # stem up
        _head(log, 1, 220)                       # stem DOWN
        _stem(log, 220 + 18, 16, h=62)
        _head(log, 2, 120)                       # the stemless head
        _beam(log, 0, -62, w=200)                # catches 0 and 2
        _beam(log, 100, 80, w=200)               # catches 2 and 1
        _run(log)
        self.assertEqual(_v(log, 2).reason, "no_stem")

    def test_a_mate_that_cannot_answer_for_itself_is_not_a_witness(self):
        """⚠️ Letting a `stems_disagree` head vote would launder an ambiguity
        into a corroboration."""
        log = Log()
        _head(log, 0, 10)
        _stem(log, 10 + 18, -60, h=62)           # one stem up...
        _stem(log, 10 - 2, 16, h=62)             # ...and one down: ambiguous
        _head(log, 1, 120)
        _beam(log, 0, -62, w=200)
        _run(log)
        self.assertEqual(_v(log, 0).reason, "stems_disagree")
        self.assertEqual(_v(log, 1).reason, "no_stem")

    def test_the_head_must_stand_ON_the_beam_by_its_CENTRE(self):
        """⚠️ THE CENTRE, NOT AN OVERLAP: worth 4 points of accuracy. A head
        whose box merely grazes the end of a stroke is hanging from the next
        group, not this one."""
        log = Log()
        _stemmed_mate_up(log, 0, 10)
        _head(log, 1, 95)                        # box 95..115, centre 105
        _beam(log, 0, -62, w=100)                # span 0..100: grazes only
        _run(log)
        self.assertEqual(_v(log, 1).reason, "no_stem")

    def test_a_whole_note_under_a_beam_IS_answered_and_that_is_stated(self):
        """⚠️ A KNOWN LIMIT, PINNED RATHER THAN ASSERTED AWAY.

        A whole note carries no stem, so 9 of this document's 793 `no_stem`
        abstentions are the decision being RIGHT. This tier reads BOXES and
        the detected CLASS is not part of its evidence, so a whole note whose
        box happens to sit inside a beam's span — a whole note in one voice
        against a beamed run in another — IS answered.

        It is left that way deliberately. `Q.NOTEHEAD_CLASS` is this
        decision's DOMAIN and not a `wants`, and the FIRST tier has the
        identical exposure: a whole note whose box overlaps a neighbouring
        voice's stem already takes `stem_projection`. Excluding the class in
        one tier only would make the decision inconsistent about whether a
        whole note may have a direction at all, which is a worse state than a
        consistent gap. ⚠️ The first draft of this test asserted
        `in ("beam_mate", "no_stem")` — a disjunction that cannot fail, which
        is the vacuity this repo keeps paying for."""
        log = Log()
        g = R.glyph(0, 0, 0, 0, 1)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadWhole",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadWhole", 120, 0, 24, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                    category="notehead")
        _stemmed_mate_up(log, 0, 10)
        _beam(log, 0, -62, w=300)
        _run(log)
        self.assertEqual(_v(log, 1).reason, "beam_mate")


if __name__ == "__main__":
    unittest.main()
