"""ROADMAP 2.37 -- Sean's redirect (2026-09-29, quoted, stopping the
absolute-threshold width-test round where it stood):

*"pitch is geometric -- staff spacing tells line vs space for any note
outside the staff; ledger lines always exist between the note and its own
staff. Pitch already works that way (`restate_pitch` from `Q.NOTEHEAD_
STAFF_POSITION`, no ledger read). So the ledger reader is ONLY needed for
OWNERSHIP of a note between two staves, and for that we do not need to
read every rung with absolute thresholds."*

One comparison per contested head: the ONE ledger position adjacent to the
head on each candidate side (geometry names it -- `gather._ledger_owner_
informative_step`), raw ink density read with no found/not-found threshold
(`gather.ledger_owner_ink_density`), the owner decided by `glyph_owner`
from the RATIO between the two candidates' own readings
(`ownership._ledger_owner_comparison`) -- never an absolute floor compared
across documents. The detector-based ladder (`ledger_direction`) is kept as
a CORROBORATING witness: where it also has an opinion and disagrees, the
glyph declines outright (`ledger_witnesses_disagree`). The all-rungs
elimination rule built in an earlier round on this branch is left OFF: see
`test_staged_ledger_cv_first_2_37.py::TestElimination`'s own note.

⚠️ RUN RED FIRST: `gather._ledger_owner_informative_step`,
`gather.ledger_owner_ink_density`, `gather._observe_ledger_owner_density`,
`Q.LEDGER_OWNER_DENSITY` and `ownership._ledger_owner_comparison` do not
exist before this round.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import ownership as OWN
from tools.omr.staged.record import Log, Outcome, Q, READERS

# ─────────────────────────────────────────────────────────────────────────────
# Part 1 -- the geometry: which step is informative
# ─────────────────────────────────────────────────────────────────────────────

SP = 10.0


class TestInformativeStep(unittest.TestCase):

    def test_within_the_staff_or_first_space_needs_no_ledger(self):
        self.assertIsNone(gather._ledger_owner_informative_step(0.0, SP))
        self.assertIsNone(gather._ledger_owner_informative_step(5.0, SP))

    def test_a_head_in_a_space_samples_the_adjacent_rung(self):
        """1.5 spaces out (state b: resting in the space just beyond the
        first ledger) -- the adjacent rung IS that first ledger, step 1,
        no coincidence with the head's own row to avoid."""
        self.assertEqual(gather._ledger_owner_informative_step(15.0, SP), 1)

    def test_a_head_on_a_ledger_samples_one_step_further_out(self):
        """10.0 (state c: exactly on the first ledger) -- that row IS the
        head's own ink; with a second rung available (here there is only
        one, so this specific case has no further step)."""
        self.assertIsNone(gather._ledger_owner_informative_step(10.0, SP))

    def test_a_head_on_the_second_ledger_falls_back_one_space(self):
        """20.0 (on the SECOND ledger): the head's own row is uninformative
        but step 1 (one space closer to the staff) is available and is
        sampled instead of step 2."""
        self.assertEqual(gather._ledger_owner_informative_step(20.0, SP), 1)

    def test_a_head_in_the_next_space_out_samples_that_rung(self):
        """25.0 (state b again, one ledger further out): step 2, no
        coincidence."""
        self.assertEqual(gather._ledger_owner_informative_step(25.0, SP), 2)


