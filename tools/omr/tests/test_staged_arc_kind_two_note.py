"""ROADMAP 2.75 -- `Q.ARC_KIND` by Sean's two-note rule (2026-10-09), STAGED,
GATHER+ADJUDICATE only.

    *"If an arc only goes from one note to the next and they are both on the
    same pitch it can only be a tie - never a slur. A slur requires different
    notes if only 2 are involved."*
    *"If there are 2 arcs - one over the other - then the tie will always be
    the bottom and the slur on top."*

THE HISTORY THESE TESTS GUARD. The same comparison existed as `OMR_ARC_RECLASS`
and was REFUSED on OMR-NED (+130 scan edits, ALL tie->slur: a scan's pitch at
an arc's end was unreliable). So the tests that matter most are the CONTROLS --
the arcs the rule must NOT change: a real slur over three notes whose ends
share a position, a tie whose end position was never read, a tie across
different-looking positions the second instrument disagrees with, an arc a
chord or a printed accidental makes uncertain, a staff line refused as an arc.
Each refusal sits beside a positive control in the same class (the same
geometry with the one fact changed that should let the rule act), or it would
pass by refusing everything (CLAUDE.md §6b).

⚠️ Run RED against `0a06e5c2` (origin/main before this lane): the "decides"
tests fail there -- the detector's class decides and the grammar is only
recorded -- and the controls pass there too, which is what a control is for.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import (ABSTAIN, Log, Outcome, Q, READERS,
                                     Verdict)

#: page pixels: a staff space is 10 px, a head 12 x 10; a half-step is 5 px.
H_W, H_H = 12.0, 10.0
TOP = 100.0                      # y of the top staff line
CELL_W = 200.0
ORDER = (Q.ARC_IS_NOT_AN_ARC, Q.NOTEHEAD_POSITION, Q.ACCIDENTAL_OWNER,
         Q.ARC_KIND, Q.TIE_PAIR)


def _cells(log, n, staff_i=0):
    for m in range(n):
        log.observe(R.cell(0, 0, staff_i, m), Q.CELL_BOX,
                    [m * CELL_W, 50.0, (m + 1) * CELL_W, 250.0],
                    reader=READERS.GEOMETRY, frame=f"cell:{m}")


def _head(log, cell, gi, x, step, staff_i=0, *, read=True):
    """A head at half-step `step` from the top line: page box starts at `x`,
    centre y = TOP + 5 * step. `read=False` files no position row."""
    g = R.glyph(0, 0, staff_i, cell, gi)
    yc = TOP + 5.0 * step
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", 0, 0, H_W, H_H),
                reader=READERS.DETECTOR, frame=f"cell:{cell}", score=0.9,
                category="notehead",
                bbox_page_px=[x, yc - H_H / 2, x + H_W, yc + H_H / 2])
    if read:
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, float(step),
                    reader=READERS.GEOMETRY, frame=f"cell:{cell}",
                    residual=0.0, rounded=int(step))
    return g


def _arc(log, cell, gi, x0, x1, y0=112.0, y1=118.0, cls="tie", staff_i=0):
    g = R.glyph(0, 0, staff_i, cell, gi)
    log.observe(g, Q.ARC_BOX, cls, reader=READERS.DETECTOR,
                frame=f"cell:{cell}", score=0.8, x0=x0, x1=x1, y0=y0, y1=y1,
                bbox_page_px=[x0, y0, x1, y1])
    return g


def _decide(log, *arcs, extra=(), order=ORDER):
    log.freeze()
    for sub, quantity, value in extra:
        log.record(Verdict(id=log._next_id("vrd"), subject=sub,
                           quantity=quantity, outcome=Outcome.DECIDED,
                           value=value, decider="t", reason="x"))
    adjudicate.run(log, order=order)
    return [log.verdict(Q.ARC_KIND, a) for a in arcs]


def _two_heads(log, step_a, step_b, *, cls="tie", gi=5, **arc_kw):
    """Two heads in bar 0 and one arc between them."""
    _cells(log, 2)
    a = _head(log, 0, 0, 40.0, step_a)
    b = _head(log, 0, 1, 120.0, step_b)
    arc = _arc(log, 0, gi, 55.0, 115.0, cls=cls, **arc_kw)
    return a, b, arc


class TestTheRuleDecides(unittest.TestCase):
    """The detector's class is overturned where BOTH ends were read."""

    def test_two_notes_of_one_pitch_classed_SLUR_is_a_tie(self):
        log = Log()
        a, b, arc = _two_heads(log, 4, 4, cls="slur")
        (v,) = _decide(log, arc)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "tie")
        self.assertEqual(v.reason, "tie")
        rule = v.detail["grammar"]["tie_slur_rule"]
        self.assertEqual(rule["rule"], "two_notes_same_pitch")
        self.assertEqual(rule["detector_class"], "slur")
        self.assertEqual(rule["two_note"]["relation"], "same")
        self.assertEqual(rule["two_note"]["accidental"], "unchanged")

    def test_and_the_tie_pairing_then_pairs_it(self):
        """Reclassifying is only worth anything if EXPORT then writes it: the
        pairing reads `Q.ARC_KIND` and now pairs the same two heads."""
        log = Log()
        a, b, arc = _two_heads(log, 4, 4, cls="slur")
        _decide(log, arc)
        pair = log.verdict(Q.TIE_PAIR, arc)
        self.assertEqual(pair.outcome, Outcome.DECIDED)
        self.assertEqual(pair.value, {"start": a.to_key(), "stop": b.to_key()})

    def test_two_notes_a_step_apart_classed_TIE_is_a_slur(self):
        log = Log()
        _a, _b, arc = _two_heads(log, 4, 5, cls="tie")
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, "slur")
        self.assertEqual(v.reason, "slur")
        self.assertEqual(v.detail["grammar"]["tie_slur_rule"]["rule"],
                         "two_notes_different_pitch")

    def test_an_agreeing_class_is_confirmed_not_changed(self):
        for cls, steps, want in (("tie", (4, 4), "tie"), ("slur", (4, 6), "slur")):
            with self.subTest(cls=cls):
                log = Log()
                _a, _b, arc = _two_heads(log, *steps, cls=cls)
                (v,) = _decide(log, arc)
                self.assertEqual(v.value, want)
                self.assertEqual(v.detail["detector_class"], cls)

    def test_a_far_head_takes_its_LEDGER_position_not_its_geometry(self):
        """Two heads far below the staff: the geometry steps would say they
        differ (the box centres are 15 px apart), the ledger reader says
        they are ONE position -- the reading decides."""
        log = Log()
        _cells(log, 2)
        a = _head(log, 0, 0, 40.0, 14)           # geometry: step 14 -> far
        b = _head(log, 0, 1, 120.0, 14)
        arc = _arc(log, 0, 5, 55.0, 115.0, y0=162.0, y1=168.0, cls="slur")
        for g in (a, b):
            log.observe(g, Q.FAR_HEAD_LEDGER_POSITION, 14.0,
                        reader=READERS.LEDGER_FARHEAD, frame="cell:0",
                        geometry_position=14)
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, "tie")
        self.assertEqual(v.detail["grammar"]["tie_slur_rule"]["two_note"]
                         ["start_step_source"], "ledger")


