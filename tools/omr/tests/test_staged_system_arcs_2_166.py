"""ROADMAP 2.166 -- arcs read ONCE per staff across the SYSTEM on page pixels, then ONLY their own stroke erased
(STAGED GATHER `arcs_system.gather_system_arcs` -> `Q.SYSTEM_ARC`; flag `OMR_SYSTEM_ARCS`, default OFF).

Sean 2026-10-17: "Can we treat arcs the way we treat hairpins - taking into account the system or page view and then
erasing them?" / "Open the system level arc".

CONVENTION ASSUMED: an arc's stroke is one thin run per column, smooth from column to column; a head, stem, barline or
accidental is taller than a stroke where the arc meets it. WHAT WOULD FALSIFY IT: a head, rest, dot or accidental
Sean values losing ink to the erase. NOT CONFIRMED: the cut-offs are set on two plates only.

Each guarded test has a MUTATION twin that removes the guard and asserts the property then FAILS, so a test that
passes whatever the code does cannot pass here (CLAUDE.md rule 7).
"""
from __future__ import annotations

import os
import types
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import arcs_system as AS
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q

ON = {AS.ENV: "1"}
SP = 20                         # page px per staff space
LINES = [100, 120, 140, 160, 180]
BARLINE_X = 200


# ── a synthetic page: one staff, two bars, a barline at x = 200 (0 = ink) ─────────────────────────────────────────

def _blank():
    return np.full((300, 400), 255, np.uint8)


def _lines(img):
    for y in LINES:
        img[y - 1:y + 2, :] = 0


def _barline(img):
    img[LINES[0] - 1:LINES[-1] + 2, BARLINE_X - 1:BARLINE_X + 2] = 0


def _head(img, cx, cy, hollow=False):
    yy, xx = np.ogrid[:img.shape[0], :img.shape[1]]
    r = ((xx - cx) / 12.0) ** 2 + ((yy - cy) / 9.0) ** 2
    m = r <= 1.0
    if hollow:
        m &= ((xx - cx) / 9.0) ** 2 + ((yy - cy) / 6.0) ** 2 > 1.0
    img[m] = 0


def _arc(img, x0, x1, y_end, sag, t=5):
    """An arc under its notes: ends at `y_end`, its middle `sag` px lower, `t` px thick."""
    mx, hw = (x0 + x1) / 2.0, (x1 - x0) / 2.0
    for x in range(x0, x1 + 1):
        y = y_end + sag * (1.0 - ((x - mx) / hw) ** 2)
        img[int(round(y)):int(round(y)) + t, x] = 0


def _hairpin(img, x0, x1, y_mid, open_px):
    for x in range(x0, x1 + 1):
        d = int(round(open_px * (x - x0) / float(x1 - x0)))
        img[y_mid - d:y_mid - d + 2, x] = 0
        img[y_mid + d:y_mid + d + 2, x] = 0


def _det(name, box, cell_x0):
    x0, y0, x1, y1 = box
    return types.SimpleNamespace(smufl_name=name, x_canonical=x0 - cell_x0, y_canonical=y0 - 40,
                                 width_canonical=x1 - x0, height_canonical=y1 - y0, confidence=0.6)


def _setup(draw, dets_by_cell):
    """`draw(img)` paints the music (no staff lines); returns pws, cells, local, detections."""
    music = _blank()
    draw(music)
    page = music.copy()
    _lines(page)
    cells = []
    for m, (x0, x1) in enumerate(((0, BARLINE_X), (BARLINE_X, 400))):
        cells.append(types.SimpleNamespace(
            page_index=0, staff_index=0, system_index=0, measure_index=m, bbox_page_px=(x0, 40, x1, 240),
            upscale_factor=1.0, staff_line_ys_canonical=[y - 40 for y in LINES],
            image=page[40:240, x0:x1].copy(), image_no_staff=music[40:240, x0:x1].copy()))
    pws = types.SimpleNamespace(page=types.SimpleNamespace(binary=page, page_index=0), staves=[])
    local = {0: (0, 0)}
    detections = {R.cell(0, 0, 0, m).to_key(): [_det(n, b, cells[m].bbox_page_px[0]) for n, b in dets]
                  for m, dets in dets_by_cell.items()}
    return pws, cells, local, detections


def _run(pws, cells, local, detections, env=ON):
    log = Log()
    with mock.patch.dict(os.environ, env):
        summary = AS.gather_system_arcs(log, pws, cells, local, detections)
    return log, summary


