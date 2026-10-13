"""ROADMAP 2.83 -- ADJUDICATE reads what the tip reader now sees.

PART A -- a FLAG READ AT THE STEM TIP OUTRANKS THE DISCOUNT NARROWING. `adjudicate_duration` returns
`beam_discounted_uncertain` (the head value or ONE beam level, the beam level ranked above the head's own) whenever every
stroke that could have been this head's beam was refused (a neighbour staff's beam, a decided arc's ink, a stroke the ink
reads as too thin) and nothing else marks the note. That branch sat BEFORE the stem-tip reading (2.18c/2.69), so a head whose
own stem tip carries a flag the tip reader SAW never reached it: 3,604 of 24,260 Brahms heads stand in that narrowing
(FINDINGS 17). Where the tip reader says a hook is there, the head is a flagged note: DECIDED where the ink counted the hooks
(`hooks_counted`), NARROWED over the flag levels (`flag_ink_unread`, level 0 excluded) where it did not.

PART B -- A DETECTOR FLAG BOX ATTACHES TO A HEAD WHOSE STEM WAS ONLY READ BY `Q.HEAD_STEM_REACH`. `_attached_flags` joins a
flag to the CV stem that touches the head, so a contested head whose stem the CV rung never found (two stacked heads fuse into
one too-wide component) could never carry the flag the detector had boxed at its stem's tip: `flags_attached` 0 and a quarter
written (Sean's page, `q129`/`q132`). The ruler's own stem (`down_tip_y` / `up_tip_y`, the side edge the CLAUDE.md 10
convention fixes) stands in for the CV stem, and a flag box attaches only where it hangs off THAT tip the way the CV path's own
test (`gather._flag_box_hangs_off_stem`) says and its class direction agrees with the ruler's.

RUN RED FIRST against the unrepaired tree: the Part A and Part B positive tests fail; every control (a clean tip still
decides the head value, a flag box of another stem, a flag of the opposite direction, no ruler row at all) passes on both.
NO TEST ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md 6c).
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS

from tools.omr.tests.test_staged_duration import (CELL, SPACE, _beam, _flag, _notehead_ink,
                                                  _staff_space, _stem, _stem_tip_ink)

PAGE_DX, PAGE_DY = 1000.0, 900.0        # the synthetic cell's page offset (scale 1)


def _discounted_head(log, *, with_tip=None, hooks=None):
    """The 2.25b rule-8 population: a stemmed black head (stem above it, so UP) whose ONLY candidate stroke is the NEIGHBOUR
    staff's beam, discounted -- narrowed `beam_discounted_uncertain` today. `with_tip`: file the `Q.STEM_TIP_INK` row for the
    stem's top end (True / False) with `hooks` as its counted level (None = seen but uncounted)."""
    log.observe(R.staff(0, 0, 0), Q.STAFF_LINES, [950.0, 960.0, 970.0, 980.0, 990.0],
                reader=READERS.GEOMETRY, frame="page")
    _staff_space(log)
    g = R.glyph(0, 0, 0, 0, 0)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 100, 90, 20, 16), reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                bbox_page_px=[1100, 990, 1120, 1006])
    gb = R.glyph(0, 0, 1, 0, 0)
    log.observe(gb, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(gb, Q.GLYPH_BOX, ("noteheadBlack", 100, 20, 20, 16), reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                bbox_page_px=[1100, 1070, 1120, 1086])
    cell_a = g.at(R.Kind.CELL)
    log.observe(cell_a, Q.BEAM_STROKE, (90, 150, 40, 4), reader=READERS.CV_LINES, frame="cell:0", x0=90, x1=130,
                y_center=152, image="no_staff", staff_lines_erased=True)
    stem = log.observe(cell_a, Q.STEM, (105, 60, 4, 40), reader=READERS.CV_LINES, frame="cell:0", x0=105, x1=109,
                       y_center=80, image="no_staff", staff_lines_erased=True)
    cell_b = R.cell(0, 0, 1, 0)
    log.observe(cell_b, Q.STEM, (90, -10, 4, 50), reader=READERS.CV_LINES, frame="cell:0", x0=90, x1=94, y_center=15,
                image="no_staff", staff_lines_erased=True)
    if with_tip is not None:
        detail = {}
        if with_tip and hooks:
            detail = {"hooks": hooks, "hooks_min": hooks, "hooks_max": hooks, "hooks_reason": None}
        elif with_tip:
            detail = {"hooks": None, "hooks_min": 1, "hooks_max": 2, "hooks_reason": "unresolved"}
        _stem_tip_ink(log, stem_row_id=stem.id, end="top", found=with_tip, **detail)
    return g


class TestAFlagReadAtTheTipOutranksTheDiscount(unittest.TestCase):

    def test_CONTROL_without_a_tip_row_the_head_stays_beam_discounted_uncertain(self):
        log = Log()
        g = _discounted_head(log)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beam_discounted_uncertain")

    def test_CONTROL_a_tip_read_clean_does_not_change_the_discount_narrowing(self):
        """Nothing hangs from the tip: the discount narrowing stands exactly as it was (2.81's quarter rule is a separate
        item); the tip reader's False must not decide a quarter here."""
        log = Log()
        g = _discounted_head(log, with_tip=False)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beam_discounted_uncertain")

    def test_a_counted_hook_at_the_tip_DECIDES_an_eighth_RED(self):
        log = Log()
        g = _discounted_head(log, with_tip=True, hooks=1)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED, v.reason)
        self.assertEqual(v.reason, "hooks_counted")
        self.assertEqual(v.value["beam_levels"], 1)
        self.assertEqual(v.value["beats"], 0.5)

    def test_a_hook_seen_but_not_counted_NARROWS_over_the_flag_levels_and_drops_the_quarter_RED(self):
        log = Log()
        g = _discounted_head(log, with_tip=True, hooks=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "flag_ink_unread")
        self.assertNotIn(1.0, {c.value["beats"] for c in v.candidates})
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates), [0.25, 0.5])


