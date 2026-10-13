"""ROADMAP 2.97 -- narrowed notes whose own candidates land the bar are settled
by the bar (Sean 2026-10-12, "Send out 1-3").

Three parts, two stages, said plainly:

  * EVALUATE, `reconcile_duration` (the answer FOLLOWS: one event, an exact
    landing, a unique answer -- the rule's existing bound with the UNIT moved
    from a notehead to an event):
      - a chord whose every head is narrowed is ONE unit (one stem, one
        value, 2.78) -- before, its two heads were two landings of the same
        arithmetic and the rule refused on "not unique";
      - a landing made on a DECIDED note settles the bar's narrowed events
        beside it only where the JOINT search (narrowed events over their own
        candidates x at most one decided re-reading) is itself unique.
  * INFER, `collapse_narrowed_by_bar` (the answer is merely BEST, so it is
    labelled, gated and bounded to the reader's own candidates): any narrowed
    head or chord, jointly over several columns, only where EVERY landing
    agrees, on a meter that reaches the PRINT.

Each refusal has a positive control in the same class (two assignments fit ->
abstain; the same bar with one fitting -> settled).
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import consequences, evaluate, infer, inferences
from tools.omr.staged import record as R
from tools.omr.staged.record import (Candidate, Kind, Log, Outcome, Q, Subject,
                                     Verdict)
from tools.omr.tests.test_staged_bare_stem_2_81 import (_Bar, _cell, _staff,
                                                        _sub, _system)
from tools.omr.tests.test_staged_missed_rest_2_80 import ink


# ─────────────────────────────────────────────────────────────────────────────
# EVALUATE: reconcile_duration
# ─────────────────────────────────────────────────────────────────────────────

CELL = R.cell(0, 0, 1, 3)


def _v(log, sub, q, outcome, value, reason="t", candidates=(), detail=None):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome,
        value=value, decider="test", reason=reason, candidates=tuple(candidates),
        detail=detail or {}))


def _stem(log, sub, sid="stem:1"):
    """A head's DECIDED `Q.HEAD_STEM`: heads sharing an id stand on one stem."""
    return _v(log, sub, Q.HEAD_STEM, Outcome.DECIDED, sid)


def _dv(beats, levels=0):
    return {"beats": beats, "written": beats, "dots": 0, "beam_levels": levels}


class _EvalBar:
    """One bar for `reconcile_duration`: events built in order, a meter, and
    (optionally) a cell-ink reading that is clear."""

    def __init__(self, num=4, den=4, clear_ink=True):
        self.log = Log()
        self.g = 0
        self.events = []
        self.num, self.den, self.clear = num, den, clear_ink

    def _sub(self):
        s = R.glyph(0, 0, 1, 3, self.g)
        self.g += 1
        return s

    def decided(self, beats, levels=0, rest=False):
        s = self._sub()
        val = _dv(beats, levels)
        if rest:
            val["is_rest"] = True
        _v(self.log, s, Q.DURATION, Outcome.DECIDED, val,
           reason="rest_class" if rest else "head_and_marks")
        self.events.append([s.glyph])
        return s

    def _narrowed(self, cands):
        s = self._sub()
        _v(self.log, s, Q.DURATION, Outcome.NARROWED, None,
           reason="beam_discounted_uncertain",
           candidates=[Candidate(_dv(b, lv), support=sup)
                       for (b, lv, sup) in cands])
        return s

    def narrowed(self, cands=((0.5, 1, 2.0), (1.0, 0, 1.0))):
        s = self._narrowed(cands)
        self.events.append([s.glyph])
        return s

    def chord(self, n=2, cands=((0.5, 1, 2.0), (1.0, 0, 1.0)), stem="stem:1"):
        ss = [self._narrowed(cands) for _ in range(n)]
        for x in ss:
            _stem(self.log, x, stem)
        self.events.append([s.glyph for s in ss])
        return ss

    def mixed_chord(self, cands=((0.5, 1, 2.0), (1.0, 0, 1.0))):
        n = self._narrowed(cands)
        d = self.decided(1.0)
        self.events.pop()                      # the decided one joins the chord
        self.events.append([n.glyph, d.glyph])
        return n, d

    def build(self):
        _v(self.log, CELL, Q.EVENT, Outcome.DECIDED,
           {"events": [{"glyphs": e} for e in self.events]})
        if self.clear:
            ink(self.log, cell=CELL)
        meter = _v(self.log, R.system(0, 0), Q.METER, Outcome.DECIDED,
                   {"numerator": self.num, "denominator": self.den,
                    "raw": f"{self.num}/{self.den}"})
        return self.log, meter

    def fire(self):
        log, meter = self.build()
        return log, consequences.reconcile_duration(log, CELL, meter)


