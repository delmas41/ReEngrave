"""`Q.VERTICAL_RUN`: the vertical-run population, ACCEPTED AND REFUSED.

⚠️⚠️ WHY THE QUANTITY EXISTS, because it decides what these tests must pin.
Sean asked whether the stages hold the information needed to tell one kind of
vertical line from another. Measured against the tree the answer was NO, for
two reasons:

  1. `detect_stems` finds every vertical candidate, applies SIX filters and
     RETURNS ONLY THE SURVIVORS -- so a candidate the pipeline found and
     discarded left no row at all, and the population arrived at every stage
     already named `stem`. Naming and filtering are fused in GATHER, against
     its own charter that it *decides nothing*
     (`docs/breakthrough-2026-09-18-the-unit-of-enquiry.md`).
  2. Sean's barline test -- *a barline's two ends sit ON the outer staff lines;
     a stem's do not* -- needs the run's endpoints and the staff lines in ONE
     coordinate system, and `Q.STEM` is CELL canonical with no page fields at
     all while `Q.STAFF_LINES` is PAGE px.

So the tests that matter are: the survivors DO NOT MOVE (§1), the refused
population arrives WITH ITS REASON (§2), the page frame is there and is
DECLINED rather than defaulted when it cannot be had (§3), and the reason
vocabulary has not drifted from the census that measured it (§4).

⚠️ THE FIXTURES ARE DRAWN INK, NOT A MOCK, for `test_staged_ink`'s stated
reason: a test whose input is a hand-written list of boxes tests the arithmetic
and not the reader, and every filter here is a fact about a component the
morphological opening produced.
"""

from __future__ import annotations

import os
import pathlib
import unittest

import numpy as np

from tools.omr import line_detection as LD
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, CLAIM, CLAIMS, Log, Q, READERS

SPACING = 20.0                      # canonical px per staff space
LINES = [100, 120, 140, 160, 180]   # five lines, 20 px apart
H, W = 400, 600
EDGE = max(int(round(SPACING * 0.8)), 12)


class _Cell:
    """A measure cell with a drawable staff-line-erased image."""

    def __init__(self, *, staff=0, measure=0, page=0, erased=True,
                 lines=LINES, x0=1000, y0=2000, upscale=4.0,
                 page_box=True):
        self.page_index = page
        self.system_index = 0
        self.staff_index = staff
        self.measure_index = measure
        self.image = np.full((H, W), 255, np.uint8)
        # 0 = ink, 255 = paper -- `staff_line_removal`'s own convention.
        self.image_no_staff = np.full((H, W), 255, np.uint8) if erased else None
        self.staff_line_ys_canonical = list(lines)
        if page_box:
            self.bbox_page_px = (x0, y0,
                                 x0 + int(W / upscale), y0 + int(H / upscale))
            self.upscale_factor = upscale
        else:
            self.bbox_page_px = None
            self.upscale_factor = None

    @property
    def width(self) -> int:
        return self.image.shape[1]

    @property
    def height(self) -> int:
        return self.image.shape[0]

    def ink(self, x, y, w, h):
        """Paint a filled rectangle of ink into the erased raster."""
        self.image_no_staff[y:y + h, x:x + w] = 0
        self.image[y:y + h, x:x + w] = 0
        return self


def _local():
    return {0: (0, 0), 1: (0, 1)}


def _run(cells, *, on=True):
    """`gather_cv_lines` with the flag explicitly ON or explicitly OFF.

    ⚠️⚠️ OFF IS AN EXPLICIT OFF VALUE, NEVER A POP -- the hazard CLAUDE.md
    records costing ten red tests on the meter flip ("three harnesses expressed
    'off' by POPPING the variable"). Under a default-OFF flag a pop happens to
    be the OFF arm today, which is exactly what makes writing it that way
    dangerous: the day the default flips, both arms become the ON arm and every
    off-test starts passing by measuring nothing.
    """
    log = Log()
    old = os.environ.get(G.VERTICAL_RUNS_ENV)
    os.environ[G.VERTICAL_RUNS_ENV] = "1" if on else "0"
    try:
        G.gather_cv_lines(log, cells, _local())
    finally:
        if old is None:
            os.environ.pop(G.VERTICAL_RUNS_ENV, None)
        else:
            os.environ[G.VERTICAL_RUNS_ENV] = old
    return log


