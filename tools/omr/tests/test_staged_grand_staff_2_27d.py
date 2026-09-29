"""ROADMAP 2.27d: three rules gated on a DECIDED grand staff (`Q.GROUP_
SYMBOL` "brace") -- Sean, DECISIONS 2026-09-29, answering 2.27b's question 2
("no keyboard/harp work is in the acceptance set yet ... build anyway").

⚠️ MICROSCOPIC, PER DECISIONS 2026-09-29 ("work through the wiring
conceptually, proved by MICROSCOPIC tests -- not pricing runs"). Every test
below is hand-built rows for 2-3 real subjects plus a positive/negative
control; nothing here gathers a page or re-adjudicates a saved record.

Each class proves ONE connection:

  * `TestGrandStaffPartner`       -- the shared query itself (`structure.
                                     grand_staff_partner_staff`), the fact
                                     all three rules connect to.
  * `TestDynamicsSharedOnceOnly`  -- a dynamic letter CONTESTED between the
                                     two staves of a decided brace is filed
                                     ONCE, on the pair's upper staff.
  * `TestCrossStaffBeamIsThePartsOwn` -- a beam stroke touching only the
                                     decided partner's stems is not
                                     discounted as "the neighbour's beam".
  * `TestPedalOwner`              -- a pedal mark is owned by the pair's
                                     LOWER staff, never by pad position.
  * `TestOttavaOwner`             -- an ottava bracket is owned by the staff
                                     it hugs, above or below, with the
                                     MusicXML `type` correctly inverted.

Every positive-brace test carries its own negative control: the identical
geometry with the group's instrument NOT a keyboard/harp (a "bracket"
system, e.g. two horns) is untouched -- CLAUDE.md rule 7, "a control must
be able to fail".
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged.adjudicators import structure as _structure
from tools.omr.staged.adjudicators.rhythm import _not_the_neighbours_beam
from tools.omr.staged import record as R
from tools.omr.staged.record import Kind, Log, Outcome, Q, READERS, Scope, Verdict

SYSTEM = R.system(0, 0)
UPPER = R.staff(0, 0, 0)          # the brace pair's own two staves
LOWER = R.staff(0, 0, 1)
OTHER = R.staff(0, 0, 2)          # a third staff, never in the pair


def _decide(log, quantity, subject):
    return adjudicate.adjudicate_one(log, adjudicate.REGISTRY[quantity], subject)


def _inject_instrument(log, staff_sub, family):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=staff_sub, quantity=Q.INSTRUMENT,
        outcome=Outcome.DECIDED, value={"family": family},
        decider="test_fixture", reason="r", considered=(), basis=()))


def _brace_pair(log, *, family="keyboard", block=1, staves=(UPPER, LOWER)):
    """Files `Q.BRACKET_BLOCK` + a DECIDED `Q.INSTRUMENT`, then runs the
    REAL `Q.STAFF_GROUP`/`Q.GROUP_SYMBOL` decisions -- the exact fixture
    shape `test_staged_identity_chain.py`'s `_page_with_labels` already
    uses for `Q.BRACKET_BLOCK`. `family="keyboard"` decides "brace"
    (`structure.BRACE_FAMILIES`); anything else decides "bracket" -- the
    negative control every positive test below also runs.
    """
    for st in staves:
        log.observe(st, Q.BRACKET_BLOCK, block, reader=READERS.GEOMETRY,
                    frame="system")
        _inject_instrument(log, st, family)
    for st in staves:
        _decide(log, Q.STAFF_GROUP, st)
    return _decide(log, Q.GROUP_SYMBOL, SYSTEM)


class TestGrandStaffPartner(unittest.TestCase):
    """The shared connection every rule below reads. A hand-rolled
    `Evidence` (the same construction `test_staged_adjudicate.py` uses)
    stands in for a real decision's own, since `Q.DYNAMIC`'s own spec
    already declares both quantities `wants` needs."""

    def _ev(self, log, subject):
        from tools.omr.staged.adjudicate import Evidence
        return Evidence(log, subject, adjudicate.REGISTRY[Q.DYNAMIC])

    def test_a_decided_brace_pair_names_its_partner(self):
        log = Log()
        _brace_pair(log)
        log.freeze()
        ev = self._ev(log, UPPER)
        self.assertEqual(_structure.grand_staff_partner_staff(ev, UPPER.to_key()),
                         LOWER.to_key())
        ev2 = self._ev(log, LOWER)
        self.assertEqual(_structure.grand_staff_partner_staff(ev2, LOWER.to_key()),
                         UPPER.to_key())

    def test_RED_a_bracket_pair_names_no_partner(self):
        """⚠️ THE CONTROL THAT MUST BE ABLE TO FAIL (rule 7): the identical
        block/geometry, only the instrument family differs (two horns, not
        a keyboard) -- `Q.GROUP_SYMBOL` decides "bracket" and the query
        must return `None`."""
        log = Log()
        v = _brace_pair(log, family="brass")
        self.assertEqual(v.value, "bracket")
        log.freeze()
        ev = self._ev(log, UPPER)
        self.assertIsNone(
            _structure.grand_staff_partner_staff(ev, UPPER.to_key()))

    def test_a_third_staff_outside_the_pair_has_no_partner(self):
        log = Log()
        _brace_pair(log)
        log.observe(OTHER, Q.BRACKET_BLOCK, 2, reader=READERS.GEOMETRY,
                    frame="system")
        _decide(log, Q.STAFF_GROUP, OTHER)
        log.freeze()
        ev = self._ev(log, OTHER)
        self.assertIsNone(
            _structure.grand_staff_partner_staff(ev, OTHER.to_key()))


# ─────────────────────────────────────────────────────────────────────────────
# 2.27d.1 -- grand-staff dynamics
# ─────────────────────────────────────────────────────────────────────────────


def _letter(log, glyph, letter, x0, x1, *, y=100.0):
    from tools.omr.staged import gather as G
    return log.observe(
        glyph, Q.DYNAMIC_LETTER, "dynamic" + letter.upper(),
        reader=READERS.DETECTOR, frame=G.FRAME_PAGE, score=0.8,
        letter=letter, cell_frame="cell:0",
        bbox_page_px=[x0, y - 5.0, x1, y + 5.0],
        x_center_page=(x0 + x1) / 2.0, y_center_page=y)


def _contest(log, glyph, *, winner, loser, near=1.0, far=4.0):
    from tools.omr.staged import gather as G
    log.observe(glyph, Q.GLYPH_BAND_DISTANCE, far, reader=READERS.GEOMETRY,
                frame=G.FRAME_PAGE, candidate=loser.to_key(), own=True,
                position_in_candidate=2.0)
    log.observe(glyph, Q.GLYPH_BAND_DISTANCE, near, reader=READERS.GEOMETRY,
                frame=G.FRAME_PAGE, candidate=winner.to_key(), own=False,
                position_in_candidate=2.0)


class TestDynamicsSharedOnceOnly(unittest.TestCase):
    """DECISIONS 2026-09-29: *"a dynamic between its two staves belongs to
    BOTH staves (the part), not one."* Written ONCE, on the pair's UPPER
    staff, per `_canonical_grand_staff_owner`'s own convention.

    ⚠️ THE FIXTURE IS THE SAME SHAPE `test_staged_dynamics.py`'s own
    `TestOwnershipResolvesTheContest` uses: two glyphs of ONE printed
    letter, one detected per staff's cell, `Q.GLYPH_OWNER` DECIDING one of
    them a winner -- here LOWER, by the fixture's own distance tiers,
    exactly as a real cell's padding would hand a between-staves letter to
    whichever staff's ladder/distance reading wins first.
    """

    def _log(self, *, family="keyboard"):
        log = Log()
        _brace_pair(log, family=family)
        g_upper = R.glyph(0, 0, 0, 0, 0)
        g_lower = R.glyph(0, 0, 1, 0, 0)
        _letter(log, g_upper, "f", 100.0, 110.0)
        _letter(log, g_lower, "f", 100.0, 110.0)
        # `Q.GLYPH_OWNER`'s own ladder/distance tiers name LOWER the winner
        # -- the shape 24% of real cross-staff letters take (CLAUDE.md).
        _contest(log, g_upper, winner=LOWER, loser=UPPER)
        _contest(log, g_lower, winner=LOWER, loser=UPPER)
        log.freeze()
        _decide(log, Q.GLYPH_OWNER, g_upper)
        _decide(log, Q.GLYPH_OWNER, g_lower)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, g_upper).value,
                         LOWER.to_key())
        return log

    def test_RED_off_a_brace_the_letter_stays_where_glyph_owner_put_it(self):
        """⚠️ THE CONTROL. Off a decided brace (family=brass -> "bracket")
        this is EXACTLY `test_staged_dynamics.py`'s own shipped behaviour:
        LOWER keeps the letter, UPPER loses its copy. If this ever goes
        green for the wrong reason (the brace branch firing when it should
        not), this assertion is what catches it."""
        log = self._log(family="brass")
        v_lower = _decide(log, Q.DYNAMIC, R.cell(0, 0, 1, 0))
        v_upper = _decide(log, Q.DYNAMIC, R.cell(0, 0, 0, 0))
        self.assertEqual(v_lower.value, ["f"])
        self.assertEqual(v_upper.value, [])
        self.assertEqual(v_upper.reason, "owned_elsewhere")
        self.assertEqual(v_lower.detail["letters_shared_on_grand_staff"], 0)

    def test_GREEN_on_a_decided_brace_the_letter_moves_to_the_upper_staff(self):
        log = self._log(family="keyboard")
        v_upper = _decide(log, Q.DYNAMIC, R.cell(0, 0, 0, 0))
        v_lower = _decide(log, Q.DYNAMIC, R.cell(0, 0, 1, 0))
        self.assertEqual(v_upper.value, ["f"])
        # ⚠️ TWO, NOT ONE: the counter is per ROW (the same granularity
        # `letters_moved_out`/`letters_dropped_as_duplicate` already use),
        # and a contested letter is TWO rows -- one cut from each cell --
        # both of which the brace canonicalises before the duplicate one
        # is dropped below.
        self.assertEqual(v_upper.detail["letters_shared_on_grand_staff"], 2)
        self.assertEqual(v_lower.value, [])
        self.assertEqual(v_lower.reason, "owned_elsewhere")

    def test_an_UNCONTESTED_letter_is_never_relocated_even_on_a_brace(self):
        """⚠️ ONLY THE CONTESTED CASE MOVES. A letter with no twin (`Q.
        GLYPH_OWNER` never ran on it) stays exactly where it was cut, even
        inside a decided brace -- canonicalising it would relocate a mark
        CLAUDE.md rule 6 forbids relocating from pad position alone."""
        log = Log()
        _brace_pair(log, family="keyboard")
        _letter(log, R.glyph(0, 0, 1, 0, 0), "p", 100.0, 110.0)
        log.freeze()
        v_lower = _decide(log, Q.DYNAMIC, R.cell(0, 0, 1, 0))
        v_upper = _decide(log, Q.DYNAMIC, R.cell(0, 0, 0, 0))
        self.assertEqual(v_lower.value, ["p"])
        self.assertEqual(v_upper.value, [])
        self.assertEqual(v_upper.reason, "no_letters")


# ─────────────────────────────────────────────────────────────────────────────
# 2.27d.3 -- cross-staff beaming
# ─────────────────────────────────────────────────────────────────────────────


class _Row:
    """A minimal stand-in for a gathered `Observation` -- `_xywh` reads only
    `.value`, so this is every `_not_the_neighbours_beam` needs from one."""

    def __init__(self, value):
        self.value = value


class TestCrossStaffBeamIsThePartsOwn(unittest.TestCase):
    """DECISIONS 2026-09-29 / ROADMAP 2.27d item 1: *"a beam joining stems
    on BOTH staves of one brace is one beam of the part; it must not be
    discounted as the neighbour's beam."*

    ⚠️ `_not_the_neighbours_beam` IS CALLED DIRECTLY, not through the whole
    of `adjudicate_duration` -- the function under test needs `ev`, `cell`,
    `beams`, `stems`, `own_stems`, and it is a pure `(kept, dropped)`
    partition over `beams`, so testing it directly is the SAME class of
    move `test_staged_dynamics.py` makes calling `adjudicate_dynamic`'s
    own decision function rather than driving the whole pipeline.
    """

    def _cell_anchor(self, log, cell_sub, *, page_x0, page_y0):
        """One dual-frame `Q.GLYPH_BOX` row, `up=1.0`, so canonical and page
        coordinates differ only by this cell's own fixed origin -- the
        minimum `_cell_frame` needs to solve the affine map."""
        g = R.glyph(cell_sub.page, cell_sub.system, cell_sub.staff,
                    cell_sub.cell, 99)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", 10.0, 10.0, 20.0, 20.0),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                    category="notehead",
                    bbox_page_px=[page_x0 + 10.0, page_y0 + 10.0,
                                 page_x0 + 30.0, page_y0 + 30.0])

    def _fixture(self, *, family="keyboard"):
        log = Log()
        _brace_pair(log, family=family)
        home = R.cell(0, 0, 0, 0)          # UPPER's own cell
        neighbour = R.cell(0, 0, 1, 0)     # LOWER's own cell, the pair partner
        self._cell_anchor(log, home, page_x0=100.0, page_y0=400.0)
        self._cell_anchor(log, neighbour, page_x0=100.0, page_y0=500.0)
        # UPPER's own staff lines: page y 430..470 (top=430, bottom=470).
        log.observe(UPPER, Q.STAFF_LINES, [430.0, 440.0, 450.0, 460.0, 470.0],
                    reader=READERS.GEOMETRY, frame="page")
        # LOWER's own stem, filed on the neighbour CELL (`Q.STEM` rows are
        # cell-scoped, `READERS.CV_LINES` -- the same shape
        # `test_staged_duration.py`'s own STEM fixtures use): canonical
        # (10, -15, 2, 25) -> page (110, 485, 2, 25), reaching well past
        # UPPER's bottom line (470) toward the beam stroke below.
        log.observe(neighbour, Q.STEM, (10.0, -15.0, 2.0, 25.0),
                    reader=READERS.CV_LINES, frame="cell:0", score=0.9)
        log.freeze()
        ev = adjudicate.Evidence(log, home, adjudicate.REGISTRY[Q.DURATION])
        # ⚠️ A CANONICAL BEAM STROKE, in UPPER's own cell frame (origin
        # 100, 400): canonical (5, 90, 30, 4) -> page (105, 490, 30, 4),
        # whose page y-centre (492) sits BEYOND UPPER's bottom line (470)
        # and whose page box overlaps LOWER's stem box above -- exactly
        # the shape `_not_the_neighbours_beam` was built to discount.
        beam = _Row((5.0, 90.0, 30.0, 4.0))
        stems = tuple(ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS,
                              subject=home))
        return ev, home, beam, stems

    def test_RED_across_a_bracket_the_stroke_is_still_the_neighbours(self):
        """⚠️ THE CONTROL (rule 7). The identical geometry, `family="brass"`
        -- `Q.GROUP_SYMBOL` decides "bracket" and 2.25b's shipped rule
        fires unchanged: the stroke is dropped."""
        ev, home, beam, stems = self._fixture(family="brass")
        kept, dropped = _not_the_neighbours_beam(ev, home, [beam], stems, [])
        self.assertEqual(kept, [])
        self.assertEqual(dropped, [beam])

    def test_GREEN_on_a_decided_brace_the_stroke_is_kept(self):
        ev, home, beam, stems = self._fixture(family="keyboard")
        kept, dropped = _not_the_neighbours_beam(ev, home, [beam], stems, [])
        self.assertEqual(kept, [beam])
        self.assertEqual(dropped, [])


# ─────────────────────────────────────────────────────────────────────────────
# 2.27d.2 -- pedal marks
# ─────────────────────────────────────────────────────────────────────────────


def _pedal_glyph(log, staff_sub, *, cls="keyboardPedalPed"):
    g = R.glyph(staff_sub.page, staff_sub.system, staff_sub.staff, 0, 0)
    log.observe(g, Q.GLYPH_BOX, (cls, 10.0, 10.0, 8.0, 8.0),
                reader=READERS.DETECTOR, frame="cell:0", score=0.7,
                category="keyboard")
    return g


class TestPedalOwner(unittest.TestCase):
    """`PLACEMENT-CONVENTIONS.md`, "Pedal marks": below the ENTIRE grand
    staff, "never attributed to the nearer one by distance" -- so a pedal
    glyph detected in EITHER staff's own cell (here filed on LOWER, where
    the mark actually sits) is owned by the pair's LOWER staff either way.
    """

    def test_GREEN_a_pedal_mark_is_owned_by_the_lower_staff(self):
        log = Log()
        _brace_pair(log)
        g = _pedal_glyph(log, LOWER)
        log.freeze()
        v = _decide(log, Q.PEDAL_OWNER, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, LOWER.to_key())
        self.assertEqual(v.reason, "grand_staff_lower_staff")
        self.assertEqual(v.detail["pair"], sorted([UPPER.to_key(), LOWER.to_key()]))
        self.assertTrue(v.used, "the brace/group verdicts it connected to")

    def test_a_pedal_mark_filed_on_the_UPPER_cell_still_resolves_to_lower(self):
        """The mark's OWN cell does not decide the answer -- the pair does."""
        log = Log()
        _brace_pair(log)
        g = _pedal_glyph(log, UPPER)
        log.freeze()
        v = _decide(log, Q.PEDAL_OWNER, g)
        self.assertEqual(v.value, LOWER.to_key())

    def test_RED_off_a_decided_brace_it_abstains_rather_than_guessing(self):
        """⚠️ THE CONTROL (rule 7): the identical glyph, no brace decided
        (`family="brass"`) -- CLAUDE.md rule 8, a fallback never converts
        'cannot tell' into an answer, so this must ABSTAIN, never pick the
        nearer staff by pad position."""
        log = Log()
        _brace_pair(log, family="brass")
        g = _pedal_glyph(log, LOWER)
        log.freeze()
        v = _decide(log, Q.PEDAL_OWNER, g)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_brace")

    def test_no_brace_decided_anywhere_also_abstains(self):
        log = Log()
        g = _pedal_glyph(log, OTHER)
        log.freeze()
        v = _decide(log, Q.PEDAL_OWNER, g)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_brace")


