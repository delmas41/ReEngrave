"""`positions.py`: every family's own staff-relative position fact.

⚠️⚠️ SEAN, 2026-09-17: *"send an agent out to give the families real position
information - or if it should be symbol specific then make it so"* — and the
second clause is what these tests are mostly about. Eleven families graded
`position: NONE` in `capture.py`; they do NOT get one schema eleven times,
because a rest's position (which side of which line it hangs from), a meter's
(two marks, one in each half) and a dynamic's (how far below the bottom line,
since it is not on the grid at all) are different measurements.

⚠️⚠️ AND, THE SAME DAY: *"position is an option for helping us determine
something but will rarely be a clear rule that determines by itself... Quick
rules will give us quick results that could be poor."* So `TestNothingHereRules
AnythingOut` asserts the ABSENCE of a veto — there is no threshold in the
module and no field that refuses anything — and `TestAmbiguityIsRecordedNot
Resolved` asserts the fields that exist to keep an ambiguous reading ambiguous.
Both are pinned by mutation arms, because an assertion about an absence is the
easiest kind to write vacuously.

⚠️ THE ENGRAVING FACTS THE FIXTURES ENCODE ARE CHECKABLE BY A MUSICIAN, which
is the point of using them rather than round numbers: a whole rest hangs BELOW
the second line from the top, a half rest SITS ON the middle line, and they are
otherwise the same rectangle. If a fixture here disagrees with a score, the
fixture is wrong.
"""

from __future__ import annotations

import inspect
import os
import unittest

from tools.omr.staged import gather as G
from tools.omr.staged import positions as POS
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Observation, Q, READERS

#: Five lines 20 canonical px apart, so one STEP is 10 px and the bottom line
#: sits at step 8.0. Every expected value below is hand-derived from that.
LINES = [100.0, 120.0, 140.0, 160.0, 180.0]
STEP = 10.0


def step_y(step: float) -> float:
    """Canonical y of a staff STEP. Top line is 0.0, bottom line 8.0."""
    return LINES[0] + step * STEP


class _Det:
    def __init__(self, name, *, top_step, bottom_step, x=50.0, w=30.0,
                 conf=0.5):
        self.smufl_name = name
        self.category = "notehead"
        self.x_canonical = x
        self.y_canonical = step_y(top_step)
        self.width_canonical = w
        self.height_canonical = step_y(bottom_step) - step_y(top_step)
        self.confidence = conf
        self.x_center = x + w / 2.0
        self.y_center = self.y_canonical + self.height_canonical / 2.0


class _Cell:
    def __init__(self, *, staff=0, measure=0, page=0, lines=LINES,
                 x0=1000, y0=2000, upscale=4.0):
        self.page_index = page
        self.system_index = 0
        self.staff_index = staff
        self.measure_index = measure
        self.staff_line_ys_canonical = list(lines) if lines else []
        self.bbox_page_px = (x0, y0, x0 + 400, y0 + 200)
        self.upscale_factor = upscale


class _Staff:
    """What `_staff_bands` reads: `line_ys` in PAGE pixels + a spacing."""

    def __init__(self, staff_index=0, top=2000.0, spacing=25.0):
        self.staff_index = staff_index
        self.line_ys = [top + i * spacing for i in range(5)]
        self.staff_line_spacing = spacing


class _Page:
    def __init__(self, page_index=0):
        self.page_index = page_index


class _Pws:
    def __init__(self, staves, page_index=0):
        self.page = _Page(page_index)
        self.staves = staves


def _local(n=1):
    return {i: (0, i) for i in range(n)}