def _rows(log, quantity=Q.VERTICAL_RUN, cell=None):
    sub = cell if cell is not None else R.cell(0, 0, 0, 0)
    return [row for row in log.all_rows()
            if getattr(row, "quantity", None) == quantity
            and row.subject.at(R.Kind.CELL) == sub]


def _outcomes(log):
    return sorted(r.detail["run_outcome"] for r in _rows(log)
                  if getattr(r, "value", None) is not None)


# a stem-shaped run: 4 px wide (0.2 spaces), 80 px tall (4.0 spaces), clear of
# both cell edges. Every filter passes it.
def _stemmy(cell, x=200, y=110, w=4, h=80):
    return cell.ink(x, y, w, h)


# ─────────────────────────────────────────────────────────────────────────────
# §1 THE SURVIVORS DO NOT MOVE — the hard safety requirement
# ─────────────────────────────────────────────────────────────────────────────


class TestDetectStemsReturnsExactlyWhatItReturned(unittest.TestCase):
    """⚠️⚠️ THE LOAD-BEARING CLASS. `line_detection.py` is on the path every
    stem arm in this repo proves faithful before it reports a delta (1,920 =
    1,920 strokes on Litolff, 2,305 = 2,305 on Breitkopf). If `detect_stems`'
    return value moves, those controls break and it looks like THEIR bug.

    So the candidate population leaves through an append-only out-parameter,
    and these tests assert the return value is byte-identical with the
    parameter supplied and withheld -- on ink that exercises every branch,
    which is what stops the assertion being vacuous."""

    def _busy(self):
        """One cell exercising ALL SEVEN outcomes at once."""
        c = _Cell()
        _stemmy(c)                                   # accepted
        c.ink(240, 110, 4, 36)                       # h=1.8 spaces -> SHORT
        c.ink(280, 20, 4, 360)                        # h=18 spaces  -> TALL
        c.ink(320, 110, 30, 80)                      # w=1.5 spaces -> WIDE
        c.ink(2, 110, 4, 80)                         # at the left edge
        c.ink(380, 110, 40, 60)                      # 2.0 spaces -> WIDE
        c.ink(440, 110, 4, 60)                       # \\ a PAIR: two strokes
        c.ink(452, 110, 4, 60)                       # /  0.6 spaces apart
        return c

    def test_the_return_value_is_identical_with_and_without_the_out_param(self):
        c = self._busy()
        without = LD.detect_stems(c)
        got = []
        with_out = LD.detect_stems(c, candidates_out=got)
        self.assertEqual(
            [(d.x_canonical, d.y_canonical, d.width_canonical,
              d.height_canonical, d.smufl_name, d.category, d.confidence)
             for d in without],
            [(d.x_canonical, d.y_canonical, d.width_canonical,
              d.height_canonical, d.smufl_name, d.category, d.confidence)
             for d in with_out])
        # ⚠️ THE POSITIVE CONTROL: the fixture has to be busy enough that the
        # equality could have failed. A cell with one stem in it would pass
        # this test under any mutation of the recording code at all.
        self.assertGreater(len(got), len(with_out),
                           "fixture exercises no rejection at all")

    def test_detect_lines_forwards_it_and_its_stems_do_not_move(self):
        c = self._busy()
        plain = LD.detect_lines(c)
        got = []
        forwarded = LD.detect_lines(c, candidates_out=got)
        self.assertEqual([(d.x_canonical, d.height_canonical)
                          for d in plain["stems"]],
                         [(d.x_canonical, d.height_canonical)
                          for d in forwarded["stems"]])
        self.assertEqual(len(plain["beams"]), len(forwarded["beams"]))
        self.assertTrue(got)

    def test_the_gather_rung_writes_the_same_stem_rows_either_way(self):
        """⚠️ THE ARM THAT MATTERS TO THE SHARED RECORDS, in miniature. The
        real assertion is `vertical_run_arm.py` reproducing 1,920 and 2,305
        strokes over the two committed gathers; this is the unit form of it,
        and it is here so the property cannot regress without a red test on a
        machine with no weights and no `library/`."""
        off = _run([self._busy()], on=False)
        on = _run([self._busy()], on=True)
        # ⚠️ COMPARED THROUGH `to_json`, which serialises an OBSERVATION and an
        # ABSTENTION alike. Reading `.value` off both was the first draft and
        # it crashed on this very fixture, where the beam family ABSTAINS -- a
        # projection that cannot express half the rows would have compared the
        # observations and silently skipped the abstentions.
        # ⚠️⚠️ AND THE ROW `id` IS EXCLUDED, WHICH IS A REAL LIMIT AND NOT A
        # CONVENIENCE. Ids are a running counter over the whole `Log`, so ANY
        # added row shifts every later one -- `Q.INK` has the same property.
        # The contract this quantity can keep is therefore precise: FLAG-OFF
        # is byte-identical to a tree without it (asserted in
        # `TestFlagOffIsAbsentRatherThanQuiet` and against both shared records
        # by the arm), and FLAG-ON leaves every `Q.STEM` row's SUBJECT, VALUE,
        # DETAIL, READER and FRAME untouched while renumbering it. Claiming
        # byte-identity under the flag would be false, so it is not claimed.
        def strip(rows):
            out = []
            for r in rows:
                d = dict(r.to_json())
                d.pop("id", None)
                out.append(d)
            return out

        for quantity in (Q.STEM, Q.BEAM_STROKE):
            self.assertEqual(strip(_rows(off, quantity)),
                             strip(_rows(on, quantity)), quantity)
        # positive control on the projection: it is not empty for either, and
        # the ids really did move -- so `strip` is doing something
        self.assertTrue(_rows(off, Q.STEM))
        self.assertTrue(_rows(off, Q.BEAM_STROKE))
        self.assertNotEqual([r.to_json()["id"] for r in _rows(off, Q.STEM)],
                            [r.to_json()["id"] for r in _rows(on, Q.STEM)])
        # positive control: the ON arm really did add something
        self.assertEqual(_rows(off, Q.VERTICAL_RUN), [])
        self.assertTrue(_rows(on, Q.VERTICAL_RUN))


