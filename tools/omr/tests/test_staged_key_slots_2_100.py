"""ROADMAP 2.100 -- only a clef stands before a key signature's accidentals.

Sean, 2026-10-12: *"Eighth note rest would never be found before key
signature flats -- in fact -- only clefs appear before key accidentals in a
bar."*  Found by 2.99: 4 of 30 `rest8th` boxes on Litolff p1-3 are the
signature's third flat, boxed a second time (IoU 0.92-0.99 with the
`keyFlat`), which hid a real missing eighth rest.

⚠️ RUN RED FIRST against `origin/main` 86c1c8c5: every `TestRefused*` test
below fails there with the rest / notehead verdict `value=False, reason="rest"`
/ `"notehead"` -- the box is kept as music. The fixtures use the REAL numbers
of Litolff p1 s0 staff 0 (`glyph/1/0/0/0/6`): cell staff space 89.75, clef box
x 243 w 267, three `keyFlat` boxes, the rest8th identical to the third.

⚠️ EVERY REFUSAL HAS A POSITIVE CONTROL IN THE SAME CLASS (CLAUDE.md §6b):
a real rest8th printed AFTER the signature's last accidental stays a rest; a
C-major header (no accidentals) with a rest after its clef stays a rest; a
lone in-bar accidental far from the clef opens no window.

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import header as H
from tools.omr.staged.adjudicators import key_slots as K
from tools.omr.staged.record import Log, Outcome, Q, READERS

SPACE = 89.75
CLEF = ("clefG", 243, 402, 267, 641)
# three flats, one slot apart (the real boxes: 541 / 650 / 747..)
FLATS = [("keyFlat", 541, 590, 105, 270),
         ("keyFlat", 650, 540, 105, 270),
         ("keyFlat", 747, 585, 102, 239)]
THIRD = FLATS[2]


def _cell0(log, boxes, *, staff=0):
    """One header cell: its staff space and one `Q.GLYPH_BOX` per box, as
    GATHER files them (`log.observe(g, Q.GLYPH_BOX, (cls, x, y, w, h))`)."""
    log.observe(R.cell(1, 0, staff, 0), Q.CELL_STAFF_SPACE, SPACE,
                reader=READERS.GEOMETRY, frame="cell:0")
    out = []
    for gi, box in enumerate(boxes):
        g = R.glyph(1, 0, staff, 0, gi)
        log.observe(g, Q.GLYPH_BOX, tuple(box), reader=READERS.DETECTOR,
                    frame="cell:0", score=0.5, category="x")
        cls = box[0]
        if cls.startswith("rest"):
            log.observe(g, Q.REST, cls, reader=READERS.DETECTOR,
                        frame="cell:0", score=0.5, category="rest")
        if cls.startswith("notehead"):
            log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR,
                        frame="cell:0", score=0.5, category="notehead")
        out.append(g)
    return out


def _run(log):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                               Q.REST_IS_NOT_A_REST))
    return log


class TestRefusedInTheKeySlots(unittest.TestCase):

    def test_a_rest8th_boxed_over_the_third_flat_is_refused(self):
        log = Log()
        g = _cell0(log, [CLEF, *FLATS, ("rest8th", *THIRD[1:])])
        _run(log)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g[4])
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_in_a_key_signature_slot")
        self.assertEqual(len(v.detail["key_slot_members"]), 3)

    def test_a_rest8th_between_two_flat_boxes_is_refused(self):
        """The middle flat boxed ONLY as a rest8th (no `keyFlat` under it):
        it stands between the signature's first and last accidental, inside
        the window although nothing key-shaped is under it."""
        log = Log()
        flats = [FLATS[0], ("keyFlat", 700, 590, 102, 270)]
        g = _cell0(log, [CLEF, *flats, ("rest8th", 620, 585, 102, 239)])
        _run(log)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g[3])
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_in_a_key_signature_slot")

    def test_a_rest_boxed_before_the_first_flat_but_after_the_clef(self):
        """Only a clef stands before the accidentals: a rest between the
        clef's right edge and the first flat is the first flat's ink."""
        log = Log()
        g = _cell0(log, [CLEF, ("rest8th", 520, 585, 102, 239),
                         ("keyFlat", 650, 540, 105, 270)])
        _run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, g[1]).value, True)

    def test_a_notehead_boxed_on_a_flats_bowl_is_refused(self):
        log = Log()
        g = _cell0(log, [CLEF, *FLATS,
                         ("noteheadBlackOnLine", 760, 700, 90, 80)])
        _run(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g[4])
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "notehead_in_a_key_signature_slot")

    def test_it_is_refused_with_the_sharps_too(self):
        log = Log()
        sharps = [("keySharp", 541 + 105 * i, 400, 80, 250) for i in range(3)]
        g = _cell0(log, [CLEF, *sharps, ("rest8th", *sharps[2][1:])])
        _run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, g[4]).value, True)


class TestPositiveControlsStayMusic(unittest.TestCase):

    def test_a_real_rest8th_after_the_last_flat_stays_a_rest(self):
        """⚠️ THE CONTROL THAT CAN FAIL: Litolff p1's REAL eighth rest stands
        1.2 spaces past the third flat (cx 1000+ against a window ending at
        ~880). A rule that refused every rest in cell 0 fails here."""
        log = Log()
        g = _cell0(log, [CLEF, *FLATS, ("rest8th", 960, 585, 102, 239)])
        _run(log)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g[4])
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_a_note_after_the_last_flat_stays_a_note(self):
        log = Log()
        g = _cell0(log, [CLEF, *FLATS,
                         ("noteheadBlackOnLine", 1010, 700, 120, 100)])
        _run(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g[4])
        self.assertIs(v.value, False)

    def test_c_major_no_accidentals_a_rest_after_the_clef_stays(self):
        log = Log()
        g = _cell0(log, [CLEF, ("rest8th", 560, 585, 102, 239)])
        _run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, g[1]).value, False)

    def test_a_lone_in_bar_accidental_far_from_the_clef_opens_no_window(self):
        """C major, a rest after the clef, then a flat before the third note
        (an in-bar accidental, 8 spaces from the clef). It must not stretch
        a window back over the rest."""
        log = Log()
        g = _cell0(log, [CLEF, ("rest8th", 560, 585, 102, 239),
                         ("accidentalFlat", 1300, 600, 105, 270)])
        _run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, g[1]).value, False)

    def test_a_rest_in_a_later_bar_is_not_in_the_header(self):
        """The window is the header's: cell 1 of the same staff, with a
        flat-shaped box in it (a key CHANGE printed at that bar), is not
        cell 0 and this rule does not reach it."""
        log = Log()
        log.observe(R.cell(1, 0, 0, 1), Q.CELL_STAFF_SPACE, SPACE,
                    reader=READERS.GEOMETRY, frame="cell:1")
        a = R.glyph(1, 0, 0, 1, 0)
        b = R.glyph(1, 0, 0, 1, 1)
        for g, box in ((a, ("keyFlat", 100, 590, 105, 270)),
                       (b, ("rest8th", 100, 590, 105, 270))):
            log.observe(g, Q.GLYPH_BOX, box, reader=READERS.DETECTOR,
                        frame="cell:1", score=0.5, category="x")
        log.observe(b, Q.REST, "rest8th", reader=READERS.DETECTOR,
                    frame="cell:1", score=0.5, category="rest")
        _run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, b).value, False)

    def test_a_neighbour_staffs_ink_in_the_padding_is_not_in_the_window(self):
        """Level with the signature only: a rest padded in from the staff
        below stands 3+ spaces under the run."""
        log = Log()
        g = _cell0(log, [CLEF, *FLATS, ("rest8th", 650, 1100, 102, 239)])
        _run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, g[4]).value, False)


class TestOneUnboxedSlotIsBridged(unittest.TestCase):
    """Litolff p1 s0 staff 11: the detector boxed slots 1 and 3 (2.6 spaces
    apart) and the rest8th lies over the third flat's keyFlat."""

    def test_the_rest_over_a_flat_past_one_missing_slot_is_refused(self):
        log = Log()
        g = _cell0(log, [CLEF, ("keyFlat", 526, 660, 97, 244),
                         ("keyFlat", 766, 721, 102, 237),
                         ("rest8th", 766, 721, 103, 234)])
        _run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, g[3]).value, True)

    def test_two_missing_slots_are_not_bridged(self):
        """Control: a KEY-class box 3.5 spaces on is not this run's."""
        log = Log()
        g = _cell0(log, [CLEF, ("keyFlat", 526, 660, 97, 244),
                         ("keyFlat", 850, 721, 102, 237),
                         ("rest8th", 850, 721, 103, 234)])
        _run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, g[3]).value, False)

    def test_an_in_bar_accidental_class_box_is_not_bridged_to(self):
        """Control: a real rest between the key's flat and a later in-bar
        accidental (class accidentalFlat) stays a rest."""
        log = Log()
        g = _cell0(log, [CLEF, ("keyFlat", 526, 660, 97, 244),
                         ("rest8th", 680, 721, 103, 234),
                         ("accidentalFlat", 766, 721, 102, 237)])
        _run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, g[2]).value, False)


