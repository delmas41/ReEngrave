"""ROADMAP 2.72 -- the meter on Brahms 1/i Breitkopf page 2 (pdf page 1).

Sean, 2026-10-09, the held-bar tiles: the header at bar 8 prints **9/8** on
every staff (tiles 1, 2) and bar 9 prints a **6/8 change** on every staff
(tiles 3, 4). Today's record read `9/4` for the first, nothing for the second,
and abstained on the next system. Three causes, one test class each:

  * GATHER, the header: the whole-stack correlation under-reads the
    DENOMINATOR (`time_signature_locator._split_reading`).
  * GATHER, the bar head: the change is never asked about, and where it is the
    stack's floor refuses it (`locate_meter_by_halves`, the stacked-head
    candidate column, `rhythm._meter_changes` visiting template-only cells).
  * ADJUDICATE: the courtesy `9/8` printed after page 1's last barline was
    filed as a CHANGE at a cell that is not a bar, because 2.47b stopped
    counting that tail in `Q.MEASURE_PARTITION` and the cautionary test still
    compared against the old last cell (`rhythm._meter_changes`).

⚠️ THE CROPS ARE THE PLATE, NOT A DRAWING OF IT. `fixtures/meter_2_72/` holds
the pipeline's own header cells and bar-head windows cut from the real page
(`library/` Breitkopf 317803, pdf page 1) -- the fixture the unit tests of this
reader have never had (ROADMAP 2.12i: "a clean printed 6/8 the detector never
boxes ... the fixture the flag was waiting for"). Each reading test carries the
control that makes it able to fail: the unrepaired reading is asserted on the
SAME crop, so a fixture that cannot reproduce the defect fails loudly.

RED against `origin/main` (404285f3...): every test class below that names a
repaired behaviour fails there -- recorded in the commit message.
"""

from __future__ import annotations

import json
import pathlib
import unittest
from dataclasses import replace

import cv2
import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm as rhythm_mod
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.time_signature_locator import (
    DEFAULT_LOCATOR_CONFIG as CONFIG,
    _meter_templates,
    locate_meter_by_halves,
    locate_time_signature,
)
from tools.omr.types import MeasureCell

FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "meter_2_72"
META = json.loads((FIX / "meta.json").read_text())
STACK_ONLY = replace(CONFIG, split_halves=False)


def _real(name: str) -> MeasureCell:
    """A cell built from one committed crop of the real page."""
    img = cv2.imread(str(FIX / name), cv2.IMREAD_GRAYSCALE)
    assert img is not None, name
    ys = META[name]["ys"]
    return MeasureCell(
        page_index=1, system_index=0, staff_index=META[name]["staff"],
        measure_index=META[name].get("cell", 0), image=img,
        image_no_staff=img, bbox_page_px=(0, 0, img.shape[1], img.shape[0]),
        staff_line_ys_canonical=ys, upscale_factor=1.0)


SPACING = CONFIG.template_em_px / 4.0


def _printing(raw: str) -> MeasureCell:
    """A cell drawn at exactly template scale, printing `raw` -- a clean
    Bravura stack, the control a real-plate crop cannot supply."""
    height, width = int(SPACING * 14), int(SPACING * 30)
    ink = np.zeros((height, width), np.uint8)
    top = int(SPACING * 4)
    template = next(t for (_n, _d, r), t in
                    _meter_templates(CONFIG.template_em_px,
                                     tuple(CONFIG.meters)) if r == raw)
    x0 = int(SPACING * 2)
    ink[top:top + template.shape[0], x0:x0 + template.shape[1]] = template
    image = 255 - ink
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=image, image_no_staff=image, bbox_page_px=(0, 0, width, height),
        staff_line_ys_canonical=[top + i * int(SPACING) for i in range(5)],
        upscale_factor=1.0)


# ─────────────────────────────────────────────────────────────────────────────
# GATHER, the header -- a denominator is read from its own ink
# ─────────────────────────────────────────────────────────────────────────────


