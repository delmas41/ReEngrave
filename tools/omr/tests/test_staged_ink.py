"""`gather_ink`: the page's INK as the population, classification as an
attribute that may be absent.

⚠️⚠️ SEAN, 2026-09-17: *"Missing doesn't make sense to me. We can only gather
what we see. We may or may not be able to classify it correctly initially - or
at all - but ink is ink. There is nothing that should be classified as unseen -
only unclassified."* Every other measurement in GATHER starts from a DETECTION,
so until this rung the record's population was the DETECTOR'S OUTPUT and ink it
did not fire on produced no row at all -- the ABSENT/DECLINED collapse
`record.py` exists to prevent, happening to the ink itself.

⚠️ AND, 2026-09-17: *"even staff residue should go through the process and
hopefully our rules and measurements will determine at the appropriate stage
that it is just that - staff residue."* So there is NO FILTER here and the
tests below assert its absence directly: a one-pixel speck gets a row, because
a threshold at the gather site is a decision taken in the wrong stage and the
one kind that cannot be revisited.

⚠️ THE FIXTURES ARE DRAWN INK, NOT A MOCK. A component test whose input is a
hand-written list of boxes tests the arithmetic and not the reader; every case
here paints pixels into a cell image and asks the shipped function what it
finds, which is what makes `NO_MASK` and the merge behaviour testable at all.
"""

from __future__ import annotations

import os
import unittest

import numpy as np

from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q, READERS

SPACING = 20.0                      # canonical px per staff space
LINES = [100, 120, 140, 160, 180]   # five lines, 20 px apart
H, W = 400, 600


class _Det:
    """The shape `gather_detections` hands on: canonical box + class."""

    def __init__(self, name, x, y, w, h, conf=0.5, category="notehead"):
        self.smufl_name = name
        self.category = category
        self.x_canonical = x
        self.y_canonical = y
        self.width_canonical = w
        self.height_canonical = h
        self.confidence = conf
        self.x_center = x + w / 2.0
        self.y_center = y + h / 2.0


class _Cell:
    """A measure cell with a drawable staff-line-erased image."""

    def __init__(self, *, staff=0, measure=0, page=0, erased=True,
                 lines=LINES, x0=1000, y0=2000, upscale=4.0):
        self.page_index = page
        self.system_index = 0
        self.staff_index = staff
        self.measure_index = measure
        self.image = np.full((H, W), 255, np.uint8)
        # 0 = ink, 255 = paper -- `staff_line_removal`'s own convention.
        self.image_no_staff = np.full((H, W), 255, np.uint8) if erased else None
        self.staff_line_ys_canonical = list(lines)
        self.bbox_page_px = (x0, y0, x0 + int(W / upscale), y0 + int(H / upscale))
        self.upscale_factor = upscale

    def ink(self, x, y, w, h):
        self.image_no_staff[y:y + h, x:x + w] = 0
        return self


def _local():
    return {0: (0, 0), 1: (0, 1)}


def _run(cells, detections=None, *, on=True, component_rows=True):
    """⚠️ `component_rows=True` is this HELPER's default, not `gather_ink`'s.

    Every test below this helper was written to test the PER-COMPONENT
    shape (one row per piece of ink, its own frame, its own coverage) --
    which since roadmap 1.1 is what `component_rows=True` (`--ink-rows` on
    the CLI) reproduces, byte for byte, rather than what a bare call does.
    Keeping the test helper's own default at the old shape means the tests
    below assert exactly what they always asserted; the summary form (the
    pipeline's own new default) has its own tests further down, which pass
    `component_rows=False` explicitly.
    """
    log = Log()
    old = os.environ.get(G.INK_ENV)
    # ⚠️⚠️ OFF MUST BE AN EXPLICIT OFF WORD, NEVER A POP. Under a default-ON
    # flag, popping the variable IS the ON arm -- so the two arms would be
    # identical and every off-test would pass by measuring nothing. CLAUDE.md
    # records exactly this costing ten red tests on the meter flip: "three
    # harnesses expressed 'off' by POPPING the variable". This helper had it,
    # and the flip is what exposed it.
    os.environ[G.INK_ENV] = "1" if on else "0"
    try:
        G.gather_ink(log, cells, _local(), detections or {},
                     component_rows=component_rows)
    finally:
        if old is None:
            os.environ.pop(G.INK_ENV, None)
        else:
            os.environ[G.INK_ENV] = old
    return log


