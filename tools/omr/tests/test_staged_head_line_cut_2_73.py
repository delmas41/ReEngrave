"""ROADMAP 2.73 -- a hollow head CUT BY A LINE, and the keep choice between
boxes on one head. PATH: STAGED, GATHER + ADJUDICATE only.

Sean (2026-10-09): *"half notes, especially ones that are on lines or ledger
lines, get split up into two smaller boxes instead of one large box around the
notehead. I think the way the boxes are automatically choosing the hollow note
heads is off."* Measured against his 27 hand-labelled half heads
(`benchmarks/omr-head-fill-2026-09/FINDINGS.md` Sec.8).

Layers, each with a positive control in the same class (a refusal test that
cannot fail passes by refusing everything):

  A. `gather.head_cut_by_line` -- the PURE reading, on painted rings.
  B. `gather.gather_head_line_cut` / `gather_notehead_positions` /
     `gather_notehead_ink` -- the reading wired into a Log.
  C. `notehead_precision` -- `head_cut_piece`, and the two keep choices
     (2.30, 2.42) that now put the head's shape before its ink.
  D. `rhythm._ink_reads_decisively_hollow` -- the hollow cut, off the line.

⚠️ RUN RED FIRST against the unrepaired tree (`HEAD` before this commit): A, B
raise `AttributeError` (`gather.head_cut_by_line`, `Q.HEAD_LINE_CUT`), C's
`head_cut_piece`/octave/shape tests FAIL on the old keep choices, D's centre
0.7 reads not-hollow. NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md
6c).
"""

from __future__ import annotations

import math
import types
import unittest

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.types import MeasureCell

from tools.omr.tests.test_staged_notehead_precision import (
    CELL, _cell_geometry, _notehead)

S = 40.0                      # staff space, canonical px
HEAD_W, HEAD_H = 1.4 * S, 1.1 * S


# ─────────────────────────────────────────────────────────────────────────────
# painted rings
# ─────────────────────────────────────────────────────────────────────────────


def _paper(h=300, w=300):
    return np.full((h, w), 255, np.uint8)


