"""ROADMAP 2.121 -- a bare stem whose every refused "beam" is a slur's or tie's ink.

2.119's twins split A (24 pairs) read as "the beam reader misses a beam the detector sees". Sean's own boxes on Brahms 317803 pdf 0
say otherwise: of the 24 missed notes 19 carry NO beam and NO flag in his truth (the detector's `beam` boxes beside them are his
slurs and ties), 4 stand under a real beam (2 with no stem found, 2 `beam_certain_not_joined`) and 1 under a real flag. So the
ink reader was right to refuse; what was missing is the positive reading "every refused stroke is a slur". It is ONE witness
(the arc reader's decided glyph and the CV ink test read the same ink), so INFER gets it and it is GUESSED (blue), default OFF.

Two pieces, both under test:
  * ADJUDICATE files, per refused stroke, what it was refused AS and whether it stands at the stem tip
    (`refused_strokes` in the `beam_discounted_uncertain` detail) -- decides nothing new;
  * INFER's `collapse_arc_ink_not_beam` collapses the narrowing to the head's own unbeamed value only where every refusal is
    positive (a decided arc, or measured too thin / bowed) and the tip was read clean.

Every refusal below is paired with a positive control (CLAUDE.md §6b). The `real_*` fixtures reproduce the detail of the real
records (Brahms 317803 pdf 0, 20261013-night): counts as printed there; the per-stroke split is the only illustrated part
(that field did not exist then).
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate, evaluate, infer
from tools.omr.staged import inferences as INFS
from tools.omr.staged import record as R
from tools.omr.staged.record import (READERS, Candidate, Kind, Log, Outcome, Q,
                                     Verdict)
from tools.omr.tests.test_staged_duration import _beam, _stem

CELL = R.cell(0, 0, 0, 0)


def _arc(log, *, x0=60, x1=140, y0=30, y1=50, gi=900, cls="slur"):
    g = R.glyph(0, 0, 0, 0, gi)
    return log.observe(g, Q.ARC_BOX, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.8, x0=x0, x1=x1, y0=y0, y1=y1,
                       x_center=(x0 + x1) / 2.0, y_center=(y0 + y1) / 2.0)


def _head(log, g=None):
    g = g or R.glyph(0, 0, 0, 0, 0)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack", reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16), reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    return g


def _tip(log, stem_row, *, found):
    return log.observe(CELL, Q.STEM_TIP_INK, bool(found), reader=READERS.CV_STEM_TIP, frame="cell:0",
                       stem_row_id=stem_row.id, end="top")


def _under_a_slur(tip_found=False):
    """Up stem tip at y=38; the ONLY stroke (y=40) lies inside a decided slur's box -> ADJUDICATE narrows."""
    log = Log()
    log.observe(R.staff(0, 0, 0), Q.STAFF_LINES, [950.0, 960.0, 970.0, 980.0, 990.0], reader=READERS.GEOMETRY, frame="page")
    log.observe(CELL, Q.CELL_STAFF_SPACE, 16.0, reader=READERS.GEOMETRY, frame="cell:0")
    _arc(log)
    _beam(log, y=40, x0=60, x1=140)
    g = _head(log)
    s = _stem(log, x=135, y=38, h=60)
    if tip_found is not None:
        _tip(log, s, found=tip_found)
    adjudicate.run(log)
    return log, g


# ---------------------------------------------------------------------------------------------------------------------------
# ADJUDICATE: what each refused stroke was refused AS
# ---------------------------------------------------------------------------------------------------------------------------
class TestRefusedStrokesAreFiledPerStroke(unittest.TestCase):

    def test_a_slur_stroke_is_filed_as_arc_and_the_verdict_is_unchanged_RED(self):
        log, g = _under_a_slur(tip_found=False)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual((v.outcome, v.reason), (Outcome.NARROWED, "beam_discounted_uncertain"))
        self.assertEqual({c.value["beats"] for c in v.candidates}, {1.0, 0.5})
        self.assertEqual([s["why"] for s in v.detail["refused_strokes"]], ["arc"])
        self.assertIn(v.detail["refused_strokes"][0]["at_tip"], (True, False))

    def test_CONTROL_a_real_second_beam_still_decides_and_files_nothing_to_collapse(self):
        log = Log()
        _arc(log)
        _beam(log, y=40, x0=60, x1=140)
        _beam(log, y=70, x0=60, x1=140)
        g = _head(log)
        _stem(log, x=135, y=38, h=60)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertNotIn("refused_strokes", v.detail)


