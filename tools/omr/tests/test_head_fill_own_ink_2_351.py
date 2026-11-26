"""ROADMAP 2.351 -- a head is hollow or black by its own ink, not by an over-wide box (STAGED ADJUDICATE, `rhythm`, `OMR_HEAD_FILL_OWN_INK`).

The rule as a musician says it: the box says where to look; the head's own ink says filled or hollow. Never a hollow read off paper beside
the head; never a head its own ink reads hollow turned black; a box one head wide is not touched.

CAUSE: 2.70 (`hollow_head_bare_stem`) reads 2.23's centre window, a fraction of the DETECTOR BOX, and 2.83 sized that box by its height
only. A box wider than one head -- a stem-end rescue box from a barline to the head, a box over a head and its slur, a box on a slur --
puts the window on paper and the note is written a half.

Every case is the 20261123-night record's own GATHER rows for the head's cell (fixture `head_fill_own_ink_2_351.json.gz`, cut by
`/private/tmp/claude-501/lane-2.351/mkfix.py`), re-adjudicated. What each head IS comes from our look at the 600-dpi crops, not Sean's,
except the two judged controls named below. Each positive fails with the flag off (main writes the half).
"""
from __future__ import annotations

import gzip
import json
import os
import pathlib
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Outcome, Q, Subject
from tools.omr.staged.review import rerun as RR

FIX = json.loads(gzip.decompress((pathlib.Path(__file__).parent / "fixtures" / "head_fill_own_ink_2_351.json.gz").read_bytes()))
FLAG = rhythm.HEAD_FILL_OWN_INK_ENV

#: a box wider than one head whose own ink is not a hollow head: written a half on main (our look: a black head, or no head at all)
WRONG_HALVES = {
    "litolff|glyph/2/0/10/2/13": "black C3 quarter, box 2.74 sp from the barline to the head (2.306 r22 item 2); own ink filled",
    "litolff|glyph/2/0/1/4/7": "a split box on staff lines and a stem between two black heads; own ink not one head",
    "litolff|glyph/4/1/4/5/7": "a box 2.21 sp on two slurs; own ink not one head",
    "brahms|glyph/8/0/2/7/11": "black head, box 2.05 sp running right over a slur; own ink filled",
}
#: the other side: halves the rule must leave alone
KEPT_HALVES = {
    "litolff|glyph/7/0/8/10/5": "a real half on a 2.16 sp box: own ink hollow, so the window still speaks",
    "litolff|glyph/4/1/9/14/10": "a real half on a 0.83 sp box whose own ink reads FILLED (slur through the slit): a narrow box is not touched",
    "litolff|glyph/10/1/10/1/3": "a real half on a 0.81 sp box, own ink not one head: a narrow box is not touched",
}
#: Sean's judged marks near the width cut (2.220 tiles): written by the detector's class, unchanged either way
JUDGED_UNCHANGED = {
    "litolff|glyph/4/0/3/6/2": "Sean 2.220-m2 tile 1, a half; box 1.94 sp, own ink hollow",
    "litolff|glyph/6/1/5/11/1": "Sean 2.220-plan tile 7, a half; box 1.91 sp, own ink not one head (written a quarter on main too)",
}


def _verdict(key, on):
    sub = Subject.from_key(key.split("|")[1])
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        log, _ = RR.rebuild_gather(FIX[key])
        adjudicate.run(log)
    return log.verdict(Q.DURATION, sub)


def _written(v):
    return (v.outcome, v.reason, v.value.get("written") if isinstance(v.value, dict) else None)


class WideBoxOwnInk(unittest.TestCase):

    def test_flag_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG, None)
            self.assertFalse(rhythm.head_fill_own_ink_enabled())

    def test_wrong_halves_fail_on_main(self):
        for k in WRONG_HALVES:
            with self.subTest(k):
                self.assertEqual(_written(_verdict(k, False)), (Outcome.DECIDED, "hollow_head_bare_stem", 2.0))

    def test_wrong_halves_are_not_halves_with_the_rule(self):
        for k in WRONG_HALVES:
            with self.subTest(k):
                o, r, w = _written(_verdict(k, True))
                self.assertNotEqual(r, "hollow_head_bare_stem")
                self.assertNotEqual(w, 2.0)

    def test_real_halves_stay_halves(self):
        for k in KEPT_HALVES:
            with self.subTest(k):
                self.assertEqual(_written(_verdict(k, True)), _written(_verdict(k, False)))
                self.assertEqual(_written(_verdict(k, True))[2], 2.0)

    def test_judged_marks_unchanged(self):
        for k in JUDGED_UNCHANGED:
            with self.subTest(k):
                self.assertEqual(_written(_verdict(k, True)), _written(_verdict(k, False)))


if __name__ == "__main__":
    unittest.main()
