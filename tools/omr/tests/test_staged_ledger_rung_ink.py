"""ROADMAP 2.6d — a far head's ledger rungs are READ from the ink (CV), not
only from the detector's boxes.

⚠️ WHY THIS FILE EXISTS. 2.6c.2 made the ledger lines a HARD GATE
(`ownership.ledger_direction`) and a far note with no rung found either way
now abstains `far_no_rungs`, dropped at export as `owner_not_read`
(FINDINGS `benchmarks/omr-owner-domain-2026-09/FINDINGS.md` §2.6c.2). On the
saved 27b arm records ALL 655 of those abstentions are `nothing_boxed_at_
any_step` — no `ledgerLine` box, kept or refused, at any step toward any
candidate — and two of the eight crops cut for Sean show printed ledger
lines the detector never boxed. Today a rung is named ONLY from
`Q.GLYPH_BOX`. This is the second reader: `Q.LEDGER_RUNG_INK`
(`gather.ledger_rung_ink`, `gather._observe_ledger_rung_ink`), read off the
staff-erased raster at the SAME step arithmetic `_observe_ladder` already
uses, merged into the ONE ledger helper (`ownership.cv_rungs`,
`ownership.ledger_direction`) both `glyph_owner` and 2.7b's
`belongs_to_a_nearer_staff` ask.

⚠️ RUN RED FIRST: every test below either fails to import (`gather.ledger_
rung_ink`, `gather._observe_ledger_rung_ink` and `ownership.cv_rungs` do not
exist on `c2ab5f55`) or, for `TestALadderWithNoCVWitnessStillAbstains` and
`TestWithNoLedgerEvidenceTheHeadIsRefused`, is the shape 2.6c.2 already
shipped RED against — kept here as the negative control a positive-control
discipline requires (CLAUDE.md §6b: *"a refusal test needs a positive
control in the same class, or it passes by refusing everything"*).
"""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from tools.omr.staged import adjudicate, gather
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import ownership as OWN
from tools.omr.staged.record import Log, Outcome, Q, READERS

# ─────────────────────────────────────────────────────────────────────────────
# Part 1 — the pure measurement, on synthetic rasters (0 = ink)
# ─────────────────────────────────────────────────────────────────────────────

SP = 20.0                      # one staff space, canonical px
HEAD_X0, HEAD_X1 = 190.0, 210.0   # a head 20px (1 space) wide, centred on 200
CY = 200.0                       # the tested y


def _paper(h=400, w=400):
    return np.full((h, w), 255, dtype=np.uint8)


def _draw(img, x0, y0, x1, y1):
    img[int(round(y0)):int(round(y1)), int(round(x0)):int(round(x1))] = 0


class TestTheMeasurement(unittest.TestCase):
    """`gather.ledger_rung_ink` — a windowed ink-density ruler, no identity,
    no ownership. All coordinates already in the raster's own canonical
    frame, exactly as the caller (`_observe_ledger_rung_ink`) hands them."""

    def _measure(self, img, thickness_px=None):
        return gather.ledger_rung_ink(img, HEAD_X0, HEAD_X1, CY, SP,
                                      thickness_px)

    def test_a_real_rung_crossing_and_past_the_head_is_found(self):
        """A stroke wider than the head, thin, centred at the tested y."""
        img = _paper()
        _draw(img, 182, 197, 218, 203)
        m = self._measure(img)
        self.assertTrue(m["found"])
        self.assertGreaterEqual(m["center"], gather.LEDGER_RUNG_INK_DENSE)
        self.assertGreaterEqual(m["left"], gather.LEDGER_RUNG_INK_DENSE)
        self.assertGreaterEqual(m["right"], gather.LEDGER_RUNG_INK_DENSE)

    def test_POSITIVE_CONTROL_the_guard_can_be_satisfied(self):
        """⚠️ THE CONTROL, RUN FAILING FIRST: the exact same draw with the
        head narrowed so the SAME ink no longer reaches past its edges —
        a lone stem's shape — must NOT be found. Proves the overhang test
        can fail, not only pass."""
        img = _paper()
        _draw(img, 182, 197, 218, 203)
        m = gather.ledger_rung_ink(img, 178.0, 222.0, CY, SP, None)
        self.assertFalse(m["found"])

    def test_a_stem_only_does_not_reach_past_the_head(self):
        """Ink confined to the head's OWN x-span (a stem, or the head's
        stroke itself): centre reads dense, neither overhang bin does."""
        img = _paper()
        _draw(img, 195, 190, 205, 210)
        m = self._measure(img)
        self.assertFalse(m["found"])
        self.assertLess(m["left"], gather.LEDGER_RUNG_INK_DENSE)
        self.assertLess(m["right"], gather.LEDGER_RUNG_INK_DENSE)

    def test_a_thick_blob_fails_the_adjacent_band_guard(self):
        """A beam-like stroke crossing the whole window AND tall enough that
        the bands immediately above and below are just as inked -- the
        guard against a thick shape passing as a thin rung."""
        img = _paper()
        _draw(img, 182, 185, 218, 215)      # 30px tall, dwarfing the window
        m = self._measure(img)
        self.assertFalse(m["found"])
        self.assertGreater(m["adjacent"], gather.LEDGER_RUNG_INK_ADJACENT_MAX)

    def test_nothing_here_is_not_found(self):
        img = _paper()
        m = self._measure(img)
        self.assertFalse(m["found"])

    def test_window_off_the_raster_is_none(self):
        img = _paper(h=6, w=400)
        m = self._measure(img)
        self.assertIsNone(m)

    def test_no_unit_no_measurement(self):
        img = _paper()
        self.assertIsNone(gather.ledger_rung_ink(img, HEAD_X0, HEAD_X1, CY,
                                                 0.0, None))

    def test_a_measured_staff_line_thickness_is_honoured(self):
        """The tested band scales with the caller-supplied thickness: ink
        drawn to exactly fill a THIN measured line's band is found there,
        and the SAME ink read against a much WIDER assumed thickness -- so
        the tested band reaches well past it into bare paper -- is not. The
        thickness parameter is load-bearing, not decorative."""
        thin_px = 2.0
        pad = gather.LEDGER_RUNG_INK_THICKNESS_PAD_SPACES * SP
        half_h = thin_px / 2.0 + pad
        img = _paper()
        _draw(img, 182, CY - half_h, 218, CY + half_h)
        thin = gather.ledger_rung_ink(img, HEAD_X0, HEAD_X1, CY, SP,
                                      thickness_px=thin_px)
        self.assertTrue(thin["found"])
        wide = gather.ledger_rung_ink(img, HEAD_X0, HEAD_X1, CY, SP,
                                      thickness_px=thin_px * 20)
        self.assertFalse(wide["found"])


