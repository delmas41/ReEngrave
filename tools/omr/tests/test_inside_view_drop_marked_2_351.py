"""ROADMAP 2.351 (second question) -- a note read and decided is never dropped unmarked (STAGED EXPORT, `OMR_INSIDE_VIEW_DROP_MARKED`).

`relocation_inside_owner_view` refuses a head another staff owns that the owner's view saw but drew no box for (it could be one head's
ink counted twice). It was filed as not-a-gap, so the note vanished with no mark. With the flag the refusal stands -- nothing is
written -- and the place carries 2.333's dropped-head mark. Wiring only: the real-page effect was measured offline by exporting the
20261123-night slices (Litolff p1/2/4/6/8/9/10/11/13/16, Brahms sample pages), flag off vs on: 7 + 2 places marked, nothing else in
the file changed (lane 2.351 report).
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import export as E

R = "relocation_inside_owner_view"


class InsideViewDropMarked(unittest.TestCase):

    def test_off_by_default_the_drop_is_silent(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(E.INSIDE_VIEW_DROP_MARKED_ENV, None)
            self.assertFalse(E.inside_view_drop_marked_enabled())
            self.assertFalse(E._dropped_head_may_be_a_note(R))

    def test_on_the_drop_is_a_dropped_head(self):
        with mock.patch.dict(os.environ, {E.INSIDE_VIEW_DROP_MARKED_ENV: "1"}):
            self.assertTrue(E._dropped_head_may_be_a_note(R))

    def test_on_nothing_else_moves(self):
        # other not-a-gap refusals (another mark's ink, a duplicate box) stay scraps with the flag on
        with mock.patch.dict(os.environ, {E.INSIDE_VIEW_DROP_MARKED_ENV: "1"}):
            for r in ("relocation_on_another_mark", "relocation_not_a_head_by_ink", "mark_group_duplicate",
                      "not_a_notehead:claimed_by:word"):
                with self.subTest(r):
                    self.assertFalse(E._dropped_head_may_be_a_note(r))

    def test_still_not_a_bar_gap(self):
        self.assertIn(R, E._NOT_A_GAP_REASONS)        # the bar is not marked unread as a whole; only the spot

    def test_mark_words(self):
        self.assertIn(R, E._DROPPED_HEAD_REASON_WORDS)


if __name__ == "__main__":
    unittest.main()