class TestADenominatorIsReadFromItsOwnInk(unittest.TestCase):

    HEADERS = ("header_staff3.png", "header_staff5.png", "header_staff9.png")

    def test_the_FIXTURE_reproduces_the_defect_on_the_stack_alone(self):
        """⚠️ THE CONTROL THAT LETS THE TEST BELOW FAIL. On the plate's own
        crops the whole-stack match reads `9/4` (the defect, ten staves of
        fourteen on the page). If this ever reads `9/8` the fixture has gone
        soft and the next test is vacuous."""
        for name in self.HEADERS:
            found = locate_time_signature(_real(name), config=STACK_ONLY)
            self.assertIsNotNone(found, name)
            self.assertEqual(found.raw, "9/4", name)

    def test_the_plates_9_over_8_is_read_9_over_8(self):
        for name in self.HEADERS:
            found = locate_time_signature(_real(name))
            self.assertIsNotNone(found, name)
            self.assertEqual((found.numerator, found.denominator), (9, 8),
                             name)
            self.assertEqual(found.raw, "9/8", name)

    def test_only_the_DENOMINATOR_is_re_read_and_the_record_says_so(self):
        found = locate_time_signature(_real("header_staff3.png"))
        self.assertEqual(found.numerator, 9)
        self.assertEqual(found.stack_raw, "9/4")
        self.assertGreater(found.denominator_margin, 0.0)
        out = found.as_dict()
        self.assertEqual(out["stack_raw"], "9/4")
        self.assertIn("denominator_margin", out)

    def test_the_stack_still_decides_THAT_a_meter_stands_there(self):
        """Nothing new enters the search: a crop the stack refuses is refused
        however its halves would have scored, and the staves the stack
        refused on this plate (below 0.50) stay refused. A blank cell is the
        small form of it."""
        blank = _printing("9/8")
        blank = replace(blank, image=np.full_like(blank.image, 255),
                        image_no_staff=np.full_like(blank.image, 255))
        self.assertIsNone(locate_time_signature(blank))

    # ── controls: a real 9/4 stays 9/4, and the rest of the table does not move

    def test_a_clean_9_over_4_STAYS_9_over_4(self):
        """⚠️ THE RE-READ MUST BE ABLE TO LEAVE A DENOMINATOR ALONE. A bottom
        half that always preferred `8` would pass the Brahms test above and
        fail here."""
        found = locate_time_signature(_printing("9/4"))
        self.assertEqual(found.raw, "9/4")
        self.assertIsNone(getattr(found, "stack_raw", None))

    def test_a_clean_9_over_8_is_9_over_8_on_both_readers(self):
        for cfg in (CONFIG, STACK_ONLY):
            self.assertEqual(
                locate_time_signature(_printing("9/8"), config=cfg).raw, "9/8")

    def test_Litolffs_2_over_4_and_the_other_clean_meters_are_unchanged(self):
        for raw in ("2/4", "3/4", "6/8", "12/8", "2/2"):
            self.assertEqual(
                locate_time_signature(_printing(raw)).raw, raw, raw)

    def test_a_letter_form_has_no_halves_and_is_returned_as_it_was(self):
        self.assertEqual(locate_time_signature(_printing("C")).raw, "C")


# ─────────────────────────────────────────────────────────────────────────────
# GATHER, the bar head -- a change is read from its halves
# ─────────────────────────────────────────────────────────────────────────────


class TestABarHeadChangeIsReadFromItsHalves(unittest.TestCase):

    CHANGE = ("barhead_staff0_cell1.png", "barhead_staff3_cell1.png",
              "barhead_staff7_cell1.png")
    EMPTY = tuple(f"barhead_staff{s}_cell{c}.png"
                  for s in (0, 3, 7) for c in (2, 3))

    def test_the_FIXTURE_reproduces_the_defect_on_the_whole_stack(self):
        """On the plate's bar-9 windows the whole-stack reader (the header
        reader, as `gather_meter_at_bars` used it) reads NO `6/8` on any of
        these staves: it scores 0.47 against a floor of 0.50 (and names
        `6/4` or `9/8` as its best)."""
        for name in self.CHANGE:
            found = locate_time_signature(_real(name))
            self.assertTrue(found is None or found.raw != "6/8", name)

    def test_the_plates_6_over_8_change_is_read_from_the_halves(self):
        for name in self.CHANGE:
            found = locate_meter_by_halves(_real(name))
            self.assertIsNotNone(found, name)
            self.assertEqual(found.raw, "6/8", name)
            self.assertGreaterEqual(found.score, CONFIG.bar_head_half_floor)

    def test_a_bar_that_prints_nothing_is_REFUSED(self):
        """⚠️ THE POSITIVE CONTROL IS THE TEST ABOVE, in the same class: a
        reader that answered everything would pass it and fail here. These
        are real windows of bars 10 and 11 of the same system."""
        for name in self.EMPTY:
            self.assertIsNone(locate_meter_by_halves(_real(name)), name)

    def test_the_weaker_half_is_the_score_so_one_strong_row_cannot_carry_it(self):
        trace: dict = {}
        found = locate_meter_by_halves(_real(self.CHANGE[0]), trace=trace)
        self.assertAlmostEqual(
            found.score,
            min(trace["best"]["numerator"], trace["best"]["denominator"]),
            places=3)

    def test_a_clean_stamped_meter_reads_and_a_blank_window_does_not(self):
        self.assertEqual(locate_meter_by_halves(_printing("3/4")).raw, "3/4")
        blank = _printing("3/4")
        blank = replace(blank, image=np.full_like(blank.image, 255),
                        image_no_staff=np.full_like(blank.image, 255))
        self.assertIsNone(locate_meter_by_halves(blank))