# ─────────────────────────────────────────────────────────────────────────────
# Part 1b — a REAL printed rung, cut from the page (CALIBRATION, 2026-09-29)
#
# Manager follow-up on the first landing: `found=True` fired on ZERO of 876
# windows measured on the two acceptance-set pages, so before merging,
# calibrate on a POSITIVE case. Sean's own 2.6c.2 crops
# (`benchmarks/omr-owner-domain-2026-09/out/print/2.6c-far-*-manifest.json`)
# are real `far_no_rungs` heads; read visually (all 8), only ONE shows an
# unambiguous printed ledger line: Breitkopf pdf idx 22, `glyph/22/1/6/10/2`
# toward `staff/22/1/6` -- a notehead with a ledger line visibly crossing it,
# wings poking out both sides (`out/print/2.6c-far-breitkopf-03.png`, its own
# zoom confirms it). A one-page re-gather measured it and MISSED it:
# `left=0.5126` against the 0.55 `DENSE` floor, `right=0.6632` passing --
# the overhang test was averaging density over the WHOLE context window
# (0.375 head widths) and a short wing was diluted by the blank paper past
# it. `LEDGER_RUNG_INK_OVERHANG_TEST_FRAC` narrows the tested band to sit
# right at the edge (0.20 head widths); re-measured, `found=True`.
#
# `ledger_rung_ink_brk_p22_real.png` is the EXACT canonical raster this
# lane's own re-gather sampled (dumped from inside `_observe_ledger_rung_
# ink` for this one (glyph, candidate) pair, cropped to the two tested
# steps with margin) -- not redrawn, not re-rendered at a different DPI or
# scale, so this test exercises the real ink, not an approximation of it.
# ─────────────────────────────────────────────────────────────────────────────

REAL_RUNG_FIXTURE = (Path(__file__).parent / "fixtures"
                    / "ledger_rung_ink_brk_p22_real.png")
#: The head's own canonical x-span in the fixture's OWN frame (a crop, so
#: these are relative to the crop's origin, not the page).
REAL_RUNG_HEAD_X = (150.0, 291.0)
#: The two tested steps' y, in the SAME frame -- step 1 (nearer the staff,
#: adjacent-guard rejects it: this ink sits close enough to the staff that
#: the guard's "one band further up" reads staff ink, an OPEN finding, not
#: fixed here) and step 2 (the one this calibration confirms).
REAL_RUNG_STEP1_Y = 70.165137614679
REAL_RUNG_STEP2_Y = 170.165137614679
REAL_RUNG_SPACE_C = 100.0
REAL_RUNG_THICKNESS_C = 29.357798165137616


