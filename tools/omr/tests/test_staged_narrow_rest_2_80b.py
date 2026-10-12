"""ROADMAP 2.80b -- a narrow "notehead" that is an eighth rest, read on ITS OWN
ink and never off the bar.

Sean, 2026-10-11, tile 1 of `out/print/2.80-review/` (Brahms Contrabass bar 13,
the blue mark): *"It is an 8th note rest"*. The detector boxed the rest's blob
as `noteheadBlackInSpace`, 0.67 spaces wide; ADJUDICATE refused it `too_narrow`.

`adjudicate_narrow_box_is_an_eighth_rest` reads `Q.NARROW_BOX_SHAPE` (GATHER's
measurement of the ink under a narrow box) on a box already refused
`too_narrow`; EVALUATE's `size_reinstated_rest` gives a `True` an eighth's
length; the bar the rest stands in is never consulted to decide it.

Every refusal below carries its positive control in the same class: the shape
that is NOT a rest stays refused, the shape that is one is reinstated, and the
one witness each `False`/abstention lacks is supplied in its twin test. Tests
named `*_RED` fail on the tree without the decision (the quantity does not
exist there).
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, consequences
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict

CELL = R.cell(0, 0, 0, 2)


def _verdict(log, sub, q, outcome, value, reason="t", detail=None):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome,
        value=value, decider="test", reason=reason, detail=detail or {}))


def _shape(log, gi, *, w=1.12, h=2.25, step=4.1, pieces=2, edge=False,
           others=(), fill=0.5):
    g = R.glyph(0, 0, 0, 2, gi)
    log.observe(g, Q.NARROW_BOX_SHAPE, h, reader=READERS.CV_NARROW_BOX_SHAPE,
                frame="cell:2", n_pieces=pieces, width_spaces=w,
                height_spaces=h, staff_step=step, fill=fill,
                touches_cell_edge=edge,
                overlapping_detections=list(others),
                bbox_page_px=[0.0, 0.0, 10.0, 10.0])
    return g


def _refused(log, g, reason="too_narrow"):
    return _verdict(log, g, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Outcome.DECIDED,
                    True, reason=reason)


def _decide(log, g):
    log.freeze()
    adjudicate._ensure_decisions()
    return log


def _run(log, g, setup=lambda: None):
    _decide(log, g)
    setup()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_AN_EIGHTH_REST,))
    return log.verdict(Q.NOTEHEAD_IS_AN_EIGHTH_REST, g)


def _case(*, refusal="too_narrow", **shape):
    log = Log()
    g = _shape(log, 0, **shape)
    log.freeze()
    adjudicate._ensure_decisions()
    if refusal:
        _refused(log, g, refusal)
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_AN_EIGHTH_REST,))
    return log, g, log.verdict(Q.NOTEHEAD_IS_AN_EIGHTH_REST, g)


class TestTheDecision(unittest.TestCase):

    def test_a_rest_shaped_refused_narrow_box_is_an_eighth_rest_RED(self):
        """The Contrabass-13 shape: 1.12 x 2.25 spaces, two pieces, hung on
        the middle of the staff."""
        _log, _g, v = _case()
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest8th_shape")

    def test_it_records_the_two_rows_it_stood_on_and_the_shape(self):
        """What the verdict RECORDS: the refusal and the shape row it used,
        nothing it did not declare, and the measurements in `detail`."""
        log, g, v = _case()
        shape_row = log.rows(Q.NARROW_BOX_SHAPE, g)[-1]
        refusal = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertEqual(set(v.used), {refusal.id, shape_row.id})
        self.assertEqual(v.missing, ())
        self.assertEqual(v.declined, ())
        self.assertEqual(v.detail["height_spaces"], 2.25)
        self.assertEqual(v.detail["staff_step"], 4.1)
        self.assertEqual(v.detail["n_pieces"], 2)

    def test_the_decision_reads_no_bar(self):
        """⚠️ THE RULE, ASSERTED OFF THE REGISTRY: no meter, event, duration
        or voice quantity is declared, so none can be read (Evidence refuses
        an undeclared read). A bar's length is not evidence about a mark."""
        wants = set(adjudicate.REGISTRY[Q.NOTEHEAD_IS_AN_EIGHTH_REST].wants)
        for q in (Q.METER, Q.EVENT, Q.DURATION, Q.VOICES, Q.ONSET_COLUMN):
            self.assertNotIn(q, wants)

    def test_not_refused_too_narrow_abstains_POSITIVE_CONTROL(self):
        """The same ink under a box refused for ANOTHER reason (or not
        refused) is not this decision's to read."""
        for refusal in ("clipped_fragment", None):
            _l, _g, v = _case(refusal=refusal)
            self.assertIs(v.outcome, Outcome.ABSTAINED, refusal)
            self.assertEqual(v.reason, "not_refused_as_too_narrow")

    def test_a_real_narrow_non_rest_stays_refused(self):
        """A crumb (0.3 x 0.9), a head with its stem (1.3 x 3.9) and a quarter
        rest's height are decisively NOT an eighth rest: False, never True."""
        for w, h in ((0.3, 0.9), (1.3, 3.9), (1.2, 3.1 + 0.3)):
            _l, _g, v = _case(w=w, h=h, pieces=1)
            self.assertIs(v.value, False, (w, h))
            self.assertEqual(v.reason, "not_rest_shaped")

    def test_a_barline_remnant_at_the_cell_edge_does_not_decide(self):
        """Right size, right height -- touching the cell's edge: abstain."""
        _l, _g, v = _case(edge=True)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "shape_cannot_tell")
        _l, _g, v = _case(edge=False)               # the twin: True
        self.assertIs(v.value, True)

    def test_off_the_middle_of_the_staff_abstains(self):
        _l, _g, v = _case(step=1.0)
        self.assertEqual(v.reason, "shape_cannot_tell")
        _l, _g, v = _case(step=4.9)                 # inside the window
        self.assertIs(v.value, True)

    def test_an_in_between_size_abstains_it_does_not_guess(self):
        """1.7 x 2.9 is bigger than an eighth rest and smaller than a
        decisive 'no': the shape cannot tell, so the bar stays held out."""
        _l, _g, v = _case(w=1.7, h=2.9)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "shape_cannot_tell")

    def test_no_ink_under_the_box_abstains(self):
        log = Log()
        g = R.glyph(0, 0, 0, 2, 0)
        log.observe(g, Q.NARROW_BOX_SHAPE, 0.0,
                    reader=READERS.CV_NARROW_BOX_SHAPE, frame="cell:2",
                    n_pieces=0)
        log.freeze()
        adjudicate._ensure_decisions()
        _refused(log, g)
        adjudicate.run(log, order=(Q.NOTEHEAD_IS_AN_EIGHTH_REST,))
        self.assertEqual(log.verdict(Q.NOTEHEAD_IS_AN_EIGHTH_REST, g).reason,
                         "no_ink_under_box")


