"""ROADMAP 2.78 -- ONE STEM, ONE VALUE (Sean, DECISIONS 2026-10-09, "no exceptions").

`adjudicators/stem_value.py`: `Q.HEAD_STEM` (which stem a notehead box stands on,
filed once) and `Q.STEM_VALUE` (the stem's written value, per head, read from the
stem's own evidence: hollow heads, the beams at its tip, the dots).

Every case below is a synthetic stem with the pattern of one of Sean's 14 blind
tiles (`out/print/2.78-review/answers.json`), named by tile, plus the controls the
rule needs: a positive control (stems that already agree are untouched), a
KEEP-THE-REAL-NOTE control (a filled-classed box on a hollow stem is NOT refused:
it stays a member and takes the stem's value -- Sean's "never by fill alone"), a
control that the TIP and not the minimum is what reads the beams, and a control
that the whole-class convention is what decides tile 9.

RED against the unrepaired tree: `Q.HEAD_STEM`, `Q.STEM_VALUE` and
`adjudicators/stem_value.py` do not exist there (`AttributeError`/`ImportError`),
confirmed by running this file against a clean `git archive` of the parent commit.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  (populates the registry)
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import stem_value as SV
from tools.omr.staged.record import (Candidate, Log, Outcome, Q, READERS,
                                     Verdict)

CELL = R.cell(0, 0, 0, 0)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures -- the real row shapes, nothing the gather would not file
# ─────────────────────────────────────────────────────────────────────────────

def _v(log, sub, q, outcome, value, *, reason="t", candidates=(), detail=None):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome,
        value=value, decider="test", reason=reason, candidates=candidates,
        detail=detail or {}))


def _stem(log, *, x=100, y=0, w=4, h=80):
    return log.observe(CELL, Q.STEM, (x, y, w, h), reader=READERS.CV_LINES,
                       frame="cell:0", x0=x, x1=x + w, y_center=y + h / 2.0,
                       image="no_staff", staff_lines_erased=True)


def _dur(written, dots=0, levels=0, scale=1.0):
    return {"beats": written * scale, "written": written, "dots": dots,
            "beam_levels": levels}


class Stem:
    """One cell holding one stem and the heads on it. `heads` are added with
    `head(...)`; `run()` runs the two decisions over every head."""

    def __init__(self, *, direction="up", x=100, y=0, w=4, h=80, staff=0):
        self.log = Log()
        self.row = _stem(self.log, x=x, y=y, w=w, h=h)
        self.direction = direction
        self.x, self.staff = x, staff
        self.heads = {}

    def head(self, gi, cls, y, *, decided=None, narrowed=None, abstain=False,
             x=None, w=20, h=16, direction="same"):
        """`decided=(written, dots, levels)`; `narrowed=[(written, dots,
        levels), ...]`. `x` defaults to a head whose RIGHT edge is flush with
        the stem (a stem up stands at the right of its head)."""
        g = R.glyph(0, 0, self.staff, 0, gi)
        hx = (self.x + 2 - w) if x is None else x
        self.log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR,
                         frame="cell:0", score=0.9)
        self.log.observe(g, Q.GLYPH_BOX, (cls, hx, y, w, h),
                         reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        if decided is not None:
            _v(self.log, g, Q.DURATION, Outcome.DECIDED, _dur(*decided),
               reason="head_and_marks")
        elif narrowed is not None:
            _v(self.log, g, Q.DURATION, Outcome.NARROWED, None,
               reason="beam_discounted_uncertain",
               candidates=tuple(Candidate(_dur(*o), 2.0 - i)
                                for i, o in enumerate(narrowed)))
        elif abstain:
            _v(self.log, g, Q.DURATION, Outcome.ABSTAINED, None,
               reason="unknown_head")
        d = self.direction if direction == "same" else direction
        if d:
            _v(self.log, g, Q.STEM_DIRECTION, Outcome.DECIDED, d,
               reason="stem_projection")
        self.heads[gi] = g
        return g

    def refuse(self, gi, reason="tremolo_slash_crosses_stem"):
        _v(self.log, self.heads[gi], Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
           Outcome.DECIDED, True, reason=reason)

    def give_away(self, gi, to="staff/0/0/9"):
        _v(self.log, self.heads[gi], Q.GLYPH_OWNER, Outcome.DECIDED, to,
           reason="distance")

    def run(self):
        for q in (Q.HEAD_STEM, Q.STEM_VALUE):
            spec = adjudicate.REGISTRY[q]
            for sub in adjudicate.subjects_for(self.log, spec):
                adjudicate.adjudicate_one(self.log, spec, sub)
        return self

    def value(self, gi):
        return self.log.verdict(Q.STEM_VALUE, self.heads[gi])

    def join(self, gi):
        return self.log.verdict(Q.HEAD_STEM, self.heads[gi])


def _w(v):
    """(written, dots, beam_levels) of a decided STEM_VALUE."""
    return (v.value["written"], v.value["dots"], v.value["beam_levels"])


class _Case(unittest.TestCase):
    def assertValue(self, v, written, dots=0, levels=0):
        self.assertIs(v.outcome, Outcome.DECIDED, (v.reason, v.detail))
        self.assertEqual(_w(v), (written, dots, levels), v.detail)


# ─────────────────────────────────────────────────────────────────────────────
# Q.HEAD_STEM -- the join, filed once
# ─────────────────────────────────────────────────────────────────────────────

class TestTheJoin(_Case):

    def test_two_heads_of_one_chord_name_the_SAME_stem(self):
        """The positive control: nothing on the record said this before."""
        s = Stem()
        s.head(0, "noteheadHalfOnLine", 60, decided=(2.0, 0, 0))
        s.head(1, "noteheadHalfInSpace", 30, decided=(2.0, 0, 0))
        s.run()
        j0, j1 = s.join(0), s.join(1)
        self.assertIs(j0.outcome, Outcome.DECIDED)
        self.assertEqual(j0.value, s.row.id)
        self.assertEqual(j0.value, j1.value)
        self.assertEqual(j0.reason, "one_stem")

    def test_a_head_touching_no_stem_ABSTAINS(self):
        """The negative control: a box nowhere near the stem has no stem."""
        s = Stem()
        s.head(0, "noteheadWholeOnLine", 60, decided=(4.0, 0, 0), x=300)
        s.run()
        self.assertIs(s.join(0).outcome, Outcome.ABSTAINED)
        self.assertEqual(s.join(0).reason, "no_stem")

    def test_two_rows_that_are_ONE_physical_stem_collapse_onto_the_taller(self):
        """12 / 5 stem groups on the count-page ranges were the same head-set
        reached through duplicate CV rows (FINDINGS Sec.11.1)."""
        s = Stem()
        dup = _stem(s.log, x=101, y=2, w=4, h=70)       # the same stem, shorter
        s.head(0, "noteheadBlack", 60, decided=(1.0, 0, 0))
        s.head(1, "noteheadBlack", 30, decided=(1.0, 0, 0))
        s.run()
        self.assertEqual(s.join(0).value, s.row.id)       # the taller (h=80)
        self.assertEqual(s.join(1).value, s.row.id)
        self.assertIn(dup.id, s.join(0).detail["stem_rows"])

    def test_two_distinct_stems_one_FLUSH_the_side_rule_picks_it(self):
        """A stem stands at the side of its head (CLAUDE.md §10): of two stems
        that touch a box, only the one flush with a side is its stem. (No
        direction is read here, so only the bare flush test is left.)"""
        s = Stem(direction=None)
        other = _stem(s.log, x=90, y=0, w=4, h=80)        # through its middle
        s.head(0, "noteheadBlack", 60, decided=(1.0, 0, 0))
        s.run()
        j = s.join(0)
        self.assertIs(j.outcome, Outcome.DECIDED)
        self.assertEqual(j.value, s.row.id)
        self.assertEqual(j.reason, "stem_by_flush")
        self.assertEqual(j.detail["rivals"], [other.id])

    def test_two_distinct_stems_BOTH_flush_and_no_direction_NARROWS(self):
        """A box with a stem at each side is equally two heads' stem, and with
        no direction read nothing names a side: not decided (rule 8)."""
        s = Stem(direction=None)
        _stem(s.log, x=82, y=0, w=4, h=80)                # at its LEFT side
        s.head(0, "noteheadBlack", 60, decided=(1.0, 0, 0))
        s.run()
        j = s.join(0)
        self.assertIs(j.outcome, Outcome.NARROWED)
        self.assertEqual(j.reason, "two_stems")
        self.assertEqual(len(j.candidates), 2)

    def test_the_stem_DIRECTION_names_the_side_up_is_right(self):
        """Brahms p0 `glyph/0/0/1/6/2`-style: a stem flush at each side of one
        box, the head's own stem pointing UP -> the stem at its RIGHT is its."""
        s = Stem(direction="up")
        left = _stem(s.log, x=82, y=0, w=4, h=80)
        s.head(0, "noteheadBlack", 60, decided=(1.0, 0, 0))
        s.run()
        j = s.join(0)
        self.assertIs(j.outcome, Outcome.DECIDED)
        self.assertEqual(j.value, s.row.id)               # x=100: the RIGHT one
        self.assertEqual(j.reason, "stem_by_side")
        self.assertEqual(j.detail["rivals"], [left.id])
        self.assertEqual(j.detail["direction"], "up")

    def test_the_stem_DIRECTION_CONTROL_down_is_left_so_the_choice_FLIPS(self):
        """The control that can fail: the same two stems with the head's stem
        pointing DOWN -> the stem at its LEFT is its. A rule that ignored the
        direction (or always took the right one) would not flip."""
        s = Stem(direction="down")
        left = _stem(s.log, x=82, y=0, w=4, h=80)
        s.head(0, "noteheadBlack", 60, decided=(1.0, 0, 0))
        s.run()
        j = s.join(0)
        self.assertIs(j.outcome, Outcome.DECIDED)
        self.assertEqual(j.value, left.id)
        self.assertEqual(j.reason, "stem_by_side")

    def test_tile_7_a_stem_FRAGMENT_inside_the_heads_height_is_not_its_stem(self):
        """Litolff p2 `glyph/2/1/9/11/3`: a big hollow box touched by a long
        stem at its right and a short fragment at its left, both flush. The
        fragment never leaves the head's own height (0.4 space past the box
        against a measured 0.8 minimum), so the long stem is the head's."""
        s = Stem(y=0, h=200)                                  # the long stem
        s.log.observe(CELL, Q.CELL_STAFF_SPACE, 10.0, reader=READERS.GEOMETRY,
                      frame="cell:0")
        frag = _stem(s.log, x=84, y=96, w=4, h=44)            # inside y 100..140
        s.head(0, "noteheadHalfInSpace", 100, w=20, h=40,
               decided=(2.0, 0, 0))
        s.run()
        j = s.join(0)
        self.assertIs(j.outcome, Outcome.DECIDED)
        self.assertEqual(j.value, s.row.id)
        self.assertEqual(j.reason, "stem_by_reach")
        self.assertEqual(j.detail["rivals"], [frag.id])

    def test_tile_7_CONTROL_two_stems_that_both_REACH_still_narrow(self):
        """The control that can fail: give the left stem a real length and the
        reach test no longer separates them, so the join is NARROWED again
        (no direction is read, so the side rule has nothing to say either)."""
        s = Stem(y=0, h=200, direction=None)
        s.log.observe(CELL, Q.CELL_STAFF_SPACE, 10.0, reader=READERS.GEOMETRY,
                      frame="cell:0")
        _stem(s.log, x=84, y=0, w=4, h=200)                   # reaches 100 px
        s.head(0, "noteheadHalfInSpace", 100, w=20, h=40,
               decided=(2.0, 0, 0))
        s.run()
        self.assertIs(s.join(0).outcome, Outcome.NARROWED)

    def test_without_a_staff_space_the_reach_test_is_SKIPPED_not_defaulted(self):
        """Rule 6: no unit, no reach test -- with no direction read either, only
        the bare flush test is left, and both stems are flush."""
        s = Stem(y=0, h=200, direction=None)
        _stem(s.log, x=84, y=96, w=4, h=44)
        s.head(0, "noteheadHalfInSpace", 100, w=20, h=40,
               decided=(2.0, 0, 0))
        s.run()
        self.assertIs(s.join(0).outcome, Outcome.NARROWED)

    def test_a_REFUSED_head_still_gets_a_join(self):
        """Which stem a box touches is geometry; whether it is a head is
        another decision's question."""
        s = Stem()
        s.head(0, "noteheadBlack", 60, decided=(1.0, 0, 0))
        s.refuse(0)
        s.run()
        self.assertEqual(s.join(0).value, s.row.id)


