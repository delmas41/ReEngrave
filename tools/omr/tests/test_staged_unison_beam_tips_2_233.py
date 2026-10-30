"""ROADMAP 2.233 (STAGED ADJUDICATE, flag `OMR_UNISON_BEAM_TIPS`, default OFF): a one-head-two-voices (unison) head whose voices the box readers read
DIFFERENTLY is read from each stem's own tip by the stroke map; both tips counting the same beams decides that level.

MEASURED REACH ON THE 20261029-NIGHT LITOLFF SAMPLE IS ZERO (benchmarks/value-undecided-2026-10/FINDINGS.md): on every narrowed unison head the
stroke map agrees with the box readers that the UP stem carries no beam at its tip. These tests pin what the flag must NOT do (move any
reading with no stroke map, decide when the tips differ, change a head when it is OFF); the positive case has no real-geometry fixture because
no real head reached it.
Constructed cells only."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences          # noqa: F401
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Outcome, Q
from tools.omr.tests.test_staged_duration import _staff_space
from tools.omr.tests.test_staged_rhythm_leftovers import _head, _ink_row, _real_stem, _stroke

FLAG = rhythm.UNISON_BEAM_TIPS_ENV


def _differing_voices():
    """One head, a stem each way; the up voice one beam, the down voice two (the 2.75 control cell): NARROWED [1, 2] with no stroke map."""
    log = Log()
    _staff_space(log, 100)
    g = _head(log, 0, (143, 523, 139, 124))
    _real_stem(log, (261, 351, 19, 311))          # up
    _real_stem(log, (146, 560, 26, 413))          # down
    up = _stroke(log, (255, 343, 622, 64))
    d1 = _stroke(log, (154, 895, 628, 70))
    d2 = _stroke(log, (154, 840, 628, 40))
    for st in (up, d1, d2):
        _ink_row(log, st, 2.3, 0.01, (True, True))
    return log, g


def _run(flag):
    log, g = _differing_voices()
    with mock.patch.dict(os.environ, {FLAG: flag}):
        adjudicate.run(log)
    return log.verdict(Q.DURATION, g)


class TestTheFlag(unittest.TestCase):
    def test_default_is_OFF(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG, None)
            self.assertFalse(rhythm.unison_beam_tips_enabled())

    def test_the_on_words(self):
        for w in ("1", "true", "yes", "on"):
            with mock.patch.dict(os.environ, {FLAG: w}):
                self.assertTrue(rhythm.unison_beam_tips_enabled(), w)
        for w in ("0", "", "off", "no", "false"):
            with mock.patch.dict(os.environ, {FLAG: w}):
                self.assertFalse(rhythm.unison_beam_tips_enabled(), w)


class TestNothingMovesWithoutTheStrokeMap(unittest.TestCase):
    def test_CONTROL_off_is_the_2_75_narrowing(self):
        v = _run("0")
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(sorted(c.value["beam_levels"] for c in v.candidates), [1, 2])

    def test_on_with_no_stroke_map_is_byte_identical_to_off(self):
        a, b = _run("0"), _run("1")
        self.assertEqual((a.outcome, a.reason, a.value), (b.outcome, b.reason, b.value))
        self.assertEqual(sorted(c.value["beam_levels"] for c in a.candidates), sorted(c.value["beam_levels"] for c in b.candidates))


# ═════════════════════════════════════════════════════════════════════════════
# The second 2.233 flag: `OMR_TIP_WINDOW_FROM_STROKES` -- ONLY the stem-tip accessors read the stroke map; the stems stay the finder's.
# ═════════════════════════════════════════════════════════════════════════════
from tools.omr.staged import record as R                                        # noqa: E402
from tools.omr.staged.adjudicate import Evidence                                # noqa: E402
from tools.omr.staged.record import READERS                                     # noqa: E402
from tools.omr.tests.test_staged_stems_from_strokes_2_204 import UP, V, build   # noqa: E402

TIPFLAG = rhythm.TIP_WINDOW_FROM_STROKES_ENV
STEMFLAG = rhythm.STEMS_FROM_STROKES_ENV


class TestTipWindowFromStrokes(unittest.TestCase):
    def _ev(self, log, g):
        rhythm._STEM_MEMO[:] = [None] * 5
        return Evidence(log, g, adjudicate.REGISTRY[Q.DURATION])

    def _planted(self):
        log, gs = build([V(0, UP)], finder=(UP,))
        stem = [r for r in log.rows(Q.STEM, R.cell(0, 0, 0, 0), scope=R.Scope.SELF_AND_DESCENDANTS)][0]
        log.observe(stem.subject, Q.STEM_TIP_INK, True, reader=READERS.CV_STEM_TIP, frame="cell:0", end="top", stem_row_id=stem.id, hooks=1,
                    hooks_min=1, hooks_max=1)
        return log, gs, stem

    def _tip(self, tip, stems="0"):
        log, gs, stem = self._planted()
        with mock.patch.dict(os.environ, {TIPFLAG: tip, STEMFLAG: stems}):
            return rhythm._stem_tip_flag_ink(self._ev(log, gs[0]), R.cell(0, 0, 0, 0), [stem], "up")[0]

    def test_default_is_OFF(self):
        with mock.patch.dict(os.environ, {}):
            os.environ.pop(TIPFLAG, None)
            self.assertFalse(rhythm.tip_window_from_strokes_enabled())

    def test_OFF_reads_the_GATHER_row(self):
        self.assertEqual(self._tip("0"), True)

    def test_ON_reads_the_stroke_map_and_ignores_that_row_RED(self):
        self.assertEqual(self._tip("1"), False)           # the stroke map shows a clean tip; the planted flag-ink row was not read

    def test_the_stems_stay_the_finders_when_only_this_flag_is_ON(self):
        with mock.patch.dict(os.environ, {TIPFLAG: "1", STEMFLAG: "0"}):
            self.assertFalse(rhythm.stems_from_strokes_enabled())
            self.assertTrue(rhythm.tip_window_from_strokes_enabled())

    def test_ON_with_no_stroke_map_falls_back_to_the_GATHER_row_TWIN(self):
        log, gs = build([], finder=(UP,))
        stem = [r for r in log.rows(Q.STEM, R.cell(0, 0, 0, 0), scope=R.Scope.SELF_AND_DESCENDANTS)][0]
        log.observe(stem.subject, Q.STEM_TIP_INK, True, reader=READERS.CV_STEM_TIP, frame="cell:0", end="top", stem_row_id=stem.id, hooks=1,
                    hooks_min=1, hooks_max=1)
        with mock.patch.dict(os.environ, {TIPFLAG: "1", STEMFLAG: "0"}):
            ink, _rows = rhythm._stem_tip_flag_ink(self._ev(log, gs[0]), R.cell(0, 0, 0, 0), [stem], "up")
        self.assertEqual(ink, True)


if __name__ == "__main__":
    unittest.main()
