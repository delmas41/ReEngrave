"""ROADMAP 2.52: a whole rest the detector never boxed, found by a targeted
ink search in a bar with no notehead/rest box at all.

Sean / `docs/DECISIONS.md` 2026-10-01: *"If a bar has no notes it should
expect to find a whole note rest and look in the middle of the bar first.
If it finds it then the bar is complete."* `gather.gather_empty_bar_rest_
search` is the GATHER half (a targeted connected-component search over the
cell's own, LOCALLY-corrected staff lines); `adjudicators.rest_search.
adjudicate_empty_bar_whole_rest` is the ADJUDICATE half that turns a match
into "whole-bar rest" and a miss into an ABSTENTION, never a `False` that
would claim the bar is silent (CLAUDE.md §2 rule 8).

GATHER+ADJUDICATE ONLY (Sean, 2026-09-30): this file does not touch
EVALUATE/EXPORT, and `TestTheAdjudicateDecision` injects the GATHER row
directly rather than running a full GATHER pass, the same pattern
`test_staged_unread_mark.py` uses for `Q.UNREAD_MARK`.

⚠️ RUN RED FIRST, against the tree before `gather_empty_bar_rest_search`
and `rest_search.py` existed: every test below fails on `AttributeError`
(no such function) or `KeyError` (no such quantity in the registry).
"""
from __future__ import annotations

import unittest

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401 -- registers decisions
from tools.omr.staged import gather
from tools.omr.staged.record import (
    Log, Outcome, Q, cell as R_cell,
)

#: The synthetic staff shared by every GATHER-level test: 5 lines, 20px
#: apart (half_step = 10px), ascending top (index 0) to bottom (index 4) --
#: the SAME ordering `_cell_grid` assumes of `staff_line_ys_canonical`.
LINES = [20.0, 40.0, 60.0, 80.0, 100.0]
BOTTOM_LINE = LINES[-1]      # 100.0
HALF_STEP = 10.0             # (LINES[1]-LINES[0]) / 2.0... == gap/2
#: 4th line from the bottom, 2nd from the top -- where a whole rest hangs.
TARGET_LINE = LINES[1]       # 40.0
BAR_WIDTH = 120
BAR_HEIGHT = 160
#: Middle third of `BAR_WIDTH`: [40, 80].
MID_LO, MID_HI = BAR_WIDTH / 3.0, 2.0 * BAR_WIDTH / 3.0


class _FakeDet:
    def __init__(self, smufl_name):
        self.smufl_name = smufl_name


class _FakeCell:
    """The handful of attributes `gather_empty_bar_rest_search` reads off a
    real `MeasureCell` -- nothing else."""

    def __init__(self, image_no_staff, *, line_ys=LINES, page_index=0,
                staff_index=0, measure_index=0):
        self.image_no_staff = image_no_staff
        self.staff_line_ys_canonical = list(line_ys)
        self.page_index = page_index
        self.staff_index = staff_index
        self.measure_index = measure_index


def _blank_image(width=BAR_WIDTH, height=BAR_HEIGHT):
    return np.full((height, width), 255, dtype=np.uint8)


def _image_with_block(x0, y0, x1, y1, *, width=BAR_WIDTH, height=BAR_HEIGHT):
    img = _blank_image(width, height)
    img[int(y0):int(y1), int(x0):int(x1)] = 0
    return img


def _whole_rest_block(x0):
    """A 20x10px (1.0 x 0.5 staff-space) filled block centred vertically at
    `WHOLE_REST_STEP` (step 5.5): top edge AT the target line (y=40),
    hanging DOWN from it."""
    return _image_with_block(x0, TARGET_LINE, x0 + 20.0, TARGET_LINE + 10.0)


def _half_rest_block(x0):
    """Same shape, but centred at `HALF_REST_STEP` (step 4.5): resting ON
    the 3rd (middle) line, y=60 -- SITS ON it, never hangs under the 4th."""
    return _image_with_block(x0, 50.0, x0 + 20.0, 60.0)


def _run_gather(cell, detections=None):
    log = Log()
    local = {cell.staff_index: (0, 0)}
    gather.gather_empty_bar_rest_search(log, [cell], local, detections or {})
    return log


def _sub():
    return R_cell(0, 0, 0, 0)


