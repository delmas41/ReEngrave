"""ROADMAP 2.56: the far-head ledger reader, wired into STAGED.

`tools/omr/annotate/far_head_reader.py` is Sean's accepted arm E3 (round-8
ledgers + exclusion rules + template-sized head box). `gather.gather_far_head_
ledger_positions` files its result as `Q.FAR_HEAD_LEDGER_POSITION` -- an
Observation under `READERS.LEDGER_FARHEAD`, or an Abstention with a reason
word -- beside (never over) the geometry row; `adjudicators.position.
adjudicate_notehead_position` decides `Q.NOTEHEAD_POSITION` from it; and
EVALUATE's `restate_pitch` reads that verdict ahead of the geometry row.

GATHER+ADJUDICATE is the measured scope (Sean, 2026-09-30); the one EVALUATE
line is the consumer that keeps the new quantity from being a producer-only gap.

⚠️ RUN RED FIRST: against the tree before this item, every test here fails on
`AttributeError`/`KeyError` (no `gather_far_head_ledger_positions`, no
`Q.FAR_HEAD_LEDGER_POSITION`, no registered decision). The control that can
fail is `test_the_same_head_with_its_ledgers_erased_is_not_read_at_the_ledger`.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import cv2
import numpy as np

from tools.omr.annotate import far_head_reader as FH
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401 -- registers decisions
from tools.omr.staged import consequences
from tools.omr.staged import gather
from tools.omr.staged.record import (Log, Outcome, Q, Subject, cell as R_cell,
                                     glyph as R_glyph, staff as R_staff)

SP = 20.0                                   # staff space, px
TOP = 200.0                                 # top staff line
LINES = [TOP + SP * i for i in range(5)]    # 200..280
HEAD_W, HEAD_H = 28.0, 21.0
SHAPE = dict(long_sp=1.4, short_sp=1.05, tilt=28.0)


def _page(*, ledgers=True, head_pos=-4, n_px=(1000, 600)):
    """A white page: five staff lines, and a filled head `head_pos` half-steps
    above the top line with its ledger lines (positions -2, -4, ...) drawn
    through it when `ledgers`. Returns (rgb, box)."""
    h, w = n_px
    img = np.full((h, w), 255, np.uint8)
    for y in LINES:
        img[int(y) - 1:int(y) + 2, 40:560] = 0
    cx = 300.0
    cy = TOP + head_pos * (SP / 2.0)
    if ledgers:
        for p in range(-2, head_pos - 1, -2):
            y = int(TOP + p * SP / 2.0)
            img[y - 1:y + 2, int(cx - 22):int(cx + 22)] = 0
    cv2.ellipse(img, (int(cx), int(cy)), (int(HEAD_W / 2), int(HEAD_H / 2)), -28,
                0, 360, 0, -1)
    box = (cx - HEAD_W / 2, cy - HEAD_H / 2, cx + HEAD_W / 2, cy + HEAD_H / 2)
    return img, box


class _Det:
    def __init__(self, box, name="noteheadBlackOnLine", conf=0.9):
        # page px -> canonical via a 1:1 cell at the page origin
        self.smufl_name = name
        self.category = "notehead"
        self.confidence = conf
        self.x_canonical, self.y_canonical = box[0], box[1]
        self.width_canonical = box[2] - box[0]
        self.height_canonical = box[3] - box[1]


class _Cell:
    def __init__(self):
        self.page_index, self.staff_index, self.measure_index = 0, 0, 0
        self.bbox_page_px = (0.0, 0.0, 600.0, 1000.0)
        self.upscale_factor = 1.0


class _Staff:
    staff_index = 0
    line_ys = LINES


class _Page_:
    page_index = 0

    def __init__(self, gray):
        self.rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)


class _Pws:
    def __init__(self, gray):
        self.page = _Page_(gray)
        self.staves = [_Staff()]


class _PooledPage(FH.FarHeadPage):
    """The real page reader, with eight clean on-line heads on offer -- a
    synthetic page cannot print eight gate-passing heads cheaply, and the
    SHAPE measurement is not what these tests exercise (the parity run
    against the benchmark scorer is)."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.samples = [dict(SHAPE)] * 8


def _run(gray, box, *, geom_pos=-4.0, state=None, patch=True):
    log = Log()
    sub = R_cell(0, 0, 0, 0)
    det = _Det(box)
    g = R_glyph(0, 0, 0, 0, 0)
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, geom_pos, reader="geometry",
                frame="cell:0", residual=0.0, rounded=int(round(geom_pos)))
    dets = {sub.to_key(): [det]}
    local = {0: (0, 0)}
    ctx = mock.patch.object(FH, "FarHeadPage", _PooledPage) if patch \
        else mock.patch.object(FH, "FarHeadPage", FH.FarHeadPage)
    with ctx:
        census = gather.gather_far_head_ledger_positions(
            log, _Pws(gray), [_Cell()], local, dets, state)
    return log, g, census