class TestFlagOffIsAbsentRatherThanQuiet(unittest.TestCase):
    """Off means the rows are ABSENT -- `OMR_INFER`'s discipline applied to a
    gather change, so a flag-off record is byte-identical to a tree without
    this quantity. An abstention would NOT be that: it is a row."""

    def test_off_writes_no_row_at_all_not_even_an_abstention(self):
        log = _run([_stemmy(_Cell())], on=False)
        self.assertEqual(
            [r for r in log.all_rows()
             if getattr(r, "quantity", None) == Q.VERTICAL_RUN], [])

    def test_the_on_test_is_an_allow_list(self):
        """Default OFF, so a typo must leave it OFF."""
        old = os.environ.get(G.VERTICAL_RUNS_ENV)
        try:
            for word, want in (("1", True), ("true", True), ("yes", True),
                               ("on", True), ("ON", True),
                               ("0", False), ("", False), ("yess", False),
                               ("off", False), ("no", False)):
                os.environ[G.VERTICAL_RUNS_ENV] = word
                self.assertIs(G.vertical_runs_enabled(), want, word)
            os.environ.pop(G.VERTICAL_RUNS_ENV, None)
            self.assertFalse(G.vertical_runs_enabled(), "default must be OFF")
        finally:
            if old is None:
                os.environ.pop(G.VERTICAL_RUNS_ENV, None)
            else:
                os.environ[G.VERTICAL_RUNS_ENV] = old


# ─────────────────────────────────────────────────────────────────────────────
# §2 THE REFUSED POPULATION ARRIVES, WITH ITS REASON
# ─────────────────────────────────────────────────────────────────────────────