# ─────────────────────────────────────────────────────────────────────────────
# 2.27d.4 -- octave brackets
# ─────────────────────────────────────────────────────────────────────────────


class TestOttavaOwner(unittest.TestCase):
    """`PLACEMENT-CONVENTIONS.md`, "Brace, bracket, ottava bracket": *"an
    ottava bracket sits above (8va) or below (8vb) the staff whose octave
    it shifts"* -- and the MusicXML `type` is the OPPOSITE of the printed
    side (verified 2026-09-29 against `usermanuals.musicxml.com`)."""

    def _staff_lines(self, log, sub=UPPER):
        log.observe(sub, Q.STAFF_LINES, [100.0, 110.0, 120.0, 130.0, 140.0],
                    reader=READERS.GEOMETRY, frame="page")

    def _bracket(self, log, y, h, sub=UPPER):
        g = R.glyph(sub.page, sub.system, sub.staff, 0, 0)
        log.observe(g, Q.GLYPH_BOX, ("ottavaBracket", 0.0, y, 40.0, h),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                    category="ottava")
        return g

    def test_GREEN_above_the_staff_is_8va_type_down(self):
        log = Log()
        self._staff_lines(log)
        g = self._bracket(log, y=70.0, h=10.0)          # 70-80, above top=100
        log.freeze()
        v = _decide(log, Q.OTTAVA_OWNER, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "above")
        self.assertEqual(v.value["direction"], "above")
        self.assertEqual(v.value["staff"], UPPER.to_key())
        # ⚠️ THE INVERSION IS THE POINT -- see the module docstring.
        self.assertEqual(v.value["musicxml_type"], "down")
        self.assertEqual(v.detail["staff_top"], 100.0)
        self.assertTrue(v.used, "the box and staff-lines rows it read")

    def test_GREEN_below_the_staff_is_8vb_type_up(self):
        log = Log()
        self._staff_lines(log)
        g = self._bracket(log, y=160.0, h=10.0)         # 160-170, below bottom=140
        log.freeze()
        v = _decide(log, Q.OTTAVA_OWNER, g)
        self.assertEqual(v.reason, "below")
        self.assertEqual(v.value["direction"], "below")
        self.assertEqual(v.value["musicxml_type"], "up")

    def test_RED_ink_inside_the_staff_band_abstains_rather_than_guessing(self):
        """⚠️ THE CONTROL: the same class, centred INSIDE the five-line band
        (a misread this decision's own domain never expects) -- abstain,
        never force a side."""
        log = Log()
        self._staff_lines(log)
        g = self._bracket(log, y=115.0, h=10.0)         # 115-125, inside 100-140
        log.freeze()
        v = _decide(log, Q.OTTAVA_OWNER, g)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_staff_lines")


if __name__ == "__main__":
    unittest.main()