class TestAdjacentExcludesTheHeadsOwnBox(unittest.TestCase):
    """ROADMAP 2.37 (manager print check, ROUND 2, 2026-09-29). A fresh
    re-gather of both acceptance-set pages with THIS branch tabulated,
    per failing `det_all` row (detector boxed every expected rung), which
    named condition actually blocked it: `wide_adjacent` (the ORIGINAL,
    head-centred guard) was the dominant failure -- 32 of 37 Litolff p3
    rows, 84 of 119 Brahms p1. Manager's hypothesis, confirmed: for the
    rung THROUGH the head or one space beyond it, the head's OWN solid
    ink sits inside "one band further away", read as false "thick"
    evidence against its own real, thin rung. The head is `ev.subject`,
    already known -- `_exclude_head_box` removes exactly its own rows
    from every adjacent test (wide and per-side), never any other ink.
    Re-gathered after the fix: Brahms p1 `det_all` pairs with ANY step
    found rose 19/82 -> 43/82; Litolff p3 barely moved (1/23 -> 2/23,
    left/right DENSE itself is the remaining blocker there, a SEPARATE,
    not-yet-understood question for the MERGING plate)."""

    def test_no_overlap_is_unchanged(self):
        self.assertEqual(gather._exclude_head_box(100.0, 110.0, 50.0, 60.0),
                         (100.0, 110.0))

    def test_head_fully_covers_the_band_is_none(self):
        self.assertIsNone(gather._exclude_head_box(100.0, 110.0, 90.0, 120.0))

    def test_head_overlaps_the_near_side_keeps_the_far_side(self):
        """The head's box starts inside the band (its bottom, say, sits a
        little into the band tested just below it) -- only the portion
        BEYOND the head survives."""
        self.assertEqual(gather._exclude_head_box(100.0, 110.0, 80.0, 104.0),
                         (104.0, 110.0))

    def test_head_overlaps_the_far_side_keeps_the_near_side(self):
        self.assertEqual(gather._exclude_head_box(100.0, 110.0, 106.0, 130.0),
                         (100.0, 106.0))

    def test_no_head_box_known_is_unchanged(self):
        """An old caller, or one with no page geometry for the head, still
        gets exactly the un-excluded band -- never a crash, never a
        different answer where the exclusion cannot be computed."""
        self.assertEqual(gather._exclude_head_box(100.0, 110.0, None, None),
                         (100.0, 110.0))

    def test_a_rung_through_the_head_is_now_found(self):
        """RED before this round: the head's own tall body sat inside the
        wide adjacent band above AND below a rung tested at its own
        centre, so a real, thin, fully-overhanging rung was refused as
        'thick'. The head's box is passed and excluded; the SAME ink is
        now found."""
        img = _paper(h=400, w=400)
        # the head: a tall solid block (200x30), simulating its own body
        _draw(img, 185, 185, 215, 215)
        # the rung: thin, at the head's OWN centre, crossing well past it
        _draw(img, 175, 197, 225, 203)
        head_y0, head_y1 = 185.0, 215.0
        without = gather.ledger_rung_ink(img, HEAD_X0, HEAD_X1, CY, SP, None)
        withh = gather.ledger_rung_ink(img, HEAD_X0, HEAD_X1, CY, SP, None,
                                       head_y0=head_y0, head_y1=head_y1)
        self.assertFalse(without["found"])
        self.assertTrue(withh["found"])


class TestDeclineOnUnreadableAdjacent(unittest.TestCase):
    """ROADMAP 2.37 (manager print check, round 3, 2026-09-29): a step
    whose density looked like a real rung but whose ADJACENT evidence
    (wide or per-side) could not be read AT ALL -- off the raster, never
    the head's own KNOWN, safely-excluded box -- must DECLINE (`None`,
    the same "cannot tell" signal a caller already treats as an
    abstention), not silently default a missing "cannot rule out thick"
    into "clean". Measured against the real re-gather: both confound-
    control false positives round 2 introduced were exactly this shape
    (`left_adjacent`/`right_adjacent`/`adjacent` all `None`, density alone
    cleared)."""

    def test_declines_when_the_raster_cannot_test_adjacent_at_all(self):
        """A real, dense, fully-overhanging rung -- but the raster is only
        as tall as the tested band itself, so NEITHER the above nor the
        below comparison band has anywhere left to read (genuinely off
        the raster, no head box declared at all). RED before this round:
        the OLD `adjacent is None` fallback defaulted this straight to
        `found=True`."""
        img = _paper(h=7, w=400)
        half_h = gather.LEDGER_RUNG_INK_DEFAULT_THICKNESS_SPACES * SP / 2.0 \
            + gather.LEDGER_RUNG_INK_THICKNESS_PAD_SPACES * SP
        cy = half_h + 0.2       # the tightest fit that still lets y0 round to 0
        _draw(img, 175, cy - half_h, 225, cy + half_h)
        m = gather.ledger_rung_ink(img, HEAD_X0, HEAD_X1, cy, SP, None)
        self.assertIsNone(m)

    def test_a_rung_through_the_head_is_not_declined_over_the_SAME_raster(self):
        """POSITIVE CONTROL: identical geometry (the adjacent bands reach
        off the SAME short raster), but this time the head's own box is
        declared and covers those bands -- a KNOWN, safe exclusion, not
        "cannot tell". This must still be FOUND, never declined."""
        img = _paper(h=7, w=400)
        half_h = gather.LEDGER_RUNG_INK_DEFAULT_THICKNESS_SPACES * SP / 2.0 \
            + gather.LEDGER_RUNG_INK_THICKNESS_PAD_SPACES * SP
        cy = half_h + 0.2
        _draw(img, 175, cy - half_h, 225, cy + half_h)
        m = gather.ledger_rung_ink(img, HEAD_X0, HEAD_X1, cy, SP, None,
                                   head_y0=-1000.0, head_y1=1000.0)
        self.assertIsNotNone(m)
        self.assertTrue(m["found"])

    def test_a_confirmed_thick_stroke_is_a_negative_not_a_decline(self):
        """POSITIVE CONTROL: the adjacent band IS readable and genuinely
        dense (a real thick blob) -- a confirmed block is `found=False`,
        never a decline; declining is for MISSING evidence only, not for
        evidence that positively says "thick"."""
        img = _paper()
        _draw(img, 182, 185, 218, 215)     # tall, dwarfing the window
        m = gather.ledger_rung_ink(img, HEAD_X0, HEAD_X1, CY, SP, None)
        self.assertIsNotNone(m)
        self.assertFalse(m["found"])


