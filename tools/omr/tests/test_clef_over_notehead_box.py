"""ROADMAP 2.11 — clef-sized ink at the header is the clef, and a notehead
box standing on it is the error.

Sean, 2026-09-23 (`docs/DECISIONS.md`): *"it also looks like the clef box is
too small. the size of clefs are consistent to the staff and the edge of the
first measure on the system."* Registry entry `C88`.

⚠️ RUN RED FIRST, AND THE EXACT SPLIT IS PART OF THE CLAIM. Against the
unmodified tree: **13 failed, 3 passed**. The 13 are every test that touches
`occupied_classes`, `overrode_occupied`, `trace["override_refused"]` or the
`is_a_clef` verdict — none of which existed. The 3 that pass on BOTH trees
are the refusal's own positive controls (`a_notehead_elsewhere_on_the_staff
_is_untouched`, `a_clef_read_that_overrode_NOTHING_refuses_nothing`,
`a_staff_with_no_clef_row_at_all_refuses_nothing`), and they are the reason
this file is not a battery that passes by refusing everything.

⚠️ `TestTheVetoSurvives` is red on base for a SHALLOW reason and that is
worth saying rather than claiming more than it proves: the VERDICT it asserts
(the read is refused, `found is None`) is the base tree's behaviour too — it
fails there only on the `override_refused` trace key, which names WHICH gate
held. Each of those tests is still a way for 2.11 to fail, because each one
is a cluster the override must NOT take.

⚠️ NO SOURCE-TEXT ASSERTIONS. Every test drives the real `locate_clef` over a
drawn cell, or the real adjudicator over a real `Log`.
"""

from __future__ import annotations

import unittest

import cv2
import numpy as np

from tools.omr.clef_locator import DEFAULT_LOCATOR_CONFIG, locate_clef
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS

from tools.omr.tests.test_clef_locator import (
    CELL_W,
    SPACING,
    blank_page,
    draw_noteheads,
    line_y,
    make_cell,
)


# ─────────────────────────────────────────────────────────────────────────────
# A C clef drawn TALL ENOUGH TO BE IN THE MEASURED BAND.
#
# ⚠️ THE MODULE'S OWN FIXTURE CLEF IS 2.6 STAFF SPACES AND THAT IS TOO SHORT
# FOR THIS RULE ON PURPOSE. `test_clef_locator.CLEF_HALF` draws 2.6 spaces —
# inside `min_height_spaces` (2.2) so it is READ, but OUTSIDE the measured
# clef band (`clef_family_*`, 3.3–4.7), so it is exactly the cluster the veto
# must still refuse. Both shapes are used below, and which is which is the
# whole experiment: the tall one is a clef by size, the short one is not.
# ─────────────────────────────────────────────────────────────────────────────

CLEF_W = 28                       # 1.4 staff spaces, as in the module fixture
TALL_HALF = int(2.1 * SPACING)    # 4.2 staff spaces tall — inside 3.3–4.7


