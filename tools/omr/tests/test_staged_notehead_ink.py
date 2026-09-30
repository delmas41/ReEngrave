"""A head's fill (hollow vs black), read from the ink -- ROADMAP 2.23.

⚠️ WHY THIS FILE EXISTS. `benchmarks/omr-bar-sum-holdout-2026-09/
FINDINGS.md` §17b: on Litolff 1/i the single biggest minimal-fix class over
the whole movement's held bars is `F` (300 bars, 405 released as the sole
fix) -- a hollow (half/whole) notehead read as BLACK on this MERGING plate
(CLAUDE.md §10).

This file tests only the GATHER half, ported from `claude/no-ink-head-2.6h`
(`a8394476`): `gather.notehead_ink_under` / `gather_notehead_ink`, the ink
fraction inside a notehead's OWN box, two ways (`center`, `ring`), off BOTH
the UNERASED canonical raster (`cell.binary`) and the staff-ERASED one
(`cell.image_no_staff`). The ADJUDICATE half this port adds is exercised in
`test_staged_rhythm.py` (`TestHeadFillFromInk`), not here.

⚠️ RUN RED FIRST: every test below fails with `AttributeError`
(`gather.notehead_ink_under` / `gather.gather_notehead_ink` /
`Q.NOTEHEAD_INK` absent) against the tree before this change.
"""

from __future__ import annotations

