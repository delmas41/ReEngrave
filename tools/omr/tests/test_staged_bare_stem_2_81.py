"""ROADMAP 2.81 phase 2 -- a bare stem is a quarter, as a LABELLED LIKELIHOOD.

Sean, 2026-10-10: a filled head on a stem whose every candidate beam was
refused and whose tip is seen clean is most likely a quarter -- but his blind
tiles put that at 0.76 pooled / 0.80 strict, below his 95% bar, so it is NOT an
ADJUDICATE decision. Two pieces, both under test here:

  * ADJUDICATE ranks the quarter ABOVE the eighth in the `beam_discounted_
    uncertain` narrowing -- but only where the evidence holds (a decided own
    stem, a tip window READ clean, no refused stroke standing at the tip).
    Where it does not, the order is the one it always was and NOTHING is
    claimed.
  * INFER's `collapse_bare_stem_by_bar` settles such a head ONLY where the
    bar's arithmetic forces it (every landing agrees), behind the default-OFF
    flag `OMR_BARE_STEM_BAR`.

⚠️ Each refusal is paired with a positive control in the same class (CLAUDE.md
§6b): a test that passes by refusing everything is not a test.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate, evaluate, infer, inferences
from tools.omr.staged import adjudicators, consequences  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.gather import FRAME_PAGE
from tools.omr.staged.record import (READERS, Candidate, Kind, Log, Outcome, Q,
                                     Subject, Verdict)

CELL = R.cell(0, 0, 0, 0)
SPACE = 16


# ─────────────────────────────────────────────────────────────────────────────
# ADJUDICATE: the ranking
# ─────────────────────────────────────────────────────────────────────────────


def _head(log, g, *, x=100, y=90):
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", x, y, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                bbox_page_px=[1000 + x, 990, 1020 + x, 1006])


def _two_staff(log):
    """The 2.25b fixture: staff 0 holds the head, staff 1's own stem makes the
    stroke far below staff 0 THAT staff's beam (discounted)."""
    log.observe(R.staff(0, 0, 0), Q.STAFF_LINES,
                [950.0, 960.0, 970.0, 980.0, 990.0],
                reader=READERS.GEOMETRY, frame="page")
    log.observe(CELL, Q.CELL_STAFF_SPACE, float(SPACE),
                reader=READERS.GEOMETRY, frame="cell:0")
    g = R.glyph(0, 0, 0, 0, 0)
    _head(log, g, x=100, y=90)
    gb = R.glyph(0, 0, 1, 0, 0)
    log.observe(gb, Q.NOTEHEAD_CLASS, "noteheadBlack",
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(gb, Q.GLYPH_BOX, ("noteheadBlack", 100, 20, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                bbox_page_px=[1100, 1070, 1120, 1086])
    return g


def _stem(log, *, x, y, w=4, h=20):
    return log.observe(CELL, Q.STEM, (x, y, w, h), reader=READERS.CV_LINES,
                       frame="cell:0", x0=x, x1=x + w, y_center=y + h / 2.0,
                       image="no_staff", staff_lines_erased=True)


def _tip(log, stem_row, *, found, end="top"):
    return log.observe(CELL, Q.STEM_TIP_INK, bool(found),
                       reader=READERS.CV_STEM_TIP, frame="cell:0",
                       stem_row_id=stem_row.id, end=end)


def _neighbour_discounted_head(log, *, tip_found=None):
    """Up-stem head whose ONLY stroke (far below, nowhere near the tip) is the
    neighbour staff's beam -> `beam_discounted_uncertain`."""
    g = _two_staff(log)
    log.observe(CELL, Q.BEAM_STROKE, (90, 150, 40, 4),
                reader=READERS.CV_LINES, frame="cell:0", x0=90, x1=130,
                y_center=152, image="no_staff", staff_lines_erased=True)
    s = _stem(log, x=105, y=80)                      # up, tip at y=80
    log.observe(R.cell(0, 0, 1, 0), Q.STEM, (90, -10, 4, 50),
                reader=READERS.CV_LINES, frame="cell:0", x0=90, x1=94,
                y_center=15, image="no_staff", staff_lines_erased=True)
    if tip_found is not None:
        _tip(log, s, found=tip_found)
    return g


def _beats(v):
    return [c.value["beats"] for c in v.candidates]


def _rank_on():
    """`OMR_BARE_STEM_RANK` is default OFF: the tests that exercise the
    ranking turn it on, and one below asserts the default."""
    return mock.patch.dict(os.environ, {"OMR_BARE_STEM_RANK": "1"})


class TestTheQuarterIsRankedFirstWhereTheEvidenceHolds(unittest.TestCase):

    def test_clean_tip_and_no_refused_stroke_at_the_tip_ranks_the_quarter_first(
            self):
        log = Log()
        g = _neighbour_discounted_head(log, tip_found=False)
        with _rank_on():
            adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beam_discounted_uncertain")
        self.assertEqual(_beats(v), [1.0, 0.5])
        self.assertEqual(v.detail["bare_stem_likelihood"], "quarter_first")
        # still a NARROWING: nothing decided
        self.assertIsNone(v.value)

    def test_CONTROL_the_flag_OFF_keeps_the_old_order_though_the_evidence_holds(
            self):
        """Default OFF (it moves EVALUATE's bar sums -- see the flag's note):
        the same head, the same clean tip, the order it always had; the
        label still says the evidence held."""
        log = Log()
        g = _neighbour_discounted_head(log, tip_found=False)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMR_BARE_STEM_RANK", None)
            adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(_beats(v), [0.5, 1.0])
        self.assertTrue(v.detail["bare_stem_evidence_holds"])
        self.assertEqual(v.detail["bare_stem_likelihood"], "not_claimed")

    def test_a_typo_in_the_flag_leaves_the_order_alone(self):
        for word in ("", "nope", "0", "off"):
            log = Log()
            g = _neighbour_discounted_head(log, tip_found=False)
            with mock.patch.dict(os.environ, {"OMR_BARE_STEM_RANK": word}):
                adjudicate.run(log)
            self.assertEqual(_beats(log.verdict(Q.DURATION, g)), [0.5, 1.0],
                             word)

    def test_CONTROL_no_tip_reading_keeps_the_old_order_and_claims_nothing(
            self):
        log = Log()
        g = _neighbour_discounted_head(log, tip_found=None)
        with _rank_on():
            adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.reason, "beam_discounted_uncertain")
        self.assertEqual(_beats(v), [0.5, 1.0])
        self.assertEqual(v.detail["bare_stem_likelihood"], "not_claimed")

    def test_a_refused_stroke_AT_THE_TIP_keeps_the_old_order(self):
        """The refused stroke is the thing 2.74's ink test may have got wrong
        (17 of Phase 1's 22 misses): where one stands at the stem's tip the
        quarter is NOT ranked first, even with a clean tip window."""
        log = Log()
        g = _two_staff(log)
        # a decided arc whose box holds a stroke AT the stem tip (y 78..82)
        log.observe(R.glyph(0, 0, 0, 0, 900), Q.ARC_BOX, "slur",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                    x0=60, x1=140, y0=70, y1=90, x_center=100, y_center=80)
        log.observe(CELL, Q.BEAM_STROKE, (60, 78, 80, 4),
                    reader=READERS.CV_LINES, frame="cell:0", x0=60, x1=140,
                    y_center=80, image="no_staff", staff_lines_erased=True)
        s = _stem(log, x=105, y=80)
        _tip(log, s, found=False)
        with _rank_on():
            adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.reason, "beam_discounted_uncertain")
        self.assertTrue(v.detail["bare_stem_refused_stroke_at_tip"])
        self.assertEqual(v.detail["bare_stem_likelihood"], "not_claimed")
        self.assertEqual(_beats(v), [0.5, 1.0])

    def test_a_head_with_no_stem_keeps_the_old_order(self):
        log = Log()
        g = _two_staff(log)
        log.observe(CELL, Q.BEAM_STROKE, (90, 150, 40, 4),
                    reader=READERS.CV_LINES, frame="cell:0", x0=90, x1=130,
                    y_center=152, image="no_staff", staff_lines_erased=True)
        log.observe(R.cell(0, 0, 1, 0), Q.STEM, (90, -10, 4, 50),
                    reader=READERS.CV_LINES, frame="cell:0", x0=90, x1=94,
                    y_center=15, image="no_staff", staff_lines_erased=True)
        with _rank_on():
            adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        if v.outcome is Outcome.NARROWED and \
                v.reason == "beam_discounted_uncertain":
            self.assertEqual(v.detail["bare_stem_likelihood"], "not_claimed")