class TestTheGatherSearch(unittest.TestCase):
    def test_a_whole_rest_in_the_middle_of_the_bar_is_found(self):
        """The population this search exists for: centred in the bar."""
        img = _whole_rest_block(x0=50.0)  # centre 60, inside [40, 80]
        log = _run_gather(_FakeCell(img))
        rows = log.rows(Q.EMPTY_BAR_REST_SEARCH, _sub())
        self.assertEqual(len(rows), 1)
        self.assertIs(rows[0].value, True)
        self.assertEqual(rows[0].detail["witness"], "middle")

    def test_an_off_centre_whole_rest_is_found_by_widening(self):
        """CLAUDE.md §2 rule 7's own shape: the middle-first search must not
        be the ONLY search, or an off-centre real rest is missed."""
        img = _whole_rest_block(x0=5.0)  # centre 15, OUTSIDE [40, 80]
        log = _run_gather(_FakeCell(img))
        rows = log.rows(Q.EMPTY_BAR_REST_SEARCH, _sub())
        self.assertEqual(len(rows), 1)
        self.assertIs(rows[0].value, True)
        self.assertEqual(rows[0].detail["witness"], "widened")

    def test_a_half_rest_shape_on_the_middle_line_is_not_a_whole_rest(self):
        """⚠️ CLAUDE.md rule 7 -- a control that can fail. Same shape as the
        population test, deliberately placed where a HALF rest sits (ON the
        3rd line), not where a whole rest hangs (under the 4th)."""
        img = _half_rest_block(x0=50.0)
        log = _run_gather(_FakeCell(img))
        rows = log.rows(Q.EMPTY_BAR_REST_SEARCH, _sub())
        self.assertEqual(len(rows), 1)
        self.assertIs(rows[0].value, False)
        self.assertEqual(rows[0].detail.get("reason"),
                         "not_rest_shaped_or_positioned")

    def test_an_empty_bar_with_no_ink_is_not_found(self):
        """No ink at all -- the search looked and found nothing to test,
        which is a DIFFERENT fact from 'found a shape and rejected it'."""
        log = _run_gather(_FakeCell(_blank_image()))
        rows = log.rows(Q.EMPTY_BAR_REST_SEARCH, _sub())
        self.assertEqual(len(rows), 1)
        self.assertIs(rows[0].value, False)
        self.assertEqual(rows[0].detail.get("reason"), "no_ink")

    def test_a_bar_with_a_notehead_box_is_never_searched(self):
        """⚠️ CLAUDE.md 2026-10-01 'Leave the whole rest alone': this search
        only ever looks at a bar GATHER already shows has NO notehead/rest
        box. A bar that already has one is untouched -- no row at all, not
        even an abstention."""
        img = _whole_rest_block(x0=50.0)  # shape would otherwise fire
        cell = _FakeCell(img)
        sub = R_cell(0, 0, 0, 0)
        detections = {sub.to_key(): [_FakeDet("noteheadBlackOnLine")]}
        log = _run_gather(cell, detections)
        self.assertEqual(log.rows(Q.EMPTY_BAR_REST_SEARCH, sub), ())
        self.assertEqual(log.refusals(Q.EMPTY_BAR_REST_SEARCH, sub), ())

    def test_a_bar_with_a_rest_box_is_never_searched(self):
        """Same guard, the REST half of it."""
        img = _whole_rest_block(x0=50.0)
        cell = _FakeCell(img)
        sub = R_cell(0, 0, 0, 0)
        detections = {sub.to_key(): [_FakeDet("restQuarter")]}
        log = _run_gather(cell, detections)
        self.assertEqual(log.rows(Q.EMPTY_BAR_REST_SEARCH, sub), ())

    def test_no_image_no_staff_abstains_no_mask(self):
        """`_ink_components` returns `None`, not `[]`, when the cell carries
        no erased raster at all -- a different fact from an erased raster
        with nothing on it."""
        cell = _FakeCell(None)
        log = _run_gather(cell)
        sub = R_cell(0, 0, 0, 0)
        self.assertEqual(log.rows(Q.EMPTY_BAR_REST_SEARCH, sub), ())
        refusals = log.refusals(Q.EMPTY_BAR_REST_SEARCH, sub)
        self.assertEqual(len(refusals), 1)
        self.assertEqual(refusals[0].reason, "no_mask")


def _decide(log, subject=None):
    subject = subject or R_cell(0, 0, 0, 0)
    spec = adjudicate.REGISTRY[Q.EMPTY_BAR_WHOLE_REST]
    log.freeze()
    v = adjudicate.adjudicate_one(log, spec, subject)
    assert v.quantity == Q.EMPTY_BAR_WHOLE_REST
    return v


class TestTheAdjudicateDecision(unittest.TestCase):
    def test_a_found_search_result_decides_the_bar_is_a_whole_rest(self):
        log = Log()
        sub = R_cell(0, 0, 0, 0)
        log.observe(sub, Q.EMPTY_BAR_REST_SEARCH, True,
                   reader="cv_rest_search", frame="cell:0", found=True,
                   witness="middle", staff_step=5.5)
        v = _decide(log, sub)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "whole_rest_found_by_search")
        self.assertEqual(v.detail.get("witness"), "middle")
        self.assertTrue(v.considered)
        self.assertFalse(v.missing)
        self.assertFalse(v.declined)

    def test_a_search_that_found_nothing_abstains_never_claims_empty(self):
        """⚠️ CLAUDE.md §2 rule 8: a fallback never converts 'cannot tell'
        into an answer. `found=False` must NOT become a `False` verdict
        that would claim the bar is empty -- only an abstention, counted
        as unread."""
        log = Log()
        sub = R_cell(0, 0, 0, 0)
        log.observe(sub, Q.EMPTY_BAR_REST_SEARCH, False,
                   reader="cv_rest_search", frame="cell:0", found=False,
                   reason="not_rest_shaped_or_positioned")
        v = _decide(log, sub)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "not_found_by_search")
        self.assertIsNone(v.value)

    def test_no_ink_at_all_also_abstains_not_a_false(self):
        log = Log()
        sub = R_cell(0, 0, 0, 0)
        log.observe(sub, Q.EMPTY_BAR_REST_SEARCH, False,
                   reader="cv_rest_search", frame="cell:0", found=False,
                   reason="no_ink")
        v = _decide(log, sub)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "not_found_by_search")

    def test_no_gather_row_at_all_abstains(self):
        """Neither an Observation nor an Abstention was ever filed (the
        decision reached a subject outside its own `subjects_from` domain,
        which can only happen if called directly, as this test does)."""
        log = Log()
        sub = R_cell(0, 0, 0, 0)
        v = _decide(log, sub)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)

    def test_the_no_staff_geometry_abstention_passes_through(self):
        log = Log()
        sub = R_cell(0, 0, 0, 0)
        log.abstain(sub, Q.EMPTY_BAR_REST_SEARCH, reader="cv_rest_search",
                   frame="cell:0", reason="no_staff_geometry")
        v = _decide(log, sub)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_staff_geometry")


if __name__ == "__main__":
    unittest.main()