# ─────────────────────────────────────────────────────────────────────────────
# PART B -- a flag box and a head whose stem only the ruler read
# ─────────────────────────────────────────────────────────────────────────────

def _reach_head(log, *, side="down", ext=3.2, with_flag=None, flag_x=98, reach_row=True):
    """A black head (x 100..120, y 90..106) with NO CV stem, its stem read by `Q.HEAD_STEM_REACH` (page frame: the
    synthetic cell's page offset is (+1000, +900) at scale 1, one space = SPACE px). `with_flag`: the detector's flag class
    boxed at the tip of that stem."""
    _staff_space(log)
    # a decoy beam far away in x, on the STEM side of the head, so the beam reader state is READ, not absent
    # (`beam_evidence` none_over_this_note) and no stroke is removed as being on the far side of the head
    decoy_y = 150 if side == "down" else 2
    log.observe(CELL, Q.BEAM_STROKE, (400, decoy_y, 60, 4), reader=READERS.CV_LINES, frame="cell:0", x0=400, x1=460,
                y_center=decoy_y + 2, image="no_staff", staff_lines_erased=True)
    g = R.glyph(0, 0, 0, 0, 0)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 100, 90, 20, 16), reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                bbox_page_px=[1100.0, 990.0, 1120.0, 1006.0])
    if reach_row:
        tip_canon = 106 + ext * SPACE if side == "down" else 90 - ext * SPACE
        detail = dict(head_box_page=[1100.0, 990.0, 1120.0, 1006.0], sp=float(SPACE), down_ext=0.0, up_ext=0.0,
                      down_tip_y=None, up_tip_y=None)
        detail[side + "_ext"] = ext
        detail[side + "_tip_y"] = tip_canon + PAGE_DY
        log.observe(g, Q.HEAD_STEM_REACH, side, reader=READERS.CV_HEAD_STEM_REACH, frame="page", **detail)
    if with_flag:
        tip = 106 + ext * SPACE if side == "down" else 90 - ext * SPACE
        # a down-stem's flag box hangs UP from its bottom tip; an up-stem's hangs DOWN from its top tip
        y = tip - 40 if side == "down" else tip
        _flag(log, gi=50, cls=with_flag, x=flag_x, y=y, w=12, h=42)
    return g