# ---------------------------------------------------------------------------------------------------------------------------
# INFER: the rule, over the narrowing as the real records carry it
# ---------------------------------------------------------------------------------------------------------------------------
def _narrowed(detail_over=None, *, reason="beam_discounted_uncertain", strokes=None, gi=7):
    """A `beam_discounted_uncertain` verdict shaped like the real ones (q1319: head + one beam level, quarter second)."""
    d = {"head": "noteheadBlackInSpace", "head_is_open": False, "beam_evidence": "none_over_this_note", "cv_beams": 0,
         "yolo_beams": 2, "yolo_kept": 2, "beams_neighbour_staff": 0, "beams_decided_arc": 1, "beams_far_side": 0,
         "beams_beyond_stem": 0, "stems_attached": 1, "beams_by_stem": 0, "flags_attached": 0, "flag_levels": 0,
         "levels_certain": 0, "levels_possible": 0, "bare_stem_tip_window_clean": True,
         "refused_strokes": strokes if strokes is not None else [{"id": "obs:1", "why": "arc", "at_tip": True}]}
    d.update(detail_over or {})
    log = Log()
    g = R.glyph(0, 0, 0, 0, gi)
    v = log.record(Verdict(
        id=log._next_id("vrd"), subject=g, quantity=Q.DURATION, outcome=Outcome.NARROWED, value=None,
        decider="adjudicate_duration", reason=reason,
        candidates=(Candidate({"beats": 0.5, "written": 0.5, "dots": 0, "beam_levels": 1}, support=2.0),
                    Candidate({"beats": 1.0, "written": 1.0, "dots": 0, "beam_levels": 0}, support=1.0)),
        detail=d))
    return log, g, v


def _fire(log):
    return INFS.collapse_arc_ink_not_beam(log, CELL)


class TestTheRuleCollapsesToTheUnbeamedValue(unittest.TestCase):

    def test_real_q1319_a_slur_at_the_tip_and_a_thin_stroke_off_it_is_a_quarter_RED(self):
        """q1319 (Brahms pdf 0 s0-st11-m2): 2 refused strokes, 1 decided arc + 1 `too_thin`; Sean's truth: a bare stem."""
        log, g, v = _narrowed({"beams_not_by_ink": 1, "beams_not_by_ink_why": {"too_thin": 1}},
                              strokes=[{"id": "a", "why": "arc", "at_tip": True},
                                       {"id": "b", "why": "ink:too_thin", "at_tip": False}])
        out = _fire(log)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].subject, g)
        self.assertEqual(out[0].value["beats"], 1.0)
        self.assertEqual(out[0].value["beam_levels"], 0)
        self.assertEqual(out[0].detail["witness_count"], 1)
        self.assertEqual(out[0].basis, (v.id,))

    def test_real_q1272_one_decided_arc_only(self):
        self.assertEqual(len(_fire(_narrowed()[0])), 1)

    def test_a_thin_stroke_away_from_the_tip_collapses(self):
        log, *_ = _narrowed(strokes=[{"id": "a", "why": "ink:too_thin", "at_tip": False},
                                     {"id": "b", "why": "ink:bowed", "at_tip": False}])
        self.assertEqual(len(_fire(log)), 1)

    def test_a_dotted_head_collapses_to_its_own_dotted_unbeamed_value(self):
        log, g, v = _narrowed()
        # same head with a dot: the candidates carry the dot, the rule only picks the beam_levels==0 one
        log2 = Log()
        log2.record(Verdict(
            id=log2._next_id("vrd"), subject=g, quantity=Q.DURATION, outcome=Outcome.NARROWED, value=None,
            decider="adjudicate_duration", reason="beam_discounted_uncertain",
            candidates=(Candidate({"beats": 0.75, "written": 0.5, "dots": 1, "beam_levels": 1}, support=2.0),
                        Candidate({"beats": 1.5, "written": 1.0, "dots": 1, "beam_levels": 0}, support=1.0)),
            detail=dict(v.detail)))
        out = _fire(log2)
        self.assertEqual((out[0].value["beats"], out[0].value["dots"]), (1.5, 1))