# ─────────────────────────────────────────────────────────────────────────────
# Q.STEM_VALUE -- Sean's 14 tiles
# ─────────────────────────────────────────────────────────────────────────────

class TestSeansTiles(_Case):

    def test_tile_13_the_dot_belongs_to_the_stem(self):
        """A dotted half and an undotted half on one stem: *"2 dotted half
        notes"*."""
        s = Stem()
        s.head(0, "noteheadHalfInSpace", 60, decided=(3.0, 1, 0))
        s.head(1, "noteheadHalfInSpace", 20, decided=(2.0, 0, 0))
        s.run()
        self.assertValue(s.value(0), 3.0, 1)
        self.assertValue(s.value(1), 3.0, 1)
        self.assertEqual(s.value(1).reason, "stem_value_from_evidence")

    def test_tile_5_a_WHOLE_CLASS_box_on_a_stem_takes_the_stems_value(self):
        """A box classed `noteheadWhole` on a dotted-half chord: *"Dotted half
        notes"*. The whole-class box casts no vote; it takes the stem's."""
        s = Stem()
        s.head(0, "noteheadWholeOnLine", 20, decided=(6.0, 1, 0))
        s.head(1, "noteheadHalfInSpace", 60, decided=(3.0, 1, 0))
        s.run()
        self.assertValue(s.value(0), 3.0, 1)
        self.assertValue(s.value(1), 3.0, 1)

    def test_tile_1_the_beams_are_read_at_the_TIP_not_the_minimum(self):
        """One head counts two strokes, the other one; the stem points UP, so
        its tip is the TOP and the upper head is the one that sees only the tip's
        strokes: *"8th note"*."""
        s = Stem(direction="up")
        s.head(0, "noteheadBlackOnLine", 68, decided=(0.25, 0, 2))   # lower
        s.head(1, "noteheadBlackInSpace", 24, decided=(0.5, 0, 1))   # upper
        s.run()
        self.assertValue(s.value(0), 0.5, 0, 1)
        self.assertValue(s.value(1), 0.5, 0, 1)

    def test_tile_1_CONTROL_the_tip_is_what_reads_it_so_a_DOWN_stem_flips_it(self):
        """The control that can fail: the same two heads on a stem pointing
        DOWN have their tip at the BOTTOM, so the LOWER head's two strokes
        stand. A rule that took the minimum (or the maximum) would not move."""
        s = Stem(direction="down")
        s.head(0, "noteheadBlackOnLine", 68, decided=(0.25, 0, 2))
        s.head(1, "noteheadBlackInSpace", 24, decided=(0.5, 0, 1))
        s.run()
        self.assertValue(s.value(0), 0.25, 0, 2)
        self.assertValue(s.value(1), 0.25, 0, 2)

    def test_tile_14_a_NARROWED_black_box_beside_a_decided_half_takes_the_half(self):
        """*"Half note"*: the black box (narrowed eighth|quarter, a duplicate
        box) is the same note. The decided hollow head's value is the stem's,
        although the narrowing EXCLUDES it."""
        s = Stem()
        s.head(0, "noteheadHalfOnLine", 62, decided=(2.0, 0, 0))
        s.head(1, "noteheadBlackOnLine", 56, narrowed=[(0.5, 0, 1), (1.0, 0, 0)])
        s.run()
        self.assertValue(s.value(0), 2.0)
        self.assertValue(s.value(1), 2.0)
        self.assertTrue(s.value(1).detail["changed"])

    def test_tiles_4_and_8_dotted_half_beside_a_narrowed_black_box(self):
        s = Stem()
        s.head(0, "noteheadHalfInSpace", 62, decided=(3.0, 1, 0))
        s.head(1, "noteheadBlackOnLine", 8, narrowed=[(0.5, 0, 1), (1.0, 0, 0)])
        s.run()
        self.assertValue(s.value(0), 3.0, 1)
        self.assertValue(s.value(1), 3.0, 1)

    def test_tile_2_a_hollow_stem_with_a_BEAMED_black_box_MID_STEM_is_a_half(self):
        """Tile 2's pattern: the stem points DOWN (its tip is the bottom), the
        two hollow heads sit at either side of a small black box that read an
        eighth (a slash's stroke counted as a beam). The tip-most head is hollow,
        so the stroke between the heads is not a beam: *"Half notes"*."""
        s = Stem(direction="down")
        s.head(0, "noteheadHalfInSpace", 8, decided=(2.0, 0, 0))
        s.head(1, "noteheadBlackInSpace", 30, decided=(0.5, 0, 1))
        s.head(2, "noteheadHalfInSpace", 56, decided=(2.0, 0, 0))   # tip-most
        s.run()
        for gi in (0, 1, 2):
            self.assertValue(s.value(gi), 2.0)

    def test_tiles_6_and_7_a_hollow_stem_with_a_DECIDED_quarter_black_box(self):
        """Tiles 6 and 7: a decided black box (quarter, no beam) at the stem's
        tip beside a hollow head is the stem's half: *"Half note with a trem
        slash"*."""
        s = Stem(direction="up")
        s.head(0, "noteheadHalfInSpace", 62, decided=(2.0, 0, 0))
        s.head(1, "noteheadBlackOnLine", 8, decided=(1.0, 0, 0))   # tip-most
        s.run()
        for gi in (0, 1):
            self.assertValue(s.value(gi), 2.0)

    def test_tile_9_the_whole_class_box_must_not_make_a_beamed_stem_a_half(self):
        """A smeared blob boxed `noteheadWhole` and a black head narrowed
        quarter|eighth: Sean read an EIGHTH. With the convention the whole-class
        box casts no vote and the stem stays NARROWED, the answer inside; without
        it the box's hollow reading would have decided a half."""
        s = Stem(direction="down")
        s.head(0, "noteheadBlackOnLine", 6, narrowed=[(1.0, 0, 0), (0.5, 0, 1)])
        s.head(1, "noteheadWholeOnLine", 66, decided=(4.0, 0, 0))
        s.run()
        v = s.value(0)
        self.assertIs(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "stem_levels_unread")
        self.assertEqual({c.value["written"] for c in v.candidates}, {1.0, 0.5})
        self.assertEqual({c.value["written"] for c in s.value(1).candidates},
                         {1.0, 0.5})

    def test_tile_9_CONTROL_the_convention_is_what_decides_it(self):
        """The control that can fail: with the convention OFF the whole-class
        box votes HOLLOW and the same stem is decided a half."""
        old = SV.WHOLE_CLASS_BOX_ON_A_STEM_IS_NOT_WHOLE
        SV.WHOLE_CLASS_BOX_ON_A_STEM_IS_NOT_WHOLE = False
        try:
            s = Stem(direction="down")
            s.head(0, "noteheadBlackOnLine", 6,
                   narrowed=[(1.0, 0, 0), (0.5, 0, 1)])
            s.head(1, "noteheadWholeOnLine", 66, decided=(4.0, 0, 0))
            s.run()
            self.assertValue(s.value(0), 2.0)
        finally:
            SV.WHOLE_CLASS_BOX_ON_A_STEM_IS_NOT_WHOLE = old

    def test_the_controls_10_and_12_stems_that_already_agree_are_untouched(self):
        """Tile 10 (two halves) and tile 12 (two dotted halves) were right and
        must stay so: the stem agrees, nothing changes."""
        for dec in ((2.0, 0, 0), (3.0, 1, 0)):
            s = Stem()
            s.head(0, "noteheadHalfInSpace", 60, decided=dec)
            s.head(1, "noteheadHalfOnLine", 30, decided=dec)
            s.run()
            for gi in (0, 1):
                self.assertValue(s.value(gi), dec[0], dec[1])
                self.assertEqual(s.value(gi).reason, "stem_agrees")
                self.assertFalse(s.value(gi).detail["changed"])