class TestOneSidedWing(unittest.TestCase):
    """ROADMAP 2.37 (manager print check, 2026-09-29): real Brahms p1 crops
    (`out/print/beam-stem-ink-2.38/brahms_ledger_missed.png`, 33 of 39
    `det_all` pairs -- the detector boxed EVERY expected rung, yet this
    reader found none) measured a genuine wing reading dense on the side
    it actually extends (0.558-0.622) and weak on the other (0.266-0.371)
    -- a short, asymmetric wing, not a stem. RED before this change: the
    ORIGINAL predicate (`center and left and right`) refuses a real wing
    that only clears the `DENSE` floor on ONE side."""

    def test_a_wing_on_only_the_right_is_found(self):
        img = _paper()
        _draw(img, 190, 197, 218, 203)      # crosses centre, extends RIGHT
        m = gather.ledger_rung_ink(img, HEAD_X0, HEAD_X1, CY, SP, None)
        self.assertTrue(m["found"])
        self.assertGreaterEqual(m["right"], gather.LEDGER_RUNG_INK_DENSE)
        self.assertLess(m["left"], gather.LEDGER_RUNG_INK_DENSE)

    def test_a_wing_on_only_the_left_is_found(self):
        img = _paper()
        _draw(img, 182, 197, 210, 203)      # crosses centre, extends LEFT
        m = gather.ledger_rung_ink(img, HEAD_X0, HEAD_X1, CY, SP, None)
        self.assertTrue(m["found"])
        self.assertGreaterEqual(m["left"], gather.LEDGER_RUNG_INK_DENSE)
        self.assertLess(m["right"], gather.LEDGER_RUNG_INK_DENSE)

    def test_POSITIVE_CONTROL_neither_side_still_refuses(self):
        """The same centre-only ink as `test_a_stem_only_does_not_reach_
        past_the_head`, restated here as this class's own negative
        control: no overhang on EITHER side must still refuse."""
        img = _paper()
        _draw(img, 195, 197, 205, 203)
        m = gather.ledger_rung_ink(img, HEAD_X0, HEAD_X1, CY, SP, None)
        self.assertFalse(m["found"])

    def test_a_tall_stroke_on_one_side_still_refuses_that_side(self):
        """A TALL stroke attached at the head's right edge (a stem, not a
        wing): dense at `right` but ALSO dense one thickness further up
        and down IN THAT SAME narrow x-range -- the PER-SIDE guard, not
        the wide `adjacent` one (which only tests the head-centred `ww`
        span and would not by itself catch a stem sitting just outside
        it), is what must refuse this."""
        img = _paper()
        _draw(img, 190, 197, 210, 203)       # the centre, dense
        _draw(img, 210, 150, 214, 250)        # a tall stroke at the RIGHT band
        m = gather.ledger_rung_ink(img, HEAD_X0, HEAD_X1, CY, SP, None)
        self.assertFalse(m["found"])
        self.assertGreaterEqual(m["right"], gather.LEDGER_RUNG_INK_DENSE)
        self.assertGreater(m["right_adjacent"],
                           gather.LEDGER_RUNG_INK_ADJACENT_MAX)