def _run(cells, detections, *, on=True, pws=None):
    """Drive the SHIPPED entry point with the flag set explicitly.

    ⚠️⚠️ OFF IS AN EXPLICIT OFF WORD AND NEVER A POP. Under a default-OFF flag
    a pop happens to give the right answer — which is exactly why it must not
    be used: the day the default flips, every off-test silently becomes an
    on-test. CLAUDE.md records that costing ten red tests on the meter flip
    ("three harnesses expressed 'off' by POPPING the variable"), and
    `test_staged_ink`'s helper had the same bug. Set the value.
    """
    log = Log()
    old = os.environ.get(POS.POSITIONS_ENV)
    os.environ[POS.POSITIONS_ENV] = "1" if on else "0"
    try:
        POS.gather_family_positions(
            log, pws or _Pws([_Staff()]), cells, _local(len(
                {c.staff_index for c in cells})), detections)
    finally:
        if old is None:
            os.environ.pop(POS.POSITIONS_ENV, None)
        else:
            os.environ[POS.POSITIONS_ENV] = old
    return log


def _one(log, quantity):
    rows = [r for r in log.all_rows()
            if r.quantity == quantity and isinstance(r, Observation)]
    assert len(rows) == 1, f"{quantity}: expected 1 row, got {len(rows)}"
    return rows[0]


def _key(cell):
    return R.cell(cell.page_index, 0, cell.staff_index,
                  cell.measure_index).to_key()


# ─────────────────────────────────────────────────────────────────────────────


class TestTheFlagIsOffByDefaultAndIsAnAllowList(unittest.TestCase):
    """⚠️ CLAUDE.md, *"A flag's OFF test must follow its DEFAULT"*: five shipped
    flags had it backwards. Under a DEFAULT-OFF flag a deny-list is switched ON
    by a typo, which is the mirror of the default-ON hazard. These assert the
    direction directly rather than trusting the derived scan, because that scan
    has twice been blind to the flag it was looking at."""

    def setUp(self):
        self._old = os.environ.pop(POS.POSITIONS_ENV, None)

    def tearDown(self):
        if self._old is not None:
            os.environ[POS.POSITIONS_ENV] = self._old
        else:
            os.environ.pop(POS.POSITIONS_ENV, None)

    def test_absent_is_off(self):
        self.assertFalse(POS.positions_enabled())

    def test_a_typo_leaves_it_off(self):
        for word in ("yess", "", "ON!", "2", "true-ish", " "):
            os.environ[POS.POSITIONS_ENV] = word
            self.assertFalse(POS.positions_enabled(), word)

    def test_an_explicit_on_word_turns_it_on(self):
        for word in ("1", "true", "YES", "on", " On "):
            os.environ[POS.POSITIONS_ENV] = word
            self.assertTrue(POS.positions_enabled(), word)

    def test_flag_off_writes_nothing_at_all(self):
        """⚠️ NOT AN ABSTENTION EITHER — ABSENT. A record from a tree carrying
        this module must be byte-identical to one from a tree without it, and
        `"position": None` rows would break exactly that."""
        cell = _Cell()
        dets = {_key(cell): [_Det("restWhole", top_step=2.0, bottom_step=3.0)]}
        self.assertEqual(len(_run([cell], dets, on=False).all_rows()), 0)
        # the POSITIVE CONTROL that makes the zero mean something
        self.assertGreater(len(_run([cell], dets, on=True).all_rows()), 0)