class TestAChordIsOneUnit(unittest.TestCase):

    def test_two_narrowed_heads_of_one_chord_land_the_bar_together_RED(self):
        """3 quarters + a chord of two heads each narrowed {eighth, quarter}
        in 4/4. Per head this was TWO landings (either head to a quarter
        gives 4.0) and the rule refused; as one event it is ONE."""
        b = _EvalBar()
        for _ in range(3):
            b.decided(1.0)
        heads = b.chord(2)
        log, out = b.fire()
        self.assertEqual(len(out), 2)
        for h in heads:
            v = log.verdict(Q.DURATION, h)
            self.assertEqual(v.outcome, Outcome.DECIDED)
            self.assertEqual(v.value["beats"], 1.0)
            self.assertEqual(v.decider, "reconcile_duration")
            self.assertEqual(v.detail["chord_of"], 2)

    def test_the_chosen_value_is_one_of_each_heads_own_candidates(self):
        b = _EvalBar()
        for _ in range(3):
            b.decided(1.0)
        heads = b.chord(3)
        log, _out = b.fire()
        for h in heads:
            old = [v for v in log._vrd.values()
                   if v.subject == h and v.outcome is Outcome.NARROWED][0]
            now = log.verdict(Q.DURATION, h)
            self.assertIn(now.value["beats"],
                          [c.value["beats"] for c in old.candidates])
            self.assertEqual(now.supersedes, old.id)

    def test_CONTROL_a_chord_that_admits_no_common_length_is_left_alone(self):
        """The heads' candidate sets share no length: there is nothing the
        event can take, so nothing is written."""
        b = _EvalBar()
        for _ in range(3):
            b.decided(1.0)
        n1 = b._narrowed(((0.5, 1, 2.0), (1.0, 0, 1.0)))
        n2 = b._narrowed(((0.25, 2, 2.0), (2.0, 0, 1.0)))
        _stem(b.log, n1)
        _stem(b.log, n2)
        b.events.append([n1.glyph, n2.glyph])
        log, out = b.fire()
        self.assertEqual(out, [])
        self.assertEqual(log.verdict(Q.DURATION, n1).outcome, Outcome.NARROWED)

    def test_two_landings_still_refuse_a_chord_beside_another_narrowed_head(
            self):
        """The unique-answer bound is unchanged: a chord and a single narrowed
        head that EACH could carry the bar are two landings."""
        b = _EvalBar()
        b.decided(1.0)
        b.decided(1.0)
        b.chord(2, cands=((0.5, 1, 2.0), (1.0, 0, 1.0)))
        b.narrowed()
        # best total 2 + 0.5 + 0.5 = 3.0; 3.5 is reached by EITHER one -> 2
        b.num, b.den = 7, 8
        log, out = b.fire()
        self.assertEqual(out, [])

    def test_a_chord_with_a_DECIDED_head_is_not_a_narrowed_chord(self):
        """A mixed event stays per head (2.89 owns its value)."""
        b = _EvalBar()
        b.decided(1.0)
        b.decided(1.0)
        n, d = b.mixed_chord()
        b.decided(1.0)
        log, meter = b.build()
        self.assertEqual(consequences._narrowed_chords(
            log, CELL, [v for v in consequences._standing(log, CELL, Q.DURATION)]),
            [])

    def test_CONTROL_heads_on_TWO_stems_are_two_voices_not_one_chord(self):
        """Sean's hand-truth page: a grouped 'chord' whose heads print a
        dotted quarter and a quarter. Without one decided stem the heads
        change nothing together."""
        b = _EvalBar()
        for _ in range(3):
            b.decided(1.0)
        n1 = b._narrowed(((0.5, 1, 2.0), (1.0, 0, 1.0)))
        n2 = b._narrowed(((0.5, 1, 2.0), (1.0, 0, 1.0)))
        _stem(b.log, n1, "stem:1")
        _stem(b.log, n2, "stem:2")
        b.events.append([n1.glyph, n2.glyph])
        log, out = b.fire()
        self.assertEqual(out, [])
        self.assertEqual(log.verdict(Q.DURATION, n1).outcome, Outcome.NARROWED)

    def test_a_single_narrowed_head_is_unchanged(self):
        """Positive control for the old path: one head, one landing."""
        b = _EvalBar()
        for _ in range(3):
            b.decided(1.0)
        h = b.narrowed()
        log, out = b.fire()
        self.assertEqual(len(out), 1)
        self.assertEqual(log.verdict(Q.DURATION, h).value["beats"], 1.0)

    def test_a_LENGTHENING_still_needs_the_ink_witness_for_a_chord(self):
        b = _EvalBar(clear_ink=False)
        for _ in range(3):
            b.decided(1.0)
        heads = b.chord(2)
        log, out = b.fire()                  # ink unread: rule 8
        self.assertEqual(out, [])
        self.assertEqual(log.verdict(Q.DURATION, heads[0]).outcome,
                         Outcome.NARROWED)