class _Det:
    def __init__(self, smufl_name, x, y, w=10.0, h=10.0):
        self.smufl_name = smufl_name
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h
        self.y_center = y + h / 2.0
        self.confidence = 0.9


class TestAStackedHeadPairOpensAColumn(unittest.TestCase):
    """ROADMAP 2.72: on a scan the detector boxes a printed change's two
    digits as two NOTEHEADS far more often than as a time signature, so a
    column gated on `timeSig*` alone is a column the detector happened to
    name."""

    LOCAL = {0: (0, 0), 1: (0, 1)}
    SPACING = 25.0

    def _dets(self, boxes_by_staff_cell):
        out = {}
        for (staff, cell), boxes in boxes_by_staff_cell.items():
            sysi, sti = self.LOCAL[staff]
            out[R.cell(0, sysi, sti, cell).to_key()] = boxes
        return out

    def _pair(self, x=40.0):
        # two heads at one x, 0.8 space apart centre to centre -- the
        # numerator/denominator pair `is_a_meter_digit` tests
        return [_Det("noteheadBlack", x, 60.0), _Det("noteheadBlack", x, 80.0)]

    def test_the_pair_opens_a_column_where_no_timesig_was_detected(self):
        dets = self._dets({(0, 3): self._pair(), (1, 3): self._pair()})
        cols = G._meter_candidate_columns(
            dets, 0, self.LOCAL, {0: self.SPACING, 1: self.SPACING})
        self.assertEqual(cols, {0: {3: 2}})

    def test_without_the_spacing_the_old_gate_is_all_there_is(self):
        dets = self._dets({(0, 3): self._pair()})
        self.assertEqual(G._meter_candidate_columns(dets, 0, self.LOCAL), {})

    def test_a_lone_head_or_two_heads_far_apart_open_nothing(self):
        dets = self._dets({
            (0, 3): [_Det("noteheadBlack", 40.0, 60.0)],
            (1, 3): [_Det("noteheadBlack", 40.0, 60.0),
                     _Det("noteheadBlack", 400.0, 80.0)]})
        self.assertEqual(G._meter_candidate_columns(
            dets, 0, self.LOCAL, {0: self.SPACING, 1: self.SPACING}), {})

    def test_cell_zero_is_still_never_a_candidate(self):
        dets = self._dets({(0, 0): self._pair()})
        self.assertEqual(G._meter_candidate_columns(
            dets, 0, self.LOCAL, {0: self.SPACING}), {})


# ─────────────────────────────────────────────────────────────────────────────
# ADJUDICATE -- the courtesy in the tail is a courtesy
# ─────────────────────────────────────────────────────────────────────────────


def _staff_count(log, sysj, n):
    log.record(adjudicate.Verdict(
        id=log._next_id("vrd"), subject=sysj, quantity=Q.SYSTEM_STAFF_COUNT,
        outcome=Outcome.DECIDED, value=n, decider="t", reason="counted"))


def _partition(log, sysj, n_staves, n_bars, reason="cautionary_tail_not_a_bar"):
    for st in range(n_staves):
        log.record(adjudicate.Verdict(
            id=log._next_id("vrd"),
            subject=R.staff(sysj.page, sysj.system, st),
            quantity=Q.MEASURE_PARTITION, outcome=Outcome.DECIDED,
            value=n_bars, decider="t", reason=reason))


