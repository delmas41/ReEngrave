"""ROADMAP 2.160 -- the lone-event rule (2.158) declines a head with too little head-shaped ink: `OMR_LONE_EVENT_HEAD_INK_GUARD`,
default OFF (STAGED INFER `inferences.lone_event_decline`).

Sean 2026-10-17: *"Let's explore the top little note head idea"* -- 2.158 tile 14, a tie's tail on the bottom line boxed as the
bar's only head. The guard reads the staff-line-ERASED reading `Q.NOTEHEAD_INK.detail.ink_net.best` (tile 14: 0.218, while
`value`, max(raw, net), read 0.700 off the staff line) against `consequences.LONE_EVENT_MIN_HEAD_INK_NET`, a cut fitted on our
plates, so it may only NARROW: a declined head stays NARROWED, never gets another value. Each guard test fails with the guard
removed from `lone_event_decline`; the controls fail if the guard over-reaches.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import consequences, inferences
from tools.omr.staged.record import READERS, Outcome, Q
from tools.omr.tests.test_staged_bare_stem_2_81 import _cell, _sub
from tools.omr.tests.test_staged_lone_event_fills_bar_2_158 import _LoneBar, _fired, _run, _v

GUARD = consequences.LONE_EVENT_HEAD_INK_GUARD_ENV
CUT = consequences.LONE_EVENT_MIN_HEAD_INK_NET


def _ink(b, g, value, net):
    """File `Q.NOTEHEAD_INK` on head `g` as `gather_notehead_ink` does: value = max(raw, net), each reading whole."""
    b.log.observe(_sub(0, g, b.cell_idx), Q.NOTEHEAD_INK, value, reader=READERS.CV_NOTEHEAD_INK, frame="cell",
                  ink_raw={"best": value, "best_window": "center", "windows": {"center": value}},
                  ink_net=None if net is None else {"best": net, "best_window": "ring", "windows": {"ring": net}})


def _bar(*inks):
    """A 2/4 bar with one event: one head per `(value, net)` (a chord on one stem when more than one)."""
    b = _LoneBar(2, 4)
    gs = []
    for i, ink in enumerate(inks):
        g = b.head(event=None if i == 0 else 0)
        if ink is not None:
            _ink(b, g, *ink)
        gs.append(g)
    return b.finish(), gs


def _go(log, guard):
    with mock.patch.dict(os.environ, {GUARD: "1" if guard else "0"}, clear=False):
        why = inferences.lone_event_decline(log, _cell(0, 0))
        rep = _run(log)
    return why, rep


TIE_TAIL = (0.700, 0.218)        # 2.158 tile 14 (Litolff glyph/5/1/4/2/1)
LOWEST_REAL = (0.688, 0.486)     # the lowest net of 208 heads Sean valued (Litolff glyph/4/0/7/7/10)


class TestTheFlag(unittest.TestCase):

    def test_default_off_only_an_on_word_enables(self):
        for word, on in ((None, False), ("", False), ("0", False), ("off", False), ("nope", False),
                         ("1", True), ("on", True), ("yes", True), ("true", True)):
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop(GUARD, None)
                if word is not None:
                    os.environ[GUARD] = word
                self.assertEqual(consequences.lone_event_head_ink_guard_enabled(), on, word)

    def test_the_cut_sits_inside_the_measured_gap(self):
        self.assertTrue(TIE_TAIL[1] < CUT < LOWEST_REAL[1])


class TestTheGuard(unittest.TestCase):

    def test_CONTROL_guard_off_the_tie_tail_is_guessed(self):
        log, (g,) = _bar(TIE_TAIL)
        why, rep = _go(log, guard=False)
        self.assertEqual(why, (None, 2.0))
        self.assertEqual(_v(log, g).reason, inferences.LONE_EVENT_REASON)

    def test_guard_on_the_tie_tail_stays_narrowed_RED(self):
        log, (g,) = _bar(TIE_TAIL)
        why, rep = _go(log, guard=True)
        self.assertIsNone(why[1])
        self.assertTrue(why[0].startswith("head_ink_below_cut"), why)
        self.assertEqual(_fired(rep), [])
        v = _v(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)          # unread, its candidates intact -- never another value
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates), [1.0, 2.0, 4.0])

    def test_it_reads_the_erased_ink_not_the_value(self):
        # value 0.700 is far above the cut; only the erased reading (net) declines. A guard on `value` would guess it.
        self.assertGreater(TIE_TAIL[0], CUT)
        log, (g,) = _bar(TIE_TAIL)
        _go(log, guard=True)
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_one_low_head_in_a_chord_declines_the_event(self):
        log, gs = _bar((0.95, 0.95), TIE_TAIL)
        why, rep = _go(log, guard=True)
        self.assertTrue(why[0].startswith("head_ink_below_cut"), why)
        for g in gs:
            self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_CONTROL_the_lowest_real_head_is_still_guessed(self):
        log, (g,) = _bar(LOWEST_REAL)
        why, rep = _go(log, guard=True)
        self.assertEqual(why, (None, 2.0))
        self.assertEqual((_v(log, g).outcome, _v(log, g).reason), (Outcome.DECIDED, inferences.LONE_EVENT_REASON))

    def test_CONTROL_no_ink_row_never_declines(self):
        for ink in (None, (0.9, None)):
            log, (g,) = _bar(ink)
            why, rep = _go(log, guard=True)
            self.assertEqual(why, (None, 2.0), ink)
            self.assertEqual(_v(log, g).reason, inferences.LONE_EVENT_REASON)


if __name__ == "__main__":
    unittest.main()
