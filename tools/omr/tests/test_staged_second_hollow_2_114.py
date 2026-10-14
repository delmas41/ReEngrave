"""ROADMAP 2.114 -- a SECOND detector at GATHER for hollow noteheads only; the head's own interior decides a disagreement.

Production's boxes are read exactly as today. A hollow-tuned model's boxes (hollow classes only) are filed as a separate witness
(`Q.SECOND_HOLLOW`, reader `SECOND_DETECTOR`); where it and production disagree on a head, or production saw nothing, the head's OWN ink decides
(Sean 2026-10-13: *"It needs to be a certain amount of white on the inside of the notehead"* -- the 2.88 reading, not a clear middle).

RUN RED FIRST against the tree before this change (`ca46eae4`): every test here fails on `AttributeError: Q.SECOND_HOLLOW` / a missing module.
The controls (flag OFF identical, non-hollow classes ignored, a filled head stays black, a DECIDED verdict is not overturned) are the ones that
can fail if the change leaks. NO TEST ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md 6c).
"""
from __future__ import annotations

import json
import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences  # noqa: F401
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged import second_hollow as SH
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS

from tools.omr.tests.test_staged_duration import CELL, _beam, _dot, _note, _staff_space, _stem
from tools.omr.tests.test_staged_pipeline import FakeDet, FakeDetector, build_page


def _dump(log):
    return json.dumps(log.to_json(), sort_keys=True, default=str)