class TestTheGatherReader(unittest.TestCase):
    def test_a_far_head_on_its_ledgers_is_filed_under_its_own_reader(self):
        gray, box = _page(ledgers=True, head_pos=-4)
        log, g, census = _run(gray, box)
        rows = log.rows(Q.FAR_HEAD_LEDGER_POSITION, g)
        self.assertEqual(census["far"], 1)
        self.assertEqual(len(rows), 1, census)
        self.assertEqual(rows[0].value, -4)
        self.assertEqual(rows[0].reader, "ledger_farhead")
        # a SECOND witness: the geometry row is still the only one of its kind
        self.assertEqual(len(log.rows(Q.NOTEHEAD_STAFF_POSITION, g)), 1)

    def test_the_same_head_with_its_ledgers_erased_is_not_read_at_the_ledger(self):
        """CLAUDE.md §2 rule 7 -- a control that can fail. Same head, same
        place, NO printed ledgers: the reader must not report -4."""
        gray, box = _page(ledgers=False, head_pos=-4)
        log, g, _census = _run(gray, box)
        rows = log.rows(Q.FAR_HEAD_LEDGER_POSITION, g)
        self.assertTrue(not rows or rows[0].value != -4,
                        "a head with no ledger line was read as sitting on one")

    def test_an_unreadable_far_head_is_an_abstention_with_a_reason_word(self):
        gray, box = _page(ledgers=False, head_pos=-4)
        log, g, _census = _run(gray, box)
        if not log.rows(Q.FAR_HEAD_LEDGER_POSITION, g):
            refusals = log.refusals(Q.FAR_HEAD_LEDGER_POSITION, g)
            self.assertEqual(len(refusals), 1)
            self.assertEqual(refusals[0].reason, "ledger_not_read")
            self.assertTrue(refusals[0].detail.get("ledger_reason"))

    def test_an_on_staff_head_is_never_read(self):
        gray, box = _page(ledgers=False, head_pos=2)
        log, g, census = _run(gray, box, geom_pos=2.0)
        self.assertEqual(census["far"], 0)
        self.assertEqual(log.rows(Q.FAR_HEAD_LEDGER_POSITION, g), ())
        self.assertEqual(log.refusals(Q.FAR_HEAD_LEDGER_POSITION, g), ())

    def test_the_first_space_outside_the_staff_is_on_staff(self):
        gray, box = _page(ledgers=False, head_pos=-1)
        log, g, census = _run(gray, box, geom_pos=-1.0)
        self.assertEqual(census["far"], 0)

    def test_a_page_with_no_head_size_abstains_no_page_shape(self):
        """The reader does not borrow a size it did not measure."""
        gray, box = _page(ledgers=True, head_pos=-4)
        log, g, census = _run(gray, box, patch=False)   # real page: no clean heads
        self.assertEqual(len(log.rows(Q.FAR_HEAD_LEDGER_POSITION, g)), 0)
        refusals = log.refusals(Q.FAR_HEAD_LEDGER_POSITION, g)
        self.assertEqual([r.reason for r in refusals], ["no_page_shape"])

    def test_the_switch_turns_the_reader_off(self):
        gray, box = _page(ledgers=True, head_pos=-4)
        with mock.patch.dict(os.environ, {gather.FARHEAD_LEDGER_ENV: "0"}):
            log, g, census = _run(gray, box)
        self.assertEqual(census["far"], 0)
        self.assertEqual(log.rows(Q.FAR_HEAD_LEDGER_POSITION, g), ())

    def test_a_typo_leaves_the_default_on(self):
        gray, box = _page(ledgers=True, head_pos=-4)
        with mock.patch.dict(os.environ, {gather.FARHEAD_LEDGER_ENV: "banana"}):
            log, g, census = _run(gray, box)
        self.assertEqual(census["far"], 1)

    def test_a_held_page_is_read_when_the_pool_reaches_the_minimum(self):
        gray, box = _page(ledgers=True, head_pos=-4)
        state = gather.FarHeadState()
        log = Log()
        g = R_glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, -4.0, reader="geometry",
                    frame="cell:0", residual=0.0, rounded=-4)
        dets = {R_cell(0, 0, 0, 0).to_key(): [_Det(box)]}
        # first pass: the real page cannot size a head -> held, nothing filed
        census = gather.gather_far_head_ledger_positions(
            log, _Pws(gray), [_Cell()], {0: (0, 0)}, dets, state)
        self.assertEqual(census["held"], 1)
        self.assertEqual(log.rows(Q.FAR_HEAD_LEDGER_POSITION, g), ())
        # the pool reaches the minimum (a later page supplies the heads)
        state.pool.extend([dict(SHAPE)] * 8)
        pooled = FH.pooled_shape(state.pool)
        self.assertIsNotNone(pooled)
        gather.finish_far_head_ledger_positions(log, state)
        rows = log.rows(Q.FAR_HEAD_LEDGER_POSITION, g)
        self.assertEqual([r.value for r in rows], [-4])
        self.assertTrue(rows[0].detail["shape_source"].startswith("document pool"))