class TestARestIsWhichSideOfWhichLine(unittest.TestCase):
    """⚠️⚠️ THE MOTIVATING FAMILY. A whole rest and a half rest are the SAME
    RECTANGLE and differ only in which line they touch and on which side — a
    whole HANGS BELOW the second line from the top, a half SITS ON the middle
    one. No shape fact separates them, which is why the phantom-note census
    recorded being unable to, and why `OMR_WHOLE_REST_INK` (the one staged rule
    that DELETES notes) leans on a shape window plus a slot witness."""

    def _rest(self, top, bottom):
        cell = _Cell()
        dets = {_key(cell): [_Det("restWhole", top_step=top,
                                  bottom_step=bottom)]}
        return _one(_run([cell], dets), Q.REST_POSITION).detail

    def test_a_whole_rest_hangs_below_the_second_line(self):
        d = self._rest(2.0, 3.0)
        self.assertEqual(d["attached_line"], 1)     # 2nd line from the top
        self.assertEqual(d["attached_edge"], "top")
        self.assertEqual(d["hangs"], "below")
        self.assertAlmostEqual(d["attach_residual"], 0.0)

    def test_a_half_rest_sits_on_the_middle_line(self):
        d = self._rest(3.0, 4.0)
        self.assertEqual(d["attached_line"], 2)     # the middle line
        self.assertEqual(d["attached_edge"], "bottom")
        self.assertEqual(d["hangs"], "above")
        self.assertAlmostEqual(d["attach_residual"], 0.0)

    def test_the_two_differ_ONLY_in_position(self):
        """The discriminating pair, stated as one assertion: same class, same
        height, same width — and the fact separates them."""
        whole, half = self._rest(2.0, 3.0), self._rest(3.0, 4.0)
        self.assertEqual(whole["height_steps"], half["height_steps"])
        self.assertNotEqual((whole["attached_line"], whole["hangs"]),
                            (half["attached_line"], half["hangs"]))


class TestAmbiguityIsRecordedNotResolved(unittest.TestCase):
    """⚠️⚠️ SEAN, 2026-09-17: *"position ... will rarely be a clear rule that
    determines by itself"*. Where a measurement does not separate, the record
    must SAY SO rather than pick — a rest whose two edges are equally near a
    line has not told us which it hangs from, and `hangs: below` read as a fact
    would be a coin flip wearing a field name."""

    def test_a_rest_centred_between_two_lines_attaches_to_neither(self):
        cell = _Cell()
        # top at step 2.5, bottom at 3.5: both 0.5 from a line, exactly.
        dets = {_key(cell): [_Det("restWhole", top_step=2.5,
                                  bottom_step=3.5)]}
        d = _one(_run([cell], dets), Q.REST_POSITION).detail
        self.assertIsNone(d["attached_edge"])
        self.assertIsNone(d["hangs"])
        self.assertAlmostEqual(d["attach_margin"], 0.0)

    def test_attach_margin_says_how_decisive_the_pick_was(self):
        cell = _Cell()
        dets = {_key(cell): [_Det("restWhole", top_step=2.0,
                                  bottom_step=3.0)]}
        decisive = _one(_run([cell], dets), Q.REST_POSITION).detail
        cell2 = _Cell(measure=1)
        dets2 = {_key(cell2): [_Det("restWhole", top_step=2.4,
                                    bottom_step=3.4)]}
        marginal = _one(_run([cell2], dets2), Q.REST_POSITION).detail
        self.assertGreater(decisive["attach_margin"],
                           marginal["attach_margin"])

    def test_both_edges_are_recorded_whatever_the_pick(self):
        """The pick is DERIVED and the raw measurement survives it, so a
        consumer that distrusts the pick loses nothing."""
        cell = _Cell()
        dets = {_key(cell): [_Det("restWhole", top_step=2.0,
                                  bottom_step=3.0)]}
        d = _one(_run([cell], dets), Q.REST_POSITION).detail
        for k in ("top_line", "top_residual", "bottom_line",
                  "bottom_residual"):
            self.assertIn(k, d)

    def test_an_arc_does_not_claim_which_way_it_bends(self):
        """⚠️ A bounding box is IDENTICAL for an arc opening up and one opening
        down, so `opens` is None rather than guessed. That is what stops a
        consumer reading a box as a curve."""
        cell = _Cell()
        dets = {_key(cell): [_Det("slur", top_step=-4.0, bottom_step=-1.0)]}
        d = _one(_run([cell], dets), Q.ARC_POSITION).detail
        self.assertIsNone(d["opens"])
        self.assertIn("ink", d["opens_note"])