class TestARealPrintedRung(unittest.TestCase):
    """`benchmarks/omr-owner-domain-2026-09/out/print/2.6c-far-breitkopf-03.
    png` shows it; this is the ink itself, byte-identical to what
    `_observe_ledger_rung_ink` sampled on the real page."""

    def _measure(self, y):
        img = np.array(Image.open(REAL_RUNG_FIXTURE))
        return gather.ledger_rung_ink(img, *REAL_RUNG_HEAD_X, y,
                                      REAL_RUNG_SPACE_C,
                                      REAL_RUNG_THICKNESS_C)

    def test_the_real_rung_is_found(self):
        """THE POSITIVE CASE: step 2, where the crop shows the ledger's
        wings crossing the notehead on both sides."""
        m = self._measure(REAL_RUNG_STEP2_Y)
        self.assertTrue(m["found"])
        self.assertGreaterEqual(m["center"], gather.LEDGER_RUNG_INK_DENSE)
        self.assertGreaterEqual(m["left"], gather.LEDGER_RUNG_INK_DENSE)
        self.assertGreaterEqual(m["right"], gather.LEDGER_RUNG_INK_DENSE)

    def test_RED_on_the_wider_overhang_window(self):
        """RED-before-the-fix control: the SAME real ink, tested with the
        pre-calibration overhang span (0.375 head widths, `head_w *
        LEDGER_RUNG_INK_WIDTH_HEAD_MULT` minus the head itself, halved) —
        reproduces the miss this lane found (`left` under `DENSE`), so the
        fixture is proven to distinguish the two thresholds and this is not
        a test that would pass regardless of the fix."""
        img = np.array(Image.open(REAL_RUNG_FIXTURE))
        head_w = REAL_RUNG_HEAD_X[1] - REAL_RUNG_HEAD_X[0]
        cx = sum(REAL_RUNG_HEAD_X) / 2.0
        ww = head_w * gather.LEDGER_RUNG_INK_WIDTH_HEAD_MULT
        thickness = REAL_RUNG_THICKNESS_C
        pad = gather.LEDGER_RUNG_INK_THICKNESS_PAD_SPACES * REAL_RUNG_SPACE_C
        half_h = thickness / 2.0 + pad
        y0, y1 = REAL_RUNG_STEP2_Y - half_h, REAL_RUNG_STEP2_Y + half_h
        ink = (img == 0)

        def frac(x0, x1, ya, yb):
            ix0, ix1 = max(0, int(round(x0))), min(img.shape[1], int(round(x1)))
            iy0, iy1 = max(0, int(round(ya))), min(img.shape[0], int(round(yb)))
            region = ink[iy0:iy1, ix0:ix1]
            return float(region.sum()) / float(region.size)

        left_wide = frac(cx - ww / 2.0, REAL_RUNG_HEAD_X[0], y0, y1)
        self.assertLess(left_wide, gather.LEDGER_RUNG_INK_DENSE,
                        "the wide window's own left density")

    def test_step_1_still_misses_it_the_adjacent_guard_open_finding(self):
        """NOT FIXED here, and pinned so a change to the guard shows up:
        step 1 sits close enough to the staff that the adjacent-band test
        reads dense (the staff itself, or ink the erasure left behind), so
        the SAME real rung's inner step is still rejected. `staged.check`
        and this test are how a future fix proves itself against this
        exact ink rather than a synthetic stand-in."""
        m = self._measure(REAL_RUNG_STEP1_Y)
        self.assertFalse(m["found"])
        self.assertGreaterEqual(m["center"], gather.LEDGER_RUNG_INK_DENSE)
        self.assertGreaterEqual(m["left"], gather.LEDGER_RUNG_INK_DENSE)
        self.assertGreaterEqual(m["right"], gather.LEDGER_RUNG_INK_DENSE)
        self.assertGreater(m["adjacent"], gather.LEDGER_RUNG_INK_ADJACENT_MAX)


# ─────────────────────────────────────────────────────────────────────────────
# Part 2 — GATHER integration: `_observe_ledger_rung_ink` on a fake cell
# ─────────────────────────────────────────────────────────────────────────────

class FakeCell:
    def __init__(self, *, image_no_staff, bbox_page_px, upscale_factor,
                staff_line_ys_canonical):
        self.image_no_staff = image_no_staff
        self.bbox_page_px = bbox_page_px
        self.upscale_factor = upscale_factor
        self.staff_line_ys_canonical = staff_line_ys_canonical


def _candidate_cell():
    """`upscale_factor=1.0` and an origin at (0, 0): canonical == page, so
    the coordinate-conversion arithmetic is checked with arithmetic anyone
    can verify by eye, not hidden behind a scale factor."""
    img = _paper(h=300, w=300)
    _draw(img, 182, 88, 218, 92)     # the rung: step 1 above CAND (want=90)
    return FakeCell(image_no_staff=img, bbox_page_px=[0.0, 0.0, 1000.0, 1000.0],
                    upscale_factor=1.0,
                    staff_line_ys_canonical=[0.0, 10.0, 20.0, 30.0, 40.0])