# ─────────────────────────────────────────────────────────────────────────────
# INFER: the bar's arithmetic
# ─────────────────────────────────────────────────────────────────────────────


def _sub(staff, glyph, cell=0):
    return Subject(Kind.GLYPH, page=0, system=0, staff=staff, cell=cell,
                   glyph=glyph)


def _cell(staff=0, cell=0):
    return Subject(Kind.CELL, page=0, system=0, staff=staff, cell=cell)


def _system():
    return Subject(Kind.SYSTEM, page=0, system=0)


class _Bar:
    """One staff, one bar, events in order, a meter on the system.

    The meter is shaped like `adjudicate_meter`'s: a `voted` verdict that
    USED printed `Q.METER_TEMPLATE` readings (and, like the real one, whose
    `basis` is wide). `meter_reason`/`meter_used_member` bend it for the
    refusals.
    """

    def __init__(self, num=4, den=4, meter_reason="voted", segments=1,
                 carried=False):
        self.log = Log()
        self.events = []
        self.g = 0
        self.num, self.den = num, den
        self.meter_reason = meter_reason
        self.segments = segments
        self.carried = carried
        self.members = []
        self.durations = []
        self.meter_basis_extra = ()
        self.cell_idx = 0

    def _id(self):
        return self.log._next_id("vrd")

    def decided(self, beats, reason="head_and_marks"):
        g = self.g
        self.g += 1
        self.durations.append(self.log.record(Verdict(
            id=self._id(), subject=_sub(0, g, self.cell_idx), quantity=Q.DURATION,
            outcome=Outcome.DECIDED, value={"beats": beats, "written": beats},
            decider="adjudicate_duration", reason=reason)))
        self.events.append([g])
        return g

    def bare(self, quarter_first=True, reason="beam_discounted_uncertain",
             beats=(1.0, 0.5), tip_clean=True):
        g = self.g
        self.g += 1
        sup = (2.0, 1.0) if quarter_first else (1.0, 2.0)
        v = self.log.record(Verdict(
            id=self._id(), subject=_sub(0, g, self.cell_idx), quantity=Q.DURATION,
            outcome=Outcome.NARROWED, value=None,
            decider="adjudicate_duration", reason=reason,
            candidates=tuple(sorted(
                (Candidate({"beats": b, "written": b,
                            "beam_levels": i}, support=s)
                 for i, (b, s) in enumerate(zip(beats, sup))),
                key=lambda c: -c.support)),
            detail={"bare_stem_likelihood": "quarter_first"
                    if quarter_first else "not_claimed",
                    "bare_stem_tip_window_clean": tip_clean}))
        self.events.append([g])
        self.members.append(v)
        return g

    def finish(self):
        self.log.record(Verdict(
            id=self._id(), subject=_cell(0, self.cell_idx), quantity=Q.EVENT,
            outcome=Outcome.DECIDED,
            value={"events": [{"glyphs": e} for e in self.events]},
            decider="test:events", reason="grouped"))
        rows = [self.log.observe(_staff(i), Q.METER_TEMPLATE, 0.9,
                                 reader=READERS.TEMPLATE, frame="page")
                for i in range(3)]
        val = {"numerator": self.num, "denominator": self.den}
        val["segments"] = [dict(val, from_cell=k) for k in range(self.segments)]
        home = Subject(Kind.SYSTEM, page=0, system=5) if self.carried \
            else _system()
        voted = self.log.record(Verdict(
            id=self._id(), subject=home, quantity=Q.METER,
            outcome=Outcome.DECIDED, value=val, decider="adjudicate_meter",
            reason="voted", used=tuple(r.id for r in rows),
            # like the real one: it CONSIDERED every duration of the system
            basis=tuple(r.id for r in rows)
            + tuple(d.id for d in self.durations)
            + tuple(m.id for m in self.members)))
        if self.carried:
            # the system under test CARRIES an earlier system's printed meter
            val2 = dict(val)
            if self.carried == "different":
                val2 = {"numerator": 3, "denominator": 4,
                        "segments": [{"numerator": 3, "denominator": 4,
                                      "from_cell": 0}]}
            self.log.record(Verdict(
                id=self._id(), subject=_system(), quantity=Q.METER,
                outcome=Outcome.DECIDED, value=val2,
                decider="adjudicate_meter", reason="carried",
                used=(voted.id,),
                basis=(voted.id,) + tuple(d.id for d in self.durations)
                + tuple(m.id for m in self.members)))
        elif self.meter_reason != "voted":
            self.log.record(Verdict(
                id=self._id(), subject=_system(), quantity=Q.METER,
                outcome=Outcome.DECIDED, value=val,
                decider="adjudicate_meter", reason=self.meter_reason,
                used=(voted.id,), basis=(voted.id,),
                supersedes=voted.id))
        self.log.freeze()
        return self.log