class TestInformativeStepAgainstARealHeadBox(unittest.TestCase):
    """ROADMAP 2.37 (manager review, round 2 -- Sean's own addition): the
    step search must check the REAL standard head box, not the
    approximate "close to an integer" heuristic above (which is kept
    only as a geometry-only fallback for callers with no box)."""

    def test_a_step_overlapping_the_real_box_is_rejected(self):
        """The geometry-only heuristic would call 3.62 spaces 'not on a
        ledger' (0.38 spaces from an integer, over its own 0.15
        tolerance) and sample step 3 directly (want = 3 * SP = 30.0) --
        but with a real head box centred there, step 3 still falls
        inside it. The search must find step 2 instead."""
        edge = 0.0
        gap = 3.62 * SP           # steps=3.62, expected=int(3.87)=3
        head_y0, head_y1 = 30.0 - 8.0, 30.0 + 8.0   # centred on step 3's own y
        step = gather._ledger_owner_informative_step(
            gap, SP, edge=edge, above=False, head_y0=head_y0,
            head_y1=head_y1, half_h=1.0)
        self.assertEqual(step, 2)

    def test_a_single_expected_rung_coinciding_with_the_head_declines(self):
        """MEASURED on a real Litolff re-gather: `expected == 1` and that
        ONE rung's own position falls inside the head's real box, with no
        second rung to fall back to -- correctly declines (the head
        stands exactly on its own single required rung, per Sean's own
        convention "uninformative -- skip it"; there is nothing else to
        sample toward THIS candidate)."""
        edge = 0.0
        gap = 1.225 * SP          # steps=1.225, expected=int(1.475)=1
        step = gather._ledger_owner_informative_step(
            gap, SP, edge=edge, above=False, head_y0=gap - 8.66,
            head_y1=gap + 8.66, half_h=2.59)
        self.assertIsNone(step)

    def test_a_step_two_out_still_overlapping_keeps_searching(self):
        """A wider standard box (or a smaller staff space) can still
        overlap ONE step out -- the search must not stop after a single
        fallback; it walks all the way to a step that genuinely clears,
        or to none."""
        edge = 0.0
        gap = 5.0 * SP            # expected=5
        # step 5 wants 5*SP=50, step 4 wants 4*SP=40, step 3 wants 30 --
        # a box wide enough to swallow 50 AND 40, but not 30.
        head_y0, head_y1 = 3.5 * SP, 5.5 * SP
        step = gather._ledger_owner_informative_step(
            gap, SP, edge=edge, above=False, head_y0=head_y0,
            head_y1=head_y1, half_h=0.01)
        self.assertEqual(step, 3)


# ─────────────────────────────────────────────────────────────────────────────
# Part 2 -- the raw density measurement
# ─────────────────────────────────────────────────────────────────────────────

def _paper(h=400, w=400):
    import numpy as np
    return np.full((h, w), 255, dtype="uint8")


def _draw(img, x0, y0, x1, y1):
    img[int(round(y0)):int(round(y1)), int(round(x0)):int(round(x1))] = 0


class TestLedgerOwnerInkDensity(unittest.TestCase):

    def test_a_real_stroke_reads_high(self):
        img = _paper()
        _draw(img, 175, 197, 225, 203)     # crosses well past 190-210
        d = gather.ledger_owner_ink_density(img, 190.0, 210.0, 200.0, SP,
                                            None)
        self.assertGreater(d, 0.8)

    def test_nothing_here_reads_low(self):
        img = _paper()
        d = gather.ledger_owner_ink_density(img, 190.0, 210.0, 200.0, SP,
                                            None)
        self.assertEqual(d, 0.0)

    def test_off_the_raster_declines(self):
        img = _paper(h=6, w=400)
        d = gather.ledger_owner_ink_density(img, 190.0, 210.0, 200.0, SP,
                                            None)
        self.assertIsNone(d)


# ─────────────────────────────────────────────────────────────────────────────
# Part 3 -- the ratio comparison, through the REAL glyph_owner decision
# ─────────────────────────────────────────────────────────────────────────────

#: head_y = 176.0: 3.6 spaces below UP (needs 3 rungs), 2.4 above DOWN
#: (needs 2) -- the SAME geometry `test_staged_ledger_cv_first_2_37.py`'s
#: own `_contest` helper uses, reproduced here (not imported) so this
#: file's fixture does not depend on that file's internal names.
UP = R.staff(0, 0, 0)
DOWN = R.staff(0, 0, 1)
HEAD = R.glyph(0, 0, 0, 0, 0)
UP_LINES = [100.0, 110.0, 120.0, 130.0, 140.0]
DOWN_LINES = [200.0, 210.0, 220.0, 230.0, 240.0]
HEAD_Y = 176.0


def _owner_density_row(log, *, candidate, value, step=1):
    log.observe(HEAD, Q.LEDGER_OWNER_DENSITY, value, reader=READERS.CV_LEDGER,
                frame="page", candidate=candidate, step=step,
                want_y_page=0.0)


