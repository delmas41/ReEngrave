"""ROADMAP 2.49 -- a stroke crossing a stem is a tremolo slash, not a
notehead.

Sean, DECISIONS 2026-10-01: "a single notehead can't extend on either side
of the stem. A beam can but it must be connected to another stem and must
be at the end of the stem. Any time a stem has a diagonal ink slash (that
could be confused with a notehead) it must land on one side of the stem."
CONVENTION CONFIRMED (not assumed) -- Sean stated the rule directly.

Three layers, matching how `test_staged_stacked_head_fit.py` (ROADMAP 2.42,
the mechanism this item composes with) splits its own:

  A. `gather._stem_cross_regions` / `gather._region_ink_fraction` -- pure,
     on constructed boxes and rasters. No Log, no cells.
  B. `gather.gather_notehead_stem_cross_ink` -- the reader wired into a Log,
     over synthetic `MeasureCell`s -- confirms the SPLIT (ink read on each
     side of the matched stem) and the no-row cases (no stem, not a
     notehead detection).
  C. `notehead_precision._tremolo_slash_crosses_stem` and its effect on
     `_stacked_head_duplicate_refusal`'s own keep-choice -- ADJUDICATE, with
     `Q.NOTEHEAD_STEM_CROSS_INK`/`Q.STACKED_HEAD_FIT` rows injected directly
     (the same style `test_staged_stacked_head_fit.py` injects
     `Q.STACKED_HEAD_FIT`).

⚠️ RUN RED FIRST: `gather._stem_cross_regions`, `gather._region_ink_
fraction`, `gather.gather_notehead_stem_cross_ink`, `Q.NOTEHEAD_STEM_CROSS_
INK`, `READERS.CV_NOTEHEAD_STEM_CROSS_INK` and `notehead_precision.
_tremolo_slash_crosses_stem`/`TREMOLO_SLASH_REASON` do not exist on the
tree before this round -- every reference below raises `AttributeError`
and the `adjudicate.run` calls at layer C are unaffected by that (the
decision itself already exists from ROADMAP 2.4a) but score differently
without the fix (see `TestTremoloSlashNeverWinsAStackedKeepChoice`'s own
"without the fix" regression test, which passes BOTH before and after --
it exists to prove the OTHER test in that class is not a tautology).

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""

from __future__ import annotations

import unittest
import unittest.mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.staged.record import Log, Q, READERS, State

from tools.omr.tests.test_staged_notehead_recentre import _paper
from tools.omr.tests.test_staged_notehead_precision import (
    _cell_geometry, _notehead)
from tools.omr.tests.test_staged_stacked_head_fit import (
    _cell, _detection, _fit_row, _stem_row)

SPACING = 40.0


# ─────────────────────────────────────────────────────────────────────────────
# A. `gather._stem_cross_regions` / `gather._region_ink_fraction` -- pure
# ─────────────────────────────────────────────────────────────────────────────


class TestStemCrossRegionsPure(unittest.TestCase):

    def test_splits_around_the_stems_own_centre_with_a_guard(self):
        box = (100.0, 50.0, 140.0, 100.0)        # x, y, w, h -- spans 100-240
        stem = (160.0, 0.0, 10.0, 260.0)         # centre x = 165, half=5
        regions = gather._stem_cross_regions(box, stem, guard_px=1.0)
        self.assertIsNotNone(regions)
        left, right = regions
        self.assertAlmostEqual(left[0], 100.0)
        self.assertAlmostEqual(left[0] + left[2], 159.0)   # 165 - 5 - 1
        self.assertAlmostEqual(right[0], 171.0)            # 165 + 5 + 1
        self.assertAlmostEqual(right[0] + right[2], 240.0)

    def test_box_entirely_on_one_side_of_the_stem_has_no_regions(self):
        """A normal head's box runs from the stem's own edge OUTWARD, never
        straddling its centre -- `None`, not a degenerate zero-width side."""
        box = (0.0, 0.0, 50.0, 50.0)
        stem = (500.0, 0.0, 10.0, 200.0)
        self.assertIsNone(gather._stem_cross_regions(box, stem))

    def test_a_stem_wider_than_the_box_has_no_regions(self):
        box = (100.0, 0.0, 10.0, 50.0)
        stem = (90.0, 0.0, 40.0, 200.0)           # stem spans 90-130
        self.assertIsNone(gather._stem_cross_regions(box, stem))


class TestRegionInkFractionPure(unittest.TestCase):

    def test_solid_ink_reads_one(self):
        img = _paper(h=50, w=50)
        img[:, :] = 0
        self.assertEqual(gather._region_ink_fraction(img, (0, 0, 50, 50)), 1.0)

    def test_blank_paper_reads_zero(self):
        img = _paper(h=50, w=50)
        self.assertEqual(gather._region_ink_fraction(img, (0, 0, 50, 50)), 0.0)

    def test_off_raster_box_is_none(self):
        img = _paper(h=50, w=50)
        self.assertIsNone(
            gather._region_ink_fraction(img, (1000.0, 1000.0, 10.0, 10.0)))


# ─────────────────────────────────────────────────────────────────────────────
# B. `gather.gather_notehead_stem_cross_ink` -- wired into a Log
# ─────────────────────────────────────────────────────────────────────────────


class TestGatherNoteheadStemCrossInkWiring(unittest.TestCase):

    def _run(self, img, dets, *, stem=(200.0, 40.0, 10.0, 260.0)):
        cell = _cell(img)
        sub = R.cell(0, 0, 0, 0)
        log = Log()
        if stem is not None:
            _stem_row(log, sub, x_c=stem[0], y_c=stem[1], w_c=stem[2],
                     h_c=stem[3])
        gather.gather_notehead_stem_cross_ink(
            log, [cell], {0: (0, 0)}, {sub.to_key(): dets})
        return log

    def test_a_real_head_beside_its_stem_reads_low_on_the_far_side(self):
        """CONTROL -- Sean's own convention: a real head's ink lies on ONE
        side. Box spans x 130-270 around a stem centred at x=200; ink is
        painted only LEFT of the stem (a down-stem head attaching at its
        right edge, CLAUDE.md §10: 'down -> left')."""
        img = _paper(h=400, w=400)
        img[150:250, 130:195] = 0
        d = _detection("noteheadBlackInSpace", 200.0, 200.0, w=140.0, h=100.0)
        log = self._run(img, [d])
        g = R.glyph(0, 0, 0, 0, 0)
        rows = log.rows(Q.NOTEHEAD_STEM_CROSS_INK, g)
        self.assertEqual(len(rows), 1)
        left, right = rows[0].value
        self.assertGreater(left, 0.5)
        self.assertLess(right, 0.05)

    def test_a_tremolo_slash_reads_high_on_both_sides(self):
        """The shape this item exists to catch: ink on BOTH sides of the
        stem, within the SAME box."""
        img = _paper(h=400, w=400)
        img[150:250, 130:195] = 0
        img[150:250, 205:270] = 0
        d = _detection("noteheadBlackInSpace", 200.0, 200.0, w=140.0, h=100.0)
        log = self._run(img, [d])
        g = R.glyph(0, 0, 0, 0, 0)
        rows = log.rows(Q.NOTEHEAD_STEM_CROSS_INK, g)
        self.assertEqual(len(rows), 1)
        left, right = rows[0].value
        self.assertGreater(left, 0.5)
        self.assertGreater(right, 0.5)
        self.assertIsNotNone(rows[0].detail.get("stem"),
                             "the row must name the Q.STEM row it split against")

    def test_a_beam_stroke_crossing_the_box_is_excluded_from_both_sides(self):
        """CONTROL -- manager review, real re-gather: a `Q.BEAM_STROKE` box
        reaches far past a notehead's own box on both sides whenever it
        overlaps the box at all (measured ~500 px vs ~150 px on Litolff),
        which is the convention's own named exception ("a beam may cross,
        but only joined to another stem at the stem's end"). Ink painted
        for the SAME beam stroke on both sides must be EXCLUDED, not read
        as a slash."""
        img = _paper(h=400, w=400)
        # a beam stroke spanning far wider than the box, crossing the stem
        img[150:170, 0:400] = 0
        d = _detection("noteheadBlackInSpace", 200.0, 200.0, w=140.0, h=100.0)
        cell = _cell(img)
        sub = R.cell(0, 0, 0, 0)
        log = Log()
        _stem_row(log, sub, x_c=200.0, y_c=40.0, w_c=10.0, h_c=260.0)
        log.observe(sub, Q.BEAM_STROKE, (0.0, 150.0, 400.0, 20.0),
                   reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        gather.gather_notehead_stem_cross_ink(
            log, [cell], {0: (0, 0)}, {sub.to_key(): [d]})
        g = R.glyph(0, 0, 0, 0, 0)
        rows = log.rows(Q.NOTEHEAD_STEM_CROSS_INK, g)
        self.assertEqual(len(rows), 1)
        left, right = rows[0].value
        self.assertEqual(left, 0.0)
        self.assertEqual(right, 0.0)

    def test_no_stem_at_all_gets_no_row(self):
        """CLAUDE.md rule 8: with no stem read in the cell, this quantity
        has nothing to say -- no row, never a guess."""
        img = _paper(h=400, w=400)
        d = _detection("noteheadBlackInSpace", 200.0, 200.0, w=140.0, h=100.0)
        log = self._run(img, [d], stem=None)
        g = R.glyph(0, 0, 0, 0, 0)
        self.assertEqual(log.state(Q.NOTEHEAD_STEM_CROSS_INK, g), State.ABSENT)

    def test_a_non_notehead_detection_gets_no_row(self):
        img = _paper(h=400, w=400)
        d = _detection("beam", 200.0, 200.0, w=140.0, h=20.0)
        log = self._run(img, [d])
        g = R.glyph(0, 0, 0, 0, 0)
        self.assertEqual(log.state(Q.NOTEHEAD_STEM_CROSS_INK, g), State.ABSENT)

    def test_a_head_whose_box_does_not_reach_past_the_stem_gets_no_row(self):
        """`_stem_cross_regions` returns `None` -- this measurement does not
        apply, not a guessed zero on either side."""
        img = _paper(h=400, w=400)
        d = _detection("noteheadBlackInSpace", 50.0, 200.0, w=40.0, h=40.0)
        log = self._run(img, [d], stem=(500.0, 40.0, 10.0, 260.0))
        g = R.glyph(0, 0, 0, 0, 0)
        self.assertEqual(log.state(Q.NOTEHEAD_STEM_CROSS_INK, g), State.ABSENT)


# ─────────────────────────────────────────────────────────────────────────────
# C. ADJUDICATE -- `_tremolo_slash_crosses_stem` and the stacked keep-choice
# ─────────────────────────────────────────────────────────────────────────────


def _cross_ink_row(log, g, *, left, right, stem="stem/0/0/0/0"):
    return log.observe(g, Q.NOTEHEAD_STEM_CROSS_INK, [left, right],
                       reader=READERS.CV_NOTEHEAD_STEM_CROSS_INK,
                       frame="cell:0", stem=stem, left=left, right=right)


def _run_notehead(log):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    return log


class TestTremoloSlashCrossesStem(unittest.TestCase):
    """⚠️⚠️ MEASURED NET NEGATIVE ON REAL DATA AND HELD BACK
    (`TREMOLO_SLASH_SHIPS = False`, see its own docstring): the Litolff small
    re-gather (pages 1-3 through the count page, 2026-10-01) refuses the TWO
    fixed cases correctly but ALSO refuses 121-132 of 481 notehead-classed
    glyphs on the count page alone (~25%) -- crops under `out/print/2.49/`
    show every sampled false positive is a dense beamed run or chord on this
    MERGING plate, not a slash. The SIGNAL (`detail["tremolo_slash_signal"]`,
    including `would_fire`) is still computed and recorded; it never sets
    `value=True` while the constant is `False`. These tests assert the
    SIGNAL, not a refusal -- the same discipline `TestUnladdered` in
    `test_staged_notehead_precision.py` uses for its own held-back rule."""

    def test_ink_on_both_sides_above_floor_is_SIGNALLED_but_not_refused(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlackInSpace")
        _cross_ink_row(log, g, left=0.5, right=0.5)
        log = _run_notehead(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")
        self.assertTrue(v.detail["tremolo_slash_signal"]["would_fire"])

    def test_a_head_beside_its_stem_signals_would_NOT_have_fired(self):
        """CONTROL: ink almost entirely on ONE side -- never flagged, even
        were this rule shipped."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlackInSpace")
        _cross_ink_row(log, g, left=0.8, right=0.02)
        log = _run_notehead(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")
        self.assertFalse(v.detail["tremolo_slash_signal"]["would_fire"])

    def test_a_real_beam_join_at_a_stems_end_is_not_signalled_at_all(self):
        """CONTROL named in the brief: a real beam crosses only joined to
        ANOTHER stem at THIS stem's end -- it is never boxed as a notehead
        at all, so it never reaches this rule. Modelled here as "no
        `Q.NOTEHEAD_STEM_CROSS_INK` row filed" (GATHER only measures
        notehead-classed glyphs); nothing is even computed."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlackInSpace")
        log = _run_notehead(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")
        self.assertNotIn("tremolo_slash_signal", v.detail)

    def test_a_chord_second_on_opposite_sides_of_the_stem_is_untouched(self):
        """CONTROL -- Sean, 2026-09-30: "a second is always on opposite
        sides of the stem." Each note's OWN box carries ink on its OWN side
        only; neither glyph's own split crosses the stem."""
        log = Log()
        _cell_geometry(log)
        # dy = 0.5 sp (SPACING=100, this file's own default), past 2.30's
        # own 0.25 sp centre gate, so `notehead_is_a_duplicate_box` does not
        # refuse `b` as the SAME mark as `a` before this rule ever runs --
        # the same fixture discipline used throughout this file.
        a = _notehead(log, 0, cls="noteheadBlackInSpace", pos_float=3.0,
                     y_c=200.0)
        b = _notehead(log, 1, cls="noteheadBlackInSpace", pos_float=4.0,
                     y_c=250.0)
        _cross_ink_row(log, a, left=0.7, right=0.0)
        _cross_ink_row(log, b, left=0.0, right=0.7)
        log.freeze()
        adjudicate._ensure_decisions()
        adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
        v_a = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, a)
        v_b = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, b)
        self.assertIs(v_a.value, False)
        self.assertIs(v_b.value, False)
        self.assertFalse(v_a.detail["tremolo_slash_signal"]["would_fire"])
        self.assertFalse(v_b.detail["tremolo_slash_signal"]["would_fire"])

    def test_one_side_below_floor_signals_would_NOT_have_fired(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlackInSpace")
        _cross_ink_row(log, g, left=0.5,
                       right=NP.TREMOLO_SLASH_INK_FLOOR - 0.01)
        log = _run_notehead(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, False)
        self.assertFalse(v.detail["tremolo_slash_signal"]["would_fire"])

    def test_the_reason_is_named_apart_from_every_other_mechanism(self):
        self.assertNotEqual(NP.TREMOLO_SLASH_REASON, "stacked_head_duplicate")
        self.assertNotEqual(NP.TREMOLO_SLASH_REASON,
                            "notehead_is_a_duplicate_box")
        self.assertNotEqual(NP.TREMOLO_SLASH_REASON, "same_side_second")

    def test_it_can_never_actually_refuse_anything_today(self):
        """⚠️ ASSERTED OFF THE CONSTANT, so a future flip is a one-line,
        reviewable change rather than a silent behavioural drift --
        `TestUnladdered.test_it_can_never_actually_refuse_anything`'s own
        discipline."""
        self.assertFalse(NP.TREMOLO_SLASH_SHIPS)


class TestTremoloSlashWouldNeverWinAStackedKeepChoiceIfShipped(unittest.TestCase):
    """ROADMAP 2.49's own fixed case: Litolff `glyph/13/1/8/13/5` -- 2.42's
    stacked-head keep-choice picked a tremolo slash's higher ink OVER the
    real open head it crossed. The MECHANISM that fixes this (the slash
    refused on its own ink, BEFORE the stacked comparison, and dropped from
    the group so it can never be chosen as the slot's keeper) is built and
    verified HERE with `TREMOLO_SLASH_SHIPS` patched on for the one test --
    but it is NOT active by default (see `TestTremoloSlashCrossesStem`'s own
    class docstring: measured net negative on real data). Confirmed on the
    real Litolff re-gather too (`benchmarks/acceptance/quick/out/
    beethoven5-litolff-p13/p13.record.json`, page 13 system 1 staff 8 cell
    13): the slash sharing that head's slot DOES carry both-sides ink
    (0.78/0.63) and the real head's own slot has no cross-ink row at all
    (its box never reaches past the stem on either side) -- the shape this
    item targets is real, only the corpus-wide floor is not safe yet."""

    def test_with_the_mechanism_SHIPPED_the_slash_loses_and_the_head_survives(self):
        log = Log()
        _cell_geometry(log)
        # dy = 0.5 sp (SPACING=100 here, `_notehead`'s own default),
        # past 2.30's own 0.25 sp centre gate, so `notehead_is_a_duplicate_
        # box` does not refuse either box first and mask this rule entirely
        # -- the same fixture discipline `test_staged_stacked_head_fit.py`
        # uses for the identical reason.
        head = _notehead(log, 0, cls="noteheadHalfOnLine", pos_float=4.0,
                        y_c=200.0)
        slash = _notehead(log, 1, cls="noteheadHalfOnLine", pos_float=4.0,
                          y_c=250.0)
        _fit_row(log, head, k=1, slot=0, pos_float=4.0, ink=0.30)
        _fit_row(log, slash, k=1, slot=0, pos_float=4.0, ink=0.90)
        _cross_ink_row(log, slash, left=0.55, right=0.55)
        log.freeze()
        adjudicate._ensure_decisions()
        with unittest.mock.patch.object(NP, "TREMOLO_SLASH_SHIPS", True):
            adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
        v_head = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, head)
        v_slash = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, slash)
        self.assertIs(v_slash.value, True)
        self.assertEqual(v_slash.reason, "tremolo_slash_crosses_stem")
        self.assertIs(v_head.value, False,
                      "the real head must survive now that its only "
                      "competitor in the stacked group is a tremolo slash")

    def test_UNSHIPPED_today_the_slash_still_wins_the_keep_choice(self):
        """The current, DEFAULT behaviour: with `TREMOLO_SLASH_SHIPS` at its
        real value (`False`), the signal changes nothing and 2.42's own
        ink-not-score rule still picks the slash's higher ink, refusing the
        real head instead -- the held-back state, not a fixed one."""
        log = Log()
        _cell_geometry(log)
        head = _notehead(log, 0, cls="noteheadHalfOnLine", pos_float=4.0,
                        y_c=200.0)
        slash = _notehead(log, 1, cls="noteheadHalfOnLine", pos_float=4.0,
                          y_c=250.0)
        _fit_row(log, head, k=1, slot=0, pos_float=4.0, ink=0.30)
        _fit_row(log, slash, k=1, slot=0, pos_float=4.0, ink=0.90)
        _cross_ink_row(log, slash, left=0.55, right=0.55)
        log = _run_notehead(log)
        v_head = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, head)
        self.assertIs(v_head.value, True)
        self.assertEqual(v_head.reason, "stacked_head_duplicate")


if __name__ == "__main__":
    unittest.main()