def _staff(i):
    return Subject(Kind.STAFF, page=0, system=0, staff=i)


def _run(log, *, flag="1"):
    # the 2.97 columns rule (default ON) is a different rule: isolate this one
    env = {infer.NARROWED_BAR_ENV: "0"}
    if flag is not None:
        env[infer.BARE_STEM_BAR_ENV] = flag
    with mock.patch.dict(os.environ, env, clear=False):
        if flag is None:
            os.environ.pop(infer.BARE_STEM_BAR_ENV, None)
        return infer.run(log, evaluate.Report([], [], []))


def _fired(report):
    return [i for i in report.inferred
            if i[0] == infer.Inference.COLLAPSE_BARE_STEM_BY_BAR.value]


class TestTheBarsArithmeticSettlesABareStem(unittest.TestCase):

    def test_three_quarters_and_a_bare_stem_in_4_4_is_a_quarter(self):
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        g = b.bare()
        log = b.finish()
        rep = _run(log)
        self.assertEqual(len(_fired(rep)), 1)
        v = log.verdict(Q.DURATION, _sub(0, g))
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertTrue(v.detail["inferred"])
        self.assertEqual(v.detail["rule"], "collapse_bare_stem_by_bar")
        self.assertTrue(v.decider.startswith("infer:"))

    def test_the_arithmetic_NEVER_says_EIGHTH_without_a_flag_or_beam(self):
        """Sean 2026-10-12 (ROADMAP 2.102): *"only when we see evidence of an
        eighth should it be called that."* 3 quarters + the bare stem in 7/8
        (3.5 beats) forces the EIGHTH arithmetically; the rule refuses it and
        the stem stays narrowed. (Formerly the positive control that it could
        say eighth.)"""
        b = _Bar(7, 8)
        for _ in range(3):
            b.decided(1.0)
        g = b.bare()
        log = b.finish()
        _run(log)
        v = log.verdict(Q.DURATION, _sub(0, g))
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_eighth_first_ranking_does_not_change_the_answer(self):
        """Nothing reads `support`: the same bar, ranked the other way, is
        settled the same way."""
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        g = b.bare(quarter_first=False)
        log = b.finish()
        _run(log)
        self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).value["beats"],
                         1.0)

    def test_two_unknowns_forced_to_EIGHTHS_stay_narrowed(
            self):
        """2 quarters + two bare stems in 3/4 (3.0 beats): the only landing is
        a=b=0.5 -- the shorter length, which the arithmetic may not choose."""
        b = _Bar(3, 4)
        b.decided(1.0)
        b.decided(1.0)
        # a + b == 1.0 -> (0.5, 0.5) only, since (1.0, 1.0) = 2.0 overshoots
        g1, g2 = b.bare(), b.bare()
        log = b.finish()
        _run(log)
        for g in (g1, g2):
            self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).outcome,
                             Outcome.NARROWED)

    def test_a_dotted_beat_value_is_matched_exactly(self):
        """Dotted quarter (1.5) vs dotted eighth (0.75): fractions, not floats."""
        b = _Bar(6, 8)
        b.decided(1.5)
        g = b.bare(beats=(1.5, 0.75))
        log = b.finish()
        _run(log)
        self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).value["beats"],
                         1.5)


