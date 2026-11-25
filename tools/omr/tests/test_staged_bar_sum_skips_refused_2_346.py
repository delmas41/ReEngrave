"""ROADMAP 2.346 -- a glyph ADJUDICATE already refused as NOT A NOTE takes no time in its bar (STAGED ADJUDICATE `rhythm._bar_lengths_for`).

CONTROL FROM REAL ROWS (CLAUDE.md rule 7): `fixtures/bar_sum_refused_2_346_brahms_p6_s1_c0.json` holds the verdict rows ADJUDICATE filed
for Brahms system/6/1 cell 0 staff 6 (bar 107, printed 3.0 quarters in 6/8) in the 20261123-night record: three eighth rests and three
eighth notes (3.0), two clef/key glyphs refused `claimed_by:leading_column` that still carry a decided 1.0 each, and a sharp boxed as a
head (narrowed 0.5 / 1.0, NOT refused: out of scope). EVENTS = the real `Q.EVENT` grouping of that cell as the OFF replay of the
20261123-night rows filed it (that replay reproduces the record, 2037 of 2037 duration/rest verdicts): the two refused glyphs are ONE chord
event at the start of the bar. The old sum is the range 4.5 .. 5.0 (the trace's "5.0 against a printed 3.0" is its upper end).

NEVER-CONTROLS: an undecided (narrowed / abstained) verdict still makes the bar a RANGE / unknown; a decided refusal on a glyph that is a
reinstated eighth rest (2.80b) keeps it in the bar; a bar whose every glyph is refused is not summed as an empty bar.
"""
from __future__ import annotations

import json
import os
import pathlib
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicate import Candidate
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Outcome, Q, Subject

FIX = pathlib.Path(__file__).parent / "fixtures" / "bar_sum_refused_2_346_brahms_p6_s1_c0.json"
ENV = rhythm.BAR_SUM_SKIPS_REFUSED_ENV
_Q = {"duration": Q.DURATION, "notehead_is_not_a_notehead": Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
      "rest_is_not_a_rest": Q.REST_IS_NOT_A_REST, "notehead_is_an_eighth_rest": Q.NOTEHEAD_IS_AN_EIGHTH_REST}


def _put(log, subject, quantity, outcome, value=None, reason="t", candidates=()):
    log.record(adjudicate.Verdict(id=log._next_id("vrd"), subject=subject, quantity=quantity, outcome=outcome,
                                  value=value, decider="t", reason=reason,
                                  candidates=tuple(Candidate(c, support=1.0) for c in candidates)))


def _real_log(drop_refusals=()):
    """The real rows of the bar, one event per glyph, filed under the real glyph subjects."""
    rows = json.loads(FIX.read_text())["rows"]
    log = Log()
    gl = []
    for r in rows:
        sub = Subject.from_key(r["subject"])
        if sub.glyph not in gl:
            gl.append(sub.glyph)
        if r["quantity"] == "notehead_is_not_a_notehead" and sub.glyph in drop_refusals:
            continue
        if r["quantity"] == "duration" and r["outcome"] == "narrowed":
            _put(log, sub, Q.DURATION, Outcome.NARROWED, None, r["reason"], r["candidates"])
        else:
            _put(log, sub, _Q[r["quantity"]], Outcome(r["outcome"]), r["value"], r["reason"])
    cell = Subject.from_key("cell/6/1/6/0")
    real = [[20, 21], [5], [18], [14], [3], [9], [1], [12]]       # the record's own Q.EVENT grouping of the cell, left to right
    assert sorted(g for e in real for g in e) == sorted(gl)
    _put(log, cell, Q.EVENT, Outcome.DECIDED, {"events": [{"glyphs": e, "x": float(i)} for i, e in enumerate(real)]})
    return log, cell


def _lengths(log, cell, *, on):
    log.freeze()
    adjudicate._ensure_decisions()
    spec = adjudicate.REGISTRY[Q.METER]
    ev = adjudicate.Evidence(log, Subject.from_key("system/6/1"), spec)
    with mock.patch.dict(os.environ, {ENV: "1" if on else "0", "OMR_NARROWED_BAR_LENGTH_UNKNOWN": "1"}, clear=False):
        return rhythm._bar_lengths_for(ev)


