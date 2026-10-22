"""ROADMAP 2.69 follow-up -- a "dot" that is the curled tip of a flag is not
a lengthening dot (Sean, 2026-10-09, DECISIONS).

2.65 tile 13 is a plain eighth. The detector drew an `augmentationDot` box
glyph/1/1/8/3/15 ON THE CURLED TIP OF THE NOTE'S OWN FLAG, `adjudicate_dot_role`
placed it right of and level with the head, and the note was DECIDED dotted
(0.75) the moment 2.69 counted its hook. Sean: *"a dot can not fully or
mostly overlap a flag but it can touch it"* -- overlap, not contact.

GATHER: `gather.dot_stroke_ink` / `_observe_dot_stroke_ink` (`Q.DOT_STROKE_INK`)
-- the share of a dot box's ink that lies on an elongated stroke. ADJUDICATE:
`adjudicate_dot_role` abstains `on_a_stroke` at or above `DOT_ON_STROKE_MIN`.

⚠️ RED FIRST: every test below that names `Q.DOT_STROKE_INK`,
`gather.dot_stroke_ink` or `on_a_stroke` fails (AttributeError / wrong value)
on the unrepaired tree. Positive controls in the same class: an isolated
round dot, a round dot TOUCHING a flag, a staccato above a note, an ordinary
right-of-head dot -- Sean's earlier dot rulings (DECISIONS 2026-10-07) stay.
"""

from __future__ import annotations

import unittest

import cv2
import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS

SP = 40.0


def _paper(h=500, w=500):
    return np.full((h, w), 255, dtype=np.uint8)


def _flag_tip(img, x=200, y0=60, y1=300, thick=0.4):
    """A long thick stroke, the descending tail of a flag, ending at y1."""
    t = int(round(thick * SP))
    img[y0:y1, x:x + t] = 0


def _disc(img, cx, cy, d=0.45):
    r = int(round(d * SP / 2))
    cv2.circle(img, (int(cx), int(cy)), r, 0, thickness=-1)


class TestTheMeasurement(unittest.TestCase):
    """`gather.dot_stroke_ink` on synthetic rasters (0 = ink)."""

    BOX = (200, 270, 16, 30)          # the dot-sized box at the stroke's END

    def test_the_box_on_the_end_of_a_flag_stroke_is_stroke_RED(self):
        img = _paper()
        _flag_tip(img)
        m = gather.dot_stroke_ink(img, self.BOX, SP)
        self.assertGreaterEqual(m["fraction"], 0.5)

    def test_a_box_on_a_stem_body_is_stroke(self):
        img = _paper()
        img[40:400, 205:211] = 0
        m = gather.dot_stroke_ink(img, (203, 150, 12, 14), SP)
        self.assertGreaterEqual(m["fraction"], 0.5)

    def test_POSITIVE_CONTROL_an_isolated_round_dot_is_not_stroke(self):
        img = _paper()
        _disc(img, 250, 250)
        m = gather.dot_stroke_ink(img, (240, 240, 20, 20), SP)
        self.assertEqual(m["fraction"], 0.0)
        self.assertGreater(m["ink_px"], 0)

    def test_POSITIVE_CONTROL_a_round_dot_TOUCHING_a_flag_is_not_stroke_RED(self):
        """Sean: a dot may TOUCH a flag. The disc stands clear beside the
        stroke with its edge against it -- contact, not overlap."""
        img = _paper()
        _flag_tip(img, x=200)
        _disc(img, 200 + 16 + 9, 280)          # edge meets the stroke's edge
        box = (200 + 16, 270, 20, 20)
        m = gather.dot_stroke_ink(img, box, SP)
        self.assertLess(m["fraction"], 0.5)

    def test_a_round_dot_on_an_erased_staff_stripe_is_not_stroke(self):
        """The erase leaves horizontal stripes; they must not read as a
        stroke (the 0-degree line is deliberately not tried)."""
        img = _paper()
        img[245:250, 100:400] = 0
        _disc(img, 250, 248)
        m = gather.dot_stroke_ink(img, (240, 238, 20, 20), SP)
        self.assertLess(m["fraction"], 0.5)

    def test_a_box_with_no_ink_is_zero_with_no_ink_px(self):
        m = gather.dot_stroke_ink(_paper(), (240, 240, 20, 20), SP)
        self.assertEqual((m["fraction"], m["ink_px"]), (0.0, 0))

    def test_unusable_inputs_decline(self):
        self.assertIsNone(gather.dot_stroke_ink(None, self.BOX, SP))
        self.assertIsNone(gather.dot_stroke_ink(_paper(), self.BOX, 0.0))
        self.assertIsNone(gather.dot_stroke_ink(_paper(), (0, 0, 0, 0), SP))


class _Det:
    def __init__(self, name, x, y, w, h):
        self.smufl_name = name
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h


class _Cell:
    def __init__(self, img):
        self.image_no_staff = img


SUB = R.cell(0, 0, 0, 0)