class TestNothingHereRulesAnythingOut(unittest.TestCase):
    """⚠️⚠️ SEAN, 2026-09-17: *"Quick rules will give us quick results that
    could be poor."* This module is step TWO — gather everything that could
    help — and step three, deciding what helps, is not its job. These pin the
    ABSENCE of a rule, which is the easiest assertion to write vacuously, so
    each one names the mechanism it would catch."""

    def test_the_module_writes_no_verdict_and_refuses_nothing(self):
        src = inspect.getsource(POS)
        self.assertNotIn(".decide(", src)
        self.assertNotIn("Ruling", src)
        # ⚠️ The only `abstain` calls are about a MISSING RULER (no staff
        # grid, no page box, no band) — never about a value being wrong.
        for reason in ("BELOW_THRESHOLD", "AMBIGUOUS", "OFF_STAFF"):
            self.assertNotIn(f"ABSTAIN.{reason}", src)

    def test_a_meter_glyph_crossing_the_middle_line_is_still_recorded(self):
        """⚠️⚠️ THE ONE THAT WOULD HAVE BEEN A QUICK RULE. Ink bleed fuses a
        numerator and a denominator into one stroke, so a `spans` reading is
        COMPATIBLE with a real meter — and a broken barline also produces two
        fragments in two halves. Neither shape may refuse anything, so a
        spanning glyph gets an ordinary observation like any other."""
        cell = _Cell()
        dets = {_key(cell): [_Det("timeSig4", top_step=1.0, bottom_step=7.0)]}
        row = _one(_run([cell], dets), Q.METER_GLYPH_POSITION)
        self.assertEqual(row.detail["half"], "spans")
        self.assertTrue(row.detail["crosses_middle_line"])
        self.assertIsInstance(row.value, float)

    def test_every_position_row_is_scoreless(self):
        """⚠️ A RULER READING IS NOT A GUESS. `score=None` is the mechanical
        signature `capture.py` keys on, and a score would invite a consumer to
        weigh a measurement as a confidence."""
        cell = _Cell()
        dets = {_key(cell): [
            _Det("restWhole", top_step=2.0, bottom_step=3.0, conf=0.99),
            _Det("slur", top_step=-3.0, bottom_step=-1.0, conf=0.11),
            _Det("timeSig4", top_step=0.0, bottom_step=4.0, conf=0.77),
            _Det("fermataAbove", top_step=-3.0, bottom_step=-1.5),
            _Det("articStaccatoAbove", top_step=-2.0, bottom_step=-1.5),
            _Det("tremolo1", top_step=1.0, bottom_step=2.0),
            _Det("tuplet3", top_step=-4.0, bottom_step=-2.0),
        ]}
        rows = [r for r in _run([cell], dets).all_rows()
                if isinstance(r, Observation)]
        self.assertTrue(rows)
        for r in rows:
            self.assertIsNone(r.score, f"{r.quantity} carries a score")
            self.assertEqual(r.reader, READERS.GEOMETRY)


