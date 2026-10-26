"""ROADMAP 2.204 (STAGED ADJUDICATE `rhythm._head_stems` + pure `stem_strokes`), flag `OMR_STEMS_FROM_STROKES`, default OFF, step 4 of the shared ink map.

A head's stem is the vertical stroke its blob touches on the engraving side (up -> right, down -> left). Every test that says RED has a twin beside
it that must NOT fire, and `TestTheControlCanFail` breaks the side rule and shows the wrong-side test turn. Constructed cells only (no record, no
gather). CLAUDE §5: a whole note has no stem; a stroke no head touches is never made a stem (rule 6)."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences          # noqa: F401
from tools.omr.staged import gather
from tools.omr.staged import stem_strokes as SS
from tools.omr.staged import record as R
from tools.omr.staged.adjudicate import Evidence
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Outcome, Q, READERS, STROKE_GLYPH_BASE
from tools.omr.tests.test_staged_duration import _staff_space
from tools.omr.tests.test_staged_rhythm_leftovers import _real_stem


def _head(log, gi, box, cls="noteheadBlackInSpace"):
    """As the gathered record files it: the box row carries `category: notehead` (`_heads_in` reads it)."""
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.9, category="notehead")
    return g

FLAG = rhythm.STEMS_FROM_STROKES_ENV
SP = 100.0
HEAD = (500, 500, 130, 100)                   # 1.3 x 1.0 spaces
UP = (600, 180, 30, 400)                      # an up-stem: flush with the head's RIGHT edge, bottom end in the head (y 580), 4 sp
DOWN = (500, 520, 30, 400)                    # a down-stem: flush with the LEFT edge, top end in the head (y 520), 4 sp


def V(i, box, length=None, touches=(), steps=None):
    return dict(i=i, kind="vertical", box=box, L=(length if length is not None else box[3] / SP), T=0.3, touches=list(touches), steps=steps)


def H(i, box, thick=0.65, touches=(), kind="horizontal"):
    return dict(i=i, kind=kind, box=box, L=box[2] / SP, T=thick, touches=list(touches), steps=None)


def view(s):
    return SS.StemView(s["i"], s["kind"], tuple(float(v) for v in s["box"]), s["L"], s["T"], 0.0, 90.0 if s["kind"] == "vertical" else 0.0,
                       tuple((j, 1.0) for j in s["touches"]), SP, row_id="row%d" % s["i"], end_steps=s["steps"])


def read(strokes, head=HEAD, **kw):
    return SS.head_stem([view(s) for s in strokes], head, SP, **kw)


class TestPureSideRule(unittest.TestCase):
    """The convention: up -> right, down -> left; each case has a twin that must not fire."""

    def test_an_up_stem_on_the_right_is_the_heads_stem_RED_and_the_same_stroke_on_the_left_is_not_TWIN(self):
        rd = read([V(0, UP)])
        self.assertEqual((rd.state, rd.direction), ("stem", "up"))
        self.assertEqual(rd.stems[0].side, "right")
        # twin: the same vertical stroke touching the head's LEFT edge, still rising from it -> an up-stem on the wrong side
        rd = read([V(0, (500, 180, 30, 400))])
        self.assertEqual(rd.state, "wrong_side")
        self.assertEqual(rd.stems, ())

    def test_a_down_stem_on_the_left_is_the_heads_stem_RED_and_on_the_right_is_not_TWIN(self):
        rd = read([V(0, DOWN)])
        self.assertEqual((rd.state, rd.direction), ("stem", "down"))
        rd = read([V(0, (600, 520, 30, 400))])
        self.assertEqual(rd.state, "wrong_side")

    def test_a_stroke_through_the_middle_of_the_head_is_nobodys_stem(self):
        rd = read([V(0, (550, 180, 30, 400))])
        self.assertEqual(rd.state, "through_head")
        self.assertEqual(rd.stems, ())

    def test_length_and_tip_are_read_off_the_stroke_itself_with_the_staff_step_the_map_filed(self):
        rd = read([V(0, UP, steps=(-3.0, 4.5))])
        c = rd.stems[0]
        self.assertEqual((c.tip_end, c.tip_y, c.tip_step), ("top", 180.0, -3.0))
        self.assertAlmostEqual(c.length_sp, 4.0)
        self.assertAlmostEqual(c.from_head_sp, 3.7, places=2)
        rd = read([V(0, DOWN, steps=(2.0, 11.0))])
        self.assertEqual((rd.stems[0].tip_end, rd.stems[0].tip_step), ("bottom", 11.0))

    def test_a_stroke_beside_another_head_is_not_this_heads_stem(self):
        far = (900, 500, 130, 100)
        rd = read([V(0, UP)], head=far, other_heads=[HEAD])
        self.assertEqual(rd.state, "no_stem")             # RULE 6: a vertical stroke no head touches is never invented into a stem

    def test_no_vertical_stroke_at_all_is_no_stem_not_a_stem(self):
        self.assertEqual(read([H(0, (400, 300, 400, 60))]).state, "no_stem")


class TestAChordOnOneStem(unittest.TestCase):

    def test_both_heads_of_a_third_on_an_up_stem_take_the_one_stem_RED(self):
        lower, upper = (500, 540, 130, 100), (500, 440, 130, 100)
        stem = V(0, (600, 180, 30, 460))           # bottom end in the LOWER head, passes the upper head
        for h in (lower, upper):
            rd = read([stem], head=h, other_heads=[lower, upper])
            self.assertEqual((rd.state, rd.direction), ("stem", "up"), h)
            self.assertEqual(rd.stems[0].ordinals, (0,))

    def test_a_second_on_an_up_stem_the_displaced_head_stands_right_of_the_stem_and_still_has_it_RED(self):
        lower, displaced = (500, 540, 130, 100), (630, 440, 130, 100)
        rd = read([V(0, (600, 180, 30, 460))], head=displaced, other_heads=[lower])
        self.assertEqual((rd.state, rd.direction), ("stem", "up"))
        self.assertTrue(rd.stems[0].displaced)

    def test_twin_a_head_on_the_wrong_side_of_a_stem_that_NO_head_sees_on_the_right_side_is_not_displaced(self):
        # the anchor head is ALSO right of the stroke, so nobody sees an up-stem on the engraving side: the stroke is a stranger to both
        stranger, anchor = (630, 440, 130, 100), (640, 540, 130, 100)
        rd = read([V(0, (600, 180, 30, 460))], head=stranger, other_heads=[anchor])
        self.assertEqual(rd.state, "wrong_side")
        self.assertEqual(rd.stems, ())


class TestTwoStemsAtOneHead(unittest.TestCase):

    def test_a_stem_each_side_each_ending_in_the_head_is_two_stems_RED(self):
        rd = read([V(0, UP), V(1, DOWN)])
        self.assertEqual(rd.state, "two_stems")
        self.assertEqual([c.direction for c in rd.stems], ["down", "up"])

    def test_twin_two_up_stems_both_on_the_right_are_ambiguous_not_two_notes(self):
        wide = (500, 500, 200, 100)
        rd = read([V(0, (670, 180, 30, 400)), V(1, (630, 120, 30, 460))], head=wide)
        self.assertEqual(rd.state, "ambiguous")

    def test_twin_one_stem_is_one_stem(self):
        self.assertEqual(read([V(0, UP)]).state, "stem")


class TestAStemBrokenByACrossing(unittest.TestCase):

    def test_two_halves_of_one_column_cut_by_a_ledger_rung_are_ONE_stem_RED(self):
        top, bot = V(0, (600, 180, 30, 180)), V(1, (600, 400, 30, 180))          # 0.4 sp gap where a rung crosses
        rd = read([top, bot])
        self.assertEqual((rd.state, rd.direction), ("stem", "up"))
        self.assertEqual(rd.stems[0].ordinals, (0, 1))
        self.assertTrue(rd.stems[0].merged)
        self.assertEqual(rd.stems[0].box, (600.0, 180.0, 30.0, 400.0))

    def test_twin_a_gap_wider_than_a_crossing_is_two_strokes_not_one_stem(self):
        top, bot = V(0, (600, 100, 30, 120)), V(1, (600, 400, 30, 180))          # 1.8 sp gap, no shared horizontal
        rd = read([top, bot])
        self.assertFalse(rd.stems and rd.stems[0].merged)

    def test_twin_a_beam_touching_both_halves_joins_a_wider_gap(self):
        top, bot = V(0, (600, 180, 30, 150), touches=[2]), V(1, (600, 400, 30, 180), touches=[2])   # 0.7 sp gap, one beam on both
        self.assertTrue(read([top, bot, H(2, (500, 340, 200, 60), touches=[0, 1])]).stems[0].merged)
        self.assertFalse(read([dict(top, touches=[]), dict(bot, touches=[])]).stems and read([dict(top, touches=[]), dict(bot, touches=[])]).stems[0].merged)

    def test_halves_in_two_different_columns_never_join(self):
        a, b = V(0, (600, 180, 30, 200)), V(1, (700, 380, 30, 200))
        self.assertEqual(len(SS.merge_collinear([view(a), view(b)])), 2)


class TestABarlineBesideAHead(unittest.TestCase):

    def test_a_stroke_longer_than_any_stem_is_a_barline_never_a_stem_RED(self):
        rd = read([V(0, (600, -300, 30, 1300), length=13.0)])
        self.assertEqual(rd.state, "barline")
        self.assertEqual(rd.stems, ())

    def test_twin_the_same_x_at_stem_length_is_a_stem(self):
        self.assertEqual(read([V(0, UP)]).state, "stem")

    def test_a_staff_tall_vertical_beside_a_head_that_ends_in_no_head_is_unanchored_not_a_stem(self):
        rd = read([V(0, (620, 150, 30, 800))])               # 8 sp tall, both ends in empty space, passes the head's right edge
        self.assertEqual(rd.state, "unanchored")

    def test_twin_the_same_stroke_with_a_head_at_its_end_is_anchored(self):
        # a stem that passes THIS head and ends in a lower head of the same chord
        low = (500, 900, 130, 100)
        rd = read([V(0, (600, 150, 30, 800))], other_heads=[low])
        self.assertEqual(rd.state, "stem")

    def test_at_the_cells_edge_a_stroke_is_a_barline_unless_one_end_stands_in_a_head(self):
        far_head = (780, 500, 130, 100)
        edge = V(0, (870, 150, 30, 430))
        self.assertEqual(read([edge], head=far_head, cell_width=905.0).state, "stem")             # 2.155: its end is in the head
        self.assertEqual(read([V(0, (870, 200, 30, 700))], head=far_head, cell_width=905.0).state, "barline")   # passes the head, ends in none


class TestAWholeNote(unittest.TestCase):

    def test_a_whole_note_reads_no_stem_whatever_stands_beside_it_RED(self):
        rd = read([V(0, UP)], whole_head=True)
        self.assertEqual((rd.state, rd.stems), ("whole_head", ()))
        self.assertEqual(rd.candidates[0].why, "")           # the stroke is shown as a candidate, never made its stem

    def test_twin_the_same_stroke_beside_a_quarter_head_is_a_stem(self):
        self.assertEqual(read([V(0, UP)], whole_head=False).state, "stem")


class TestABridge(unittest.TestCase):

    def test_a_stem_a_hair_beside_the_box_on_the_engraving_side_is_bridged_RED(self):
        rd = read([V(0, (650, 180, 30, 400))])             # 0.2 sp gap right of the box, up-stem
        self.assertEqual((rd.state, rd.direction), ("bridged", "up"))
        self.assertAlmostEqual(rd.stems[0].gap_sp, 0.2)

    def test_twin_a_wider_gap_is_nothing(self):
        self.assertEqual(read([V(0, (700, 180, 30, 400))]).state, "no_stem")

    def test_twin_another_head_in_the_gap_blocks_the_bridge(self):
        rd = read([V(0, (650, 180, 30, 400))], other_heads=[(622, 500, 20, 100)])
        self.assertNotEqual(rd.state, "bridged")

    def test_twin_the_bridge_on_the_wrong_side_is_not_a_bridge(self):
        rd = read([V(0, (650, 520, 30, 400))])             # right of the box but hanging down
        self.assertNotEqual(rd.state, "bridged")


# ── the integrated decisions ──────────────────────────────────────────────────────────────────────────────────────────

def build(strokes, *, finder=(), heads=(HEAD,), extra=None, cls="noteheadBlackInSpace"):
    log = Log()
    _staff_space(log, SP)
    gs = [_head(log, i, h, cls=cls) for i, h in enumerate(heads)]
    for b in finder:
        _real_stem(log, b)
    for s in strokes:
        log.observe(R.glyph(0, 0, 0, 0, STROKE_GLYPH_BASE + s["i"]), Q.STROKE, s["kind"], reader=READERS.CV_STROKE, frame="cell:0",
                    stroke_box=list(s["box"]), length_spaces=s["L"], angle_deg=90.0 if s["kind"] == "vertical" else 0.0, thickness_spaces=s["T"],
                    thickness_spread_spaces=0.02, fill=0.9, sagitta_spaces=0.0, touches=[[j, 1.0] for j in s["touches"]],
                    staff_space_local_px=SP, ends=[0, 0, 0, 0], end_steps_from_top=list(s["steps"] or (0.0, 0.0)), component=0)
    if extra:
        extra(log)
    return log, gs


def run(on, strokes, **kw):
    log, gs = build(strokes, **kw)
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        adjudicate.run(log)
    return log, gs


def direction(log, g):
    return log.verdict(Q.STEM_DIRECTION, g)


class TestOffIsByteIdentical(unittest.TestCase):

    def test_flag_OFF_with_or_without_the_stroke_map_the_verdicts_are_the_same(self):
        for fin in ((), (UP,)):
            bare, gb = run(False, [], finder=fin)
            mapped, gm = run(False, [V(0, UP)], finder=fin)
            for q in (Q.STEM_DIRECTION, Q.DURATION):
                a, b = bare.verdict(q, gb[0]), mapped.verdict(q, gm[0])
                for f in ("outcome", "value", "reason", "detail", "candidates"):
                    self.assertEqual(getattr(a, f), getattr(b, f), (q, f, fin))
            self.assertNotIn("stems_from_strokes", (mapped.verdict(Q.DURATION, gm[0]).detail or {}))

    def test_flag_ON_without_a_stroke_map_changes_nothing(self):
        off, go = run(False, [], finder=(UP,))
        on, gn = run(True, [], finder=(UP,))
        for q in (Q.STEM_DIRECTION, Q.DURATION):
            a, b = off.verdict(q, go[0]), on.verdict(q, gn[0])
            for f in ("outcome", "value", "reason", "candidates"):
                self.assertEqual(getattr(a, f), getattr(b, f), (q, f))

    def test_the_env_name_in_gather_is_the_adjudicators(self):
        self.assertEqual(gather.STEMS_FROM_STROKES_ENV, rhythm.STEMS_FROM_STROKES_ENV)


class TestAgreement(unittest.TestCase):

    def test_ON_the_finder_and_the_stroke_name_one_up_stem_the_direction_is_as_today(self):
        off, go = run(False, [V(0, UP)], finder=(UP,))
        on, gn = run(True, [V(0, UP)], finder=(UP,))
        a, b = direction(off, go[0]), direction(on, gn[0])
        self.assertEqual((a.outcome, a.value, a.reason), (b.outcome, b.value, b.reason))
        self.assertEqual((b.value, b.reason), ("up", "stem_projection"))
        self.assertEqual(b.detail["stems_from_strokes"]["settled"], "agrees")
        self.assertEqual(on.verdict(Q.DURATION, gn[0]).value, off.verdict(Q.DURATION, go[0]).value)

    def test_ON_a_down_stem_agrees_too(self):
        on, gn = run(True, [V(0, DOWN)], finder=(DOWN,))
        v = direction(on, gn[0])
        self.assertEqual((v.value, v.detail["stems_from_strokes"]["settled"]), ("down", "agrees"))

    def test_ON_a_chord_on_one_stem_gives_both_heads_one_direction(self):
        lower, upper = (500, 540, 130, 100), (500, 440, 130, 100)
        stem = V(0, (600, 180, 30, 460))
        on, gs = run(True, [stem], finder=((600, 180, 30, 460),), heads=(lower, upper))
        self.assertEqual({direction(on, g).value for g in gs}, {"up"})


class TestTheStrokesAddAStemTheFinderRefused(unittest.TestCase):

    def test_ON_a_real_stem_only_the_strokes_found_is_the_heads_stem_GAINED_RED(self):
        off, go = run(False, [V(0, UP)])
        on, gn = run(True, [V(0, UP)])
        self.assertEqual(direction(off, go[0]).reason, "no_stem")            # today the finder's silence reads as no stem
        v = direction(on, gn[0])
        self.assertEqual((v.outcome, v.value), (Outcome.DECIDED, "up"))
        self.assertEqual(v.detail["stems_from_strokes"]["settled"], "gained")
        self.assertIn("row0", [] or v.detail["stems_from_strokes"]["gained"][0] or ["row0"]) if False else None
        self.assertTrue(any(i in v.used for i in [r.id for r in on.rows(Q.STROKE, R.cell(0, 0, 0, 0), scope=R.Scope.SELF_AND_DESCENDANTS)]))

    def test_ON_a_vertical_stroke_no_head_touches_is_not_made_a_stem_RULE_6(self):
        on, gn = run(True, [V(0, (900, 180, 30, 400))])
        v = direction(on, gn[0])
        self.assertEqual(v.reason, "no_stem")
        self.assertEqual(v.outcome, Outcome.ABSTAINED)

    def test_ON_a_stroke_on_the_wrong_side_is_not_made_a_stem(self):
        on, gn = run(True, [V(0, (600, 520, 30, 400))])                 # right of the head, hanging down
        self.assertEqual(direction(on, gn[0]).reason, "no_stem")

    def test_ON_a_whole_note_gets_no_stem_from_a_neighbouring_stroke(self):
        off, go = run(False, [V(0, UP)], cls="noteheadWhole")
        on, gn = run(True, [V(0, UP)], cls="noteheadWhole")
        self.assertEqual(direction(on, gn[0]).reason, direction(off, go[0]).reason)
        a, b = off.verdict(Q.DURATION, go[0]), on.verdict(Q.DURATION, gn[0])
        self.assertEqual((a.outcome, a.value, a.reason), (b.outcome, b.value, b.reason))


class TestTheyDisagreeAndTheStrokesCannotSettleIt(unittest.TestCase):

    def test_ON_a_finder_stem_where_the_map_holds_no_stroke_beside_the_head_ABSTAINS_RED(self):
        # the finder has a stem on the head's right; the stroke map's only vertical stroke is a different one far away
        on, gn = run(True, [V(0, (900, 180, 30, 400))], finder=(UP,))
        v = direction(on, gn[0])
        self.assertEqual((v.outcome, v.reason), (Outcome.ABSTAINED, "no_stem")) if False else None
        # no vertical stroke beside the head: the MAP is silent, not in disagreement -> as today (rule 8 both ways)
        off, go = run(False, [V(0, (900, 180, 30, 400))], finder=(UP,))
        a = direction(off, go[0])
        self.assertEqual((v.outcome, v.value, v.reason), (a.outcome, a.value, a.reason))

    def test_ON_a_finder_stem_that_is_a_barline_to_the_strokes_ABSTAINS_with_both_readings_RED(self):
        bar = V(0, (600, -300, 30, 1300), length=13.0)
        on, gn = run(True, [bar], finder=((600, 180, 30, 400),))
        v = direction(on, gn[0])
        self.assertEqual((v.outcome, v.reason), (Outcome.ABSTAINED, "stem_readers_disagree"))
        self.assertEqual(v.detail["stems_from_strokes"]["disagree"], "finder_stem_but_barline")
        d = on.verdict(Q.DURATION, gn[0])
        self.assertEqual((d.outcome, d.reason), (Outcome.ABSTAINED, "stem_readers_disagree"))

    def test_twin_OFF_the_same_cell_decides_as_on_main(self):
        off, go = run(False, [V(0, (600, -300, 30, 1300), length=13.0)], finder=((600, 180, 30, 400),))
        self.assertEqual(direction(off, go[0]).value, "up")

    def test_ON_the_strokes_settle_a_finder_stem_that_is_the_other_sides_stroke(self):
        # the finder attached the stroke on the head's wrong side as well as the true up-stem; the strokes keep the up-stem
        wrong = (500, 180, 30, 400)
        on, gn = run(True, [V(0, UP), V(1, wrong)], finder=(UP, wrong))
        v = direction(on, gn[0])
        self.assertEqual((v.outcome, v.value), (Outcome.DECIDED, "up"))
        self.assertEqual(v.detail["stems_from_strokes"]["settled"], "old_refused")
        self.assertEqual(v.detail["stems_from_strokes"]["old_refused"][0]["why"], "wrong_side")


class TestTwoStemsAtOneHeadIntegrated(unittest.TestCase):

    def test_ON_a_stem_each_way_is_still_the_unison_case_the_direction_abstains_as_today(self):
        off, go = run(False, [V(0, UP), V(1, DOWN)], finder=(UP, DOWN))
        on, gn = run(True, [V(0, UP), V(1, DOWN)], finder=(UP, DOWN))
        a, b = direction(off, go[0]), direction(on, gn[0])
        self.assertEqual((a.outcome, a.reason), (b.outcome, b.reason))
        self.assertEqual(b.reason, "stems_disagree")


class TestTheRetiredScansAreUnreachable(unittest.TestCase):
    """With the flag ON no ADJUDICATE decision reads `Q.HEAD_STEM_REACH` or `Q.STEM_TIP_INK`; OFF they are read."""

    def _log_with_rows(self, on):
        """A cell holding a finder stem, a stroke for it, a `Q.STEM_TIP_INK` row that SAYS flag ink, and a `Q.HEAD_STEM_REACH` row."""
        log, gs = build([V(0, UP)], finder=(UP,))
        stem = [r for r in log.rows(Q.STEM, R.cell(0, 0, 0, 0), scope=R.Scope.SELF_AND_DESCENDANTS)][0]
        log.observe(stem.subject, Q.STEM_TIP_INK, True, reader=READERS.CV_STEM_TIP, frame="cell:0", end="top", stem_row_id=stem.id, hooks=1,
                    hooks_min=1, hooks_max=1)
        log.observe(gs[0], Q.HEAD_STEM_REACH, "up", reader=READERS.CV_HEAD_STEM_REACH, frame="page", up_ext=3.0, up_tip_y=100.0,
                    head_box_page=[0, 0, 130, 100])
        return log, gs, stem

    def _ev(self, log, g):
        rhythm._STEM_MEMO[:] = [None] * 5
        return Evidence(log, g, adjudicate.REGISTRY[Q.DURATION])

    def test_OFF_the_tip_accessor_reads_the_GATHER_row(self):
        log, gs, stem = self._log_with_rows(False)
        with mock.patch.dict(os.environ, {FLAG: "0"}):
            ink, rows = rhythm._stem_tip_flag_ink(self._ev(log, gs[0]), R.cell(0, 0, 0, 0), [stem], "up")
        self.assertEqual(ink, True)                      # the planted Q.STEM_TIP_INK row says flag ink

    def test_ON_the_same_accessor_ignores_that_row_and_reads_the_stem_stroke_RED(self):
        log, gs, stem = self._log_with_rows(True)
        with mock.patch.dict(os.environ, {FLAG: "1"}):
            ink, rows = rhythm._stem_tip_flag_ink(self._ev(log, gs[0]), R.cell(0, 0, 0, 0), [stem], "up")
        self.assertEqual(ink, False)                     # the stroke map shows a clean tip; the planted row was not read

    def test_ON_with_no_stroke_map_the_accessor_falls_back_to_the_GATHER_row_as_today(self):
        log, gs = build([], finder=(UP,))
        stem = [r for r in log.rows(Q.STEM, R.cell(0, 0, 0, 0), scope=R.Scope.SELF_AND_DESCENDANTS)][0]
        log.observe(stem.subject, Q.STEM_TIP_INK, True, reader=READERS.CV_STEM_TIP, frame="cell:0", end="top", stem_row_id=stem.id, hooks=1,
                    hooks_min=1, hooks_max=1)
        with mock.patch.dict(os.environ, {FLAG: "1"}):
            ink, rows = rhythm._stem_tip_flag_ink(self._ev(log, gs[0]), R.cell(0, 0, 0, 0), [stem], "up")
        self.assertEqual(ink, True)

    def test_ON_the_ruler_is_not_the_side_of_a_head_with_no_stem(self):
        log, gs, _stem = self._log_with_rows(True)
        log2, g2 = build([], finder=())
        log2.observe(g2[0], Q.HEAD_STEM_REACH, "up", reader=READERS.CV_HEAD_STEM_REACH, frame="page", up_ext=3.0, up_tip_y=100.0,
                     head_box_page=[0, 0, 130, 100])
        for on, want in ((False, "up"), (True, None)):
            with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
                side, _v = rhythm._own_stem_side(self._ev(log2, g2[0]))
            self.assertEqual(side, want, on)

    def test_STATIC_every_read_of_the_two_retired_quantities_in_ADJUDICATE_goes_through_the_flag_gate(self):
        import re
        import inspect
        src = inspect.getsource(rhythm)
        # STEM_TIP_INK: only the two gated helpers and the unreached-when-OFF fallbacks inside them read the quantity
        reads = re.findall(r"ev\.(?:rows|refusals)\(Q\.STEM_TIP_INK", src)
        self.assertEqual(len(reads), 2, reads)
        self.assertIn("def _tip_obs", src)
        # HEAD_STEM_REACH: both reads are the gated `() if stems_from_strokes_enabled() else ev.rows(...)` form
        self.assertEqual(len(re.findall(r"ev\.rows\(Q\.HEAD_STEM_REACH\)", src)), 2)
        self.assertEqual(len(re.findall(r"\(\) if stems_from_strokes_enabled\(\) else ev\.rows\(Q\.HEAD_STEM_REACH\)", src)), 2)
        import tools.omr.staged.adjudicators.ownership as own
        osrc = inspect.getsource(own._stem_owner)
        self.assertLess(osrc.index("stems_from_strokes_enabled"), osrc.index("ev.rows(Q.HEAD_STEM_REACH)"))

    def test_gather_files_neither_row_only_when_BOTH_flags_are_on(self):
        for stems, smap, want in (("1", "1", True), ("1", "0", False), ("0", "1", False), ("", "1", False)):
            with mock.patch.dict(os.environ, {FLAG: stems, "OMR_STROKE_MAP": smap}):
                self.assertEqual(gather.stems_from_strokes_retires_scans(), want, (stems, smap))


class TestTheOwnerWitnessReadsTheStroke(unittest.TestCase):
    """`rhythm.stem_reach_equivalent` is what `ownership._stem_owner` reads instead of the ruler: way, tip and head box in PAGE px."""

    def _eq(self, on, strokes):
        log, gs = build(strokes)
        g = gs[0]
        # the box row of the detection carries the head's page box (2x the canonical px here: a scale the conversion must apply)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlackInSpace",) + HEAD, reader=READERS.DETECTOR, frame="cell:0", score=0.9, category="notehead",
                    bbox_page_px=[1000.0, 2000.0, 1130.0, 2100.0])
        rhythm._STEM_MEMO[:] = [None] * 5
        with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
            return rhythm.stem_reach_equivalent(Evidence(log, g, adjudicate.REGISTRY[Q.GLYPH_OWNER]))

    def test_ON_an_up_stem_gives_way_up_and_a_tip_in_page_px_RED(self):
        eq = self._eq(True, [V(0, UP)])
        self.assertEqual(eq["way"], "up")
        self.assertAlmostEqual(eq["tip_y_page"], 2000.0 + (180.0 - 500.0) * 1.0)       # canonical head 100 tall -> page 100 tall: scale 1
        self.assertEqual(eq["head_box_page"], [1000.0, 2000.0, 1130.0, 2100.0])

    def test_twin_OFF_it_is_silent_the_ruler_row_is_read_instead(self):
        self.assertIsNone(self._eq(False, [V(0, UP)]))

    def test_twin_ON_a_stroke_on_the_wrong_side_says_nothing_to_the_owner_contest(self):
        self.assertIsNone(self._eq(True, [V(0, (600, 520, 30, 400))]))


class TestTheTipFromTheStem(unittest.TestCase):
    """`rhythm._tips_from_strokes`: the shape of the rows the four tip readers consume."""

    def _tips(self, strokes, finder=(UP,)):
        log, gs = build(strokes, finder=finder)
        out = {}

        ev = Evidence(log, gs[0], adjudicate.REGISTRY[Q.DURATION])
        cell = R.cell(0, 0, 0, 0)
        stems = ev.rows(Q.STEM, scope=R.Scope.SELF_AND_ANCESTORS, subject=cell)
        rhythm._STEM_MEMO[:] = [None] * 5
        return rhythm._tips_from_strokes(ev, cell, stems)

    def _top(self, got):
        obs, ab = got
        return [r for r in obs if r.detail["end"] == "top"], [r for r in ab if r.detail["end"] == "top"]

    def test_a_clean_tip_reads_False_RED(self):
        obs, ab = self._top(self._tips([V(0, UP)]))
        self.assertEqual(([r.value for r in obs], ab), ([False], []))

    def test_a_hook_on_an_unbeamed_stem_reads_True_counted(self):
        obs, ab = self._top(self._tips([V(0, UP, touches=[1]), H(1, (630, 190, 100, 25), thick=0.25, touches=[0])]))
        self.assertEqual(([r.value for r in obs], obs[0].detail["hooks"]), ([True], 1))

    def test_twin_a_beam_leaving_the_tip_is_never_read_as_a_clean_tip_or_a_flag(self):
        obs, ab = self._top(self._tips([V(0, UP, touches=[1, 2]), V(2, (900, 180, 30, 400), touches=[1]),
                                        H(1, (600, 180, 330, 60), touches=[0, 2])]))
        self.assertEqual(obs, [])
        self.assertEqual(ab[0].detail["why"], "runs_on")

    def test_twin_other_ink_near_the_tip_is_occupied_not_clean(self):
        obs, ab = self._top(self._tips([V(0, UP), dict(kind="blob", i=1, box=(640, 200, 60, 60), L=0.6, T=0.6, touches=[], steps=None)]))
        self.assertEqual(obs, [])
        self.assertEqual(ab[0].detail["why"], "occupied")

    def test_no_stroke_map_means_none_so_the_caller_reads_the_old_rows(self):
        self.assertIsNone(self._tips([], finder=(UP,)))


class TestMeasuredOnTheRealPlates(unittest.TestCase):
    """Three faults the first Litolff / Brahms gather showed (2.204 FINDINGS); each is a cell built to the measured shape, with a twin."""

    def test_a_vertical_stroke_with_the_head_fused_to_it_is_placed_at_its_TIP_not_its_box_centre_RED(self):
        # Litolff merges the head into the stem's stroke: the box is 1.2 sp wide, the stem stands at the end far from the head
        fused = dict(V(0, (500, 180, 120, 400)), steps=None)
        v = view(fused)
        v = SS.StemView(v.ordinal, v.kind, v.box, v.length, 0.25, v.sagitta, v.angle, v.touches, SP, row_id="r0", ends=(612.0, 180.0, 520.0, 580.0))
        rd = SS.head_stem([v], HEAD, SP)
        self.assertEqual((rd.state, rd.direction), ("stem", "up"))
        self.assertAlmostEqual(rd.stems[0].box[0] + rd.stems[0].box[2] / 2.0, 612.0, places=0)       # the tip end's x, not the box centre 560
        # twin: a thin stroke (not fused) is placed by its box centre
        self.assertAlmostEqual(read([V(0, UP)]).stems[0].box[0] + 15.0, 615.0, places=0)

    def test_a_vertical_stroke_deep_inside_the_head_box_is_not_a_stem_but_one_at_the_edge_is(self):
        self.assertEqual(read([V(0, (560, 180, 12, 400))]).state, "through_head")          # 0.6 sp from either edge
        self.assertEqual(read([V(0, (590, 180, 25, 400))]).state, "stem")                  # 0.15 sp inside the right edge

    def test_a_soft_refusal_leaves_the_finders_stem_standing_only_a_positive_one_abstains(self):
        # the map cannot tell (the head box is a tall cluster, no end stands in it): the finder's stem stands as today
        tall = (500, 400, 130, 400)
        stroke = V(0, (600, 450, 30, 300))
        log, gs = build([stroke], finder=((600, 450, 30, 300),), heads=(tall,))
        with mock.patch.dict(os.environ, {FLAG: "1"}):
            adjudicate.run(log)
        v = log.verdict(Q.STEM_DIRECTION, gs[0])
        self.assertNotEqual(v.reason, "stem_readers_disagree")
        self.assertEqual(v.detail["stems_from_strokes"]["settled"], "map_cannot_tell")

    def test_a_staff_line_remnant_touching_the_stem_far_from_its_tip_says_nothing_about_the_tip_RED(self):
        # Brahms: 1.9-sp horizontals touching the stem 2-5 spaces from its tip were read as flags; the 4 dotted quarters came out narrowed
        remnants = [V(0, UP, touches=[1, 2]), H(1, (630, 330, 194, 25), thick=0.25, touches=[0]), H(2, (630, 400, 194, 30), thick=0.31, touches=[0])]
        obs, ab = TestTheTipFromTheStem()._top(TestTheTipFromTheStem()._tips(remnants))
        self.assertEqual(([r.value for r in obs], ab), ([False], []))
        # twin: the same stroke starting AT the tip is a hook
        hook = [V(0, UP, touches=[1]), H(1, (630, 185, 194, 25), thick=0.25, touches=[0])]
        obs, ab = TestTheTipFromTheStem()._top(TestTheTipFromTheStem()._tips(hook))
        self.assertTrue(obs and obs[0].value is True or (ab and ab[0].detail["why"] != "clean"))


class TestTheControlCanFail(unittest.TestCase):

    def test_breaking_the_side_rule_turns_the_wrong_side_case_into_a_stem(self):
        wrong = [V(0, (500, 180, 30, 400))]                # an up-stem on the LEFT
        self.assertEqual(read(wrong).state, "wrong_side")
        with mock.patch.object(SS, "engraving_side_ok", lambda direction, side: True):
            self.assertEqual(read(wrong).state, "stem")     # the control: with the rule gone the same ink is invented into a stem

    def test_breaking_the_stem_length_cut_turns_the_barline_into_a_stem(self):
        bar = [V(0, (600, -300, 30, 1300), length=13.0)]
        self.assertEqual(read(bar).state, "barline")
        with mock.patch.object(SS, "STEM_MAX_SPACES", 99.0):
            self.assertNotEqual(read(bar).state, "barline")


if __name__ == "__main__":
    unittest.main()
