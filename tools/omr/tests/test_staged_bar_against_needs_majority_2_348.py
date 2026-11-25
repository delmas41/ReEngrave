"""ROADMAP 2.348 (c) -- a bar speaks AGAINST a candidate meter only when most of the system's staves read it (flag `OMR_BAR_AGAINST_NEEDS_MAJORITY`, default OFF).

STAGED ADJUDICATE `rhythm._score_bars`. CONTROL FROM REAL ROWS (CLAUDE.md rule 7): `fixtures/bars_majority_2_348_brahms.json` holds the per-staff bar
lengths of the two Brahms systems the 20261123-night record abstained `carry_outweighed_by_the_bars` (system/6/1: bar 0 was read by 4 of 11 staves, 2 of them
agreeing, and voted the 6/8 down; system/21/0). Both prints continue 6/8, so the carry was right.

NEVERS: a bar read by most staves still votes against; a bar that agrees is never touched; an unknown staff count silences nothing; flag OFF is the old rule.
"""
from __future__ import annotations

import json
import os
import pathlib
import unittest
from unittest import mock

from tools.omr.staged.adjudicators import rhythm

FIX = json.loads((pathlib.Path(__file__).parent / "fixtures" / "bars_majority_2_348_brahms.json").read_text())["systems"]
ENV = rhythm.BAR_AGAINST_NEEDS_MAJORITY_ENV
SIX_EIGHT = 3.0


def _bars(key):
    return {int(c): [tuple(x) if isinstance(x, list) else x for x in ls] for c, ls in FIX[key]["bars"].items()}


def _score(key, *, on, n_staves="fixture"):
    n = FIX[key]["n_staves"] if n_staves == "fixture" else n_staves
    with mock.patch.dict(os.environ, {ENV: "1" if on else "0"}, clear=False):
        return rhythm._score_bars(_bars(key), SIX_EIGHT, n)


class TestRealSystems(unittest.TestCase):

    def test_off_is_the_old_rule(self):
        r = _score("system/6/1", on=False)
        self.assertEqual((r["bars_agree"], r["bars_disagree"]), (1, 1))          # 1 for, 1 against = the record's carry_outweighed row
        r = _score("system/21/0", on=False)
        self.assertEqual((r["bars_agree"], r["bars_disagree"]), (2, 2))

    def test_on_silences_the_bar_read_by_a_minority_of_the_staves(self):
        r = _score("system/6/1", on=True)
        self.assertEqual(r["state"], "too_few_assessable_bars")                  # 1 bar for, none against: nothing to outweigh the carry
        self.assertEqual((r["bars_agree"], r["bars_disagree"]), (1, 0))
        self.assertEqual(r["bars_minority"], [{"cell": 0, "spoke": 4, "of": 11, "length": 6.0}])

    def test_never_a_bar_read_by_most_staves_stops_voting_against(self):
        r = _score("system/21/0", on=True)
        self.assertEqual((r["bars_agree"], r["bars_disagree"]), (2, 1))          # cell 3 (8 of 11 read it) still votes against; cell 7 (5 of 11) is silent
        self.assertEqual([m["cell"] for m in r["bars_minority"]], [7])

    def test_never_an_agreeing_bar_is_touched(self):
        for key in FIX:
            self.assertEqual(_score(key, on=True)["bars_agree"], _score(key, on=False)["bars_agree"])

    def test_an_unknown_staff_count_silences_nothing(self):
        for n in (None, 0):
            r = _score("system/6/1", on=True, n_staves=n)
            self.assertEqual((r["bars_agree"], r["bars_disagree"]), (1, 1))

    def test_the_flag_word(self):
        for word, want in (("", False), ("0", False), ("1", True), ("on", True), ("yes", True)):
            with mock.patch.dict(os.environ, {ENV: word}, clear=False):
                self.assertEqual(rhythm.bar_against_needs_majority_enabled(), want, word)


if __name__ == "__main__":
    unittest.main()
