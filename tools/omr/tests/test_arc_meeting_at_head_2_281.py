"""ROADMAP 2.281 (`OMR_ARC_MEETING_AT_HEAD`, default OFF): two arcs that MEET at a note are not "half of one arc".

`arc_claim.bind_end` refuses an end with `continues_in_another_curve` when another curve begins nearer this end than the closest head stands. On legato the next arc begins ON the head
this one ends on, so its start is always nearer: the refusal fired on 22 of 33 ends on Brahms p0, all of them two arcs meeting at a note. The flag releases an end whose closest head has
the offending curve's end AT it too (inside the binder's own head windows); the half of an arc (a head far from this end) keeps the refusal. Every guard has a twin that fails without it.
"""
from __future__ import annotations

import os
import unittest

from tools.omr.staged import arc_claim as AC
from tools.omr.staged import page_arc_bind as PB

SP = 10.0


def _h(key, cx, cy, w=12.0, h=10.0):
    return {"key": key, "cx": cx, "cy": cy, "w": w, "h": h, "cell": 0}


def _detail(xl, yl, xr, yr, sag=-15.0):
    tr = []
    for x in range(int(xl), int(xr) + 1, 2):
        f = (x - xl) / float(xr - xl)
        tr.append([x, yl + f * (yr - yl) + sag * 4 * f * (1 - f) - 1, yl + f * (yr - yl) + sag * 4 * f * (1 - f) + 1])
    return {"space_page_px": SP, "x_left_page": xl, "y_left_page": yl, "x_right_page": xr, "y_right_page": yr, "trace": tr}


class _Flag:
    def __init__(self, on):
        self.on = on

    def __enter__(self):
        self.old = os.environ.get(AC.ENV_MEETING_AT_HEAD)
        os.environ[AC.ENV_MEETING_AT_HEAD] = "1" if self.on else "0"

    def __exit__(self, *a):
        if self.old is None:
            os.environ.pop(AC.ENV_MEETING_AT_HEAD, None)
        else:
            os.environ[AC.ENV_MEETING_AT_HEAD] = self.old


class TestMeetingAtAHead(unittest.TestCase):
    def test_default_off_and_allow_list(self):
        old = os.environ.pop(AC.ENV_MEETING_AT_HEAD, None)
        try:
            self.assertFalse(AC.meeting_at_head_enabled())
            os.environ[AC.ENV_MEETING_AT_HEAD] = "0"
            self.assertFalse(AC.meeting_at_head_enabled())
            os.environ[AC.ENV_MEETING_AT_HEAD] = "1"
            self.assertTrue(AC.meeting_at_head_enabled())
        finally:
            if old is None:
                os.environ.pop(AC.ENV_MEETING_AT_HEAD, None)
            else:
                os.environ[AC.ENV_MEETING_AT_HEAD] = old

    def _bind(self, heads, others):
        d = _detail(0, 100, 100, 100)
        return PB.closest_binder({"left": [], "right": list(others)})(heads, SP, None, True, None, d)

    # the scene: this arc's ink ends at x=100; its note stands 10 px (1.0 space) BEHIND the end (the ink ends on the head's far edge: past 2.166's 0.8-space look-behind, so the
    # closest-note rule binds it); the next arc begins at x=95, on the same head.
    HEADS = [_h("a", -5, 108), _h("c", 90, 108)]

    def test_an_arc_that_begins_on_the_same_head_is_a_meeting_not_a_continuation(self):
        with _Flag(False):
            off = self._bind(self.HEADS, [(95.0, 100.0)])
        self.assertEqual(off["right"].get("unbound"), "continues_in_another_curve")          # today's refusal
        with _Flag(True):
            on = self._bind(self.HEADS, [(95.0, 100.0)])
        self.assertEqual(on["right"].get("head"), "c")          # both ends stand inside the head windows: two arcs meet at the note

    def test_the_half_of_an_arc_keeps_its_refusal_with_the_flag_on(self):
        heads = [_h("a", -5, 108), _h("far", 190, 108)]          # the closest head is 9 spaces away; the next curve begins 4 px past the end, nowhere near it
        with _Flag(True):
            b = self._bind(heads, [(104.0, 100.0)])
        self.assertEqual(b["right"].get("unbound"), "continues_in_another_curve")

    def test_an_offending_end_past_the_head_window_keeps_the_refusal(self):
        # the other curve begins at x=112, 2.2 spaces past the head's centre: nearer this end than the head is, but not on the head
        with _Flag(True):
            b = self._bind(self.HEADS, [(112.0, 100.0)])
        self.assertEqual(b["right"].get("unbound"), "continues_in_another_curve")

    def test_one_offender_off_the_head_among_several_keeps_the_refusal(self):
        with _Flag(True):
            b = self._bind(self.HEADS, [(95.0, 100.0), (112.0, 100.0)])
        self.assertEqual(b["right"].get("unbound"), "continues_in_another_curve")

    def test_with_nothing_beginning_there_the_end_binds_with_or_without_the_flag(self):
        for on in (False, True):
            with _Flag(on):
                b = self._bind(self.HEADS, [])
            self.assertEqual(b["right"].get("head"), "c")


if __name__ == "__main__":
    unittest.main()
