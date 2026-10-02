"""ROADMAP 2.39b EXTENSION -- cause A of the "8 far heads neither reader
gets right" (DECISIONS 2026-10-01, `lane-farhead-combined`,
`out/print/ledgers/neither_right_sheet.png` tile 1, partly tile 3): *"found
the correct ledger line but the box is small and only covers the top of
the half note"*. Litolff half notes often don't close their own oval, so
the detector's box sits mostly on blank paper -- and `recentre_notehead`'s
matched-window FILL search (ROADMAP 2.39b, first half) DECLINES there no
matter where the window sits, exactly as `test_staged_notehead_recentre.
py`'s own `test_a_hollow_head_declines_below_threshold` already shows for
a hollow ring.

This file tests the FALLBACK this round adds: where the fill search
declines AND the detector's own box is clearly SHORTER than the standard
head height (`gather.SHORT_BOX_HEIGHT_RATIO_MAX`), a second reader
(`gather._notehead_vertical_ink_extent`, filed as `READERS.CV_NOTEHEAD_
VERTICAL_EXTENT`) reads the oval's own ink EXTENT in a narrow central
column strip instead of its density -- a hollow ring still marks its own
top/bottom row even though its centre stays white. A box of NORMAL height
is left exactly as 2.39b's first half already leaves it (untouched); a
box short in height but with a GOOD fill (filled head population, not
hollow) keeps using the original fill-based recentre, unchanged.

⚠️ RUN RED FIRST: `gather._notehead_vertical_ink_extent`,
`gather.SHORT_BOX_HEIGHT_RATIO_MAX` and `READERS.CV_NOTEHEAD_VERTICAL_
EXTENT` do not exist before this round -- every reference below raises
`AttributeError`.
"""
from __future__ import annotations

import unittest
import types

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q, READERS, State
from tools.omr.types import MeasureCell

SPACING = 40.0  # px per staff space, canonical -- mirrors the sibling file


def _paper(h=300, w=300):
    return np.full((h, w), 255, dtype=np.uint8)


