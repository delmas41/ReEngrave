"""ROADMAP 2.128 -- a dot carries its staff position (STAGED GATHER).

`gather.gather_dot_positions` files `Q.DOT_STAFF_POSITION` for every
`Q.AUG_DOT` box (augmentation and staccato alike), measured against the five
staff lines LOCALLY at the dot's own x (CLAUDE.md Sec.5: a scanned staff tilts
and ~1 px decides a near-boundary pitch), in `NOTEHEAD_STAFF_POSITION`'s unit:
half-steps below the top line, an even step a LINE and an odd one a SPACE.

The fixtures are synthetic rasters (the staff lines are drawn into a numpy
page), so every number below is checkable by hand: one staff space is 20 px,
the top line is at y=100, a step is 10 px.
"""
from __future__ import annotations

import os
import types
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import capture
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS, Scope

SPACE = 20.0
TOP = 100.0
WIDTH, HEIGHT = 1400, 520


def _page(tilt: float = 0.0, staves=((0, TOP),)):
    """A 0 = ink page with one five-line staff per `(index, top_y)`; `tilt`
    is pixels of drop per pixel of x (the staff slopes DOWN to the right)."""
    img = np.full((HEIGHT, WIDTH), 255, dtype=np.uint8)
    xs = np.arange(WIDTH)
    for _i, top in staves:
        for k in range(5):
            ys = np.round(top + k * SPACE + tilt * xs).astype(int)
            for dy in (0, 1):
                img[np.clip(ys + dy, 0, HEIGHT - 1), xs] = 0
    return img


def _staff(index, top):
    # the PAGE-WIDE model: the line rows at x = 0 (a tilted print is only
    # right there)
    return types.SimpleNamespace(
        staff_index=index, line_ys=[top + k * SPACE for k in range(5)],
        x_start=0, x_end=WIDTH, line_spacing_px=SPACE)


def _pws(img, staves):
    return types.SimpleNamespace(
        page=types.SimpleNamespace(binary=img, page_index=0),
        staves=list(staves))


def _cell(staff_index=0, top=TOP):
    """A bar cut at 1:1 from page x 0..WIDTH, y 0..HEIGHT, its own grid the
    page model's rows."""
    return types.SimpleNamespace(
        page_index=0, staff_index=staff_index, measure_index=0,
        bbox_page_px=(0, 0, WIDTH, HEIGHT), upscale_factor=1.0,
        staff_line_ys_canonical=[top + k * SPACE for k in range(5)])


class _Det:
    def __init__(self, name, cx, cy, w=6, h=6):
        self.smufl_name = name
        self.x_canonical, self.y_canonical = cx - w / 2.0, cy - h / 2.0
        self.width_canonical, self.height_canonical = w, h
        self.confidence, self.category = 0.9, "ornament"

    @property
    def x_center(self):
        return self.x_canonical + self.width_canonical / 2.0

    @property
    def y_center(self):
        return self.y_canonical + self.height_canonical / 2.0


CELL = R.cell(0, 0, 0, 0)


def _run(dets, *, tilt=0.0, staves=((0, TOP),), cells=None, img=None):
    """Gather positions for `dets` (all in the cell of staff 0)."""
    img = _page(tilt, staves) if img is None else img
    pws = _pws(img, [_staff(i, t) for i, t in staves])
    local = {i: (0, i) for i, _t in staves}
    cells = [_cell(0, TOP)] if cells is None else cells
    log = Log()
    G.gather_dot_positions(log, pws, cells, local,
                           {CELL.to_key(): list(dets)})
    return log


def _row(log, gi=0):
    g = R.glyph(0, 0, 0, 0, gi)
    return log.rows(Q.DOT_STAFF_POSITION, g)


def _y_of_step(step, top=TOP):
    """Page y of a half-step position on the (untilted) staff."""
    return top + step * SPACE / 2.0