G = R.glyph(0, 0, 0, 0, 0)             # the head, filed on its OWN staff 0
CAND_KEY = R.staff(0, 0, 1).to_key()   # the candidate, a different staff
CAND_LINES = [100.0, 110.0, 120.0, 130.0, 140.0]   # PAGE px
CAND_SPACING = 10.0
HEAD_BOX_PAGE = (190.0, 80.0, 210.0, 90.0)          # y_center = 85 (1.5sp above)


class TestGatherIntegration(unittest.TestCase):

    def test_a_boxed_rung_files_a_found_row_at_the_right_page_window(self):
        cell_by_key = {(0, 0, 1, 0): _candidate_cell()}
        log = Log()
        gather._observe_ledger_rung_ink(log, G, HEAD_BOX_PAGE, CAND_KEY,
                                        CAND_LINES, CAND_SPACING, cell_by_key,
                                        None)
        log.freeze()
        rows = log.rows(Q.LEDGER_RUNG_INK, G)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIs(row.value, True)
        self.assertEqual(row.reader, READERS.CV_LEDGER)
        self.assertEqual(row.detail["candidate"], CAND_KEY)
        self.assertEqual(row.detail["step"], 1)
        self.assertAlmostEqual(row.detail["want_y_page"], 90.0, places=1)
        win = row.detail["window_page_px"]
        self.assertEqual(len(win), 4)
        self.assertLess(win[0], HEAD_BOX_PAGE[0])     # extends past the head
        self.assertGreater(win[2], HEAD_BOX_PAGE[2])

    def test_no_cell_at_all_abstains_no_mask(self):
        log = Log()
        gather._observe_ledger_rung_ink(log, G, HEAD_BOX_PAGE, CAND_KEY,
                                        CAND_LINES, CAND_SPACING, {}, None)
        log.freeze()
        ab = log.refusals(Q.LEDGER_RUNG_INK, G)
        self.assertEqual(len(ab), 1)
        self.assertEqual(ab[0].reason, R.ABSTAIN.NO_MASK)

    def test_a_cell_with_no_page_box_abstains_no_staff_geometry(self):
        cell = _candidate_cell()
        cell.bbox_page_px = None
        log = Log()
        gather._observe_ledger_rung_ink(log, G, HEAD_BOX_PAGE, CAND_KEY,
                                        CAND_LINES, CAND_SPACING,
                                        {(0, 0, 1, 0): cell}, None)
        log.freeze()
        ab = log.refusals(Q.LEDGER_RUNG_INK, G)
        self.assertEqual(len(ab), 1)
        self.assertEqual(ab[0].reason, R.ABSTAIN.NO_STAFF_GEOMETRY)

    def test_inside_the_staffs_own_band_writes_nothing(self):
        log = Log()
        inside_box = (190.0, 115.0, 210.0, 125.0)   # y_center 120, IN band
        gather._observe_ledger_rung_ink(log, G, inside_box, CAND_KEY,
                                        CAND_LINES, CAND_SPACING,
                                        {(0, 0, 1, 0): _candidate_cell()},
                                        None)
        log.freeze()
        self.assertEqual(len(log.rows(Q.LEDGER_RUNG_INK, G)), 0)
        self.assertEqual(len(log.refusals(Q.LEDGER_RUNG_INK, G)), 0)


# ─────────────────────────────────────────────────────────────────────────────
# Part 3 — the ONE helper credits a step from EITHER reader
# ─────────────────────────────────────────────────────────────────────────────

UP = R.staff(0, 0, 0)
DOWN = R.staff(0, 0, 1)
HEAD = R.glyph(0, 0, 0, 0, 0)
UP_LINES = [100.0, 110.0, 120.0, 130.0, 140.0]
DOWN_LINES = [200.0, 210.0, 220.0, 230.0, 240.0]
CONTEST_SP = 10.0


def _cv_row(log, subject, *, candidate, step, want_y, found=True):
    log.observe(subject, Q.LEDGER_RUNG_INK, found, reader=READERS.CV_LEDGER,
                frame="page", candidate=candidate, step=step,
                want_y_page=want_y, window_page_px=[490.0, want_y - 1.0,
                                                     522.0, want_y + 1.0],
                center=0.9, left=0.9, right=0.9, adjacent=0.1)


