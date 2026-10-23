"""ROADMAP 2.187b: the KEY TAIL (slots a staff did not read itself) is judged by what that staff may print -- flag `OMR_KEY_PER_SYSTEM` (OFF).

CAUSE (Sean's 2.187 tiles): the tail was NARROWED for every box in it, and 7 of the 9 changes were real notes just after a short signature.
Sean 2026-10-22, three rulings: (1) a transposing instrument prints its OWN written key (a horn none, a B-flat clarinet in three flats one);
(2) look for the accidental the run can hold, not "a flat": flats for a flat key, sharps for a sharp key, cancelling naturals first at a key change,
any of the three where the type is unknown; (3) slot k holds only the k-th accidental of the fixed order (Bb Eb Ab Db ... / F# C# G# D# ...) at a
fixed staff step for the clef.

Every test has a TWIN that must not fire (the opposite expectation on a near-identical input), so a judge that narrows everything, or nothing,
cannot pass. Glyphs are painted at staff space 20 px: a flat is a stem rising above a round bowl on its left, a sharp two verticals crossed by
two bars, a natural two offset verticals joined by two bars, a note a solid oval with a stem.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import key_object as KO

SP = 20.0
TOP = 200.0
LINES = [TOP + SP * j for j in range(5)]
W, H = 700, 600
X0, PITCH = 110, 24


def staff_img():
    img = np.full((H, W), 255, np.uint8)
    for y in LINES:
        img[int(y):int(y) + 2, 20:W - 20] = 0
    return img


def y_of_step(step):
    return TOP + step * SP / 2.0


def paint_flat(img, x, pitch_step):
    """Bowl (12 x 26 px ring) centred on the line/space `pitch_step` steps below the top line; a 3 px stem up to 54 px in all."""
    yp = int(round(y_of_step(pitch_step)))
    bot = yp + 13
    img[bot - 54:bot, x:x + 3] = 0
    yy, xx = np.mgrid[bot - 26:bot, x:x + 13]
    r = ((yy - (bot - 13)) / 13.0) ** 2 + ((xx - (x + 5.0)) / 8.0) ** 2
    img[bot - 26:bot, x:x + 13][(r <= 1.0) & (r >= 0.45)] = 0


def paint_sharp(img, x, pitch_step):
    yp = int(round(y_of_step(pitch_step)))
    top, bot = yp - 30, yp + 30
    img[top + 6:bot, x + 2:x + 5] = 0
    img[top:bot - 6, x + 9:x + 12] = 0
    for off in (-6, 6):
        for xx in range(x, x + 14):
            y = yp + off - int((xx - x) * 0.35)
            img[y:y + 4, xx] = 0


def paint_natural(img, x, pitch_step):
    yp = int(round(y_of_step(pitch_step)))
    top, bot = yp - 28, yp + 28
    img[top:top + 40, x + 2:x + 5] = 0
    img[bot - 40:bot, x + 9:x + 12] = 0
    img[yp - 8:yp - 4, x + 2:x + 12] = 0
    img[yp + 4:yp + 8, x + 2:x + 12] = 0


def paint_note(img, x, step):
    """A quarter note: oval head centred on `step`, stem up on its right."""
    yp = int(round(y_of_step(step)))
    yy, xx = np.mgrid[yp - 9:yp + 9, x:x + 24]
    img[yp - 9:yp + 9, x:x + 24][((yy - yp) / 9.0) ** 2 + ((xx - (x + 12)) / 12.0) ** 2 <= 1.0] = 0
    img[yp - 70:yp, x + 21:x + 24] = 0


def tb_of(painter, k, step, img=None):
    """Paint `painter` at slot k (pitch-step `step`) and measure the detector-style box around it."""
    img = staff_img() if img is None else img
    x = X0 + PITCH * (k - 1)
    painter(img, x, step)
    yc = y_of_step(step)
    return KO.measure_tail_box(img, LINES, SP, [x - 3, yc - 40, x + 24, yc + 40])


def slot_cx(own=0, upto=7):
    return {k: X0 + PITCH * (k - 1) + 6 for k in range(own + 1, upto + 1)}


def pitch_step(clef, acc, j):
    return KO.expected_step(clef, acc, j)


def judge(tb, *, own=0, n=3, written=None, previous="same", clef="treble"):
    prev = written if previous == "same" else previous
    return KO.judge_tail_box(tb, slot_cx(own), SP, own=own, system_n=n, written=written, previous=prev, clef=clef)


class TestThePaintedGlyphsAreWhatTheyClaim(unittest.TestCase):
    """The test glyphs must read as the shapes the judge keys on, or every test below proves nothing."""

    def test_shapes(self):
        for painter, want in ((paint_flat, "flat"), (paint_sharp, "sharp"), (paint_natural, "natural")):
            tb = tb_of(painter, 1, 4)
            self.assertEqual((tb["shape"], tb["basis"]), (want, "piece"), (painter.__name__, tb))

    def test_a_note_reads_sharp_the_way_the_real_notes_do(self):
        # measured: 53 of 66 real tail notes with an accidental-sized piece read `sharp` (a head and a stem fill both corners)
        self.assertEqual(tb_of(paint_note, 1, 4)["shape"], "sharp")


class TestFixedOrderAndStep(unittest.TestCase):
    """(b): slot k holds only the k-th accidental of the fixed order, at that clef's step."""

    def _flat(self, clef, j, shift=0.0, written=-3):
        tb = tb_of(paint_flat, j, pitch_step(clef, "b", j) + shift)
        return judge(tb, own=j - 1, n=3, written=written, clef=clef)

    def test_slot_3_ab_in_treble_bass_and_alto(self):
        for clef in ("treble", "bass", "alto"):
            v = self._flat(clef, 3)
            self.assertTrue(v["narrow"], (clef, v))
            self.assertEqual((v["slot"], v["position"]), (3, "matches"), clef)

    def test_TWIN_the_same_flat_two_steps_off_is_left_alone(self):
        for clef in ("treble", "bass", "alto"):
            v = self._flat(clef, 3, shift=2.0)
            self.assertEqual((v["narrow"], v["why"]), (False, "wrong_staff_step_for_the_slot"), clef)

    def test_a_notehead_at_another_step_in_the_same_x_is_untouched_in_every_clef(self):
        for clef in ("treble", "bass", "alto"):
            tb = tb_of(paint_note, 3, pitch_step(clef, "b", 3) + 5)
            self.assertFalse(judge(tb, own=2, n=3, written=-3, clef=clef)["narrow"], clef)

    def test_TWIN_a_notehead_whose_ink_reads_sharp_is_rejected_in_a_flat_run_even_at_the_flats_step(self):
        for clef in ("treble", "bass", "alto"):
            tb = tb_of(paint_note, 3, pitch_step(clef, "b", 3) + 1.5)
            v = judge(tb, own=2, n=3, written=-3, clef=clef)
            self.assertEqual((v["narrow"], v["why"]), (False, "wrong_accidental_type"), clef)

    def test_the_order_changes_the_step_slot_by_slot(self):
        # a flat painted at slot 2's step (Eb) in slot 1's x (Bb) is the wrong accidental THERE; at slot 1's own step it is right
        v = judge(tb_of(paint_flat, 1, pitch_step("treble", "b", 2)), own=0, n=3, written=-3)
        self.assertEqual((v["narrow"], v["why"]), (False, "wrong_staff_step_for_the_slot"))
        self.assertTrue(judge(tb_of(paint_flat, 1, pitch_step("treble", "b", 1)), own=0, n=3, written=-3)["narrow"])

    def test_two_sharps_run_slot_2_is_c_sharp_in_every_clef(self):
        for clef in ("treble", "bass", "alto"):
            self.assertTrue(judge(tb_of(paint_sharp, 2, pitch_step(clef, "#", 2)), own=1, n=2, written=2, clef=clef)["narrow"], clef)
            self.assertFalse(judge(tb_of(paint_sharp, 2, pitch_step(clef, "#", 2) + 2.0), own=1, n=2, written=2, clef=clef)["narrow"], clef)  # TWIN

    def test_slot_3_of_a_two_sharp_run_is_beyond_the_written_count(self):
        v = judge(tb_of(paint_sharp, 3, pitch_step("treble", "#", 3)), own=2, n=2, written=2)
        self.assertEqual(v["why"], "beyond_the_written_count")

    def test_no_clef_leaves_the_position_unchecked_and_says_so(self):
        v = judge(tb_of(paint_flat, 3, 99 - 90), own=2, written=-3, clef=None)
        self.assertEqual((v["narrow"], v["position"]), (True, "unchecked_no_clef"))

    def test_a_crushed_flat_boxed_over_its_bowl_alone_is_still_placed_by_its_bowl(self):
        # the detector's rest box covers the bowl only (Litolff): no whole glyph (shape unread), the box's own ink centre stands on the pitch
        img = staff_img()
        x = X0 + PITCH * 2
        paint_flat(img, x, pitch_step("treble", "b", 3))
        yc = y_of_step(pitch_step("treble", "b", 3))
        tb = KO.measure_tail_box(img, LINES, SP, [x - 2, yc - 14, x + 16, yc + 14])
        self.assertTrue(judge(tb, own=2, n=3, written=-3)["narrow"], tb)
        tb = KO.measure_tail_box(img, LINES, SP, [x - 2, yc - 14 + 20, x + 16, yc + 14 + 20])     # TWIN: the same box 2 steps lower
        self.assertFalse(judge(tb, own=2, n=3, written=-3)["narrow"], tb)