def _ring_head(img, cx, cy, *, hole=True, tilt_deg=30.0, ink_fill=False):
    """A notehead centred on (cx, cy): an ellipse 1.4 x 1.1 sp; a TILTED white
    ellipse hole (the engraved half note's) unless `ink_fill` (a black head)."""
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    a, b = HEAD_W / 2.0, HEAD_H / 2.0
    outer = ((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2 <= 1.0
    img[outer] = 0
    if hole and not ink_fill:
        t = math.radians(tilt_deg)
        dx, dy = xx - cx, -(yy - cy)
        u = dx * math.cos(t) + dy * math.sin(t)
        v = -dx * math.sin(t) + dy * math.cos(t)
        img[(u / (0.42 * S)) ** 2 + (v / (0.20 * S)) ** 2 <= 1.0] = 255


def _line(img, y, cx, half=1.0 * S, thick=4):
    img[int(y - thick // 2):int(y + (thick + 1) // 2),
        int(cx - half):int(cx + half)] = 0


def _head_on_line(cx=150.0, cy=150.0, **kw):
    img = _paper()
    _ring_head(img, cx, cy, **kw)
    _line(img, cy, cx)
    return img, cx, cy


def _lower_half_box(cx, cy):
    """The detector's partial box: the lower half-ring, top edge ON the line."""
    return (cx - HEAD_W / 2.0, cy - 2.0, cx + HEAD_W / 2.0, cy + 0.6 * S)


def _upper_half_box(cx, cy):
    return (cx - HEAD_W / 2.0, cy - 0.6 * S, cx + HEAD_W / 2.0, cy + 2.0)


# ─────────────────────────────────────────────────────────────────────────────
# A. the pure reading
# ─────────────────────────────────────────────────────────────────────────────


class TestHeadCutByLinePure(unittest.TestCase):

    def test_a_ring_cut_by_a_line_is_found_from_its_lower_half_box(self):
        img, cx, cy = _head_on_line()
        cut = gather.head_cut_by_line(img == 0, _lower_half_box(cx, cy), S)
        self.assertIsNotNone(cut)
        self.assertAlmostEqual(cut["line_y"], cy, delta=3.0)
        self.assertAlmostEqual(cut["cx"], cx, delta=0.2 * S)
        self.assertEqual(cut["edge"], "top")
        self.assertEqual(len(cut["holes"]), 2)

    def test_and_from_its_upper_half_box(self):
        img, cx, cy = _head_on_line()
        cut = gather.head_cut_by_line(img == 0, _upper_half_box(cx, cy), S)
        self.assertIsNotNone(cut)
        self.assertAlmostEqual(cut["line_y"], cy, delta=3.0)
        self.assertEqual(cut["edge"], "bottom")

    def test_a_dotted_head_with_a_dot_beside_the_line_still_reads(self):
        """A dot to the right of the head (standing on the line's own rows) is
        ink on one side of the line: the longer side still reads the line."""
        img, cx, cy = _head_on_line()
        img[int(cy) - 4:int(cy) + 5, int(cx + 0.85 * S):int(cx + 1.0 * S)] = 0
        self.assertIsNotNone(
            gather.head_cut_by_line(img == 0, _lower_half_box(cx, cy), S))

    # --- the controls: each is a head that must NOT be rebuilt -------------

    def test_CONTROL_a_hollow_head_in_a_space_has_one_hole_and_no_row(self):
        """Same ring, same hole, NO line through it: one hole. A half box of it
        (its lower half) must not be rebuilt -- the head is in the space."""
        img = _paper()
        _ring_head(img, 150.0, 150.0)
        self.assertIsNone(
            gather.head_cut_by_line(img == 0, _lower_half_box(150.0, 150.0), S))

    def test_CONTROL_a_black_head_with_a_line_through_it_is_not_a_cut_ring(self):
        img = _paper()
        _ring_head(img, 150.0, 150.0, ink_fill=True)
        _line(img, 150.0, 150.0)
        self.assertIsNone(
            gather.head_cut_by_line(img == 0, _lower_half_box(150.0, 150.0), S))

    def test_CONTROL_a_head_sized_box_is_never_a_candidate(self):
        img, cx, cy = _head_on_line()
        whole = (cx - HEAD_W / 2.0, cy - HEAD_H / 2.0,
                 cx + HEAD_W / 2.0, cy + HEAD_H / 2.0)
        self.assertIsNone(gather.head_cut_by_line(img == 0, whole, S))

    def test_CONTROL_a_box_whose_edge_is_not_on_the_line_is_not_rebuilt(self):
        """The ring IS cut, but this box is a piece of ink a space away: its
        edge stands 0.9 sp off the line."""
        img, cx, cy = _head_on_line()
        far = (cx - HEAD_W / 2.0, cy + 0.9 * S, cx + HEAD_W / 2.0,
               cy + 1.5 * S)
        self.assertIsNone(gather.head_cut_by_line(img == 0, far, S))

    def test_CONTROL_two_holes_with_no_line_between_them_are_not_a_cut_head(self):
        """A slash through the hole makes two holes too, but no line runs past
        the head on the slash's row: a tremolo is not a ledger line."""
        img = _paper()
        _ring_head(img, 150.0, 150.0)
        img[148:153, int(150 - 0.5 * S):int(150 + 0.5 * S)] = 0   # short bar
        self.assertIsNone(
            gather.head_cut_by_line(img == 0, _lower_half_box(150.0, 150.0), S))

    def test_CONTROL_a_chord_second_is_not_one_cut_head(self):
        """Two real hollow heads a half-space apart, each a whole box: neither
        box is half a head, so neither is a candidate."""
        img = _paper()
        _ring_head(img, 150.0, 130.0)
        _ring_head(img, 150.0, 150.0)
        for cy in (130.0, 150.0):
            whole = (150 - HEAD_W / 2.0, cy - HEAD_H / 2.0,
                     150 + HEAD_W / 2.0, cy + HEAD_H / 2.0)
            self.assertIsNone(gather.head_cut_by_line(img == 0, whole, S))


# ─────────────────────────────────────────────────────────────────────────────
# B. the reading, wired
# ─────────────────────────────────────────────────────────────────────────────


def _detection(name, box):
    x0, y0, x1, y1 = box
    return types.SimpleNamespace(
        smufl_name=name, x_canonical=x0, y_canonical=y0,
        width_canonical=x1 - x0, height_canonical=y1 - y0,
        x_center=(x0 + x1) / 2.0, y_center=(y0 + y1) / 2.0)


# staff lines 100..260 step 40; a ledger-free head ON the middle line (180)
LINES = (100.0, 140.0, 180.0, 220.0, 260.0)


def _cell_of(img):
    cell = MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img, bbox_page_px=(0, 0, 300, 300),
        staff_line_ys_canonical=list(LINES), upscale_factor=1.0)
    cell.__dict__["binary"] = img
    return cell


class TestTheReadingIsFiledAndConnected(unittest.TestCase):

    def _gather(self, img, dets):
        cell = _cell_of(img)
        sub = R.cell(0, 0, 0, 0)
        log = Log()
        det = {sub.to_key(): dets}
        gather.gather_head_line_cut(log, [cell], {0: (0, 0)}, det)
        gather.gather_notehead_positions(log, [cell], {0: (0, 0)}, det)
        gather.gather_notehead_ink(log, [cell], {0: (0, 0)}, det)
        return log

    def _staff_head(self, cy=180.0, **kw):
        img, cx, cy = _head_on_line(cy=cy, **kw)
        return img, cx, cy

    def test_the_piece_files_a_row_and_its_position_is_the_line(self):
        img, cx, cy = self._staff_head(180.0)
        box = _lower_half_box(cx, cy)
        log = self._gather(img, [_detection("noteheadHalfInSpace", box)])
        g = R.glyph(0, 0, 0, 0, 0)
        rows = log.rows(Q.HEAD_LINE_CUT, g)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].reader, READERS.CV_HEAD_LINE_CUT)
        self.assertEqual(rows[0].detail["line_half_step"], 4)   # line 3 of 5
        pos = log.rows(Q.NOTEHEAD_STAFF_POSITION, g)[-1]
        self.assertAlmostEqual(float(pos.value), 4.0, delta=0.08)
        self.assertEqual(pos.detail["from_head_cut"], rows[0].id)

    def test_without_the_reading_the_position_is_the_detector_centre(self):
        """The control: the box's own centre (a space's worth off the line)
        stands when no row exists -- the move is the row's, not a global
        shift."""
        img = _paper()
        _ring_head(img, 150.0, 180.0)          # no line: one hole, in place
        box = _lower_half_box(150.0, 180.0)
        log = self._gather(img, [_detection("noteheadHalfInSpace", box)])
        g = R.glyph(0, 0, 0, 0, 0)
        self.assertEqual(len(log.rows(Q.HEAD_LINE_CUT, g)), 0)
        pos = log.rows(Q.NOTEHEAD_STAFF_POSITION, g)[-1]
        det_centre = ((box[1] + box[3]) / 2.0 - LINES[0]) / 20.0
        self.assertAlmostEqual(float(pos.value), det_centre, delta=1e-6)
        self.assertNotIn("from_head_cut", pos.detail or {})

    def test_the_detector_box_is_left_alone_on_the_record_only_a_row_is_added(self):
        img, cx, cy = self._staff_head(180.0)
        log = self._gather(img, [_detection("noteheadHalfInSpace",
                                            _lower_half_box(cx, cy))])
        # `gather_head_line_cut` never writes Q.GLYPH_BOX (the detector's)
        self.assertEqual(len(log.rows(Q.GLYPH_BOX, R.glyph(0, 0, 0, 0, 0))), 0)

    def test_the_ink_is_read_on_the_rebuilt_head_and_off_the_line_rows(self):
        img, cx, cy = self._staff_head(180.0)
        log = self._gather(img, [_detection("noteheadHalfInSpace",
                                            _lower_half_box(cx, cy))])
        row = log.rows(Q.NOTEHEAD_INK, R.glyph(0, 0, 0, 0, 0))[-1]
        self.assertIn("ink_off_line", row.detail)
        self.assertIn("box_source", row.detail)
        off = row.detail["ink_off_line"]
        self.assertLess(off["windows"]["center"], 0.75)
        # ... and the hollow cut agrees on it
        self.assertTrue(rhythm._ink_reads_decisively_hollow(row.detail))

    def test_CONTROL_a_black_head_on_a_line_reads_filled_off_the_line(self):
        """A filled head with the staff line through it: solid on every window,
        the off-line one included. It must NOT read hollow."""
        img = _paper()
        _ring_head(img, 150.0, 180.0, ink_fill=True)
        _line(img, 180.0, 150.0)
        box = (150 - HEAD_W / 2.0, 180 - HEAD_H / 2.0,
               150 + HEAD_W / 2.0, 180 + HEAD_H / 2.0)
        log = self._gather(img, [_detection("noteheadBlackOnLine", box)])
        row = log.rows(Q.NOTEHEAD_INK, R.glyph(0, 0, 0, 0, 0))[-1]
        self.assertGreater(row.detail["ink_off_line"]["windows"]["center"], 0.95)
        self.assertFalse(rhythm._ink_reads_decisively_hollow(row.detail))

    def test_a_line_through_the_hole_reads_as_fill_on_the_raw_window_only(self):
        """The reason the third reading exists: with the line left IN, the raw
        centre window of a whole-box half head reads mostly ink; with its rows
        left OUT it reads the hole."""
        img, cx, cy = _head_on_line(cy=180.0)
        box = (cx - HEAD_W / 2.0, cy - HEAD_H / 2.0,
               cx + HEAD_W / 2.0, cy + HEAD_H / 2.0)
        raw = gather.notehead_ink_under(
            img, (box[0], box[1], box[2] - box[0], box[3] - box[1]))
        off = gather.notehead_ink_off_line(
            img, (box[0], box[1], box[2] - box[0], box[3] - box[1]), S)
        self.assertIsNotNone(off)
        self.assertLess(off["windows"]["center"], raw["windows"]["center"])


