"""A rung with no BOXED head — ROADMAP 3.4g-3.

⚠️ WHY THIS FILE EXISTS, AND IT IS A PERSON WHO SAID SO. 3.4g-2 shipped
Sean's second ledger convention (`[C91]`, *"only happen if there are actual
notes in the staff"*) as a REFUSAL, `no_head_on_the_rung`, read off the
DETECTOR's notehead boxes. Sean adjudicated its four crops on 2026-09-27
(`benchmarks/omr-family-refusals-2026-09/out/print/
ADJUDICATION-sean-2026-09-27.json`): crops 1 and 3 are REAL rungs whose
printed notehead the detector never boxed. A missing detector box is
"cannot tell", and CLAUDE.md §2 rule 8 forbids a fallback converting that
into an answer — so:

  PART A (ADJUDICATE)  where no boxed head is near, the decision ABSTAINS
                       (`rung_without_boxed_head`); it refuses only where a
                       second witness says the paper is empty.
  PART B (GATHER)      `Q.LEDGER_INK_UNDER` — the ink under the rung, read
                       off the cell's staff-erased raster at gather time —
                       is that witness. Ink well above the background keeps
                       the rung (`ink_under_the_rung`); ink at the
                       background restores the refusal with two witnesses;
                       in between the abstention stands.

⚠️ RUN RED FIRST: Part A's tests were run against `origin/main` `8226aa93`
(the four crops come back `no_head_on_the_rung`, refused) before the change;
the captured run is in the FINDINGS §3.4g-3.
"""

from __future__ import annotations

import unittest

import numpy as np

from tools.omr.staged import adjudicate, gather
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import export as SX
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import family_precision as FP
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_family_refusals import (
    HEAD_H_CANONICAL, LEDGER_X_CANONICAL, LEDGER_Y_CANONICAL,
    SPACING_CANONICAL, _box, _page_box_at_step, _run, _staff_geometry)


def _rung(*, step, h_c=20.0, w_c=140.0, heads_outward=(), ink=None,
          ink_abstains=False):
    """One `ledgerLine` box, the x-overlapping heads (SIGNED distances in
    spaces, + farther from the staff), and optionally the GATHER witness.

    `ink` — `(under, background)` as fractions: files one
    `Q.LEDGER_INK_UNDER` row exactly as `gather.gather_ledger_ink` does.
    """
    log = Log()
    _staff_geometry(log)
    out_dir = -1.0 if step > 8.0 else 1.0     # canonical y grows DOWN
    rung_mid = LEDGER_Y_CANONICAL + h_c / 2.0
    for i, off in enumerate(heads_outward):
        head_mid = rung_mid + off * out_dir * SPACING_CANONICAL
        _box(log, 9 + i, "noteheadBlackOnLine", quantity=Q.NOTEHEAD_CLASS,
             page_box=_page_box_at_step(step), w_c=130.0,
             h_c=HEAD_H_CANONICAL, x_c=LEDGER_X_CANONICAL,
             y_c=head_mid - HEAD_H_CANONICAL / 2.0)
    g = _box(log, 0, "ledgerLine", w_c=w_c, h_c=h_c,
             x_c=LEDGER_X_CANONICAL, y_c=LEDGER_Y_CANONICAL,
             page_box=_page_box_at_step(step))
    if ink is not None:
        under, background = ink
        log.observe(g, Q.LEDGER_INK_UNDER, float(under),
                    reader=READERS.CV_INK, frame="cell:0",
                    ink_background=float(background),
                    ink_windows={"on": under, "above": under,
                                 "below": under},
                    window_spaces=[1.3, 1.0])
    elif ink_abstains:
        log.abstain(g, Q.LEDGER_INK_UNDER, reader=READERS.CV_INK,
                    frame="cell:0", reason=R.ABSTAIN.NO_MASK)
    _run(log, Q.LEDGER_IS_NOT_A_LEDGER)
    return log.verdict(Q.LEDGER_IS_NOT_A_LEDGER, g)