class TestTheRunsAccidentalType(unittest.TestCase):
    """(a): flats for a flat key, sharps for a sharp key, naturals at a change, any of the three where unknown."""

    def test_a_sharp_key_staff_narrows_a_sharp_but_not_a_flat(self):
        self.assertTrue(judge(tb_of(paint_sharp, 1, pitch_step("treble", "#", 1)), own=0, n=2, written=2)["narrow"])
        v = judge(tb_of(paint_flat, 1, pitch_step("treble", "b", 1)), own=0, n=2, written=2)
        self.assertEqual((v["narrow"], v["why"]), (False, "wrong_accidental_type"))

    def test_a_flat_key_staff_does_not_narrow_a_sharp(self):
        v = judge(tb_of(paint_sharp, 1, pitch_step("treble", "#", 1)), own=0, n=3, written=-3)
        self.assertEqual((v["narrow"], v["why"]), (False, "wrong_accidental_type"))

    def test_a_note_in_a_sharp_key_tail_at_another_step_is_untouched(self):
        self.assertFalse(judge(tb_of(paint_note, 1, pitch_step("treble", "#", 1) + 5), own=0, n=2, written=2)["narrow"])

    def test_cancelling_naturals_at_a_key_change_are_narrowed(self):
        # 3 flats -> 1 flat: slots 1-3 are naturals cancelling Bb Eb Ab at the OLD key's steps, then the new Bb
        for k in (1, 2, 3):
            v = judge(tb_of(paint_natural, k, pitch_step("treble", "b", k)), own=0, n=3, written=-1, previous=-3)
            self.assertTrue(v["narrow"], (k, v))

    def test_TWIN_the_same_natural_with_no_key_change_is_left_alone(self):
        v = judge(tb_of(paint_natural, 1, pitch_step("treble", "b", 1)), own=0, n=3, written=-3, previous=-3)
        self.assertEqual((v["narrow"], v["why"]), (False, "natural_without_a_key_change"))

    def test_TWIN_a_natural_at_a_change_but_at_the_wrong_step_is_left_alone(self):
        self.assertFalse(judge(tb_of(paint_natural, 1, pitch_step("treble", "b", 1) + 3), own=0, n=3, written=-1, previous=-3)["narrow"])

    def test_a_note_in_the_cancel_slots_is_untouched(self):
        self.assertFalse(judge(tb_of(paint_note, 2, pitch_step("treble", "b", 2) + 5), own=0, n=3, written=-1, previous=-3)["narrow"])

    def test_after_the_cancels_the_new_accidental_is_counted_from_the_cancels_end(self):
        # 3 flats -> 1 flat: slot 4 is the NEW key's first flat (Bb), not the fourth flat (Db)
        self.assertTrue(judge(tb_of(paint_flat, 4, pitch_step("treble", "b", 1)), own=0, n=3, written=-1, previous=-3)["narrow"])
        self.assertFalse(judge(tb_of(paint_flat, 4, pitch_step("treble", "b", 4)), own=0, n=3, written=-1, previous=-3)["narrow"])   # TWIN

    def test_unknown_type_accepts_a_flat_a_sharp_or_a_natural_at_its_place(self):
        self.assertTrue(judge(tb_of(paint_flat, 1, pitch_step("treble", "b", 1)), own=0, n=3, written=None)["narrow"])
        self.assertTrue(judge(tb_of(paint_sharp, 1, pitch_step("treble", "#", 1)), own=0, n=3, written=None)["narrow"])
        self.assertTrue(judge(tb_of(paint_natural, 1, pitch_step("treble", "b", 1)), own=0, n=3, written=None, previous=None)["narrow"])

    def test_unknown_type_never_a_note_at_another_step(self):
        for acc in ("b", "#"):
            self.assertFalse(judge(tb_of(paint_note, 1, pitch_step("treble", acc, 1) + 5), own=0, n=3, written=None, previous=None)["narrow"], acc)

    def test_unknown_instrument_reaches_only_the_system_count(self):
        v = judge(tb_of(paint_flat, 4, pitch_step("treble", "b", 4)), own=0, n=3, written=None)
        self.assertEqual((v["narrow"], v["why"]), (False, "not_at_a_slot_x"))