def _rows(log, cell=None):
    sub = cell if cell is not None else R.cell(0, 0, 0, 0)
    out = []
    for row in log.all_rows():
        if getattr(row, "quantity", None) != Q.INK:
            continue
        if row.subject.at(R.Kind.CELL) == sub:
            out.append(row)
    return out


class TestTheFlagIsOnByDefault(unittest.TestCase):
    """⚠️ A GATHER change adds rows to EVERY record the pipeline writes, which
    is the widest blast radius a change here has. `test_flag_default_direction`
    derives the flag list and checks the OFF-test DIRECTION; what it cannot
    check is what the default actually PRODUCES, which is this class's job.

    ⚠️⚠️ FLIPPED 2026-09-17 ON SEAN'S CALL, default OFF -> ON. These two tests
    went red ON SUCCESS, which is the shape CLAUDE.md records when the last
    stub closed: eight assertions failed because the thing they asserted had
    been achieved. They are REWRITTEN to the new contract rather than deleted,
    and each still exercises the mechanism in BOTH directions -- a test that
    only pins a default is a property of the build's progress, not of the
    code."""

    def setUp(self):
        self._old = os.environ.pop(G.INK_ENV, None)

    def tearDown(self):
        if self._old is not None:
            os.environ[G.INK_ENV] = self._old

    def test_the_default_writes_rows(self):
        c = _Cell().ink(300, 130, 24, 24)
        self.assertTrue(_rows(_run([c])),
                        "the default must now GATHER the ink, not skip it")

    def test_turning_it_off_is_still_a_complete_no_op(self):
        """⚠️ The negative control, and it is the one that matters on a flip.

        A default-ON flag whose OFF branch has rotted is indistinguishable
        from one that has no OFF branch, and the escape hatch Sean is owed is
        exactly that branch."""
        c = _Cell().ink(300, 130, 24, 24)
        log = _run([c], on=False)
        self.assertEqual(log.all_rows(), (),
                         "flag-off must be a no-op, not a quiet row")

    def test_a_deny_list_leaves_a_typo_ON(self):
        """⚠️ THE DIRECTION REVERSED WITH THE DEFAULT, and that is the whole
        point of the rewrite: under an allow-list an empty value or a typo
        would silently restore the pre-flip behaviour."""
        for word in ("", "0", "off", "OFF", "false", "no", " off "):
            os.environ[G.INK_ENV] = word
            self.assertFalse(G._ink_enabled(), f"{word!r} must turn it off")
        for word in ("1", "true", "YES", " on ", "yess", "ON!", "1 1"):
            os.environ[G.INK_ENV] = word
            self.assertTrue(G._ink_enabled(),
                            f"{word!r} is not an off word and must leave it ON")


class TestOneRowPerPieceOfInk(unittest.TestCase):

    def test_two_separate_marks_are_two_rows(self):
        c = _Cell().ink(100, 130, 24, 24).ink(300, 130, 24, 24)
        rows = _rows(_run([c]))
        self.assertEqual(len(rows), 2)

    def test_a_blank_cell_abstains_rather_than_saying_nothing(self):
        """⚠️ `NO_INK` is a MEASUREMENT -- the reader ran and the cell is
        empty. A cell with no row at all would be indistinguishable from a
        cell the rung never reached, which is the distinction this whole
        quantity exists to keep."""
        log = _run([_Cell()])
        refusals = [r for r in log.all_rows()
                    if getattr(r, "quantity", None) == Q.INK]
        self.assertEqual(len(refusals), 1)
        self.assertEqual(refusals[0].reason, ABSTAIN.NO_INK)

    def test_a_cell_with_no_erased_image_refuses_by_name(self):
        """⚠️ `line_detection` SILENTLY falls back to `cell.image` in this
        situation, which makes a whole-rung failure look like a thin page.
        This reader refuses, so the two can be told apart."""
        c = _Cell().ink(300, 130, 24, 24)
        c.image_no_staff = None          # the erased variant never got built
        log = _run([c])
        rows = [r for r in log.all_rows()
                if getattr(r, "quantity", None) == Q.INK]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].reason, ABSTAIN.NO_MASK)

    def test_the_reader_is_named_and_is_not_the_detector(self):
        c = _Cell().ink(300, 130, 24, 24)
        self.assertEqual({r.reader for r in _rows(_run([c]))},
                         {READERS.CV_INK})