class TestEachFamilyGetsItsOwnFact(unittest.TestCase):
    """⚠️ SYMBOL-SPECIFIC, and these are the discriminators that differ."""

    def _detail(self, det, quantity):
        cell = _Cell()
        return _one(_run([cell], {_key(cell): [det]}), quantity).detail

    def test_a_meter_digit_names_the_half_it_stands_in(self):
        upper = self._detail(_Det("timeSig3", top_step=0.0, bottom_step=4.0),
                             Q.METER_GLYPH_POSITION)
        lower = self._detail(_Det("timeSig4", top_step=4.0, bottom_step=8.0),
                             Q.METER_GLYPH_POSITION)
        self.assertEqual(upper["half"], "upper")
        self.assertEqual(lower["half"], "lower")
        # a real pair is centred on the middle line from opposite sides
        self.assertLess(upper["centre_steps_from_middle"], 0)
        self.assertGreater(lower["centre_steps_from_middle"], 0)

    def test_a_tuplet_digit_says_whether_it_clears_the_staff(self):
        over = self._detail(_Det("tuplet3", top_step=-4.0, bottom_step=-2.0),
                            Q.TUPLET_MARKER_POSITION)
        inside = self._detail(_Det("tuplet3", top_step=1.0, bottom_step=3.0),
                              Q.TUPLET_MARKER_POSITION)
        self.assertTrue(over["over_staff"])
        self.assertFalse(inside["over_staff"])

    def test_an_arc_records_its_own_depth(self):
        deep = self._detail(_Det("slur", top_step=-6.0, bottom_step=-1.0),
                            Q.ARC_POSITION)
        shallow = self._detail(_Det("tie", top_step=3.0, bottom_step=3.5),
                               Q.ARC_POSITION)
        self.assertGreater(deep["depth_steps"], shallow["depth_steps"])
        self.assertEqual(deep["arc_side"], "above")

    def test_a_mark_is_measured_not_read_off_its_class_name(self):
        """⚠️⚠️ THE POINT OF THE ARTICULATION / FERMATA / ORNAMENT ROWS. The
        class says `Above`; the ruler is asked independently, and this fixture
        puts a `fermataAbove` BELOW the staff so the two DISAGREE. Nothing here
        resolves that — recording the disagreement is the job."""
        d = self._detail(_Det("fermataAbove", top_step=10.0, bottom_step=12.0),
                         Q.FERMATA_POSITION)
        self.assertEqual(d["measured_side"], "below")
        self.assertGreater(d["steps_clear_of_staff"], 0)

    def test_articulation_fermata_and_ornament_are_THREE_quantities(self):
        """⚠️ NOT ONE. A fermata hangs over whatever sounds beneath it (most
        often a whole-bar rest) while an articulation attaches to one notehead
        on the side its class names, and a tremolo rides the STEM and states no
        side at all. Three populations, three distributions; pooling them would
        average a mark that attaches with one that does not."""
        cell = _Cell()
        dets = {_key(cell): [
            _Det("articTenutoBelow", top_step=9.0, bottom_step=9.5),
            _Det("fermataAbove", top_step=-3.0, bottom_step=-1.5),
            _Det("ornamentTrill", top_step=-2.5, bottom_step=-1.0),
        ]}
        log = _run([cell], dets)
        for q in (Q.ARTICULATION_POSITION, Q.FERMATA_POSITION,
                  Q.ORNAMENT_POSITION):
            _one(log, q)


class TestTheTwoFramesAreNamedOnEveryRow(unittest.TestCase):
    """⚠️ TWO UNITS ON PURPOSE, and a consumer must not be able to mix them by
    accident: a mark ON the grid is in STAFF STEPS from the top line, a mark in
    the row of the page BELOW the staff is in STAFF SPACES below the bottom
    line. Giving a `ff` a step coordinate would put it at step 14, a number
    that composes across documents and means nothing."""

    def test_a_step_row_names_the_step_unit(self):
        cell = _Cell()
        dets = {_key(cell): [_Det("restWhole", top_step=2.0, bottom_step=3.0)]}
        self.assertEqual(_one(_run([cell], dets), Q.REST_POSITION)
                         .detail["unit"], POS.UNIT_STEP)

    def test_a_band_row_names_the_band_unit_and_is_in_page_pixels(self):
        cell = _Cell()
        dets = {_key(cell): [_Det("dynamicF", top_step=12.0,
                                  bottom_step=14.0)]}
        row = _one(_run([cell], dets), Q.DYNAMIC_BAND_POSITION)
        self.assertEqual(row.detail["unit"], POS.UNIT_BAND)
        self.assertEqual(row.frame, G.FRAME_PAGE)

    def test_the_band_value_is_spaces_below_the_bottom_line(self):
        """Hand-derived: the staff fixture's bottom line is page y 2100 with
        25 px spacing, so a mark centred at 2150 is +2.0 spaces below it."""
        cell = _Cell()
        det = _Det("dynamicF", top_step=0.0, bottom_step=1.0)
        # place the page box directly: centre at page y 2150
        det.y_canonical, det.height_canonical = 0.0, 100.0
        det.y_center = 50.0
        cell.bbox_page_px = (1000, 2100, 1400, 2300)
        cell.upscale_factor = 1.0
        row = _one(_run([cell], {_key(cell): [det]}),
                   Q.DYNAMIC_BAND_POSITION)
        self.assertAlmostEqual(row.value, 2.0, places=6)