# ─────────────────────────────────────────────────────────────────────────────
# C. ADJUDICATE
# ─────────────────────────────────────────────────────────────────────────────

SP = 100.0       # `_cell_geometry`'s staff space


def _cut_row(log, g, *, cx, cy):
    """A `Q.HEAD_LINE_CUT` row: the standard head box centred on (cx, cy)."""
    w, h = 1.4 * SP, 1.1 * SP
    return log.observe(
        g, Q.HEAD_LINE_CUT, [cx - w / 2.0, cy - h / 2.0, w, h],
        reader=READERS.CV_HEAD_LINE_CUT, frame="cell:0", line_y=cy,
        line_half_step=4, line_half_step_float=4.0, edge="top")


def _ink_row(log, g, net):
    return log.observe(
        g, Q.NOTEHEAD_INK, net, reader=READERS.CV_NOTEHEAD_INK, frame="cell:0",
        ink_net={"best": net, "windows": {"center": net, "ring": net}},
        ink_raw={"best": net, "windows": {"center": net, "ring": net}})


def _run(log):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    return log


def _verdict(log, g):
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)


class TestOneHeadOneBox(unittest.TestCase):

    def _piece(self, log, gi, *, y_c, cy_head=200.0, conf=0.6, cut=True):
        """A half-ring box (0.6 sp tall) of a head centred at (200, cy_head)."""
        g = _notehead(log, gi, cls="noteheadHalfInSpace", x_c=130.0, y_c=y_c - 30.0,
                      w_c=140.0, h_c=60.0, conf=conf, pos_float=4.0)
        if cut:
            _cut_row(log, g, cx=200.0, cy=cy_head)
        return g

    def test_two_halves_of_one_cut_head_are_one_head(self):
        log = Log()
        _cell_geometry(log)
        upper = self._piece(log, 0, y_c=170.0, conf=0.7)
        lower = self._piece(log, 1, y_c=230.0, conf=0.5)
        _run(log)
        refused = [g for g in (upper, lower) if _verdict(log, g).value is True]
        kept = [g for g in (upper, lower) if _verdict(log, g).value is False]
        self.assertEqual(len(refused), 1)
        self.assertEqual(len(kept), 1)
        self.assertEqual(_verdict(log, refused[0]).reason, "head_cut_piece")
        self.assertEqual(kept[0], upper, "higher detector score keeps the head")

    def test_a_lone_piece_is_the_head_and_is_kept(self):
        """NEVER the last box on a head."""
        log = Log()
        _cell_geometry(log)
        only = self._piece(log, 0, y_c=230.0)
        _run(log)
        self.assertIs(_verdict(log, only).value, False)

    def test_a_whole_box_on_the_head_keeps_it_and_the_pieces_go(self):
        log = Log()
        _cell_geometry(log)
        piece = self._piece(log, 0, y_c=230.0, conf=0.95)
        whole = _notehead(log, 1, cls="noteheadHalfInSpace", 
            x_c=130.0, y_c=145.0, w_c=140.0, h_c=110.0, conf=0.3,
                          pos_float=4.0)
        _ink_row(log, whole, 0.8)
        _run(log)
        self.assertIs(_verdict(log, whole).value, False,
                      "the whole box is the head, whatever the score")
        v = _verdict(log, piece)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "head_cut_piece")

    def test_CONTROL_a_chord_neighbour_a_second_away_is_another_head(self):
        """Two real heads: the cut head's piece and a whole box half a space
        above (a second, centre 50 px up). Neither may be refused."""
        log = Log()
        _cell_geometry(log)
        piece = self._piece(log, 0, y_c=230.0)
        neighbour = _notehead(log, 1, cls="noteheadHalfInSpace", 
            x_c=130.0, y_c=95.0, w_c=140.0, h_c=110.0, conf=0.9,
                              pos_float=3.0)
        _ink_row(log, neighbour, 0.8)
        _run(log)
        self.assertIs(_verdict(log, piece).value, False)
        self.assertIs(_verdict(log, neighbour).value, False)

    def test_CONTROL_no_cut_row_no_head_cut_refusal(self):
        """Two half-height boxes with no row (the ink showed no mirror hole):
        this reason never fires."""
        log = Log()
        _cell_geometry(log)
        a = self._piece(log, 0, y_c=170.0, cut=False)
        b = self._piece(log, 1, y_c=230.0, cut=False)
        _run(log)
        for g in (a, b):
            self.assertNotEqual(_verdict(log, g).reason, "head_cut_piece")


