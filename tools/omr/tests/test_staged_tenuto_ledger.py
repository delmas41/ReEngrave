"""ROADMAP 2.84 -- a LEDGER LINE the detector boxed as a tenuto is not an
articulation (STAGED, ADJUDICATE, `adjudicate_articulation_is_not_an_
articulation`).

Sean, 2026-10-10: *"handle ledger lines read as articulations - tenuto vs
ledger lines. There will never be another ledger line or note above a
tenuto... right?"* -- and the 2.12f round-2 tiles 1, 4 and 7, which he
answered "Ledger line". The convention in its general form: a ledger line
lies between a staff and its note -- a notehead stands ON it or FARTHER from
that staff in its column -- while an articulation outside the staff lies
BEYOND its note. "Its staff" is the staff that OWNS the head
(`Q.GLYPH_OWNER`), because a padded cell holds the neighbour staff's ledgers
too (the whole-movement census: 23 of 30 Brahms tenuto boxes are ledgers
whose note is staffward of the staff they are filed on).

⚠️ RUN RED FIRST against `origin/main` `40ab373a` (the decision was human-only
and never read a head or a staff): every `True` / abstain test below failed
there with `False` / `articulation`, and the ORDER test failed because the
decision ran before `Q.GLYPH_OWNER`. Every refusal has a positive control in
the same class -- a real tenuto beyond its note, above and below the staff.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS, Verdict

CELL = R.cell(0, 0, 0, 0)
STAFF0 = R.staff(0, 0, 0)
STAFF1 = R.staff(0, 0, 1)
SPACE = 20.0                       # one staff space, page px
#: Staff 0's lines, top first; `_staff_step`: bottom (1080) = step 0, top = 8.
LINES0 = [1000.0, 1020.0, 1040.0, 1060.0, 1080.0]
#: Staff 1 sits 6 spaces under staff 0.
LINES1 = [1200.0, 1220.0, 1240.0, 1260.0, 1280.0]
CANON = 5.0                        # canonical px per page px in the cell

ORDER = (Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.GLYPH_OWNER,
         Q.ARTICULATION_IS_NOT_AN_ARTICULATION)


def _y_of_step(step, lines=LINES0):
    return max(lines) - step * SPACE / 2.0


def _geometry(log):
    for st, ls in ((STAFF0, LINES0), (STAFF1, LINES1)):
        log.observe(st, Q.STAFF_LINES, list(ls), reader=READERS.GEOMETRY,
                    frame="page")
        log.observe(st, Q.STAFF_SPACING, SPACE, reader=READERS.GEOMETRY,
                    frame="page")
    log.observe(CELL, Q.CELL_STAFF_SPACE, SPACE * CANON,
                reader=READERS.GEOMETRY, frame="cell:0")


def _glyph(log, gi, cls, cy, *, x0=500.0, x1=530.0, h=3.0, quantity=None):
    """A glyph whose page box is centred at y `cy`, its canonical box the page
    box scaled by `CANON` -- one frame, so the fixture cannot disagree with
    itself about which boxes overlap."""
    g = R.glyph(0, 0, 0, 0, gi)
    pb = [x0, cy - h / 2.0, x1, cy + h / 2.0]
    log.observe(g, Q.GLYPH_BOX, (cls, x0 * CANON, pb[1] * CANON,
                                 (x1 - x0) * CANON, h * CANON),
                reader=READERS.DETECTOR, frame="cell:0", score=0.7,
                category=cls, bbox_page_px=pb)
    if quantity is not None:
        log.observe(g, quantity, cls, reader=READERS.DETECTOR,
                    frame="cell:0", score=0.7)
    return g


def _tenuto(log, step, *, lines=LINES0, cls="articTenutoBelow"):
    return _glyph(log, 1, cls, _y_of_step(step, lines),
                  quantity=Q.ARTICULATION_MARK)


def _head(log, gi, step, *, lines=LINES0, x0=502.0, x1=528.0):
    g = _glyph(log, gi, "noteheadBlackOnLine", _y_of_step(step, lines),
               x0=x0, x1=x1, h=SPACE * 0.9)
    # the notehead refusal's domain (`subjects_from`)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine",
                reader=READERS.DETECTOR, frame="cell:0", score=0.7)
    return g


def _owner(log, g, outcome, value, candidates=()):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=g, quantity=Q.GLYPH_OWNER,
        outcome=outcome, value=value, decider="test", reason="distance",
        candidates=tuple(candidates)))


def _decide(log):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=ORDER)
    return log.verdict(Q.ARTICULATION_IS_NOT_AN_ARTICULATION,
                       R.glyph(0, 0, 0, 0, 1))


def _scene(mark_step, head_steps=(), *, mark_lines=LINES0, head_lines=LINES0,
           cls="articTenutoBelow", owners=None):
    log = Log()
    _geometry(log)
    _tenuto(log, mark_step, lines=mark_lines, cls=cls)
    heads = [_head(log, 10 + i, s, lines=head_lines)
             for i, s in enumerate(head_steps)]
    return log, heads


class TestALedgerIsNotATenuto(unittest.TestCase):

    def test_below_the_staff_a_head_farther_out_makes_it_a_ledger(self):
        # rung one space under line 1, head in the space beyond it
        log, _ = _scene(-2.0, (-3.0,))
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "ledger_between_staff_and_note")

    def test_above_the_staff_the_mirror(self):
        log, _ = _scene(10.0, (11.0,))
        v = _decide(log)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "ledger_between_staff_and_note")

    def test_a_head_standing_ON_the_rung_makes_it_a_ledger(self):
        log, _ = _scene(12.0, (12.0,))
        self.assertIs(_decide(log).value, True)

    def test_an_inner_rung_of_a_ladder_far_from_its_note(self):
        log, _ = _scene(10.0, (15.0,))
        self.assertIs(_decide(log).value, True)

    def test_the_facts_are_recorded(self):
        log, _ = _scene(-2.0, (-3.0,))
        d = _decide(log).detail
        self.assertEqual(d["ledger_of_staff"], STAFF0.to_key())
        self.assertAlmostEqual(d["mark_beyond_spaces"], 1.0, places=3)
        self.assertAlmostEqual(d["head_beyond_spaces"], 1.5, places=3)
        self.assertAlmostEqual(d["rung_offset_spaces"], 0.0, places=3)


class TestARealTenutoIsKept(unittest.TestCase):
    """The positive controls: Sean's convention says an articulation outside
    the staff stands BEYOND its note, so its head is staffward of it."""

    def test_below_the_staff_tenuto_under_its_note(self):
        log, _ = _scene(-3.0, (-1.0,))
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "articulation")

    def test_above_the_staff_tenuto_over_its_note(self):
        log, _ = _scene(11.5, (9.0,))
        self.assertIs(_decide(log).value, False)

    def test_a_tenuto_whose_box_touches_its_note_is_still_kept(self):
        # head centre 0.75 space staffward: the boxes intersect (head 0.9 sp
        # tall) but the head is not ON the dash
        log, _ = _scene(-3.5, (-2.0,))
        self.assertIs(_decide(log).value, False)

    def test_no_head_in_the_column_is_kept(self):
        log, _ = _scene(-3.0, ())
        self.assertIs(_decide(log).value, False)

    def test_a_head_in_ANOTHER_column_does_not_count(self):
        log = Log()
        _geometry(log)
        _tenuto(log, -2.0)
        _glyph(log, 10, "noteheadBlackOnLine", _y_of_step(-3.0),
               x0=600.0, x1=626.0, h=18.0)
        self.assertIs(_decide(log).value, False)

    def test_a_dash_inside_the_staff_is_never_a_ledger(self):
        log, _ = _scene(3.0, (2.0,))
        self.assertIs(_decide(log).value, False)

    def test_another_class_is_not_asked(self):
        # an accent is not dash-shaped: SHAPE FROM THE CLASS (2.12)
        log, _ = _scene(-2.0, (-3.0,), cls="articAccentBelow")
        v = _decide(log)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "articulation")

    def test_a_head_refused_as_not_a_notehead_does_not_count(self):
        log, heads = _scene(-2.0, (-3.0,))
        log.observe(heads[0], Q.HUMAN_BOX_VERDICT, "not_a_symbol",
                             reader=READERS.SEAN, frame="review:box",
                             sidecar="t.json", action="act-1")
        log.freeze()
        adjudicate._ensure_decisions()
        adjudicate.run(log, order=ORDER)
        nn = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, heads[0])
        self.assertIs(nn.value, True)          # the refusal really ran
        v = log.verdict(Q.ARTICULATION_IS_NOT_AN_ARTICULATION,
                        R.glyph(0, 0, 0, 0, 1))
        self.assertIs(v.value, False)


class TestTheHeadsOwnStaff(unittest.TestCase):
    """The census: a padded cell holds the NEIGHBOUR staff's ledgers."""

    def test_a_ledger_of_the_staff_below_filed_on_the_staff_above(self):
        # mark 1 space over staff 1's top line, head 2 spaces over it; both
        # filed in staff 0's cell. Against staff 0 the head is STAFFWARD of
        # the mark; against its owner, staff 1, it is beyond.
        log = Log()
        _geometry(log)
        _tenuto(log, 10.0, lines=LINES1)
        h = _head(log, 10, 12.0, lines=LINES1)
        _owner(log, h, Outcome.DECIDED, STAFF1.to_key())
        v = _decide(log)
        self.assertIs(v.value, True)
        self.assertEqual(v.detail["ledger_of_staff"], STAFF1.to_key())

    def test_an_uncontested_head_given_to_the_nearer_staff(self):
        # no `Q.GLYPH_OWNER` contest at all: 2.7b's notehead refusal
        # (`belongs_to_a_nearer_staff`) names the staff, and that is asked
        log = Log()
        _geometry(log)
        _tenuto(log, 10.0, lines=LINES1)
        _head(log, 10, 12.0, lines=LINES1)
        v = _decide(log)
        self.assertIs(v.value, True)
        self.assertEqual(v.detail["ledger_of_staff"], STAFF1.to_key())

    def test_the_note_boxed_only_in_the_neighbour_staffs_cell(self):
        # the census's crop 28: the dash padded into staff 0's cell, the head
        # standing on it boxed only in staff 1's cell of the same bar
        log = Log()
        _geometry(log)
        _tenuto(log, 10.0, lines=LINES1)
        g = R.glyph(0, 0, 1, 0, 3)
        y = _y_of_step(10.0, LINES1)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", 0, 0, 1, 1),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.7,
                    bbox_page_px=[502.0, y - 9.0, 528.0, y + 9.0])
        v = _decide(log)
        self.assertIs(v.value, True)
        self.assertEqual(v.detail["ledger_of_staff"], STAFF1.to_key())

    def test_a_head_in_a_neighbour_cell_of_ANOTHER_bar_does_not_count(self):
        log = Log()
        _geometry(log)
        _tenuto(log, 10.0, lines=LINES1)
        g = R.glyph(0, 0, 1, 1, 3)
        y = _y_of_step(10.0, LINES1)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", 0, 0, 1, 1),
                    reader=READERS.DETECTOR, frame="cell:1", score=0.7,
                    bbox_page_px=[502.0, y - 9.0, 528.0, y + 9.0])
        self.assertIs(_decide(log).value, False)

    def test_a_tenuto_under_the_upper_staffs_note_is_kept(self):
        # head of staff 0 in the space under it, tenuto under the head: the
        # head is beyond the mark only as seen from staff 1, which does not
        # own it.
        log = Log()
        _geometry(log)
        _tenuto(log, -3.0)
        h = _head(log, 10, -1.0)
        _owner(log, h, Outcome.DECIDED, STAFF0.to_key())
        self.assertIs(_decide(log).value, False)

    def test_an_unread_owner_that_would_make_it_a_ledger_abstains(self):
        log = Log()
        _geometry(log)
        _tenuto(log, 10.0, lines=LINES1)
        h = _head(log, 10, 12.0, lines=LINES1)
        _owner(log, h, Outcome.NARROWED, None,
               candidates=((STAFF0.to_key(), 1.0), (STAFF1.to_key(), 1.0)))
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "head_owner_unread")

    def test_an_unread_owner_that_could_not_make_it_a_ledger_is_kept(self):
        log = Log()
        _geometry(log)
        _tenuto(log, -3.0)
        h = _head(log, 10, -1.0)
        # an abstained contest names no candidate: the home staff is asked
        _owner(log, h, Outcome.ABSTAINED, None)
        self.assertIs(_decide(log).value, False)