class TestTheControlsThatMustNotChange(unittest.TestCase):

    def test_a_real_slur_over_three_notes_stays_a_slur_even_if_its_ends_match(self):
        """C D C under a slur. THE refused flag's whole risk: ends at one
        position are not a tie when a note stands between them."""
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 40.0, 4)
        _head(log, 0, 1, 80.0, 6)                # the middle note
        _head(log, 0, 2, 120.0, 4)
        arc = _arc(log, 0, 5, 55.0, 115.0, cls="slur")
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, "slur")
        self.assertTrue(v.detail["grammar"]["tie_slur_rule"]["two_note"]["between"])
        self.assertIsNone(v.detail["grammar"]["tie_slur_rule"]["rule"])

    def test_the_positive_control_the_same_ends_with_no_note_between_ARE_a_tie(self):
        """The class above with the middle note removed: same two ends, same
        position, same detector class -- now the rule acts."""
        log = Log()
        _a, _b, arc = _two_heads(log, 4, 4, cls="slur")
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, "tie")

    def test_a_two_note_slur_between_different_pitches_stays_a_slur(self):
        log = Log()
        _a, _b, arc = _two_heads(log, 4, 7, cls="slur")
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, "slur")

    def test_a_TIE_with_one_end_position_UNREAD_is_not_turned_into_a_slur(self):
        """The refused flag's exact failure: a misread or missing end position
        read as 'different pitch'. A far head whose ledger reading ABSTAINED
        has no position -- the geometry's extrapolation is not substituted."""
        log = Log()
        _cells(log, 2)
        a = _head(log, 0, 0, 40.0, 14)           # far head, ledgers unread
        b = _head(log, 0, 1, 120.0, 13)          # far head, ledgers READ
        arc = _arc(log, 0, 5, 55.0, 115.0, y0=162.0, y1=168.0, cls="tie")
        log.abstain(a, Q.FAR_HEAD_LEDGER_POSITION, reader=READERS.LEDGER_FARHEAD,
                    frame="cell:0", reason=ABSTAIN.LEDGER_NOT_READ)
        log.observe(b, Q.FAR_HEAD_LEDGER_POSITION, 13.0,
                    reader=READERS.LEDGER_FARHEAD, frame="cell:0",
                    geometry_position=13)
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, "tie", "an unread end must not make a slur")
        two = v.detail["grammar"]["tie_slur_rule"]["two_note"]
        self.assertEqual(two["relation"], "unread")
        self.assertEqual(two["start_step_source"], "far_head_ledger_unread")

    def test_the_two_instruments_must_AGREE(self):
        """Steps say 'different' (4 vs 5) but the boxes sit at one height
        (a thick-scan or grid error). A disagreement is `conflict`, not an
        answer -- the detector's class stands."""
        log = Log()
        _cells(log, 2)
        a = _head(log, 0, 0, 40.0, 4)
        b = _head(log, 0, 1, 120.0, 4)           # same y ...
        # ... but the row of the second head claims a different step
        log.observe(b, Q.NOTEHEAD_STAFF_POSITION, 5.0, reader=READERS.GEOMETRY,
                    frame="cell:0", residual=0.0, rounded=5)
        arc = _arc(log, 0, 5, 55.0, 115.0, cls="tie")
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, "tie")

    def test_a_chord_end_with_NO_same_pitch_pairing_is_not_called_a_slur(self):
        """Chord to chord, every DETECTED pairing a different pitch. The
        partner may be a note nobody detected (fused or doubled boxes), so the
        slur direction does not fire at a chord -- the class stands. (The
        first version slurred tied chords: Brahms p0 bar 3.)"""
        for cls in ("tie", "slur"):
            with self.subTest(cls=cls):
                log = Log()
                _cells(log, 2)
                for gi, (x, step) in enumerate(((40.0, 4), (40.0, 9),
                                                (120.0, 6), (120.0, 8))):
                    _head(log, 0, gi, x, step)
                arc = _arc(log, 0, 8, 55.0, 115.0, y0=109.0, y1=115.0, cls=cls)
                (v,) = _decide(log, arc)
                self.assertEqual(v.value, cls)
                self.assertEqual(v.detail["grammar"]["tie_slur_rule"]["two_note"]
                                 ["relation"], "chord_no_same_pitch")

    def test_the_positive_control_single_heads_a_step_apart_ARE_a_slur(self):
        log = Log()
        _two_heads(log, 4, 6, cls="tie")
        a = R.glyph(0, 0, 0, 0, 5)
        (v,) = _decide(log, a)
        self.assertEqual(v.value, "slur")

    def test_a_chord_end_with_one_member_UNREAD_does_not_prove_no_pairing(self):
        """The unread member may be the partner: the class stands."""
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 40.0, 4)
        _head(log, 0, 1, 40.0, 9, read=False)
        _head(log, 0, 2, 120.0, 6)
        _head(log, 0, 3, 120.0, 8)
        arc = _arc(log, 0, 8, 55.0, 115.0, y0=109.0, y1=115.0, cls="tie")
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, "tie")
        self.assertEqual(v.detail["grammar"]["tie_slur_rule"]["two_note"]["relation"],
                         "unread")

    def test_a_tied_chord_arc_nearest_the_OTHER_notes_is_still_a_tie(self):
        """Sean 2026-10-09 (litolff_02 / litolff_03 tiles): a two-note chord
        tied across the barline, the arc printed nearest one note at each end
        but those two are a step apart. The OTHER pair is one pitch, and
        "if they are close to note heads that are the same it is a tie"."""
        log = Log()
        _cells(log, 2)
        for gi, (x, step) in enumerate(((40.0, 4), (40.0, 9), (120.0, 5), (120.0, 9))):
            _head(log, 0, gi, x, step)
        arc = _arc(log, 0, 8, 55.0, 115.0, y0=109.0, y1=115.0, cls="tie")
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, "tie")
        two = v.detail["grammar"]["tie_slur_rule"]["two_note"]
        self.assertEqual(two["relation"], "same")
        self.assertEqual(two["pairs_at_one_pitch"], 1)

    def test_the_same_chord_tie_across_a_BARLINE_half_arc(self):
        """The litolff_02 shape: the arc is the right half of a tie cut at the
        barline, the heads in the next bar are a two-note chord."""
        log = Log()
        _cells(log, 3)
        for gi, (x, step) in enumerate(((150.0, 4), (150.0, 9))):
            _head(log, 0, gi, x, step)
        for gi, (x, step) in enumerate(((230.0, 5), (230.0, 9))):
            _head(log, 1, gi, x, step)
        h1 = _arc(log, 0, 8, 165.0, 200.0, y0=109.0, y1=115.0, cls="tie")
        h2 = _arc(log, 1, 8, 200.0, 222.0, y0=109.0, y1=115.0, cls="tie")
        v1, v2 = _decide(log, h1, h2)
        self.assertEqual((v1.value, v2.value), ("tie", "tie"))

    def test_a_chord_member_at_one_pitch_makes_a_SLUR_class_a_tie(self):
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 40.0, 4)
        _head(log, 0, 1, 40.0, 5)                # a chord member at the start
        _head(log, 0, 2, 120.0, 4)
        arc = _arc(log, 0, 5, 55.0, 115.0, cls="slur")
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, "tie")
        self.assertTrue(v.detail["grammar"]["tie_slur_rule"]["two_note"]["chord"])

    def test_a_sliver_is_not_judged(self):
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 40.0, 4)
        _head(log, 0, 1, 70.0, 4)
        arc = _arc(log, 0, 5, 52.0, 60.0, cls="slur")      # 0.67 head widths
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, "slur")
        self.assertEqual(v.detail["grammar"]["tie_slur_rule"]["two_note"]["why"],
                         "arc_narrower_than_a_head_and_a_half")

    def test_a_staff_line_refused_as_an_arc_stays_refused_and_is_not_judged(self):
        """2.60: the refusal is its own quantity; this rule must neither undo
        it nor run on the box. Two same-position heads would make a `slur`
        class a tie -- on a REFUSED box it is left alone."""
        log = Log()
        a, b, arc = _two_heads(log, 4, 4, cls="slur")
        log.observe(arc, Q.ARC_INK_SHAPE, 0.0, reader=READERS.CV_ARC_INK,
                    frame="cell:0", tall_cols=0.0, lines_in_box=1,
                    width_spaces=22.0, height_spaces=1.4)
        log.freeze()
        adjudicate.run(log, order=ORDER)
        refused = log.verdict(Q.ARC_IS_NOT_AN_ARC, arc)
        self.assertIs(refused.value, True)
        v = log.verdict(Q.ARC_KIND, arc)
        self.assertEqual(v.value, "slur")
        self.assertEqual(v.detail["grammar"]["tie_slur_rule"]["two_note"]["why"],
                         "refused_not_an_arc")