def _fit_row(log, g, *, k, slot, pos_float, ink, side="right",
             stem="stem/0/0/0/0"):
    return log.observe(
        g, Q.STACKED_HEAD_FIT, [k, slot, pos_float, 0.2],
        reader=READERS.CV_STACKED_HEAD_FIT, frame="cell:0",
        side=side, stem=stem, ink=ink, scores={})


class TestTheStackedGroupKeepChoice(unittest.TestCase):

    def test_two_heads_an_octave_apart_on_one_stem_are_both_kept(self):
        """Brahms 317803 pdf 0 (`glyph/0/0/5/1/2` and `/16`): one stem, one side,
        two real heads 3.5 sp apart, GATHER's fit slotted them as ONE head (the
        mean ink falls when the weaker is added). Neither box overlaps the
        other: the more inked must NOT delete the whole box of the other."""
        log = Log()
        _cell_geometry(log)
        upper = _notehead(log, 0, cls="noteheadHalfInSpace", 
            x_c=130.0, y_c=45.0, w_c=140.0, h_c=110.0, pos_float=1.0)
        lower = _notehead(log, 1, cls="noteheadHalfInSpace", 
            x_c=130.0, y_c=395.0, w_c=140.0, h_c=110.0, pos_float=8.0)
        _fit_row(log, upper, k=1, slot=0, pos_float=4.0, ink=0.70)
        _fit_row(log, lower, k=1, slot=0, pos_float=4.0, ink=0.74)
        _run(log)
        self.assertIs(_verdict(log, upper).value, False)
        self.assertIs(_verdict(log, lower).value, False)

    def test_CONTROL_two_overlapping_boxes_in_one_slot_still_lose_one(self):
        """The same fit, the same slot, but the boxes OVERLAP (one head boxed
        twice): the refusal this rule exists for still happens."""
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadBlackInSpace", 
            x_c=130.0, y_c=150.0, w_c=140.0, h_c=100.0, conf=0.9)
        b = _notehead(log, 1, cls="noteheadBlackInSpace", 
            x_c=130.0, y_c=200.0, w_c=140.0, h_c=100.0, conf=0.3)
        _fit_row(log, a, k=1, slot=0, pos_float=4.0, ink=0.08)
        _fit_row(log, b, k=1, slot=0, pos_float=4.0, ink=0.90)
        _run(log)
        self.assertIs(_verdict(log, a).value, True)
        self.assertEqual(_verdict(log, a).reason, "stacked_head_duplicate")
        self.assertIs(_verdict(log, b).value, False)

    def test_the_whole_box_beats_the_denser_partial_one(self):
        """`max(centre, ring)` of half a ring reads HIGHER than the whole
        head's: ink alone kept the partial box. Shape first."""
        log = Log()
        _cell_geometry(log)
        whole = _notehead(log, 0, cls="noteheadHalfInSpace", 
            x_c=130.0, y_c=145.0, w_c=140.0, h_c=110.0, conf=0.5)
        partial = _notehead(log, 1, cls="noteheadHalfInSpace", 
            x_c=130.0, y_c=200.0, w_c=140.0, h_c=60.0, conf=0.5)
        _fit_row(log, whole, k=1, slot=0, pos_float=4.0, ink=0.62)
        _fit_row(log, partial, k=1, slot=0, pos_float=4.0, ink=0.91)
        _run(log)
        self.assertIs(_verdict(log, whole).value, False)
        self.assertIs(_verdict(log, partial).value, True)
        self.assertEqual(_verdict(log, partial).reason,
                         "stacked_head_duplicate")

    def test_CONTROL_two_whole_boxes_still_go_by_ink(self):
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadBlackInSpace", 
            x_c=130.0, y_c=147.5, w_c=140.0, h_c=105.0, conf=0.5)
        b = _notehead(log, 1, cls="noteheadBlackInSpace", 
            x_c=130.0, y_c=205.0, w_c=140.0, h_c=110.0, conf=0.5)
        _fit_row(log, a, k=1, slot=0, pos_float=4.0, ink=0.95)
        _fit_row(log, b, k=1, slot=0, pos_float=4.0, ink=0.60)
        _run(log)
        self.assertIs(_verdict(log, a).value, False)
        self.assertIs(_verdict(log, b).value, True)