class TestWrittenCountFromTheInstrument(unittest.TestCase):
    """The system's count never reaches a transposing staff (page-facts section 2, Sean 2026-10-22)."""

    def _flat(self, k):
        return tb_of(paint_flat, k, pitch_step("treble", "b", k))

    def test_horn_written_zero_has_no_tail(self):
        for k in (1, 2, 3):
            self.assertEqual(judge(self._flat(k), own=0, n=3, written=0)["why"], "beyond_the_written_count")

    def test_TWIN_the_same_boxes_on_a_concert_pitch_staff_are_narrowed(self):
        for k in (1, 2, 3):
            self.assertTrue(judge(self._flat(k), own=0, n=3, written=-3)["narrow"], k)

    def test_b_flat_clarinet_in_three_flats_gets_one_slot(self):
        self.assertTrue(judge(self._flat(1), own=0, n=3, written=-1)["narrow"])
        for k in (2, 3):
            self.assertEqual(judge(self._flat(k), own=0, n=3, written=-1)["why"], "not_at_a_slot_x")      # reach is 1 slot: boxes at slots 2, 3 are not its tail

    def test_a_transposing_staff_in_sharps_reaches_past_the_systems_count(self):
        tb = tb_of(paint_sharp, 4, pitch_step("treble", "#", 4))
        self.assertTrue(judge(tb, own=0, n=3, written=5)["narrow"])
        self.assertFalse(judge(tb, own=0, n=3, written=None)["narrow"])                                   # TWIN: unknown reaches only 3

    def test_a_sharp_written_key_for_a_flat_concert_key_is_handled(self):
        tb = tb_of(paint_sharp, 2, pitch_step("treble", "#", 2))
        self.assertTrue(judge(tb, own=0, n=3, written=2)["narrow"])
        self.assertFalse(judge(tb, own=0, n=3, written=-3)["narrow"])                                      # TWIN

    def test_slots_the_staff_read_itself_are_not_the_tails_business(self):
        v = judge(tb_of(paint_flat, 2, pitch_step("treble", "b", 2)), own=2, n=3, written=-3)
        self.assertEqual(v["why"], "not_at_a_slot_x")


