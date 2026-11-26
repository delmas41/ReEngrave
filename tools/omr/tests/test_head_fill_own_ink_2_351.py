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
FIX2 = json.loads(gzip.decompress((pathlib.Path(__file__).parent / "fixtures" / "head_fill_own_ink_2_351_r2.json.gz").read_bytes()))
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


def _verdict(key, on, fix=None):
    sub = Subject.from_key(key.split("|")[1].split("#")[0])
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        log, _ = RR.rebuild_gather((fix or FIX)[key])
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


def _candidates(v):
    return sorted({(c.value or {}).get("written") for c in (v.candidates or ())} - {None})


#: ROUND 2 (2026-11-26). The rule's nevers, enforced on the REAL rows: never a hollow read off paper beside the head; never a head its own ink
#: reads hollow turned black; and never "own ink UNREAD" read as "black" -- where the head's own ink cannot tell, the window's hollow does not
#: DECIDE a half, and the note keeps what read it before (the narrowing black / half / whole), never a plain quarter (CLAUDE rule 8).
JUDGED_HALF = "litolff|glyph/9/0/4/2/8"       # Sean 2.158-review tile 11, "2" = a half; box 1.91 sp, own ink (old reader) not_one_head too_wide
SLUR_BOX = "litolff|glyph/11/1/5/0/4"          # a box 3.81 sp on a slur: own ink no_head_ink; the record narrowed it
JUDGED_QUARTER = "litolff|glyph/2/0/10/2/13"   # Sean 2026-11-25 "was a quarter": box 2.74 sp, own ink READ filled
UNREAD_WRONG_HALVES = ("litolff|glyph/2/0/1/4/7", "litolff|glyph/4/1/4/5/7")   # boxes on a stem / on beams; own ink not one head


class OwnInkUnreadIsNotBlack(unittest.TestCase):

    def test_judged_half_is_not_turned_into_a_plain_quarter(self):
        v = _verdict(JUDGED_HALF, True, FIX2)
        self.assertNotEqual((v.outcome, _written(v)[2]), (Outcome.DECIDED, 1.0))
        self.assertEqual(_written(v), _written(_verdict(JUDGED_HALF, False, FIX2)))   # what read it before (the narrowing) stands
        self.assertIn(2.0, _candidates(v))

    def test_judged_half_with_the_head_ink_of_2_355_is_a_half(self):
        k = JUDGED_HALF + "#new_ink"
        for on in (False, True):
            self.assertEqual(_written(_verdict(k, on, FIX2))[2], 2.0)

    def test_slur_box_stays_narrowed_never_a_plain_quarter(self):
        v = _verdict(SLUR_BOX, True, FIX2)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(_written(v), _written(_verdict(SLUR_BOX, False, FIX2)))

    def test_unread_wide_boxes_are_narrowed_not_halves_and_not_black(self):
        for k in UNREAD_WRONG_HALVES:
            with self.subTest(k):
                v = _verdict(k, True)
                self.assertEqual(v.outcome, Outcome.NARROWED)
                self.assertTrue({1.0, 2.0} <= set(_candidates(v)))

    def test_judged_quarter_is_not_a_half_and_black_head_read_filled_stays_black(self):
        self.assertEqual(_written(_verdict(JUDGED_QUARTER, True)), (Outcome.DECIDED, "head_and_marks", 1.0))


if __name__ == "__main__":
    unittest.main()