def _base(log, *, up_ladder_boxed=False):
    """The SAME staff/head/band-distance geometry as `test_staged_ledger_
    cv_first_2_37.py`'s own `_contest` fixture, at `HEAD_Y`. Optionally
    boxes REAL `ledgerLine` detections at all 3 of UP's expected rung
    positions -- a genuinely COMPLETE, `points`-worthy detector ladder,
    the CORROBORATING witness `_ledger_owner_comparison` is checked
    against."""
    for st, lines in ((UP, UP_LINES), (DOWN, DOWN_LINES)):
        log.observe(st, Q.STAFF_LINES, list(lines), reader=READERS.GEOMETRY,
                    frame="page")
        log.observe(st, Q.STAFF_SPACING, SP, reader=READERS.GEOMETRY,
                    frame="page")
    log.observe(HEAD, Q.GLYPH_BOX, ("noteheadBlackInSpace", 0, 0, 10, 10),
                reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                bbox_page_px=[500.0, HEAD_Y - 5.0, 512.0, HEAD_Y + 5.0],
                x_center_page=506.0, y_center_page=HEAD_Y)
    for st, lines in ((UP, UP_LINES), (DOWN, DOWN_LINES)):
        top, bottom = min(lines), max(lines)
        gap = (top - HEAD_Y) if HEAD_Y < top else (HEAD_Y - bottom)
        log.observe(HEAD, Q.GLYPH_BAND_DISTANCE, max(0.0, gap / SP),
                    reader=READERS.GEOMETRY, frame="page",
                    candidate=st.to_key(), own=(st == UP),
                    position_in_candidate=(HEAD_Y - top) / (SP / 2))
    if up_ladder_boxed:
        up_bottom = max(UP_LINES)
        for k in (1, 2, 3):
            want = up_bottom + k * SP
            log.observe(R.glyph(0, 0, 0, 0, k + 1), Q.GLYPH_BOX,
                        ("ledgerLine", 0, 0, 10, 2), reader=READERS.DETECTOR,
                        frame="cell:0", score=0.8,
                        bbox_page_px=[494.0, want - 1.0, 518.0, want + 1.0],
                        category="ledgerLine")


class TestLedgerOwnerComparison(unittest.TestCase):

    def _run(self, *, readings, up_ladder_boxed=False):
        log = Log()
        _base(log, up_ladder_boxed=up_ladder_boxed)
        for cand, val in readings.items():
            _owner_density_row(log, candidate=cand, value=val)
        log.freeze()
        adjudicate._ensure_decisions()
        return adjudicate.adjudicate_one(
            log, adjudicate.REGISTRY[Q.GLYPH_OWNER], HEAD)

    def test_a_clear_ratio_decides_the_denser_side(self):
        v = self._run(readings={UP.to_key(): 0.05, DOWN.to_key(): 0.8})
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, DOWN.to_key())
        self.assertEqual(v.reason, "ledger_owner_density")

    def test_comparable_ink_is_not_decided_by_density(self):
        """Neither side clearly wins (ratio under the floor) -- the
        density mechanism itself stays silent (never `ledger_owner_
        density`); the glyph is still decided by whatever the EXISTING
        tiers say (here, plain distance -- DOWN is nearer), unaffected."""
        v = self._run(readings={UP.to_key(): 0.5, DOWN.to_key(): 0.6})
        self.assertNotEqual(v.reason, "ledger_owner_density")

    def test_both_near_empty_is_not_decided_by_density(self):
        v = self._run(readings={UP.to_key(): 0.02, DOWN.to_key(): 0.01})
        self.assertNotEqual(v.reason, "ledger_owner_density")

    def test_disagreement_with_the_detector_ladder_declines(self):
        """The density comparison picks DOWN; the detector's own ladder
        completeness (a CORROBORATING witness, 3 REAL boxed `ledgerLine`
        detections at all 3 of UP's expected positions) says UP `points`
        outright -- two witnesses disagree, and NEITHER is trusted alone."""
        v = self._run(readings={UP.to_key(): 0.05, DOWN.to_key(): 0.8},
                      up_ladder_boxed=True)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "ledger_witnesses_disagree")

    def test_agreement_with_the_detector_ladder_still_decides(self):
        """Both witnesses name the SAME side: decided, not blocked."""
        v = self._run(readings={UP.to_key(): 0.8, DOWN.to_key(): 0.05},
                      up_ladder_boxed=True)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, UP.to_key())

    def test_only_one_side_read_does_not_decide(self):
        """Fewer than two candidates have a `Q.LEDGER_OWNER_DENSITY`
        reading (Sean's own two-candidate case) -- this mechanism stays
        silent, never guessing from one side alone."""
        v = self._run(readings={UP.to_key(): 0.9})
        self.assertNotEqual(v.reason, "ledger_owner_density")