class TestALandingOnADecidedNoteLeavesTheNarrowedBesideItNarrowed(unittest.TestCase):
    """REFUSED on Sean's blind tiles 2026-10-12 (singles 1-4 all wrong: bare
    stems settled to an eighth that print a quarter). The old rule's landing
    on the decided neighbour is unchanged; the narrowed head stays narrowed."""

    def test_the_narrowed_head_is_NOT_settled_beside_the_landing(self):
        b = _EvalBar(2, 4)
        n = b.narrowed()
        d = b.decided(1.0)
        b.decided(1.0, rest=True)
        log, out = b.fire()
        self.assertEqual(log.verdict(Q.DURATION, d).value["beats"], 0.5)
        self.assertEqual(log.verdict(Q.DURATION, n).outcome, Outcome.NARROWED)


# ─────────────────────────────────────────────────────────────────────────────
# INFER: collapse_narrowed_by_bar
# ─────────────────────────────────────────────────────────────────────────────


class _InferBar(_Bar):
    """`_Bar` plus a chord event and a cell-ink reading."""

    def __init__(self, *a, ink_read=True, **kw):
        super().__init__(*a, **kw)
        self.ink_read = ink_read

    def narrowed_chord(self, n=2, reason="beams_ambiguous",
                       beats=(0.5, 1.0), sup=(2.0, 1.0), stem="stem:1",
                       detail=None):
        gs = []
        for _ in range(n):
            g = self.g
            self.g += 1
            self.members.append(self.log.record(Verdict(
                id=self._id(), subject=_sub(0, g, self.cell_idx),
                quantity=Q.DURATION, outcome=Outcome.NARROWED, value=None,
                decider="adjudicate_duration", reason=reason,
                candidates=tuple(
                    Candidate({"beats": b, "written": b,
                               "beam_levels": 0 if b == max(beats) else 1},
                              support=s)
                    for b, s in zip(beats, sup)),
                detail=dict(detail or {}))))
            _stem(self.log, _sub(0, g, self.cell_idx), stem)
            gs.append(g)
        self.events.append(gs)
        return gs

    def finish(self):
        if self.ink_read:
            from tools.omr.tests.test_staged_missed_rest_2_80 import clear_ink
            clear_ink(self.log, _cell(0, self.cell_idx))
        return super().finish()


def _run(log, *, on=True):
    env = {infer.NARROWED_BAR_ENV: "1" if on else "0"}
    with mock.patch.dict(os.environ, env, clear=False):
        return infer.run(log, evaluate.Report([], [], []))