def _far_contest(head_y, *, cv_toward_up=(), cv_found=True):
    """`HEAD` far from both UP and DOWN, no `ledgerLine` boxes anywhere;
    `cv_toward_up` names which UP steps (1-based) carry a CV witness."""
    log = Log()
    for st, lines in ((UP, UP_LINES), (DOWN, DOWN_LINES)):
        log.observe(st, Q.STAFF_LINES, list(lines), reader=READERS.GEOMETRY,
                    frame="page")
        log.observe(st, Q.STAFF_SPACING, CONTEST_SP, reader=READERS.GEOMETRY,
                    frame="page")
    log.observe(HEAD, Q.GLYPH_BOX, ("noteheadBlackInSpace", 0, 0, 10, 10),
                reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                bbox_page_px=[500.0, head_y - 5.0, 512.0, head_y + 5.0],
                x_center_page=506.0, y_center_page=head_y)
    for st, lines in ((UP, UP_LINES), (DOWN, DOWN_LINES)):
        top, bottom = min(lines), max(lines)
        gap = (top - head_y) if head_y < top else (head_y - bottom)
        log.observe(HEAD, Q.GLYPH_BAND_DISTANCE, max(0.0, gap / CONTEST_SP),
                    reader=READERS.GEOMETRY, frame="page",
                    candidate=st.to_key(), own=(st == UP),
                    position_in_candidate=(head_y - top) / (CONTEST_SP / 2))
    # ⚠️ `head_y` (176.0 below) sits BELOW UP's bottom line, so UP's steps
    # walk DOWN the page from UP's bottom -- the same arithmetic
    # `_observe_ladder`/`ladder_side` use.
    up_bottom = max(UP_LINES)
    for k in cv_toward_up:
        want = up_bottom + k * CONTEST_SP
        _cv_row(log, HEAD, candidate=UP.to_key(), step=k, want_y=want,
               found=cv_found)
    log.freeze()
    adjudicate._ensure_decisions()
    return adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.GLYPH_OWNER],
                                     HEAD)


class TestCVRungsAreASecondReaderOfTheSameLadder(unittest.TestCase):

    def test_a_far_no_rungs_contest_is_decided_by_a_cv_only_ladder(self):
        """176.0: 3.6 spaces below UP (needs 3 rungs), 2.4 above DOWN (needs
        2). No detector box anywhere. RED before 2.6d: `far_no_rungs`. Two
        of UP's three expected steps (2 and 3 — the ladder ENDS at the note,
        0.6 spaces short of it, one miss tolerated) carry a
        `Q.LEDGER_RUNG_INK` row, found: the ladder reaches, UP points, and
        nothing toward DOWN — `ledger_direction` decides."""
        v = _far_contest(176.0, cv_toward_up=(2, 3))
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, UP.to_key())
        self.assertEqual(v.reason, "ledger_direction")

    def test_the_credited_step_names_its_own_reader(self):
        """`trace` must be able to say WHICH reader named a step: read the
        `sources` map directly off the verdict's ledger summary."""
        v = _far_contest(176.0, cv_toward_up=(2, 3))
        sources = v.detail["ledger"]["sides"][UP.to_key()]["sources"]
        self.assertEqual(len(sources), 2)
        self.assertTrue(all(src == "cv_ink" for src in sources.values()))

    def test_a_cv_row_that_found_nothing_credits_no_step(self):
        """The SAME two steps, but the CV reader's own measurement said
        `found=False` (it looked and there was no ink) -- `cv_rungs` reads
        only rows whose `value is True`, so this must stay `far_no_rungs`,
        never a guess in either direction."""
        v = _far_contest(176.0, cv_toward_up=(2, 3), cv_found=False)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "far_no_rungs")

    def test_a_lone_cv_rung_is_not_a_ladder(self):
        """One step only: `n_toward=1` but two of UP's three expected steps
        are still missing (over `LADDER_MAX_MISSING`) -- UP does not
        `point`. One side carrying a hint (`n_toward != 0`) also takes the
        contest OUT of `far_no_rungs` (Sean's rule is about a reading gap on
        EVERY side): it falls to the ordinary tiers, and DOWN — nearer,
        2.4 spaces against 3.6 — wins on distance, exactly as a lone
        detector-boxed rung already does (`test_staged_ledger_direction.
        TestAFarNoteWithNoRungsAbstains.test_CONTROL_a_lone_rung_is_not_a_
        ladder`)."""
        v = _far_contest(176.0, cv_toward_up=(3,))
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, DOWN.to_key())
        self.assertEqual(v.reason, "distance")

    def test_POSITIVE_CONTROL_with_no_cv_evidence_at_all_it_still_abstains(self):
        """The negative-control discipline: the SAME geometry with no CV
        rows and no detector boxes must reproduce 2.6c.2's own shipped
        result, or this file could not tell a real credit from a broken
        test."""
        v = _far_contest(176.0)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "far_no_rungs")


