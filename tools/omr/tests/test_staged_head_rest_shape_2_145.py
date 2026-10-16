"""ROADMAP 2.145 -- a lone rest the detector boxed as a notehead (no rest box beside it) is read from its INK
(STAGED ADJUDICATE `adjudicate_notehead_is_not_a_notehead` -> `is_a_rest_shape`, `adjudicate_head_ink_is_a_rest`;
EVALUATE `size_head_ink_rest`; EXPORT; flag `OMR_HEAD_INK_IS_A_REST`, default ON since 2026-10-16).

Sean 2026-10-15, tile 3: Litolff p6 sys1 st2 c5, *"an eighth rest"*, boxed `noteheadBlackOnLine` and written as a note.
Every CONTROL_ test is green with the rule absent or present, so a rule that refuses everything cannot pass; the
stem control is the one that matters (a head and its stem make a rest-sized cluster of ink: 14 Litolff stemmed heads
read `quarter` by shape alone).
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate, adjudicators            # noqa: F401
from tools.omr.staged import consequences, margins
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import head_rest_shape as H
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_duration import CELL, _staff_space

ENV = {H.ENV: "1"}
CL = R.glyph(0, 0, 0, 0, 350_000)       # the cluster of ink

#: Shapes MEASURED off the clusters under Sean's tile 3 and the 2.99 controls.
EIGHTH = dict(w=1.34, h=2.29, step=3.9, mass_y=0.43, col=0.75, profile=[0.39, 0.58, 0.58, 0.58, 0.75, 0.59])
QUARTER = dict(w=1.19, h=2.81, step=4.4, mass_y=0.55, col=1.0, profile=[0.4, 0.89, 1.0, 0.77, 0.6, 0.31])
SEAN_TILE_3 = dict(w=1.46, h=2.28, step=5.96, mass_y=0.466, col=0.75, profile=[0.39, 0.56, 0.56, 0.72, 0.75, 0.39])
FLAT = dict(w=1.04, h=2.7, step=4.0, mass_y=0.57, col=1.0, profile=[1.0, 1.0, 0.35, 0.35, 0.33, 0.23])
HEAD_BOX = (300, 200, 130, 100)
INK_BOX = [290, 150, 440, 380]            # corners, canonical: the head box lies inside the ink


def _head(log, gi=0, box=HEAD_BOX, cls="noteheadBlackOnLine"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.4)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.4,
                category="notehead")
    return g


def _rest_box(log, gi, box, cls="rest8th"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.REST, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="rest")
    return g


def _stem(log, box):
    x, y, w, h = box
    return log.observe(CELL, Q.STEM, (x, y, w, h), reader=READERS.CV_LINES, frame="cell:0", x0=x, x1=x + w,
                       y_center=y + h / 2.0, image="no_staff", staff_lines_erased=True)


def _cluster(log, *, w, h, step, mass_y, col, profile, cover=0.46, by=("noteheadBlackOnLine",), box=INK_BOX,
             sub=CL):
    log.observe(sub, Q.UNBOXED_REST_SHAPE, h, reader=READERS.CV_UNBOXED_REST_SHAPE, frame="cell:0",
                n_pieces=1, width_spaces=w, height_spaces=h, staff_step=step, fill=0.44, max_column_share=col,
                mass_y=mass_y, column_profile=profile, coverage=cover, covered_by=list(by), right_head=None,
                first_cell=False, header_known=False, left_of_header=False, touches_cell_edge=False,
                bbox_canonical=list(box), bbox_page_px=[0.0, 0.0, 10.0, 10.0])


def _fixture(shape=EIGHTH, stem=None, cls="noteheadBlackOnLine", by=("noteheadBlackOnLine",), second_head=False,
             rest_twin=False):
    log = Log()
    _staff_space(log, 100)
    h = _head(log, 0, cls=cls)
    if second_head:
        _head(log, 3, box=(305, 215, 120, 90))
    if rest_twin:
        _rest_box(log, 1, HEAD_BOX)
    _cluster(log, **shape, by=by)
    if stem is not None:
        _stem(log, stem)
    return log, h


def _run(log, env=ENV):
    adjudicate._ensure_decisions()
    log.freeze()
    with mock.patch.dict(os.environ, env):
        adjudicate.run(log)
    return log


class TestTheGate(unittest.TestCase):
    def test_a_stemless_head_on_eighth_rest_ink_leaves_the_bar_RED(self):
        log, h = _fixture(EIGHTH)
        _run(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h)
        self.assertTrue(v.value is True and v.reason == "is_a_rest_shape", (v.value, v.reason))
        self.assertGreaterEqual(v.margin, 0.0)
        self.assertEqual(v.detail["rest_shape"]["value"], "eighth")

    def test_the_cluster_is_read_an_eighth_and_sized_half_a_quarter_RED(self):
        log, h = _fixture(EIGHTH)
        _run(log)
        r = log.verdict(Q.HEAD_INK_IS_A_REST, CL)
        self.assertEqual((r.outcome, r.value, r.reason), (Outcome.DECIDED, "eighth", "rest8th_head_ink"))
        self.assertEqual(r.detail["head"], h.to_key())
        out = consequences.size_head_ink_rest(log, CL, r)
        self.assertEqual(len(out), 1)
        d = log.verdict(Q.DURATION, CL)
        self.assertEqual((d.value["beats"], d.value["is_rest"], d.value["unboxed_rest"]), (0.5, True, True))
        self.assertEqual(d.decider, "size_head_ink_rest")
        self.assertEqual(consequences.size_head_ink_rest(log, CL, r), [])          # idempotent

    def test_a_quarter_rest_shaped_ink_is_a_quarter_rest(self):
        log, h = _fixture(QUARTER)
        _run(log)
        self.assertEqual(log.verdict(Q.HEAD_INK_IS_A_REST, CL).value, "quarter")
        consequences.size_head_ink_rest(log, CL, log.verdict(Q.HEAD_INK_IS_A_REST, CL))
        self.assertEqual(log.verdict(Q.DURATION, CL).value["beats"], 1.0)

    def test_sean_tile_3_a_rest_one_space_above_the_middle_line_is_a_DISPLACED_eighth(self):
        log, h = _fixture(SEAN_TILE_3)
        _run(log)
        r = log.verdict(Q.HEAD_INK_IS_A_REST, CL)
        self.assertEqual((r.value, r.reason), ("eighth", "rest8th_head_ink_displaced"))
        self.assertTrue(r.detail["displaced"])
        self.assertTrue(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h).value)

    def test_CONTROL_a_stem_touching_the_head_declines_it_a_real_note_survives(self):
        """The control that can fail: the same rest-shaped ink, but a stem runs along the head."""
        log, h = _fixture(QUARTER, stem=(420, 0, 10, 300))
        _run(log)
        self.assertFalse(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h).value)
        self.assertNotEqual(log.verdict(Q.HEAD_INK_IS_A_REST, CL).outcome, Outcome.DECIDED)

    def test_CONTROL_a_stem_touching_the_ink_only_also_declines(self):
        log, h = _fixture(EIGHTH, stem=(445, 0, 10, 300))                      # past the head, inside the ink box
        log2, h2 = _fixture(EIGHTH, stem=(430, 0, 12, 400))
        _run(log2)
        self.assertFalse(log2.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h2).value)

    def test_CONTROL_flag_off_the_head_stands(self):
        log, h = _fixture(EIGHTH)
        _run(log, env={H.ENV: "0"})
        self.assertFalse(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h).value)
        self.assertNotEqual(log.verdict(Q.HEAD_INK_IS_A_REST, CL).outcome, Outcome.DECIDED)

    def test_the_flag_defaults_ON(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(H.ENV, None)
            self.assertTrue(H.enabled())
        for on in ("1", "true", "yes", "on"):
            with mock.patch.dict(os.environ, {H.ENV: on}):
                self.assertTrue(H.enabled())

    def test_CONTROL_a_flat_shaped_cluster_under_a_head_is_not_a_rest(self):
        log, h = _fixture(FLAT)
        _run(log)
        self.assertFalse(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h).value)

    def test_CONTROL_head_sized_ink_is_not_a_rest(self):
        """A bare black head's ink is about 1.3 x 1.0 spaces: below the rest windows."""
        log, h = _fixture(dict(w=1.3, h=1.0, step=4.0, mass_y=0.5, col=0.9, profile=[0.5, 0.9, 1.0, 1.0, 0.9, 0.5]))
        _run(log)
        self.assertFalse(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h).value)

    def test_CONTROL_a_displaced_QUARTER_is_not_widened(self):
        """Only the eighth gets a displaced window (one measurement, NOT CONFIRMED)."""
        log, h = _fixture({**QUARTER, "step": 6.4})
        _run(log)
        self.assertFalse(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h).value)

    def test_CONTROL_an_eighth_far_off_the_staff_is_not_displaced_into_a_rest(self):
        log, h = _fixture({**EIGHTH, "step": 9.0})
        _run(log)
        self.assertFalse(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h).value)

    def test_CONTROL_a_rest_box_twin_is_2_142s_not_this_rules(self):
        log, h = _fixture(EIGHTH, rest_twin=True)
        _run(log)
        self.assertEqual(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h).reason, "is_a_rest_twin")

    def test_CONTROL_two_head_boxes_on_one_ink_are_not_a_rest(self):
        log, h = _fixture(EIGHTH, second_head=True)
        _run(log)
        self.assertFalse(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h).value)

    def test_CONTROL_ink_covered_by_a_flag_or_clef_class_is_not_a_head_s_ink(self):
        log, h = _fixture(EIGHTH, by=("flag8thUp", "noteheadBlackOnLine"))
        _run(log)
        self.assertFalse(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h).value)

    def test_CONTROL_a_cluster_the_head_covers_too_little_is_not_its_ink(self):
        log, h = _fixture(EIGHTH)
        far = Log()
        _staff_space(far, 100)
        h2 = _head(far, 0)
        _cluster(far, **EIGHTH, cover=0.1)
        _run(far)
        self.assertFalse(far.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h2).value)

    def test_the_decision_reads_no_bar(self):
        spec = adjudicate.REGISTRY[Q.HEAD_INK_IS_A_REST]
        for banned in (Q.METER, Q.DURATION, Q.EVENT):
            self.assertNotIn(banned, spec.wants)

    def test_the_rule_is_caused_by_the_ink_reading_alone(self):
        rule = [r for r in __import__("tools.omr.staged.evaluate", fromlist=["RULES"]).RULES
                if r.consequence.value == "size_head_ink_rest"]
        self.assertEqual(len(rule), 1)
        self.assertEqual(rule[0].cause, Q.HEAD_INK_IS_A_REST)

    def test_every_reason_is_classified_in_the_margin_registry(self):
        problems, _notes = margins.check_margins()
        self.assertEqual([p for p in problems if "head_ink" in p or "rest_shape" in p], [])