class TestNothingIsFiltered(unittest.TestCase):
    """⚠️⚠️ SEAN'S SECOND CORRECTION, ASSERTED DIRECTLY. Staff residue and
    speckle are not false rows -- they are correctly gathered ink that a LATER
    stage should name. A size gate here would destroy the evidence that rule
    needs before the rule exists."""

    def test_a_single_pixel_gets_a_row(self):
        c = _Cell().ink(300, 130, 1, 1)
        rows = _rows(_run([c]))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail["ink_area_px"], 1)

    def test_a_staff_line_remnant_gets_a_row_and_is_not_marked_bad(self):
        """A 20-space-wide, 2px-tall streak along a line's own row. It is
        residue; the row says only how wide, how tall and how filled it is."""
        c = _Cell().ink(20, 120, 400, 2)
        rows = _rows(_run([c]))
        self.assertEqual(len(rows), 1)
        d = rows[0].detail
        self.assertGreater(d["width_spaces"], 15.0)
        self.assertLess(d["height_spaces"], 0.2)
        self.assertNotIn("is_residue", d)
        self.assertNotIn("keep", d)

    def test_a_speck_and_a_notehead_are_reported_the_same_way(self):
        c = _Cell().ink(50, 130, 1, 1).ink(300, 130, 24, 16)
        rows = _rows(_run([c]))
        self.assertEqual(len(rows), 2)
        self.assertEqual({tuple(sorted(r.detail)) for r in rows}.__len__(), 1,
                         "every row carries the same fields")


class TestTheShapeAndTheFrame(unittest.TestCase):

    def test_the_box_is_reported_in_BOTH_frames(self):
        """⚠️ THE PAGE FRAME IS THE POINT. A canonical x is measured inside
        one cell rescaled so the staff span is constant, so two staves' values
        are not the same quantity -- the fault that made `Q.ONSET_COLUMN`
        report 1,062 columns of nothing. The canonical box is kept beside it
        for cell-local consumers."""
        c = _Cell(x0=1000, y0=2000, upscale=4.0).ink(300, 130, 24, 16)
        d = _rows(_run([c]))[0].detail
        self.assertEqual(d["ink_bbox_canonical"], [300, 130, 324, 146])
        self.assertEqual(d["bbox_page_px"],
                         [1000 + 300 / 4.0, 2000 + 130 / 4.0,
                          1000 + 324 / 4.0, 2000 + 146 / 4.0])
        self.assertAlmostEqual(d["x_center_page"], 1000 + 312 / 4.0)

    def test_a_cell_with_no_page_frame_DECLINES_it(self):
        """⚠️ Declined, never defaulted to the cell frame: a component whose
        page position is unknown and one measured at page x 1075 are different
        facts, and only the second may reach a cross-staff consumer."""
        c = _Cell().ink(300, 130, 24, 16)
        c.upscale_factor = None
        d = _rows(_run([c]))[0].detail
        self.assertNotIn("bbox_page_px", d)
        self.assertIn("frame_note", d)

    def test_the_unit_is_the_CELLS_own_staff_space(self):
        """⚠️ NOT the nominal `CANONICAL_STAFF_SPAN_PX / 4`.
        `_upscale_to_canonical` scales a too-wide cell by WIDTH, so on one
        engraved fixture 184 of 368 cells read 100 px per space and the other
        184 read 38.5-56. A fixture at the nominal could not tell the two
        apart, so this one is deliberately at 20."""
        c = _Cell().ink(300, 130, 40, 20)
        d = _rows(_run([c]))[0].detail
        self.assertAlmostEqual(d["cell_staff_space_px"], SPACING)
        self.assertAlmostEqual(d["width_spaces"], 2.0)
        self.assertAlmostEqual(d["height_spaces"], 1.0)

    def test_fill_separates_a_solid_mark_from_an_outline(self):
        solid = _Cell().ink(300, 130, 40, 40)
        ring = _Cell(measure=1)
        ring.ink(300, 130, 40, 4).ink(300, 166, 40, 4)
        ring.ink(300, 130, 4, 40).ink(336, 130, 4, 40)
        self.assertAlmostEqual(_rows(_run([solid]))[0].detail["ink_fill"], 1.0)
        rows = _rows(_run([ring]), R.cell(0, 0, 0, 1))
        self.assertLess(rows[0].detail["ink_fill"], 0.5)