class TestTheDecision(unittest.TestCase):
    def _decide(self, log, g):
        spec = adjudicate.REGISTRY[Q.NOTEHEAD_POSITION]
        log.freeze()
        return adjudicate.adjudicate_one(log, spec, g)

    def test_the_decision_is_registered_in_the_order(self):
        self.assertIn(Q.NOTEHEAD_POSITION, adjudicate.ORDER)
        self.assertIn(Q.FAR_HEAD_LEDGER_POSITION,
                      adjudicate.REGISTRY[Q.NOTEHEAD_POSITION].wants)

    def test_a_ledger_reading_decides_the_position(self):
        log = Log()
        g = R_glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, -3.0, reader="geometry",
                    frame="cell:0")
        log.observe(g, Q.FAR_HEAD_LEDGER_POSITION, -4, reader="ledger_farhead",
                    frame="cell:0", ledger_reason="x", box_source="standard",
                    geometry_position=-3)
        v = self._decide(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, -4)
        self.assertEqual(v.reason, "ledger_position")
        self.assertIs(v.detail["agrees_with_geometry"], False)
        self.assertEqual(v.detail["geometry_position"], -3)

    def test_an_unread_ledger_abstains_and_never_borrows_the_geometry(self):
        """CLAUDE.md §2 rule 8."""
        log = Log()
        g = R_glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, -4.0, reader="geometry",
                    frame="cell:0")
        log.abstain(g, Q.FAR_HEAD_LEDGER_POSITION, reader="ledger_farhead",
                    frame="cell:0", reason="ledger_not_read",
                    ledger_reason="no_rungs")
        v = self._decide(log, g)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "ledger_not_read")
        self.assertIsNone(v.value)

    def test_no_page_shape_passes_through(self):
        log = Log()
        g = R_glyph(0, 0, 0, 0, 0)
        log.abstain(g, Q.FAR_HEAD_LEDGER_POSITION, reader="ledger_farhead",
                    frame="cell:0", reason="no_page_shape")
        v = self._decide(log, g)
        self.assertEqual(v.reason, "no_page_shape")


class TestTheConsumer(unittest.TestCase):
    """EVALUATE's `restate_pitch` reads the decided position ahead of the
    geometry row -- the consumer that keeps the verdict from being a producer
    with nothing downstream."""

    def _pitch(self, geom, ledger_outcome):
        log = Log()
        g = R_glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, float(geom), reader="geometry",
                    frame="cell:0")
        if ledger_outcome is not None:
            log.observe(g, Q.FAR_HEAD_LEDGER_POSITION, ledger_outcome,
                        reader="ledger_farhead", frame="cell:0")
        else:
            log.abstain(g, Q.FAR_HEAD_LEDGER_POSITION, reader="ledger_farhead",
                        frame="cell:0", reason="ledger_not_read")
        staff = R_staff(0, 0, 0)
        clef = consequences._verdict(log, staff, Q.CLEF, "treble",
                                     decider="t", reason="t", basis=())
        log.freeze()
        far = adjudicate.adjudicate_one(
            log, adjudicate.REGISTRY[Q.NOTEHEAD_POSITION], g)
        return consequences.restate_pitch(log, staff, clef), far

    def test_a_decided_ledger_position_sets_the_pitch(self):
        out, far = self._pitch(geom=-3, ledger_outcome=-4)
        self.assertEqual(far.outcome, Outcome.DECIDED)
        self.assertEqual([v.value for v in out], ["C6"])     # -4 on a treble staff

    def test_an_abstained_ledger_leaves_the_geometry_pitch_as_before(self):
        out, far = self._pitch(geom=-3, ledger_outcome=None)
        self.assertEqual(far.outcome, Outcome.ABSTAINED)
        self.assertEqual(len(out), 1)
        self.assertNotEqual(out[0].value, "C6")              # position -3, not -4


if __name__ == "__main__":
    unittest.main()