class TestTheGridIsRequiredAndItsAbsenceIsRecordedOnce(unittest.TestCase):
    """⚠️ A ONE-LINE PERCUSSION STAFF HAS NO RULER. The refusal is filed ONCE
    for the cell rather than once per mark, so the record says *this cell has
    no grid* instead of reporting one fault twenty times — the shape
    `gather_notehead_positions` already uses for the same case."""

    def test_no_grid_abstains_once_with_the_count(self):
        cell = _Cell(lines=[140.0])          # one line: no grid
        dets = {_key(cell): [
            _Det("restWhole", top_step=2.0, bottom_step=3.0),
            _Det("restWhole", top_step=4.0, bottom_step=5.0),
            _Det("slur", top_step=-2.0, bottom_step=-1.0)]}
        rows = [r for r in _run([cell], dets).all_rows()
                if r.quantity == Q.CELL_POSITION_BASIS]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].reason, ABSTAIN.NO_STAFF_GEOMETRY)
        self.assertEqual(rows[0].detail["marks_unmeasured"], 3)
        self.assertFalse([r for r in _run([cell], dets).all_rows()
                          if r.quantity == Q.REST_POSITION])

    def test_a_cell_with_no_marks_at_all_writes_nothing(self):
        """⚠️ The refusal is about MARKS IT COULD NOT MEASURE, so a gridless
        cell holding nothing produces no row — otherwise every percussion cell
        on the page would report a fault that has no victim."""
        cell = _Cell(lines=[140.0])
        dets = {_key(cell): [_Det("noteheadBlackInSpace", top_step=2.0,
                                  bottom_step=3.0)]}
        self.assertEqual(len(_run([cell], dets).all_rows()), 0)


class TestTheRoutingIsGathersOwnAndCannotDrift(unittest.TestCase):
    """⚠️⚠️ IMPORTED, NEVER RESTATED. The glyph index of a position row must be
    the glyph index of the SHAPE row, and both walks route by class — so a
    second copy of that routing that drifted by one branch would file a mark
    under the wrong family and attribute its position to ink it does not
    measure. All ten `artic*` classes carry the detector's `ornament` CATEGORY,
    which a category-keyed router would get wrong."""

    def test_the_predicates_come_from_gather(self):
        src = inspect.getsource(POS._family_of)
        for name in ("_ARC_CLASSES", "_ARTIC_PREFIX", "_REST_PREFIX",
                     "_FERMATA_PREFIX", "_ornament_kind", "_TUPLET_CLASSES"):
            self.assertIn(f"G.{name}", src)

    def test_a_tremolo_is_an_ornament_though_its_name_says_otherwise(self):
        self.assertEqual(POS._family_of("tremolo1"), "ornament")

    def test_a_fermata_is_not_an_articulation(self):
        self.assertEqual(POS._family_of("fermataAbove"), "fermata")
        self.assertEqual(POS._family_of("articStaccatoAbove"), "articulation")

    def test_the_glyph_index_matches_the_shape_rows(self):
        """⚠️ THE PARTITION, ASSERTED RATHER THAN TRUSTED. Both walks
        `enumerate(dets)` over the same list, so `glyph/.../7` here must
        measure the ink `glyph/.../7` there names."""
        cell = _Cell()
        dets = [_Det("noteheadBlackInSpace", top_step=1.0, bottom_step=2.0),
                _Det("restWhole", top_step=2.0, bottom_step=3.0),
                _Det("noteheadBlackInSpace", top_step=3.0, bottom_step=4.0),
                _Det("slur", top_step=-3.0, bottom_step=-1.0)]
        d = {_key(cell): dets}
        shape = Log()
        G.gather_glyph_families(shape, d, [cell], _local())
        pos = _run([cell], d)
        for quantity, shape_q in ((Q.REST_POSITION, Q.REST),
                                  (Q.ARC_POSITION, Q.ARC_BOX)):
            p = {r.subject.to_key() for r in pos.all_rows()
                 if r.quantity == quantity}
            s = {r.subject.to_key() for r in shape.all_rows()
                 if r.quantity == shape_q}
            self.assertEqual(p, s, quantity)