class TestRefusalsStillComeFirst(unittest.TestCase):

    def test_no_staff_geometry_abstains_for_a_dash(self):
        log = Log()
        log.observe(CELL, Q.CELL_STAFF_SPACE, SPACE * CANON,
                    reader=READERS.GEOMETRY, frame="cell:0")
        _tenuto(log, -2.0)
        _head(log, 10, -3.0)
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, ABSTAIN.NO_STAFF_GEOMETRY)

    def test_a_human_nothing_still_wins(self):
        log, _ = _scene(-3.0, (-1.0,))
        log.observe(R.glyph(0, 0, 0, 0, 1), Q.HUMAN_BOX_VERDICT,
                    "not_a_symbol", reader=READERS.SEAN, frame="review:box",
                    sidecar="t.json", action="act-1")
        v = _decide(log)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "human_not_a_symbol")

    def test_it_runs_after_the_owner_and_the_notehead_refusal(self):
        o = list(adjudicate.ORDER)
        me = o.index(Q.ARTICULATION_IS_NOT_AN_ARTICULATION)
        self.assertGreater(me, o.index(Q.GLYPH_OWNER))
        self.assertGreater(me, o.index(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD))
        self.assertLess(me, o.index(Q.ARTICULATION_OWNER))


if __name__ == "__main__":
    unittest.main()