class TestAFlagBoxAttachesToAHeadWhoseStemOnlyTheRulerRead(unittest.TestCase):

    def test_CONTROL_without_a_flag_box_the_head_decides_its_head_value(self):
        log = Log()
        g = _reach_head(log, with_flag=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beam_levels"], 0)

    def test_a_flag_box_at_the_tip_of_the_rulers_down_stem_attaches_RED(self):
        log = Log()
        g = _reach_head(log, side="down", with_flag="flag8thDown")
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED, v.reason)
        self.assertEqual(v.value["beam_levels"], 1)
        self.assertEqual(v.detail["flags_attached"], 1)

    def test_the_same_for_an_UP_stem(self):
        log = Log()
        g = _reach_head(log, side="up", ext=3.2, with_flag="flag8thUp", flag_x=114)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beam_levels"], 1)
        self.assertEqual(v.detail["flags_attached"], 1)

    def test_CONTROL_a_flag_box_of_ANOTHER_stem_does_not_attach(self):
        """A flag box standing two spaces to the side hangs from some other stem."""
        log = Log()
        g = _reach_head(log, side="down", with_flag="flag8thDown", flag_x=98 + 2 * SPACE)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beam_levels"], 0)
        self.assertEqual(v.detail["flags_attached"], 0)

    def test_CONTROL_a_flag_box_far_from_the_tip_does_not_attach(self):
        """A flag box standing mid-stem (its far edge a space and a half short of the tip) is not at the tip."""
        log = Log()
        g = _reach_head(log, side="down", with_flag=None)
        _flag(log, gi=50, cls="flag8thDown", x=98, y=106 + 0.5 * SPACE, w=12, h=1.5 * SPACE)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beam_levels"], 0)

    def test_CONTROL_a_flag_of_the_OPPOSITE_direction_does_not_attach(self):
        """The ruler says the stem points down; a flag the detector calls an UP flag is not this stem's."""
        log = Log()
        g = _reach_head(log, side="down", with_flag="flag8thUp")
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.value["beam_levels"], 0)
        self.assertEqual(v.detail["flags_attached"], 0)

    def test_CONTROL_with_no_ruler_row_nothing_attaches(self):
        """No stem read at all (not a CV stem, not the ruler): there is no tip to hang a flag from, and the flag box is not
        guessed onto the head. (Chord mates and stemless heads are another item: FINDINGS 2.83.)"""
        log = Log()
        g = _reach_head(log, side="down", with_flag="flag8thDown", reach_row=False)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.detail["flags_attached"], 0)