class TestTheNextSlotForARest(unittest.TestCase):
    """Litolff p1 s0 staff 10: two boxed flats and the third flat boxed ONLY
    as a rest8th, standing exactly where the next slot would."""

    def test_a_rest_on_the_next_slot_is_the_next_accidental(self):
        log = Log()
        g = _cell0(log, [CLEF, FLATS[0], FLATS[1],
                         ("rest8th", 747, 585, 102, 239)])
        _run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, g[3]).value, True)

    def test_a_rest_a_slot_and_a_half_on_is_music(self):
        """Control: 0.4 spaces off the next slot (the nearest real rest the
        count pages hold) stays a rest."""
        log = Log()
        g = _cell0(log, [CLEF, FLATS[0], FLATS[1],
                         ("rest8th", 790, 585, 102, 239)])
        _run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, g[3]).value, False)

    def test_a_notehead_on_the_next_slot_is_not_refused(self):
        """Control: the rule is for rest classes only (a whole note stands
        0.4 spaces off the next slot in Brahms and is music)."""
        log = Log()
        g = _cell0(log, [CLEF, FLATS[0], FLATS[1],
                         ("noteheadBlackOnLine", 747, 650, 110, 100)])
        _run(log)
        self.assertIs(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g[3]).value,
                      False)

    def test_a_single_flat_has_no_measurable_pitch(self):
        log = Log()
        g = _cell0(log, [CLEF, FLATS[0], ("rest8th", 650, 585, 102, 239)])
        _run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, g[2]).value, False)


