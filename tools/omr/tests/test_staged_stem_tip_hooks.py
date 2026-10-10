"""ROADMAP 2.69 -- COUNT the hooks at a stem tip (Sean, 2026-10-09).

*"Count the hooks and if you can't count use the fact that there is a hook to
help later deduction process. ... if we see a hook but can't tell if it has 1
or 2 hooks then pass that along and a later deduction where we add up bar
math could tell us if we are missing an eighth note then it could decide."*

And, the same day (ROADMAP 2.71): *"The hook of a flag is very different from
a slash. The slash crosses both sides of the stem with a thick line at an
angle. Beams have to be connected to other notes - slashes never are."* So a
hook hangs from ONE side of the stem tip; ink that crosses BOTH sides is never
a hook.

This file holds the GATHER half (`gather.stem_tip_hooks`, the per-end detail
`_observe_stem_tip_ink` files) and the bar-arithmetic half
(`consequences.reconcile_duration` taking the new narrowing as it is). The
ADJUDICATE half is in `test_staged_duration.py`
(`TestCountedHooksDecideAndUncountedHooksNarrow`).

⚠️ RUN RED FIRST: the `*_RED` tests fail before `gather.stem_tip_hooks`
exists (AttributeError) -- the commit says so. Every refusal test has a
positive control in the same class: a clean one-hook stroke that DOES count.
"""

from __future__ import annotations

import unittest

import cv2
import numpy as np

from tools.omr.staged import consequences, gather
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Candidate, Log, Outcome, Q, Verdict

SP = 40.0                              # one staff space, canonical px
STEM_X0, STEM_X1 = 300.0, 306.0        # a 6px-wide stem
TIP_Y, FAR_Y = 100.0, 340.0            # an up stem: tip at the top, 6 spaces long


def _paper(h=500, w=600):
    return np.full((h, w), 255, dtype=np.uint8)


def _stem(img, x0=STEM_X0, x1=STEM_X1, y0=TIP_Y, y1=FAR_Y):
    img[int(y0):int(y1), int(x0):int(x1)] = 0


def _hook(img, tip_y, *, x0=STEM_X1, down=True, thick=0.4):
    """ONE flag hook: a thick stroke leaving the stem's RIGHT edge at `tip_y`
    and curling away from the tip (down for a top tip), the shape of every
    flag on the plate -- a wedge from the stem, then the curl."""
    t = max(2, int(round(thick * SP)))
    sgn = 1 if down else -1
    pts = np.array([[x0 - 2, tip_y + sgn * 0.0 * SP],
                    [x0 + 0.5 * SP, tip_y + sgn * 0.5 * SP],
                    [x0 + 0.85 * SP, tip_y + sgn * 1.5 * SP],
                    [x0 + 0.8 * SP, tip_y + sgn * 2.1 * SP]], np.int32)
    cv2.polylines(img, [pts.reshape(-1, 1, 2)], False, 0, thickness=t)


def _count(img, **kw):
    return gather.stem_tip_hooks(img, STEM_X0, STEM_X1, TIP_Y, 1.0, SP, **kw)