class TestEveryFilterIsNamed(unittest.TestCase):
    """⚠️ ONE TEST PER FILTER, EACH ON INK THAT TRIPS ONLY THAT FILTER. A
    single fixture asserting "seven outcomes appear" would pass with any two
    of the reasons swapped, which is the mutation these tests exist to catch.
    """

    def _one(self, cell):
        got = []
        LD.detect_stems(cell, candidates_out=got)
        # exactly one component was drawn, so there is exactly one candidate
        self.assertEqual(len(got), 1, [c.outcome for c in got])
        return got[0]

    def test_a_stem_shaped_run_is_accepted(self):
        self.assertEqual(self._one(_stemmy(_Cell())).outcome, LD.RUN_ACCEPTED)

    def test_too_short(self):
        """⚠️ THE WINDOW IS NARROWER THAN IT LOOKS, and the fixture had to be
        measured rather than guessed: the opening kernel is
        `min_height_lines * STEM_KERNEL_MARGIN` = 1.6 spaces, so anything
        under 32 px is ERASED and produces no component at all. `too SHORT`
        is reachable only in the 32-40 px band between the kernel and the
        floor -- 1.6 to 2.0 staff spaces. A 20 px run does not test this
        filter; it tests the kernel, and yields nothing to test."""
        c = _Cell().ink(200, 110, 4, 36)      # 1.8 spaces: past the kernel,
        self.assertEqual(self._one(c).outcome, LD.RUN_TOO_SHORT)   # under 2.0

    def test_a_run_under_the_kernel_height_yields_no_candidate_at_all(self):
        """⚠️⚠️ AND THAT IS A LIMIT OF THIS QUANTITY, NAMED RATHER THAN HIDDEN.
        The population is *every component the OPENING produced*, and the
        opening is itself a filter -- ink shorter than 1.6 staff spaces never
        becomes a candidate, so it gets no row here either. This quantity
        widens the population from `Q.STEM`'s survivors to the opening's
        output; it does NOT widen it to the ink. `Q.INK` is the layer that
        does, and the two are complementary rather than nested."""
        c = _Cell().ink(200, 110, 4, 20)
        got = []
        LD.detect_stems(c, candidates_out=got)
        self.assertEqual(got, [])

    def test_too_tall(self):
        c = _Cell().ink(200, 20, 4, 360)      # 18 spaces
        self.assertEqual(self._one(c).outcome, LD.RUN_TOO_TALL)

    def test_too_wide(self):
        c = _Cell().ink(200, 110, 30, 80)     # 1.5 spaces wide
        self.assertEqual(self._one(c).outcome, LD.RUN_TOO_WIDE)

    def test_at_a_cell_edge(self):
        c = _Cell().ink(2, 110, 4, 80)
        self.assertEqual(self._one(c).outcome, LD.RUN_AT_CELL_EDGE)

    def test_at_the_right_cell_edge_too(self):
        """⚠️ BOTH EDGES, because the test is `x < margin OR x + w > w -
        margin` and a mutation that drops either half is invisible to a
        left-edge-only fixture."""
        c = _Cell().ink(W - 6, 110, 4, 80)
        self.assertEqual(self._one(c).outcome, LD.RUN_AT_CELL_EDGE)

    def test_the_aspect_and_area_filters_cannot_fire_at_all(self):
        """⚠️⚠️ A FINDING, NOT A GAP IN THE FIXTURES, AND IT IS ARITHMETIC.
        `detect_stems` is described everywhere -- its own docstring, the stage
        charter, §9 of the boxing proposal -- as SIX filters. Under the
        SHIPPED CONSTANTS only FOUR can ever fire:

          * ASPECT (`h/w < 3.0`) is unreachable because a candidate that got
            this far has `h >= min_h = 2.0 spaces` and `w <= max_w = 0.6
            spaces`, so `h/w >= 2.0/0.6 = 3.33 > 3.0` ALWAYS.
          * AREA (`area < max(4, spacing*0.5)`) is unreachable because a
            component that survived a `(1, 1.6 spaces)` opening carries at
            least 1.6 spaces of ink in one column -- 32 px here against a
            floor of 10.

        ⚠️ IT IS NOT AN ARGUMENT FOR DELETING THEM. `max_width_lines` is a
        KEYWORD and `filter_sweep_arm.py` relaxes it to 1.5, at which both
        become live. They are dead at the DEFAULTS, which is what every
        measurement of this chain has been taken at. Asserted as an
        INEQUALITY over the constants rather than by failing to build a
        fixture, because *"I could not make it fire"* and *"it cannot fire"*
        are different claims and only the second is checkable."""
        self.assertGreaterEqual(2.0 / 0.6, 3.0)
        self.assertGreaterEqual(2.0 * LD.STEM_KERNEL_MARGIN * SPACING,
                                max(4, SPACING * 0.5))
        self.assertIn(LD.RUN_ASPECT, LD.RUN_DIMENSION_REASONS)
        self.assertIn(LD.RUN_TOO_LITTLE_AREA, LD.RUN_DIMENSION_REASONS)

    def test_a_squat_blob_is_refused_as_too_wide_and_never_as_aspect(self):
        """The positive control on the class above: ink that LOOKS like an
        aspect failure is caught one filter earlier, which is why that branch
        is dead."""
        c = _Cell().ink(200, 110, 40, 60)     # 1.5:1, 2.0 spaces wide
        self.assertEqual(self._one(c).outcome, LD.RUN_TOO_WIDE)

    def test_the_pair_rule_is_a_seventh_outcome_and_not_one_of_the_six(self):
        """⚠️⚠️ THE ONE REJECTION A CANDIDATE'S OWN MEASUREMENTS CANNOT
        EXPLAIN. `_drop_paired_strokes` runs over the SET, after the range
        filters, so both members passed every dimension bound and were refused
        by a RELATION. Pooling it with the six would hide that."""
        c = _Cell()
        c.ink(440, 110, 4, 60)
        c.ink(452, 110, 4, 60)
        got = []
        kept = LD.detect_stems(c, candidates_out=got)
        self.assertEqual(kept, [], "the pair rule did not fire")
        self.assertEqual([x.outcome for x in got],
                         [LD.RUN_PAIRED, LD.RUN_PAIRED])
        for x in got:
            self.assertNotIn(x.outcome, LD.RUN_DIMENSION_REASONS)
            self.assertFalse(x.accepted)

    def test_with_the_pair_rule_off_the_same_two_read_accepted(self):
        """The positive control on the class above: the two runs pass every
        dimension bound, so `RUN_PAIRED` is genuinely about the relation."""
        c = _Cell()
        c.ink(440, 110, 4, 60)
        c.ink(452, 110, 4, 60)
        got = []
        kept = LD.detect_stems(c, drop_accidental_pairs=False,
                               candidates_out=got)
        self.assertEqual(len(kept), 2)
        self.assertEqual([x.outcome for x in got],
                         [LD.RUN_ACCEPTED, LD.RUN_ACCEPTED])