# ─────────────────────────── the pure helpers ───────────────────────────
class TestOnlyHollowHeadsAreKept(unittest.TestCase):

    def test_the_kept_classes_are_exactly_the_regular_hollow_heads(self):
        self.assertEqual(SH.HOLLOW_CLASSES, {
            "noteheadHalfOnLine", "noteheadHalfInSpace", "noteheadWholeOnLine", "noteheadWholeInSpace", "noteheadWhole"})

    def test_every_other_class_is_dropped_CONTROL(self):
        dets = [FakeDet(n, 10, 10, confidence=0.9) for n in (
            "beam", "ledgerLine", "tie", "slur", "noteheadBlackInSpace", "noteheadBlackOnLine", "noteheadHalfSmall",
            "noteheadHalfInSpaceSmall", "noteheadDoubleWholeInSpace", "timeSig4", "flag8thUp", "restQuarter")]
        self.assertEqual(SH.keep_hollow(dets), [])
        keep = FakeDet("noteheadHalfInSpace", 10, 10, confidence=0.9)
        self.assertEqual(SH.keep_hollow(dets + [keep]), [keep])

    def test_one_head_boxed_twice_keeps_the_higher_confidence(self):
        a = FakeDet("noteheadHalfInSpace", 10, 10, confidence=0.4)
        b = FakeDet("noteheadWholeInSpace", 11, 10, confidence=0.7)
        self.assertEqual(SH.keep_hollow([a, b]), [b])

    def test_the_wrapper_filters_what_the_inner_detector_returns(self):
        class Inner:
            def detect(self, cell, conf_threshold=0.25, imgsz=None):
                return [FakeDet("beam", 0, 0, confidence=0.9), FakeDet("noteheadWholeOnLine", 50, 50, confidence=0.5)]
        got = SH.SecondHollowDetector(inner=Inner()).detect(object(), conf_threshold=0.25, imgsz=None)
        self.assertEqual([d.smufl_name for d in got], ["noteheadWholeOnLine"])

    def test_the_flag_is_OFF_by_default_and_an_allow_list(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(SH.ENV, None)
            self.assertFalse(SH.enabled())
        for v in ("1", "true", "on", "yes"):
            with mock.patch.dict(os.environ, {SH.ENV: v}):
                self.assertTrue(SH.enabled(), v)
        for v in ("0", "", "off", "false", "no", "typo"):
            with mock.patch.dict(os.environ, {SH.ENV: v}):
                self.assertFalse(SH.enabled(), v)

    def test_plan_cell_separates_head_other_and_unseen(self):
        prod = [FakeDet("noteheadBlackInSpace", 200, 100), FakeDet("timeSig0", 400, 100, 20, 30, category="timeSig")]
        on_head = FakeDet("noteheadHalfInSpace", 201, 101)
        over_other = FakeDet("noteheadHalfInSpace", 401, 101, 20, 30)
        unseen = FakeDet("noteheadWholeOnLine", 600, 100)
        plan = SH.plan_cell(prod, [on_head, over_other, unseen])
        self.assertEqual([(i, d) for i, d, _ in plan["on_head"]], [(0, on_head)])
        self.assertEqual([(i, d) for i, d, _ in plan["over_other"]], [(1, over_other)])
        self.assertEqual(plan["second_only"], [unseen])


# ─────────────────────────── the GATHER half ───────────────────────────
class _Second:
    """A stand-in for `SecondHollowDetector`: the same hollow boxes for every cell, or only for the ones `where` accepts."""

    def __init__(self, boxes, where=lambda c: c.measure_index == 0 and c.staff_index == 0, error=None):
        self.boxes, self.where, self.error, self.calls = boxes, where, error, []

    def detect(self, cell, conf_threshold=0.25, imgsz=None):
        self.calls.append((conf_threshold, imgsz))
        if self.error:
            raise self.error
        return SH.keep_hollow(self.boxes) if self.where(cell) else []


def _gather_with(second, **env):
    """`gather()` as the product runs it: the FLAG builds the second detector (here a stand-in for the weights)."""
    with mock.patch.dict(os.environ, {SH.ENV: "1"}), mock.patch.object(SH, "default_detector", return_value=second):
        return gather.gather(build_page(), detector=FakeDetector())


class TestGatherFilesASeparateWitness(unittest.TestCase):

    def setUp(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(SH.ENV, None)
            self.base = gather.gather(build_page(), detector=FakeDetector())

    def test_flag_OFF_is_bit_identical_CONTROL(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(SH.ENV, None)
            again = gather.gather(build_page(), detector=FakeDetector())
        self.assertEqual(_dump(again), _dump(self.base))
        # and a second detector that sees nothing changes nothing either
        silent = _gather_with(_Second([]))
        self.assertEqual(_dump(silent), _dump(self.base))
        # flag OFF never even builds the detector: a stand-in that raises on construction is not reached
        with mock.patch.dict(os.environ, {}, clear=False), mock.patch.object(SH, "default_detector", side_effect=AssertionError):
            os.environ.pop(SH.ENV, None)
            gather.gather(build_page(), detector=FakeDetector())

    def test_a_hollow_box_over_production_black_head_is_a_witness_on_that_glyph_RED(self):
        sec = _Second([FakeDet("noteheadHalfInSpace", 201, 101, confidence=0.8)])
        log = _gather_with(sec)
        g = R.glyph(0, 0, 0, 0, 1)                      # cell (0,0,0,0): clef is 0, the black head is 1
        rows = log.rows(Q.SECOND_HOLLOW, g)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].reader, READERS.SECOND_DETECTOR)
        self.assertEqual(rows[0].value, "noteheadHalfInSpace")
        self.assertEqual(rows[0].detail["relation"], "disagrees")
        self.assertEqual(rows[0].detail["production_class"], "noteheadBlack")
        # production's own rows on that glyph are UNCHANGED: same class, same box, same reader
        for q in (Q.NOTEHEAD_CLASS, Q.GLYPH_BOX, Q.GLYPH_CONF):
            self.assertEqual([(r.value, r.reader) for r in log.rows(q, g)], [(r.value, r.reader) for r in self.base.rows(q, g)])
        self.assertEqual(sec.calls[0], (0.25, None))      # production's conf, per-cell imgsz

    def test_a_hollow_box_where_production_boxed_nothing_is_a_glyph_of_its_own_RED(self):
        unseen = FakeDet("noteheadWholeOnLine", 600, 100, confidence=0.6)
        log = _gather_with(_Second([unseen]))
        g = R.glyph(0, 0, 0, 0, 2)                      # past the clef (0) and the black head (1)
        self.assertEqual([(r.value, r.reader) for r in log.rows(Q.NOTEHEAD_CLASS, g)],
                         [("noteheadWholeOnLine", READERS.SECOND_DETECTOR)])
        self.assertEqual(log.rows(Q.GLYPH_BOX, g)[0].reader, READERS.SECOND_DETECTOR)
        self.assertEqual(log.rows(Q.SECOND_HOLLOW, g)[0].detail["relation"], "second_only")
        # no DETECTOR row anywhere carries the second detector's box
        det_boxes = [r.value for r in log.all_rows() if r.quantity == Q.GLYPH_BOX and r.reader == READERS.DETECTOR]
        base_boxes = [r.value for r in self.base.all_rows() if r.quantity == Q.GLYPH_BOX and r.reader == READERS.DETECTOR]
        self.assertEqual(det_boxes, base_boxes)

    def test_a_second_only_head_gets_the_rulers_stem_reading_RED(self):
        """Round 2: the witness of a note that is not the second box. A second-only head is not contested, so it had no `Q.HEAD_STEM_REACH`."""
        unseen = FakeDet("noteheadHalfInSpace", 600, 100, confidence=0.6)
        log = _gather_with(_Second([unseen]))
        g = R.glyph(0, 0, 0, 0, 2)
        rows = log.rows(Q.HEAD_STEM_REACH, g)
        # the fake page may carry no raster; where it does, the row exists and is the ruler's. Never an invented direction either way.
        for r in rows:
            self.assertIn(r.value, ("up", "down", "both", "none"))
        if getattr(getattr(build_page(), "page", None), "rgb", None) is not None:
            self.assertEqual(len(rows), 1)

    def test_a_hollow_box_over_another_production_class_is_refused_not_added(self):
        over_clef = FakeDet("noteheadHalfInSpace", 20, 92, confidence=0.7)        # production's clefG sits at (20, 92)
        log = _gather_with(_Second([over_clef]))
        self.assertEqual([o for o in log.to_json()["observations"] if o["quantity"] == Q.SECOND_HOLLOW], [])
        self.assertTrue(any(a.detail.get("relation") == "over_other" and a.detail.get("production_class") == "clefG"
                            for a in log.refusals(Q.SECOND_HOLLOW, R.cell(0, 0, 0, 0))))
        self.assertEqual(_dump_without_second(log), _dump_without_second(self.base))

    def test_a_detector_that_throws_is_a_refusal_not_no_hollow_heads(self):
        log = _gather_with(_Second([], where=lambda c: True, error=ValueError("x")))
        ref = log.refusals(Q.SECOND_HOLLOW, R.cell(0, 0, 0, 0))
        self.assertEqual(ref[0].reason, ABSTAIN.READER_UNAVAILABLE)
        self.assertEqual(ref[0].detail["error"], "ValueError")


def _dump_without_second(log):
    """Every OBSERVATION that is not the second detector's, by (subject, quantity, reader, value) -- ids shift when a refusal is added."""
    return sorted((str(o.subject), o.quantity, o.reader, repr(o.value)) for o in log.all_rows()
                  if hasattr(o, "value") and o.quantity != Q.SECOND_HOLLOW and o.reader != READERS.SECOND_DETECTOR)


# ─────────────────────────── the ADJUDICATE half ───────────────────────────
def _ink(log, g, *, center, ring, rasters=("ink_raw", "ink_net", "ink_off_line")):
    detail = {k: {"best": max(center, ring), "best_window": "ring", "windows": {"center": center, "ring": ring}} for k in rasters}
    return log.observe(g, Q.NOTEHEAD_INK, round(max(center, ring), 4), reader=READERS.CV_NOTEHEAD_INK, frame="cell:0", **detail)


def _second_row(log, g, relation="disagrees", cls="noteheadHalfInSpace", **extra):
    return log.observe(g, Q.SECOND_HOLLOW, cls, reader=READERS.SECOND_DETECTOR, frame="cell:0", score=0.8,
                       relation=relation, second_class=cls, second_score=0.8, second_box=[0, 0, 20, 16], **extra)


class _Heads(unittest.TestCase):

    def _seen_black(self, log, *, second=True, box_w=20, box_h=16):
        """A production BLACK head with its own stem, in a beamless cell the beam reader LOOKED at, tip nobody measured (so neither the
        landed 2.70 nor 2.88 rule decides it): the state in which main today narrows it `head_fill_from_ink` where its ink reads hollow."""
        _staff_space(log)
        log.abstain(CELL, Q.BEAM_STROKE, reader=READERS.CV_LINES, frame="cell:0", reason=ABSTAIN.NO_LINE_ACCEPTED)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, box_w, box_h), reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _stem(log, x=135, y=38, h=60)
        if second:
            _second_row(log, g)
        return g

    def _second_only(self, log, *, cls="noteheadHalfInSpace", stem=True):
        _staff_space(log)
        log.abstain(CELL, Q.BEAM_STROKE, reader=READERS.CV_LINES, frame="cell:0", reason=ABSTAIN.NO_LINE_ACCEPTED)
        g = R.glyph(0, 0, 0, 0, 5)
        log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.SECOND_DETECTOR, frame="cell:0", score=0.8)
        log.observe(g, Q.GLYPH_BOX, (cls, 135, 90, 20, 16), reader=READERS.SECOND_DETECTOR, frame="cell:0", score=0.8)
        if stem:
            _stem(log, x=135, y=38, h=60)
        _second_row(log, g, relation="second_only", cls=cls)
        return g

    def _duration(self, log, g):
        adjudicate.run(log)
        return log.verdict(Q.DURATION, g)


