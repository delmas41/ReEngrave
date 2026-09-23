"""ROADMAP 2.6 — the cross-staff contest's identity test, and its floor.

⚠️ THE FAULT THIS PINS. `gather_ownership_evidence` admitted a pair on
`di.smufl_name == dj.smufl_name`, and `…OnLine` / `…InSpace` is the head's
position RELATIVE TO A STAFF — the exact quantity a cross-staff contest exists
to arbitrate. One head printed in the gap between two staves is
`noteheadBlackOnLine` in the staff above's cell and `noteheadBlackInSpace` in
the staff below's, and the name test then ruled that the ink was not the same
thing as itself. It is now `di.category == dj.category`, which is the frozen
legacy reader's own predicate (`transcribe._dedupe_cross_staff_detections`),
together with that reader's swept `_CROSS_STAFF_DUPLICATE_IOU = 0.3`.

⚠️ RUN RED FIRST, against the unrepaired tree: `test_a_suffix_only_pair_IS_a
contest` and `test_a_pair_between_the_old_and_the_new_floor_IS_a_contest` both
FAIL on `CONTEST_IOU = 0.5` + the smufl-name test, which is what makes their
passing here a statement about the change rather than about the fixture.

⚠️ THE NEGATIVE CONTROLS ARE THE POINT, because a gate that admits everything
passes every positive test above. Three of them: a pair BELOW the swept 0.3
floor stays out, a pair whose CATEGORIES differ stays out, and two copies on
ONE staff stay out. Each is paired with a positive control differing in exactly
one fixture value, so none of them can pass by the gatherer filing nothing.

⚠️ NO SOURCE TEXT IS READ HERE. Every assertion runs the real
`gather_ownership_evidence` over a two-staff system and reads the rows it
files, which is what `test_contest_join.py`'s AST assertions cannot do.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q


#: The two staves' bands. The contested ink sits in the gap between them, which
#: is the geometry `measure_extractor`'s 4-space pad exists for.
_UPPER = [1100.0, 1110.0, 1120.0, 1130.0, 1140.0]
_LOWER = [1300.0, 1310.0, 1320.0, 1330.0, 1340.0]

#: Box height, and the vertical offsets that put two equal boxes at an exact
#: IoU. For equal boxes sharing their x span, IoU = (h - dy) / (h + dy), so
#: dy = 13 gives 14/40 = 0.35 and dy = 18 gives 9/45 = 0.20.
_H = 27.0
_DY_0_35 = 13.0
_DY_0_20 = 18.0


class _Det:
    """One detection, carrying the two fields the contest reads.

    ⚠️ `category` is not a convenience of this fixture: `gather_glyph_boxes`
    already writes `d.category` into every `Q.GLYPH_BOX` row, so a detection
    without one is not a detection this pipeline has ever seen.
    """

    def __init__(self, name, x, y, w, h, category="notehead"):
        self.smufl_name = name
        self.category = category
        self.x_canonical = x
        self.y_canonical = y
        self.width_canonical = w
        self.height_canonical = h
        self.confidence = 0.8


class _Staff:
    def __init__(self, staff_index, line_ys):
        self.staff_index = staff_index
        self.line_ys = line_ys


class _Cell:
    def __init__(self, staff_index, measure_index):
        self.page_index = 0
        self.staff_index = staff_index
        self.measure_index = measure_index
        # ⚠️ The identity transform, so a canonical coordinate IS a page pixel
        # here and an IoU computed in this file is the IoU the gatherer sees.
        self.bbox_page_px = [0.0, 0.0, 2000.0, 2000.0]
        self.upscale_factor = 1.0


class _P:
    page_index = 0


class _PWS:
    def __init__(self, staves):
        self.staves = staves
        self.page = _P()


def _band_rows(dets_by_staff):
    """Run the REAL gatherer and return its `Q.GLYPH_BAND_DISTANCE` rows."""
    log = Log()
    staves = [_Staff(0, _UPPER), _Staff(1, _LOWER)]
    cells = [_Cell(0, 0), _Cell(1, 0)]
    dets = {R.cell(0, 0, s, 0).to_key(): list(ds)
            for s, ds in dets_by_staff.items()}
    G.gather_ownership_evidence(
        log, _PWS(staves), cells,
        {st.staff_index: (0, st.staff_index) for st in staves}, dets)
    return [r for r in log.all_rows()
            if getattr(r, "quantity", None) == Q.GLYPH_BAND_DISTANCE]


class TestTheIouIsWhatTheFixtureSays(unittest.TestCase):
    """⚠️ THE FIXTURE'S OWN CONTROL. Every threshold claim below rests on two
    boxes sitting at a stated IoU; asserting the arithmetic here means a
    fixture that drifts fails as a fixture rather than as a verdict."""

    def _iou_at(self, dy):
        a = (200.0, 1200.0, 220.0, 1200.0 + _H)
        b = (200.0, 1200.0 + dy, 220.0, 1200.0 + dy + _H)
        return G._iou(a, b)

    def test_the_two_offsets_are_where_they_are_claimed_to_be(self):
        self.assertAlmostEqual(self._iou_at(_DY_0_35), 0.35, places=9)
        self.assertAlmostEqual(self._iou_at(_DY_0_20), 0.20, places=9)

    def test_the_floor_is_the_legacy_readers_swept_value(self):
        """⚠️ The value is not restated here — it is compared against the
        FROZEN reference reader's own constant, so the two cannot drift."""
        from tools.omr import transcribe
        self.assertEqual(G.CONTEST_IOU, transcribe._CROSS_STAFF_DUPLICATE_IOU)