def draw_tall_c_clef(img: np.ndarray, line_from_bottom: int = 3,
                     x: int = 22) -> None:
    """The same archaic ladder glyph, drawn to 4.2 staff spaces.

    Proportions follow `test_clef_locator.draw_c_clef_at`: two vertical
    strokes joined by two bars, symmetric top-to-bottom, with bars short
    enough to survive `strip_horizontal_rules`.
    """
    cy = line_y(line_from_bottom)
    cv2.rectangle(img, (x, cy - TALL_HALF), (x + 11, cy + TALL_HALF), 0, -1)
    cv2.rectangle(img, (x + CLEF_W - 11, cy - TALL_HALF),
                  (x + CLEF_W, cy + TALL_HALF), 0, -1)
    for dy in (-SPACING // 2, SPACING // 2):
        cv2.rectangle(img, (x, cy + dy - 4), (x + CLEF_W, cy + dy + 4), 0, -1)


def _cell(tall: bool):
    img = blank_page()
    if tall:
        draw_tall_c_clef(img)
    else:
        from tools.omr.tests.test_clef_locator import draw_c_clef
        draw_c_clef(img, 3)
    draw_noteheads(img)
    return make_cell(img)


def _read(cell, **kw):
    trace: dict = {}
    found = locate_clef(cell, trace=trace, **kw)
    return found, trace


def _box_on_the_clef(cell, **kw):
    """A box covering the clef the locator would otherwise read, sized like a
    notehead (about one staff space tall, 1.3 wide — CLAUDE.md §10)."""
    found, _ = _read(cell)
    assert found is not None, "fixture broken: no clef to stand on"
    x, y, w, h = found.bbox
    cy = y + h / 2.0
    return (int(x), int(cy - SPACING / 2), int(w), int(SPACING))


# ─────────────────────────────────────────────────────────────────────────────


class TestTheFixturesAreWhatTheyClaim(unittest.TestCase):
    """⚠️ THE EXPERIMENT'S OWN CONTROL. Every test below turns on one cluster
    being inside the measured clef band and another being outside it. If the
    two fixtures ever drew the same height the whole file would pass by
    accident, so the heights are asserted from the READ, not from the
    drawing."""

    def test_the_tall_clef_is_inside_the_measured_band(self):
        _found, trace = _read(_cell(tall=True))
        self.assertEqual(trace.get("reason"), "located")
        h = trace["h_spaces"]
        self.assertGreaterEqual(h, DEFAULT_LOCATOR_CONFIG.clef_family_min_height_spaces)
        self.assertLessEqual(h, DEFAULT_LOCATOR_CONFIG.clef_family_max_height_spaces)

    def test_the_short_clef_is_outside_it_and_still_readable(self):
        found, trace = _read(_cell(tall=False))
        self.assertIsNotNone(found)
        self.assertLess(trace["h_spaces"],
                        DEFAULT_LOCATOR_CONFIG.clef_family_min_height_spaces)
        self.assertGreaterEqual(trace["h_spaces"],
                                DEFAULT_LOCATOR_CONFIG.min_height_spaces)


class TestTheOverride(unittest.TestCase):
    """A notehead-sized box on clef-sized ink at the header does not veto."""

    def test_a_notehead_box_on_a_band_sized_clef_is_overridden(self):
        cell = _cell(tall=True)
        box = _box_on_the_clef(cell)
        found, trace = _read(cell, occupied_boxes=[box],
                             occupied_classes=["noteheadBlackOnLine"])
        self.assertIsNotNone(found)
        self.assertEqual(found.read.name, "alto")
        self.assertEqual(trace.get("reason"), "located")
        self.assertEqual(found.overrode_occupied, (0,))

    def test_it_names_EVERY_box_it_overrode_and_no_other(self):
        """Two boxes on the clef, one elsewhere: the read must cite the two
        it actually stood on. Citing all three would make the downstream
        refusal condemn a real notehead further into the bar."""
        cell = _cell(tall=True)
        on = _box_on_the_clef(cell)
        upper = (on[0], on[1] - SPACING, on[2], SPACING)
        elsewhere = (300, line_y(3) - 10, 30, 20)
        found, _ = _read(
            cell, occupied_boxes=[on, elsewhere, upper],
            occupied_classes=["noteheadBlackOnLine"] * 3)
        self.assertIsNotNone(found)
        self.assertEqual(set(found.overrode_occupied), {0, 2})

    def test_an_ordinary_read_overrides_nothing(self):
        """A clef with no box on it reports an EMPTY override list, so a
        consumer cannot mistake "read" for "read over something"."""
        found, _ = _read(_cell(tall=True), occupied_boxes=[],
                         occupied_classes=[])
        self.assertIsNotNone(found)
        self.assertEqual(found.overrode_occupied, ())


class TestTheVetoSurvives(unittest.TestCase):
    """⚠️ THE POSITIVE CONTROLS. `_occupied_boxes` was added because a stacked
    chord is tall, glyph-sized and symmetric enough to pass for a C clef
    (`a481398c`). 2.11 removes that short-circuit for ONE named population and
    for no other, and each of these four is a way for it to fail."""

    def test_a_cluster_outside_the_clef_band_still_vetoes(self):
        cell = _cell(tall=False)
        box = _box_on_the_clef(cell)
        found, trace = _read(cell, occupied_boxes=[box],
                             occupied_classes=["noteheadBlackOnLine"])
        self.assertIsNone(found)
        self.assertEqual(trace.get("reason"), "occupied")
        self.assertEqual(trace.get("override_refused"),
                         "cluster_height_outside_clef_band")

    def test_a_NON_notehead_occupying_box_still_vetoes(self):
        cell = _cell(tall=True)
        box = _box_on_the_clef(cell)
        found, trace = _read(cell, occupied_boxes=[box],
                             occupied_classes=["dynamicForte"])
        self.assertIsNone(found)
        self.assertEqual(trace.get("reason"), "occupied")
        self.assertEqual(trace.get("override_refused"),
                         "an_occupying_box_is_not_a_notehead")

    def test_one_non_notehead_among_noteheads_still_vetoes(self):
        cell = _cell(tall=True)
        on = _box_on_the_clef(cell)
        upper = (on[0], on[1] - SPACING, on[2], SPACING)
        found, trace = _read(
            cell, occupied_boxes=[on, upper],
            occupied_classes=["noteheadBlackOnLine", "restQuarter"])
        self.assertIsNone(found)
        self.assertEqual(trace.get("reason"), "occupied")

    def test_a_box_that_is_ITSELF_clef_sized_still_vetoes(self):
        """"Too small" is the claim, so a box big enough to BE the clef is
        not obviously the error and keeps its veto."""
        cell = _cell(tall=True)
        found0, _ = _read(cell)
        found, trace = _read(cell, occupied_boxes=[found0.bbox],
                             occupied_classes=["noteheadBlackOnLine"])
        self.assertIsNone(found)
        self.assertEqual(trace.get("override_refused"),
                         "an_occupying_box_is_itself_clef_sized")

    def test_a_caller_that_supplies_no_classes_is_unchanged(self):
        """⚠️ THE FROZEN PATHS' CONTROL. `transcribe.py` and
        `key_signature_locator.py` pass boxes and no classes; neither may
        change behaviour under 2.11."""
        cell = _cell(tall=True)
        box = _box_on_the_clef(cell)
        found, trace = _read(cell, occupied_boxes=[box])
        self.assertIsNone(found)
        self.assertEqual(trace.get("reason"), "occupied")
        self.assertEqual(trace.get("override_refused"),
                         "caller_supplied_no_classes")

    def test_a_notehead_box_ELSEWHERE_never_reached_the_test_at_all(self):
        """The pre-2.11 behaviour this rule must not disturb: a box that does
        not overlap the cluster was never a veto."""
        cell = _cell(tall=True)
        found, _ = _read(cell, occupied_boxes=[(300, 100, 30, 20)],
                         occupied_classes=["noteheadBlackOnLine"])
        self.assertIsNotNone(found)
        self.assertEqual(found.overrode_occupied, ())


# ─────────────────────────────────────────────────────────────────────────────
# The refusal: the boxes the clef overrode are not noteheads.
# ─────────────────────────────────────────────────────────────────────────────

STAFF = R.staff(0, 0, 0)
CELL = R.cell(0, 0, 0, 0)
CANONICAL_SPACING = 100.0


def _log_with(overrode, *, clef="alto", n_glyphs=2):
    log = Log()
    log.observe(CELL, Q.CELL_STAFF_SPACE, CANONICAL_SPACING,
                reader=READERS.GEOMETRY, frame="cell:0")
    log.observe(CELL, Q.CELL_BOX, [500.0, 1000.0, 700.0, 1300.0],
                reader=READERS.GEOMETRY, frame="cell:0")
    kw = {}
    if overrode is not None:
        kw = {"overrides_notehead_box": True,
              "overrode_glyph_subjects": list(overrode)}
    log.observe(STAFF, Q.CLEF_LOCATED, clef, reader=READERS.CV_LOCATOR,
                frame="header_window", score=0.81, family="C", line=3,
                line_source="geometry", x_center=60, bbox=[40, 300, 40, 420],
                **kw)
    glyphs = []
    for gi in range(n_glyphs):
        g = R.glyph(0, 0, 0, 0, gi)
        # ⚠️ Ordinary, unimpeachable notehead geometry: 1.4 x 1.0 staff
        # spaces, inside the staff, high confidence, nowhere near the crop
        # edge. Neither `too_narrow` nor `clipped_fragment` can fire, so a
        # refusal below can only be `is_a_clef`.
        log.observe(g, Q.GLYPH_BOX,
                    ("noteheadBlackOnLine", 200.0 + 300 * gi, 200.0,
                     140.0, 100.0),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                    category="notehead",
                    bbox_page_px=[560.0 + 30 * gi, 1100.0,
                                  574.0 + 30 * gi, 1110.0])
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.8)
        log.observe(g, Q.GLYPH_CONF, 0.8, reader=READERS.DETECTOR,
                    frame="cell:0", score=0.8)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 4.0,
                    reader=READERS.GEOMETRY, frame="cell:0")
        glyphs.append(g)
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    return log, glyphs