class TestAProductionBlackHeadTheSecondCallsHollow(_Heads):

    def test_firm_white_interior_is_a_DECIDED_half_RED(self):
        log = Log()
        g = self._seen_black(log)
        _ink(log, g, center=0.45, ring=0.85)
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "second_hollow_confirmed")
        self.assertEqual(v.value["beats"], 2.0)
        self.assertEqual(v.detail["second_hollow"]["settled"], "hollow_read")
        self.assertGreaterEqual(v.detail["second_hollow"]["margin"], 0.0)

    def test_a_staff_line_through_the_middle_still_reads_hollow_RED(self):
        """Sean: many hollow heads have lines through the middle -- the centre carries ink (0.60 here) but the ring is far darker."""
        log = Log()
        g = self._seen_black(log)
        _ink(log, g, center=0.60, ring=0.95)
        v = self._duration(log, g)
        self.assertEqual(v.reason, "second_hollow_confirmed")
        self.assertEqual(v.outcome, Outcome.DECIDED)

    def test_CONTROL_without_the_second_witness_the_same_ink_is_main_s_narrowing(self):
        log = Log()
        g = self._seen_black(log, second=False)
        _ink(log, g, center=0.45, ring=0.85)
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "head_fill_from_ink")

    def test_a_filled_head_stays_black_with_the_disagreement_and_margin_recorded_CONTROL(self):
        log = Log()
        g = self._seen_black(log)
        _ink(log, g, center=1.0, ring=1.0)
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "head_and_marks")
        self.assertEqual(v.value["beats"], 1.0)
        sh = v.detail["second_hollow"]
        self.assertEqual((sh["relation"], sh["settled"], sh["interior"]), ("disagrees", "black_stands", "filled"))
        self.assertLess(sh["margin"], 0.0)                # signed: declined short of the firm gate
        self.assertIsNotNone(sh["margin_axis"])

    def test_an_ambiguous_interior_is_NARROWED_with_both_candidates_RED(self):
        log = Log()
        g = self._seen_black(log)
        _ink(log, g, center=0.70, ring=0.80)             # middle under 0.75 but ring - centre 0.10 < 0.15: not firm
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "second_hollow_unclear")
        fills = [c.value["head_fill"] for c in v.candidates]
        self.assertIn("black", fills)
        self.assertIn("half", fills)
        self.assertEqual(fills[0], "half")                # the second detector's claim ranks first, black stays a candidate
        self.assertEqual(v.detail["second_hollow"]["settled"], "narrowed_unclear")

    def test_a_box_that_is_not_head_shaped_cannot_be_read_firm(self):
        log = Log()
        g = self._seen_black(log, box_h=60)               # a cluster-sized box
        _ink(log, g, center=0.45, ring=0.85)
        v = self._duration(log, g)
        self.assertNotEqual(v.outcome, Outcome.DECIDED if v.reason == "second_hollow_confirmed" else None)
        self.assertNotEqual(v.reason, "second_hollow_confirmed")

    def test_CONTROL_a_DECIDED_verdict_resting_on_other_evidence_is_not_overturned(self):
        """A head under a read beam is an eighth whatever the second detector says (CLAUDE.md 3: a second opinion never overturns a DECIDED
        verdict). With no hollow ink the eighth stays DECIDED; with hollow ink main already narrows it (`head_fill_from_ink`) and the second
        witness must change NOTHING about that."""
        for ink in (False, True):
            outs = []
            for with_second in (False, True):
                log = Log()
                _staff_space(log)
                g = _note(log, 0, "noteheadBlack", levels=1)
                if with_second:
                    _second_row(log, g)
                if ink:
                    _ink(log, g, center=0.45, ring=0.85)
                adjudicate.run(log)
                v = log.verdict(Q.DURATION, g)
                outs.append((v.outcome, v.reason, v.value))
                self.assertNotIn(v.reason, ("second_hollow_confirmed", "second_hollow_unclear"))
            self.assertEqual(outs[0], outs[1], f"ink={ink}")
            if not ink:
                self.assertEqual(outs[1][0], Outcome.DECIDED)
                self.assertEqual(outs[1][2]["beats"], 0.5)

    def test_CONTROL_an_AGREEING_witness_changes_nothing(self):
        base = Log()
        g0 = self._seen_black(base, second=False)
        _ink(base, g0, center=0.45, ring=0.85)
        a = Log()
        g1 = self._seen_black(a, second=False)
        _second_row(a, g1, relation="agrees")
        _ink(a, g1, center=0.45, ring=0.85)
        v0, v1 = self._duration(base, g0), self._duration(a, g1)
        self.assertEqual((v0.outcome, v0.reason), (v1.outcome, v1.reason))