class TestClassificationIsAnAttribute(unittest.TestCase):

    def test_a_detection_over_the_ink_is_recorded_as_coverage(self):
        c = _Cell().ink(300, 130, 24, 16)
        dets = {R.cell(0, 0, 0, 0).to_key():
                [_Det("noteheadBlackInSpace", 298, 128, 28, 20)]}
        d = _rows(_run([c], dets))[0].detail
        self.assertEqual(d["ink_detector_coverage"], 1.0)
        self.assertEqual(d["ink_explained_by"], ["noteheadBlackInSpace"])

    def test_ink_no_detection_reaches_is_a_row_with_coverage_zero(self):
        """⚠️ THE CASE THE WHOLE LAYER EXISTS FOR. It is not an error state
        and it is not filtered; it is a row whose classification is absent."""
        c = _Cell().ink(300, 130, 24, 16).ink(100, 130, 24, 16)
        dets = {R.cell(0, 0, 0, 0).to_key():
                [_Det("noteheadBlackInSpace", 298, 128, 28, 20)]}
        rows = sorted(_rows(_run([c], dets)),
                      key=lambda r: r.detail["ink_bbox_canonical"][0])
        self.assertEqual(rows[0].detail["ink_detector_coverage"], 0.0)
        self.assertEqual(rows[0].detail["ink_explained_by"], [])
        self.assertEqual(rows[1].detail["ink_detector_coverage"], 1.0)

    def test_a_SPAN_detection_explains_nothing(self):
        """⚠️⚠️ THE RULE WITHOUT WHICH THE LAYER IS VACUOUS, AND IT WAS
        MEASURED BEFORE IT WAS WRITTEN. A `staff` box is 26.6 staff spaces
        wide and a `slur` box is the rectangle its arc travels through -- both
        mostly paper. On Litolff Beethoven 5 p.62 cell 6, with spans counted,
        ALL SEVENTEEN staves' printed `3/4` read as fully covered, by the
        `staff` box. The cut is IMPORTED from
        `direction_text.BandConfig.max_blank_width_spaces`, the same constant
        that reader uses to decide what it may blank."""
        c = _Cell().ink(300, 130, 24, 16)
        span = _Det("staff", 0, 0, int(26.0 * SPACING), 200, category="staff")
        dets = {R.cell(0, 0, 0, 0).to_key(): [span]}
        d = _rows(_run([c], dets))[0].detail
        self.assertEqual(d["ink_detector_coverage"], 0.0)
        self.assertEqual(d["ink_explained_by"], [])

    def test_the_span_cut_is_the_direction_readers_own_constant(self):
        from tools.omr.direction_text import DEFAULT_BAND_CONFIG
        import inspect
        src = inspect.getsource(G._explaining_detections)
        self.assertIn("max_blank_width_spaces", src)
        self.assertNotIn("4.0", src.split('"""')[-1],
                         "the constant must be imported, never restated")
        # and it is still the value the measurement was taken at
        self.assertEqual(DEFAULT_BAND_CONFIG.max_blank_width_spaces, 4.0)

    def test_two_overlapping_detections_do_not_over_count(self):
        """⚠️ The UNION, not a sum. On the staged path one notehead survives
        NMS as three rows at IoU 0.91-0.96, which `gather_detections` records
        and does not fix -- summed, they would report coverage above 1.0."""
        c = _Cell().ink(300, 130, 40, 20)
        dets = {R.cell(0, 0, 0, 0).to_key(): [
            _Det("noteheadBlackInSpace", 300, 130, 40, 20),
            _Det("noteheadHalfInSpace", 298, 128, 44, 24)]}
        d = _rows(_run([c], dets))[0].detail
        self.assertLessEqual(d["ink_detector_coverage"], 1.0)
        self.assertEqual(d["ink_detector_coverage"], 1.0)


