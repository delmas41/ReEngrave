"""ROADMAP 2.47c — a meter digit's ink boxed TWICE, once as `timeSig*`
(correctly) and once as a notehead, was never refused by anything.

`benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` §21b and
`benchmarks/omr-measure-partition-2026-09/FINDINGS.md` §10c/§11c both
crop-verify the SAME ink on Brahms 1/i (Breitkopf 317803) PDF p0, system 0's
cautionary "9/8": the detector draws a `timeSig8` box and, on the same ink,
a SECOND box at IoU 0.94-0.96 classed `noteheadWholeInSpace` (confidence as
low as 0.267 — the open-bowl shape a round numeral shares with a hollow
head). The existing same-class duplicate rule (`notehead_precision.
_notehead_duplicate_box_refusal`, ROADMAP 2.30) never compares against a
DIFFERENT class, so this cross-family duplicate reached export as a real
note — one of the `+1.0 quarter` bar-sum population's two named causes.

`notehead_precision._timesig_digit_duplicate_refusal` ports the SAME
geometric fact across the family boundary: a notehead-classed box at IoU >
`TIMESIG_DIGIT_DUPLICATE_IOU_MIN` (0.9) against a `timeSig*`-classed box in
the SAME cell is that digit's own ink, not a head. IoU ALONE is the gate
(no centre test, unlike 2.30) because a `timeSig*` box and a real nearby
notehead are two independently-drawn boxes that never share 90% of their
area by chance — see the module's own 2.47c section comment.

⚠️ RUN RED FIRST, against the tree before this branch's edit to
`notehead_precision.py`: every test below that expects the refusal fails,
because `TIMESIG_DIGIT_DUPLICATE_IOU_MIN`/`_timesig_digit_duplicate_
refusal` do not exist and `adjudicate_notehead_is_not_a_notehead` never
compares a notehead box against a `timeSig*` box at all — the duplicate
decides `value=False, reason="notehead"` on the unmodified tree.

⚠️ THE POSITIVE CONTROL (CLAUDE.md §6b) is
`test_a_real_notehead_beside_a_timesig_box_is_kept`: without the IoU floor,
a rule that refused every notehead sharing a cell with ANY time-signature
digit would also pass the RED->GREEN test, and would wrongly delete a real
first note of the bar printed just after a meter change.

⚠️ ROADMAP 2.47bc CLOSES THE GAP THE PARAGRAPH ABOVE USED TO DESCRIBE.
`Q.MEASURE_PARTITION` still runs BEFORE `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` in
`adjudicate.ORDER` (unchanged -- `adjudicate.ORDER` is not touched by this
round), so `structure._trailing_cell_is_cautionary_only` still cannot read
this rule's REFUSAL verdict. What changed is that the IoU>0.9 "same ink"
test itself moved to `geometry.is_timesig_digit_ink`/`geometry.box_iou`
(ONE constant, `geometry.TIMESIG_DIGIT_DUPLICATE_IOU_MIN`, ONE function),
shared by BOTH `notehead_precision._timesig_digit_duplicate_refusal` (this
file's own `TestTimeSigDigitDuplicate`, above) and `structure._trailing_
cell_is_cautionary_only` directly -- so the structure-stage rule now asks
the identical geometric question of the raw detector boxes itself, without
needing the notehead-stage refusal to have run first. `TestMeasure
PartitionOrderingGap` below is the RED->GREEN test for that connection:
RED on the tree before this round's edit to `structure.py` (value stayed 8,
reason "read" -- the assertion this test carried before this round), GREEN
after (value 7, reason "cautionary_tail_not_a_bar"). `adjudicate.ORDER`
itself is untouched, confirmed by `test_order_is_unchanged` below.

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.staged.adjudicators import structure as _structure
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_notehead_precision import (
    CELL, _cell_geometry, _notehead, _run, _verdict)


def _timesig_box(log, gi, *, cls="timeSig8", x_c, y_c, w_c=100.0, h_c=100.0,
                 conf=0.663):
    """A `timeSig*`-classed detection in the SAME cell — no notehead-only
    quantities (`Q.NOTEHEAD_CLASS` etc.), matching what the detector itself
    files for this class."""
    g = R.glyph(CELL.page, CELL.system, CELL.staff, CELL.cell, gi)
    log.observe(g, Q.GLYPH_BOX, (cls, x_c, y_c, w_c, h_c),
                reader=READERS.DETECTOR, frame="cell:0", score=conf,
                category="timeSig")
    return g


class TestTimeSigDigitDuplicate(unittest.TestCase):
    """`_timesig_digit_duplicate_refusal`, in isolation."""

    def test_notehead_duplicate_of_a_timesig_digit_is_refused(self):
        """The crop-verified shape: a `timeSig8` box and, on the SAME ink
        (IoU > 0.9, measured 0.94-0.96 on the real page), a second box the
        detector classed `noteheadWholeInSpace`. Refused, named, and the
        `timeSig*` box it duplicates is recorded."""
        log = Log()
        _cell_geometry(log)
        ts = _timesig_box(log, 0, x_c=200.0, y_c=200.0, w_c=100.0, h_c=100.0)
        dup = _notehead(log, 1, cls="noteheadWholeInSpace", x_c=202.0,
                        y_c=201.0, w_c=97.0, h_c=98.0, conf=0.267)
        log = _run(log)

        iou = NP._notehead_box_iou(
            ("timeSig8", 200.0, 200.0, 100.0, 100.0),
            ("noteheadWholeInSpace", 202.0, 201.0, 97.0, 98.0))
        self.assertGreater(iou, NP.TIMESIG_DIGIT_DUPLICATE_IOU_MIN,
                           "fixture must actually clear the floor it tests")

        v = _verdict(log, dup)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "is_a_time_signature_digit")
        ts_row = log.rows(Q.GLYPH_BOX, subject=ts)[-1]
        self.assertEqual(v.detail.get("timesig_digit_of"), ts_row.id)
        self.assertEqual(v.detail.get("timesig_digit_class"), "timeSig8")

    def test_a_real_notehead_beside_a_timesig_box_is_kept(self):
        """⚠️ THE CONTROL THAT CAN FAIL. A real notehead printed just past a
        cautionary signature — the brief's own named risk (a real head NEAR
        a meter digit). IoU ~0.25 (horizontal neighbours, same size boxes,
        well inside the brief's 0.2-0.5 range), nowhere near the 0.9 floor:
        kept."""
        log = Log()
        _cell_geometry(log)
        _timesig_box(log, 0, x_c=200.0, y_c=200.0, w_c=100.0, h_c=100.0)
        head = _notehead(log, 1, cls="noteheadBlackInSpace", x_c=260.0,
                         y_c=200.0, w_c=100.0, h_c=100.0, conf=0.8)
        log = _run(log)

        iou = NP._notehead_box_iou(
            ("timeSig8", 200.0, 200.0, 100.0, 100.0),
            ("noteheadBlackInSpace", 260.0, 200.0, 100.0, 100.0))
        self.assertLess(iou, NP.TIMESIG_DIGIT_DUPLICATE_IOU_MIN)
        self.assertGreater(iou, 0.0)

        v = _verdict(log, head)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")

    def test_a_notehead_with_no_timesig_in_the_cell_is_unchanged(self):
        """Control: no `timeSig*` box anywhere in the cell at all — the
        ordinary case for nearly every notehead in the document. Untouched
        by this rule."""
        log = Log()
        _cell_geometry(log)
        head = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=200.0,
                         y_c=200.0, conf=0.8)
        log = _run(log)

        v = _verdict(log, head)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")

    def test_a_timesig_classed_box_is_never_refused_by_this_rule(self):
        """This rule only ever condemns a NOTEHEAD-classed box; it is not
        wired onto `timeSig*`-classed glyphs at all (they are not subjects
        of `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD`, `subjects_from=Q.NOTEHEAD_
        CLASS`), so there is no verdict to read for the `timeSig8` row
        itself — asking for one returns nothing."""
        log = Log()
        _cell_geometry(log)
        ts = _timesig_box(log, 0, x_c=200.0, y_c=200.0, w_c=100.0, h_c=100.0)
        _notehead(log, 1, cls="noteheadWholeInSpace", x_c=202.0, y_c=201.0,
                 w_c=97.0, h_c=98.0, conf=0.267)
        log = _run(log)
        self.assertIsNone(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, ts))


class TestMeasurePartitionOrderingGap(unittest.TestCase):
    """ROADMAP 2.47bc: does refusing the duplicate let ROADMAP 2.47b's
    cautionary-tail rule now demote? `Q.MEASURE_PARTITION` still precedes
    `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` in `adjudicate.ORDER`
    (`tools/omr/staged/adjudicate.py`, unchanged by this round --
    `test_order_is_unchanged` below), so `structure._trailing_cell_is_
    cautionary_only` still cannot read `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD`'s own
    REFUSAL verdict. Instead it now asks `geometry.is_timesig_digit_ink`
    the identical geometric question `notehead_precision._timesig_digit_
    duplicate_refusal` asks, directly against the raw detector boxes --
    same constant, same arithmetic, two call sites, no reorder.

    `test_the_measure_partition_decision_does_not_see_this_refusal` is the
    RED->GREEN test for that connection: RED on the tree before this
    round's `structure.py` edit (`value=8, reason="read"` -- what this test
    asserted before this round, pinning the then-true finding that nothing
    connected); GREEN after (`value=7,
    reason="cautionary_tail_not_a_bar"`)."""

    PAGE, SYS, N_STAVES = 0, 0, 3

    def _barline_column(self, log, staff_sub, n_cells):
        log.observe(staff_sub, Q.BARLINE_COLUMN, n_cells,
                    reader=READERS.GEOMETRY, frame="page")

    def _build(self, log):
        """Shrunk Brahms-p0 shape (3 of 14 staves): 7 real bars, then an
        8th/final cell holding a genuine `timeSig8` plus the SAME ink boxed
        a second time as `noteheadWholeInSpace` — the exact §10c/§11c crop,
        on every staff (cross-staff quorum satisfied either way)."""
        for st_idx in range(self.N_STAVES):
            staff_sub = R.staff(self.PAGE, self.SYS, st_idx)
            self._barline_column(log, staff_sub, 8)
            for cell_idx in range(7):
                g = R.glyph(self.PAGE, self.SYS, st_idx, cell_idx, 0)
                log.observe(g, Q.GLYPH_BOX,
                           ("noteheadBlackOnLine", 0.0, 0.0, 1.0, 1.0),
                           reader=READERS.DETECTOR, frame="cell:%d" % cell_idx,
                           score=0.9, category="notehead")
            ts = R.glyph(self.PAGE, self.SYS, st_idx, 7, 0)
            log.observe(ts, Q.GLYPH_BOX,
                       ("timeSig8", 200.0, 200.0, 100.0, 100.0),
                       reader=READERS.DETECTOR, frame="cell:7", score=0.663,
                       category="timeSig")
            dup = R.glyph(self.PAGE, self.SYS, st_idx, 7, 1)
            log.observe(dup, Q.GLYPH_BOX,
                       ("noteheadWholeInSpace", 202.0, 201.0, 97.0, 98.0),
                       reader=READERS.DETECTOR, frame="cell:7", score=0.267,
                       category="notehead")
            log.observe(dup, Q.NOTEHEAD_CLASS, "noteheadWholeInSpace",
                       reader=READERS.DETECTOR, frame="cell:7", score=0.267)
            log.observe(dup, Q.GLYPH_CONF, 0.267, reader=READERS.DETECTOR,
                       frame="cell:7", score=0.267)
            log.observe(dup, Q.NOTEHEAD_STAFF_POSITION, 4.0,
                       reader=READERS.GEOMETRY, frame="cell:7")
            tail_cell = R.cell(self.PAGE, self.SYS, st_idx, 7)
            log.observe(tail_cell, Q.CELL_STAFF_SPACE, 100.0,
                       reader=READERS.GEOMETRY, frame="cell:7")
            log.observe(tail_cell, Q.CELL_BOX, [0.0, 0.0, 400.0, 400.0],
                       reader=READERS.GEOMETRY, frame="cell:7")

    def test_the_duplicate_is_refused_on_its_own_quantity(self):
        log = Log()
        self._build(log)
        log.freeze()
        adjudicate._ensure_decisions()
        for st_idx in range(self.N_STAVES):
            dup = R.glyph(self.PAGE, self.SYS, st_idx, 7, 1)
            v = adjudicate.adjudicate_one(
                log, adjudicate.REGISTRY[Q.NOTEHEAD_IS_NOT_A_NOTEHEAD], dup)
            self.assertEqual(v.outcome, Outcome.DECIDED)
            self.assertIs(v.value, True)
            self.assertEqual(v.reason, "is_a_time_signature_digit")

    def test_the_measure_partition_decision_does_not_see_this_refusal(self):
        """RED->GREEN (ROADMAP 2.47bc). RED on the pre-2.47bc tree: this
        asserted `value=8, reason="read"` because the tail cell's duplicate
        notehead box still failed `_is_signature_glyph_class` by its raw
        class alone. GREEN here: `structure._trailing_cell_is_cautionary_
        only` now also accepts a notehead-classed box whose ink duplicates
        a `timeSig*` box in the SAME staff's cell
        (`geometry.is_timesig_digit_ink`), so the cell reads as
        signature-only on every staff and the system demotes to 7."""
        log = Log()
        self._build(log)
        log.freeze()
        adjudicate._ensure_decisions()
        for st_idx in range(self.N_STAVES):
            staff_sub = R.staff(self.PAGE, self.SYS, st_idx)
            v = adjudicate.adjudicate_one(
                log, adjudicate.REGISTRY[Q.MEASURE_PARTITION], staff_sub)
            self.assertEqual(v.outcome, Outcome.DECIDED)
            self.assertEqual(v.value, 7, f"staff {st_idx}")
            self.assertEqual(v.reason, "cautionary_tail_not_a_bar")
        self.assertTrue(
            _structure._is_signature_glyph_class("timeSig8"))
        self.assertFalse(
            _structure._is_signature_glyph_class("noteheadWholeInSpace"))

    def test_a_real_notehead_beside_the_tail_digit_is_not_demoted(self):
        """⚠️ THE CONTROL THAT CAN FAIL (CLAUDE.md §6b/rule 7). Same shape as
        `_build`, but the tail cell's non-signature box is a REAL notehead
        beside the `timeSig8` (IoU ~0.3, same geometry as `notehead_
        precision`'s own `test_a_real_notehead_beside_a_timesig_box_is_
        kept`), not the same ink boxed twice. `_trailing_cell_is_
        cautionary_only` must still see a real musical event in the tail
        and leave the system at its full count -- a rule that accepted ANY
        notehead near a `timeSig*` box, not just the same ink, would pass
        the RED->GREEN test above and still be wrong."""
        log = Log()
        for st_idx in range(self.N_STAVES):
            staff_sub = R.staff(self.PAGE, self.SYS, st_idx)
            self._barline_column(log, staff_sub, 8)
            for cell_idx in range(7):
                g = R.glyph(self.PAGE, self.SYS, st_idx, cell_idx, 0)
                log.observe(g, Q.GLYPH_BOX,
                           ("noteheadBlackOnLine", 0.0, 0.0, 1.0, 1.0),
                           reader=READERS.DETECTOR,
                           frame="cell:%d" % cell_idx, score=0.9,
                           category="notehead")
            ts = R.glyph(self.PAGE, self.SYS, st_idx, 7, 0)
            log.observe(ts, Q.GLYPH_BOX,
                       ("timeSig8", 200.0, 200.0, 100.0, 100.0),
                       reader=READERS.DETECTOR, frame="cell:7", score=0.663,
                       category="timeSig")
            head = R.glyph(self.PAGE, self.SYS, st_idx, 7, 1)
            log.observe(head, Q.GLYPH_BOX,
                       ("noteheadBlackInSpace", 260.0, 200.0, 100.0, 100.0),
                       reader=READERS.DETECTOR, frame="cell:7", score=0.8,
                       category="notehead")
            log.observe(head, Q.NOTEHEAD_CLASS, "noteheadBlackInSpace",
                       reader=READERS.DETECTOR, frame="cell:7", score=0.8)
            log.observe(head, Q.GLYPH_CONF, 0.8, reader=READERS.DETECTOR,
                       frame="cell:7", score=0.8)
            log.observe(head, Q.NOTEHEAD_STAFF_POSITION, 4.0,
                       reader=READERS.GEOMETRY, frame="cell:7")
            tail_cell = R.cell(self.PAGE, self.SYS, st_idx, 7)
            log.observe(tail_cell, Q.CELL_STAFF_SPACE, 100.0,
                       reader=READERS.GEOMETRY, frame="cell:7")
            log.observe(tail_cell, Q.CELL_BOX, [0.0, 0.0, 400.0, 400.0],
                       reader=READERS.GEOMETRY, frame="cell:7")
        log.freeze()
        adjudicate._ensure_decisions()

        iou = NP._notehead_box_iou(
            ("timeSig8", 200.0, 200.0, 100.0, 100.0),
            ("noteheadBlackInSpace", 260.0, 200.0, 100.0, 100.0))
        self.assertLess(iou, NP.TIMESIG_DIGIT_DUPLICATE_IOU_MIN)
        self.assertGreater(iou, 0.0)

        for st_idx in range(self.N_STAVES):
            staff_sub = R.staff(self.PAGE, self.SYS, st_idx)
            v = adjudicate.adjudicate_one(
                log, adjudicate.REGISTRY[Q.MEASURE_PARTITION], staff_sub)
            self.assertEqual(v.outcome, Outcome.DECIDED)
            self.assertEqual(v.value, 8, f"staff {st_idx}")
            self.assertEqual(v.reason, "read")

    def test_order_is_unchanged(self):
        """`adjudicate.ORDER` is DATA (a tuple of `Q` members this test
        reads), not module source text (CLAUDE.md §6c's exemption is for
        source-text assertions, not for reading an ordering tuple) --
        confirms the brief's instruction that this round connects through
        `geometry.py`, never by moving `Q.MEASURE_PARTITION` or
        `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` in `adjudicate.ORDER`."""
        order = list(adjudicate.ORDER)
        self.assertLess(order.index(Q.MEASURE_PARTITION),
                        order.index(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD))


if __name__ == "__main__":
    unittest.main()