class TestItDeclinesWhereTheArithmeticDoesNotForceIt(unittest.TestCase):

    def test_two_landings_leave_both_members_narrowed(self):
        """q,q + two bare stems in 5/8... use 1.5: (1.0,0.5) and (0.5,1.0)
        both land -> the order is the prior's to claim and INFER may not."""
        b = _Bar(3, 8)               # 1.5 beats
        g1, g2 = b.bare(), b.bare()
        log = b.finish()
        rep = _run(log)
        self.assertEqual(_fired(rep), [])
        for g in (g1, g2):
            self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).outcome,
                             Outcome.NARROWED)

    def test_a_bar_that_does_not_add_up_under_any_assignment_is_left_alone(
            self):
        b = _Bar()                   # 4.0
        b.decided(1.0)
        b.decided(1.0)
        g = b.bare()                 # 2.0 + {1.0, 0.5} never reaches 4.0
        log = b.finish()
        rep = _run(log)
        self.assertEqual(_fired(rep), [])
        self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).outcome,
                         Outcome.NARROWED)

    def test_CONTROL_the_same_bar_that_does_add_up_IS_settled(self):
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        g = b.bare()
        log = b.finish()
        _run(log)
        self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).outcome,
                         Outcome.DECIDED)

    def test_a_tip_that_was_not_SEEN_clean_is_left_narrowed(self):
        """Sean's condition. The same bar, the same arithmetic -- but this
        head's stem-tip window was occupied (or never read): the one wrong
        decision on his hand-truth page was a head like this."""
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        g = b.bare(tip_clean=False)
        log = b.finish()
        rep = _run(log)
        self.assertEqual(_fired(rep), [])
        self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).outcome,
                         Outcome.NARROWED)
        self.assertEqual(
            inferences.solve_bare_stem_bar(log, _cell()).tip_not_clean, 1)

    def test_a_tip_window_with_no_reading_at_all_is_left_narrowed(self):
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        g = b.bare(tip_clean=None)
        log = b.finish()
        self.assertEqual(_fired(_run(log)), [])

    def test_it_speaks_only_into_beam_discounted_uncertain(self):
        """A narrowing of any OTHER reason (here `beams_ambiguous`) in the
        identical bar is not this item's and is left alone."""
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        g = b.bare(reason="beams_ambiguous")
        log = b.finish()
        rep = _run(log)
        self.assertEqual(_fired(rep), [])
        self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).outcome,
                         Outcome.NARROWED)

    def test_a_meter_DERIVED_FROM_THE_BARS_is_not_an_umpire(self):
        """`adjudicate_meter`'s own bars-derived reasons reach no printed
        reading: declined by name, whatever the bar sums to."""
        for why in ("derived_from_bars", "carry_outweighed_by_the_bars"):
            b = _Bar(meter_reason=why)
            for _ in range(3):
                b.decided(1.0)
            g = b.bare()
            log = b.finish()
            rep = _run(log)
            self.assertEqual(_fired(rep), [], why)
            self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).outcome,
                             Outcome.NARROWED)
            self.assertEqual(
                inferences.solve_bare_stem_bar(log, _cell()).decline,
                "meter_not_from_the_print")

    def test_a_CARRIED_printed_meter_settles_through_the_chain(self):
        b = _Bar(carried=True)
        for _ in range(3):
            b.decided(1.0)
        g = b.bare()
        log = b.finish()
        self.assertEqual(log.verdict(Q.METER, _system()).reason, "carried")
        _run(log)
        self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).outcome,
                         Outcome.DECIDED)

    def test_a_carry_whose_value_is_not_the_sources_is_declined(self):
        b = _Bar(carried="different")
        for _ in range(3):
            b.decided(1.0)
        g = b.bare()
        log = b.finish()
        self.assertEqual(
            inferences.solve_bare_stem_bar(log, _cell()).decline,
            "meter_not_from_the_print")

    def test_a_bar_AT_a_printed_change_is_declined_and_one_BEFORE_it_is_not(
            self):
        """Segments: the opening meter from cell 0, a change from cell 1. The
        bar under test is cell 0 (before it) -- served; a copy of the same
        bar at cell 1 (the change) -- declined."""
        for cell_idx, settled in ((0, True), (1, False)):
            b = _Bar(segments=2)
            b.cell_idx = cell_idx
            for _ in range(3):
                b.decided(1.0)
            g = b.bare()
            log = b.finish()
            out = inferences.solve_bare_stem_bar(log, _cell(0, cell_idx))
            if settled:
                self.assertIsNone(out.decline)
                self.assertEqual(out.forced, 1)
            else:
                self.assertEqual(out.decline, "meter_not_from_the_print")

    def test_POSITIVE_CONTROL_a_wide_basis_alone_does_not_decline_it(self):
        """The real verdict's `basis` holds EVERY duration of the system, the
        narrowing included. Only what it USED is the evidence: this is the
        fixture the first draft of the rule failed on 99 of 102 Brahms
        members."""
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        g = b.bare()
        log = b.finish()
        self.assertIn(b.members[0].id, log.closure(
            log.verdict(Q.METER, _system()).id))
        _run(log)
        self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).outcome,
                         Outcome.DECIDED)

    def test_no_decided_meter_no_inference(self):
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        g = b.bare()
        b.log.record(Verdict(
            id=b._id(), subject=_cell(), quantity=Q.EVENT,
            outcome=Outcome.DECIDED,
            value={"events": [{"glyphs": e} for e in b.events]},
            decider="t", reason="r"))
        b.log.freeze()
        rep = _run(b.log)
        self.assertEqual(_fired(rep), [])
        self.assertEqual(b.log.verdict(Q.DURATION, _sub(0, g)).outcome,
                         Outcome.NARROWED)