class TestLedgerOwnerComparisonHelper(unittest.TestCase):
    """`ownership._ledger_owner_comparison` in isolation."""

    def test_picks_the_higher_reading_over_the_ratio_and_floor(self):
        log = Log()
        _owner_density_row(log, candidate=UP.to_key(), value=0.05)
        _owner_density_row(log, candidate=DOWN.to_key(), value=0.8)
        log.observe(HEAD, Q.GLYPH_BAND_DISTANCE, 3.6, reader=READERS.GEOMETRY,
                    frame="page", candidate=UP.to_key(), own=True,
                    position_in_candidate=0.0)
        log.observe(HEAD, Q.GLYPH_BAND_DISTANCE, 2.4, reader=READERS.GEOMETRY,
                    frame="page", candidate=DOWN.to_key(), own=False,
                    position_in_candidate=0.0)
        log.freeze()
        adjudicate._ensure_decisions()
        spec = adjudicate.REGISTRY[Q.GLYPH_OWNER]
        ev = adjudicate.Evidence(log, HEAD, spec)
        result = OWN._ledger_owner_comparison(
            ev, [UP.to_key(), DOWN.to_key()])
        self.assertIsNotNone(result)
        winner, detail = result
        self.assertEqual(winner, DOWN.to_key())
        self.assertAlmostEqual(detail["ratio"], 16.0, places=1)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.39b -- `_observe_ledger_owner_density`'s own box (this reader's
# copy of the standard box `_observe_ledger_rung_ink` also builds) is
# RE-CENTRED where `g`'s own `Q.NOTEHEAD_RECENTRE` row exists.
#
# ⚠️ RUN RED FIRST: `_observe_ledger_owner_density` read no `Q.NOTEHEAD_
# RECENTRE` row before this round, so `cy` (and therefore the step search
# and `want_y_page`) never moved -- `test_a_recentre_row_moves_the_
# informative_step` fails (`want_y_page == 90.0`, `step == 1`, both calls)
# against the pre-2.39b tree.
# ─────────────────────────────────────────────────────────────────────────────

class FakeCellForOwnerDensity:
    def __init__(self, *, image_no_staff, bbox_page_px, upscale_factor,
                staff_line_ys_canonical):
        self.image_no_staff = image_no_staff
        self.bbox_page_px = bbox_page_px
        self.upscale_factor = upscale_factor
        self.staff_line_ys_canonical = staff_line_ys_canonical


class TestRecentreMovesTheInformativeStep(unittest.TestCase):
    """A head 2.4 spaces above the candidate's own top line -- one rung is
    informative at step 1, want_y_page 90.0. Shifting the search's own `cy`
    UP by half a space (dy_sp -0.5) pushes the head to 2.9 spaces above,
    moving the informative step to 2 (want_y_page 80.0) -- ink is painted
    at every candidate step so a step change is visible regardless of
    which one gets asked."""

    def _cell(self):
        import numpy as np
        img = _paper()
        for step in range(1, 6):
            y = 100 - step * 10
            img[int(y) - 1:int(y) + 2, 150:250] = 0
        return FakeCellForOwnerDensity(
            image_no_staff=img, bbox_page_px=[0.0, 0.0, 1000.0, 1000.0],
            upscale_factor=1.0,
            staff_line_ys_canonical=[0.0, 10.0, 20.0, 30.0, 40.0])

    def test_a_recentre_row_moves_the_informative_step(self):
        head_box = (190.0, 71.0, 210.0, 81.0)   # y_center 76.0
        cell_by_key = {(0, 0, 0, 0): self._cell()}

        baseline_log = Log()
        gather._observe_ledger_owner_density(
            baseline_log, HEAD, head_box, UP.to_key(), UP_LINES, 10.0,
            cell_by_key, None)
        base_row = baseline_log.rows(Q.LEDGER_OWNER_DENSITY, HEAD)[0]
        self.assertEqual(base_row.detail["step"], 1)
        self.assertAlmostEqual(base_row.detail["want_y_page"], 90.0)

        shifted_log = Log()
        shifted_log.observe(HEAD, Q.NOTEHEAD_RECENTRE, [0.0, -0.5],
                           reader=READERS.CV_NOTEHEAD_RECENTRE, frame="page",
                           fill=0.9, margin=0.2, runner_up=0.6)
        gather._observe_ledger_owner_density(
            shifted_log, HEAD, head_box, UP.to_key(), UP_LINES, 10.0,
            cell_by_key, None)
        shifted_row = shifted_log.rows(Q.LEDGER_OWNER_DENSITY, HEAD)[0]
        self.assertEqual(shifted_row.detail["step"], 2)
        self.assertAlmostEqual(shifted_row.detail["want_y_page"], 80.0)


if __name__ == "__main__":
    unittest.main()