class TestStepArithmetic(unittest.TestCase):
    def test_a_dot_in_the_space_above_the_middle_line_is_an_odd_step(self):
        f = G.dot_step_fields(_y_of_step(3), TOP, SPACE / 2.0)
        self.assertEqual((f["step"], f["on"]), (3, "space"))
        self.assertAlmostEqual(f["margin"], 0.5)

    def test_a_dot_on_a_line_is_an_even_step(self):
        f = G.dot_step_fields(_y_of_step(4), TOP, SPACE / 2.0)
        self.assertEqual((f["step"], f["on"]), (4, "line"))

    def test_the_margin_is_the_distance_to_the_line_space_boundary(self):
        # 0.4 of a step below a line: nearly on the boundary
        f = G.dot_step_fields(_y_of_step(4) + 0.4 * SPACE / 2.0, TOP,
                              SPACE / 2.0)
        self.assertEqual(f["on"], "line")
        self.assertAlmostEqual(f["margin"], 0.1, places=6)

    def test_outside_is_signed(self):
        up = G.dot_step_fields(_y_of_step(-3), TOP, SPACE / 2.0)
        dn = G.dot_step_fields(_y_of_step(11), TOP, SPACE / 2.0)
        self.assertAlmostEqual(up["steps_outside_staff"], -3.0)
        self.assertAlmostEqual(dn["steps_outside_staff"], 3.0)


class TestGatherFilesAPositionForEveryDot(unittest.TestCase):
    def test_RED_a_dot_in_a_space_is_filed_as_a_space_step(self):
        # the space above the middle line (step 3): a line-note's dot
        log = _run([_Det("augmentationDot", 300, _y_of_step(3))])
        (r,) = _row(log)
        self.assertEqual(r.detail["step"], 3)
        self.assertEqual(r.detail["on"], "space")
        self.assertEqual(r.detail["basis"], "local_ink")
        self.assertTrue(r.detail["home"])
        self.assertIsNone(r.score)

    def test_a_dot_on_a_line_is_filed_as_a_line_step(self):
        log = _run([_Det("augmentationDot", 300, _y_of_step(4))])
        (r,) = _row(log)
        self.assertEqual((r.detail["step"], r.detail["on"]), (4, "line"))

    def test_a_staccato_class_dot_is_measured_too(self):
        log = _run([_Det("articStaccatoAbove", 300, _y_of_step(5))])
        (r,) = _row(log)
        self.assertEqual(r.detail["detector_role"], "staccato")
        self.assertEqual(r.detail["step"], 5)

    def test_only_dot_boxes_get_a_position(self):
        log = _run([_Det("noteheadBlack", 300, _y_of_step(4), 20, 16),
                    _Det("augmentationDot", 340, _y_of_step(3))])
        self.assertEqual(_row(log, 0), ())
        self.assertEqual(len(_row(log, 1)), 1)


class TestMeasuredLocally(unittest.TestCase):
    """CLAUDE.md Sec.5. The staff slopes 0.012 px/px: 16 px (0.8 of a space)
    lower at x=1340 than at x=0. The page-wide model's rows are the x=0 ones."""

    TILT = 0.012

    def test_RED_a_tilted_staff_is_measured_at_the_dots_own_x(self):
        x = 1200
        drop = self.TILT * x                       # 14.4 px
        # centred in the space above the middle line OF THE LOCAL STAFF
        y = _y_of_step(3) + drop
        log = _run([_Det("augmentationDot", x, y)], tilt=self.TILT)
        (r,) = _row(log)
        self.assertEqual(r.detail["basis"], "local_ink")
        self.assertEqual((r.detail["step"], r.detail["on"]), (3, "space"))
        self.assertGreater(r.detail["margin"], 0.35)

    def test_CONTROL_the_untilted_model_would_have_read_the_wrong_step(self):
        """The same ink against the page-wide (x=0) rows lands 1.44 steps
        away -- a different step AND the other side of line/space. This is
        what the local measurement prevents; it fails if the fixture stops
        tilting."""
        x = 1200
        y = _y_of_step(3) + self.TILT * x
        f = G.dot_step_fields(y, TOP, SPACE / 2.0)
        self.assertNotEqual(f["step"], 3)

    def test_the_two_ends_of_one_staff_give_two_answers_for_one_height(self):
        """A dot at the SAME page y is in a space at the left end and on a
        line at the right: the local lines decide, not a single model."""
        y = _y_of_step(3)
        left = _row(_run([_Det("augmentationDot", 200, y)],
                         tilt=self.TILT))[0]
        right = _row(_run([_Det("augmentationDot", 1250, y)],
                          tilt=self.TILT))[0]
        self.assertNotEqual((left.detail["step"], right.detail["step"]),
                            (3, 3))