def _opening(log, sysj, num, den, n_staves):
    for st in range(n_staves):
        log.observe(R.staff(sysj.page, sysj.system, st), Q.METER_TEMPLATE,
                    (num, den), reader=READERS.TEMPLATE,
                    frame="header_window", score=0.7, raw=f"{num}/{den}")


def _stacked(log, sysj, staff, cell, num, den):
    for digit, y in ((num, 10.0), (den, 30.0)):
        log.observe(R.staff(sysj.page, sysj.system, staff), Q.METER_GLYPH,
                    "timeSig%d" % digit, reader=READERS.DETECTOR,
                    frame="cell:%d" % cell, score=0.9, cell=cell, x=10.0,
                    y_center=y, letter=False)


def _run(log):
    log.freeze()
    adjudicate._ensure_decisions()
    spec = adjudicate.REGISTRY[Q.METER]
    for sysj in sorted(log.subjects(R.Kind.SYSTEM)):
        adjudicate.adjudicate_one(log, spec, sysj)


class TestACautionaryInTheTailIsACourtesy(unittest.TestCase):
    """Brahms 1/i page 1 (pdf 0): 7 bars, the courtesy `9/8` printed after the
    last barline in cell 7, which `Q.MEASURE_PARTITION` (2.47b,
    `cautionary_tail_not_a_bar`) does not count -- so the last BAR is cell 6."""

    N = 3

    def _source(self, glyph_cell=7, glyph_staves=(0, 1)):
        log = Log()
        src = R.system(0, 0)
        _staff_count(log, src, self.N)
        _partition(log, src, self.N, 7)
        _opening(log, src, 6, 8, self.N)
        for st in glyph_staves:
            _stacked(log, src, st, glyph_cell, 9, 8)
        return log, src

    def test_a_meter_in_the_tail_is_a_cautionary_and_governs_no_bar(self):
        log, src = self._source()
        _run(log)
        v = log.verdict(Q.METER, src)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual([s["from_cell"] for s in v.value["segments"]], [0],
                         "no change is proposed at a cell that is not a bar")
        caution = v.value.get("cautionary")
        self.assertIsNotNone(caution)
        self.assertEqual((caution["numerator"], caution["denominator"]),
                         (9, 8))
        self.assertTrue(caution["corroborated"])

    def test_the_same_glyph_at_a_real_bar_is_still_a_CHANGE(self):
        """⚠️ THE CONTROL THAT KEEPS THE RULE HONEST. Cell 3 is a bar (the
        partition counts 7); two staves of three read `9/8` there, which
        clears the change floor and is NOT in the tail, so it is a segment
        and no cautionary."""
        log, src = self._source(glyph_cell=3)
        _run(log)
        v = log.verdict(Q.METER, src)
        self.assertEqual([s["from_cell"] for s in v.value["segments"]], [0, 3])
        self.assertIsNone(v.value.get("cautionary"))

    def test_the_cautionary_reaches_the_next_systems_opening(self):
        """The reason it matters: page 1's header votes `9/4` (the denominator
        defect) and the corroborated courtesy `9/8` before it must be asked
        about it (2.12h). With the tail filed as a change that route was
        never taken and the `9/4` was simply decided."""
        log, src = self._source()
        dst = R.system(1, 0)
        _staff_count(log, dst, self.N)
        _opening(log, dst, 9, 4, self.N)
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertFalse(
            v.outcome is Outcome.DECIDED and v.reason == "voted"
            and (v.value["numerator"], v.value["denominator"]) == (9, 4),
            "the vote that contradicts a corroborated courtesy was asserted")

    def test_an_agreeing_opening_is_unchanged(self):
        log, src = self._source()
        dst = R.system(1, 0)
        _staff_count(log, dst, self.N)
        _opening(log, dst, 9, 8, self.N)
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (9, 8))

    def test_a_meter_with_no_change_keeps_holding(self):
        """Sean 2026-10-09: a carried meter HOLDS until a printed change. A
        system that prints nothing after a decided one is still carried (the
        2.22b path is untouched by the tail rule)."""
        log, src = self._source(glyph_staves=())
        dst = R.system(0, 1)
        _staff_count(log, dst, self.N)
        _run(log)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (6, 8))


if __name__ == "__main__":       # pragma: no cover
    unittest.main()