class TestInkAnotherGlyphAlreadyReads(unittest.TestCase):
    """Glyph 11 of the same bar is a SECOND narrow box over the FIRST eighth
    rest, which the detector boxed correctly (`rest8th`, kept). Its ink is
    already a rest, so it is a duplicate, not a missed mark."""

    def _two(self, *, other_class, other_verdict):
        log = Log()
        g = _shape(log, 1, others=[{"glyph": 0, "class": other_class}])
        other = R.glyph(0, 0, 0, 2, 0)
        log.freeze()
        adjudicate._ensure_decisions()
        _refused(log, g)
        if other_verdict is not None:
            q, val = other_verdict
            _verdict(log, other, q, Outcome.DECIDED, val)
        adjudicate.run(log, order=(Q.NOTEHEAD_IS_AN_EIGHTH_REST,))
        return log.verdict(Q.NOTEHEAD_IS_AN_EIGHTH_REST, g)

    def test_a_standing_rest_over_the_same_ink_makes_it_a_duplicate(self):
        v = self._two(other_class="rest8th",
                      other_verdict=(Q.REST_IS_NOT_A_REST, False))
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "ink_already_read_as_a_glyph")

    def test_a_REFUSED_rest_over_the_same_ink_is_no_claim_POSITIVE_CONTROL(self):
        v = self._two(other_class="rest8th",
                      other_verdict=(Q.REST_IS_NOT_A_REST, True))
        self.assertIs(v.value, True)

    def test_a_standing_notehead_over_the_same_ink_is_a_claim(self):
        v = self._two(other_class="noteheadBlackOnLine",
                      other_verdict=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, False))
        self.assertIs(v.value, False)

    def test_another_class_over_the_ink_abstains(self):
        """A flag, a beam: ink this decision cannot see past."""
        v = self._two(other_class="flag8thUp", other_verdict=None)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "claimed_by_another_class")

    def test_an_undecided_neighbour_abstains(self):
        v = self._two(other_class="rest8th", other_verdict=None)
        self.assertIs(v.outcome, Outcome.ABSTAINED)


