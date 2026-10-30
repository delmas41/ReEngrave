"""ROADMAP 2.235 (STAGED ADJUDICATE `rhythm._tips_honouring_claims`), flag `OMR_TIPS_HONOUR_CLAIMS`, default OFF.

The stem-tip readers consult the claims: GATHER's tip window abstains `occupied` where a detection box (a dot, a slur, an accidental) covers
ink attached to the tip; where the strokes `Q.STROKE_OWNER` DECIDED to another mark are the only ink there, the tip is clean. Every test that
says RED has a twin that must NOT fire (contested ink, unclaimed ink, a hook, the flag OFF). Constructed cells only."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences          # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicate import Evidence
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Q, READERS
from tools.omr.tests.test_staged_stems_from_strokes_2_204 import UP, V, build
from tools.omr.tests.test_stroke_owner_2_205 import _claimant

FLAG = rhythm.TIPS_HONOUR_CLAIMS_ENV
CELL = R.cell(0, 0, 0, 0)
DOT = dict(kind="blob", i=1, box=(640, 200, 40, 40), L=0.4, T=0.4, touches=[], steps=None)
HOOK = dict(kind="horizontal", i=1, box=(630, 185, 194, 25), L=1.9, T=0.25, touches=[0], steps=None)


def tips(on, strokes, claimants=(), why="occupied"):
    def extra(log):
        for gi, cls, box, cov in claimants:
            _claimant(log, gi, cls, box, cov)
        stem = [r for r in log.rows(Q.STEM, CELL, scope=R.Scope.SELF_AND_DESCENDANTS)][0]
        log.abstain(stem.subject, Q.STEM_TIP_INK, reader=READERS.CV_STEM_TIP, frame="cell:0", reason="occupied",
                    stem_row_id=stem.id, end="top", why=why)
    log, gs = build(strokes, finder=(UP,), extra=extra)
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        adjudicate.run(log)
        ev = Evidence(log, gs[0], adjudicate.REGISTRY[Q.DURATION])
        stems = ev.rows(Q.STEM, scope=R.Scope.SELF_AND_ANCESTORS, subject=CELL)
        rhythm._STEM_MEMO[:] = [None] * 5
        rhythm._CLAIM_TIPS_MEMO[:] = [None] * 3
        flag, rows = rhythm._stem_tip_flag_ink(ev, CELL, stems, "up")
        notes = rhythm._tips_honouring_claims(ev, CELL, stems)[2] if on else {}
    return flag, notes


class TestClaimsExplainTheOccupiedTip(unittest.TestCase):

    def test_a_dot_the_dot_owns_does_not_make_the_tip_unclean_RED(self):
        flag, notes = tips(True, [V(0, UP), DOT], claimants=[(7, "augmentationDot", (640, 200, 40, 40), (1,))])
        self.assertIs(flag, False)
        (n,) = notes.values()
        self.assertTrue(n["converted"])
        self.assertEqual(n["claims_ignored"], ["dot"])

    def test_twin_OFF_the_same_cell_is_still_occupied(self):
        flag, _ = tips(False, [V(0, UP), DOT], claimants=[(7, "augmentationDot", (640, 200, 40, 40), (1,))])
        self.assertIsNone(flag)

    def test_twin_ink_nobody_claimed_keeps_the_tip_occupied(self):
        flag, notes = tips(True, [V(0, UP), DOT])
        self.assertIsNone(flag)
        self.assertFalse(list(notes.values())[0]["converted"])

    def test_twin_a_flag_shaped_stroke_is_never_ignored_even_beside_a_claimed_dot(self):
        flag, notes = tips(True, [V(0, UP, touches=[2]), dict(HOOK, i=2, touches=[0]), DOT],
                           claimants=[(7, "augmentationDot", (640, 200, 40, 40), (1,))])
        self.assertIsNot(flag, False)

    def test_twin_other_cannot_tell_words_are_not_the_claims_to_explain(self):
        flag, notes = tips(True, [V(0, UP), DOT], claimants=[(7, "augmentationDot", (640, 200, 40, 40), (1,))], why="head_at_this_end")
        self.assertIsNone(flag)
        self.assertEqual(notes, {})


if __name__ == "__main__":
    unittest.main()
