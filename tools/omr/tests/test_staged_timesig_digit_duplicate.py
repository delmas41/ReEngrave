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

⚠️ `test_the_measure_partition_decision_does_not_see_this_refusal`
documents a brief-mandated finding rather than a fix: `Q.MEASURE_PARTITION`
runs BEFORE `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` in `adjudicate.ORDER`, and
`structure._trailing_cell_is_cautionary_only` reads `Q.GLYPH_BOX`'s own raw
DETECTOR class directly, never any refusal verdict -- so a duplicate box
refused here by its CLASS alone (still `noteheadWholeInSpace` on the
record, only REFUSED, never relabelled or removed) still fails `_is_
signature_glyph_class` and still blocks ROADMAP 2.47b's cautionary-tail
demotion on Brahms p0. CLAUDE.md rule 6 (connect, never guess) and the
brief both say to report this rather than reorder `ORDER` or change
`structure.py` to read a NOTEHEAD-family verdict from a STRUCTURE-stage
decision that must run before identity exists.

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
    """Brief point 2: does refusing the duplicate here let ROADMAP 2.47b's
    cautionary-tail rule now demote? `Q.MEASURE_PARTITION` precedes
    `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` in `adjudicate.ORDER`
    (`tools/omr/staged/adjudicate.py`), and `_trailing_cell_is_cautionary_
    only` reads each glyph's raw DETECTOR class, never a refusal verdict —
    so NEITHER of the brief's two conditions for a safe reorder holds. This
    test pins that finding rather than attempting the reorder (CLAUDE.md
    rule 6: connect, never guess past what the record actually wires)."""

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
        """Documents the gap: `measure_partition` still reads the tail cell
        as MIXED (a `noteheadWholeInSpace`-classed row is present, by its
        raw class, regardless of this decision's own later refusal) and
        does NOT demote — `value` stays at `n_cells` (8), `reason="read"`,
        matching FINDINGS §10c/§11c's own "Brahms p0/sys0 stays 8" result.
        A control that CAN fail: if `structure.py` were changed to read the
        refusal, this assertion would need updating to `value=7` — it is
        pinned here so that future change is visible, not silent."""
        log = Log()
        self._build(log)
        log.freeze()
        adjudicate._ensure_decisions()
        for st_idx in range(self.N_STAVES):
            staff_sub = R.staff(self.PAGE, self.SYS, st_idx)
            v = adjudicate.adjudicate_one(
                log, adjudicate.REGISTRY[Q.MEASURE_PARTITION], staff_sub)
            self.assertEqual(v.outcome, Outcome.DECIDED)
            self.assertEqual(v.value, 8, f"staff {st_idx}")
            self.assertEqual(v.reason, "read")
        self.assertTrue(
            _structure._is_signature_glyph_class("timeSig8"))
        self.assertFalse(
            _structure._is_signature_glyph_class("noteheadWholeInSpace"))


if __name__ == "__main__":
    unittest.main()