# ─────────────────────────────────────────────────────────────────────────────
# Never refuse by fill alone (T11) -- and what the rule must NOT do
# ─────────────────────────────────────────────────────────────────────────────

class TestKeepTheRealNote(_Case):

    def test_a_filled_box_on_a_hollow_stem_is_KEPT_and_takes_the_value(self):
        """The T11-style control. Sean: a filled box on a half note's stem is not
        a note on 2, 4, 6, 8, 14 (a duplicate or the slash) but IS one on 11 --
        so fill alone never refuses. With NO per-box witness the box stays a
        member, takes the stem's half, and nothing here files a refusal."""
        s = Stem()
        s.head(0, "noteheadHalfOnLine", 62, decided=(2.0, 0, 0))
        s.head(1, "noteheadBlackInSpace", 30, decided=(1.0, 0, 0))
        s.run()
        v = s.value(1)
        self.assertValue(v, 2.0)
        self.assertNotEqual(v.reason, "not_a_member")
        self.assertIsNone(s.log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, s.heads[1]))
        self.assertIsNone(s.log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, s.heads[0]))

    def test_the_heads_own_duration_verdict_is_never_overturned(self):
        s = Stem()
        s.head(0, "noteheadHalfOnLine", 62, decided=(2.0, 0, 0))
        s.head(1, "noteheadBlackInSpace", 30, decided=(1.0, 0, 0))
        before = s.log.verdict(Q.DURATION, s.heads[1])
        s.run()
        now = s.log.verdict(Q.DURATION, s.heads[1])
        self.assertEqual(now.id, before.id)
        self.assertEqual(now.value["written"], 1.0)
        self.assertEqual(s.value(1).value["written"], 2.0)

    def test_a_box_a_decision_REFUSED_is_not_a_member(self):
        """The boxes `notehead_precision` refused (a slash, a duplicate) neither
        vote nor take a value: with one left the stem has a lone head."""
        s = Stem()
        s.head(0, "noteheadHalfOnLine", 62, decided=(2.0, 0, 0))
        s.head(1, "noteheadBlackInSpace", 30, decided=(1.0, 0, 0))
        s.refuse(1)
        s.run()
        self.assertEqual(s.value(1).reason, "not_a_member")
        self.assertEqual(s.value(0).reason, "lone_head")

    def test_another_staffs_copy_is_not_a_member(self):
        s = Stem()
        s.head(0, "noteheadHalfOnLine", 62, decided=(2.0, 0, 0))
        s.head(1, "noteheadBlackInSpace", 30, decided=(1.0, 0, 0))
        s.give_away(1)
        s.run()
        self.assertEqual(s.value(1).reason, "not_a_member")