class TestTheCounter(unittest.TestCase):
    """`gather.stem_tip_hooks` -- a pure ruler on a synthetic raster (0=ink)."""

    def test_ONE_hook_is_counted_as_one(self):
        img = _paper()
        _stem(img)
        _hook(img, TIP_Y + 3)
        r = _count(img, head_edge=FAR_Y - 40)
        self.assertEqual(r["hooks"], 1)
        self.assertEqual((r["hooks_min"], r["hooks_max"]), (1, 1))
        self.assertIsNone(r["hooks_reason"])

    def test_TWO_hooks_are_counted_as_two_RED(self):
        img = _paper()
        _stem(img)
        _hook(img, TIP_Y + 3)
        _hook(img, TIP_Y + 3 + 0.7 * SP)
        r = _count(img, head_edge=FAR_Y - 40)
        self.assertEqual(r["hooks"], 2)

    def test_THREE_hooks_are_counted_as_three_RED(self):
        img = _paper()
        _stem(img)
        for k in range(3):
            _hook(img, TIP_Y + 3 + k * 0.7 * SP)
        r = _count(img, head_edge=FAR_Y - 40)
        self.assertEqual(r["hooks"], 3)

    def test_a_DOWN_stem_counts_from_its_BOTTOM_tip(self):
        """Mirror: a down stem's tip is its bottom and the hooks curl UP."""
        img = _paper()
        _stem(img)
        _hook(img, FAR_Y - 3, down=False)
        _hook(img, FAR_Y - 3 - 0.7 * SP, down=False)
        r = gather.stem_tip_hooks(img, STEM_X0, STEM_X1, FAR_Y, -1.0, SP,
                                  head_edge=TIP_Y + 40)
        self.assertEqual(r["hooks"], 2)

    def test_POSITIVE_CONTROL_a_bare_stem_counts_NOTHING(self):
        """⚠️ The control: with no hook drawn the ruler must say it cannot
        count, never `1` -- it proves `hooks` can be None, not only an int."""
        img = _paper()
        _stem(img)
        r = _count(img, head_edge=FAR_Y - 40)
        self.assertIsNone(r["hooks"])
        self.assertEqual(r["hooks_reason"], gather.HOOKS_UNCOUNTED_TOO_LITTLE)

    def test_a_SLASH_crossing_BOTH_sides_of_the_stem_is_never_a_hook(self):
        """Sean 2026-10-09 (ROADMAP 2.71): a tremolo slash is a thick angled
        stroke that crosses both sides of one stem. It must be REFUSED --
        not counted as a hook, and not counted as two."""
        img = _paper()
        _stem(img)
        cv2.line(img, (int(STEM_X0 - 1.0 * SP), int(TIP_Y + 2.2 * SP)),
                 (int(STEM_X1 + 1.0 * SP), int(TIP_Y + 1.4 * SP)), 0,
                 thickness=int(0.45 * SP))
        r = _count(img, head_edge=FAR_Y - 40)
        self.assertIsNone(r["hooks"])
        self.assertEqual(r["hooks_reason"], gather.HOOKS_UNCOUNTED_BOTH_SIDES)

    def test_a_hook_AND_a_slash_on_the_same_stem_is_still_refused(self):
        img = _paper()
        _stem(img)
        _hook(img, TIP_Y + 3)
        cv2.line(img, (int(STEM_X0 - 1.0 * SP), int(TIP_Y + 2.6 * SP)),
                 (int(STEM_X1 + 1.0 * SP), int(TIP_Y + 1.8 * SP)), 0,
                 thickness=int(0.45 * SP))
        r = _count(img, head_edge=FAR_Y - 40)
        self.assertIsNone(r["hooks"])

    def test_attached_ink_far_from_the_tip_is_not_a_SECOND_hook(self):
        """A slur or a ledger line meeting the stem's RIGHT side only, two
        spaces below the hook, is attached ink and not a stacked hook:
        hooks leave the stem a hook-spacing apart, not two spaces."""
        img = _paper()
        _stem(img)
        _hook(img, TIP_Y + 3)
        img[int(TIP_Y + 2.4 * SP):int(TIP_Y + 2.8 * SP),
            int(STEM_X1):int(STEM_X1 + 1.3 * SP)] = 0
        r = _count(img, head_edge=FAR_Y - 40)
        self.assertIsNone(r["hooks"])
        self.assertEqual(r["hooks_reason"], gather.HOOKS_UNCOUNTED_UNRESOLVED)
        self.assertEqual((r["hooks_min"], r["hooks_max"]), (1, 2))

    def test_the_stems_OWN_head_is_not_counted_as_a_hook(self):
        """A down stem's head stands to the RIGHT of the stem at its far
        end. Past `head_edge` it is not part of the band; without the cut it
        is (the control that proves the cut matters)."""
        img = _paper()
        _stem(img)
        _hook(img, TIP_Y + 3)
        # a head blob right of the stem, 3.1 spaces below the tip
        img[int(TIP_Y + 3.1 * SP):int(TIP_Y + 4.1 * SP),
            int(STEM_X1):int(STEM_X1 + 1.3 * SP)] = 0
        cut = _count(img, head_edge=TIP_Y + 3.1 * SP)
        self.assertEqual(cut["hooks"], 1)
        uncut = _count(img)
        self.assertNotEqual(uncut["hooks"], 1)

    def test_a_raster_with_no_room_returns_None(self):
        self.assertIsNone(gather.stem_tip_hooks(None, 1, 2, 3, 1.0, SP))
        self.assertIsNone(gather.stem_tip_hooks(_paper(h=50, w=50), STEM_X0,
                                                STEM_X1, TIP_Y, 1.0, SP))
        self.assertIsNone(gather.stem_tip_hooks(_paper(), STEM_X0, STEM_X1,
                                                TIP_Y, 1.0, 0.0))

    def test_too_short_a_band_says_no_room(self):
        img = _paper()
        _stem(img)
        _hook(img, TIP_Y + 3)
        r = _count(img, head_edge=TIP_Y + 0.8 * SP)
        self.assertIsNone(r["hooks"])
        self.assertEqual(r["hooks_reason"], gather.HOOKS_UNCOUNTED_NO_ROOM)


