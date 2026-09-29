"""A notehead box with no ink under it -- ROADMAP 2.6h.

⚠️ WHY THIS FILE EXISTS. `benchmarks/omr-owner-domain-2026-09/FINDINGS.md`
§2.6g cropped 14 of Litolff's 345 `owner_not_read` (`far_no_rungs`) heads,
read by eye: 4 stand over TRULY BLANK PAPER (left AND right overhang ~=0.0
on both sides, no ledger of any kind visible near the head). CLAUDE.md §10
already names the mechanism at population scale (46 of 180 sampled Litolff
"notehead" boxes were not noteheads); "there is no ink" -> "not a notehead"
FOLLOWS, and does not need `glyph_owner`'s contest or a rung search to say
so.

  PART A (GATHER)      `gather.notehead_ink_under` / `gather_notehead_ink`
                       -- the ink fraction inside a notehead's OWN box,
                       two ways (`center`, `ring`), off BOTH the UNERASED
                       canonical raster (`cell.binary`) and the staff-
                       ERASED one (`cell.image_no_staff`).
  PART B (ADJUDICATE)  `notehead_precision._no_ink_under_box`, exercised
                       directly against injected `Q.NOTEHEAD_INK` rows in
                       `test_staged_notehead_precision.py` -- refuses only
                       where NEITHER raster shows ink under the box.

⚠️ RUN RED FIRST: every test below fails with `AttributeError`
(`gather.notehead_ink_under` / `gather.gather_notehead_ink` /
`Q.NOTEHEAD_INK` absent) against the tree before this change.
"""

from __future__ import annotations

import unittest

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, CLAIM, Log, Q


def _paper(h=200, w=200):
    return np.full((h, w), 255, dtype=np.uint8)


def _box(cx=100, cy=100, w=52, h=40):
    """(x, y, w, h) canonical, a notehead-shaped box centred at (cx, cy)."""
    return (cx - w / 2.0, cy - h / 2.0, float(w), float(h))