# ─────────────────────────────────────────────────────────────────────────────
# Rule 8 -- where the stem's own evidence cannot say, NARROW or ABSTAIN
# ─────────────────────────────────────────────────────────────────────────────

class TestWhereItCannotSay(_Case):

    def test_a_genuine_hollow_head_under_a_beam_certain_at_the_tip_NARROWS(self):
        """The tie nothing breaks: a half note's head and a beam that reads
        CERTAIN at the tip (the tip-most head is a decided eighth). Neither is
        picked."""
        s = Stem(direction="up")
        s.head(0, "noteheadHalfInSpace", 68, decided=(2.0, 0, 0))   # base
        s.head(1, "noteheadBlackInSpace", 14, decided=(0.5, 0, 1))  # at the tip
        s.run()
        v = s.value(0)
        self.assertIs(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "hollow_head_on_a_beamed_stem")
        self.assertEqual({c.value["written"] for c in v.candidates}, {2.0, 0.5})
        self.assertIs(s.value(1).outcome, Outcome.NARROWED)

    def test_the_SAME_stem_with_the_beam_at_a_NON_tip_head_does_not_narrow(self):
        """The control: the beamed filled head is NEAR THE HEADS' END, not the
        tip, so its stroke is not a beam -- the stem is a half (tile 2)."""
        s = Stem(direction="up")
        s.head(0, "noteheadBlackInSpace", 68, decided=(0.5, 0, 1))  # base end
        s.head(1, "noteheadHalfInSpace", 14, decided=(2.0, 0, 0))   # tip-most
        s.run()
        self.assertValue(s.value(0), 2.0)
        self.assertValue(s.value(1), 2.0)

    def test_two_dot_counts_NARROW_never_a_vote(self):
        s = Stem()
        s.head(0, "noteheadHalfInSpace", 60, decided=(3.0, 1, 0))
        s.head(1, "noteheadHalfInSpace", 30, decided=(3.5, 2, 0))
        s.run()
        v = s.value(0)
        self.assertIs(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "stem_dots_disagree")

    def test_a_stem_direction_nobody_read_names_no_tip(self):
        """Two filled heads with different levels and NO decided direction: the
        levels are the union, a narrowing, not a pick."""
        s = Stem(direction=None)
        s.head(0, "noteheadBlackOnLine", 68, decided=(0.25, 0, 2))
        s.head(1, "noteheadBlackInSpace", 24, decided=(0.5, 0, 1))
        s.run()
        v = s.value(0)
        self.assertIs(v.outcome, Outcome.NARROWED)
        self.assertEqual({c.value["beam_levels"] for c in v.candidates}, {1, 2})

    def test_every_member_unread_ABSTAINS(self):
        s = Stem()
        s.head(0, "noteheadBlack", 60, abstain=True)
        s.head(1, "noteheadBlack", 30, abstain=True)
        s.run()
        self.assertIs(s.value(0).outcome, Outcome.ABSTAINED)
        self.assertEqual(s.value(0).reason, "stem_unread")

    def test_a_lone_head_has_no_stem_value(self):
        s = Stem()
        s.head(0, "noteheadBlack", 60, decided=(1.0, 0, 0))
        s.run()
        self.assertIs(s.value(0).outcome, Outcome.ABSTAINED)
        self.assertEqual(s.value(0).reason, "lone_head")

    def test_a_head_whose_join_is_NARROWED_has_an_ambiguous_stem(self):
        s = Stem(direction=None)
        _stem(s.log, x=82, y=0, w=4, h=80)
        s.head(0, "noteheadBlack", 60, decided=(1.0, 0, 0))
        s.run()
        self.assertEqual(s.value(0).reason, "ambiguous_stem")