def _fill_row(log, g, *, center, ring):
    """`Q.NOTEHEAD_INK` with one raster reading, centre/ring as given."""
    reading = {"best": max(center, ring),
               "windows": {"center": center, "ring": ring}}
    return log.observe(g, Q.NOTEHEAD_INK, reading["best"],
                       reader=READERS.CV_NOTEHEAD_INK, frame="cell:0",
                       ink_raw=reading, ink_net=reading)


class TestOneHeadTwoClassesTheInkNamesTheClass(unittest.TestCase):
    """Litolff: one head boxed twice, `noteheadBlack*` and `noteheadHalf*`;
    ink alone (`max(centre, ring)`) kept the filled box by construction."""

    def _pair(self, log, *, black_ink, half_ink):
        black = _notehead(log, 0, cls="noteheadBlackOnLine", x_c=130.0,
                          y_c=150.0, w_c=140.0, h_c=100.0, conf=0.8,
                          pos_float=4.0)
        half = _notehead(log, 1, cls="noteheadHalfOnLine", x_c=130.0,
                         y_c=190.0, w_c=140.0, h_c=100.0, conf=0.4,
                         pos_float=4.0)
        _fit_row(log, black, k=1, slot=0, pos_float=4.0, ink=black_ink)
        _fit_row(log, half, k=1, slot=0, pos_float=4.0, ink=half_ink)
        return black, half

    def test_hollow_ink_keeps_the_half_class_box(self):
        log = Log()
        _cell_geometry(log)
        black, half = self._pair(log, black_ink=0.95, half_ink=0.70)
        for g in (black, half):
            _fill_row(log, g, center=0.6, ring=0.85)    # a sliver-hole half note
        _run(log)
        self.assertIs(_verdict(log, half).value, False)
        self.assertIs(_verdict(log, black).value, True)
        self.assertEqual(_verdict(log, black).reason, "stacked_head_duplicate")

    def test_CONTROL_solid_ink_keeps_the_black_class_box(self):
        log = Log()
        _cell_geometry(log)
        black, half = self._pair(log, black_ink=0.70, half_ink=0.95)
        for g in (black, half):
            _fill_row(log, g, center=1.0, ring=0.8)
        _run(log)
        self.assertIs(_verdict(log, black).value, False)
        self.assertIs(_verdict(log, half).value, True)

    def test_CONTROL_ink_that_says_neither_leaves_the_ink_choice(self):
        log = Log()
        _cell_geometry(log)
        black, half = self._pair(log, black_ink=0.95, half_ink=0.70)
        for g in (black, half):
            _fill_row(log, g, center=0.82, ring=0.9)    # neither cut
        _run(log)
        self.assertIs(_verdict(log, black).value, False)
        self.assertIs(_verdict(log, half).value, True)


