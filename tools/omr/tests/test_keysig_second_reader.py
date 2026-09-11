"""The key signature's SECOND reader, and the header window it depends on.

Two mechanisms, landed together because neither is safe alone:

  * `staff_header.measure_header_window` no longer lets a mis-placed `x0`
    promote the system's own opening rule to a measure boundary. Without that,
    a system whose left edge under-runs gets header windows with no music in
    them, and `key_signature_template` answers a confident `fifths 0` — a key
    signature FABRICATED from an empty crop, which is strictly worse than the
    locator's silence.
  * `adjudicate_key_signature` consults `key_signature_template` where
    `key_signature_locator` produced no fit for the settled clef.

Measured against a hand-read print truth in
`benchmarks/omr-keysig-truth-2026-09/FINDINGS.md`.
"""

from __future__ import annotations

import unittest

import cv2
import numpy as np

from tools.omr.staff_header import measure_header_window
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.types import Barline, PageImage, PageWithStaves, Staff

SUB = R.staff(0, 0, 0)
SPACING = 20
PAGE_W, PAGE_H = 900, 600
STAFF_LEFT = 100
OPENING_RULE = 104
REAL_BARLINE = 260


def _page_with(barline_xs: list[int]) -> PageWithStaves:
    img = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
    lines = [100 + i * SPACING for i in range(5)]
    for y in lines:
        cv2.line(img, (STAFF_LEFT, y), (PAGE_W - 60, y), 0, 2)
    page = PageImage(pdf_path=None, page_index=0, dpi=300,
                     rgb=cv2.cvtColor(img, cv2.COLOR_GRAY2RGB), binary=img)
    staff = Staff(page_index=0, staff_index=0, line_ys=lines,
                  x_start=STAFF_LEFT, x_end=PAGE_W - 60, system_index=0)
    bars = [Barline(page_index=0, x=x, y_top=lines[0], y_bottom=lines[-1],
                    system_index=0) for x in barline_xs]
    return PageWithStaves(page=page, staves=[staff], barlines=bars)


class TestTheOpeningRuleMarginIsAnchoredOnTheCONSENSUS(unittest.TestCase):
    """⚠️ The margin that keeps the system's own initial rule out of the
    measure barlines used to be measured from `x0`, and `x0` comes from
    `system_left_edge`, which is a MINIMUM over one estimate per staff. A
    minimum is only as good as its worst estimate, so one under-running staff
    moves `x0` left, the opening rule clears the margin, and the window ends ON
    the rule. Measured on Beethoven 5 / Litolff p.2 system 1: ten of eleven
    staves estimate 331-347, the eleventh estimates 263, and all eleven header
    windows came out 6.2 staff spaces wide against 16.0 on every other system
    of those four pages — none of them containing a clef.

    The test is unchanged and the constant is unchanged. Only the anchor moved,
    from the minimum to the median of the same measurement."""

    def test_one_under_running_staff_no_longer_ends_the_window_on_the_rule(self):
        pws = _page_with([OPENING_RULE, REAL_BARLINE])
        # left_edge under-runs; the consensus does not. The real shape: 263
        # where ten sibling staves of the same system said 331-347.
        w = measure_header_window(pws, pws.staves[0], left_edge=20,
                                  left_consensus=STAFF_LEFT)
        self.assertEqual(w.x1, REAL_BARLINE)
        self.assertEqual(w.right_from, "barline")

    def test_THE_MUTATION_GUARD_anchoring_on_x0_reproduces_the_bug(self):
        """⚠️ The test above passes trivially for any rule that stopped
        looking at barlines at all, so this pins that the OLD anchor really
        does produce the broken window on this fixture — i.e. that the fixture
        reaches the hazard the class is named for."""
        pws = _page_with([OPENING_RULE, REAL_BARLINE])
        w = measure_header_window(pws, pws.staves[0], left_edge=20,
                                  left_consensus=20)
        self.assertEqual(w.x1, OPENING_RULE)

    def test_the_positive_control_a_REAL_first_barline_is_still_taken(self):
        """Without this, a rule that ignored every barline — making every
        header window the width cap — would look exactly like a fix."""
        pws = _page_with([OPENING_RULE, REAL_BARLINE, 500])
        w = measure_header_window(pws, pws.staves[0], left_edge=20,
                                  left_consensus=STAFF_LEFT)
        self.assertEqual(w.x1, REAL_BARLINE)
        self.assertEqual(w.right_from, "barline")

    def test_a_sound_left_edge_is_unchanged(self):
        """The overwhelming majority of windows must not move: 63 of the 75
        measured take the width cap and 1 takes a genuine barline."""
        pws = _page_with([OPENING_RULE, REAL_BARLINE])
        w = measure_header_window(pws, pws.staves[0], left_edge=STAFF_LEFT)
        self.assertEqual(w.x1, REAL_BARLINE)

    def test_the_consensus_is_a_MEDIAN_so_one_outlier_cannot_move_it(self):
        """⚠️ A mean would follow the documented heavy tail: a staff whose
        anchor landed inside the music walks left only to the first barline it
        meets and reports hundreds of pixels too large — 788, 983 and 1058 all
        occur on the four pages measured."""
        from tools.omr.staff_header import system_left_consensus
        pws = _page_with([OPENING_RULE, REAL_BARLINE])
        got = system_left_consensus(pws, 0, estimates=[340, 263, 345, 1058, 341])
        self.assertEqual(got, 341)