class TestWhereTheHeadStands(unittest.TestCase):
    """`gather._head_edge_for_end` -- the cut, and the end-is-a-head guard."""

    def test_a_head_at_the_far_end_gives_the_edge_the_band_stops_at(self):
        heads = [(STEM_X0 - 50, FAR_Y - 20, 52, 40)]          # up stem's head
        edge, here = gather._head_edge_for_end(
            heads, STEM_X0, STEM_X1, TIP_Y, 1.0, SP)
        self.assertFalse(here)
        self.assertEqual(edge, FAR_Y - 20)

    def test_a_head_AT_this_end_means_it_is_not_a_flags_tip(self):
        heads = [(STEM_X0 - 50, TIP_Y - 20, 52, 40)]
        edge, here = gather._head_edge_for_end(
            heads, STEM_X0, STEM_X1, TIP_Y, 1.0, SP)
        self.assertTrue(here)
        self.assertIsNone(edge)

    def test_no_detection_map_cuts_nothing(self):
        self.assertEqual(gather._head_edge_for_end(
            None, STEM_X0, STEM_X1, TIP_Y, 1.0, SP), (None, False))

    def test_a_far_away_head_is_not_this_stems(self):
        heads = [(STEM_X0 + 400, FAR_Y - 20, 52, 40)]
        self.assertEqual(gather._head_edge_for_end(
            heads, STEM_X0, STEM_X1, TIP_Y, 1.0, SP), (None, False))


class FakeCell:
    def __init__(self, image_no_staff):
        self.image_no_staff = image_no_staff


SUB = R.cell(0, 0, 0, 0)
STEM_BOX = (STEM_X0, TIP_Y, STEM_X1 - STEM_X0, FAR_Y - TIP_Y)        # x,y,w,h
HEAD_AT_FAR_END = [(STEM_X0 - 50.0, FAR_Y - 20.0, 52.0, 40.0)]


def _file(img, heads=HEAD_AT_FAR_END):
    log = Log()
    gather._observe_stem_tip_ink(log, SUB, "cell:0", FakeCell(img),
                                 "obs:stem-1", STEM_BOX, [], SP, heads=heads)
    log.freeze()
    return {r.detail["end"]: r for r in log.rows(Q.STEM_TIP_INK, SUB)}


class TestTheRowCarriesTheCount(unittest.TestCase):

    def test_a_seen_hook_files_its_count_in_the_detail_RED(self):
        img = _paper()
        _stem(img)
        _hook(img, TIP_Y + 3)
        _hook(img, TIP_Y + 3 + 0.7 * SP)
        rows = _file(img)
        top = rows["top"]
        self.assertTrue(top.value)
        self.assertEqual(top.detail["hooks"], 2)
        self.assertEqual(top.detail["hooks_min"], 2)

    def test_the_value_stays_the_2_18c_boolean(self):
        img = _paper()
        _stem(img)
        _hook(img, TIP_Y + 3)
        top = _file(img)["top"]
        self.assertIs(top.value, True)

    def test_POSITIVE_CONTROL_no_ink_files_no_count(self):
        """Not found -> no count keys at all (the count is read only where a
        hook is seen), so a clean tip can never carry a stale one."""
        img = _paper()
        _stem(img)
        rows = _file(img)
        self.assertFalse(rows["top"].value)
        self.assertNotIn("hooks", rows["top"].detail)

    def test_a_head_at_the_end_is_not_a_tip_so_no_row_and_no_count(self):
        """The same ink asked at the HEAD'S end of the stem: this end is not
        a flag's tip. ROADMAP 2.83: it was filed as a found row whose count
        said so; the window now stops short of the stem's own head and an end a
        head stands at abstains OCCUPIED with the reason word, so no row can
        carry a count at all (the head's ink is not a hook)."""
        img = _paper()
        _stem(img)
        _hook(img, FAR_Y - 3 - 0.0 * SP, down=False)
        heads = [(STEM_X0 - 50.0, FAR_Y - 20.0, 52.0, 40.0)]
        log = Log()
        gather._observe_stem_tip_ink(log, SUB, "cell:0", FakeCell(img),
                                     "obs:stem-1", STEM_BOX, [], SP, heads=heads)
        log.freeze()
        rows = {r.detail["end"]: r for r in log.rows(Q.STEM_TIP_INK, SUB)}
        abst = {a.detail["end"]: a for a in log.refusals(Q.STEM_TIP_INK, SUB)}
        self.assertNotIn("bottom", rows)
        self.assertEqual(abst["bottom"].reason, ABSTAIN.OCCUPIED)
        self.assertEqual(abst["bottom"].detail["why"],
                         gather.HOOKS_UNCOUNTED_HEAD_AT_END)


