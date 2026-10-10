"""ROADMAP 2.12f round 2 -- the owner of an articulation is the nearest head
whose NOTEHEAD side faces the mark.

Sean (DECISIONS 2026-10-09, CONFIRMED -- not an assumption of this lane): an
articulation sits on the NOTEHEAD side, opposite the stem (stem up -> below the
head, stem down -> above). With two voices on one staff (opposite stems in one
column) it goes on the STEM side.

Sean judged the round-1 tiles: the class suffix's side was right on every real
articulation (10 of 10); the three far picks (the x-only pick took a head ~3
heads away) were all wrong -- the mark belongs to the head it touches.

THE TWO READERS: the class SUFFIX (the detector) and the STEM direction (the CV
rung) are different readers. The suffix still GATES the candidates (a head on
the side the class names, in the cell -- the old, true `no_notehead` for a mark
whose head is in the NEIGHBOUR staff), the stem convention SELECTS among them,
and both are recorded. Where the stem is unread, or the convention puts the mark
on the stem side of a single voice, or two heads qualify about equally, the mark
abstains / narrows with a reason word (CLAUDE.md rule 8). It never falls back to
nearest-in-x.

POSITIONS: a 20 x 20 head at y 40..60 (centre 50); a mark box 6 x 6; stems are CV
rows on the cell. The refusals each sit beside the same page with ONE fact
changed that decides, so none passes by refusing everything.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS

CELL = R.cell(0, 0, 0, 0)
HEAD_Y, HEAD_H = 40.0, 20.0


def _head(log, gi, x=97.0, y=HEAD_Y, *, w=20.0, h=HEAD_H, stem=None, staff=0):
    """A notehead; `stem` in (None, 'up', 'down') files ONE CV stem touching it."""
    g = R.glyph(0, 0, staff, 0, gi)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead")
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine",
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    # ⚠️ 40 px, SO A STEM NEVER REACHES THE NEXT HEAD OF A COLUMN: a stem that
    # touches a second head's box is a chord stem to the reader, and the fixtures
    # that file two heads one above the other are about two heads, not one chord.
    if stem == "up":          # rises from the right edge, above the head
        _stem(log, x + w - 3, y - 40, 40 + h / 2)
    elif stem == "down":      # hangs from the left edge, below the head
        _stem(log, x, y + h / 2, 40 + h / 2)
    return g


def _stem(log, x, y, h, w=3.0):
    log.observe(CELL, Q.STEM, (x, y, w, h), reader=READERS.CV_LINES,
                frame="cell:0", x0=x, x1=x + w, y_center=y + h / 2,
                image="no_staff", staff_lines_erased=True)


def _mark(log, gi, x, y, cls, *, w=6.0, h=6.0, staff=0, page_box=None):
    g = R.glyph(0, 0, staff, 0, gi)
    side = ("above" if cls.endswith("Above")
            else "below" if cls.endswith("Below") else None)
    extra = {}
    if page_box is not None:
        extra["bbox_page_px"] = list(page_box)
    log.observe(g, Q.ARTICULATION_MARK, cls, reader=READERS.DETECTOR,
                frame="cell:0", score=0.8,
                x0=x, x1=x + w, y0=y, y1=y + h,
                x_center=x + w / 2.0, y_center=y + h / 2.0, side=side, **extra)
    return g


def _decide(log, mark):
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.ARTICULATION_OWNER, mark)


MARK0 = R.glyph(0, 0, 0, 0, 0)


class TestTheStemDirectionIsDecidedBeforeTheOwner(unittest.TestCase):
    def test_RED_stem_direction_precedes_articulation_owner_in_ORDER(self):
        """ADJUDICATE reads a frozen log: a verdict decided AFTER this one reads
        as a hole. The owner reads `Q.STEM_DIRECTION`, so it must come later."""
        self.assertLess(adjudicate.ORDER.index(Q.STEM_DIRECTION),
                        adjudicate.ORDER.index(Q.ARTICULATION_OWNER))


class TestTheNoteheadSideFacesTheMark(unittest.TestCase):
    def test_RED_stem_down_takes_a_mark_ABOVE_it(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articAccentAbove")
        head = _head(log, 1, stem="down")
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, head.to_key())
        self.assertEqual(v.reason, "nearest_on_notehead_side")
        self.assertEqual(v.detail["stem_direction"], "down")
        self.assertEqual(v.detail["notehead_side"], "above")
        self.assertEqual(v.detail["stem_rule"], "notehead_side")
        self.assertFalse(v.detail["two_voice"])

    def test_stem_up_takes_a_mark_BELOW_it(self):
        """The other side, or an inverted comparison passes."""
        log = Log()
        _mark(log, 0, 100.0, 80.0, "articAccentBelow")
        head = _head(log, 1, stem="up")
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, head.to_key())
        self.assertEqual(v.detail["stem_direction"], "up")
        self.assertEqual(v.detail["notehead_side"], "below")

    def test_RED_a_mark_on_the_STEM_side_of_a_single_voice_abstains(self):
        """Class Above, mark above the head, but the stem rises from it: the mark
        is on the stem side. The two readers disagree -- neither wins."""
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articAccentAbove")
        _head(log, 1, stem="up")
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "stem_contradicts_class_side")
        self.assertEqual(v.detail["suffix_side"], "above")
        self.assertEqual(v.detail["stem_direction"], "up")
        self.assertEqual(v.detail["notehead_side"], "below")

    def test_POSITIVE_CONTROL_the_same_page_with_the_stem_flipped_decides(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articAccentAbove")
        head = _head(log, 1, stem="down")
        self.assertEqual(_decide(log, MARK0).value, head.to_key())


class TestTwoVoicesPutTheMarkOnTheStemSide(unittest.TestCase):
    """Opposite stems in one column: the upper voice's stem rises, the lower
    voice's hangs, and each mark stands OUTSIDE the pair, on its own stem side."""

    def _two_voices(self, cls, y):
        log = Log()
        _mark(log, 0, 100.0, y, cls)
        upper = _head(log, 1, y=0.0, stem="up")        # y 0..20, stem rises
        lower = _head(log, 2, y=100.0, stem="down")    # y 100..120, stem hangs
        return log, upper, lower

    def test_RED_a_mark_above_the_UPPER_voice_is_its_stem_side(self):
        log, upper, _lower = self._two_voices("articAccentAbove", -40.0)
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, upper.to_key())
        self.assertTrue(v.detail["two_voice"])
        self.assertEqual(v.detail["stem_rule"], "stem_side")
        self.assertEqual(v.detail["stem_direction"], "up")

    def test_a_mark_below_the_LOWER_voice_is_its_stem_side(self):
        log, _upper, lower = self._two_voices("articAccentBelow", 140.0)
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, lower.to_key())
        self.assertTrue(v.detail["two_voice"])

    def test_POSITIVE_CONTROL_one_voice_the_same_mark_abstains(self):
        """The identical mark above a head whose column-mate points the SAME way
        is a single voice: the mark is on the stem side, and abstains."""
        log = Log()
        _mark(log, 0, 100.0, -40.0, "articAccentAbove")
        _head(log, 1, y=0.0, stem="up")
        _head(log, 2, y=100.0, stem="up")
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "stem_contradicts_class_side")