class TestTwoStemsDoNotMix(_Case):

    def test_each_stem_keeps_its_own_value(self):
        s = Stem()
        other = _stem(s.log, x=200, y=0, w=4, h=80)
        s.head(0, "noteheadHalfInSpace", 60, decided=(2.0, 0, 0))
        s.head(1, "noteheadHalfInSpace", 30, decided=(2.0, 0, 0))
        # a second chord on a second stem, eighths
        g2 = R.glyph(0, 0, 0, 0, 2)
        g3 = R.glyph(0, 0, 0, 0, 3)
        for g, y in ((g2, 60), (g3, 30)):
            s.log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                          reader=READERS.DETECTOR, frame="cell:0", score=0.9)
            s.log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 182, y, 20, 16),
                          reader=READERS.DETECTOR, frame="cell:0", score=0.9)
            _v(s.log, g, Q.DURATION, Outcome.DECIDED, _dur(0.5, 0, 1))
            _v(s.log, g, Q.STEM_DIRECTION, Outcome.DECIDED, "up")
        s.run()
        self.assertEqual(s.join(0).value, s.row.id)
        self.assertEqual(s.log.verdict(Q.HEAD_STEM, g2).value, other.id)
        self.assertValue(s.value(0), 2.0)
        self.assertValue(s.log.verdict(Q.STEM_VALUE, g2), 0.5, 0, 1)

    def test_a_heads_own_tuplet_scale_is_kept(self):
        """The stem's WRITTEN value is the stem's; the tuplet a head sits in is
        the head's (`beats` is scaled, `written` is not)."""
        s = Stem()
        g = s.head(0, "noteheadBlack", 60, decided=(0.5, 0, 1))
        s.head(1, "noteheadBlack", 30, decided=(0.5, 0, 1))
        # head 0 sits in a triplet: beats = written * 2/3
        s.log.record(Verdict(
            id=s.log._next_id("vrd"), subject=g, quantity=Q.DURATION,
            outcome=Outcome.DECIDED, value=_dur(0.5, 0, 1, scale=2.0 / 3.0),
            decider="test2", reason="head_and_marks", supersedes=s.log.verdict(
                Q.DURATION, g).id))
        s.run()
        self.assertAlmostEqual(s.value(0).value["beats"], 0.5 * 2.0 / 3.0)
        self.assertAlmostEqual(s.value(0).value["written"], 0.5)
        self.assertAlmostEqual(s.value(1).value["beats"], 0.5)