class TestPromotionIsPerPageAndIsNotDerivedFrom(unittest.TestCase):
    """⚠️⚠️ THE BUG THAT SHIPPED AND WAS CAUGHT BY A NUMBER THAT NEEDED
    EXPLAINING. `gather()` calls this once PER PAGE and `Log.all_rows()` is the
    WHOLE log — so without a page filter, page 2's pass re-measures page 0's
    and page 1's rows against page 2's bands and files them as ABSTENTIONS,
    because an earlier page's staff key is not in this page's band map. On a
    4-page Brahms run that read 10 direction words it produced 32 rows, 22 of
    them spurious refusals."""

    def _wedge_row(self, log, page, staff_key):
        g = R.glyph(page, 0, 0, 0, 100_000)
        log.observe(g, Q.WEDGE_BOX, "crescendo", reader=READERS.CV_HAIRPINS,
                    frame=G.FRAME_PAGE, score=None,
                    bbox_page_px=[10.0, 2150.0, 90.0, 2170.0])

    def test_an_earlier_pages_rows_are_not_re_measured(self):
        log = Log()
        self._wedge_row(log, 0, None)
        pws1 = _Pws([_Staff()], page_index=1)
        POS._promote_from_log(log, G._staff_bands(pws1, _local()),
                              Q.WEDGE_BOX, Q.WEDGE_BAND_POSITION,
                              only_reader=READERS.CV_HAIRPINS, page=1)
        self.assertFalse([r for r in log.all_rows()
                          if r.quantity == Q.WEDGE_BAND_POSITION])

    def test_its_own_page_IS_measured(self):
        """The positive control: without it the test above passes for a rule
        that measures nothing at all."""
        log = Log()
        self._wedge_row(log, 0, None)
        pws0 = _Pws([_Staff()], page_index=0)
        POS._promote_from_log(log, G._staff_bands(pws0, _local()),
                              Q.WEDGE_BOX, Q.WEDGE_BAND_POSITION,
                              only_reader=READERS.CV_HAIRPINS, page=0)
        rows = [r for r in log.all_rows()
                if r.quantity == Q.WEDGE_BAND_POSITION]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail["source_reader"],
                         READERS.CV_HAIRPINS)

    def test_a_promoted_row_names_its_source_and_is_NOT_derived_from_it(self):
        """⚠️⚠️ `promoted_from` IS NOT `derived_from`, AND THE DIFFERENCE IS
        THE WHOLE POINT OF THE PROMOTION. `derived_from` puts both rows in one
        `Log.closure`, which makes `correlated_groups` call them ONE SIGNAL —
        the absorbed-witness state this change exists to leave. The id is
        recorded so a human can follow the join; the closure stays disjoint."""
        log = Log()
        self._wedge_row(log, 0, None)
        pws0 = _Pws([_Staff()], page_index=0)
        POS._promote_from_log(log, G._staff_bands(pws0, _local()),
                              Q.WEDGE_BOX, Q.WEDGE_BAND_POSITION,
                              only_reader=READERS.CV_HAIRPINS, page=0)
        row = _one(log, Q.WEDGE_BAND_POSITION)
        self.assertIn("promoted_from", row.detail)
        self.assertEqual(row.basis, ())
        source = log.row(row.detail["promoted_from"])
        self.assertIsNotNone(source)
        self.assertFalse(log.closure(row.id) & log.closure(source.id))


