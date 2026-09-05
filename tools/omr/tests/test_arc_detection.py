"""Tests for the classical-CV arc reader and its OMR_ARC_CV arbitration."""
import os
import unittest
from unittest import mock

import numpy as np

from tools.omr import arc_detection as ad
from tools.omr.arc_detection import (
    LineDetection,
    apply_arc_cv,
    arc_cv_mode,
    detect_arcs,
)


def _cell(img, ys=(100, 124, 148, 172, 196)):
    class _C:
        staff_line_ys_canonical = list(ys)
        image = img
        image_no_staff = img
    return _C()


def _blank(h=300, w=800):
    return np.full((h, w), 255, dtype=np.uint8)


def _draw_arc(img, x0, x1, y, rise, thickness=3):
    """Draw a downward-opening arch (apex above the endpoints)."""
    for x in range(x0, x1):
        t = (x - x0) / max(1, x1 - x0 - 1)
        yy = int(round(y - rise * 4 * t * (1 - t)))
        img[yy:yy + thickness, x] = 0


class TestDetectArcs(unittest.TestCase):
    def test_finds_a_clean_arc(self):
        img = _blank()
        # staff spacing 24px; arc 6 spaces wide, rise ~0.5 spaces
        _draw_arc(img, 200, 344, 250, 12)
        arcs = detect_arcs(_cell(img))
        self.assertEqual(len(arcs), 1)
        a = arcs[0]
        self.assertIn(a.smufl_name, ("tie", "slur"))
        self.assertLess(abs(a.x_canonical - 200), 6)
        self.assertGreater(a.width_canonical, 120)

    def test_flat_stroke_refused(self):
        img = _blank()
        img[250:253, 200:500] = 0          # a dead-flat line (ledger/staff jag)
        self.assertEqual(detect_arcs(_cell(img)), [])

    def test_stroke_cut_by_top_edge_refused(self):
        img = _blank()
        _draw_arc(img, 200, 344, 12, 14)   # apex pokes through the top border
        self.assertEqual(detect_arcs(_cell(img)), [])

    def test_stroke_far_below_staff_refused(self):
        img = _blank()
        # staff bottom line at 196, sp 24; centre ~276 = +3.3 spaces below
        _draw_arc(img, 200, 344, 280, 12)
        self.assertEqual(detect_arcs(_cell(img)), [])

    def test_arc_cut_by_stem_is_chained(self):
        img = _blank()
        _draw_arc(img, 200, 344, 250, 12)
        img[:, 270:274] = 255              # a white cut where a stem was
        arcs = detect_arcs(_cell(img))
        self.assertEqual(len(arcs), 1)
        self.assertGreater(arcs[0].width_canonical, 120)

    def test_none_and_empty_inputs(self):
        self.assertEqual(detect_arcs(None), [])
        self.assertEqual(detect_arcs(_cell(np.zeros((0, 0), np.uint8))), [])


class TestArcCvMode(unittest.TestCase):
    def test_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMR_ARC_CV", None)
            self.assertEqual(arc_cv_mode(), "off")

    def test_spellings(self):
        for v, want in [("0", "off"), ("false", "off"), ("veto", "veto"),
                        ("1", "veto"), ("veto+cv", "veto+cv"),
                        ("replace", "replace"), ("garbage", "off"),
                        ("anchor", "anchor"), ("anchor+cv", "anchor+cv"),
                        ("anchor_cv", "anchor+cv")]:
            with mock.patch.dict(os.environ, {"OMR_ARC_CV": v}):
                self.assertEqual(arc_cv_mode(), want, v)