# ─────────────────────────────────────────────────────────────────────────────
# The bar's arithmetic settles an uncounted hook (EVALUATE, not a new rule)
# ─────────────────────────────────────────────────────────────────────────────

CELL = R.cell(0, 0, 1, 3)


def _v(log, sub, q, outcome, value, reason="t", candidates=()):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome,
        value=value, decider="test", reason=reason, detail={},
        candidates=candidates))


def _dur(beats, levels):
    return {"beats": beats, "written": beats, "dots": 0,
            "beam_levels": levels}


def _decided(log, g, beats, levels):
    sub = R.glyph(0, 0, 1, 3, g)
    _v(log, sub, Q.DURATION, Outcome.DECIDED, _dur(beats, levels),
       reason="head_and_marks")
    return sub


def _uncounted_hook(log, g):
    """The narrowing `adjudicate_duration` files for a hook seen and not
    counted: an eighth or a sixteenth, NEVER the quarter the head says."""
    sub = R.glyph(0, 0, 1, 3, g)
    _v(log, sub, Q.DURATION, Outcome.NARROWED, None, reason="flag_ink_unread",
       candidates=(Candidate(_dur(0.5, 1), 2.0), Candidate(_dur(0.25, 2), 1.0)))
    return sub


def _meter(log, num, den):
    return _v(log, R.system(0, 0), Q.METER, Outcome.DECIDED,
              {"numerator": num, "denominator": den, "raw": f"{num}/{den}"})


def _events(log, *groups):
    _v(log, CELL, Q.EVENT, Outcome.DECIDED,
       {"events": [{"glyphs": [g]} for g in groups]})


class TestTheBarSettlesAnUncountedHook(unittest.TestCase):

    def test_a_bar_that_needs_an_EIGHTH_takes_the_eighth(self):
        """2/4 = 3 eighths + the unread-count note: only the eighth fits."""
        log = Log()
        for g in range(3):
            _decided(log, g, 0.5, 1)
        note = _uncounted_hook(log, 3)
        _events(log, 0, 1, 2, 3)
        out = consequences.reconcile_duration(log, CELL, _meter(log, 2, 4))
        self.assertEqual(len(out), 1)
        self.assertEqual(log.verdict(Q.DURATION, note).value["beats"], 0.5)

    def test_a_bar_that_needs_a_SIXTEENTH_takes_the_sixteenth(self):
        """5/16 = a quarter + the unread-count note: only the SIXTEENTH
        fits -- the bar's arithmetic chose it where the ink could not, which
        is the whole of Sean's ruling. (Green on the old tree too: EVALUATE
        already searches a narrowing's own candidates -- this pins that it
        takes the new narrowing as it is, with nothing added.)
        """
        log = Log()
        _decided(log, 0, 1.0, 0)
        note = _uncounted_hook(log, 1)
        _events(log, 0, 1)
        out = consequences.reconcile_duration(log, CELL, _meter(log, 5, 16))
        self.assertEqual(len(out), 1)
        self.assertEqual(log.verdict(Q.DURATION, note).value["beats"], 0.25)

    def test_POSITIVE_CONTROL_a_bar_neither_fits_is_left_unsettled(self):
        """3/8 = 1.5 beats: 2 eighths + {0.5, 0.25} lands on 1.5 with the
        EIGHTH and on 1.25 with the sixteenth -- settled. Here, 2 eighths +
        a quarter in 3/16 land NEITHER, so nothing changes and the note
        stays narrowed: the rule refuses rather than guesses."""
        log = Log()
        _decided(log, 0, 0.5, 1)
        _decided(log, 1, 0.5, 1)
        note = _uncounted_hook(log, 2)
        _events(log, 0, 1, 2)
        out = consequences.reconcile_duration(log, CELL, _meter(log, 3, 16))
        self.assertEqual(out, [])
        self.assertIs(log.verdict(Q.DURATION, note).outcome, Outcome.NARROWED)


if __name__ == "__main__":
    unittest.main()