class TestEveryPositionQuantityIsRegistered(unittest.TestCase):
    """⚠️ DERIVED, so a new quantity added here without telling the derived
    instruments is a RED TEST rather than a silent omission — the
    `class_aliases.unaccounted()` contract this repo already trusts."""

    def test_capture_classifies_each_one_and_names_its_family(self):
        from tools.omr.staged import capture as C
        from tools.omr.staged import export as E
        for q in (Q.REST_POSITION, Q.ARC_POSITION, Q.ARTICULATION_POSITION,
                  Q.FERMATA_POSITION, Q.ORNAMENT_POSITION,
                  Q.TUPLET_MARKER_POSITION, Q.METER_GLYPH_POSITION,
                  Q.DYNAMIC_BAND_POSITION, Q.WEDGE_BAND_POSITION,
                  Q.DIRECTION_BAND_POSITION):
            name = q.upper()
            self.assertIn(name, C.UNSCORED, name)
            self.assertTrue(C._is_position(name), name)
            fams = C._families_of(name)
            self.assertTrue(fams, name)
            for fam in fams:
                self.assertIn(fam, E.FAMILIES, f"{name} -> {fam}")

    def test_reach_accounts_for_every_one_as_an_OPEN_finding(self):
        """⚠️ THE TEN POSITIONS ARE `OPEN BY DESIGN` — producers whose first
        consumer deliberately has not landed, so that the reach measurement is
        not circular. Each entry names that consumer, because *UNREAD and
        unremarked* is how `Q.STEM` stayed unread through three discoveries."""
        from tools.omr.staged import reach
        for q in (Q.REST_POSITION, Q.ARC_POSITION, Q.ARTICULATION_POSITION,
                  Q.FERMATA_POSITION, Q.ORNAMENT_POSITION,
                  Q.TUPLET_MARKER_POSITION, Q.METER_GLYPH_POSITION,
                  Q.DYNAMIC_BAND_POSITION, Q.WEDGE_BAND_POSITION,
                  Q.DIRECTION_BAND_POSITION):
            self.assertIn(q, reach.KNOWN_GAPS, q)
            self.assertIn("OPEN BY DESIGN", reach.KNOWN_GAPS[q], q)
            self.assertIn("CONSUMER", reach.KNOWN_GAPS[q], q)

    def test_the_refusal_row_is_accounted_for_as_a_DIFFERENT_kind(self):
        """⚠️ AND `CELL_POSITION_BASIS` IS NOT ONE OF THEM — asserted apart,
        because the first version of the test above required `OPEN` of it too
        and went red. It is ABSTAIN-ONLY BY CONSTRUCTION (the shape
        `Q.SYSTEMIC_COLUMN` already has): it is never observed, so it is not a
        producer waiting for a consumer. Folding the two kinds into one
        assertion would have made the stricter claim untestable."""
        from tools.omr.staged import reach
        self.assertIn(Q.CELL_POSITION_BASIS, reach.KNOWN_GAPS)
        self.assertIn("ABSTAIN-ONLY",
                      reach.KNOWN_GAPS[Q.CELL_POSITION_BASIS])
        self.assertNotIn("OPEN BY DESIGN",
                         reach.KNOWN_GAPS[Q.CELL_POSITION_BASIS])

    def test_this_module_is_a_declared_GATHER_stage(self):
        """⚠️ `reach.unaccounted_modules()` found this file in neither list on
        the day it landed — a new staged module is otherwise silently skipped
        and every quantity only it reads reads as UNREAD."""
        from tools.omr.staged import reach
        self.assertEqual(reach.STAGE_OF_FILE.get("positions.py"), "GATHER")
        self.assertEqual(reach.unaccounted_modules(), [])

    def test_the_arc_quantity_serves_BOTH_arc_families(self):
        """⚠️ ONE QUANTITY, TWO FAMILIES. `slur` and `tie` read one quantity
        over one piece of ink; two position quantities on one glyph would be
        the *two rows from one reader are ONE signal* fault made by accident."""
        from tools.omr.staged import capture as C
        self.assertEqual(set(C._families_of("ARC_POSITION")), {"slur", "tie"})


if __name__ == "__main__":
    unittest.main()