class TestTheAccidentalState(unittest.TestCase):
    """'The same sounding accidental' is proved as 'no accidental on the stop
    head'; an accidental that is printed, or that stands there unclaimed, is
    not proved the same."""

    def _acc(self, log, cell, gi, x, step, staff_i=0):
        g = R.glyph(0, 0, staff_i, cell, gi)
        yc = TOP + 5.0 * step
        log.observe(g, Q.GLYPH_BOX, ("accidentalSharp", 0, 0, 8.0, 20.0),
                    reader=READERS.DETECTOR, frame=f"cell:{cell}", score=0.9,
                    category="accidental",
                    bbox_page_px=[x, yc - 10, x + 8, yc + 10])
        log.observe(g, Q.ACCIDENTAL_STAFF_POSITION, float(step),
                    reader=READERS.GEOMETRY, frame=f"cell:{cell}",
                    alteration=1)
        return g

    def test_a_PRINTED_accidental_on_the_stop_head_keeps_the_class(self):
        """C then C-sharp under a slur: one step, two pitches. Not a tie."""
        log = Log()
        a, b, arc = _two_heads(log, 4, 4, cls="slur")
        acc = self._acc(log, 0, 9, 106.0, 4)
        order = tuple(q for q in ORDER if q != Q.ACCIDENTAL_OWNER)
        (v,) = _decide(log, arc, order=order,
                       extra=((acc, Q.ACCIDENTAL_OWNER, b.to_key()),))
        self.assertEqual(v.value, "slur")
        self.assertEqual(v.detail["grammar"]["tie_slur_rule"]["two_note"]
                         ["accidental"], "printed")

    def test_the_positive_control_no_accidental_at_all_is_a_tie(self):
        log = Log()
        _a, _b, arc = _two_heads(log, 4, 4, cls="slur")
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, "tie")

    def test_an_UNCLAIMED_accidental_beside_a_slur_abstains(self):
        """Two notes at one step cannot be a slur; whether they are one PITCH
        needs an accidental nobody could read (the owner decision abstains:
        no staff-space unit). Abstain -- not 'slur', not 'tie' (rule 8)."""
        log = Log()
        _a, _b, arc = _two_heads(log, 4, 4, cls="slur")
        self._acc(log, 0, 9, 106.0, 4)
        (v,) = _decide(log, arc)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "same_pitch_accidental_unread")

    def test_the_same_unclaimed_accidental_beside_a_TIE_leaves_the_tie(self):
        """The refusal above is for a SLUR class only: a tie with a glyph it
        cannot account for stays what the detector read."""
        log = Log()
        _a, _b, arc = _two_heads(log, 4, 4, cls="tie")
        self._acc(log, 0, 9, 106.0, 4)
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, "tie")

    def test_an_accidental_far_to_the_left_is_not_this_heads(self):
        log = Log()
        _a, _b, arc = _two_heads(log, 4, 4, cls="slur")
        self._acc(log, 0, 9, 60.0, 4)            # >3 head widths left of 120
        (v,) = _decide(log, arc)
        self.assertEqual(v.value, "tie")