#: ⚠️⚠️ SEAN'S FOUR `no_head_on_the_rung` CROPS, AS FIXTURES.
#:
#: `(n, subject, is a ledger line?, staff step, height in spaces, the
#:  x-overlapping heads as SIGNED distances in spaces)` — the geometry is the
#: 3.4g-2 crop manifest's (`out/print/crop-manifest-g2-litolff-p1p4.json`),
#: MEASURED off `beethoven5-p1-p4.record.json`, never read off the picture.
#:
#: ⚠️ CROP 2 IS NOT REFUSED ON POSITION, AND THE BRIEF FOR THIS LANE SAID IT
#: WAS. Its centre is 0.315 spaces outside line 1 (step -0.63), past
#: `ON_A_STAFF_LINE_TOL_SPACES` = 0.25, so `on_a_staff_line` never reached
#: it — 3.4g-2 refused it `no_head_on_the_rung` like the other three. The
#: same holds for crop 4 (0.29 spaces). On the print both lie ON the true
#: bottom line and the modelled line sits ~0.3 spaces above it: registration
#: on a merging plate, the cause `RUNG_STEP_SHIPS = False` records.
SEANS_FOUR = (
    (1, "glyph/1/0/3/14/0", True, 10.59, 0.25, ()),
    (2, "glyph/2/0/2/2/12", False, -0.63, 0.29, ()),
    (3, "glyph/2/1/0/12/6", True, 13.3165, 0.34, (-10.1,)),
    (4, "glyph/3/1/0/6/12", False, -0.5835, 0.34, (-5.64, -5.64)),
)


def _crop(row, **kw):
    _n, _s, _real, step, h, heads = row
    return _rung(step=step, h_c=h * SPACING_CANONICAL,
                 heads_outward=heads, **kw)


class TestPartA_NoBoxedHeadAbstains(unittest.TestCase):
    """Where the detector boxed no head near the rung and nothing else has
    looked, the decision cannot tell — and says so."""

    def test_seans_real_rungs_are_never_refused(self):
        """⚠️⚠️ THE GATE: crops 1 and 3 — real rungs, heads the detector
        never boxed — must never come back REFUSED."""
        for n in (1, 3):
            row = next(r for r in SEANS_FOUR if r[0] == n)
            with self.subTest(crop=n, subject=row[1]):
                v = _crop(row)
                self.assertIsNot(v.value, True)
                self.assertEqual(v.outcome, Outcome.ABSTAINED)
                self.assertEqual(v.reason, "rung_without_boxed_head")

    def test_every_one_of_the_four_abstains_without_the_witness(self):
        """⚠️ ALL FOUR, not only the two real ones: without a second
        witness the machine cannot tell crop 1 from crop 2, and a rule that
        refused 2 and kept 1 on this evidence would be guessing right."""
        for row in SEANS_FOUR:
            with self.subTest(crop=row[0], subject=row[1]):
                v = _crop(row)
                self.assertEqual(v.outcome, Outcome.ABSTAINED)
                self.assertEqual(v.reason, "rung_without_boxed_head")

    def test_the_abstention_keeps_its_evidence(self):
        """An abstention is not an empty row: the head facts and the rows it
        looked at stay on it, so the viewer can say WHY it could not tell."""
        v = _crop(SEANS_FOUR[0])
        self.assertEqual(v.detail["heads_x_overlapping"], 0)
        self.assertIsNone(v.detail["head_distance_spaces"])
        self.assertTrue(v.used)
        self.assertIn("staff_step", v.detail)
        self.assertIs(v.detail["ink_witness"], None)

    def test_a_witness_that_abstained_is_not_a_witness(self):
        """GATHER looked and could not measure (`no_mask`): DECLINED, and
        it must not read as empty paper."""
        v = _crop(SEANS_FOUR[1], ink_abstains=True)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "rung_without_boxed_head")

    # ── the positive controls: nothing else moves ───────────────────────────

    def test_a_rung_with_its_head_on_it_is_still_KEPT(self):
        v = _rung(step=-2.0, heads_outward=(0.0,))
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "ledger_line")

    def test_position_and_shape_refusals_are_untouched(self):
        for step, h, reason in ((4.0, 0.2, "inside_the_staff"),
                                (-0.2, 0.2, "on_a_staff_line"),
                                (-2.0, 0.62, "tall_not_a_rung")):
            with self.subTest(reason=reason):
                v = _rung(step=step, h_c=h * SPACING_CANONICAL,
                          heads_outward=(-2.975,))
                self.assertIs(v.value, True)
                self.assertEqual(v.reason, reason)

    def test_the_census_counts_the_abstention_by_reason(self):
        """`family_refusals` already partitions `abstained`; 3.4g-3 names
        the reason inside it, so 79 abstentions are not read as 79
        `no_staff_geometry`."""
        log = Log()
        _staff_geometry(log)
        g = _box(log, 0, "ledgerLine", x_c=LEDGER_X_CANONICAL,
                 y_c=LEDGER_Y_CANONICAL, page_box=_page_box_at_step(-2.0))
        _run(log, Q.LEDGER_IS_NOT_A_LEDGER)
        self.assertEqual(log.verdict(Q.LEDGER_IS_NOT_A_LEDGER, g).outcome,
                         Outcome.ABSTAINED)
        rec = SX.Record({"record": log.to_json()})
        fam = SX._family_refusals(rec)[Q.LEDGER_IS_NOT_A_LEDGER]
        self.assertEqual(fam["abstained"], 1)
        self.assertEqual(fam["abstained_reasons"],
                         {"rung_without_boxed_head": 1})
        self.assertTrue(fam["balanced"])