def _fill_ellipse(img, box, *, shrink=0.0):
    """A filled ellipse inscribed in `box` (a BLACK head), shrunk on every
    side by `shrink` (a fraction of the box's own half-extent)."""
    x, y, w, h = box
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    cx, cy = x + w / 2.0, y + h / 2.0
    a, b = max(1.0, w / 2.0 * (1.0 - shrink)), max(1.0, h / 2.0 * (1.0 - shrink))
    img[((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2 <= 1.0] = 0


def _ring(img, box, thickness):
    """A HOLLOW head: an ellipse OUTLINE only, `thickness` px wide."""
    x, y, w, h = box
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    cx, cy = x + w / 2.0, y + h / 2.0
    a, b = w / 2.0, h / 2.0
    outer = ((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2 <= 1.0
    a2, b2 = max(1.0, a - thickness), max(1.0, b - thickness)
    inner = ((xx - cx) / a2) ** 2 + ((yy - cy) / b2) ** 2 <= 1.0
    img[outer & ~inner] = 0


def _line(img, y, *, thickness=2):
    img[int(y):int(y + thickness), :] = 0


class TestTheMeasurement(unittest.TestCase):
    """`gather.notehead_ink_under` -- pure, on synthetic rasters."""

    def test_blank_paper_reads_zero_on_every_window(self):
        img = _paper()
        m = gather.notehead_ink_under(img, _box())
        self.assertEqual(m["best"], 0.0)
        self.assertEqual(m["windows"]["center"], 0.0)
        self.assertEqual(m["windows"]["ring"], 0.0)

    def test_a_filled_BLACK_head_reads_high_ON_THE_CENTRE(self):
        img = _paper()
        box = _box()
        _fill_ellipse(img, box)
        m = gather.notehead_ink_under(img, box)
        self.assertGreater(m["best"], 0.4)
        self.assertEqual(m["best_window"], "center")

    def test_a_HOLLOW_head_reads_high_but_NOT_on_the_centre(self):
        """⚠️⚠️ THE POSITIVE CONTROL THE BRIEF NAMES: a hollow (half/whole)
        head's own middle is near-empty by design, and must never be read
        as blank -- `ring` is its witness, not `center`."""
        img = _paper()
        box = _box()
        _ring(img, box, thickness=6)
        m = gather.notehead_ink_under(img, box)
        self.assertGreater(m["best"], 0.2)
        self.assertEqual(m["best_window"], "ring")
        self.assertLess(m["windows"]["center"], 0.15)

    def test_a_STAFF_LINE_ALONE_crossing_the_box_is_a_KNOWN_LIMITATION(self):
        """⚠️ NOT A SAFETY PROPERTY OF THIS FUNCTION ALONE. A thin line
        through the box's own interior band DOES read as some `center`
        ink (a stroke a few px thick over a much taller window), but a
        line spanning the box's FULL height would not exist on a real
        page -- the actual defence against "staff-line pixels alone read
        as ink" is the DUAL-RASTER design one level up
        (`notehead_precision._no_ink_under_box`, tested there): the SAME
        line is read on the staff-ERASED raster too, where it is gone."""
        img = _paper()
        box = _box()
        _line(img, box[1] + box[3] / 2.0, thickness=2)
        m = gather.notehead_ink_under(img, box)
        self.assertLess(m["best"], 0.2)

    def test_a_window_off_the_raster_is_clipped_not_invented(self):
        img = _paper(h=20, w=200)
        box = _box(cy=4)
        m = gather.notehead_ink_under(img, box)
        self.assertIsNotNone(m)
        self.assertEqual(m["best"], 0.0)

    def test_no_raster_no_measurement(self):
        self.assertIsNone(gather.notehead_ink_under(None, _box()))

    def test_a_3d_image_is_declined_not_guessed(self):
        rgb = np.dstack([_paper()] * 3)
        self.assertIsNone(gather.notehead_ink_under(rgb, _box()))

    def test_a_degenerate_box_is_declined(self):
        img = _paper()
        self.assertIsNone(gather.notehead_ink_under(img, (10.0, 10.0, 0.0, 0.0)))

    def test_a_box_too_short_for_an_interior_is_DECLINED_not_faked(self):
        """⚠️ `center`/`ring` would degenerate to the same pixels below the
        shrink -- left `None`, never invented; a box this small is not
        this rule's population (see `too_narrow`'s own width floor)."""
        img = _paper()
        box = (80.0, 98.0, 40.0, 2.0)
        img[98:100, 80:120] = 0
        m = gather.notehead_ink_under(img, box)
        self.assertIsNone(m)


class TestGatherFilesTheQuantity(unittest.TestCase):

    def test_the_quantity_is_a_measurement(self):
        self.assertIn(Q.NOTEHEAD_INK, Q.all())
        self.assertEqual(R.claim_of(Q.NOTEHEAD_INK), CLAIM.MEASUREMENT)


class _FakeCell:
    page_index = 0
    measure_index = 0

    def __init__(self, staff_index=0, *, binary=None, image_no_staff=None):
        self.staff_index = staff_index
        if binary is not None:
            self.binary = binary
        if image_no_staff is not None:
            self.image_no_staff = image_no_staff


class _FakeDetection:
    def __init__(self, smufl_name, box):
        self.smufl_name = smufl_name
        (self.x_canonical, self.y_canonical,
         self.width_canonical, self.height_canonical) = box


class TestGatherNoteheadInk(unittest.TestCase):
    """`gather.gather_notehead_ink` -- the orchestration, on a fake cell.

    ⚠️ `Q.NOTEHEAD_INK` is a GATHER quantity, not an ADJUDICATE decision --
    `Log.verdict()` resolves only `Verdict` rows, so these read the raw
    `Observation`/`Abstention` rows directly (`log.rows`/`log.refusals`),
    exactly as the record itself distinguishes READ from DECLINED
    (`Log.state`)."""

    def _run(self, *, binary=None, image_no_staff=None,
             cls="noteheadBlackOnLine"):
        box = _box()
        c = _FakeCell(binary=binary, image_no_staff=image_no_staff)
        local = {0: (0, 0)}
        sub = R.cell(0, 0, 0, 0)
        detections = {sub.to_key(): [_FakeDetection(cls, box)]}
        log = Log()
        gather.gather_notehead_ink(log, [c], local, detections)
        log.freeze()
        return log, R.glyph(0, 0, 0, 0, 0)

    def test_files_the_max_of_both_rasters(self):
        raw = _paper()
        _fill_ellipse(raw, _box())          # raw shows a real head
        net = _paper()                      # erased raster: nothing left
        log, g = self._run(binary=raw, image_no_staff=net)
        self.assertEqual(log.state(Q.NOTEHEAD_INK, g), R.State.READ)
        row = log.rows(Q.NOTEHEAD_INK, g)[-1]
        self.assertGreater(row.value, 0.4)
        self.assertIn("ink_raw", row.detail)
        self.assertIn("ink_net", row.detail)
        self.assertGreater(row.detail["ink_raw"]["best"], 0.4)
        self.assertEqual(row.detail["ink_net"]["best"], 0.0)

    def test_non_notehead_classes_are_not_measured_at_all(self):
        c = _FakeCell(binary=_paper(), image_no_staff=_paper())
        local = {0: (0, 0)}
        sub = R.cell(0, 0, 0, 0)
        detections = {sub.to_key(): [_FakeDetection("ledgerLine", _box())]}
        log = Log()
        gather.gather_notehead_ink(log, [c], local, detections)
        log.freeze()
        g = R.glyph(0, 0, 0, 0, 0)
        self.assertEqual(log.state(Q.NOTEHEAD_INK, g), R.State.ABSENT)

    def test_neither_raster_present_ABSTAINS_no_mask(self):
        log, g = self._run(binary=None, image_no_staff=None)
        self.assertEqual(log.state(Q.NOTEHEAD_INK, g), R.State.DECLINED)
        row = log.refusals(Q.NOTEHEAD_INK, g)[-1]
        self.assertEqual(row.reason, ABSTAIN.NO_MASK)


if __name__ == "__main__":       # pragma: no cover
    unittest.main()