class TestTheFlagAndTheLabel(unittest.TestCase):

    def _bar(self):
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        g = b.bare()
        return b.finish(), g

    def test_default_ON(self):
        log, g = self._bar()
        rep = _run(log, flag=None)
        self.assertEqual(len(_fired(rep)), 1)
        self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).outcome,
                         Outcome.DECIDED)

    def test_an_explicit_off_word_turns_it_off_and_a_typo_leaves_it_on(self):
        for word in ("0", "off", "false", "no", ""):
            log, g = self._bar()
            rep = _run(log, flag=word)
            self.assertEqual(_fired(rep), [], word)
            self.assertIn(("collapse_bare_stem_by_bar",
                           infer.BARE_STEM_BAR_ENV),
                          [tuple(d) for d in rep.disabled])
        for word in ("nope", "1", "on"):
            log, g = self._bar()
            self.assertEqual(len(_fired(_run(log, flag=word))), 1, word)

    def test_the_answer_is_a_candidate_the_reader_admitted_and_is_labelled(
            self):
        log, g = self._bar()
        _run(log)
        v = log.verdict(Q.DURATION, _sub(0, g))
        self.assertTrue(infer.is_inferred(v))
        admitted = [c.value["beats"] for c in v.candidates]
        self.assertIn(v.value["beats"], admitted)

    def test_the_rule_declares_that_it_reads_the_meter(self):
        """⚠️ By `.value`, not identity: `test_infer_bypass` reloads `infer`,
        which mints a NEW `Inference` enum and leaves the registry holding
        members of the old one."""
        infer._ensure_rules()
        r = [r for r in infer.RULES
             if r.inference.value == "collapse_bare_stem_by_bar"][0]
        self.assertIn(Q.METER, r.reads)
        self.assertTrue(infer.scoring_conflict(r, [Q.METER]))

    def test_it_is_the_ONE_registered_rule_that_reads_the_meter(self):
        """The registry-wide invariant `test_infer_barline_rule` pins (no
        rule reads the meter, so bar-fill stays a legitimate self-check)
        carries exactly this named exception. It is default ON since
        2026-10-11 (Sean), so `self_check.py` looks only at the rules that RAN
        and refuses to score a run by bar-fill while it is enabled."""
        infer._ensure_rules()
        readers = [r for r in infer.RULES if Q.METER in r.reads]
        self.assertEqual([r.inference.value for r in readers],
                         ["collapse_bare_stem_by_bar", "collapse_narrowed_by_bar"])
        with mock.patch.dict(os.environ, {infer.BARE_STEM_BAR_ENV: "0"}):
            self.assertNotIn(
                "collapse_bare_stem_by_bar",
                [r.inference.value for r in infer.enabled_rules()])
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(infer.BARE_STEM_BAR_ENV, None)
            self.assertIn(
                "collapse_bare_stem_by_bar",
                [r.inference.value for r in infer.enabled_rules()])


if __name__ == "__main__":
    unittest.main()


_BAR_SUM_CONFIRM_ONLY_WAS = None


def setUpModule():
    """These tests pin the bar-sum deciders as shipped BEFORE ROADMAP 2.154 (the bar may choose among a narrowing's
    candidates); `OMR_BAR_SUM_CONFIRM_ONLY` went default ON at arm a 2026-10-16 (Sean), so this module runs with it off.
    The arm-a behaviour is tested in `test_staged_bar_sum_confirm_only_2_154.py`."""
    import os
    global _BAR_SUM_CONFIRM_ONLY_WAS
    _BAR_SUM_CONFIRM_ONLY_WAS = os.environ.get("OMR_BAR_SUM_CONFIRM_ONLY")
    os.environ["OMR_BAR_SUM_CONFIRM_ONLY"] = "off"


def tearDownModule():
    import os
    if _BAR_SUM_CONFIRM_ONLY_WAS is None:
        os.environ.pop("OMR_BAR_SUM_CONFIRM_ONLY", None)
    else:
        os.environ["OMR_BAR_SUM_CONFIRM_ONLY"] = _BAR_SUM_CONFIRM_ONLY_WAS