class TestReadout(_Case):

    def test_a_stem_value_reads_as_a_duration_in_the_stage_readout(self):
        """`readout.human_value` spells a stem's value the way a head's own
        duration is spelled, so `readout show` and the HTML page are readable."""
        from tools.omr.staged import readout
        s = Stem()
        s.head(0, "noteheadHalfInSpace", 60, decided=(3.0, 1, 0))
        s.head(1, "noteheadHalfInSpace", 20, decided=(2.0, 0, 0))
        s.run()
        v = s.value(1).to_json()
        self.assertEqual(readout.human_value(Q.STEM_VALUE, v),
                         readout.human_value(Q.DURATION, {
                             "outcome": "decided", "value": _dur(3.0, 1, 0)}))
        self.assertNotIn("{", readout.human_value(Q.STEM_VALUE, v))


class TestRegistration(unittest.TestCase):

    def test_both_decisions_are_registered_and_ordered(self):
        order = adjudicate.ORDER
        self.assertIn(Q.HEAD_STEM, adjudicate.REGISTRY)
        self.assertIn(Q.STEM_VALUE, adjudicate.REGISTRY)
        self.assertLess(order.index(Q.DURATION), order.index(Q.HEAD_STEM))
        self.assertLess(order.index(Q.HEAD_STEM), order.index(Q.STEM_VALUE))
        self.assertLess(order.index(Q.STEM_VALUE), order.index(Q.EVENT))

    def test_the_convention_is_named_and_on(self):
        self.assertTrue(SV.WHOLE_CLASS_BOX_ON_A_STEM_IS_NOT_WHOLE)


if __name__ == "__main__":
    unittest.main()