class TestTheReasonReachesTheRecord(unittest.TestCase):

    def test_a_refused_run_gets_a_row_where_before_it_got_nothing(self):
        c = _Cell().ink(200, 110, 30, 80)     # too WIDE, nothing else
        log = _run([c])
        rows = _rows(log)
        self.assertEqual(len(rows), 1)
        d = rows[0].detail
        self.assertEqual(d["run_outcome"], LD.RUN_TOO_WIDE)
        self.assertFalse(d["run_accepted"])
        self.assertTrue(d["run_refused_by_dimension"])
        # ⚠️⚠️ THIS ASSERTION USED TO PIN THE COLLAPSE RATHER THAN THE FIX.
        # It read: *"`Q.STEM` STILL SAYS `NO_INK` ABOUT THE SAME CELL, which
        # is the collapse this quantity exists to make VISIBLE rather than to
        # fix"* -- and a test that pins a known-false claim keeps it alive.
        # The claim was false 2,377 times on one record (`trace
        # --empty-claims`), so `Q.STEM` now says what it actually knows: the
        # reader RAN and accepted no stroke. The cell has ink, `Q.VERTICAL_RUN`
        # says which filter refused the candidate, and neither row claims the
        # page is blank.
        stem = [r for r in log.all_rows()
                if getattr(r, "quantity", None) == Q.STEM]
        self.assertEqual(len(stem), 1)
        self.assertEqual(stem[0].reason, ABSTAIN.NO_LINE_ACCEPTED)
        # ⚠️ The two rows must still say DIFFERENT things about one cell --
        # that separation is what this quantity exists for, and collapsing
        # them into one word is the fault from the other direction.
        self.assertNotEqual(stem[0].reason, d["run_outcome"])

    def test_the_value_is_x_y_w_h_and_not_corners(self):
        """⚠️⚠️ THREE BOX CONVENTIONS DISAGREE IN ONE RECORD and reading one
        as another yields a NEGATIVE width and a clean believable zero -- it
        cost `omr-ink-extent-2026-09` a whole run. Asserted against the row's
        OWN stated spans, which is the check that write-up asks for."""
        c = _stemmy(_Cell(), x=200, y=110, w=4, h=80)
        got = []
        LD.detect_stems(c, candidates_out=got)
        rows = _rows(_run([c]))
        self.assertEqual(len(rows), 1)
        x, y, w, h = rows[0].value
        # ⚠️ AGAINST THE CANDIDATE'S OWN BOX, not the drawn rectangle: an
        # even-height structuring element shifts the opened component by a
        # pixel (drawn at y=110, found at y=111). Asserting the drawn value
        # would be asserting a property of `cv2`'s anchor, and it fails.
        self.assertEqual((x, y, w, h), (got[0].x, got[0].y, got[0].w, got[0].h))
        self.assertEqual((w, h), (4, 80))
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)
        # the page box IS corners, and the two agree through the upscale
        px0, py0, px1, py1 = rows[0].detail["run_bbox_page_px"]
        self.assertAlmostEqual(px1 - px0, w / c.upscale_factor, places=6)
        self.assertAlmostEqual(py1 - py0, h / c.upscale_factor, places=6)

    def test_the_run_carries_no_score(self):
        """A ruler reading is not a guess. `CLAIMS` says MEASUREMENT and
        `capture.py` files it under RAW_INK; this is the row agreeing."""
        rows = _rows(_run([_stemmy(_Cell())]))
        self.assertIsNone(rows[0].score)
        self.assertEqual(CLAIMS["VERTICAL_RUN"], CLAIM.MEASUREMENT)

    def test_the_reader_and_the_raster_are_recorded(self):
        rows = _rows(_run([_stemmy(_Cell())]))
        self.assertEqual(rows[0].reader, READERS.CV_LINES)
        self.assertTrue(rows[0].detail["staff_lines_erased"])
        self.assertEqual(rows[0].detail["image"], "no_staff")

    def test_a_cell_with_no_erased_raster_says_original(self):
        """`line_detection` falls back to `cell.image` SILENTLY, which is why
        every row says which raster answered."""
        c = _Cell(erased=False)
        c.image[110:190, 200:204] = 0
        rows = _rows(_run([c]))
        self.assertTrue(rows)
        self.assertFalse(rows[0].detail["staff_lines_erased"])
        self.assertEqual(rows[0].detail["image"], "original")

    def test_an_empty_cell_abstains_no_ink_and_that_one_is_honest(self):
        log = _run([_Cell()])
        rows = [r for r in log.all_rows()
                if getattr(r, "quantity", None) == Q.VERTICAL_RUN]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].reason, ABSTAIN.NO_INK)
        self.assertIsNone(getattr(rows[0], "value", None))

    def test_n_candidates_travels_on_every_row(self):
        c = _Cell()
        _stemmy(c)
        c.ink(320, 110, 30, 80)
        rows = _rows(_run([c]))
        self.assertEqual(len(rows), 2)
        for r in rows:
            self.assertEqual(r.detail["run_n_candidates"], 2)

    def test_two_cells_get_disjoint_subjects(self):
        """⚠️ `_VERTICAL_RUN_GLYPH_BASE` is offset past the detector's
        ordinals, past the CV base and past the ink base so FOUR readers
        cannot collide in one cell's key space. A collision would not raise;
        it would silently merge two readers' rows into one subject."""
        a, b = _stemmy(_Cell(measure=0)), _stemmy(_Cell(measure=1))
        log = _run([a, b])
        keys = [r.subject.to_key() for r in log.all_rows()
                if getattr(r, "quantity", None) == Q.VERTICAL_RUN]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertGreater(G._VERTICAL_RUN_GLYPH_BASE, G._INK_GLYPH_BASE)