class TestAbstains(unittest.TestCase):
    def test_off_the_staff_abstains_with_the_signed_distance(self):
        # 14 steps below the top line = 6 below the bottom line... on the
        # other side of the page, far from every staff
        log = _run([_Det("augmentationDot", 300, _y_of_step(8 + 11))])
        g = R.glyph(0, 0, 0, 0, 0)
        self.assertEqual(_row(log), ())
        ab = [a for a in log.refusals(Q.DOT_STAFF_POSITION, g)] \
            if hasattr(log, "refusals") else []
        self.assertTrue(ab)
        self.assertEqual(ab[-1].reason, ABSTAIN.OFF_STAFF)
        # a refusal says how close it came: steps past the cut-off, and the side
        self.assertGreater(ab[-1].detail["margin"], 0.0)
        self.assertEqual(ab[-1].detail["side"], "below")

    def test_an_unreadable_neighbour_staff_abstains_and_names_why(self):
        """A dot that stands on the NEXT staff, whose lines are not on the
        raster here: nothing can be read at its x, and the cell's own grid is
        not the staff it stands on -- so no row, an abstention."""
        blank = np.full((HEIGHT, WIDTH), 255, dtype=np.uint8)
        # two staves in the model; the dot is nearest the second
        second_top = 300.0
        pws = _pws(blank, [_staff(0, TOP), _staff(1, second_top)])
        log = Log()
        G.gather_dot_positions(
            log, pws, [_cell(0, TOP)], {0: (0, 0), 1: (0, 1)},
            {CELL.to_key(): [_Det("augmentationDot", 300,
                                  second_top + 30)]})
        g = R.glyph(0, 0, 0, 0, 0)
        self.assertEqual(log.rows(Q.DOT_STAFF_POSITION, g), ())
        ab = list(log.refusals(Q.DOT_STAFF_POSITION, g))
        self.assertTrue(ab)
        self.assertEqual(ab[-1].reason, ABSTAIN.NO_STAFF_GEOMETRY)

    def test_an_unreadable_raster_falls_back_to_the_bars_own_grid_and_says_so(
            self):
        blank = np.full((HEIGHT, WIDTH), 255, dtype=np.uint8)
        log = _run([_Det("augmentationDot", 300, _y_of_step(3))], img=blank)
        (r,) = _row(log)
        self.assertEqual(r.detail["basis"], "cell_grid")
        self.assertEqual(r.detail["step"], 3)

    def test_no_raster_and_no_cell_is_an_abstention(self):
        pws = types.SimpleNamespace(
            page=types.SimpleNamespace(binary=None, page_index=0),
            staves=[_staff(0, TOP)])
        log = Log()
        G.gather_dot_positions(log, pws, [], {0: (0, 0)},
                               {CELL.to_key(): [_Det("augmentationDot", 300,
                                                     _y_of_step(3))]})
        g = R.glyph(0, 0, 0, 0, 0)
        self.assertEqual(log.rows(Q.DOT_STAFF_POSITION, g), ())
        self.assertTrue(list(log.refusals(Q.DOT_STAFF_POSITION, g)))