class TestADisputedTipNarrowsAndNeverDecidesZero(unittest.TestCase):
    """⚠️ ROADMAP 2.83 FIX ROUND (Sean, 2026-10-11: tiles 4 and 8 were EIGHTHS the base counted; v5 decided a quarter). CLAUDE.md rule 8: the
    new tip reader may ADD a witness, never REMOVE one. Where it positively reads nothing hanging from the tip but the 2.18c window (and
    the hook counter under it) reads a hook, the two witnesses DISAGREE: the head is NARROWED between its own level 0 and the hook's
    level, with no ordering claim -- never decided 0, and never decided as the hook."""

    def _up_head_alone(self, log, *, hollow=False, box_h=16, beam="decoy"):
        _staff_space(log)
        if beam == "ran_empty":                       # a BEAMLESS cell: the CV beam reader ran and accepted nothing
            log.abstain(CELL, Q.BEAM_STROKE, reader=READERS.CV_LINES, frame="cell:0", reason=ABSTAIN.NO_LINE_ACCEPTED)
        else:
            _beam(log, y=2, x0=400, x1=460)           # a decoy beam far away: the beam reader READ the cell
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, box_h), reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        s = _stem(log, x=135, y=38, h=60)
        if hollow:
            _notehead_ink(log, g, center=0.1, ring=0.6)
        return g, s

    def test_a_DISPUTED_tip_narrows_level_0_and_the_counted_level_RED(self):
        log = Log()
        g, s = self._up_head_alone(log)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True, tip_disagree=True, witness="disputed",
                      hooks=1, hooks_min=1, hooks_max=1, hooks_reason=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "tip_readers_disagree")
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates), [0.5, 1.0])
        self.assertEqual(len({c.support for c in v.candidates}), 1)        # no ordering claim

    def test_a_DISPUTED_tip_with_an_uncounted_hook_still_names_level_0_and_level_1(self):
        log = Log()
        g, s = self._up_head_alone(log)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True, tip_disagree=True, witness="disputed",
                      hooks=None, hooks_min=1, hooks_max=2, hooks_reason="unresolved")
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates), [0.5, 1.0])

    def test_a_dispute_at_the_WRONG_end_is_not_read(self):
        log = Log()
        g, s = self._up_head_alone(log)
        _stem_tip_ink(log, stem_row_id=s.id, end="bottom", found=True, tip_disagree=True, witness="disputed",
                      hooks=1, hooks_min=1, hooks_max=1, hooks_reason=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)

    def test_CONTROL_the_same_row_WITHOUT_the_dispute_is_a_hook_and_DECIDES_the_counted_level(self):
        log = Log()
        g, s = self._up_head_alone(log)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True, witness="window",
                      hooks=1, hooks_min=1, hooks_max=1, hooks_reason=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "hooks_counted")
        self.assertEqual(v.value["beats"], 0.5)

    def test_CONTROL_a_clean_tip_still_decides_the_head_value(self):
        log = Log()
        g, s = self._up_head_alone(log)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=False)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "head_and_marks")
        self.assertEqual(v.value["beats"], 1.0)

    def test_a_DISPUTED_tip_never_lets_2_70_read_a_bare_stem_under_hollow_ink(self):
        """2.70 needs `nothing on the stem`: a disputed tip is not that. The hollow ink is then 2.23's narrowing, never a decided half."""
        log = Log()
        g, s = self._up_head_alone(log, hollow=True)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=True, tip_disagree=True, witness="disputed",
                      hooks=1, hooks_min=1, hooks_max=1, hooks_reason=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "head_fill_from_ink")

    def test_POSITIVE_CONTROL_the_same_hollow_head_with_a_CLEAN_tip_is_still_decided_half(self):
        """The control that can fail: without the dispute 2.70 fires on this exact head, so the test above is the dispute's doing."""
        log = Log()
        g, s = self._up_head_alone(log, hollow=True)
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=False)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.reason, "hollow_head_bare_stem")
        self.assertEqual(v.value["beats"], 2.0)

    def test_a_hollow_reading_on_a_box_that_is_NOT_one_head_is_never_a_decided_half_RED(self):
        """⚠️ Sean's tile 10 (Litolff pdf 15, a FILLED QUARTER read as a half) and the four blob halves: the detector boxed a cluster 2.4-4.1
        staff spaces tall, the ink windows laid in it read half paper ('hollow'), and 2.70 decided a half over a clean tip. A box that does
        not hold ONE head (taller than `HEAD_BOX_MAX_SPACES`) gives 2.23's narrowing -- the detector's black head is a candidate."""
        log = Log()
        g, s = self._up_head_alone(log, hollow=True, box_h=3 * 16)             # 3.0 staff spaces tall
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=False)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotEqual(v.reason, "hollow_head_bare_stem")
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "head_fill_from_ink")
        self.assertIn(1.0, [c.value["beats"] for c in v.candidates])           # Sean's quarter is inside

    def test_CONTROL_a_hollow_reading_on_a_head_sized_box_is_still_a_decided_half(self):
        """The control that can fail: the same head and ink on a 1.4-space box still decides the half 2.70 exists for."""
        log = Log()
        g, s = self._up_head_alone(log, hollow=True, box_h=int(1.4 * 16))
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=False)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.reason, "hollow_head_bare_stem")
        self.assertEqual(v.value["beats"], 2.0)

    def test_the_box_height_cut_is_the_documented_one(self):
        """1.8 spaces: a 1.7-space box decides, a 1.9-space box does not (the cut is not a hair away from the 1.54 p90 nor the 2.37 wrong box)."""
        for h_spaces, expect_half in ((1.7, True), (1.9, False)):
            log = Log()
            g, s = self._up_head_alone(log, hollow=True, box_h=int(round(h_spaces * 16)))
            _stem_tip_ink(log, stem_row_id=s.id, end="top", found=False)
            adjudicate.run(log)
            v = log.verdict(Q.DURATION, g)
            self.assertEqual(v.reason == "hollow_head_bare_stem", expect_half, (h_spaces, v.reason))

    def test_a_hollow_head_in_a_BEAMLESS_cell_whose_tip_cannot_be_read_is_NARROWED_not_decided_black_RED(self):
        """⚠️ Rule 8, found by the count-page diff (Litolff pdf 3 `glyph/2/0/7/6/1`, a hollow half note): in a cell the beam reader ran in and
        accepted nothing, 2.70 decides the half over a clean tip, and with the tip NOT read clean the head used to fall through to the
        detector's black, DECIDED. Hollow ink on a one-head box now narrows (black, half, whole: the answer inside), as it does in a cell with beams."""
        log = Log()
        g, s = self._up_head_alone(log, hollow=True, beam="ran_empty")
        # no tip row at all: the tip reader could not tell
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "head_fill_from_ink")
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates), [1.0, 2.0, 4.0])

    def test_CONTROL_the_same_beamless_cell_with_a_CLEAN_tip_is_still_decided_half(self):
        log = Log()
        g, s = self._up_head_alone(log, hollow=True, beam="ran_empty")
        _stem_tip_ink(log, stem_row_id=s.id, end="top", found=False)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.reason, "hollow_head_bare_stem")

    def test_CONTROL_a_beamless_cell_hollow_reading_on_a_CLUSTER_box_keeps_the_detectors_black(self):
        """A box 3 spaces tall is not one head: its ink windows say nothing about a head, so the detector's black stands (as in main)."""
        log = Log()
        g, s = self._up_head_alone(log, hollow=True, box_h=3 * 16, beam="ran_empty")
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "head_and_marks")
        self.assertEqual(v.value["beats"], 1.0)

    def test_CONTROL_a_FILLED_head_in_a_beamless_cell_is_still_decided_black(self):
        """No hollow reading, no narrowing: an ordinary quarter in a beamless cell decides as before."""
        log = Log()
        g, s = self._up_head_alone(log, hollow=False, beam="ran_empty")
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)


if __name__ == "__main__":
    unittest.main()