class TestPartB_TheWitnessResolves(unittest.TestCase):
    """`Q.LEDGER_INK_UNDER` settles the abstention where it speaks."""

    def test_ink_well_above_background_KEEPS_the_rung(self):
        v = _crop(SEANS_FOUR[0], ink=(FP.LEDGER_INK_KEPT_MIN + 0.05, 0.0))
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "ink_under_the_rung")

    def test_ink_at_background_REFUSES_with_two_witnesses(self):
        v = _crop(SEANS_FOUR[1], ink=(0.0, 0.0))
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "no_head_on_the_rung")
        # both witnesses on the verdict: the box row AND the ink row
        self.assertIn("ink_witness", v.detail)
        self.assertEqual(v.detail["ink_witness"]["under"], 0.0)

    def test_in_between_the_abstention_stands(self):
        mid = (FP.LEDGER_INK_KEPT_MIN + FP.LEDGER_INK_REFUSED_MAX) / 2.0
        v = _crop(SEANS_FOUR[0], ink=(mid, 0.0))
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "rung_without_boxed_head")

    def test_the_thresholds_are_ordered_and_leave_a_gap(self):
        self.assertLess(FP.LEDGER_INK_REFUSED_MAX, FP.LEDGER_INK_KEPT_MIN)

    def test_ink_that_is_all_BACKGROUND_does_not_keep(self):
        """⚠️ THE CONTROL WINDOW IS READ. A cell dark everywhere (a smear, a
        dense tutti) is not a head under the rung: the under-window must
        stand ABOVE the background by the margin, not merely be high."""
        high = FP.LEDGER_INK_KEPT_MIN + 0.1
        v = _crop(SEANS_FOUR[0], ink=(high, high))
        self.assertNotEqual(v.reason, "ink_under_the_rung")

    def test_the_witness_never_touches_a_rung_with_a_boxed_head(self):
        """A rung the detector's heads already keep is not re-asked."""
        v = _rung(step=-2.0, heads_outward=(0.0,), ink=(0.0, 0.0))
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "ledger_line")

    def test_the_witness_never_rescues_a_position_refusal(self):
        v = _rung(step=4.0, ink=(0.9, 0.0))
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "inside_the_staff")

    def test_the_decision_declares_the_witness(self):
        spec = adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER]
        self.assertIn(Q.LEDGER_INK_UNDER, spec.wants)
        self.assertIn("ink_under_the_rung", spec.reasons)
        self.assertIn("rung_without_boxed_head", spec.reasons)