class TestCvRungsHelper(unittest.TestCase):
    """`ownership.cv_rungs` in isolation — the merge point both `glyph_owner`
    and 2.7b's `belongs_to_a_nearer_staff` read through."""

    def test_reads_only_found_true_rows_as_rungs(self):
        log = Log()
        _cv_row(log, HEAD, candidate=UP.to_key(), step=1, want_y=130.0,
               found=True)
        _cv_row(log, HEAD, candidate=UP.to_key(), step=2, want_y=120.0,
               found=False)
        log.freeze()
        adjudicate._ensure_decisions()
        spec = adjudicate.REGISTRY[Q.GLYPH_OWNER]
        ev = adjudicate.Evidence(log, HEAD, spec)
        rungs = OWN.cv_rungs(ev)
        self.assertEqual(len(rungs), 1)
        self.assertEqual(rungs[0].y, 130.0)
        self.assertEqual(rungs[0].source, "cv_ink")

    def test_an_abstained_row_contributes_no_rung(self):
        log = Log()
        log.abstain(HEAD, Q.LEDGER_RUNG_INK, reader=READERS.CV_LEDGER,
                    frame="page", reason=R.ABSTAIN.NO_MASK,
                    candidate=UP.to_key(), step=1)
        log.freeze()
        adjudicate._ensure_decisions()
        spec = adjudicate.REGISTRY[Q.GLYPH_OWNER]
        ev = adjudicate.Evidence(log, HEAD, spec)
        self.assertEqual(OWN.cv_rungs(ev), [])


# ─────────────────────────────────────────────────────────────────────────────
# Part 4 — 2.7b's `belongs_to_a_nearer_staff` asks the SAME helper
# ─────────────────────────────────────────────────────────────────────────────

FILED = R.staff(0, 0, 0)
NEAR = R.staff(0, 0, 1)
FILED_LINES = [100.0, 110.0, 120.0, 130.0, 140.0]
NEAR_LINES = [200.0, 210.0, 220.0, 230.0, 240.0]
HEAD_2_7B = R.glyph(0, 0, 0, 0, 0)
HEAD_Y_2_7B = 176.0        # 3.6 spaces below FILED, 2.4 spaces above NEAR


def _near_staff_contest(cv_toward_filed=()):
    log = Log()
    for st, lines in ((FILED, FILED_LINES), (NEAR, NEAR_LINES)):
        log.observe(st, Q.STAFF_LINES, list(lines), reader=READERS.GEOMETRY,
                    frame="page")
        log.observe(st, Q.STAFF_SPACING, CONTEST_SP, reader=READERS.GEOMETRY,
                    frame="page")
    cell = R.cell(0, 0, 0, 0)
    log.observe(cell, Q.CELL_STAFF_SPACE, SP, reader=READERS.GEOMETRY,
                frame="cell:0")
    log.observe(HEAD_2_7B, Q.GLYPH_BOX,
                ("noteheadHalfInSpace", 0, 0, 30, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.85,
                bbox_page_px=[500.0, HEAD_Y_2_7B - 5.0, 512.0,
                             HEAD_Y_2_7B + 5.0])
    log.observe(HEAD_2_7B, Q.NOTEHEAD_CLASS, "noteheadHalfInSpace",
                reader=READERS.DETECTOR, frame="cell:0", score=0.85)
    # ⚠️ `HEAD_Y_2_7B` (176.0) sits BELOW the filed staff's bottom line.
    filed_bottom = max(FILED_LINES)
    for k in cv_toward_filed:
        _cv_row(log, HEAD_2_7B, candidate=FILED.to_key(), step=k,
               want_y=filed_bottom + k * CONTEST_SP, found=True)
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, HEAD_2_7B)


class TestBelongsToANearerStaffAsksTheSameHelper(unittest.TestCase):

    def test_RED_with_no_ledger_evidence_the_head_is_refused(self):
        """The negative control 2.6c.2 already shipped: no rung of any
        source, the near staff is closer, and the head is dropped from the
        staff it was filed on."""
        v = _near_staff_contest()
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "belongs_to_a_nearer_staff")

    def test_a_cv_only_ladder_toward_the_filed_staff_keeps_it(self):
        """Two of the filed staff's three expected rungs, read off the ink
        alone (no `ledgerLine` box anywhere) -- the SAME `cv_rungs` merge
        `glyph_owner` uses. The ladder reaches the filed staff and the
        refusal 2.6c.2 would otherwise fire does not."""
        v = _near_staff_contest(cv_toward_filed=(2, 3))
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")
        signal = v.detail["nearer_staff_signal"]
        self.assertEqual(signal["ledger"]["winner"], FILED.to_key())
        self.assertEqual(signal["cv_rung_ink_rows"], 2)

    def test_a_lone_cv_rung_does_not_save_it(self):
        """One rung is a hint, not a ladder -- the exception needs the walk
        to REACH, and a single step short of that still refuses."""
        v = _near_staff_contest(cv_toward_filed=(3,))
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "belongs_to_a_nearer_staff")


if __name__ == "__main__":
    unittest.main()