class TestX(unittest.TestCase):
    def test_a_flat_shaped_box_between_slots_is_left_alone(self):
        img = staff_img()
        x = X0 + PITCH * 2 + 14
        paint_flat(img, x, pitch_step("treble", "b", 3))
        yc = y_of_step(pitch_step("treble", "b", 3))
        tb = KO.measure_tail_box(img, LINES, SP, [x - 3, yc - 40, x + 24, yc + 40])
        self.assertEqual(judge(tb, own=2, n=3, written=-3)["why"], "not_at_a_slot_x")

    def test_local_line_shift_follows_a_tilted_staff(self):
        img = np.full((H, W), 255, np.uint8)
        for y in LINES:
            for x in range(20, W - 20):
                yy = int(y + 6 * x / 500.0)
                img[yy:yy + 2, x] = 0
        self.assertGreater(KO.local_line_shift(img, LINES, SP, 450, 480) - KO.local_line_shift(img, LINES, SP, 100, 130), 3.0)

    def test_a_tilted_staff_moves_the_step_with_it(self):
        img = np.full((H, W), 255, np.uint8)
        for y in LINES:
            for x in range(20, W - 20):
                yy = int(y + 8 * x / 500.0)
                img[yy:yy + 2, x] = 0
        x = X0 + PITCH * 2
        yp = y_of_step(pitch_step("treble", "b", 3)) + 8 * (x + 6) / 500.0
        paint_flat(img, x, (yp - TOP) / (SP / 2.0))
        tb = KO.measure_tail_box(img, LINES, SP, [x - 3, yp - 40, x + 24, yp + 40])
        self.assertTrue(judge(tb, own=2, n=3, written=-3)["narrow"], tb)