class TestTheMergeIsReportedRatherThanRepaired(unittest.TestCase):
    """⚠️ A COMPONENT IS A PIECE OF INK, NOT A MARK. Print bleeds; a
    staff-line remnant bridges two glyphs. Measured over 221 cells of Litolff
    Beethoven 5 p.62 the median cell yields FOUR components and the largest
    holds a median 46% of the cell's remaining ink. The row says so."""

    def test_a_bridge_makes_two_marks_one_row_and_the_row_admits_it(self):
        sep = _Cell().ink(100, 130, 24, 24).ink(300, 130, 24, 24)
        sep_rows = _rows(_run([sep]))
        self.assertEqual(len(sep_rows), 2)
        # ⚠️ ASSERTED ON THE SEPARATED CELL TOO, and a mutation battery is why:
        # pinning `ink_n_components` only on the merged cell is vacuous, because
        # there the true value IS 1 and `= 1` is an equivalent mutant. The
        # counter is only worth anything if it can say TWO.
        self.assertEqual({r.detail["ink_n_components"] for r in sep_rows}, {2})

        merged = _Cell(measure=1)
        merged.ink(100, 130, 24, 24).ink(300, 130, 24, 24)
        merged.ink(100, 140, 224, 2)          # the remnant that bridges them
        rows = _rows(_run([merged]), R.cell(0, 0, 0, 1))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail["ink_n_components"], 1)
        self.assertEqual(rows[0].detail["ink_share_of_cell"], 1.0)

    def test_share_of_cell_ink_is_per_row_and_sums_to_one(self):
        c = _Cell().ink(100, 130, 20, 20).ink(300, 130, 20, 20)
        rows = _rows(_run([c]))
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(
            sum(r.detail["ink_share_of_cell"] for r in rows), 1.0, places=3)


class TestTheKeySpaceCannotCollide(unittest.TestCase):

    def test_ink_indices_sit_past_the_detector_and_the_cv_rung(self):
        """⚠️ A collision would not raise. It would silently merge a component
        row and a detection row into ONE subject, which is the 'two rows from
        one reader are ONE signal' mistake made by accident."""
        self.assertGreater(G._INK_GLYPH_BASE, G._CV_GLYPH_BASE)
        c = _Cell().ink(300, 130, 24, 16)
        row = _rows(_run([c]))[0]
        self.assertGreaterEqual(row.subject.glyph, G._INK_GLYPH_BASE)


class TestTheReaderDeclaresItsOwnCorrelation(unittest.TestCase):

    def test_CV_INK_names_the_crop_it_shares_with_CV_LINES(self):
        """⚠️ The two rungs read the SAME `cell.image_no_staff`, so a stem
        reported by both is ONE reading wearing two names. `CV_HAIRPINS` is
        the opposite case -- different images, real independence -- and the
        vocabulary must not let the two be confused."""
        import inspect
        src = inspect.getsource(R.READERS)
        i = src.index("CV_INK")
        doc = src[max(0, i - 1200):i]
        self.assertIn("image_no_staff", doc)
        self.assertIn("CV_LINES", doc)

    def test_the_gatherer_reads_the_erased_image_and_says_why(self):
        import inspect
        src = inspect.getsource(G._ink_components)
        self.assertIn("image_no_staff", src)
        self.assertIn("cell.image", src)


class TestItRunsInsideTheRealGather(unittest.TestCase):

    def test_gather_calls_it_after_detection(self):
        """⚠️ The edge is real: a component's row records how much of it the
        DETECTIONS account for, so it cannot run before they exist. Asserted
        on the source because no behavioural test on a synthetic page can
        distinguish the two orders."""
        import inspect
        src = inspect.getsource(G.gather)
        self.assertIn("gather_ink(", src)
        self.assertLess(src.index("detections = gather_detections"),
                        src.index("gather_ink("))


# ─────────────────────────────────────────────────────────────────────────────
# Roadmap 1.1 -- the SUMMARY form is the PIPELINE'S default, one row per CELL
# ─────────────────────────────────────────────────────────────────────────────

class TestTheSummaryFormIsTheDefault(unittest.TestCase):
    """`gather_ink`'s own default (no `component_rows` kwarg at all) is the
    aggregate. This is the ONE class in this file calling `G.gather_ink`
    directly rather than through `_run`, precisely to exercise the real
    default rather than the test helper's."""

    def test_a_bare_call_produces_one_row_per_cell(self):
        c = _Cell().ink(100, 130, 20, 20).ink(300, 130, 40, 30)
        log = Log()
        G.gather_ink(log, [c], _local(), {})  # no component_rows kwarg
        rows = _rows(log)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail["ink_n_components"], 2)

    def test_it_is_the_same_row_component_rows_false_gives(self):
        c = _Cell().ink(100, 130, 20, 20).ink(300, 130, 40, 30)
        bare = Log()
        G.gather_ink(bare, [c], _local(), {})
        explicit = _run([c], component_rows=False)
        self.assertEqual(_rows(bare)[0].detail, _rows(explicit)[0].detail)


