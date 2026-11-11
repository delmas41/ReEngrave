"""ROADMAP 2.284 r7 (STAGED ADJUDICATE `rhythm._tips_from_strokes`, flag `OMR_PAGE_LEDGER_OWNS`, default OFF).

A bar a HEAD box owns at a stem tip (Litolff p2 2/1/5/13/0: a noteheadDoubleWholeInSpace box over a printed beam) is not "another mark's ink":
under the flag it stays at the tip, so the 2.235 conversion does not read the tip clean (a quarter where the print has a beam). The twin
shows a round head blob at the tip is still ignored under the flag, and the flag OFF keeps the 2.235 behaviour. Constructed cells only."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import page_ledger
from tools.omr.tests.test_staged_tips_honour_claims_2_235 import DOT, V, UP, tips

BAR = dict(kind="horizontal", i=1, box=(630, 185, 230, 40), L=2.3, T=0.4, touches=[0], steps=None)
HEAD_CLAIM = (7, "noteheadDoubleWholeInSpace", (630, 185, 230, 40), (1,))
BLOB_CLAIM = (7, "noteheadBlackInSpace", (640, 200, 40, 40), (1,))


def run(flag_on, strokes, claim):
    with mock.patch.dict(os.environ, {page_ledger.ENV: "1" if flag_on else "0"}):
        return tips(True, strokes, claimants=[claim])


class TestBarOwnedByHead(unittest.TestCase):

    def test_a_bar_a_head_owns_stays_at_the_tip_under_the_flag_RED(self):
        flag, notes = run(True, [V(0, UP), BAR], HEAD_CLAIM)
        self.assertIsNone(flag)
        self.assertFalse(list(notes.values())[0]["converted"])

    def test_twin_flag_OFF_the_2_235_conversion_stands(self):
        flag, notes = run(False, [V(0, UP), BAR], HEAD_CLAIM)
        self.assertIs(flag, False)
        self.assertTrue(list(notes.values())[0]["converted"])

    def test_twin_a_round_head_blob_a_head_owns_is_still_ignored_under_the_flag(self):
        flag, notes = run(True, [V(0, UP), DOT], BLOB_CLAIM)
        self.assertIs(flag, False)


if __name__ == "__main__":
    unittest.main()