class TestNoBoxIsRefusedByOneRuleAfterAnotherKeptIt(unittest.TestCase):
    """The circularity Brahms 317803 pdf 0 showed on 4 of Sean's 14 on-line
    heads: the head's one box was kept by one rule and refused by the next, and
    the partner it lost to had itself been refused -- the head was LOST."""

    def test_the_keeper_of_a_cut_head_is_not_then_refused_by_the_stacked_rule(self):
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadHalfInSpace", x_c=130.0,
                      y_c=110.0, w_c=140.0, h_c=60.0, conf=0.7, pos_float=4.0)
        b = _notehead(log, 1, cls="noteheadHalfInSpace", x_c=130.0,
                      y_c=200.0, w_c=140.0, h_c=60.0, conf=0.5, pos_float=4.0)
        for g in (a, b):
            _cut_row(log, g, cx=200.0, cy=200.0)
        # the OTHER piece carries more ink: the stacked rule alone would keep it
        _fit_row(log, a, k=1, slot=0, pos_float=4.0, ink=0.55)
        _fit_row(log, b, k=1, slot=0, pos_float=4.0, ink=0.90)
        _run(log)
        self.assertIs(_verdict(log, a).value, False, "keeper by score: kept")
        self.assertIs(_verdict(log, b).value, True)
        self.assertEqual(_verdict(log, b).reason, "head_cut_piece")

    def test_a_rival_that_2_30_already_refused_cannot_take_the_slot(self):
        """Two boxes on one head, same class: 2.30 keeps A (higher score, shapes
        within the margin) and refuses B. B has more ink, so 2.42 alone would
        keep B and refuse A -- leaving NO box. A must stand."""
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadHalfInSpace", x_c=130.0,
                      y_c=150.0, w_c=130.0, h_c=100.0, conf=0.9, pos_float=4.0)
        b = _notehead(log, 1, cls="noteheadHalfInSpace", x_c=130.0,
                      y_c=145.0, w_c=137.0, h_c=105.0, conf=0.3, pos_float=4.0)
        _fit_row(log, a, k=1, slot=0, pos_float=4.0, ink=0.55)
        _fit_row(log, b, k=1, slot=0, pos_float=4.0, ink=0.92)
        _run(log)
        self.assertIs(_verdict(log, a).value, False)
        self.assertIs(_verdict(log, b).value, True)
        self.assertEqual(_verdict(log, b).reason, "notehead_is_a_duplicate_box")


    def test_CONTROL_a_refused_winner_does_not_shield_every_other_box(self):
        """An earlier version of this change let ANY box whose slot-winner was
        refused earlier stand, and a beam sliver boxed as a head on Litolff
        survived by it. The circle is broken only where the winner was refused
        IN FAVOUR OF THIS box. Here B (more ink) is refused by 2.30 in favour
        of C, a third box; A, a different mark, still loses the slot to B."""
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=130.0,
                      y_c=250.0, w_c=140.0, h_c=100.0, conf=0.5, pos_float=4.0)
        b = _notehead(log, 1, cls="noteheadBlackInSpace", x_c=130.0,
                      y_c=150.0, w_c=140.0, h_c=100.0, conf=0.3, pos_float=2.0)
        c = _notehead(log, 2, cls="noteheadBlackInSpace", x_c=130.0,
                      y_c=145.0, w_c=140.0, h_c=100.0, conf=0.95, pos_float=2.0)
        _fit_row(log, a, k=1, slot=0, pos_float=4.0, ink=0.50)
        _fit_row(log, b, k=1, slot=0, pos_float=4.0, ink=0.92)
        _run(log)
        self.assertIs(_verdict(log, c).value, False)
        self.assertEqual(_verdict(log, b).reason, "notehead_is_a_duplicate_box")
        self.assertIs(_verdict(log, a).value, True)
        self.assertEqual(_verdict(log, a).reason, "stacked_head_duplicate")