class TestTheNearestByGapNotByX(unittest.TestCase):
    """Sean, tiles 7, 9, 10: the x-only pick took a head ~3 heads away; the mark
    belongs to the head it touches."""

    def _column(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articTenutoAbove")    # y 0..6
        near = _head(log, 1, x=97.0, y=20.0, stem="down")    # gap 14, dx 4
        far = _head(log, 2, x=95.0, y=100.0, stem="down")    # gap 94, dx 2 (x-nearer)
        return log, near, far

    def test_RED_the_touching_head_wins_over_the_x_nearer_one(self):
        log, near, far = self._column()
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, near.to_key(), "x-nearest picked the far head")

    def test_POSITIVE_CONTROL_when_the_touching_head_is_also_x_nearest(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articTenutoAbove")
        near = _head(log, 1, x=97.0, y=20.0, stem="down")
        _head(log, 2, x=90.0, y=100.0, stem="down")
        self.assertEqual(_decide(log, MARK0).value, near.to_key())

    def test_RED_two_heads_at_about_the_same_gap_NARROW_not_argmax(self):
        """Two qualifying heads in different columns, gaps within a quarter of a
        head height: the geometry cannot choose, and picking one by x would be
        the old guess. It narrows to both."""
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articAccentAbove")
        a = _head(log, 1, x=92.0, y=20.0, stem="down")
        b = _head(log, 2, x=108.0, y=21.0, stem="down")
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "narrowed")
        self.assertEqual(v.reason, "heads_about_equally_near")
        self.assertEqual({c.value for c in v.candidates},
                         {a.to_key(), b.to_key()})

    def test_POSITIVE_CONTROL_a_clear_gap_difference_decides(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articAccentAbove")
        a = _head(log, 1, x=92.0, y=20.0, stem="down")
        _head(log, 2, x=108.0, y=50.0, stem="down")      # a full head further
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, a.to_key())


