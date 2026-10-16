"""ROADMAP 2.151 -- a dot is a dot whatever class the detector gave it
(STAGED ADJUDICATE, `OMR_DOT_BOXED_AS_A_HEAD`, default ON).

Real numbers (canonical cell frame, Brahms 317803 small re-gather pp.0-1 on
this tree): Sean's 2.146 tile 23 is `glyph/1/0/2/1/15`, a dotted quarter on
the middle line whose dot was boxed `noteheadBlackOnLine` (`/7`, 0.51 x 0.50
spaces) and refused `too_narrow` -- the dot was SEEN and nothing read it, so
the quarter was written plain. Brahms p0 `0/0/4/3`: a refused `head_cut_piece`
twin of the half `/2` stood nearer the dot `/0` and took it, so the real half
was written plain. RED first: every rule fails with the flag off; every
refusal has a control that can fail.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import aug_dot_join as J
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.staged.record import Log, Outcome, Q, READERS

ON = {"OMR_DOT_BOXED_AS_A_HEAD": "1"}
OFF = {"OMR_DOT_BOXED_AS_A_HEAD": "0"}
CELL = R.cell(1, 0, 2, 1)
SPACE = 85.5
HEAD = (1212, 454, 120, 101)          # tile 23's quarter, on the middle line
MARK = (1368, 433, 44, 43)            # its dot, boxed as a notehead


def _log():
    log = Log()
    log.observe(CELL, Q.CELL_STAFF_SPACE, SPACE, reader=READERS.GEOMETRY,
                frame="cell:1")
    return log


#: tile 23's own canonical -> page map (head `/15`: canonical x 1212 / y 454
#: at page 2219.40 / 1081.87; 120 canonical px = 38.56 page px)
K = 38.555 / 120.0


def _page(box):
    x, y, w, h = box
    x0, y0 = 2219.40 + (x - 1212) * K, 1081.87 + (y - 454) * K
    return [x0, y0, x0 + w * K, y0 + h * K]


def _box(log, gi, cls, box, pos, *, head=True):
    g = R.glyph(1, 0, 2, 1, gi)
    if head:
        log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR,
                    frame="cell:1", score=0.7)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR,
                frame="cell:1", score=0.7, bbox_page_px=_page(box))
    if pos is not None and head:
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, float(pos),
                    reader=READERS.GEOMETRY, frame="cell:1")
    return g


def _run(log, env):
    with mock.patch.dict(os.environ, env):
        adjudicate.run(log)
    return log


def _dots(log, g):
    v = log.verdict(Q.DURATION, g)
    return v.outcome, (v.value or {}).get("dots") if v.value else None, v


def _tile23(mark_pos=2.8304, mark=MARK, mark_cls="noteheadBlackOnLine"):
    log = _log()
    head = _box(log, 15, "noteheadBlackOnLine", HEAD, 4.0)
    m = _box(log, 7, mark_cls, mark, mark_pos)
    return log, head, m


class TestTheConstantIsTheGates(unittest.TestCase):
    def test_dot_shaped_size_is_the_notehead_gates_own(self):
        self.assertEqual(J.DOT_SHAPED_MAX_SPACES, NP.DOT_SIZED_MAX_SPACES)


class TestADotBoxedAsAHeadIsADot(unittest.TestCase):
    def test_the_gate_refuses_the_mark_in_both_arms(self):
        for env in (OFF, ON):
            log, head, m = _tile23()
            _run(log, env)
            r = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, m)
            self.assertEqual((r.value, r.reason), (True, "too_narrow"))

    def test_RED_tile23_the_quarter_takes_the_dot(self):
        log, head, m = _tile23()
        _run(log, ON)
        outcome, dots, v = _dots(log, head)
        self.assertEqual((outcome, dots), (Outcome.DECIDED, 1))
        self.assertEqual(v.value["written"], 1.5)

    def test_CONTROL_flag_off_the_quarter_stays_plain(self):
        log, head, m = _tile23()
        _run(log, OFF)
        outcome, dots, v = _dots(log, head)
        self.assertEqual((outcome, dots), (Outcome.DECIDED, 0))

    def test_CONTROL_a_mark_ON_A_LINE_is_not_a_dot(self):
        # Sean 2026-10-14: an augmentation dot is always in a space. The same
        # box measured on the line above the head (step 2) lengthens nothing,
        # and narrows nothing (the position says no).
        log, head, m = _tile23(mark_pos=2.05)
        _run(log, ON)
        outcome, dots, v = _dots(log, head)
        self.assertEqual((outcome, dots), (Outcome.DECIDED, 0))

    def test_RULE8_position_cannot_tell_narrows_never_lengthens(self):
        # no staff position for the mark: not enough to lengthen the note,
        # and not "no dot" either -- {as read, dotted}
        log, head, m = _tile23(mark_pos=None)
        _run(log, ON)
        outcome, _dots_, v = _dots(log, head)
        self.assertEqual(outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, J.NARROWED_REASON)
        self.assertEqual(sorted(c.value["dots"] for c in v.candidates), [0, 1])
        self.assertEqual(v.detail["kind"], "narrowed_dot_boxed_as_a_head")

    def test_CONTROL_rule8_flag_off_leaves_it_plain(self):
        log, head, m = _tile23(mark_pos=None)
        _run(log, OFF)
        outcome, dots, v = _dots(log, head)
        self.assertEqual((outcome, dots), (Outcome.DECIDED, 0))

    def test_CONTROL_a_head_sized_box_is_not_a_dot(self):
        # a real (kept) head to the right is never a dot, whatever its place
        log, head, m = _tile23(mark=(1368, 433, 118, 100))
        _run(log, ON)
        r = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, m)
        self.assertIsNot(r.value, True)
        outcome, dots, v = _dots(log, head)
        self.assertEqual((outcome, dots), (Outcome.DECIDED, 0))

    def test_CONTROL_a_mark_left_of_the_head_is_not_its_dot(self):
        log, head, m = _tile23(mark=(1100, 433, 44, 43))
        _run(log, ON)
        outcome, dots, v = _dots(log, head)
        self.assertEqual((outcome, dots), (Outcome.DECIDED, 0))

    def test_CONTROL_a_mark_far_right_is_not_its_dot(self):
        # four spaces right: another note's business
        log, head, m = _tile23(mark=(1332 + 4 * 86, 433, 44, 43))
        _run(log, ON)
        outcome, dots, v = _dots(log, head)
        self.assertEqual((outcome, dots), (Outcome.DECIDED, 0))


class TestARefusedHeadNeverOwnsADot(unittest.TestCase):
    """Brahms p0 `0/0/4/3`: the dot `/0` (canonical 300,940,41,39) is right of
    the real half `/2` (129,989,123,81, step 12.117) and of its refused
    `head_cut_piece` twin `/7` (127,945,124,77) which stands level with it."""

    def _case(self, env):
        log = Log()
        cell = R.cell(0, 0, 4, 3)
        log.observe(cell, Q.CELL_STAFF_SPACE, 100.0, reader=READERS.GEOMETRY,
                    frame="cell:3")
        def g(gi, cls, box, pos=None, head=True):
            s = R.glyph(0, 0, 4, 3, gi)
            if head:
                log.observe(s, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR,
                            frame="cell:3", score=0.5)
            log.observe(s, Q.GLYPH_BOX, (cls,) + box, reader=READERS.DETECTOR,
                        frame="cell:3", score=0.5)
            if pos is not None:
                log.observe(s, Q.NOTEHEAD_STAFF_POSITION, pos,
                            reader=READERS.GEOMETRY, frame="cell:3")
            return s
        half = g(2, "noteheadHalfInSpace", (129, 989, 123, 81), 12.117)
        twin = g(7, "noteheadHalfInSpace", (127, 945, 124, 77), 12.117)
        d = g(0, "augmentationDot", (300, 940, 41, 39), head=False)
        log.observe(d, Q.AUG_DOT, (320, 959), reader=READERS.DETECTOR,
                    frame="cell:3", score=0.7, detector_role="dot",
                    detector_class="augmentationDot")
        # the role verdict the record held: augmentation, naming the half
        log.record(R.Verdict(
            id=log._next_id("vrd"), subject=d, quantity=Q.DOT_ROLE,
            outcome=Outcome.DECIDED, value="augmentation",
            decider="adjudicate_dot_role",
            reason="right_of_and_level_with_a_head",
            detail={"head": half.to_key()}))
        # the refusal the record held for the twin (the gate's head-cut rule
        # needs ledger rows this fixture does not build)
        log.record(R.Verdict(
            id=log._next_id("vrd"), subject=twin,
            quantity=Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, outcome=Outcome.DECIDED,
            value=True, decider="adjudicate_notehead_is_not_a_notehead",
            reason="head_cut_piece"))
        return log, half, twin, d

    def test_RED_the_real_half_keeps_its_dot(self):
        from tools.omr.staged.adjudicators import rhythm as RH
        log, half, twin, d = self._case(ON)
        cell = half.at(R.Kind.CELL)
        ev_half = adjudicate.Evidence(log, half,
                                      adjudicate.REGISTRY[Q.DURATION])
        boxes = RH._cell_boxes(ev_half, cell)
        hb = RH._xywh_head(boxes[half.to_key()].value)
        with mock.patch.dict(os.environ, ON):
            got = RH._attached_dots(ev_half, cell, hb, 100.0)
        self.assertEqual([r.subject for r in got], [d])

    def test_CONTROL_flag_off_the_twin_takes_it_from_the_half(self):
        from tools.omr.staged.adjudicators import rhythm as RH
        log, half, twin, d = self._case(OFF)
        cell = half.at(R.Kind.CELL)
        ev_half = adjudicate.Evidence(log, half,
                                      adjudicate.REGISTRY[Q.DURATION])
        boxes = RH._cell_boxes(ev_half, cell)
        hb = RH._xywh_head(boxes[half.to_key()].value)
        with mock.patch.dict(os.environ, OFF):
            got = RH._attached_dots(ev_half, cell, hb, 100.0)
        self.assertEqual(got, [])


class TestOneInkCountsOnce(unittest.TestCase):
    """Brahms p0 `0/0/6/1`: the dot `/19` of the space note `/11` is ALSO
    boxed as a notehead `/18` (refused `too_narrow`); the first cut gave that
    twin to the line note `/2` beside it, which went out double-dotted."""

    def _case(self, with_dot_box=True):
        log = Log()
        cell = R.cell(0, 0, 6, 1)
        log.observe(cell, Q.CELL_STAFF_SPACE, 100.0, reader=READERS.GEOMETRY,
                    frame="cell:1")

        def g(gi, cls, box, page, pos=None, head=True):
            s = R.glyph(0, 0, 6, 1, gi)
            if head:
                log.observe(s, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR,
                            frame="cell:1", score=0.6)
            log.observe(s, Q.GLYPH_BOX, (cls,) + box, reader=READERS.DETECTOR,
                        frame="cell:1", score=0.6, bbox_page_px=page)
            if pos is not None and head:
                log.observe(s, Q.NOTEHEAD_STAFF_POSITION, pos,
                            reader=READERS.GEOMETRY, frame="cell:1")
            return s
        line = g(2, "noteheadBlackOnLine", (368, 543, 130, 116),
                 [2229.76, 3937.76, 2271.36, 3974.88], 0.02)
        space = g(11, "noteheadBlackInSpace", (253, 606, 121, 103),
                  [2192.96, 3957.92, 2231.68, 3990.88], 1.14)
        g(18, "noteheadBlackOnLine", (531, 633, 46, 43),
          [2281.92, 3966.56, 2296.64, 3980.32], 1.08)
        if with_dot_box:
            d = g(19, "augmentationDot", (531, 630, 45, 45),
                  [2281.92, 3965.6, 2296.32, 3980.0], head=False)
            log.observe(d, Q.AUG_DOT, (553, 652), reader=READERS.DETECTOR,
                        frame="cell:1", score=0.38, detector_role="dot",
                        detector_class="augmentationDot")
            log.observe(d, Q.DOT_STAFF_POSITION, 0.67, reader=READERS.GEOMETRY,
                        frame="cell:1", step=1, on="space", residual=0.33,
                        margin=0.17, basis="local_ink",
                        staff=R.staff(0, 0, 6).to_key(), home=True)
        return log, line, space

    def test_the_twin_of_a_dot_box_adds_no_dot(self):
        log, line, space = self._case()
        _run(log, ON)
        self.assertEqual(log.verdict(Q.DURATION, line).value["dots"], 0)
        self.assertEqual(log.verdict(Q.DURATION, space).value["dots"], 1)

    def test_CONTROL_the_same_in_the_base(self):
        log, line, space = self._case()
        _run(log, OFF)
        self.assertEqual(log.verdict(Q.DURATION, line).value["dots"], 0)
        self.assertEqual(log.verdict(Q.DURATION, space).value["dots"], 1)

    def test_CONTROL_without_the_dot_box_the_mark_is_read(self):
        # the twin rule has teeth only because the dot box is there: alone,
        # the mark is somebody's dot (exactly one head takes it)
        log, line, space = self._case(with_dot_box=False)
        _run(log, ON)
        got = [log.verdict(Q.DURATION, s) for s in (line, space)]
        n = sum((v.value or {}).get("dots", 0) for v in got
                if v.outcome is Outcome.DECIDED)
        n += sum(1 for v in got if v.outcome is Outcome.NARROWED)
        self.assertEqual(n, 1)


class TestDefaultOn(unittest.TestCase):
    def test_default_on(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMR_DOT_BOXED_AS_A_HEAD", None)
            self.assertTrue(J.dot_boxed_as_a_head_enabled())

    def test_off_words_disable(self):
        for w in ("0", "false", "no", "off"):
            with mock.patch.dict(os.environ, {"OMR_DOT_BOXED_AS_A_HEAD": w}):
                self.assertFalse(J.dot_boxed_as_a_head_enabled())


if __name__ == "__main__":
    unittest.main()