class TestTheSameMarkRuleKeepsTheWholeHead(unittest.TestCase):

    def test_2_30_keeps_the_whole_box_over_a_more_confident_partial(self):
        log = Log()
        _cell_geometry(log)
        whole = _notehead(log, 0, cls="noteheadHalfInSpace", 
            x_c=130.0, y_c=145.0, w_c=140.0, h_c=110.0, conf=0.35)
        partial = _notehead(log, 1, cls="noteheadHalfInSpace", 
            x_c=130.0, y_c=185.0, w_c=140.0, h_c=60.0, conf=0.85)
        _run(log)
        self.assertIs(_verdict(log, whole).value, False)
        self.assertIs(_verdict(log, partial).value, True)
        self.assertEqual(_verdict(log, partial).reason,
                         "notehead_is_a_duplicate_box")

    def test_CONTROL_equal_shapes_still_go_by_confidence(self):
        log = Log()
        _cell_geometry(log)
        a = _notehead(log, 0, cls="noteheadHalfInSpace", 
            x_c=130.0, y_c=150.0, w_c=140.0, h_c=100.0, conf=0.9)
        b = _notehead(log, 1, cls="noteheadHalfInSpace", 
            x_c=130.0, y_c=160.0, w_c=140.0, h_c=100.0, conf=0.4)
        _run(log)
        self.assertIs(_verdict(log, a).value, False)
        self.assertIs(_verdict(log, b).value, True)


