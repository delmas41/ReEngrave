"""ROADMAP 2.266b (flag OMR_ACCIDENTAL_READ_ONCE, default ON, deny-list): an accidental whose family reading names a kind is read once -- the family
reading alone decides READ / GUESSED and the 2.186 one-ink guess is never consulted for that ink. Absent / unclear family: unchanged."""
import os
import unittest
from unittest import mock

from tools.omr.staged import accidental_family as AF
from tools.omr.staged import export as E
from tools.omr.staged.record import Q

ENV = AF.ACCIDENTAL_READ_ONCE_ENV
ONE_INK = {"winner": {"class": "accidentalFlat"}, "margin": 0.1, "candidates": []}


class _Rec:
    def __init__(self, fam):
        self.owner = {"id": "o", "quantity": Q.ACCIDENTAL_OWNER, "outcome": "decided",
                      "detail": {"one_ink": ONE_INK, **({"family": fam} if fam else {})}}
        self.acc = {"id": "a", "quantity": Q.ACCIDENTAL, "outcome": "decided", "basis": ["o"]}

    def verdict(self, q, sub):
        return self.acc if q == Q.ACCIDENTAL else None

    def verdict_by_id(self, bid):
        return self.owner


def _fam(t, margin, cands, det):
    return {"type": t, "margin": margin, "candidates": list(cands), "detector_class": det, "detector_type": AF.type_of_class(det),
            "features": {}}


def _guess(fam, flag):
    with mock.patch.dict(os.environ, {ENV: flag}):
        with mock.patch("tools.omr.staged.one_ink.reads", return_value=False):
            return E.one_ink_guess_of(_Rec(fam), "s")


class ReadOnce(unittest.TestCase):
    def test_flag_default_is_on_and_deny_list_turns_it_off(self):
        with mock.patch.dict(os.environ, {}):
            os.environ.pop(ENV, None)
            self.assertTrue(AF.accidental_read_once_enabled())
        for v in ("0", "false", "no", "off", "OFF"):
            with mock.patch.dict(os.environ, {ENV: v}):
                self.assertFalse(AF.accidental_read_once_enabled(), v)

    def test_family_read_natural_off_falls_through_to_one_ink_on_does_not(self):
        fam = _fam("natural", 0.6, ("flat", "natural"), "accidentalFlat")
        with mock.patch.dict(os.environ, {"OMR_NATURAL_READ": "1"}):
            off = _guess(fam, "0")
            self.assertIsNotNone(off)
            self.assertEqual(off["rule"], E.ONE_INK_RULE)       # the control: today's second read, so this test can fail
            self.assertIsNone(_guess(fam, "1"))

    def test_family_guessed_kind_stays_the_family_guess_with_the_flag_on(self):
        fam = _fam("flat", 0.6, ("flat", "natural"), "accidentalNatural")      # flats never READ: the family's own blue stands
        self.assertEqual(_guess(fam, "1")["rule"], AF.REASON)

    def test_unclear_family_is_unchanged_by_the_flag(self):
        fam = _fam("unclear", None, ("flat",), "accidentalFlat")
        self.assertEqual(_guess(fam, "1"), _guess(fam, "0"))

    def test_absent_family_one_ink_stands(self):
        self.assertEqual(_guess(None, "1")["rule"], E.ONE_INK_RULE)


if __name__ == "__main__":
    unittest.main()