# ─────────────────────────────────────────────────────────────────────────────
# §3 THE PAGE FRAME — the thing that makes Sean's test computable
# ─────────────────────────────────────────────────────────────────────────────


class TestThePageFrameIsThereAndIsDeclinedNotDefaulted(unittest.TestCase):
    """⚠️⚠️ THIS IS THE POINT OF THE QUANTITY. `Q.STAFF_LINES` is PAGE px;
    `Q.STEM` is CELL canonical with no page fields. Sean's barline test needs
    both in one frame, so the rows carry the run's endpoints in page pixels --
    and a cell that cannot supply the frame gets `frame_note` and NO page
    fields, which is the `Q.INK` rule and the `Q.ONSET_COLUMN` lesson (1,062
    columns of nothing, read off canonical x)."""

    def test_the_endpoints_are_in_page_pixels(self):
        c = _stemmy(_Cell(x0=1000, y0=2000, upscale=4.0),
                    x=200, y=110, w=4, h=80)
        got = []
        LD.detect_stems(c, candidates_out=got)
        cand = got[0]
        d = _rows(_run([c]))[0].detail
        self.assertAlmostEqual(d["run_y_top_page"], 2000 + cand.y / 4.0)
        self.assertAlmostEqual(d["run_y_bottom_page"],
                               2000 + (cand.y + cand.h) / 4.0)
        self.assertAlmostEqual(d["run_x_center_page"],
                               1000 + (cand.x + cand.w / 2.0) / 4.0)
        # the conversion is a SCALE, so the page-px height is the canonical
        # height over the upscale -- checked so a unit slip cannot hide
        self.assertAlmostEqual(d["run_y_bottom_page"] - d["run_y_top_page"],
                               cand.h / 4.0)

    def test_two_staves_pages_differ_where_their_canonical_x_agrees(self):
        """⚠️ THE FRAME ERROR THIS EXISTS TO AVOID, asserted directly: the two
        cells hold ink at the SAME canonical x and must not report the same
        page x. A canonical x is measured inside one cell rescaled so the
        staff span is constant, so two staves' canonical x are not the same
        quantity."""
        a = _stemmy(_Cell(staff=0, x0=1000, y0=2000))
        b = _stemmy(_Cell(staff=1, x0=1000, y0=2400))
        log = _run([a, b])
        rows = [r for r in log.all_rows()
                if getattr(r, "quantity", None) == Q.VERTICAL_RUN
                and getattr(r, "value", None) is not None]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].value, rows[1].value)          # same canonical
        self.assertNotEqual(rows[0].detail["run_y_top_page"],
                            rows[1].detail["run_y_top_page"])

    def test_a_cell_with_no_page_box_declines_rather_than_defaults(self):
        c = _stemmy(_Cell(page_box=False))
        d = _rows(_run([c]))[0].detail
        for key in ("run_bbox_page_px", "run_y_top_page",
                    "run_y_bottom_page", "run_x_center_page"):
            self.assertNotIn(key, d)
        self.assertIn("no page box", d["frame_note"])

    def test_the_staff_space_unit_is_the_cells_own(self):
        """⚠️ NOT A FLAT 100 px. `_upscale_to_canonical` scales a too-wide cell
        by WIDTH, which is why `Q.CELL_STAFF_SPACE` exists as a quantity at
        all: 1,167 of 1,180 Litolff cells sit at exactly 100 and 13 do not."""
        wide = [200, 250, 300, 350, 400]          # 50 px per space, not 20
        c = _stemmy(_Cell(lines=wide), x=200, y=210, w=8, h=200)
        got = []
        LD.detect_stems(c, candidates_out=got)
        d = _rows(_run([c]))[0].detail
        self.assertAlmostEqual(d["run_staff_space_px"], 50.0)
        self.assertAlmostEqual(d["run_height_spaces"],
                               round(got[0].h / 50.0, 3))
        self.assertAlmostEqual(d["run_width_spaces"], 0.16)
        # ⚠️ AND THE FLAT 100 px WOULD HAVE BEEN WRONG HERE BY 2x, which is
        # the point: the nominal is right on 98.9% of Litolff cells and
        # silently wrong on the rest.
        self.assertNotAlmostEqual(d["run_height_spaces"], got[0].h / 100.0)

    def test_the_height_in_spaces_is_what_the_filters_were_measured_in(self):
        """§9 of the boxing proposal quotes the stem distribution as p05 2.14 /
        median 3.93 / p95 6.78 STAFF SPACES against `min_height` 2.0 and
        `max_height` 8.0. A row reporting pixels could not be compared with
        that at all, and a row reporting the wrong unit would be compared and
        be wrong."""
        c = _stemmy(_Cell(), x=200, y=110, w=4, h=80)
        d = _rows(_run([c]))[0].detail
        self.assertAlmostEqual(d["run_height_spaces"], 4.0)
        self.assertTrue(2.0 <= d["run_height_spaces"] <= 8.0)
        self.assertAlmostEqual(d["run_width_spaces"], 0.2)