class TestNearestStaff(unittest.TestCase):
    def test_a_dot_cut_into_one_strip_but_standing_on_the_next_staff(self):
        second_top = 300.0
        staves = ((0, TOP), (1, second_top))
        # step 3 of the SECOND staff, filed under the first staff's cell
        log = _run([_Det("augmentationDot", 300, _y_of_step(3, second_top))],
                   staves=staves)
        (r,) = _row(log)
        self.assertFalse(r.detail["home"])
        self.assertEqual(r.detail["staff"], R.staff(0, 0, 1).to_key())
        self.assertEqual((r.detail["step"], r.detail["on"]), (3, "space"))


class TestTheCaptureGapIsClosed(unittest.TestCase):
    def test_POSITION_dot_left_KNOWN_GAPS_and_the_quantity_is_declared(self):
        self.assertNotIn("POSITION dot", capture.KNOWN_GAPS)
        self.assertIn("DOT_STAFF_POSITION", capture.UNSCORED)
        self.assertEqual(capture.UNSCORED["DOT_STAFF_POSITION"][0],
                         capture.STAFF_GRID_POSITION)

    def test_RED_the_dot_role_decision_reads_the_dot_position(self):
        """The capture table credits a family with a position only where its
        DECIDING rule reads it (`wants`): `check`'s `UNREAD-POSITION` finding
        is this assertion failing."""
        row = next(r for r in capture.families()["rows"]
                   if r["family"] == "dot")
        self.assertIn("DOT_STAFF_POSITION", row["position"])
        self.assertEqual(row["position_declared_but_unread"], [])


# ─────────────────────────────────────────────────────────────────────────────
# ADJUDICATE: the join may use the position (`OMR_DOT_POSITION_JOIN`, OFF)
#
# The convention (docs/page-facts.md: a dot sits a space higher on a line
# note): an augmentation dot stands in a SPACE -- its note's own space, or the
# space above (usually) / below a line note's line. Never on a line.
# ─────────────────────────────────────────────────────────────────────────────

JOIN_SPACE = 16           # one staff space in the synthetic cell's frame
HOME = R.staff(0, 0, 0)
FLAG = {"OMR_DOT_POSITION_JOIN": "1"}


def _jlog():
    log = Log()
    log.observe(CELL, Q.CELL_STAFF_SPACE, float(JOIN_SPACE),
                reader=READERS.GEOMETRY, frame="cell:0")
    return log