class TestSizeReinstatedRest(unittest.TestCase):
    """EVALUATE: a reinstated rest takes an eighth; the bar then ADDS UP with
    no note changed -- and the bar had no say in whether it was a rest."""

    CELL = R.cell(0, 0, 0, 2)

    def _bar(self, *, reinstated):
        """6/8 = 3.0 quarters: an eighth note read with one beam too few
        (so `reconcile_duration` WOULD stretch it), two kept eighth rests, a
        kept quarter rest, and the narrow box that is the second rest."""
        log = Log()

        def dur(g, beats, levels=0, rest=False):
            sub = R.glyph(0, 0, 0, 2, g)
            v = {"beats": beats, "written": beats, "dots": 0,
                 "beam_levels": levels}
            if rest:
                v["is_rest"] = True
            _verdict(log, sub, Q.DURATION, Outcome.DECIDED, v,
                     reason="rest_class" if rest else "head_and_marks")
            return sub

        dur(0, 0.5, 1)                       # the eighth note
        dur(1, 0.5, rest=True)               # first eighth rest
        narrow = dur(2, 1.0)                 # the narrow box, read as a head
        dur(3, 1.0, rest=True)               # quarter rest
        dur(4, 0.5, rest=True)               # last eighth rest
        _verdict(log, self.CELL, Q.EVENT, Outcome.DECIDED,
                 {"events": [{"glyphs": [g]} for g in range(5)]})
        _verdict(log, narrow, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Outcome.DECIDED,
                 True, reason="too_narrow")
        if reinstated:
            _verdict(log, narrow, Q.NOTEHEAD_IS_AN_EIGHTH_REST,
                     Outcome.DECIDED, True, reason="rest8th_shape")
        # the ink was READ and, with the rest counted, nothing is left over
        from tools.omr.tests.test_staged_missed_rest_2_80 import clear_ink
        clear_ink(log, self.CELL)
        meter = _verdict(log, R.system(0, 0), Q.METER, Outcome.DECIDED,
                         {"numerator": 6, "denominator": 8, "raw": "6/8"})
        return log, narrow, meter

    def test_the_rest_takes_an_eighth_and_supersedes_the_head_reading_RED(self):
        log, narrow, _m = self._bar(reinstated=True)
        v = log.verdict(Q.NOTEHEAD_IS_AN_EIGHTH_REST, narrow)
        out = consequences.size_reinstated_rest(log, narrow, v)
        self.assertEqual(len(out), 1)
        now = log.verdict(Q.DURATION, narrow)
        self.assertEqual(now.value["beats"], 0.5)
        self.assertTrue(now.value["is_rest"])
        self.assertEqual(now.decider, "size_reinstated_rest")

    def test_it_is_idempotent(self):
        log, narrow, _m = self._bar(reinstated=True)
        v = log.verdict(Q.NOTEHEAD_IS_AN_EIGHTH_REST, narrow)
        consequences.size_reinstated_rest(log, narrow, v)
        self.assertEqual(consequences.size_reinstated_rest(log, narrow, v), [])

    def test_a_False_or_abstained_verdict_writes_nothing(self):
        for outcome, value in ((Outcome.DECIDED, False),
                               (Outcome.ABSTAINED, None)):
            log, narrow, _m = self._bar(reinstated=False)
            v = _verdict(log, narrow, Q.NOTEHEAD_IS_AN_EIGHTH_REST, outcome,
                         value)
            self.assertEqual(
                consequences.size_reinstated_rest(log, narrow, v), [])

    def test_with_the_rest_the_bar_adds_up_and_no_note_is_changed_RED(self):
        log, narrow, meter = self._bar(reinstated=True)
        consequences.size_reinstated_rest(
            log, narrow, log.verdict(Q.NOTEHEAD_IS_AN_EIGHTH_REST, narrow))
        out = consequences.reconcile_duration(log, self.CELL, meter)
        self.assertEqual(out, [])            # 3.0 already: nothing to re-read
        self.assertEqual(
            log.verdict(Q.DURATION, R.glyph(0, 0, 0, 2, 0)).value["beats"],
            0.5)

    def test_without_the_reading_the_old_repair_is_what_happens_CONTROL(self):
        """The bar WITHOUT the rest is short by an eighth and (ink read
        clear) the old repair stretches the eighth note. That the reading is
        what prevents it -- not an accident of the fixture -- is this test."""
        log, narrow, meter = self._bar(reinstated=False)
        out = consequences.reconcile_duration(log, self.CELL, meter)
        self.assertEqual(len(out), 1)
        self.assertEqual(
            log.verdict(Q.DURATION, R.glyph(0, 0, 0, 2, 0)).value["beats"],
            1.0)

    def test_a_reinstated_box_is_in_its_bar_not_left_it(self):
        log, narrow, _m = self._bar(reinstated=True)
        self.assertIsNone(consequences._left_the_bar(log, narrow))
        log2, narrow2, _m2 = self._bar(reinstated=False)
        self.assertIsNotNone(consequences._left_the_bar(log2, narrow2))


if __name__ == "__main__":
    unittest.main()