def _fill_ellipse(img, cx, cy, w, h):
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    a, b = max(1.0, w / 2.0), max(1.0, h / 2.0)
    img[((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2 <= 1.0] = 0


def _ring(img, cx, cy, w, h, thickness):
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    a, b = w / 2.0, h / 2.0
    outer = ((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2 <= 1.0
    a2, b2 = max(1.0, a - thickness), max(1.0, b - thickness)
    inner = ((xx - cx) / a2) ** 2 + ((yy - cy) / b2) ** 2 <= 1.0
    img[outer & ~inner] = 0


def _open_oval_top_half(img, cx, cy, w, h, thickness):
    """A half note whose oval does NOT fully close -- the Litolff shape the
    decision names: the ring is inked everywhere except a small gap at its
    own bottom tip, same as a real unclosed engraving (most of the oval,
    including both sides near the middle, is still printed -- only the
    very bottom stays open)."""
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    a, b = w / 2.0, h / 2.0
    outer = ((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2 <= 1.0
    a2, b2 = max(1.0, a - thickness), max(1.0, b - thickness)
    inner = ((xx - cx) / a2) ** 2 + ((yy - cy) / b2) ** 2 <= 1.0
    ring = outer & ~inner
    ring[yy > cy + 0.25 * b] = False  # erase only the bottom-most sliver
    img[ring] = 0


class TestVerticalInkExtent(unittest.TestCase):
    """`gather._notehead_vertical_ink_extent` -- pure, on synthetic rasters."""

    def test_a_filled_head_returns_its_own_full_extent(self):
        img = _paper()
        w = gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
        h = gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
        _fill_ellipse(img, 150.0, 150.0, w, h)
        extent = gather._notehead_vertical_ink_extent(
            img, 150.0, 150.0, SPACING, gather.STANDARD_HEAD_WIDTH_SPACES)
        self.assertIsNotNone(extent)
        y0, y1 = extent
        self.assertLess(abs((y0 + y1) / 2.0 - 150.0), 2.0)
        self.assertGreater(y1 - y0, h * 0.7)

    def test_an_unclosed_half_note_still_finds_its_own_top_edge(self):
        """⚠️ THE CASE THE BRIEF NAMES: an oval that never closes at the
        bottom still marks ink at its own top -- the extent's own top row
        must sit near the TRUE oval's top, not near the detector's short
        box (which this function never reads at all)."""
        img = _paper()
        w = gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
        h = gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
        _open_oval_top_half(img, 150.0, 150.0, w, h, thickness=4.0)
        extent = gather._notehead_vertical_ink_extent(
            img, 150.0, 150.0, SPACING, gather.STANDARD_HEAD_WIDTH_SPACES)
        self.assertIsNotNone(extent)
        y0, _ = extent
        true_top = 150.0 - h / 2.0
        self.assertLess(abs(y0 - true_top), 4.0)

    def test_a_staff_line_crossing_the_strip_is_masked_out(self):
        """A thin, FULL-WIDTH line (staff or ledger) passing through the
        search band must not be read as the oval's own cap -- it is
        masked because it keeps going well past the head, unlike a real
        cap which stops at the head's own edges."""
        img = _paper()
        w = gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
        h = gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
        _fill_ellipse(img, 150.0, 150.0, w, h)
        # A ledger-shaped stroke, full raster width, well above the head.
        line_y = 150.0 - h / 2.0 - 0.6 * SPACING
        img[int(line_y) - 1:int(line_y) + 1, :] = 0
        extent = gather._notehead_vertical_ink_extent(
            img, 150.0, 150.0, SPACING, gather.STANDARD_HEAD_WIDTH_SPACES)
        self.assertIsNotNone(extent)
        y0, y1 = extent
        # The masked line sits outside the returned extent.
        self.assertGreater(y0, line_y)

    def test_no_ink_in_the_strip_returns_none(self):
        img = _paper()
        extent = gather._notehead_vertical_ink_extent(
            img, 150.0, 150.0, SPACING, gather.STANDARD_HEAD_WIDTH_SPACES)
        self.assertIsNone(extent)

    def test_no_image_returns_none(self):
        self.assertIsNone(gather._notehead_vertical_ink_extent(
            None, 150.0, 150.0, SPACING, gather.STANDARD_HEAD_WIDTH_SPACES))

    def test_no_spacing_returns_none(self):
        img = _paper()
        self.assertIsNone(gather._notehead_vertical_ink_extent(
            img, 150.0, 150.0, 0.0, gather.STANDARD_HEAD_WIDTH_SPACES))


def _detection(name, x_center, y_center, w=None, h=None):
    w = w if w is not None else gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
    h = h if h is not None else gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
    return types.SimpleNamespace(
        smufl_name=name,
        x_canonical=x_center - w / 2.0, y_canonical=y_center - h / 2.0,
        width_canonical=w, height_canonical=h,
        x_center=x_center, y_center=y_center)


#: Gaps of 40px between lines -> `half_step = 20.0` -> `space_canonical ==
#: SPACING` (40.0), the SAME unit every ellipse/ring above is drawn in.
def _cell(img, staff_lines=(10.0, 50.0, 90.0, 130.0, 170.0)):
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img, bbox_page_px=(0, 0, 300, 300),
        staff_line_ys_canonical=list(staff_lines), upscale_factor=1.0)


class TestGatherNoteheadRecentreShortBoxFallback(unittest.TestCase):
    """`gather.gather_notehead_recentre` -- the short-box fallback wired
    into the real GATHER reader, same shape `test_staged_notehead_
    recentre.py`'s own `TestGatherNoteheadRecentreWiring` already uses."""

    def _run(self, img, *, cx=150.0, cy=150.0, w, h,
            name="noteheadHalfInSpace"):
        cell = _cell(img)
        sub = R.cell(0, 0, 0, 0)
        d = _detection(name, cx, cy, w=w, h=h)
        log = Log()
        gather.gather_notehead_recentre(log, [cell], {0: (0, 0)},
                                        {sub.to_key(): [d]})
        g = R.glyph(0, 0, 0, 0, 0)
        return log, g

    def test_a_short_box_on_a_hollow_head_is_recentred_by_extent(self):
        """⚠️ THE CASE THIS ROUND EXISTS FOR: a SHORT box (height ratio
        well under `SHORT_BOX_HEIGHT_RATIO_MAX`) on a HOLLOW head -- the
        fill search declines on it (a ring's own interior is sparse no
        matter where the window sits, exactly `test_staged_notehead_
        recentre.py`'s own `test_a_hollow_head_declines_below_threshold`),
        so the extent fallback must take over, find the ring's own top
        AND bottom caps, and re-centre toward their midpoint -- filed
        under its own reader name, moving DOWN from the detector's
        too-high short box toward the oval's true middle."""
        img = _paper()
        true_w = gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
        true_h = gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
        _ring(img, 150.0, 150.0, true_w, true_h, thickness=4.0)
        # The detector's own box: short (covers only the TOP of the oval),
        # centred on the oval's own top edge -- exactly Sean's description.
        short_h = 0.3 * true_h
        box_cy = 150.0 - true_h / 2.0 + short_h / 2.0
        log, g = self._run(img, cy=box_cy, w=true_w, h=short_h)
        self.assertEqual(log.state(Q.NOTEHEAD_RECENTRE, g), State.READ)
        row = log.rows(Q.NOTEHEAD_RECENTRE, g)[0]
        self.assertEqual(row.reader, READERS.CV_NOTEHEAD_VERTICAL_EXTENT)
        dx_sp, dy_sp = row.value
        self.assertEqual(dx_sp, 0.0)
        new_cy = box_cy + dy_sp * SPACING
        self.assertLess(abs(new_cy - 150.0), SPACING * 0.15)

    def test_a_gap_at_the_very_bottom_still_finds_the_top_cap(self):
        """An oval whose bottom does not fully close (a narrow notch, the
        Litolff shape the decision names) still has its TOP cap read
        correctly by the pure extent function -- the sibling pure-function
        test above its own class, exercised again through the full
        GATHER wiring: the short box still moves toward the ink that IS
        there, never left untouched."""
        img = _paper()
        true_w = gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
        true_h = gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
        _open_oval_top_half(img, 150.0, 150.0, true_w, true_h, thickness=4.0)
        short_h = 0.3 * true_h
        box_cy = 150.0 - true_h / 2.0 + short_h / 2.0
        log, g = self._run(img, cy=box_cy, w=true_w, h=short_h)
        self.assertEqual(log.state(Q.NOTEHEAD_RECENTRE, g), State.READ)
        row = log.rows(Q.NOTEHEAD_RECENTRE, g)[0]
        self.assertEqual(row.reader, READERS.CV_NOTEHEAD_VERTICAL_EXTENT)
        # The found extent's own top sits near the true oval's top edge,
        # not merely restating the detector's own already-short box.
        true_top = 150.0 - true_h / 2.0
        self.assertLess(abs(row.detail["ink_y0"] - true_top), 4.0)
        self.assertIn("original_box", row.detail)
        self.assertEqual(row.detail["original_box"][1], box_cy)

    def test_a_normal_height_box_is_left_exactly_as_is(self):
        """A box of NORMAL height (ratio >= `SHORT_BOX_HEIGHT_RATIO_MAX`)
        never reaches the extent fallback at all -- `RECENTRE_BOX_SIZE_
        GATE` already covers it (it is also close to standard WIDTH here,
        so the search never even runs): unchanged behaviour from before
        this round."""
        img = _paper()
        w = gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
        h = gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
        _fill_ellipse(img, 150.0, 150.0, w, h)
        log, g = self._run(img, w=w, h=h)
        self.assertEqual(log.state(Q.NOTEHEAD_RECENTRE, g), State.DECLINED)
        reason = log.refusals(Q.NOTEHEAD_RECENTRE, g)[0].reason
        self.assertEqual(reason, ABSTAIN.BOX_ALREADY_HEAD_SIZED)

    def test_a_short_box_on_a_filled_head_still_uses_the_fill_search(self):
        """A short box sitting on a FILLED (non-hollow) head: the fill
        search succeeds on its own (plenty of dense ink to find), so the
        extent fallback must never even run -- `CV_NOTEHEAD_RECENTRE`
        stays the reader, unchanged from before this round."""
        img = _paper()
        true_w = gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
        true_h = gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
        _fill_ellipse(img, 150.0, 150.0, true_w, true_h)
        short_h = 0.3 * true_h
        log, g = self._run(img, cy=150.0, w=true_w, h=short_h)
        self.assertEqual(log.state(Q.NOTEHEAD_RECENTRE, g), State.READ)
        row = log.rows(Q.NOTEHEAD_RECENTRE, g)[0]
        self.assertEqual(row.reader, READERS.CV_NOTEHEAD_RECENTRE)

    def test_a_short_box_with_no_ink_anywhere_still_declines(self):
        """Neither the fill search nor the extent fallback finds anything
        -- declined, never a guessed shift (CLAUDE.md rule 8)."""
        img = _paper()
        true_h = gather.STANDARD_HEAD_HEIGHT_SPACES * SPACING
        true_w = gather.STANDARD_HEAD_WIDTH_SPACES * SPACING
        short_h = 0.3 * true_h
        log, g = self._run(img, w=true_w, h=short_h)
        self.assertEqual(log.state(Q.NOTEHEAD_RECENTRE, g), State.DECLINED)
        reason = log.refusals(Q.NOTEHEAD_RECENTRE, g)[0].reason
        self.assertEqual(reason, ABSTAIN.BELOW_THRESHOLD)


if __name__ == "__main__":
    unittest.main()