import unittest

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import CLAIM, Log, Q


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
        """⚠️⚠️ THE POSITIVE CONTROL: a hollow (half/whole) head's own
        middle is near-empty by design, and must never be read as blank --
        `ring` is its witness, not `center`."""
        img = _paper()
        box = _box()
        _ring(img, box, thickness=6)
        m = gather.notehead_ink_under(img, box)
        self.assertGreater(m["best"], 0.2)
        self.assertEqual(m["best_window"], "ring")
        self.assertLess(m["windows"]["center"], 0.15)

    def test_a_STAFF_LINE_ALONE_crossing_the_box_is_a_KNOWN_LIMITATION(self):
        """⚠️ NOT A SAFETY PROPERTY OF THIS FUNCTION ALONE -- the actual
        defence against "staff-line pixels alone read as ink" is the
        DUAL-RASTER design one level up (`gather_notehead_ink`, tested
        below): the same line is read on the staff-ERASED raster too,
        where it is gone."""
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
        shrink -- left `None`, never invented."""
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

    def __init__(self, staff_index=0, *, binary=None, image_no_staff=None,
                staff_line_ys_canonical=None):
        self.staff_index = staff_index
        if binary is not None:
            self.binary = binary
        if image_no_staff is not None:
            self.image_no_staff = image_no_staff
        if staff_line_ys_canonical is not None:
            self.staff_line_ys_canonical = staff_line_ys_canonical


class _FakeDetection:
    def __init__(self, smufl_name, box):
        self.smufl_name = smufl_name
        (self.x_canonical, self.y_canonical,
         self.width_canonical, self.height_canonical) = box

    @property
    def x_center(self):
        return self.x_canonical + self.width_canonical / 2.0

    @property
    def y_center(self):
        return self.y_canonical + self.height_canonical / 2.0


class TestGatherNoteheadInk(unittest.TestCase):
    """`gather.gather_notehead_ink` -- the orchestration, on a fake cell.

    ⚠️ `Q.NOTEHEAD_INK` is a GATHER quantity, not an ADJUDICATE decision --
    `Log.verdict()` resolves only `Verdict` rows, so these read the raw
    `Observation`/`Abstention` rows directly (`log.rows`/`log.state`)."""

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

    def test_a_hollow_head_files_via_the_ring_on_either_raster(self):
        raw = _paper()
        _ring(raw, _box(), thickness=6)
        log, g = self._run(binary=raw, image_no_staff=None)
        row = log.rows(Q.NOTEHEAD_INK, g)[-1]
        self.assertEqual(row.detail["ink_raw"]["best_window"], "ring")
        self.assertLess(row.detail["ink_raw"]["windows"]["center"], 0.15)

    def test_non_notehead_classes_are_not_gathered(self):
        log, g = self._run(binary=_paper(), image_no_staff=_paper(),
                           cls="clefG")
        self.assertEqual(list(log.rows(Q.NOTEHEAD_INK, g)), [])

    def test_neither_raster_present_abstains_no_mask(self):
        log, g = self._run(binary=None, image_no_staff=None)
        self.assertEqual(log.state(Q.NOTEHEAD_INK, g), R.State.DECLINED)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.39 -- the standard head box, where the cell has a staff unit
# ─────────────────────────────────────────────────────────────────────────────
#
# ⚠️ RUN RED FIRST: `_FakeCell(staff_line_ys_canonical=...)`, `_FakeDetection
# .x_center`/`.y_center` did not exist before this round -- every test below
# either raised `AttributeError` or (once those were added, as this file's
# other classes need them too) asserted a `box` argument
# `gather.notehead_ink_under` never received before this change.

class TestGatherNoteheadInkStandardBox(unittest.TestCase):
    """Spies on `gather.notehead_ink_under` (not `detail`, which nothing
    else would read -- `wiring --check`'s own rule) to see which `box`
    `gather_notehead_ink` actually asked it to measure."""

    def _boxes_used(self, *, cls, staff_line_ys_canonical=None):
        box = _box()      # 52 x 40 canonical, centred (100, 100)
        raw = _paper()
        _fill_ellipse(raw, box)
        c = _FakeCell(binary=raw, image_no_staff=_paper(),
                     staff_line_ys_canonical=staff_line_ys_canonical)
        local = {0: (0, 0)}
        sub = R.cell(0, 0, 0, 0)
        detections = {sub.to_key(): [_FakeDetection(cls, box)]}
        seen = []
        real = gather.notehead_ink_under

        def spy(img, box):
            seen.append(box)
            return real(img, box)

        gather.notehead_ink_under = spy
        try:
            log = Log()
            gather.gather_notehead_ink(log, [c], local, detections)
        finally:
            gather.notehead_ink_under = real
        return seen, box     # (boxes actually used, the raw detector box)

    def test_no_staff_geometry_falls_back_to_the_detector_box(self):
        """The pre-2.39 invariant: this reader never needs a staff unit."""
        seen, raw_box = self._boxes_used(cls="noteheadBlackOnLine",
                                         staff_line_ys_canonical=None)
        self.assertTrue(all(b == raw_box for b in seen))

    def test_regular_head_with_staff_geometry_uses_the_standard_box(self):
        seen, raw_box = self._boxes_used(
            cls="noteheadBlackOnLine",
            staff_line_ys_canonical=[0.0, 20.0, 40.0, 60.0, 80.0])
        self.assertTrue(all(b != raw_box for b in seen))
        # centred the same (100, 100); 1.4 x 1.1 spaces at spacing 20 ==
        # 28 x 22, not the raw box's 52 x 40.
        x, y, w, h = seen[0]
        self.assertAlmostEqual(x + w / 2.0, 100.0)
        self.assertAlmostEqual(y + h / 2.0, 100.0)
        self.assertAlmostEqual(w, 28.0)
        self.assertAlmostEqual(h, 22.0)

    def test_whole_note_keeps_the_detector_box_even_with_staff_geometry(self):
        """ROADMAP 2.39 item 5: a whole note is a different, wider Bravura
        shape this round did not measure."""
        seen, raw_box = self._boxes_used(
            cls="noteheadWhole",
            staff_line_ys_canonical=[0.0, 20.0, 40.0, 60.0, 80.0])
        self.assertTrue(all(b == raw_box for b in seen))

    def test_small_grace_cue_head_keeps_the_detector_box(self):
        seen, raw_box = self._boxes_used(
            cls="noteheadBlackSmall",
            staff_line_ys_canonical=[0.0, 20.0, 40.0, 60.0, 80.0])
        self.assertTrue(all(b == raw_box for b in seen))


if __name__ == "__main__":
    unittest.main()