class TestTheIdentityTestIsNotTheDisputedQuantity(unittest.TestCase):

    def _suffix_pair(self, dy=_DY_0_35):
        """One head in the gap, spelled the two ways two staves spell it."""
        return {0: [_Det("noteheadBlackOnLine", 200.0, 1200.0, 20.0, _H)],
                1: [_Det("noteheadBlackInSpace", 200.0, 1200.0 + dy,
                         20.0, _H)]}

    def test_a_suffix_only_pair_IS_a_contest(self):
        """⚠️ RED BEFORE THE CHANGE: the names differ, so the smufl-name gate
        rejected it and no band row of any state existed — which is why
        `adjudicate.subjects_for` never made these glyphs subjects at all."""
        rows = _band_rows(self._suffix_pair())
        self.assertTrue(rows)
        self.assertEqual({r.subject.staff for r in rows}, {0, 1})

    def test_a_black_and_a_half_head_ARE_one_contest(self):
        """Both are `category="notehead"`. ⚠️ The contest says WHOSE the ink
        is; it does not settle the head TYPE, and the loser's own
        `Q.NOTEHEAD_CLASS` row is never touched — `adjudicate_duration` reads
        the type on the surviving glyph's OWN subject."""
        rows = _band_rows(
            {0: [_Det("noteheadBlackOnLine", 200.0, 1200.0, 20.0, _H)],
             1: [_Det("noteheadHalfInSpace", 200.0, 1200.0 + _DY_0_35,
                      20.0, _H)]})
        self.assertEqual({r.subject.staff for r in rows}, {0, 1})

    def test_two_DIFFERENT_CATEGORIES_are_NOT_a_contest(self):
        """⚠️ THE NEGATIVE CONTROL THE WIDENING NEEDS. A dynamic letter and a
        notehead overlapping across the gap are two pieces of ink, not one, and
        resolving them would DROP one of them."""
        self.assertEqual(
            _band_rows(
                {0: [_Det("noteheadBlackOnLine", 200.0, 1200.0, 20.0, _H)],
                 1: [_Det("dynamicF", 200.0, 1200.0 + _DY_0_35, 20.0, _H,
                          category="dynamic")]}),
            [])

    def test_the_same_geometry_with_ONE_category_IS_a_contest(self):
        """The positive control for the test above: identical boxes, identical
        offset, only the category changed back."""
        self.assertTrue(_band_rows(
            {0: [_Det("dynamicP", 200.0, 1200.0, 20.0, _H,
                      category="dynamic")],
             1: [_Det("dynamicF", 200.0, 1200.0 + _DY_0_35, 20.0, _H,
                      category="dynamic")]}))


class TestTheFloor(unittest.TestCase):

    def _pair_at(self, dy, name_a="noteheadBlackOnLine",
                 name_b="noteheadBlackOnLine"):
        return {0: [_Det(name_a, 200.0, 1200.0, 20.0, _H)],
                1: [_Det(name_b, 200.0, 1200.0 + dy, 20.0, _H)]}

    def test_a_pair_between_the_old_and_the_new_floor_IS_a_contest(self):
        """⚠️ RED BEFORE THE CHANGE at `CONTEST_IOU = 0.5`. 0.35 is above the
        swept legacy floor and below the value the staged gather restated."""
        self.assertTrue(_band_rows(self._pair_at(_DY_0_35)))

    def test_a_pair_BELOW_the_swept_floor_is_NOT_a_contest(self):
        """⚠️ 0.20 is under 0.3, and 0.25 was measured MERGING genuinely
        distinct neighbours and dropping three correctly-matched notes on
        Brahms. A clipped copy is not a contest anyone can win."""
        self.assertEqual(_band_rows(self._pair_at(_DY_0_20)), [])

    def test_two_copies_on_ONE_staff_are_still_NOT_a_contest(self):
        """⚠️ The same-cell duplicate is the detector's NMS question and
        ownership never speaks about it. Widening the CLASS test must not have
        widened this."""
        self.assertEqual(
            _band_rows({0: [_Det("noteheadBlackOnLine", 200.0, 1200.0,
                                 20.0, _H),
                            _Det("noteheadBlackInSpace", 200.0,
                                 1200.0 + _DY_0_35, 20.0, _H)]}),
            [])

    def test_a_lone_glyph_is_never_handed_in(self):
        """⚠️ THE CONSTRAINT §10 CALLS THE ONE PLACE A PLAUSIBLE FIX IS THE
        WRONG ONE. A glyph with no twin must NOT enter the contest: awarded
        elsewhere it would be DROPPED at export and the note would vanish,
        turning a wrong-staff error into a missing one."""
        self.assertEqual(
            _band_rows({0: [_Det("noteheadBlackOnLine", 200.0, 1200.0,
                                 20.0, _H)]}),
            [])


if __name__ == "__main__":
    unittest.main()