def _ink(cell, box):
    """Ink pixels of a cell's (possibly erased) raster inside a PAGE box."""
    x0, y0 = cell.bbox_page_px[0], cell.bbox_page_px[1]
    b = [int(box[0] - x0), int(box[1] - y0), int(box[2] - x0), int(box[3] - y0)]
    return int((cell.image_no_staff[max(0, b[1]):b[3], max(0, b[0]):b[2]] < 128).sum())


# ── the tie cut at a barline ───────────────────────────────────────────────────────────────────────────────────────

HEAD_A = (150, 150)            # in the space between lines 140 and 160
HEAD_B = (250, 150)
A_BOX = (138, 141, 162, 159)
B_BOX = (238, 141, 262, 159)


def _tie_page(tail_as_head=False):
    def draw(img):
        _head(img, *HEAD_A)
        _head(img, *HEAD_B)
        _arc(img, 156, 244, 160, 10)
        _barline(img)
    cell0 = [("noteheadBlackInSpace", A_BOX), ("tie", (156, 160, 199, 176))]
    cell1 = [("noteheadBlackInSpace", B_BOX)]
    if tail_as_head:
        # 2.164: the crop cut the tie; its tail at the bar's left edge is boxed as a head, no arc box in this bar
        cell1.append(("noteheadHalfOnLine", (203, 160, 226, 176)))
    else:
        cell1.append(("tie", (201, 160, 244, 176)))
    return _setup(draw, {0: cell0, 1: cell1})


class TestTieCutAtBarline(unittest.TestCase):

    def _rows(self, log):
        return [r for r in log.to_json()["observations"] if r["quantity"] == Q.SYSTEM_ARC]

    def test_a_tie_cut_at_a_barline_is_read_as_ONE_arc(self):
        log, summary = _run(*_tie_page())
        rows = self._rows(log)
        self.assertEqual(len(rows), 1, rows)
        d = rows[0]["detail"]
        self.assertEqual(d["cells"], [0, 1])
        self.assertEqual(len(d["pieces"]), 2)
        self.assertTrue(d["cut_at_barline"])
        self.assertEqual(rows[0]["value"], "two_heads_one_position_adjacent")
        self.assertEqual(d["anchor_left"], R.glyph(0, 0, 0, 0, 0).to_key())
        self.assertEqual(d["anchor_right"], R.glyph(0, 0, 0, 1, 0).to_key())
        self.assertEqual(summary["joined_across_barline"], 1)

    def test_MUTATION_without_the_join_the_two_pieces_are_two_arcs(self):
        with mock.patch.object(AS, "same_curve", lambda a, b, sp: False):
            log, _ = _run(*_tie_page())
        self.assertEqual(len(self._rows(log)), 2)

    def test_the_tail_boxed_as_a_head_is_stroke_only_and_its_ink_is_erased(self):
        pws, cells, local, dets = _tie_page(tail_as_head=True)
        tail = (203, 160, 226, 176)
        before = _ink(cells[1], tail)
        log, summary = _run(pws, cells, local, dets)
        self.assertIn(R.glyph(0, 0, 0, 1, 1).to_key(), summary["stroke_only_heads"])
        self.assertGreater(before, 50)
        self.assertLess(_ink(cells[1], tail), 0.1 * before)
        # the trace ran past the cut box into the next bar and anchored on the real head there
        row = self._rows(log)[0]
        self.assertEqual(row["detail"]["anchor_right"], R.glyph(0, 0, 0, 1, 0).to_key())

    def test_MUTATION_with_every_head_box_protected_the_tail_keeps_its_ink(self):
        pws, cells, local, dets = _tie_page(tail_as_head=True)
        tail = (203, 160, 226, 176)
        before = _ink(cells[1], tail)
        with mock.patch.object(AS, "STROKE_ONLY_RESIDUAL_SPACES2", -1.0):
            _run(pws, cells, local, dets)
        self.assertEqual(_ink(cells[1], tail), before)

    def test_CONTROL_flag_off_files_nothing_and_erases_nothing(self):
        pws, cells, local, dets = _tie_page()
        snap = [c.image_no_staff.copy() for c in cells]
        log, summary = _run(pws, cells, local, dets, env={AS.ENV: "0"})
        self.assertEqual(summary, {})
        self.assertEqual(self._rows(log), [])
        for c, s in zip(cells, snap):
            self.assertTrue(np.array_equal(c.image_no_staff, s))

    def test_the_detectors_image_is_never_touched(self):
        pws, cells, local, dets = _tie_page()
        snap = [c.image.copy() for c in cells]
        page = pws.page.binary.copy()
        _run(pws, cells, local, dets)
        for c, s in zip(cells, snap):
            self.assertTrue(np.array_equal(c.image, s))
        self.assertTrue(np.array_equal(pws.page.binary, page))
        self.assertIsNotNone(cells[0].image_no_staff_with_arcs)

    def test_flag_is_off_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(AS.ENV, None)
            self.assertFalse(AS.enabled())