class TestAnUnreadStemAbstainsAndNeverFallsBackToX(unittest.TestCase):
    def test_RED_no_stem_decided_abstains_with_its_own_reason(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articAccentAbove")
        head = _head(log, 1, stem=None)                  # the CV rung read no stem
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "stem_direction_unread")
        self.assertEqual(v.detail["nearest_head"], head.to_key())
        self.assertEqual(v.detail["suffix_side"], "above")
        self.assertEqual(v.detail["measured_side"], "above")

    def test_POSITIVE_CONTROL_the_same_page_with_a_stem_decides(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articAccentAbove")
        head = _head(log, 1, stem="down")
        self.assertEqual(_decide(log, MARK0).value, head.to_key())

    def test_RED_a_NEARER_head_with_an_unread_stem_is_not_skipped(self):
        """The touching head's stem is unread; a head further down qualifies. The
        touching head may be the owner, and giving the mark to the farther one is
        the far pick Sean found wrong (tiles 7, 9, 10) -- so it abstains."""
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articAccentAbove")
        _head(log, 1, x=97.0, y=20.0, stem=None)            # touching, unread
        _head(log, 2, x=97.0, y=100.0, stem="down")         # farther, qualifies
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "stem_direction_unread")

    def test_POSITIVE_CONTROL_an_unread_head_FARTHER_than_the_owner_is_no_veto(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articAccentAbove")
        good = _head(log, 1, x=97.0, y=20.0, stem="down")   # touching, qualifies
        _head(log, 2, x=97.0, y=100.0, stem=None)           # farther, unread
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, good.to_key())


class TestTheClassSideStillGatesTheCandidates(unittest.TestCase):
    """Sean, tiles 1, 2, 5, 11: the class suffix was RIGHT and the head the mark
    belongs to is in the NEIGHBOUR staff. In this cell the only head stands on
    the OTHER side of the mark -- and its stem even makes the convention agree
    with it -- so a stem-only rule would take the wrong note. The honest answer
    is the old one: no head on the declared side in this cell."""

    def test_RED_a_head_on_the_other_side_with_a_agreeing_stem_is_not_taken(self):
        log = Log()
        _mark(log, 0, 100.0, 80.0, "articAccentAbove")   # BELOW the head
        _head(log, 1, stem="up")                          # stem up: below is right
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "no_notehead")
        self.assertEqual(v.detail["suffix_side"], "above")
        self.assertEqual(v.detail["measured_side"], "below")   # the recording stays

    def test_POSITIVE_CONTROL_the_class_that_names_that_side_decides(self):
        log = Log()
        _mark(log, 0, 100.0, 80.0, "articAccentBelow")
        head = _head(log, 1, stem="up")
        self.assertEqual(_decide(log, MARK0).value, head.to_key())


class TestALevelMarkAbstains(unittest.TestCase):
    def test_a_mark_centred_inside_the_heads_extent_is_level(self):
        log = Log()
        _mark(log, 0, 100.0, 44.0, "articAccentAbove")   # y 44..50
        _head(log, 1, stem="down")
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "level_with_head")

    def test_POSITIVE_CONTROL_clear_of_the_head_decides(self):
        log = Log()
        _mark(log, 0, 100.0, 20.0, "articAccentAbove")
        head = _head(log, 1, stem="down")
        self.assertEqual(_decide(log, MARK0).value, head.to_key())


class TestTheSameInkInTheNeighboursCell(unittest.TestCase):
    """CLAUDE.md Sec.10: a cell is padded ~4 spaces and reaches the neighbour's
    ink, so a mark standing in the gap is often detected a SECOND time in the
    neighbour staff's cell, on the same ink. That is a GATHER fact (page boxes),
    recorded on every verdict -- the abstention in the first cell is correct and
    the mark is owned via the twin; nothing is searched across staves and nothing
    is relocated (a resolved cross-staff contest DROPS the loser)."""

    BOX = (500.0, 800.0, 560.0, 830.0)

    def test_RED_a_twin_in_another_cell_is_recorded_on_an_abstained_mark(self):
        log = Log()
        _mark(log, 0, 100.0, 80.0, "articAccentAbove", page_box=self.BOX)
        _head(log, 1, stem="up")
        twin = _mark(log, 5, 100.0, 80.0, "articAccentAbove", staff=1,
                     page_box=(502.0, 801.0, 561.0, 829.0))
        v = _decide(log, MARK0)
        self.assertEqual(v.reason, "no_notehead")
        self.assertEqual(v.detail["same_ink_twins"], [twin.to_key()])

    def test_the_twin_is_recorded_on_a_decided_mark_too(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articAccentAbove", page_box=self.BOX)
        _head(log, 1, stem="down")
        twin = _mark(log, 5, 100.0, 0.0, "articAccentAbove", staff=1,
                     page_box=self.BOX)
        v = _decide(log, MARK0)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.detail["same_ink_twins"], [twin.to_key()])

    def test_POSITIVE_CONTROL_a_mark_elsewhere_on_the_page_is_not_a_twin(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articAccentAbove", page_box=self.BOX)
        _head(log, 1, stem="down")
        _mark(log, 5, 100.0, 0.0, "articAccentAbove", staff=1,
              page_box=(900.0, 800.0, 960.0, 830.0))
        self.assertEqual(_decide(log, MARK0).detail["same_ink_twins"], [])

    def test_a_mark_with_no_page_box_records_an_empty_list_not_a_guess(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0, "articAccentAbove")
        _head(log, 1, stem="down")
        self.assertEqual(_decide(log, MARK0).detail["same_ink_twins"], [])


if __name__ == "__main__":
    unittest.main()