# ─────────────────────────────────────────────────────────────────────────────
# D. the hollow cut
# ─────────────────────────────────────────────────────────────────────────────


def _ink_detail(center, ring, key="ink_net"):
    return {key: {"best": max(center, ring),
                  "windows": {"center": center, "ring": ring}}}


class TestTheHollowCut(unittest.TestCase):

    def test_a_scan_half_note_with_a_sliver_hole_reads_hollow(self):
        """Litolff's half note: the hole is a thin slanted sliver, the centre
        window reads mostly ink (0.58-0.72 on Sean's judged heads)."""
        self.assertTrue(rhythm._ink_reads_decisively_hollow(
            _ink_detail(0.65, 0.80)))

    def test_CONTROL_the_floor_of_sean_s_filled_heads_is_not_hollow(self):
        """0.85 is the lowest centre Sean's 222 filled Brahms heads read."""
        self.assertFalse(rhythm._ink_reads_decisively_hollow(
            _ink_detail(0.85, 0.98)))

    def test_CONTROL_a_flat_reading_with_no_ring_gap_is_not_hollow(self):
        self.assertFalse(rhythm._ink_reads_decisively_hollow(
            _ink_detail(0.65, 0.70)))

    def test_the_off_line_reading_alone_can_decide(self):
        """A ledger line through the hole fills the raw and erased windows; the
        off-line one carries the verdict."""
        d = {**_ink_detail(0.95, 0.99, "ink_raw"),
             **_ink_detail(0.93, 0.99, "ink_net"),
             **_ink_detail(0.30, 0.80, "ink_off_line")}
        self.assertTrue(rhythm._ink_reads_decisively_hollow(d))

    def test_the_cut_is_under_both_measured_floors(self):
        self.assertLess(rhythm.HEAD_FILL_HOLLOW_CENTER_MAX, 0.85)
        self.assertGreater(rhythm.HEAD_FILL_HOLLOW_CENTER_MAX, 0.5)


if __name__ == "__main__":
    unittest.main()