class TestRealBar107(unittest.TestCase):

    def test_off_sums_the_clef_and_key_ink_RED_without_it(self):
        log, cell = _real_log()
        got = _lengths(log, cell, on=False)
        lo, hi = got[0][0]
        self.assertEqual(lo, 4.5)                    # 3.0 of real notes and rests + the refused chord's 1.0 + the sharp at its shortest
        self.assertEqual(hi, 5.0)                    # ... and at its longest (the trace's "5.0 against a printed 3.0")

    def test_on_leaves_the_refused_ink_out_and_keeps_the_sharp_a_range(self):
        log, cell = _real_log()
        lo, hi = _lengths(log, cell, on=True)[0][0]
        self.assertEqual(lo, 3.5)                    # 3.0 + the sharp at its shortest
        self.assertEqual(hi, 4.0)                    # 3.0 + the sharp at its longest: still a RANGE, never a known sum

    def test_never_an_undecided_head_is_dropped(self):
        """Take the refusal off the two phantoms (an undecided head): they stay in the bar, exactly as in the old sum."""
        log, cell = _real_log(drop_refusals=(20, 21))
        lo, hi = _lengths(log, cell, on=True)[0][0]
        self.assertEqual((lo, hi), (4.5, 5.0))


class TestNevers(unittest.TestCase):

    def _bar(self, glyphs, events=None):
        log = Log()
        cell = Subject.from_key("cell/0/0/0/0")
        for g, (out, val, cands, refused, eighth_rest) in glyphs.items():
            sub = Subject.from_key("glyph/0/0/0/0/%d" % g)
            _put(log, sub, Q.DURATION, out, val, "t", cands)
            if refused is not None:
                _put(log, sub, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, refused[0], refused[1])
            if eighth_rest:
                _put(log, sub, Q.NOTEHEAD_IS_AN_EIGHTH_REST, Outcome.DECIDED, True)
        _put(log, cell, Q.EVENT, Outcome.DECIDED, {"events": events or [{"glyphs": [g], "x": float(g)} for g in sorted(glyphs)]})
        log.freeze()
        adjudicate._ensure_decisions()
        return adjudicate.Evidence(log, Subject.from_key("system/0/0"), adjudicate.REGISTRY[Q.METER])

    def _len(self, ev, on):
        with mock.patch.dict(os.environ, {ENV: "1" if on else "0"}, clear=False):
            return rhythm._bar_lengths_for(ev).get(0)

    DEC1 = {"beats": 1.0, "written": 1.0, "dots": 0}

    def test_a_reinstated_eighth_rest_stays_in_its_bar(self):
        ev = self._bar({1: (Outcome.DECIDED, self.DEC1, (), None, False),
                        2: (Outcome.DECIDED, {"beats": 0.5, "written": 0.5, "dots": 0}, (), (Outcome.DECIDED, True), True)})
        self.assertEqual(self._len(ev, True), [1.5])

    def test_a_refused_head_with_no_reinstated_rest_leaves(self):
        ev = self._bar({1: (Outcome.DECIDED, self.DEC1, (), None, False),
                        2: (Outcome.DECIDED, self.DEC1, (), (Outcome.DECIDED, True), False)})
        self.assertEqual(self._len(ev, True), [1.0])
        self.assertEqual(self._len(ev, False), [2.0])

    def test_an_abstained_or_false_refusal_does_not_remove_a_glyph(self):
        ev = self._bar({1: (Outcome.DECIDED, self.DEC1, (), None, False),
                        2: (Outcome.DECIDED, self.DEC1, (), (Outcome.ABSTAINED, None), False),
                        3: (Outcome.DECIDED, self.DEC1, (), (Outcome.DECIDED, False), False)})
        self.assertEqual(self._len(ev, True), [3.0])

    def test_a_bar_of_only_refused_glyphs_is_not_an_empty_bar(self):
        ev = self._bar({1: (Outcome.DECIDED, self.DEC1, (), (Outcome.DECIDED, True), False)})
        self.assertEqual(self._len(ev, True), None)          # no bar at all, never a zero-length one voting
        self.assertEqual(self._len(ev, False), [1.0])

    def test_a_chord_keeps_its_value_when_one_member_is_a_refused_twin(self):
        ev = self._bar({1: (Outcome.DECIDED, self.DEC1, (), None, False),
                        2: (Outcome.DECIDED, {"beats": 2.0, "written": 2.0, "dots": 0}, (), (Outcome.DECIDED, True), False)},
                       events=[{"glyphs": [1, 2], "x": 1.0}])
        self.assertEqual(self._len(ev, True), [1.0])

    def test_the_word(self):
        for word, want in (("", True), ("1", True), ("on", True), ("0", False), ("off", False), ("no", False), ("false", False)):
            with mock.patch.dict(os.environ, {ENV: word}, clear=False):
                self.assertEqual(rhythm.bar_sum_skips_refused_enabled(), want, word)


if __name__ == "__main__":
    unittest.main()