# ─────────────────────────────────────────────────────────────────────────────
# §4 THE VOCABULARY HAS NOT DRIFTED
# ─────────────────────────────────────────────────────────────────────────────


CENSUS = (pathlib.Path(__file__).resolve().parents[3] / "benchmarks"
          / "omr-stem-ink-2026-09" / "rejection_census.py")


class TestTheReasonWordsAreTheCensusOwn(unittest.TestCase):
    """⚠️⚠️ `benchmarks/omr-stem-ink-2026-09/rejection_census.py` already
    replicates this filter chain component by component and ASSERTS PER CELL
    that its accepted set is identical to the real `detect_stems`. That makes
    its six categories the MEASURED vocabulary, and the reason strings here
    are the same characters.

    ⚠️ The check is SOURCE-LEVEL and that is deliberate: two copies of a
    vocabulary is how they drift, and a test that reads the other file's text
    is what makes an edit to either one loud. It ABSTAINS if the census is
    absent -- a benchmark tree can be pruned and a missing file must not read
    as agreement."""

    def setUp(self):
        if not CENSUS.is_file():
            self.skipTest(f"census absent: {CENSUS}")
        self.text = CENSUS.read_text(encoding="utf-8")

    def test_each_of_the_six_dimension_reasons_appears_verbatim(self):
        for word in LD.RUN_DIMENSION_REASONS:
            self.assertIn(word, self.text, word)
        # ⚠️ POSITIVE CONTROL: the assertion above would pass against any file
        # that happened to contain the strings, so check the census is really
        # the chain -- it names the function it replicates.
        self.assertIn("detect_stems", self.text)

    def test_the_pair_rule_is_named_separately_there_too(self):
        """The census's own word for it is *"a component WAS accepted (pair
        rule dropped it)"* -- a different string, because it describes a
        different axis. What must agree is that it is SEPARATE from the six,
        not that the wording matches."""
        self.assertIn("pair rule dropped it", self.text)
        self.assertNotIn(LD.RUN_PAIRED, self.text)

    def test_every_outcome_the_chain_can_produce_is_in_the_vocabulary(self):
        """⚠️ A DRIFT IN THE OTHER DIRECTION: a seventh filter added to
        `detect_stems` with a reason word not in `RUN_OUTCOMES`. Run over ink
        that trips every branch, so the set is the chain's own."""
        c = _Cell()
        _stemmy(c)
        c.ink(240, 110, 4, 36)
        c.ink(280, 20, 4, 360)
        c.ink(320, 110, 30, 80)
        c.ink(2, 110, 4, 80)
        c.ink(380, 110, 40, 60)
        c.ink(440, 110, 4, 60)
        c.ink(452, 110, 4, 60)
        got = []
        LD.detect_stems(c, candidates_out=got)
        seen = {x.outcome for x in got}
        self.assertEqual(seen - set(LD.RUN_OUTCOMES), set())
        # ⚠️ EVERY OUTCOME THAT CAN FIRE AT THE SHIPPED DEFAULTS -- six of the
        # eight, because ASPECT and AREA are unreachable (see
        # `test_the_aspect_and_area_filters_cannot_fire_at_all`). Naming the
        # two exclusions rather than asserting a bare subset is what makes
        # this go red if a ninth outcome is added and never exercised.
        self.assertEqual(
            set(LD.RUN_OUTCOMES) - seen
            - {LD.RUN_TOO_LITTLE_AREA, LD.RUN_ASPECT}, set())

    def test_the_dimension_group_is_the_six_and_not_the_seven(self):
        self.assertEqual(len(LD.RUN_DIMENSION_REASONS), 6)
        self.assertNotIn(LD.RUN_PAIRED, LD.RUN_DIMENSION_REASONS)
        self.assertNotIn(LD.RUN_ACCEPTED, LD.RUN_DIMENSION_REASONS)
        self.assertEqual(set(LD.RUN_OUTCOMES),
                         set(LD.RUN_DIMENSION_REASONS)
                         | {LD.RUN_ACCEPTED, LD.RUN_PAIRED})


class TestNothingReadsItYet(unittest.TestCase):
    """⚠️ PRODUCER ONLY, and asserted rather than promised -- the `Q.INK`
    discipline: a producer and its first consumer landing in one change makes
    the reach measurement circular. The day a decision reads it, this test
    goes red and its `KNOWN_GAPS` block leaves `wiring.py`."""

    def test_no_adjudicator_consequence_or_inference_declares_it(self):
        from tools.omr.staged import adjudicate
        for name, dec in adjudicate.REGISTRY.items():
            for attr in ("wants", "composed_from", "checked_by", "implicates"):
                for q in (getattr(dec, attr, None) or ()):
                    self.assertNotEqual(q, Q.VERTICAL_RUN,
                                        f"{name}.{attr} reads it")

    def test_the_exporter_does_not_read_it(self):
        root = pathlib.Path(__file__).resolve().parents[1] / "staged"
        for mod in ("export.py", "consequences.py", "inferences.py"):
            text = (root / mod).read_text(encoding="utf-8")
            self.assertNotIn("VERTICAL_RUN", text, mod)


if __name__ == "__main__":
    unittest.main()