# ── erasing never takes a touched head's ink ─────────────────────────────────────────────────────────────────────────

def _touch_page(hollow, boxed):
    """A slur in bar 0 whose right end runs INTO a head (its stroke touches the head's outline)."""
    def draw(img):
        _head(img, 60, 150)
        _head(img, 150, 150, hollow=hollow)
        _arc(img, 66, 150, 158, 10)
    head_box = (138, 141, 162, 159)
    dets = [("noteheadBlackInSpace", (48, 141, 72, 159)), ("slur", (66, 158, 146, 174))]
    if boxed:
        dets.append(("noteheadHalfInSpace" if hollow else "noteheadBlackInSpace", head_box))
    return _setup(draw, {0: dets, 1: []}), head_box


class TestTouchedHeadIntact(unittest.TestCase):

    def _head_ink(self, hollow, boxed, patch=None):
        (pws, cells, local, dets), head_box = _touch_page(hollow, boxed)
        before = _ink(cells[0], head_box)
        if patch:
            with mock.patch.object(AS, patch[0], patch[1]):
                _, summary = _run(pws, cells, local, dets)
        else:
            _, summary = _run(pws, cells, local, dets)
        self.assertGreater(summary["erased_px"], 0)        # the slur itself WAS erased
        return before, _ink(cells[0], head_box)

    def test_a_hollow_head_the_slur_touches_keeps_every_pixel(self):
        before, after = self._head_ink(hollow=True, boxed=True)
        self.assertEqual(after, before)

    def test_MUTATION_hollow_head_unprotected_loses_ink(self):
        before, after = self._head_ink(hollow=True, boxed=True, patch=("is_protected_class", lambda n: False))
        self.assertLess(after, before)

    def test_an_UNBOXED_filled_head_the_slur_runs_into_keeps_every_pixel(self):
        """No box protects it: the run through it is taller than a stroke, so it is kept whole."""
        before, after = self._head_ink(hollow=False, boxed=False)
        self.assertEqual(after, before)

    def test_MUTATION_box_erase_takes_the_unboxed_heads_ink(self):
        """The guard is the TRACE: only the thin, continuous stroke is erased, never every run in the arc's box."""
        (pws, cells, local, dets), head_box = _touch_page(hollow=False, boxed=False)
        before = _ink(cells[0], head_box)
        with mock.patch.object(AS, "trace_arc", _box_trace(AS.trace_arc)), \
                mock.patch.object(AS, "run_is_stroke", lambda s, e, lo, hi, slack, m: True):
            _run(pws, cells, local, dets)
        self.assertLess(_ink(cells[0], head_box), before)


def _box_trace(real):
    """The box-erase trap (hairpin-cv FINDINGS §5) as a stand-in tracer: every ink run in the arc's box is "the arc"."""
    def box_trace(ink, box, sp, **k):
        t = real(ink, box, sp, **k)
        x0, y0, x1, y1 = (int(v) for v in box)
        for x in range(x0, x1 + 1):
            for a, b in AS._runs(ink[y0:y1 + 1, x]):
                old = t["points"].get(x)
                t["points"][x] = (a + y0, b + y0) if old is None else (min(old[0], a + y0), max(old[1], b + y0))
        return t
    return box_trace


# ── a hairpin under an arc's box survives ────────────────────────────────────────────────────────────────────────────