class TestEveryRefusalMustBePositive(unittest.TestCase):
    """The rule's conjunction: each of these is a real way to be wrong, so each declines, paired with the positive above."""

    def _declines(self, **kw):
        log, *_ = _narrowed(**kw)
        self.assertEqual(_fire(log), [])

    def test_CONTROL_a_thin_stroke_AT_the_tip_declines(self):
        """2.81: a refusal at the tip is where a refused real beam would stand; only a decided slur may stand there."""
        self._declines(strokes=[{"id": "a", "why": "ink:too_thin", "at_tip": True}])

    def test_CONTROL_an_unaskable_tip_declines_for_ink_shape(self):
        self._declines(strokes=[{"id": "a", "why": "ink:too_thin", "at_tip": None}])

    def test_CONTROL_a_stroke_refused_for_standing_on_one_stem_declines(self):
        """2.82: a real beam whose other stem was not found is refused this way."""
        self._declines(strokes=[{"id": "a", "why": "ink:one_stem", "at_tip": False}])

    def test_CONTROL_one_slur_and_one_one_stem_refusal_declines(self):
        self._declines(strokes=[{"id": "a", "why": "arc", "at_tip": True}, {"id": "b", "why": "ink:one_stem", "at_tip": False}])

    def test_CONTROL_another_staffs_beam_or_the_far_side_declines(self):
        for why in ("neighbour_staff", "far_side", "beyond_stem", "ink:through_heads"):
            self._declines(strokes=[{"id": "a", "why": why, "at_tip": False}])

    def test_CONTROL_tip_not_read_clean_declines(self):
        self._declines(detail_over={"bare_stem_tip_window_clean": False})
        self._declines(detail_over={"bare_stem_tip_window_clean": None})

    def test_CONTROL_real_q1504_style_missing_tip_reading_declines(self):
        self._declines(detail_over={"bare_stem_tip_window_clean": False, "beams_decided_arc": 1})

    def test_CONTROL_no_own_stem_seen_declines(self):
        self._declines(detail_over={"stems_attached": 0})

    def test_CONTROL_no_per_stroke_facts_declines(self):
        """An old record (before 2.121) has counts only: 'cannot tell' is not 'all slurs'."""
        log, g, v = _narrowed()
        d = dict(v.detail)
        d.pop("refused_strokes")
        log2 = Log()
        log2.record(Verdict(id=log2._next_id("vrd"), subject=g, quantity=Q.DURATION, outcome=Outcome.NARROWED, value=None,
                            decider="adjudicate_duration", reason=v.reason, candidates=v.candidates, detail=d))
        self.assertEqual(_fire(log2), [])
        self._declines(strokes=[])

    def test_CONTROL_a_beam_or_flag_read_on_the_stem_declines(self):
        self._declines(detail_over={"beam_evidence": "read"})
        self._declines(detail_over={"flags_attached": 1})
        self._declines(detail_over={"levels_possible": 1})

    def test_CONTROL_other_narrowing_reasons_are_not_this_rules(self):
        """q93/q86 `beam_certain_not_joined` and q1009 `flag_ink_unread` are real beams/flags in Sean's truth."""
        for reason in ("beam_certain_not_joined", "beams_ambiguous", "flag_ink_unread"):
            log, *_ = _narrowed(reason=reason)
            self.assertEqual(_fire(log), [], reason)

    def test_CONTROL_a_decided_duration_is_never_touched(self):
        log = Log()
        g = R.glyph(0, 0, 0, 0, 3)
        log.record(Verdict(id=log._next_id("vrd"), subject=g, quantity=Q.DURATION, outcome=Outcome.DECIDED,
                           value={"beats": 0.5, "written": 0.5, "beam_levels": 1}, decider="adjudicate_duration",
                           reason="head_and_marks", detail={"refused_strokes": [{"why": "arc", "at_tip": False}]}))
        self.assertEqual(_fire(log), [])

    def test_CONTROL_it_never_makes_an_eighth(self):
        log, *_ = _narrowed()
        for p in _fire(log):
            self.assertEqual(p.value["beam_levels"], 0)