def _with_clef(log, clef="treble", sub=SUB):
    log.observe(sub, Q.CLEF_GLYPH, {"treble": "clefG", "bass": "clefF"}[clef],
                reader=READERS.DETECTOR, frame="cell:0", score=0.95)


class TestTheTemplateAnswersGapsOnly(unittest.TestCase):
    """⚠️ The precedence is INHERITED from the legacy path, not chosen here.
    Letting the fuller reading win instead is already priced and already
    refused: *"+1 on beet5-p2 and +2 on the Pastoral and a WRONG reading on the
    cleanest page in the corpus"*."""

    def test_the_template_answers_where_the_locator_produced_no_fit(self):
        log = Log()
        _with_clef(log, "treble")
        log.observe(SUB, Q.KEYSIG_TEMPLATE_FIT, "treble",
                    reader=READERS.TEMPLATE, frame="header_window",
                    n_accidentals=3, accidental="b", fifths=-3)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, SUB)
        self.assertEqual(v.value, -3)
        self.assertEqual(v.reason, "fitted_by_template")

    def test_the_LOCATOR_wins_where_both_speak(self):
        """The locator cannot invent a glyph; the template can match spurious
        ink. The one that can only under-count goes first."""
        log = Log()
        _with_clef(log, "treble")
        log.observe(SUB, Q.KEYSIG_CLEF_FIT, "treble", reader=READERS.CV_HEADER,
                    frame="header_window", n_accidentals=1, fifths=-1)
        log.observe(SUB, Q.KEYSIG_TEMPLATE_FIT, "treble",
                    reader=READERS.TEMPLATE, frame="header_window",
                    n_accidentals=3, fifths=-3)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, SUB)
        self.assertEqual(v.value, -1)
        self.assertEqual(v.reason, "fitted")

    def test_a_template_fit_for_ANOTHER_clef_is_not_taken(self):
        log = Log()
        _with_clef(log, "treble")
        log.observe(SUB, Q.KEYSIG_TEMPLATE_FIT, "bass", reader=READERS.TEMPLATE,
                    frame="header_window", n_accidentals=3, fifths=-3)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, SUB)
        self.assertIs(v.outcome, Outcome.ABSTAINED)

    def test_a_template_reading_of_ZERO_is_a_POSITIVE_answer(self):
        """⚠️ The claim the locator structurally cannot make, and the one that
        reaches the horns, trumpets and timpani — 18 of the 75 staff-systems
        measured print no signature at all, and abstaining there is only
        accidentally right, because MusicXML cannot say 'a reader could not
        tell'."""
        log = Log()
        _with_clef(log, "treble")
        log.observe(SUB, Q.KEYSIG_TEMPLATE_FIT, "treble",
                    reader=READERS.TEMPLATE, frame="header_window",
                    n_accidentals=0, accidental=None, fifths=0)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, 0)

    def test_no_clef_still_refuses_even_with_a_template_fit(self):
        log = Log()
        log.observe(SUB, Q.KEYSIG_TEMPLATE_FIT, "treble",
                    reader=READERS.TEMPLATE, frame="header_window",
                    n_accidentals=3, fifths=-3)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, SUB)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "needs_clef")


class TestTheTemplateDoesNotMoveTheCLEF(unittest.TestCase):
    """⚠️ THE REASON `Q.KEYSIG_TEMPLATE_FIT` IS A SEPARATE QUANTITY, asserted
    rather than trusted. `adjudicate_clef` raises one `Term` per
    `Q.KEYSIG_CLEF_FIT` row, so filing a second reader's fits there would
    double the weight of this evidence in a contest it was never measured
    against — a reading change leaking into a different decision."""

    def _clef_contest(self, template_rows: bool) -> str:
        log = Log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefC", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.9)
        log.observe(SUB, Q.CLEF_LOCATED, "alto", reader=READERS.CV_LOCATOR,
                    frame="header_window", score=0.7)
        log.observe(SUB, Q.CLEF_LOCATED, "tenor", reader=READERS.CV_LOCATOR,
                    frame="cell:0", score=0.7)
        log.observe(SUB, Q.KEYSIG_CLEF_FIT, "tenor", reader=READERS.CV_HEADER,
                    frame="header_window", n_accidentals=3, fifths=-3)
        if template_rows:
            # The template disagreeing as loudly as it can.
            log.observe(SUB, Q.KEYSIG_TEMPLATE_FIT, "alto",
                        reader=READERS.TEMPLATE, frame="header_window",
                        n_accidentals=3, fifths=-3)
        adjudicate.run(log)
        return log.verdict(Q.CLEF, SUB).value

    def test_the_clef_verdict_is_identical_with_and_without_template_rows(self):
        self.assertEqual(self._clef_contest(False), self._clef_contest(True))

    def test_and_the_control_that_the_contest_was_decidable_at_all(self):
        """A pair of equal verdicts proves nothing if both are abstentions."""
        self.assertEqual(self._clef_contest(False), "tenor")


if __name__ == "__main__":
    unittest.main()