def _hairpin_page(boxed_hairpin):
    """A slur over bar 0 and, INSIDE the slur's box (its rows padded as the detector pads them), a hairpin."""
    def draw(img):
        _head(img, 40, 130)
        _head(img, 170, 130)
        _arc(img, 46, 164, 122, -14)          # an arc OVER its notes (its middle 14 px higher)
        _hairpin(img, 70, 140, 125, 6)        # a small hairpin under the arc's middle, in its box
    dets = [("noteheadBlackInSpace", (28, 121, 52, 139)), ("noteheadBlackInSpace", (158, 121, 182, 139)),
            ("slur", (46, 104, 164, 134))]
    if boxed_hairpin:
        dets.append(("dynamicCrescendoHairpin", (70, 118, 141, 133)))
    return _setup(draw, {0: dets, 1: []})


HAIRPIN_BOX = (70, 118, 141, 133)


class TestHairpinUnderArcSurvives(unittest.TestCase):

    def _hairpin_ink(self, boxed, mutate=False):
        pws, cells, local, dets = _hairpin_page(boxed)
        before = _ink(cells[0], HAIRPIN_BOX)
        if mutate:
            with mock.patch.object(AS, "trace_arc", _box_trace(AS.trace_arc)), \
                    mock.patch.object(AS, "is_protected_class", lambda n: False):
                _, summary = _run(pws, cells, local, dets)
        else:
            _, summary = _run(pws, cells, local, dets)
        self.assertGreater(summary["erased_px"], 0)
        return before, _ink(cells[0], HAIRPIN_BOX), summary

    def test_an_unboxed_hairpin_inside_the_arcs_box_keeps_its_ink(self):
        before, after, summary = self._hairpin_ink(boxed=False)
        self.assertGreater(before, 100)
        # only the arc's own stroke left the hairpin's rectangle (the arc passes over its top edge): the lines stay
        self.assertGreaterEqual(after, before - 10, summary)

    def test_a_boxed_hairpin_inside_the_arcs_box_keeps_every_pixel(self):
        before, after, _ = self._hairpin_ink(boxed=True)
        self.assertEqual(after, before)

    def test_MUTATION_box_erase_wipes_the_hairpin(self):
        before, after, _ = self._hairpin_ink(boxed=False, mutate=True)
        self.assertLess(after, 0.5 * before)


class TestPureHelpers(unittest.TestCase):

    def test_runs(self):
        self.assertEqual(AS._runs(np.array([0, 1, 1, 0, 1], bool)), [(1, 2), (4, 4)])
        self.assertEqual(AS._runs(np.zeros(4, bool)), [])

    def test_trace_declines_without_a_unit_or_raster(self):
        self.assertIsNone(AS.trace_arc(None, (0, 0, 5, 5), SP, x_min=0, x_max=5))
        self.assertIsNone(AS.trace_arc(np.zeros((10, 10), bool), (0, 0, 5, 5), 0, x_min=0, x_max=5))

    def test_no_raster_abstains_per_piece(self):
        pws, cells, local, dets = _tie_page()
        pws.page.binary = None
        log, summary = _run(pws, cells, local, dets)
        ab = [a for a in log.to_json()["abstentions"] if a["quantity"] == Q.SYSTEM_ARC]
        self.assertEqual(len(ab), 2)


if __name__ == "__main__":
    unittest.main()


# ── Sean's tile 11 (2026-10-17): "Tie on one side of the barline and a slur on the other. The blue line swaps arcs." ──

_T11 = os.path.join(os.path.dirname(__file__), "data", "system_arc_tile11.npz")


def _tile11():
    z = np.load(_T11)
    shape = tuple(int(v) for v in z["shape"])
    n = shape[0] * shape[1]
    ink = np.unpackbits(z["composite"])[:n].reshape(shape).astype(bool)
    raw = np.unpackbits(z["raw"])[:n].reshape(shape).astype(bool)
    sp = float(z["sp"])
    box = [float(v) for v in z["arcs"][0][:4]]
    return ink, raw, sp, box


def _trace11():
    ink, raw, sp, box = _tile11()
    return AS.trace_arc(ink, box, sp, x_min=box[0] - AS.CUT_EXTEND_SPACES * sp,
                        x_max=box[2] + AS.FREE_EXTEND_SPACES * sp, raw=raw)


def _y_at(t, x):
    near = min(t["points"], key=lambda v: abs(v - x))
    return sum(t["points"][near]) / 2.0