class TestExportWritesTheRest(unittest.TestCase):
    TWO_FOUR = {"numerator": 2, "denominator": 4, "raw": "2/4"}
    SUB = "glyph/0/0/0/0/350000"
    QUARTER = {"beats": 1.0, "written": 1.0, "dots": 0}
    EIGHTH = {"beats": 0.5, "written": 0.5, "dots": 0}

    def _page(self, notes, *, rest=None):
        from tools.omr.tests.test_staged_export import _obs, _one_staff_page, _vrd
        page = _one_staff_page(notes=notes, meter=self.TWO_FOUR)
        if rest is not None:
            page["record"]["observations"].append(_obs(
                5000, self.SUB, Q.UNBOXED_REST_SHAPE, 2.2, bbox_canonical=[500, 40, 530, 100],
                bbox_page_px=[500.0, 40.0, 530.0, 100.0]))
            page["record"]["verdicts"].append(_vrd(5001, self.SUB, Q.HEAD_INK_IS_A_REST, rest))
            beats = 0.5 if rest == "eighth" else 1.0
            page["record"]["verdicts"].append(_vrd(
                5002, self.SUB, Q.DURATION,
                {"beats": beats, "written": beats, "dots": 0, "beam_levels": 0, "is_rest": True,
                 "unboxed_rest": True, "head_ink_rest": True}))
        return page

    def test_the_rest_read_off_a_head_s_ink_is_written_as_a_rest_RED(self):
        import xml.etree.ElementTree as ET
        from tools.omr.staged import export as SX
        notes = [("C4", self.QUARTER), ("D4", self.EIGHTH)]
        _xml0, rep0 = SX.to_musicxml(self._page(notes))
        self.assertEqual(rep0["bars_held_out_sum"]["bars"], 1)                  # control: no rest, bar short
        xml1, rep1 = SX.to_musicxml(self._page(notes, rest="eighth"))
        self.assertEqual(rep1["bars_held_out_sum"]["bars"], 0)
        root = ET.fromstring(xml1)
        self.assertEqual(len(root.findall(".//note/pitch")), 2)
        self.assertEqual(len(root.findall(".//note/rest")), 1)
        self.assertTrue(rep1["balance"]["balanced"])


if __name__ == "__main__":
    unittest.main()