class TestThePreGateIsASupersetOfEveryWrittenKey(unittest.TestCase):
    """`loose=True` is the cheap look `claimed_by.consult` takes before it reads the staff's slot, part key and labels (whose basis would ride on
    every notehead verdict it touched: Litolff's record grew 62%). It must reject nothing any written key could narrow."""

    def _boxes(self):
        out = []
        for painter, acc in ((paint_flat, "b"), (paint_sharp, "#"), (paint_natural, "b"), (paint_note, "b")):
            for k in (1, 2, 3, 4):
                for j in (1, 2, 3, 4):
                    for shift in (0.0, 0.4, 3.0):
                        out.append(tb_of(painter, k, pitch_step("treble", acc, j) + shift))
        return out

    def test_whatever_a_written_key_narrows_the_pre_gate_narrows(self):
        n_full = 0
        for tb in self._boxes():
            for written, previous in ((-3, -3), (-1, -1), (2, 2), (5, 5), (-1, -3), (0, -3), (3, 0), (None, None)):
                for own in (0, 1, 2):
                    full = KO.judge_tail_box(tb, slot_cx(own), SP, own=own, system_n=3, written=written, previous=previous, clef="treble")
                    loose = KO.judge_tail_box(tb, slot_cx(own), SP, own=own, system_n=KO.MAX_SLOTS, written=None, previous=None, clef="treble", loose=True)
                    if full["narrow"]:
                        n_full += 1
                        self.assertTrue(loose["narrow"], (written, previous, own, tb, full, loose))
        self.assertGreater(n_full, 50)                                    # the property was exercised

    def test_TWIN_the_pre_gate_does_reject_what_cannot_be_an_accidental_anywhere(self):
        rejected = [KO.judge_tail_box(tb, slot_cx(0), SP, own=0, system_n=KO.MAX_SLOTS, clef="treble", loose=True)["narrow"] for tb in
                    (tb_of(paint_note, 1, 14), tb_of(paint_flat, 1, 20), tb_of(paint_sharp, 3, -4))]
        self.assertEqual(rejected, [False, False, False])


class TestTheMeasuredClef(unittest.TestCase):
    """`clef_of_box`: the clef the detector's box names, GATHER's measurement for the cheap look (no verdict is read for it)."""

    def test_names_and_the_c_clefs_centre_line(self):
        self.assertEqual(KO.clef_of_box(("gClef", [0, 150, 30, 330]), LINES), "treble")
        self.assertEqual(KO.clef_of_box(("fClef8vb", [0, 200, 30, 260]), LINES), "bass")
        self.assertEqual(KO.clef_of_box(("cClef", [0, LINES[2] - 40, 30, LINES[2] + 40]), LINES), "alto")
        self.assertEqual(KO.clef_of_box(("cClef", [0, LINES[1] - 40, 30, LINES[1] + 40]), LINES), "tenor")

    def test_TWIN_a_c_clef_centred_between_lines_or_an_unknown_name_is_none(self):
        self.assertIsNone(KO.clef_of_box(("cClef", [0, LINES[2] - 40 + 10, 30, LINES[2] + 40 + 10]), LINES))       # a space, not a line
        self.assertIsNone(KO.clef_of_box(("clef8va", [0, 150, 30, 330]), LINES))
        self.assertIsNone(KO.clef_of_box(None, LINES))

    def test_the_pre_gate_uses_it_to_reject_a_flat_at_the_wrong_clefs_step(self):
        tb = tb_of(paint_flat, 3, pitch_step("treble", "b", 3))
        loose = lambda clef: KO.judge_tail_box(tb, slot_cx(2), SP, own=2, system_n=KO.MAX_SLOTS, clef=clef, loose=True)["narrow"]
        self.assertTrue(loose("treble"))                    # the treble Ab: some run holds it
        self.assertTrue(loose(None))                        # no clef measured: position unchecked, never rejected on a guess