class TestTheRefusal(unittest.TestCase):

    def test_the_overridden_box_is_refused_is_a_clef(self):
        log, glyphs = _log_with(["glyph/0/0/0/0/0"])
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, glyphs[0])
        self.assertTrue(v.value)
        self.assertEqual(v.reason, "is_a_clef")

    def test_a_notehead_elsewhere_on_the_staff_is_untouched(self):
        """⚠️ THE CONTROL THAT MATTERS MOST: the refusal must be keyed on the
        NAMED box, never on "this staff has an overriding clef"."""
        log, glyphs = _log_with(["glyph/0/0/0/0/0"])
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, glyphs[1])
        self.assertFalse(v.value)
        self.assertEqual(v.reason, "notehead")

    def test_the_refusal_CITES_the_clef_row(self):
        """A CONNECT, not a guess: the verdict's basis must name the read
        that caused it, or nothing downstream can trace the refusal back."""
        log, glyphs = _log_with(["glyph/0/0/0/0/0"])
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, glyphs[0])
        clef_rows = [r for r in log.rows(Q.CLEF_LOCATED, STAFF)]
        self.assertTrue(clef_rows)
        self.assertIn(clef_rows[-1].id, v.basis)

    def test_a_clef_read_that_overrode_NOTHING_refuses_nothing(self):
        """The positive control for the whole rule: the same staff, the same
        clef, the same boxes — only the `overrode_glyph_subjects` key gone."""
        log, glyphs = _log_with(None)
        for g in glyphs:
            v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
            self.assertFalse(v.value)
            self.assertEqual(v.reason, "notehead")

    def test_a_staff_with_no_clef_row_at_all_refuses_nothing(self):
        log = Log()
        log.observe(CELL, Q.CELL_STAFF_SPACE, CANONICAL_SPACING,
                    reader=READERS.GEOMETRY, frame="cell:0")
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.GLYPH_BOX,
                    ("noteheadBlackOnLine", 200.0, 200.0, 140.0, 100.0),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                    category="notehead")
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.8)
        log.observe(g, Q.GLYPH_CONF, 0.8, reader=READERS.DETECTOR,
                    frame="cell:0", score=0.8)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 4.0,
                    reader=READERS.GEOMETRY, frame="cell:0")
        log.freeze()
        adjudicate._ensure_decisions()
        adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertFalse(v.value)
        self.assertEqual(v.reason, "notehead")


if __name__ == "__main__":
    unittest.main()