class TestHalfArcsOfATieAcrossABarline(unittest.TestCase):

    def test_both_halves_of_a_slur_classed_crossing_tie_are_ties(self):
        log = Log()
        _cells(log, 3)
        _head(log, 0, 0, 150.0, 4)
        _head(log, 1, 0, 230.0, 4)
        h1 = _arc(log, 0, 5, 165.0, 200.0, cls="slur")      # cut at the barline
        h2 = _arc(log, 1, 5, 200.0, 222.0, cls="slur")
        v1, v2 = _decide(log, h1, h2)
        self.assertEqual((v1.value, v2.value), ("tie", "tie"))
        self.assertEqual(v1.detail["grammar"]["tie_slur_rule"]["two_note"]["half_arc"],
                         "right")

    def test_a_crossing_pair_that_differs_is_a_slur(self):
        log = Log()
        _cells(log, 3)
        _head(log, 0, 0, 150.0, 4)
        _head(log, 1, 0, 230.0, 7)
        h1 = _arc(log, 0, 5, 165.0, 200.0, cls="tie")
        v1, = _decide(log, h1)
        self.assertEqual(v1.value, "slur")


class TestStackedArcs(unittest.TestCase):
    """Sean: two arcs one over the other -> the lower is the tie, the upper
    the slur. Fixtures: both arcs over/under the same two heads, one staff,
    the boxes disjoint in y, owners DECIDED. Positions are left UNREAD in the
    deciding tests so the stack is the only witness; a stack over read
    positions is tested separately (positions outrank it)."""

    STAFF = "staff/0/0/0"

    def _stack(self, cls_near, cls_far, steps=(2, 2), *, below=False, read=False):
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 40.0, steps[0], read=read)
        _head(log, 0, 1, 120.0, steps[1], read=read)
        if below:
            near = _arc(log, 0, 5, 55.0, 115.0, y0=120.0, y1=126.0, cls=cls_near)
            far = _arc(log, 0, 6, 55.0, 115.0, y0=134.0, y1=140.0, cls=cls_far)
        else:
            near = _arc(log, 0, 5, 55.0, 115.0, y0=94.0, y1=100.0, cls=cls_near)
            far = _arc(log, 0, 6, 55.0, 115.0, y0=80.0, y1=86.0, cls=cls_far)
        v_near, v_far = _decide(log, near, far, extra=(
            (near, Q.ARC_OWNER, self.STAFF), (far, Q.ARC_OWNER, self.STAFF)))
        return v_near, v_far

    def test_above_the_notes_the_LOWER_arc_is_the_tie_and_the_upper_the_slur(self):
        v_low, v_up = self._stack("slur", "tie")      # detector has them swapped
        self.assertEqual((v_low.value, v_up.value), ("tie", "slur"))
        self.assertEqual(v_low.detail["grammar"]["tie_slur_rule"]["rule"],
                         "stacked_nearer_is_tie")
        self.assertEqual(v_up.detail["grammar"]["tie_slur_rule"]["rule"],
                         "stacked_farther_is_slur")
        self.assertEqual(v_low.detail["grammar"]["tie_slur_rule"]["stack"]["side"],
                         "above")

    def test_below_the_notes_the_arc_NEARER_the_heads_is_the_tie(self):
        """CONFIRMED by Sean 2026-10-09 (the two stacked-below tiles, both
        'A tie, B slur'): the arc nearer the noteheads is the tie, which
        under the notes is the UPPER of the two arcs."""
        v_near, v_far = self._stack("slur", "tie", below=True)
        self.assertEqual((v_near.value, v_far.value), ("tie", "slur"))
        self.assertEqual(v_near.detail["grammar"]["tie_slur_rule"]["stack"]["side"],
                         "below")

    def test_the_positive_control_an_agreeing_detector_is_left_alone(self):
        v_low, v_up = self._stack("tie", "slur")
        self.assertEqual((v_low.value, v_up.value), ("tie", "slur"))

    def test_a_lone_arc_has_no_stack(self):
        log = Log()
        _two_heads(log, 2, 2, cls="slur", y0=94.0, y1=100.0)
        a = R.glyph(0, 0, 0, 0, 5)
        (v,) = _decide(log, a)
        self.assertIsNone(v.detail["grammar"]["tie_slur_rule"]["stack"])

    def test_arcs_on_OPPOSITE_sides_of_the_heads_are_not_one_over_the_other(self):
        """A tie under and a slur over the same notes (the usual layout) is
        not a stack: nothing is reclassified by it."""
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 40.0, 2, read=False)
        _head(log, 0, 1, 120.0, 2, read=False)
        over = _arc(log, 0, 5, 55.0, 115.0, y0=94.0, y1=100.0, cls="slur")
        under = _arc(log, 0, 6, 55.0, 115.0, y0=120.0, y1=126.0, cls="tie")
        vo, vu = _decide(log, over, under, extra=(
            (over, Q.ARC_OWNER, self.STAFF), (under, Q.ARC_OWNER, self.STAFF)))
        self.assertEqual((vo.value, vu.value), ("slur", "tie"))
        self.assertIsNone(vo.detail["grammar"]["tie_slur_rule"]["stack"])

    def test_an_arc_with_no_DECIDED_owner_is_not_a_stack_partner(self):
        """The cell is padded into the neighbour: the next staff's arc sits
        in this cell too. No owner verdict is not 'same staff'."""
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 40.0, 2, read=False)
        _head(log, 0, 1, 120.0, 2, read=False)
        near = _arc(log, 0, 5, 55.0, 115.0, y0=94.0, y1=100.0, cls="slur")
        far = _arc(log, 0, 6, 55.0, 115.0, y0=80.0, y1=86.0, cls="tie")
        v_near, _ = _decide(log, near, far)            # no owner verdicts
        self.assertEqual(v_near.value, "slur")
        self.assertIsNone(v_near.detail["grammar"]["tie_slur_rule"]["stack"])

    def test_THREE_stacked_arcs_decide_nothing(self):
        log = Log()
        _cells(log, 2)
        _head(log, 0, 0, 40.0, 2, read=False)
        _head(log, 0, 1, 120.0, 2, read=False)
        arcs = [_arc(log, 0, 5 + i, 55.0, 115.0, y0=94.0 - 8 * i,
                     y1=100.0 - 8 * i, cls="tie") for i in range(3)]
        vs = _decide(log, arcs[0], extra=tuple(
            (a, Q.ARC_OWNER, self.STAFF) for a in arcs))
        stack = vs[0].detail["grammar"]["tie_slur_rule"]["stack"]
        self.assertIsNone(stack.get("role"))
        self.assertEqual(vs[0].value, "tie")

    def test_a_stack_does_not_override_READ_positions_that_differ(self):
        """Two notes of different pitch cannot take a tie, whatever the stack
        says: the lower arc stays (becomes) a slur and the conflict is
        recorded."""
        v_near, v_far = self._stack("tie", "slur", steps=(2, 3), read=True)
        self.assertEqual(v_near.value, "slur")
        self.assertEqual(v_near.detail["grammar"]["tie_slur_rule"]["conflict"],
                         "stack_says_tie_notes_differ")

    def test_an_upper_slur_over_two_notes_of_one_pitch_abstains(self):
        """Rule 1 says two same-pitch notes can only be a tie, the stack says
        the upper arc is a slur: the arc cannot be a slur and which rule is
        wrong is not something this decision can tell -- abstain (rule 8)."""
        v_near, v_far = self._stack("tie", "slur", steps=(2, 2), read=True)
        self.assertEqual(v_near.value, "tie")
        self.assertEqual(v_far.outcome, Outcome.ABSTAINED)
        self.assertEqual(v_far.reason, "stack_slur_over_two_same_pitch_notes")


class TestOrderAndDeclarations(unittest.TestCase):

    def test_what_the_rule_reads_is_decided_before_it(self):
        order = list(adjudicate.ORDER)
        for upstream in (Q.NOTEHEAD_POSITION, Q.ACCIDENTAL_OWNER, Q.ARC_OWNER,
                         Q.ARC_IS_NOT_AN_ARC, Q.GLYPH_OWNER):
            self.assertLess(order.index(upstream), order.index(Q.ARC_KIND),
                            upstream)
        self.assertLess(order.index(Q.ARC_KIND), order.index(Q.TIE_PAIR))


if __name__ == "__main__":
    unittest.main()