class TestApplyArcCv(unittest.TestCase):
    def _yolo_arc(self, x, y, w, h, name="tie"):
        return LineDetection(smufl_name=name, category="structural",
                             x_canonical=x, y_canonical=y,
                             width_canonical=w, height_canonical=h,
                             confidence=0.5)

    def test_off_is_identity(self):
        dets = [self._yolo_arc(10, 10, 100, 20)]
        out = apply_arc_cv(dets, None, "off")
        self.assertIs(out, dets)

    def test_veto_keeps_confirmed_and_drops_unconfirmed(self):
        img = _blank()
        _draw_arc(img, 200, 344, 250, 12)
        cell = _cell(img)
        confirmed_arc = self._yolo_arc(195, 230, 160, 30)
        phantom = self._yolo_arc(500, 50, 120, 25)
        note = LineDetection(smufl_name="noteheadBlack", category="notehead",
                             x_canonical=1, y_canonical=1,
                             width_canonical=10, height_canonical=10)
        out = apply_arc_cv([confirmed_arc, phantom, note], cell, "veto")
        self.assertIn(confirmed_arc, out)
        self.assertIn(note, out)
        self.assertNotIn(phantom, out)

    def test_veto_cv_adds_uncovered_cv_arc(self):
        img = _blank()
        _draw_arc(img, 200, 344, 250, 12)
        cell = _cell(img)
        out = apply_arc_cv([], cell, "veto+cv")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].category, "structural")

    def test_replace_swaps_arcs_only(self):
        img = _blank()
        _draw_arc(img, 200, 344, 250, 12)
        cell = _cell(img)
        phantom = self._yolo_arc(500, 50, 120, 25)
        note = LineDetection(smufl_name="noteheadBlack", category="notehead",
                             x_canonical=1, y_canonical=1,
                             width_canonical=10, height_canonical=10)
        out = apply_arc_cv([phantom, note], cell, "replace")
        self.assertIn(note, out)
        self.assertNotIn(phantom, out)
        self.assertEqual(sum(1 for d in out if d.category == "structural"), 1)


class TestAnchorMode(unittest.TestCase):
    """Round 9: an arc is kept only when its ends land on the cell's own
    noteheads (each end anchored or cut-exempt at the left/right crop edge)."""

    def _arc(self, x, y, w, h, name="tie"):
        return LineDetection(smufl_name=name, category="structural",
                             x_canonical=x, y_canonical=y,
                             width_canonical=w, height_canonical=h,
                             confidence=0.5)

    def _note(self, x, y, w=20, h=20):
        return LineDetection(smufl_name="noteheadBlack", category="notehead",
                             x_canonical=x, y_canonical=y,
                             width_canonical=w, height_canonical=h,
                             confidence=0.9)

    def test_anchored_arc_kept_unanchored_dropped(self):
        cell = _cell(_blank())
        # noteheads at x-centres 200 and 370, level with an arc at y 230-260
        n1, n2 = self._note(190, 235), self._note(360, 235)
        anchored = self._arc(210, 230, 150, 30)   # ends near both noteheads
        floater = self._arc(500, 40, 120, 25)     # nothing anchors it
        out = apply_arc_cv([anchored, floater, n1, n2], cell, "anchor")
        self.assertIn(anchored, out)
        self.assertIn(n1, out)
        self.assertNotIn(floater, out)

    def test_cut_end_is_exempt_on_that_side(self):
        cell = _cell(_blank())          # cell is 800 wide, sp 24
        n1 = self._note(700, 235)
        # arc runs from x=720 to the right crop edge: right end cut-exempt,
        # left end anchored by n1 -> kept.
        crosser = self._arc(718, 230, 82, 25)
        out = apply_arc_cv([crosser, n1], cell, "anchor")
        self.assertIn(crosser, out)

    def test_both_ends_cut_asserts_nothing_and_is_kept(self):
        cell = _cell(_blank())
        spanner = self._arc(0, 230, 800, 25)   # touches both crop edges
        # No anchor at all -> refused: an arc exempt at both ends asserts
        # nothing about this staff.
        out = apply_arc_cv([spanner], cell, "anchor")
        self.assertNotIn(spanner, out)

    def test_anchor_cv_admits_flat_arc_with_both_anchors(self):
        img = _blank()
        # A FLAT tie: rise ~0.08 spaces (2px on sp 24) — the standard rise
        # gate refuses it; with both ends anchored, anchor+cv admits it.
        _draw_arc(img, 200, 344, 250, 2)
        cell = _cell(img)
        n1, n2 = self._note(185, 240), self._note(350, 240)
        self.assertEqual(detect_arcs(cell), [])   # shape alone refuses
        out = apply_arc_cv([n1, n2], cell, "anchor+cv")
        added = [d for d in out if d.category == "structural"]
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0].smufl_name, "tie")

    def test_anchor_cv_does_not_admit_flat_arc_without_anchors(self):
        img = _blank()
        _draw_arc(img, 200, 344, 250, 2)
        cell = _cell(img)
        out = apply_arc_cv([], cell, "anchor+cv")
        self.assertEqual([d for d in out if d.category == "structural"], [])

    def test_no_geometry_abstains_whole(self):
        class _C:
            staff_line_ys_canonical = []
            image = _blank()
            image_no_staff = image
        floater = self._arc(500, 40, 120, 25)
        dets = [floater]
        out = apply_arc_cv(dets, _C(), "anchor")
        self.assertIs(out, dets)


if __name__ == "__main__":
    unittest.main()