class TestAHeadOnlyTheSecondDetectorBoxed(_Heads):

    def test_even_a_firm_interior_is_NARROWED_never_decided_RED(self):
        log = Log()
        g = self._second_only(log)
        _ink(log, g, center=0.45, ring=0.85)
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "second_only_hollow")
        self.assertEqual([c.value["head_fill"] for c in v.candidates], ["half", "whole"])   # firm: no black candidate
        self.assertEqual(v.detail["second_hollow"]["interior"], "firm")

    def test_an_unclear_interior_keeps_black_as_a_candidate_RED(self):
        log = Log()
        g = self._second_only(log)
        _ink(log, g, center=0.70, ring=0.80)
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual([c.value["head_fill"] for c in v.candidates][0], "half")
        self.assertIn("black", [c.value["head_fill"] for c in v.candidates])

    def test_ink_that_reads_filled_refuses_the_hollow_box_and_invents_nothing_RED(self):
        log = Log()
        g = self._second_only(log)
        _ink(log, g, center=1.0, ring=1.0)
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "second_hollow_refuted_by_ink")
        self.assertIsNone(v.value)

    def test_a_beam_over_it_contradicts_a_hollow_head_RED(self):
        log = Log()
        g = self._second_only(log)
        _beam(log, y=40, x0=100, x1=180)
        _ink(log, g, center=0.45, ring=0.85)
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "second_hollow_contradicted_by_marks")

    def test_a_whole_note_class_ranks_whole_first(self):
        log = Log()
        g = self._second_only(log, cls="noteheadWholeInSpace", stem=False)
        _dot(log, gi=900, x=160, y=96)                   # a whole note has no stem: its evidence is a dot
        _ink(log, g, center=0.45, ring=0.85)
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual([c.value["head_fill"] for c in v.candidates][0], "whole")

    # ── round 2: Sean's tile 5 (a tie fragment boxed by the second detector alone became a blue invented note) ──
    def test_a_second_only_head_with_NO_stem_dot_or_reach_is_refused_nothing_written_RED(self):
        log = Log()
        g = self._second_only(log, stem=False)
        _ink(log, g, center=0.45, ring=0.85)            # a firm interior: the INK alone is not a note
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "second_only_no_independent_evidence")
        self.assertIsNone(v.value)
        self.assertEqual(v.detail["second_hollow"]["independent_evidence"], [])
        self.assertEqual(v.detail["second_hollow"]["would_narrow"], ["half", "whole"])      # candidates recorded
        self.assertIn("margin", v.detail["second_hollow"])                                   # and how close

    def test_CONTROL_each_witness_alone_lets_the_head_through(self):
        # the stem reader's stem
        log = Log()
        g = self._second_only(log, stem=True)
        _ink(log, g, center=0.45, ring=0.85)
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.detail["second_hollow"]["independent_evidence"], ["stem_box"])
        # the CV ruler's stem reading
        log = Log()
        g = self._second_only(log, stem=False)
        log.observe(g, Q.HEAD_STEM_REACH, "down", reader=READERS.CV_HEAD_STEM_REACH, frame="page")
        _ink(log, g, center=0.45, ring=0.85)
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.detail["second_hollow"]["independent_evidence"], ["stem_reach"])
        # an augmentation dot
        log = Log()
        g = self._second_only(log, stem=False)
        _dot(log, gi=900, x=160, y=96)
        _ink(log, g, center=0.45, ring=0.85)
        v = self._duration(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.detail["second_hollow"]["independent_evidence"], ["aug_dot"])

    def test_CONTROL_through_ink_is_a_barline_not_a_witness(self):
        log = Log()
        g = self._second_only(log, stem=False)
        log.observe(g, Q.HEAD_STEM_REACH, "both", reader=READERS.CV_HEAD_STEM_REACH, frame="page")
        _ink(log, g, center=0.45, ring=0.85)
        self.assertEqual(self._duration(log, g).reason, "second_only_no_independent_evidence")


if __name__ == "__main__":
    unittest.main()