class TestTheRowIsFiledOnTheDotsOwnGlyph(unittest.TestCase):

    def _file(self, img, dets, space=SP):
        log = Log()
        gather._observe_dot_stroke_ink(log, SUB, "cell:0", _Cell(img), dets,
                                       space)
        log.freeze()
        return log

    def test_one_row_per_augmentation_dot_at_its_detection_index_RED(self):
        img = _paper()
        _flag_tip(img)
        dets = [_Det("noteheadBlack", 100, 100, 40, 30),
                _Det("augmentationDot", 200, 270, 16, 30),
                _Det("articStaccatoAbove", 300, 100, 10, 10)]
        log = self._file(img, dets)
        rows = log.rows(Q.DOT_STROKE_INK, R.glyph(0, 0, 0, 0, 1))
        self.assertEqual(len(rows), 1)
        self.assertGreaterEqual(rows[0].value, 0.5)
        self.assertEqual(rows[0].reader, READERS.CV_DOT_STROKE)
        # nothing was filed for the head or the staccato class
        for gi in (0, 2):
            self.assertEqual(log.rows(Q.DOT_STROKE_INK,
                                      R.glyph(0, 0, 0, 0, gi)), ())

    def test_no_raster_abstains_no_mask(self):
        log = self._file(None, [_Det("augmentationDot", 200, 270, 16, 30)])
        ab = log.refusals(Q.DOT_STROKE_INK, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(ab[0].reason, ABSTAIN.NO_MASK)

    def test_no_space_unit_abstains(self):
        log = self._file(_paper(), [_Det("augmentationDot", 200, 270, 16, 30)],
                         space=None)
        ab = log.refusals(Q.DOT_STROKE_INK, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(ab[0].reason, ABSTAIN.NO_STAFF_GEOMETRY)


# ─────────────────────────────────────────────────────────────────────────────
# ADJUDICATE
# ─────────────────────────────────────────────────────────────────────────────

CELL = R.cell(0, 0, 0, 0)
X = 100
SPACE = 16


def _staff_space(log):
    return log.observe(CELL, Q.CELL_STAFF_SPACE, float(SPACE),
                       reader=READERS.GEOMETRY, frame="cell:0")


def _note(log, gi, head="noteheadBlack"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, head, reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (head, X - 10, 0, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    return g


def _mark(log, *, gi, cls, x, y, w=4, h=8, stroke=None):
    d = R.glyph(0, 0, 0, 0, gi)
    log.observe(d, Q.GLYPH_BOX, (cls, x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.8)
    role = "dot" if cls == "augmentationDot" else "staccato"
    log.observe(d, Q.AUG_DOT, (x + w / 2.0, y + h / 2.0),
                reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                detector_role=role, detector_class=cls)
    if stroke is not None:
        log.observe(d, Q.DOT_STROKE_INK, stroke, reader=READERS.CV_DOT_STROKE,
                    frame="cell:0", ink_px=300, line_px=48)
    return d


class TestADotOnAStrokeNeverLengthens(unittest.TestCase):

    def _run(self, stroke, cls="augmentationDot", x=X + 12, y=4):
        log = Log()
        g = _note(log, 0, "noteheadHalf")
        _staff_space(log)
        d = _mark(log, gi=1, cls=cls, x=x, y=y, stroke=stroke)
        adjudicate.run(log)
        return log, g, d

    def test_RED_a_dot_box_mostly_on_a_flag_is_no_dot_and_the_note_is_not_dotted(self):
        log, g, d = self._run(0.93)
        role = log.verdict(Q.DOT_ROLE, d)
        self.assertEqual(role.outcome, Outcome.ABSTAINED)
        self.assertEqual(role.reason, "on_a_stroke")
        dur = log.verdict(Q.DURATION, g)
        self.assertEqual(dur.value["dots"], 0)
        self.assertEqual(dur.value["beats"], 2.0)

    def test_the_stroke_row_is_in_the_verdicts_basis(self):
        log, g, d = self._run(0.93)
        row = log.rows(Q.DOT_STROKE_INK, d)[-1]
        self.assertIn(row.id, log.verdict(Q.DOT_ROLE, d).basis)

    def test_POSITIVE_CONTROL_a_dot_that_only_touches_stays_a_dot(self):
        """Sean: it CAN touch -- a low stroke share is a real dot."""
        log, g, d = self._run(0.2)
        self.assertEqual(log.verdict(Q.DOT_ROLE, d).value, "augmentation")
        self.assertEqual(log.verdict(Q.DURATION, g).value["dots"], 1)

    def test_POSITIVE_CONTROL_just_under_the_line_stays_a_dot(self):
        log, g, d = self._run(0.49)
        self.assertEqual(log.verdict(Q.DOT_ROLE, d).value, "augmentation")

    def test_POSITIVE_CONTROL_no_stroke_row_at_all_is_unchanged(self):
        """An older record (or a reader that abstained): today's reading."""
        log, g, d = self._run(None)
        self.assertEqual(log.verdict(Q.DOT_ROLE, d).value, "augmentation")
        self.assertEqual(log.verdict(Q.DURATION, g).value["dots"], 1)

    def test_POSITIVE_CONTROL_a_staccato_above_a_note_is_still_a_staccato(self):
        """DECISIONS 2026-10-07: staccato dots above a note are not
        lengthening dots -- and they stay staccatos, not strokes."""
        log, g, d = self._run(0.0, cls="augmentationDot", x=X - 2, y=-16)
        role = log.verdict(Q.DOT_ROLE, d)
        self.assertEqual(role.value, "staccato")
        self.assertEqual(log.verdict(Q.DURATION, g).value["dots"], 0)

    def test_the_gate_reads_the_dots_OWN_row_not_another_dots(self):
        """A second, real dot on the same note with its own low row is
        unaffected by the first one's high row."""
        log = Log()
        g = _note(log, 0, "noteheadHalf")
        _staff_space(log)
        bad = _mark(log, gi=1, cls="augmentationDot", x=X + 12, y=4,
                    stroke=0.93)
        good = _mark(log, gi=2, cls="augmentationDot", x=X + 30, y=4,
                     stroke=0.0)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.DOT_ROLE, bad).reason, "on_a_stroke")
        self.assertEqual(log.verdict(Q.DOT_ROLE, good).value, "augmentation")


if __name__ == "__main__":
    unittest.main()
