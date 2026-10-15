"""ROADMAP 2.141h fix 1 (STAGED ADJUDICATE `rhythm.adjudicate_duration` / `_not_a_beam_by_ink`), flag
`OMR_BEAM_LEVEL_STROKE_IS_A_BEAM`, default OFF.

Litolff p5 tile 6: a long stroke that is the LEDGER LINE the heads stand on (merged with the heads' ink, 0.82 space thick, a stem
found at one end) was counted as a second down-voice level, so printed eighths read as sixteenths (Sean: 8, 8, 8). It passes every
existing beam test (thick, straight, a stem near each end) and is not covered enough by the heads for 2.75's `through_heads`
(0.40 against a cut of 0.5). What it is NOT is a beam of the head's own stem: the stem runs 3 spaces PAST it to its tip.
Refused only with TWO witnesses from different sources: the CV stem's tip (it runs past by more than the stack a beam can occupy)
AND a detector-boxed head the stroke touches.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences          # noqa: F401
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Outcome, Q
from tools.omr.tests.test_staged_duration import _staff_space
from tools.omr.tests.test_staged_rhythm_leftovers import (_head, _ink_row, _real_stem, _stroke)

FLAG = rhythm.BEAM_STROKE_IS_A_BEAM_ENV


def _group(log, *, ledger=(226, 482, 500, 37), second=None, stems=True, tips=820):
    """Three heads on down stems (stems at the heads' left edge, tip at `tips`), the primary beam at the tips, and `ledger`: the
    stroke under the heads. `second`: a box for a REAL second level."""
    _staff_space(log, 100)
    g = _head(log, 0, (235, 355, 135, 142))
    _head(log, 1, (393, 348, 127, 118))
    _head(log, 2, (554, 354, 143, 125))
    if stems:
        for x in (244, 400, 563):
            _real_stem(log, (x, 383, 31, tips - 383))
    prim = _stroke(log, (251, 757, 350, 62))
    _ink_row(log, prim, 2.32, 0.0165, (True, True))
    if ledger:
        _ink_row(log, _stroke(log, ledger), 2.93, 0.1073, (True, False))
    if second:
        _ink_row(log, _stroke(log, second), 2.3, 0.01, (True, True))
    return g


def _levels(on, **kw):
    log = Log()
    g = _group(log, **kw)
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        adjudicate.run(log)
    return log.verdict(Q.DURATION, g)


class TestAStrokeTheStemRunsPastIsNotItsLevel(unittest.TestCase):

    def test_flag_OFF_the_ledger_line_is_counted_a_second_level_as_on_main(self):
        v = _levels(False)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beam_levels"], 2)

    def test_flag_ON_the_ledger_line_is_not_a_level_and_the_eighth_reads_RED(self):
        v = _levels(True)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beam_levels"], 1)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"stem_runs_past": 1})

    def test_CONTROL_flag_ON_a_REAL_second_level_next_to_the_primary_still_counts(self):
        v = _levels(True, ledger=None, second=(251, 690, 350, 50))
        self.assertEqual(v.value["beam_levels"], 2)
        self.assertEqual(v.value["beats"], 0.25)

    def test_CONTROL_flag_ON_a_real_second_level_AND_the_ledger_line_is_a_sixteenth_not_a_32nd(self):
        v = _levels(True, second=(251, 690, 350, 50))
        self.assertEqual(v.value["beam_levels"], 2)

    def test_CONTROL_flag_ON_a_stroke_that_touches_NO_head_is_kept_a_single_witness_does_not_refuse(self):
        # the same stroke 40 px lower: the stem still runs past it, but no head is merged with it
        v = _levels(True, ledger=(226, 520, 500, 37))
        self.assertEqual(v.value["beam_levels"], 2)

    def test_CONTROL_flag_ON_the_stem_tip_AT_the_stroke_keeps_it(self):
        # the stem ends inside the stroke: it is this stem's beam, whatever else it touches
        v = _levels(True, ledger=(226, 482, 500, 37), tips=510)
        self.assertNotIn("stem_runs_past", v.detail["beams_not_by_ink_why"])
        self.assertGreaterEqual(v.value["beam_levels"], 1)

    def test_CONTROL_flag_ON_a_head_with_no_stem_read_is_unchanged(self):
        a, b = Log(), Log()
        ga = _group(a, stems=False)
        gb = _group(b, stems=False)
        with mock.patch.dict(os.environ, {FLAG: "1"}):
            adjudicate.run(a)
        with mock.patch.dict(os.environ, {FLAG: "0"}):
            adjudicate.run(b)
        va, vb = a.verdict(Q.DURATION, ga), b.verdict(Q.DURATION, gb)
        self.assertEqual((va.outcome, va.reason), (vb.outcome, vb.reason))

    def test_the_default_is_OFF_and_a_typo_leaves_it_off(self):
        for word, on in (("", False), ("yess", False), ("0", False), ("1", True), ("true", True)):
            with mock.patch.dict(os.environ, {FLAG: word}):
                self.assertEqual(rhythm.beam_level_stroke_is_a_beam_enabled(), on, word)
        env = {k: v for k, v in os.environ.items() if k != FLAG}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(rhythm.beam_level_stroke_is_a_beam_enabled())


if __name__ == "__main__":
    unittest.main()