class TestEndToEndAndTheFlag(unittest.TestCase):

    def _infer(self, log, env):
        with mock.patch.dict(os.environ, {infer.NARROWED_BAR_ENV: "0", infer.BARE_STEM_BAR_ENV: "0"}, clear=False):
            for k in (infer.ARC_INK_NOT_BEAM_ENV,):
                os.environ.pop(k, None)
            os.environ.update(env)
            return infer.run(log, evaluate.Report([], [], []))

    def test_the_default_is_ON_and_it_collapses_RED(self):
        log, g = _under_a_slur(tip_found=False)
        self._infer(log, {})
        self.assertEqual(log.verdict(Q.DURATION, g).outcome, Outcome.DECIDED)

    def test_an_explicit_off_word_turns_it_off(self):
        for bad in ("", "0", "off", "no", "false"):
            log, g = _under_a_slur(tip_found=False)
            self._infer(log, {infer.ARC_INK_NOT_BEAM_ENV: bad})
            self.assertEqual(log.verdict(Q.DURATION, g).outcome, Outcome.NARROWED, bad)

    def test_a_typo_leaves_it_on(self):
        for bad in ("yess", "ON!"):
            log, g = _under_a_slur(tip_found=False)
            self._infer(log, {infer.ARC_INK_NOT_BEAM_ENV: bad})
            self.assertEqual(log.verdict(Q.DURATION, g).outcome, Outcome.DECIDED, bad)

    def test_on_it_collapses_a_slur_covered_stem_to_a_labelled_inferred_quarter_RED(self):
        log, g = _under_a_slur(tip_found=False)
        rep = self._infer(log, {infer.ARC_INK_NOT_BEAM_ENV: "1"})
        v = log.verdict(Q.DURATION, g)
        # the stroke sits at the stem's tip INSIDE a decided slur: allowed, and it is the only thing refused
        fired = [i for i in rep.inferred if i[0] == infer.Inference.COLLAPSE_ARC_INK_NOT_BEAM.value]
        self.assertEqual(len(fired), 1)
        self.assertEqual(v.value["beam_levels"], 0)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertTrue(str(v.decider).startswith("infer:"))

    def test_CONTROL_on_but_the_tip_unread_stays_narrowed(self):
        log, g = _under_a_slur(tip_found=None)
        self._infer(log, {infer.ARC_INK_NOT_BEAM_ENV: "1"})
        self.assertEqual(log.verdict(Q.DURATION, g).outcome, Outcome.NARROWED)

    def test_CONTROL_on_but_the_tip_shows_a_hook_stays_narrowed(self):
        log, g = _under_a_slur(tip_found=True)
        self._infer(log, {infer.ARC_INK_NOT_BEAM_ENV: "1"})
        self.assertEqual(log.verdict(Q.DURATION, g).outcome, Outcome.NARROWED)

    def test_the_rule_is_registered_default_on(self):
        infer._ensure_rules()
        self.assertIn("collapse_arc_ink_not_beam", [r.inference.value for r in infer.RULES])
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(infer.ARC_INK_NOT_BEAM_ENV, None)
            self.assertIn("collapse_arc_ink_not_beam", [r.inference.value for r in infer.enabled_rules()])


if __name__ == "__main__":
    unittest.main()