def _fired(report):
    return [i for i in report.inferred
            if i[0] == infer.Inference.COLLAPSE_NARROWED_BY_BAR.value]


def _val(log, g):
    return log.verdict(Q.DURATION, _sub(0, g))


class TestAnyNarrowedHeadIsSettledByTheBar(unittest.TestCase):

    def test_a_narrowed_head_of_ANY_reason_is_settled_RED(self):
        b = _InferBar()
        for _ in range(3):
            b.decided(1.0)
        (g,) = b.narrowed_chord(1)
        log = b.finish()
        rep = _run(log)
        self.assertEqual(len(_fired(rep)), 1)
        v = _val(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertTrue(v.decider.startswith("infer:"))
        self.assertEqual(v.detail["rule"], "collapse_narrowed_by_bar")

    def test_CONTROL_the_bare_stem_rule_alone_does_not_touch_that_reason(self):
        b = _InferBar()
        for _ in range(3):
            b.decided(1.0)
        (g,) = b.narrowed_chord(1)
        log = b.finish()
        _run(log, on=False)
        self.assertEqual(_val(log, g).outcome, Outcome.NARROWED)

    def test_the_flag_is_a_deny_list_default_ON(self):
        for word, settled in (("", False), ("nope", True), ("1", True),
                              ("0", False), ("off", False), ("no", False)):
            b = _InferBar()
            for _ in range(3):
                b.decided(1.0)
            (g,) = b.narrowed_chord(1)
            log = b.finish()
            with mock.patch.dict(os.environ, {infer.NARROWED_BAR_ENV: word}):
                infer.run(log, evaluate.Report([], [], []))
            want = Outcome.DECIDED if settled else Outcome.NARROWED
            self.assertEqual(_val(log, g).outcome, want, word)

    def test_the_value_is_always_one_of_the_readers_own_candidates(self):
        b = _InferBar(7, 8)
        for _ in range(3):
            b.decided(1.0)
        (g,) = b.narrowed_chord(1, detail={"flag_levels": 1})
        log = b.finish()
        _run(log)
        v = _val(log, g)
        self.assertEqual(v.value["beats"], 0.5)        # shortening, no witness
        self.assertIn(v.value["beats"], (0.5, 1.0))


class TestAChordChangesTogether(unittest.TestCase):

    def test_both_heads_of_a_narrowed_chord_get_the_same_value_RED(self):
        b = _InferBar()
        for _ in range(3):
            b.decided(1.0)
        gs = b.narrowed_chord(2)
        log = b.finish()
        _run(log)
        vals = [_val(log, g) for g in gs]
        self.assertEqual({v.outcome for v in vals}, {Outcome.DECIDED})
        self.assertEqual({v.value["beats"] for v in vals}, {1.0})

    def test_CONTROL_a_chord_whose_heads_admit_different_lengths_declines(
            self):
        b = _InferBar()
        for _ in range(3):
            b.decided(1.0)
        a = b.narrowed_chord(1)[0]
        c = b.narrowed_chord(1, beats=(0.25, 2.0))[0]
        b.events[-2:] = [[a, c]]
        log = b.finish()
        self.assertEqual(
            inferences.solve_bare_stem_bar(log, _cell(),
                                           any_reason=True).decline,
            "event_members_admit_different_lengths")


class TestAChordNeedsOneStemForInferToo(unittest.TestCase):

    def test_heads_on_two_stems_are_declined(self):
        b = _InferBar()
        for _ in range(3):
            b.decided(1.0)
        a = b.narrowed_chord(1, stem="stem:1")[0]
        c = b.narrowed_chord(1, stem="stem:2")[0]
        b.events[-2:] = [[a, c]]
        log = b.finish()
        self.assertEqual(
            inferences.solve_bare_stem_bar(log, _cell(),
                                           any_reason=True).decline,
            "chord_not_on_one_decided_stem")


class TestSeveralColumnsJointly(unittest.TestCase):

    def test_exactly_one_joint_assignment_settles_every_column_RED(self):
        """3/4, two quarters, two narrowed columns {eighth, quarter}: a + b = 1
        has the single landing (0.5, 0.5)."""
        b = _InferBar(3, 4)
        b.decided(1.0)
        b.decided(1.0)
        ev = {"beams_by_stem": 1}
        g1 = b.narrowed_chord(1, detail=ev)[0]
        g2 = b.narrowed_chord(1, detail=ev)[0]
        log = b.finish()
        _run(log)
        for g in (g1, g2):
            self.assertEqual(_val(log, g).value["beats"], 0.5)
            self.assertEqual(_val(log, g).detail["eighth_evidence"],
                             ["beam_joined_to_stem"])

    def test_two_assignments_that_fit_abstain_POSITIVE_CONTROL(self):
        """Same two columns in 3/8-worth of room (1.5): (1.0, 0.5) and
        (0.5, 1.0) both land -- the rule may not choose."""
        b = _InferBar(3, 8)
        g1 = b.narrowed_chord(1)[0]
        g2 = b.narrowed_chord(1)[0]
        log = b.finish()
        rep = _run(log)
        self.assertEqual(_fired(rep), [])
        for g in (g1, g2):
            self.assertEqual(_val(log, g).outcome, Outcome.NARROWED)

    def test_a_bar_that_adds_up_under_no_assignment_is_left_alone(self):
        b = _InferBar(4, 4)
        b.decided(1.0)
        g1 = b.narrowed_chord(1)[0]
        g2 = b.narrowed_chord(1)[0]
        log = b.finish()
        self.assertEqual(_fired(_run(log)), [])
        self.assertEqual(_val(log, g1).outcome, Outcome.NARROWED)


class TestTheMeterMustReachThePrint(unittest.TestCase):

    def test_a_meter_chosen_by_the_bars_is_no_umpire(self):
        for why in ("derived_from_bars", "carry_outweighed_by_the_bars"):
            b = _InferBar(meter_reason=why)
            for _ in range(3):
                b.decided(1.0)
            (g,) = b.narrowed_chord(1)
            log = b.finish()
            self.assertEqual(_fired(_run(log)), [], why)
            self.assertEqual(
                inferences.solve_bare_stem_bar(
                    log, _cell(), any_reason=True).decline,
                "meter_not_from_the_print")

    def test_an_ABSTAINED_meter_settles_nothing(self):
        b = _InferBar()
        for _ in range(3):
            b.decided(1.0)
        (g,) = b.narrowed_chord(1)
        log = b.finish()
        cur = log.verdict(Q.METER, _system())
        log.record(Verdict(
            id=log._next_id("vrd"), subject=_system(), quantity=Q.METER,
            outcome=Outcome.ABSTAINED, value=None, decider="adjudicate_meter",
            reason="carry_not_corroborated", supersedes=cur.id))
        self.assertEqual(
            inferences.solve_bare_stem_bar(log, _cell(),
                                           any_reason=True).decline,
            "no_decided_meter")


class TestALengtheningNeedsTheInkWitness(unittest.TestCase):

    def test_a_bar_that_needs_the_LONGER_candidate_is_refused_with_ink_unread(
            self):
        """Best-supported is the eighth; the bar needs the quarter. A missed
        rest fills the same gap (2.80), so with the ink never read (rule 8)
        the head stays narrowed."""
        b = _InferBar(ink_read=False)
        for _ in range(3):
            b.decided(1.0)
        (g,) = b.narrowed_chord(1)
        log = b.finish()
        self.assertEqual(_fired(_run(log)), [])
        self.assertEqual(_val(log, g).outcome, Outcome.NARROWED)
        o = inferences.solve_bare_stem_bar(log, _cell(), any_reason=True)
        self.assertEqual(o.lengthening_unwitnessed, 1)

    def test_POSITIVE_CONTROL_the_same_bar_with_the_ink_read_clear_is_settled(
            self):
        b = _InferBar(ink_read=True)
        for _ in range(3):
            b.decided(1.0)
        (g,) = b.narrowed_chord(1)
        log = b.finish()
        _run(log)
        self.assertEqual(_val(log, g).value["beats"], 1.0)

    def test_a_bar_with_unexplained_ink_is_refused_even_when_read(self):
        b = _InferBar(ink_read=False)
        for _ in range(3):
            b.decided(1.0)
        (g,) = b.narrowed_chord(1)
        # a rest-sized piece no glyph box explains
        ink(b.log, (10, 10, 40, 40), cell=_cell(0, b.cell_idx))
        log = b.finish()
        self.assertEqual(_fired(_run(log)), [])


class TestABareStemTipStillCounts(unittest.TestCase):

    def test_a_tip_not_seen_clean_is_refused_by_the_2_81_rule_and_by_this_one_without_ink(
            self):
        b = _InferBar(ink_read=False)
        for _ in range(3):
            b.decided(1.0)
        g = b.bare(tip_clean=False)
        log = b.finish()
        self.assertEqual(_fired(_run(log)), [])
        self.assertEqual(_val(log, g).outcome, Outcome.NARROWED)

    def test_the_same_head_with_the_bars_ink_wholly_explained_is_settled(self):
        b = _InferBar(ink_read=True)
        for _ in range(3):
            b.decided(1.0)
        g = b.bare(tip_clean=False)
        log = b.finish()
        _run(log)
        self.assertEqual(_val(log, g).value["beats"], 1.0)

    def test_2_81_alone_is_unchanged(self):
        b = _InferBar(ink_read=True)
        for _ in range(3):
            b.decided(1.0)
        g = b.bare(tip_clean=False)
        log = b.finish()
        o = inferences.solve_bare_stem_bar(log, _cell())
        self.assertEqual(o.tip_not_clean, 1)
        self.assertEqual(o.forced, 0)


# ─────────────────────────────────────────────────────────────────────────────
# The heads must be THIS staff's own, one box each (the blind tiles, 2.97)
# ─────────────────────────────────────────────────────────────────────────────


def _box(log, sub, x0, y0, x1, y1):
    from tools.omr.staged.record import READERS
    log.observe(sub, Q.GLYPH_BOX, ["noteheadBlack", 0, 0, 0, 0],
                reader=READERS.DETECTOR, frame="cell",
                bbox_page_px=[x0, y0, x1, y1])


def _lines(log, staff_sub, top=100.0, sp=10.0):
    from tools.omr.staged.record import READERS
    log.observe(staff_sub, Q.STAFF_LINES, [top + i * sp for i in range(5)],
                reader=READERS.GEOMETRY, frame="page")


class TestTheHeadsAreThisStaffsOwn(unittest.TestCase):

    def _bar(self, boxes):
        """3 quarters + one narrowed head; `boxes` = page boxes for glyphs
        0..3 (None = no box). Staff lines 100..140, space 10."""
        b = _InferBar()
        for _ in range(3):
            b.decided(1.0)
        b.narrowed_chord(1)
        for g, bx in enumerate(boxes):
            if bx:
                _box(b.log, _sub(0, g, b.cell_idx), *bx)
        _lines(b.log, _staff(0))
        return b.finish()

    CLEAN = [(10, 100, 24, 112), (40, 110, 54, 122), (70, 120, 84, 132),
             (100, 125, 114, 137)]

    def test_POSITIVE_CONTROL_clean_heads_are_settled(self):
        log = self._bar(self.CLEAN)
        _run(log)
        self.assertEqual(_val(log, 3).outcome, Outcome.DECIDED)

    def test_one_head_boxed_twice_blocks_the_bar_RED(self):
        boxes = list(self.CLEAN)
        boxes[3] = (70, 120, 84, 132)          # on top of glyph 2's box
        log = self._bar(boxes)
        self.assertEqual(_fired(_run(log)), [])
        self.assertEqual(inferences.solve_bare_stem_bar(
            log, _cell(), any_reason=True).decline, "heads_not_this_staffs_own")

    def test_a_head_standing_above_the_staff_blocks_the_bar_RED(self):
        boxes = list(self.CLEAN)
        boxes[0] = (10, 40, 24, 52)           # 6 spaces above the top line
        log = self._bar(boxes)
        self.assertEqual(_fired(_run(log)), [])

    def test_a_head_the_NEIGHBOUR_staff_also_boxed_blocks_the_bar(self):
        b = _InferBar()
        for _ in range(3):
            b.decided(1.0)
        b.narrowed_chord(1)
        for g, bx in enumerate(self.CLEAN):
            _box(b.log, _sub(0, g, b.cell_idx), *bx)
        _lines(b.log, _staff(0))
        # staff 1 holds a kept box on glyph 3's ink
        _box(b.log, Subject(Kind.GLYPH, page=0, system=0, staff=1, cell=0,
                            glyph=0), 100, 125, 114, 137)
        log = b.finish()
        self.assertEqual(_fired(_run(log)), [])


class TestATupletBarIsNotSettledByItsSum(unittest.TestCase):
    """2.101: in a 3-quarter triplet the sum lands as an eighth."""

    def _bar(self, tuplet):
        b = _InferBar()
        for _ in range(3):
            b.decided(1.0)
        b.narrowed_chord(1)
        if tuplet:
            from tools.omr.staged.record import READERS
            b.log.observe(_sub(0, 9, b.cell_idx), Q.TUPLET_MARKER, "tuplet3",
                          reader=READERS.DETECTOR, frame="cell", x0=0, x1=10,
                          x_center=5)
        return b.finish()

    def test_a_printed_tuplet_marker_blocks_the_inference_RED(self):
        log = self._bar(True)
        self.assertEqual(_fired(_run(log)), [])
        self.assertEqual(inferences.solve_bare_stem_bar(
            log, _cell(), any_reason=True).decline, "tuplet_in_bar")

    def test_POSITIVE_CONTROL_the_same_bar_without_one_is_settled(self):
        log = self._bar(False)
        self.assertEqual(len(_fired(_run(log))), 1)

    def test_a_tuplet_marker_blocks_the_chord_landing_in_EVALUATE(self):
        b = _EvalBar()
        for _ in range(3):
            b.decided(1.0)
        b.chord(2)
        from tools.omr.staged.record import READERS
        b.log.observe(R.glyph(0, 0, 1, 3, 40), Q.TUPLET_MARKER, "tuplet3",
                      reader=READERS.DETECTOR, frame="cell", x0=0, x1=10,
                      x_center=5)
        log, out = b.fire()
        self.assertEqual(out, [])


class TestAnEighthNeedsEvidenceOfItsOwn(unittest.TestCase):
    """Sean 2026-10-12: the bar may CONFIRM an eighth that has its own
    evidence, never SUPPLY one. His tiles 1-4: bare stems with only REFUSED
    strokes (`too_thin`), all quarters."""

    def _bar(self, detail):
        b = _InferBar(7, 8)
        for _ in range(3):
            b.decided(1.0)
        (g,) = b.narrowed_chord(1, detail=detail)
        return b.finish(), g

    def test_the_sum_alone_does_not_make_an_eighth_RED(self):
        log, g = self._bar({})
        self.assertEqual(_fired(_run(log)), [])
        self.assertEqual(_val(log, g).outcome, Outcome.NARROWED)

    def test_a_REFUSED_stroke_is_not_evidence(self):
        log, g = self._bar({"beams_not_by_ink": 2,
                            "beams_not_by_ink_why": {"too_thin": 2}})
        self.assertEqual(_fired(_run(log)), [])

    def test_POSITIVE_CONTROL_a_flag_read_on_the_stem_lets_the_sum_confirm_it(self):
        log, g = self._bar({"flag_levels": 1})
        _run(log)
        v = _val(log, g)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["eighth_evidence"], ["flag_read_on_stem"])

    def test_the_LONGER_candidate_needs_no_evidence(self):
        b = _InferBar()
        for _ in range(3):
            b.decided(1.0)
        (g,) = b.narrowed_chord(1)
        log = b.finish()
        _run(log)
        self.assertEqual(_val(log, g).value["beats"], 1.0)


if __name__ == "__main__":
    unittest.main()