# ─────────────────────────────────────────────────────────────────────────────
# the GATHER measurement, on synthetic rasters
# ─────────────────────────────────────────────────────────────────────────────

SP = 20                         # one staff space in the synthetic cell, px


def _paper(h=400, w=400):
    return np.full((h, w), 255, dtype=np.uint8)


def _rung_box(cx=200, cy=200, w=50, h=4):
    """(x, y, w, h) canonical, a rung centred at (cx, cy)."""
    return (cx - w // 2, cy - h // 2, w, h)


def _draw(img, x0, y0, x1, y1):
    img[int(y0):int(y1), int(x0):int(x1)] = 0


def _head(img, cx, cy):
    """A filled notehead 1.3 x 1.0 spaces, as an ellipse."""
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    a, b = 0.65 * SP, 0.5 * SP
    img[((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2 <= 1.0] = 0


class TestTheMeasurement(unittest.TestCase):

    def _measure(self, img, box):
        return gather.ledger_ink_under(img, box, float(SP))

    def test_a_bare_rung_reads_nothing_under_it(self):
        """⚠️ THE RUNG'S OWN STROKE IS SUBTRACTED, or every rung would
        vouch for itself."""
        img = _paper()
        x, y, w, h = _rung_box()
        _draw(img, x, y, x + w, y + h)
        m = self._measure(img, (x, y, w, h))
        self.assertEqual(m["under"], 0.0)
        self.assertEqual(m["background"], 0.0)

    def test_a_head_ON_the_rung_reads_high(self):
        img = _paper()
        x, y, w, h = _rung_box()
        _draw(img, x, y, x + w, y + h)
        _head(img, 200, 200)
        m = self._measure(img, (x, y, w, h))
        self.assertGreater(m["under"], 0.5)
        self.assertEqual(m["best_window"], "on")

    def test_a_head_hanging_BELOW_the_rung_reads_high_in_its_window(self):
        img = _paper()
        x, y, w, h = _rung_box()
        _draw(img, x, y, x + w, y + h)
        _head(img, 200, 200 + SP // 2)
        m = self._measure(img, (x, y, w, h))
        self.assertGreater(m["under"], 0.5)
        self.assertEqual(m["best_window"], "below")

    def test_the_background_window_is_one_space_away(self):
        """⚠️ THE CONTROL CAN FAIL: ink one full space off the rung (and
        not under it) raises the background and not the under-window."""
        img = _paper()
        x, y, w, h = _rung_box()
        _draw(img, x, y, x + w, y + h)
        _draw(img, 180, 200 + SP + SP // 2 - 8, 220, 200 + SP + SP // 2 + 8)
        _draw(img, 180, 200 - SP - SP // 2 - 8, 220, 200 - SP - SP // 2 + 8)
        m = self._measure(img, (x, y, w, h))
        self.assertEqual(m["under"], 0.0)
        self.assertGreater(m["background"], 0.3)

    def test_a_window_off_the_raster_is_clipped_not_invented(self):
        img = _paper(h=40)
        x, y, w, h = _rung_box(cy=4)
        _draw(img, x, y, x + w, y + h)
        m = self._measure(img, (x, y, w, h))
        self.assertIsNotNone(m)
        self.assertEqual(m["under"], 0.0)

    def test_no_unit_no_measurement(self):
        img = _paper()
        self.assertIsNone(gather.ledger_ink_under(img, _rung_box(), 0.0))


class TestGatherFilesTheQuantity(unittest.TestCase):

    def test_the_quantity_is_a_measurement(self):
        self.assertIn(Q.LEDGER_INK_UNDER, Q.all())
        self.assertEqual(R.claim_of(Q.LEDGER_INK_UNDER),
                         R.CLAIM.MEASUREMENT)


if __name__ == "__main__":       # pragma: no cover
    unittest.main()