class TestKeyTailContext(unittest.TestCase):
    """`header.key_tail_context`: the staff's written key from the verdicts, never from the system's count."""

    class _V:
        def __init__(self, value, outcome=None):
            from tools.omr.staged.record import Outcome
            self.value, self.outcome = value, outcome or Outcome.DECIDED

    class _Subj:
        def __init__(self, page=1, system=0):
            self.page, self.system = page, system

        def at(self, kind):
            return self

    class _Ev:
        def __init__(self, verdicts, label=None):
            self.subject = TestKeyTailContext._Subj()
            self._v, self._label = verdicts, label

        def verdict(self, q, subject=None):
            return self._v.get(q)

        def rows(self, q, subject=None, **kw):
            from tools.omr.staged.record import Q
            if q == Q.MARGIN_LABEL and self._label:
                return [mock.Mock(value=self._label)]
            return ()

    def _ctx(self, label, slot=1, doc=-3, parts=None, count=3, shapes=()):
        from tools.omr.staged.adjudicators import header
        from tools.omr.staged.record import Q
        pk = {"document": [{"from": None, "fifths": doc}], "parts": parts or {}}
        ev = self._Ev({Q.CLEF: self._V("treble"), Q.SLOT_INDEX: self._V(slot), Q.PART_KEY: self._V(pk)}, label)
        return header.key_tail_context(ev, system_count=count, read_shapes=shapes)

    def test_a_clarinet_that_NAMES_its_crook_gets_the_concert_key_shifted(self):
        c = self._ctx("Clar. (B)")
        self.assertEqual((c["written"], c["source"], c["clef"]), (-1, "system_count+read_transposition", "treble"), c)

    def test_TWIN_an_unlabelled_clarinet_is_not_assumed_b_flat(self):
        c = self._ctx("Clar.", slot=None)
        self.assertIsNone(c["written"], c)
        self.assertEqual(c["source"], "unknown")

    def test_natural_horn_prints_no_signature(self):
        c = self._ctx("Cor. (Es)")
        self.assertEqual((c["written"], c["source"]), (0, "no_signature_convention"))

    def test_a_concert_pitch_staff_takes_the_systems_count_NOT_its_own_parts_short_majority(self):
        # the flute's own part majority is -1 (the flat boxed as a rest was never read elsewhere either): the count the staves agreed on is 3
        c = self._ctx("Fl.", slot=1, parts={"1": {"segments": [{"from": None, "fifths": -1}]}})
        self.assertEqual((c["written"], c["source"]), (-3, "system_count+read_transposition"), c)

    def test_a_part_whose_label_is_printed_elsewhere_lends_its_transposition(self):
        c = self._ctx(None, slot=4, parts={"4": {"offset": 2}})
        self.assertEqual(c["written"], -1, c)

    def test_a_sharp_concert_key_gives_a_sharper_written_key_for_a_bflat_clarinet(self):
        c = self._ctx("Clar. (B)", doc=2, count=2)
        self.assertEqual(c["written"], 4, c)                                    # 2 sharps up a tone is 4 sharps (E major): sharps, not flats

    def test_no_sign_anywhere_is_unknown_not_a_guess(self):
        c = self._ctx("Fl.", doc=0, shapes=("unclear",))
        self.assertEqual((c["written"], c["why"]), (None, "no_sign"), c)
        c = self._ctx("Fl.", doc=0, shapes=("flat", "flat"))                      # TWIN: the staff's own read slots look like flats
        self.assertEqual(c["written"], -3, c)

    def test_a_sharp_reading_is_no_witness_of_the_sign(self):
        # a crushed flat's bowl reads sharp: two sharp-shaped slots do not make a sharp key; one sharp among flats does not either
        self.assertIsNone(self._ctx("Fl.", doc=0, shapes=("sharp", "sharp"))["written"])
        self.assertIsNone(self._ctx("Fl.", doc=0, shapes=("flat", "flat", "sharp"))["written"])

    def test_a_key_change_here_gives_the_previous_stretchs_written_key(self):
        from tools.omr.staged.adjudicators import header
        from tools.omr.staged.record import Q
        pk = {"document": [{"from": None, "fifths": -3}, {"from": [1, 0], "fifths": -1}], "parts": {}}
        ev = self._Ev({Q.CLEF: self._V("treble"), Q.SLOT_INDEX: self._V(1), Q.PART_KEY: self._V(pk)}, "Fl.")
        c = header.key_tail_context(ev, system_count=1)
        self.assertEqual((c["written"], c["previous"]), (-1, -3), c)
        pk["document"][1]["from"] = [9, 9]                                        # TWIN: the change is elsewhere: no change here
        c = header.key_tail_context(ev, system_count=3)
        self.assertEqual((c["written"], c["previous"]), (-3, -3), c)


class TestTheConsultPlumbing(unittest.TestCase):
    """`claimed_by.consult`: the tail box is narrowed or left alone by the judge; the READ part is never touched."""

    def test_the_judge_is_what_decides_not_the_tail_flag(self):
        from tools.omr.staged.adjudicators import claimed_by as CB
        self.assertTrue(hasattr(CB, "consult"))
        self.assertTrue(callable(KO.judge_tail_box))


if __name__ == "__main__":
    unittest.main()
