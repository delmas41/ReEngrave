"""ROADMAP 2.78 -- why `Q.STEM_SLASH` missed Sean's tiles 7 and 8, and the two small readings that close it.

Sean (2026-10-09) read both stems as slashed (*"2 half notes with a trem slash"*, *"Dotted half with
a trem slash"*) and the reader filed `one_sided`. Replayed on the REAL ink (captured with a recorder around
`gather.stem_slashes`, FINDINGS `omr-head-fill-2026-09` Sec.12):

  tile 7  the slash's contact with the stem is 1.37 staff spaces on its left; the reader refused any contact
          over 1.3 (`STEM_SLASH_MAX_CONTACT_SPACES`) as "a head or a clump".
  tile 8  the stem flares at the slash's root, so the column the tracker starts at already holds stem ink; the
          run there is taller than the stroke's own contact, the `swelled past 1.7x` stop fires on column ZERO
          and the left track is empty (`left_reach 0.0`).

RED against the unrepaired tree: the reader has neither a 1.6 cap nor a start tolerance there, so both reads
below return no slash. Each has its own control that can fail (the old constant, the tracker called with no
skip), and the unchanged behaviours stay put (a real clump over the NEW cap is still refused; a stroke that
tracks at its first column returns exactly what it did).
"""
from __future__ import annotations

import unittest

import numpy as np

from tools.omr.staged import gather
from tools.omr.tests.test_staged_stem_slash import (
    LINE, SP, STEM_BOX, STOP, SX0, _paper, _passing, _read, _slash, _stem_ink)


class TestABoldSlashIsNotAClump(unittest.TestCase):
    """Tile 7: a contact interval between the old cap (1.3 spaces) and the new (1.6)."""

    def _bold(self):
        img = _paper()
        _stem_ink(img)
        # ~1.45 spaces of vertical contact: thick 1.3 spaces at ~25 degrees
        _slash(img, 170, thick=1.3, rise=0.45)
        return img

    def test_a_bold_slash_is_read_RED(self):
        got = _passing(_read(self._bold()))
        self.assertEqual(len(got), 1, [s["reason"] for s in _read(self._bold())])

    def test_CONTROL_with_the_old_cap_it_is_refused_as_a_clump(self):
        """The control that can fail: restore 1.3 and the same ink reads nothing."""
        old = gather.STEM_SLASH_MAX_CONTACT_SPACES
        gather.STEM_SLASH_MAX_CONTACT_SPACES = 1.3
        try:
            self.assertEqual(_passing(_read(self._bold())), [])
        finally:
            gather.STEM_SLASH_MAX_CONTACT_SPACES = old

    def test_a_real_clump_over_the_new_cap_is_STILL_refused(self):
        """A block taller than the new cap (a head's worth of ink at the stem) is not a slash."""
        img = _paper()
        _stem_ink(img)
        img[200:200 + int(2.2 * SP), 250:360] = 0
        self.assertEqual(_passing(_read(img)), [])


class TestAFlaredStemRoot(unittest.TestCase):
    """Tile 8: the column the tracker starts at is inside the stem's flare."""

    def _flared(self):
        img = _paper()
        _stem_ink(img)
        y = 170
        img[y - 40:y + 40, SX0 - 2:SX0] = 0            # the stem is 2 px wider on the left here
        _slash(img, y)
        return img

    def test_the_slash_beside_a_flared_root_is_read_RED(self):
        got = _passing(_read(self._flared()))
        self.assertEqual(len(got), 1, [(s["reason"], s.get("left_reach")) for s in _read(self._flared())])
        self.assertGreater(min(got[0]["left_reach"], got[0]["right_reach"]), 0.5)

    def test_CONTROL_without_the_start_tolerance_it_reads_one_sided(self):
        """The control that can fail: no skip, and the left track is empty (`one_sided`)."""
        old = gather.STEM_SLASH_START_SKIP_SPACES
        gather.STEM_SLASH_START_SKIP_SPACES = 0.0
        try:
            strokes = _read(self._flared())
            self.assertEqual(_passing(strokes), [])
            self.assertEqual([s["reason"] for s in strokes], ["one_sided"])
        finally:
            gather.STEM_SLASH_START_SKIP_SPACES = old

    def test_a_stroke_that_tracks_at_its_first_column_is_unchanged(self):
        """The tolerance fires only where the first column tracked NOTHING: a plain slash returns the
        very run it always did."""
        img = _paper()
        _stem_ink(img)
        _slash(img, 170)
        ink = img == 0
        a = gather._track_stroke(ink, SX0 - 2, -1, (160, 185), SP, int(1.9 * SP))
        b = gather._track_stroke_from(ink, SX0 - 2, -1, (160, 185), SP, int(1.9 * SP))
        self.assertEqual(a, b)
        self.assertTrue(a)

    def test_it_does_not_invent_a_stroke_where_there_is_no_ink(self):
        ink = np.zeros((500, 700), bool)
        self.assertEqual(gather._track_stroke(ink, 298, -1, (160, 185), SP, 70), [])


if __name__ == "__main__":
    unittest.main()