class TestTile11TheStrokeContinues(unittest.TestCase):
    """Brahms 317803 pdf 1, `glyph/1/1/11/1/21`: the tie in bar 1 is cut at the barline (crop x 187); in bar 0 its
    other half (y ~157 at x 175) runs just above the SLUR (y ~170) and the two touch near the barline. Our trace
    took the touching blob's centre and walked on along the slur."""

    def test_the_trace_stays_on_the_tie_past_the_barline(self):
        t = _trace11()
        self.assertLess(t["x0"], 150)                      # it does cross the barline into bar 0
        self.assertLess(_y_at(t, 175), 162, t["x0"])       # ... on the tie (~157), not the slur (~170)
        self.assertLess(_y_at(t, 140), 155)                # and keeps rising toward the tied head

    def test_MUTATION_without_the_thickness_guard_the_trace_swaps_onto_the_slur(self):
        with mock.patch.object(AS, "THICK_CONTINUE_FACTOR", 100.0):
            t = _trace11()
        self.assertGreater(_y_at(t, 175), 165)


def _piece(x0, x1, y_at_x0, slope, t=4):
    pts = {x: (int(round(y_at_x0 + slope * (x - x0))), int(round(y_at_x0 + slope * (x - x0))) + t)
           for x in range(x0, x1 + 1)}
    return AS._finish(pts, 1.0)


class TestEndJoinNeedsTheTangentToContinue(unittest.TestCase):

    def test_a_falling_end_does_not_join_a_rising_start_at_one_height(self):
        left = _piece(0, 60, 70, +0.5)                 # ends at ~100, still falling
        right = _piece(70, 130, 101, -0.5)             # starts at ~101, rising: a different arc turning away
        self.assertIsNone(AS.end_join_cost(left, right, SP))
        self.assertEqual(len(AS.join_traces([left, right], SP)), 2)

    def test_MUTATION_without_the_tangent_test_they_join(self):
        left = _piece(0, 60, 70, +0.5)
        right = _piece(70, 130, 101, -0.5)
        with mock.patch.object(AS, "END_JOIN_SLOPE", 10.0), mock.patch.object(AS, "END_JOIN_Y_SPACES", 10.0):
            self.assertEqual(len(AS.join_traces([left, right], SP)), 1)

    def test_CONTROL_a_continuing_end_joins(self):
        left = _piece(0, 60, 70, +0.2)
        right = _piece(68, 130, 70 + 0.2 * 68, +0.2)
        self.assertEqual(len(AS.join_traces([left, right], SP)), 1)

    def test_each_end_takes_only_the_piece_that_continues_it_best(self):
        left = _piece(0, 60, 70, 0.0)
        good = _piece(68, 130, 70, 0.0)
        worse = _piece(66, 120, 75, 0.1)                # also within tolerance, but continues it less well
        groups = AS.join_traces([left, good, worse], SP)
        self.assertIn(sorted([0, 1]), [sorted(g) for g in groups])
        self.assertIn([2], groups)


# ── Brahms 317803 pdf 1, cell 1/0/0/0: an erase up to a merge left a straight bar the beam reader read as a beam ─────

def _merge_page():
    """A slur over bar 0 with a short straight dash fused to the underside of its middle."""
    def draw(img):
        _head(img, 40, 130)
        _head(img, 170, 130)
        _arc(img, 46, 164, 122, -14, t=5)
        img[113:119, 92:122] = 0                         # the dash, merged with the arc's middle (~y 108-113)
    dets = [("noteheadBlackInSpace", (28, 121, 52, 139)), ("noteheadBlackInSpace", (158, 121, 182, 139)),
            ("slur", (46, 104, 164, 124))]
    return _setup(draw, {0: dets, 1: []})


class TestEraseKeepsClearOfAMerge(unittest.TestCase):
    NEAR = (82, 100, 132, 125)                           # the dash and a half space of arc either side

    def _near_ink(self, patch=None):
        pws, cells, local, dets = _merge_page()
        before = _ink(cells[0], self.NEAR)
        if patch:
            with mock.patch.object(AS, patch[0], patch[1]):
                _, summary = _run(pws, cells, local, dets)
        else:
            _, summary = _run(pws, cells, local, dets)
        self.assertGreater(summary["erased_px"], 0)      # the rest of the slur WAS erased
        return before, _ink(cells[0], self.NEAR)

    def test_the_arc_beside_a_merge_is_left_whole(self):
        before, after = self._near_ink()
        self.assertEqual(after, before)

    def test_MUTATION_without_the_keep_clear_the_arc_beside_the_merge_is_erased(self):
        before, after = self._near_ink(patch=("MERGE_KEEP_SPACES", 0.0))
        self.assertLess(after, before)