def _head(log, gi, pos, x=100, cls="noteheadHalf"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (cls, x - 10, 0, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    if pos is not None:
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, float(pos),
                    reader=READERS.GEOMETRY, frame="cell:0")
    return g


def _dot(log, gi, *, x, y, pos=None, staff=HOME, w=4, h=8):
    d = R.glyph(0, 0, 0, 0, gi)
    log.observe(d, Q.GLYPH_BOX, ("augmentationDot", x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.8)
    log.observe(d, Q.AUG_DOT, (x + w / 2.0, y + h / 2.0),
                reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                detector_role="dot", detector_class="augmentationDot")
    if pos is not None:
        step = int(round(pos))
        log.observe(d, Q.DOT_STAFF_POSITION, float(pos),
                    reader=READERS.GEOMETRY, frame="cell:0", step=step,
                    on="line" if step % 2 == 0 else "space",
                    residual=abs(pos - step), margin=0.5 - abs(pos - step),
                    basis="local_ink", staff=staff.to_key(),
                    home=(staff == HOME))
    return d


def _role(log, gi):
    return log.verdict(Q.DOT_ROLE, R.glyph(0, 0, 0, 0, gi))


class TestTheJoinReadsTheDotPosition(unittest.TestCase):
    # a line note at step 4 (the middle line); its dot belongs at step 3
    # (the space above, dy +0.5 sp) or 5 (below, dy -0.5 sp)

    def test_RED_a_dot_in_the_space_above_a_line_note_is_that_notes_dot(self):
        log = _jlog()
        head = _head(log, 0, 4.0)
        _dot(log, 1, x=112, y=0, pos=3.0)          # centre y=4: 0.25 sp up
        with mock.patch.dict(os.environ, FLAG):
            adjudicate.run(log)
        role = _role(log, 1)
        self.assertEqual(role.value, "augmentation")
        self.assertEqual(role.detail["head"], head.to_key())
        self.assertEqual(log.verdict(Q.DURATION, head).value["dots"], 1)

    def test_RED_a_dot_on_a_line_beside_a_line_note_is_not_its_dot(self):
        """The box geometry says level with the head (it admits it); the ruler
        says the dot sits ON the line the note is on, which no augmentation
        dot does."""
        def run(env):
            log = _jlog()
            head = _head(log, 0, 4.0)
            _dot(log, 1, x=112, y=4, pos=4.0)       # centre y=8: dead level
            with mock.patch.dict(os.environ, env):
                adjudicate.run(log)
            return log, head
        log, head = run({})
        self.assertEqual(_role(log, 1).value, "augmentation")   # CONTROL: OFF
        log, head = run(FLAG)
        self.assertNotEqual(_role(log, 1).value, "augmentation")
        self.assertEqual(log.verdict(Q.DURATION, head).value["dots"], 0)

    def test_RED_a_dot_in_the_space_below_a_line_note_is_admitted(self):
        """0.5 sp BELOW the head centre is outside the 0.25 sp box window
        (2.127's near-miss); the ruler puts it in the space below the line
        the note is on, where a dot may stand."""
        def run(env):
            log = _jlog()
            head = _head(log, 0, 4.0)
            _dot(log, 1, x=112, y=12, pos=5.0)      # centre y=16
            with mock.patch.dict(os.environ, env):
                adjudicate.run(log)
            return log, head
        log, head = run({})
        self.assertEqual(_role(log, 1).outcome, Outcome.ABSTAINED)  # CONTROL
        log, head = run(FLAG)
        role = _role(log, 1)
        self.assertEqual(role.value, "augmentation")
        self.assertEqual(role.reason, "right_of_a_head_at_its_dot_step")
        self.assertEqual(role.detail["head"], head.to_key())
        self.assertEqual(log.verdict(Q.DURATION, head).value["dots"], 1)

    def test_a_space_note_takes_its_dot_in_its_own_space(self):
        log = _jlog()
        head = _head(log, 0, 3.0)
        _dot(log, 1, x=112, y=4, pos=3.0)
        with mock.patch.dict(os.environ, FLAG):
            adjudicate.run(log)
        self.assertEqual(_role(log, 1).value, "augmentation")
        self.assertEqual(log.verdict(Q.DURATION, head).value["dots"], 1)

    def test_a_dot_a_whole_space_off_a_space_note_is_not_its_dot(self):
        log = _jlog()
        _head(log, 0, 3.0)
        _dot(log, 1, x=112, y=4, pos=1.0)          # two steps up
        with mock.patch.dict(os.environ, FLAG):
            adjudicate.run(log)
        self.assertNotEqual(_role(log, 1).value, "augmentation")

    def test_CANNOT_TELL_leaves_the_box_geometry_alone(self):
        """No position row, a dot measured against another staff, a reading
        on the line/space boundary: each is `unknown`, never a veto."""
        cases = {
            "no position row": dict(pos=None),
            "another staff": dict(pos=4.0, staff=R.staff(0, 0, 1)),
            "on the boundary": dict(pos=3.75),   # 0.25 from the line: unclear
        }
        for name, kw in cases.items():
            with self.subTest(name):
                log = _jlog()
                _head(log, 0, 4.0)
                _dot(log, 1, x=112, y=4, **kw)
                with mock.patch.dict(os.environ, FLAG):
                    adjudicate.run(log)
                self.assertEqual(_role(log, 1).value, "augmentation")

    def test_a_head_far_off_the_five_lines_is_unknown(self):
        log = _jlog()
        _head(log, 0, -9.0)
        _dot(log, 1, x=112, y=4, pos=-9.0)      # "on a line" at step -9
        with mock.patch.dict(os.environ, FLAG):
            adjudicate.run(log)
        self.assertEqual(_role(log, 1).value, "augmentation")

    def test_a_ledger_line_head_is_read_like_any_line_head(self):
        """A note on the first ledger line (step -2) takes its dot in the space
        above (-3), never on the ledger line."""
        def role(dot_pos):
            log = _jlog()
            _head(log, 0, -2.0)
            _dot(log, 1, x=112, y=4, pos=dot_pos)
            with mock.patch.dict(os.environ, FLAG):
                adjudicate.run(log)
            return _role(log, 1).value
        self.assertEqual(role(-3.0), "augmentation")
        self.assertNotEqual(role(-2.0), "augmentation")

    def test_two_heads_that_fit_leave_the_dot_unplaced(self):
        """A chord of seconds shares the space between its heads: the dot at
        step 3 stands at the line note's step-1 AND the space note's own
        step. Nothing here says whose, so nothing is admitted."""
        log = _jlog()
        _head(log, 0, 4.0, x=100)
        _head(log, 1, 3.0, x=118)                    # the other side of the stem
        _dot(log, 2, x=140, y=12, pos=3.0)           # outside the box window
        with mock.patch.dict(os.environ, FLAG):
            adjudicate.run(log)
        self.assertNotEqual(_role(log, 2).value, "augmentation")

    def test_FLAG_OFF_is_byte_for_byte_the_box_window(self):
        for pos in (3.0, 4.0, 5.0, None):
            log_off, log_none = _jlog(), _jlog()
            for lg in (log_off, log_none):
                _head(lg, 0, 4.0)
            _dot(log_off, 1, x=112, y=4, pos=pos)
            _dot(log_none, 1, x=112, y=4, pos=None)
            adjudicate.run(log_off)
            adjudicate.run(log_none)
            self.assertEqual(_role(log_off, 1).value,
                             _role(log_none, 1).value, pos)



class TestTile1AReadingNearTheLineIsNotAVeto(unittest.TestCase):
    """Sean, 2026-10-14, tile 1 of `out/print/2.128-review`: the note in the red
    corners (Brahms 317803 `glyph/0/0/3/1/1`, a top-line head, step -0.04) IS a
    dotted quarter. Its dot (`glyph/0/0/3/1/6`) was measured at step -1.69 --
    0.31 steps below the ledger line above the head, i.e. IN the space above
    it -- and the first cut, which rounded that to the line at -2, vetoed it.
    Sean, same day: a dot is *"Always in a space"*, so only a reading CLEARLY
    on a line may refuse one."""

    def _role(self, dot_pos, head_pos=-0.04):
        log = _jlog()
        head = _head(log, 0, head_pos)
        _dot(log, 1, x=112, y=4, pos=dot_pos)
        with mock.patch.dict(os.environ, FLAG):
            adjudicate.run(log)
        return _role(log, 1), head

    def test_RED_tile_1_s_real_numbers_keep_the_dot(self):
        role, head = self._role(-1.6886178861788677)
        self.assertEqual(role.value, "augmentation")
        self.assertEqual(role.detail["head"], head.to_key())

    def test_a_reading_between_line_and_space_never_vetoes(self):
        for pos in (-1.75, -1.72, -2.25, -2.28):
            with self.subTest(pos):
                role, _h = self._role(pos)
                self.assertEqual(role.value, "augmentation")

    def test_CONTROL_a_reading_clearly_on_the_line_still_vetoes(self):
        for pos in (-2.0, -1.9, -2.15):
            with self.subTest(pos):
                role, _h = self._role(pos)
                self.assertNotEqual(role.value, "augmentation")

    def test_the_cell_classification(self):
        from tools.omr.staged.adjudicators import aug_dot_join as AJ
        self.assertEqual(AJ._dot_cell(-1.69), ("space", -1))
        self.assertEqual(AJ._dot_cell(0.597), ("space", 1))
        self.assertEqual(AJ._dot_cell(4.0), ("line", 4))
        self.assertEqual(AJ._dot_cell(3.75)[0], "unclear")



if __name__ == "__main__":
    unittest.main()
