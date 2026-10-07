"""ROADMAP 2.59 -- a dot is never a notehead, and a dot belongs to the note
immediately to its LEFT (Sean, 2026-10-07, on the Brahms "worse" sheet).

Tile 4 (`brahms 7/1/0/9/9`): an augmentation dot boxed as a notehead was given
to the Flute staff -- it belongs to the Oboe, whose note it trails. Tiles 11
and 12 (`18/1/12/6/18`, `5/0/1/5/32`): the dotted note belongs to the staff
BELOW, and the dot, filed in the strip above, could not find its note
(`owned_by_another_staff`) so the reading went from "lengthens" to "cannot
tell".

`OMR_DOT_FOLLOWS_NOTE` (default OFF, allow-list) switches all three rules.
Every refusal here has its positive control in the same class, and every new
rule is shown RED with the flag off.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

FLAG = {"OMR_DOT_FOLLOWS_NOTE": "1"}
CELL = R.cell(0, 0, 0, 0)
HOME = R.staff(0, 0, 0)
BELOW = R.staff(0, 0, 1)
X = 100
SPACE = 16


def _log():
    log = Log()
    log.observe(CELL, Q.CELL_STAFF_SPACE, float(SPACE),
                reader=READERS.GEOMETRY, frame="cell:0")
    return log


def _note(log, gi, head="noteheadHalf", x=X, w=20, h=16, cell=0, y=0):
    g = R.glyph(0, 0, cell, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, head, reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (head, x - 10, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    return g


def _dot(log, gi, x, y=4, w=8, h=8, page_box=None):
    d = R.glyph(0, 0, 0, 0, gi)
    extra = {"bbox_page_px": list(page_box)} if page_box else {}
    log.observe(d, Q.GLYPH_BOX, ("augmentationDot", x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.8, **extra)
    log.observe(d, Q.AUG_DOT, (x + w / 2.0, y + h / 2.0),
                reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                detector_role="dot", detector_class="augmentationDot")
    return d


def _contest(log, glyph, winner, loser):
    """A real two-staff contest `glyph_owner` DECIDES for `winner`."""
    log.observe(glyph, Q.GLYPH_BAND_DISTANCE, 4.0, reader=READERS.GEOMETRY,
                frame="page", candidate=loser.to_key(),
                own=(loser == HOME), position_in_candidate=2.0)
    log.observe(glyph, Q.GLYPH_BAND_DISTANCE, 1.0, reader=READERS.GEOMETRY,
                frame="page", candidate=winner.to_key(),
                own=(winner == HOME), position_in_candidate=2.0)


class TestDotSizedBoxIsNotAHead(unittest.TestCase):
    def _verdict(self, head, w, h, flag):
        log = _log()
        g = _note(log, 0, head, w=w, h=h)
        with mock.patch.dict(os.environ, FLAG if flag else {}, clear=False):
            if not flag:
                os.environ.pop("OMR_DOT_FOLLOWS_NOTE", None)
            adjudicate.run(log)
        return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)

    def test_RED_a_hollow_box_of_dot_size_is_refused_as_a_dot(self):
        v = self._verdict("noteheadHalf", 8, 8, flag=True)    # 0.5 sp round
        self.assertEqual((v.value, v.reason), (True, "is_a_dot"))

    def test_the_same_box_is_untouched_with_the_flag_off(self):
        v = self._verdict("noteheadHalf", 8, 8, flag=False)
        self.assertEqual(v.value, False)

    def test_POSITIVE_CONTROL_a_real_hollow_head_is_never_refused(self):
        v = self._verdict("noteheadHalf", 21, 16, flag=True)  # 1.3 x 1.0 sp
        self.assertEqual((v.value, v.reason), (False, "notehead"))

    def test_POSITIVE_CONTROL_a_short_but_wide_head_is_not_a_dot(self):
        """Both sides must be small: a head 1.3 sp wide but only 0.5 tall is
        some other problem, not a dot."""
        v = self._verdict("noteheadHalf", 21, 8, flag=True)
        self.assertEqual(v.value, False)

    def test_the_boundary_is_stated_in_spaces(self):
        v_in = self._verdict("noteheadHalf", 12, 12, flag=True)   # 0.75 sp
        v_out = self._verdict("noteheadHalf", 13, 13, flag=True)  # 0.81 sp
        self.assertEqual(v_in.value, True)
        self.assertEqual(v_out.value, False)


class TestADotBelongsToTheNoteToItsLeft(unittest.TestCase):
    def _run(self, flag):
        log = _log()
        head = _note(log, 0, "noteheadHalf", x=X)
        _contest(log, head, winner=BELOW, loser=HOME)     # the note is BELOW's
        dot = _dot(log, 1, x=X + 12)
        _contest(log, dot, winner=HOME, loser=BELOW)      # the strip says HOME
        env = dict(FLAG) if flag else {}
        with mock.patch.dict(os.environ, env, clear=False):
            if not flag:
                os.environ.pop("OMR_DOT_FOLLOWS_NOTE", None)
            adjudicate.run(log)
        return log, head, dot

    def test_RED_the_role_is_read_when_its_note_is_owned_by_another_staff(self):
        log, head, dot = self._run(flag=True)
        role = log.verdict(Q.DOT_ROLE, dot)
        self.assertEqual(role.value, "augmentation")
        self.assertEqual(role.detail["head"], head.to_key())

    def test_the_old_reading_with_the_flag_off_is_unchanged(self):
        log, head, dot = self._run(flag=False)
        role = log.verdict(Q.DOT_ROLE, dot)
        self.assertEqual(role.outcome, Outcome.ABSTAINED)

    def test_RED_the_dot_takes_its_notes_owner_not_its_strips(self):
        log, head, dot = self._run(flag=True)
        own = log.verdict(Q.GLYPH_OWNER, dot)
        self.assertEqual(own.value, BELOW.to_key())
        self.assertEqual(own.reason, "dot_follows_note")
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, head).value,
                         BELOW.to_key())

    def test_the_strip_owner_stays_with_the_flag_off(self):
        log, head, dot = self._run(flag=False)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, dot).value,
                         HOME.to_key())

    def test_the_note_still_reads_its_dot(self):
        log, head, dot = self._run(flag=True)
        self.assertEqual(log.verdict(Q.DURATION, head).value["dots"], 1)

    def test_POSITIVE_CONTROL_a_dot_with_no_note_to_its_left_is_untouched(self):
        log = _log()
        dot = _dot(log, 0, x=X - 60)
        _contest(log, dot, winner=BELOW, loser=HOME)
        with mock.patch.dict(os.environ, FLAG, clear=False):
            adjudicate.run(log)
        own = log.verdict(Q.GLYPH_OWNER, dot)
        self.assertEqual(own.value, BELOW.to_key())
        self.assertNotEqual(own.reason, "dot_follows_note")

    def test_RED_a_distant_neighbour_note_never_turns_a_staccato_into_a_dot(self):
        """Litolff: a staccato above its own note, with another staff's note
        far to the left and level with it, was read as an augmentation when
        the foreign window came first (8 of 14 role changes)."""
        log = _log()
        home_note = _note(log, 0, "noteheadBlack", x=X)
        ghost = _note(log, 1, "noteheadBlack", x=X - 50, y=-18)
        _contest(log, ghost, winner=BELOW, loser=HOME)
        dot = _dot(log, 2, x=X - 2, y=-14)
        with mock.patch.dict(os.environ, FLAG, clear=False):
            adjudicate.run(log)
        role = log.verdict(Q.DOT_ROLE, dot)
        self.assertEqual(role.value, "staccato")
        self.assertEqual(role.detail["owner"], home_note.to_key())

    def test_RED_a_dot_stacked_over_a_notes_column_is_not_guessed_an_augmentation(self):
        """Litolff, 6 of 6 first-version flips: the dot hangs over the NEXT
        note's column (a staccato just short of the staccato window) while a
        foreign note stands to its left. Left abstained, never guessed."""
        log = _log()
        ghost = _note(log, 0, "noteheadBlack", x=X - 50, y=-6)
        _contest(log, ghost, winner=BELOW, loser=HOME)
        _note(log, 1, "noteheadBlack", x=X + 20, y=8)        # the next note
        dot = _dot(log, 2, x=X + 16, y=2)  # over its column
        with mock.patch.dict(os.environ, FLAG, clear=False):
            adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DOT_ROLE, dot).outcome,
                         Outcome.ABSTAINED)

    def test_RED_a_far_dot_does_not_follow_a_note_owned_elsewhere(self):
        """The gap head-edge to dot is capped at 0.75 sp for a note owned by
        another staff (1.1+ sp on the two Litolff dots that were another
        note's staccato); the near dot of the same page still follows."""
        for gap, want in ((2, "augmentation"), (40, None)):
            log = _log()
            head = _note(log, 0, "noteheadHalf", x=X)
            _contest(log, head, winner=BELOW, loser=HOME)
            dot = _dot(log, 1, x=X + 10 + gap)
            with mock.patch.dict(os.environ, FLAG, clear=False):
                adjudicate.run(log)
            self.assertEqual(log.verdict(Q.DOT_ROLE, dot).value, want, gap)

    def test_a_note_whose_owner_is_not_decided_files_nothing(self):
        log = _log()
        head = _note(log, 0, "noteheadHalf", x=X)
        # contested but TIED: no decided owner
        log.observe(head, Q.GLYPH_BAND_DISTANCE, 2.0, reader=READERS.GEOMETRY,
                    frame="page", candidate=HOME.to_key(), own=True,
                    position_in_candidate=2.0)
        log.observe(head, Q.GLYPH_BAND_DISTANCE, 2.0, reader=READERS.GEOMETRY,
                    frame="page", candidate=BELOW.to_key(), own=False,
                    position_in_candidate=2.0)
        dot = _dot(log, 1, x=X + 12)
        _contest(log, dot, winner=HOME, loser=BELOW)
        with mock.patch.dict(os.environ, FLAG, clear=False):
            adjudicate.run(log)
        own = log.verdict(Q.GLYPH_OWNER, dot)
        self.assertNotEqual(own.reason, "dot_follows_note")


class TestADotBoxedAsAHeadFollowsTheDot(unittest.TestCase):
    """Brahms `glyph/7/1/0/9/9`: the top half of a dot, clipped by the strip
    above and boxed as a head, was given to the Flute; the same ink is a
    whole dot in the Oboe's strip, trailing the Oboe's note."""

    DOT_PAGE = (112, 4, 120, 12)
    SLIVER_PAGE = [112, 4, 120, 8]

    def _run(self, flag, dot_page=None, sliver_page=None):
        log = _log()
        head = _note(log, 0, "noteheadHalf", x=X)                # home note
        dot = _dot(log, 1, x=X + 12, page_box=dot_page or self.DOT_PAGE)
        sliver = R.glyph(0, 0, 1, 0, 2)                          # filed BELOW
        log.observe(sliver, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine",
                    reader=READERS.DETECTOR, frame="cell:1", score=0.9)
        log.observe(sliver, Q.GLYPH_BOX, ("noteheadBlackOnLine", 0, 0, 8, 4),
                    reader=READERS.DETECTOR, frame="cell:1", score=0.9,
                    bbox_page_px=sliver_page or self.SLIVER_PAGE)
        log.observe(R.cell(0, 0, 1, 0), Q.CELL_STAFF_SPACE, float(SPACE),
                    reader=READERS.GEOMETRY, frame="cell:1")
        _contest(log, sliver, winner=BELOW, loser=HOME)
        env = dict(FLAG) if flag else {}
        with mock.patch.dict(os.environ, env, clear=False):
            if not flag:
                os.environ.pop("OMR_DOT_FOLLOWS_NOTE", None)
            adjudicate.run(log)
        return log, sliver, dot, head

    def test_RED_the_box_takes_the_dots_owner(self):
        log, sliver, dot, head = self._run(flag=True)
        self.assertEqual(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                                     sliver).value, True)
        own = log.verdict(Q.GLYPH_OWNER, sliver)
        self.assertEqual(own.value, HOME.to_key())
        self.assertEqual(own.reason, "dot_follows_note")

    def test_RED_a_clipped_dot_under_the_group_rules_IoU_still_follows(self):
        """Brahms `7/1/0/9/9` vs `7/1/1/9/10`: IoU 0.295 (under the mark-group
        bar of 0.3) but 54% of the fragment lies inside the whole dot."""
        log, sliver, dot, head = self._run(
            flag=True, dot_page=(4480.0, 4272.0, 4493.0, 4284.0),
            sliver_page=[4476.18, 4269.95, 4492.55, 4276.89])
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, sliver).value,
                         HOME.to_key())

    def test_POSITIVE_CONTROL_a_box_beside_the_dot_not_on_it_is_not_moved(self):
        log, sliver, dot, head = self._run(
            flag=True, sliver_page=[200, 4, 208, 8])
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, sliver).value,
                         BELOW.to_key())

    def test_with_the_flag_off_it_keeps_the_strips_owner(self):
        log, sliver, dot, head = self._run(flag=False)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, sliver).value,
                         BELOW.to_key())

    def test_POSITIVE_CONTROL_a_real_head_overlapping_a_dot_is_not_moved(self):
        """Only a REFUSED, dot-sized box is a dot's twin."""
        log = _log()
        head = _note(log, 0, "noteheadHalf", x=X)
        dot = _dot(log, 1, x=X + 12, page_box=(112, 4, 120, 12))
        real = R.glyph(0, 0, 1, 0, 2)
        log.observe(real, Q.NOTEHEAD_CLASS, "noteheadHalf",
                    reader=READERS.DETECTOR, frame="cell:1", score=0.9)
        log.observe(real, Q.GLYPH_BOX, ("noteheadHalf", 0, 0, 21, 16),
                    reader=READERS.DETECTOR, frame="cell:1", score=0.9,
                    bbox_page_px=[104, 0, 125, 16])
        log.observe(R.cell(0, 0, 1, 0), Q.CELL_STAFF_SPACE, float(SPACE),
                    reader=READERS.GEOMETRY, frame="cell:1")
        _contest(log, real, winner=BELOW, loser=HOME)
        with mock.patch.dict(os.environ, FLAG, clear=False):
            adjudicate.run(log)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, real).value,
                         BELOW.to_key())


if __name__ == "__main__":
    unittest.main()