class TestSummaryAggregatesMatchTheComponentsExactly(unittest.TestCase):
    """The cross-check the design rests on: every number in the one summary
    row is derivable from the many component rows `--ink-rows` still gives,
    computed independently here rather than by re-running `gather_ink`'s own
    aggregation code against itself."""

    def _both(self, cell, detections=None):
        summary = _rows(_run([cell], detections, component_rows=False))
        components = _rows(_run([cell], detections, component_rows=True))
        return summary, components

    def test_n_components_and_total_area(self):
        c = _Cell().ink(100, 130, 20, 20).ink(300, 130, 40, 30) \
                    .ink(450, 150, 10, 10)
        summary, components = self._both(c)
        self.assertEqual(len(summary), 1)
        self.assertEqual(len(components), 3)
        self.assertEqual(summary[0].detail["ink_n_components"], 3)
        self.assertEqual(summary[0].detail["ink_total_area_px"],
                         sum(r.detail["ink_area_px"] for r in components))

    def test_largest_share_is_the_max_of_the_per_component_shares(self):
        c = _Cell().ink(100, 130, 20, 20).ink(300, 130, 40, 30)
        summary, components = self._both(c)
        self.assertAlmostEqual(
            summary[0].detail["ink_largest_share"],
            max(r.detail["ink_share_of_cell"] for r in components))

    def test_explained_by_union_and_coverage_max(self):
        c = _Cell().ink(100, 130, 20, 20).ink(300, 130, 24, 16)
        dets = {R.cell(0, 0, 0, 0).to_key(): [
            _Det("noteheadBlackInSpace", 300, 130, 24, 16)]}
        summary, components = self._both(c, dets)
        union = set()
        for r in components:
            union.update(r.detail["ink_explained_by"])
        self.assertEqual(set(summary[0].detail["ink_explained_by_union"]),
                         union)
        self.assertAlmostEqual(
            summary[0].detail["ink_detector_coverage_max"],
            max(r.detail["ink_detector_coverage"] for r in components))

    def test_abstentions_are_identical_either_way(self):
        """⚠️ NO_MASK / NO_INK are already per-cell -- nothing to aggregate,
        and the schema change must not touch them."""
        no_mask = _Cell(erased=False)
        blank = _Cell()
        for on_flag in (True, False):
            with self.subTest(component_rows=on_flag):
                for cell, reason in ((no_mask, ABSTAIN.NO_MASK),
                                     (blank, ABSTAIN.NO_INK)):
                    log = _run([cell], component_rows=on_flag)
                    abstentions = [r for r in log.all_rows()
                                  if r.quantity == Q.INK
                                  and hasattr(r, "reason")]
                    self.assertEqual(len(abstentions), 1)
                    self.assertEqual(abstentions[0].reason, reason)


class TestTraceReadsBothFormsAlike(unittest.TestCase):
    """`trace._ink_cells_and_components` must report the identical answer
    whether it is handed the summary form or the pre-1.1 component form --
    the whole reason `trace.py`'s two record consumers needed a form-agnostic
    read rather than a shape check. A synthetic observation list is used
    directly (not a full staged record) so this stays a unit test of the
    helper rather than a rebuild of the pipeline."""

    def test_one_row_per_cell_and_many_rows_per_cell_agree(self):
        from tools.omr.staged.trace import _ink_cells_and_components

        summary_form = [
            {"subject": "cell/0/0/0/0", "detail": {"ink_n_components": 3}},
            {"subject": "cell/0/0/1/0", "detail": {"ink_n_components": 1}},
        ]
        component_form = [
            {"subject": "glyph/0/0/0/0/200000",
             "detail": {"ink_n_components": 3}},
            {"subject": "glyph/0/0/0/0/200001",
             "detail": {"ink_n_components": 3}},
            {"subject": "glyph/0/0/0/0/200002",
             "detail": {"ink_n_components": 3}},
            {"subject": "glyph/0/0/1/0/200000",
             "detail": {"ink_n_components": 1}},
        ]
        for label, rows in (("summary", summary_form),
                            ("component", component_form)):
            with self.subTest(form=label):
                cells, total = _ink_cells_and_components(rows)
                self.assertEqual(cells, {"cell/0/0/0/0", "cell/0/0/1/0"})
                self.assertEqual(total, 4)


if __name__ == "__main__":
    unittest.main()