class TestTheKeyIsStillRead(unittest.TestCase):

    def test_three_flats_are_still_three_flats_with_the_rest_box_refused(self):
        """The refusal removes a rest; it does not touch the key reader, and
        the markers still read -3 (`header._marker_run`)."""
        log = Log()
        sub = R.staff(1, 0, 0)
        log.observe(sub, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        _cell0(log, [CLEF, *FLATS, ("rest8th", *THIRD[1:])])
        for _kind, x, y, w, h in FLATS:
            log.observe(sub, Q.KEYSIG_MARKER, "keyFlat",
                        reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                        x=x, y_center=y + h / 2)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, sub)
        self.assertEqual(v.value, -3)


class TestTheWindowItself(unittest.TestCase):

    def test_the_constants_equal_the_key_readers_own(self):
        self.assertEqual(K.RUN_GAP_SPACES, H.MARKER_RUN_GAP_SPACES)
        self.assertEqual(K.SLOT_TOLERANCE_SPACES,
                         H.MARKER_SLOT_TOLERANCE_SPACES)
        self.assertEqual(K.MAX_SLOTS, H.MAX_FIFTHS)

    def test_more_than_seven_slots_is_not_a_signature(self):
        boxes = [K.KeyBox(f"r{i}", "keyFlat", 500 + i * 100, 500, 90, 250)
                 for i in range(9)]
        self.assertIsNone(K.key_slot_window(boxes, SPACE))

    def test_no_scale_no_window(self):
        boxes = [K.KeyBox("r0", "keyFlat", 500, 500, 90, 250)]
        self.assertIsNone(K.key_slot_window(boxes, 0.0))


if __name__ == "__main__":
    unittest.main()
