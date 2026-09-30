"""ROADMAP 2.33: two rest placement refusals plus a crop-clip refusal and a
notehead-overlap refusal, all in `adjudicators/family_precision.py`'s
`adjudicate_rest_is_not_a_rest`, next to ROADMAP 2.15's duplicate-box rule.

⚠️ RUN RED FIRST, against the tree before this lane's production edit:
`adjudicate_rest_is_not_a_rest` never reads `Q.CELL_BOX`, never calls
`_rest_off_center_refusal` / `_rest_vertical_window_refusal` /
`_rest_clipped_by_crop_refusal` / `_rest_overlaps_notehead_refusal`, and the
reasons `rest_off_center` / `rest_outside_its_staff` / `rest_clipped_by_crop`
/ `rest_overlaps_a_notehead` are not in `Q.REST_IS_NOT_A_REST`'s declared
`reasons` at all — every REFUSAL test below fails on that behaviour (the
verdict comes back `value=False, reason="rest"` instead), never on an
import error, since `Q.REST_IS_NOT_A_REST` and the decision both already
existed for the human witness and ROADMAP 2.15's duplicate-box rule.

⚠️ CONVENTION ASSUMED, PER `family_precision.py`'s §REST-PLACEMENT
docstring: Sean's own words, quoted there and not restated here. No crop
was pulled this pass (2026-09-29's process decision: wiring proved by
MICROSCOPIC RED→GREEN fixtures, no gathers, no crop batches, no pricing
runs) — the fixtures below build the handful of rows each rule reads and
check the verdict, exactly the shape `test_staged_duplicate_rest.py` and
`test_staged_family_refusals.py` already use for this same decision.

⚠️ EVERY REFUSAL TEST HAS A POSITIVE CONTROL IN THE SAME CLASS (CLAUDE.md
§6b) — a rule that refused every rest regardless of geometry would still
fail its own control.

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.adjudicate import Evidence
from tools.omr.staged.adjudicators.family_precision import (
    _rest_overlaps_notehead_refusal,
)
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_family_refusals import (
    CELL, _box, _page_box_at_step, _staff_geometry,
)

#: The bar's own [x0, x1] in page pixels — no horizontal pad (see
#: `family_precision._cell_box_page_px`'s own docstring for why the cell
#: frame can be read directly as the bar extent). Centre is x=600.
BAR_X0, BAR_X1 = 400.0, 800.0
BAR_Y0, BAR_Y1 = 900.0, 1200.0


def _bar_box(log, *, x0=BAR_X0, x1=BAR_X1, y0=BAR_Y0, y1=BAR_Y1):
    log.observe(CELL, Q.CELL_BOX, [x0, y0, x1, y1],
                reader=READERS.GEOMETRY, frame="cell:0")


def _rest(log, gi, cls, *, page_box):
    """One rest glyph's `Q.GLYPH_BOX` (carrying `bbox_page_px`) and `Q.REST`
    rows — `_box`'s own shape, `quantity=Q.REST` files the domain row
    `adjudicate_rest_is_not_a_rest` reads for its subject population."""
    return _box(log, gi, cls, quantity=Q.REST, page_box=page_box)


def _notehead(log, gi, cls, *, page_box):
    return _box(log, gi, cls, quantity=Q.NOTEHEAD_CLASS, page_box=page_box)


def _stem(log, gi, *, x, y, w=10.0, h=100.0):
    """One `Q.STEM` box, CELL canonical `(x, y, w, h)` — no class name, no
    page fields at all (`gather.py`'s own comment on the quantity)."""
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.STEM, (x, y, w, h), reader=READERS.DETECTOR,
                frame="cell:0", score=0.8, category="stem")
    return g


def _run(log, *quantities):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=tuple(quantities))
    return log


# ─────────────────────────────────────────────────────────────────────────────
# Rule 1 — `rest_off_center` (restWhole only)
# ─────────────────────────────────────────────────────────────────────────────

class TestRestOffCenter(unittest.TestCase):

    def test_off_center_whole_rest_is_refused(self):
        """A `restWhole` whose centre sits far to one side of the bar (here
        at x=420, offset 0.45 of the 400px bar width — well past the
        middle-third boundary at 1/6 ~= 0.167) is refused."""
        log = Log()
        _bar_box(log)
        g = _rest(log, 0, "restWhole", page_box=[400.0, 1000.0, 440.0, 1040.0])
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_off_center")

    def test_centered_whole_rest_is_kept(self):
        """⚠️ THE CONTROL THAT CAN FAIL. The same class, centred in the same
        bar (box centred on x=600, the bar's own centre) — offset 0.0."""
        log = Log()
        _bar_box(log)
        g = _rest(log, 0, "restWhole", page_box=[580.0, 1000.0, 620.0, 1040.0])
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_off_center_rule_does_not_apply_to_half_rests(self):
        """Sean's own narrowing (`family_precision.py` §REST-PLACEMENT,
        item 1): the blanket centring refusal is for WHOLE rests only. A
        `restHalf` at the SAME far-off-centre x as the refused `restWhole`
        above, but shaped as a genuine half rest (sitting ON one staff
        line — y-range [1030, 1050], centred on line 1040, touching no
        OTHER line — rule 3's own `one_line` shape, never `two_lines`) is
        NOT refused by this rule, nor by rule 3, nor by anything else in
        this fixture."""
        log = Log()
        _bar_box(log)
        _staff_geometry(log)
        g = _rest(log, 0, "restHalf",
                 page_box=[400.0, 1030.0, 440.0, 1050.0])
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")


# ─────────────────────────────────────────────────────────────────────────────
# Rule 2 — `rest_outside_its_staff` (per-class vertical window)
# ─────────────────────────────────────────────────────────────────────────────

class TestRestVerticalWindow(unittest.TestCase):

    def test_whole_rest_far_outside_the_staff_is_refused(self):
        """A `restWhole` 2.0 spaces above the top line (step 8 + 2*2 = 12)
        — past the MEDIUM 1.5-space window whole/half/`restHBar` get after
        recalibration (manager review, 2026-09-29: a displaced whole/half
        rest hangs a full space above the staff, so the original 1.0-space
        TIGHT tier was too tight — see the module CONVENTION header)."""
        log = Log()
        _staff_geometry(log)
        g = _rest(log, 0, "restWhole", page_box=_page_box_at_step(12.0))
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_outside_its_staff")

    def test_whole_rest_one_space_above_the_staff_is_kept(self):
        """⚠️ THE CONTROL THAT CAN FAIL, added on manager review: a displaced
        `restWhole` hanging ONE space clear above the top line (a real
        two-voice shape, not registration noise) — inside the 1.5-space
        MEDIUM window, where the original 1.0-space TIGHT tier would have
        refused it."""
        log = Log()
        _staff_geometry(log)
        g = _rest(log, 0, "restWhole", page_box=_page_box_at_step(10.0))
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_quarter_rest_now_gets_the_wide_window_is_kept(self):
        """⚠️ THE CONTROL THAT CAN FAIL. `restQuarter` moved from the TIGHT
        tier to the WIDE (2.5-space) one on manager review — a quarter rest
        is displaced for a second voice exactly as an 8th rest is, and needs
        the same room. 2.0 spaces above the top line: past the original
        1.0-space tier, inside the 2.5-space one it gets now."""
        log = Log()
        _staff_geometry(log)
        g = _rest(log, 0, "restQuarter", page_box=_page_box_at_step(12.0))
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_8th_rest_moderately_outside_the_staff_is_kept(self):
        """Sean's own correction: *"I did see some 8th note rests outside
        the staff but not nearly as far as note heads."* An `rest8th`
        centred 1.75 spaces above the top line — outside the MEDIUM window
        but well inside the 2.5-space WIDE one 8th-and-smaller (and now
        `restQuarter`) get."""
        log = Log()
        _staff_geometry(log)
        g = _rest(log, 0, "rest8th", page_box=_page_box_at_step(11.5))
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_8th_rest_far_outside_the_staff_is_refused(self):
        """The same class, this time 3.0 spaces above the top line — past
        even the WIDE window, "not nearly as far as note heads" still
        being a bound, not an unlimited pass."""
        log = Log()
        _staff_geometry(log)
        g = _rest(log, 0, "rest8th", page_box=_page_box_at_step(14.0))
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_outside_its_staff")


# ─────────────────────────────────────────────────────────────────────────────
# Rule 3 — `rest_clipped_by_crop`
# ─────────────────────────────────────────────────────────────────────────────

class TestRestClippedByCrop(unittest.TestCase):

    def test_rest_flush_against_the_cell_top_edge_is_refused(self):
        """A `restWhole` whose own page box touches the cell's top edge
        exactly (Sean: a notehead cut in half by the crop reads as this
        shape, in a staff above or below the main one)."""
        log = Log()
        _bar_box(log, y0=1000.0, y1=1300.0)
        g = _rest(log, 0, "restWhole",
                 page_box=[580.0, 1000.0, 620.0, 1040.0])
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_clipped_by_crop")

    def test_rest_a_few_px_inside_the_edge_is_kept(self):
        """⚠️ THE CONTROL THAT CAN FAIL. The SAME box, moved 3 page px away
        from the cell's top edge (well past `CELL_EDGE_TOLERANCE_PAGE_PX`,
        1 px) — and centred, and inside the tight vertical window, so no
        OTHER rule in this file can refuse it either."""
        log = Log()
        _bar_box(log, y0=1000.0, y1=1300.0)
        _staff_geometry(log, line_ys=[1040.0, 1060.0, 1080.0, 1100.0, 1120.0])
        g = _rest(log, 0, "restWhole",
                 page_box=[580.0, 1003.0, 620.0, 1043.0])
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")


# ─────────────────────────────────────────────────────────────────────────────
# (c) — `rest_has_a_stem`
# ─────────────────────────────────────────────────────────────────────────────

class TestRestHasAStem(unittest.TestCase):

    def test_rest_with_an_overlapping_stem_is_refused(self):
        """Sean: *"if there is a stem attached... that helps"* — a rest
        never has a stem. A `Q.STEM` box overlapping this `restWhole`'s own
        canonical box (`_rest`'s default (200, 200, 140, 20)) refuses it,
        for EVERY rest class."""
        log = Log()
        g = _rest(log, 0, "restWhole", page_box=_page_box_at_step(4.0))
        _stem(log, 1, x=250.0, y=190.0, w=5.0, h=100.0)
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_has_a_stem")

    def test_rest_with_no_stem_nearby_is_kept(self):
        """⚠️ THE CONTROL THAT CAN FAIL. A `restWhole` with a `Q.STEM` box
        FAR from its own — no overlap — is unaffected."""
        log = Log()
        g = _rest(log, 0, "restWhole", page_box=_page_box_at_step(4.0))
        _stem(log, 1, x=900.0, y=900.0, w=5.0, h=100.0)
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")


# ─────────────────────────────────────────────────────────────────────────────
# (a) — `rest_touches_two_staff_lines` (restWhole/restHalf only)
# ─────────────────────────────────────────────────────────────────────────────

class TestRestTouchesTwoStaffLines(unittest.TestCase):

    def test_restwhole_spanning_two_lines_is_refused(self):
        """Sean, DECISIONS 2026-09-29: *"a common mistake was a black
        notehead called a whole or half rest. The rest should never touch
        2 different staff lines."* A box whose top edge sits on line 1000
        and bottom edge sits on line 1020 (LINE_YS default, tol 5 px) fills
        a whole space — a notehead's own shape."""
        log = Log()
        _staff_geometry(log)
        g = _rest(log, 0, "restWhole", page_box=[500.0, 1000.0, 560.0, 1020.0])
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_touches_two_staff_lines")

    def test_restwhole_hanging_from_one_line_is_kept(self):
        """⚠️ THE CONTROL THAT CAN FAIL. A genuine WHOLE rest: top edge on
        line 1000, bottom edge 10 px below (well short of line 1020,
        10 px > the 5 px tolerance) — touches exactly ONE line."""
        log = Log()
        _staff_geometry(log)
        g = _rest(log, 0, "restWhole", page_box=[500.0, 1000.0, 560.0, 1010.0])
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_resthalf_sitting_on_one_line_is_kept(self):
        """⚠️ THE CONTROL THAT CAN FAIL. A genuine HALF rest: centred ON
        line 1040 (y-range [1030, 1050]), touching no OTHER line."""
        log = Log()
        _staff_geometry(log)
        g = _rest(log, 0, "restHalf", page_box=[500.0, 1030.0, 560.0, 1050.0])
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_two_line_rule_does_not_apply_to_quarter_rests(self):
        """`restQuarter` is excluded (§REST-VS-NOTEHEAD: quarter/8th/etc.
        legitimately span more than one line/space by their own shape).
        The SAME two-line geometry that refused the `restWhole` above,
        this time on a `restQuarter`, is NOT refused by this rule (nor by
        anything else in this fixture)."""
        log = Log()
        _staff_geometry(log)
        g = _rest(log, 0, "restQuarter",
                 page_box=[500.0, 1000.0, 560.0, 1020.0])
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")


# ─────────────────────────────────────────────────────────────────────────────
# Rule 4 — `rest_overlaps_a_notehead`, and (b)'s resolution for
# restWhole/restHalf
# ─────────────────────────────────────────────────────────────────────────────

class TestRestOverlapsNotehead(unittest.TestCase):

    def test_rest_overlapping_a_live_notehead_is_refused(self):
        """A rest box and a notehead box drawn on the SAME ink (high IoU,
        both at the same canonical position) in one cell — the notehead's
        own `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` verdict is DECIDED `False` (kept,
        a live candidate), so the overlap is decisive."""
        log = Log()
        _staff_geometry(log)   # Q.CELL_STAFF_SPACE, for `_same_mark_centres`
        rest = _rest(log, 0, "rest8th", page_box=_page_box_at_step(4.0))
        # ⚠️ `_notehead` (== `_box`) defaults its CANONICAL box to the exact
        # same (x_c=200, y_c=200, w_c=140, h_c=20) `_rest` used above -- one
        # mark, two class readings -- so `_rest_box_iou` reads IoU 1.0
        # without a second, redundant `Q.GLYPH_BOX` observation.
        _notehead(log, 1, "noteheadBlack", page_box=_page_box_at_step(4.0))
        _run(log, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, rest)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_overlaps_a_notehead")

    def test_rest_overlapping_an_already_refused_notehead_is_not_refused(
            self):
        """⚠️ THE CONTROL THAT CAN FAIL. The SAME overlap, but the notehead's
        OWN `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` verdict is DECIDED refused (a
        human said `not_a_symbol`) — a refused notehead's ink proves
        nothing about a rest drawn on the same spot (CLAUDE.md rule 8),
        because `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` runs BEFORE this rule and a
        refused verdict is visible to it (the exact connection the section
        docstring names)."""
        log = Log()
        _staff_geometry(log)   # Q.CELL_STAFF_SPACE, for `_same_mark_centres`
        rest = _rest(log, 0, "rest8th", page_box=_page_box_at_step(4.0))
        head = _notehead(log, 1, "noteheadBlack",
                         page_box=_page_box_at_step(4.0))
        log.observe(head, Q.HUMAN_BOX_VERDICT, "not_a_symbol",
                    reader=READERS.SEAN, frame="review:box",
                    sidecar="t.json", action="act-0001")
        _run(log, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.REST_IS_NOT_A_REST)
        head_v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, head)
        self.assertIs(head_v.value, True)   # the notehead itself IS refused
        v = log.verdict(Q.REST_IS_NOT_A_REST, rest)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_displaced_voice_rest_touching_the_other_voices_notehead_is_kept(
            self):
        """⚠️ THE CONTROL THAT CAN FAIL, added on manager review: a displaced
        voice-2 rest and a voice-1 notehead, boxes TOUCHING (IoU ~0.05 —
        above the old 0.02 duplicate floor, comfortably below the new 0.3
        substantial-overlap floor) but centres a full staff space apart
        (dy_spaces 0.9, past `NOTEHEAD_DUPLICATE_MAX_DY_STAFF_SPACES` 0.25)
        — a real two-voice shape, never one mark. Kept on EITHER gate
        alone; both are checked."""
        log = Log()
        _staff_geometry(log)
        rest = _rest(log, 0, "rest8th",
                    page_box=_page_box_at_step(4.0))
        log.observe(rest, Q.GLYPH_BOX,
                    ("rest8th", 200.0, 200.0, 140.0, 100.0),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.7,
                    category="rest", bbox_page_px=_page_box_at_step(4.0))
        head = _notehead(log, 1, "noteheadBlack",
                         page_box=_page_box_at_step(4.0))
        log.observe(head, Q.GLYPH_BOX,
                    ("noteheadBlack", 200.0, 290.0, 140.0, 100.0),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                    category="notehead", bbox_page_px=_page_box_at_step(4.0))
        _run(log, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, rest)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_rest_with_no_overlapping_notehead_is_kept(self):
        """A rest with no notehead anywhere in the cell — the ordinary
        case, and the population every other test's fixtures also rely on
        implicitly."""
        log = Log()
        rest = _rest(log, 0, "rest8th", page_box=_page_box_at_step(4.0))
        _run(log, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, rest)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    # ─────────────────────────────────────────────────────────────────────
    # (b): for restWhole/restHalf, rule (a)'s shape RESOLVES an overlap
    # instead of always refusing the rest. Three outcomes.
    # ─────────────────────────────────────────────────────────────────────

    def test_overlap_resolved_one_line_the_rest_stands(self):
        """A `restWhole` overlapping a live notehead (same canonical box,
        so IoU/centres match trivially) whose OWN page shape is a genuine
        one-line whole rest (top edge on line 1000, bottom 10 px below —
        rule (a)'s `one_line`, never `two_lines`): the rest STANDS (kept),
        and the resolution is recorded so a future EVALUATE consequence has
        an address to read (§REST-VS-NOTEHEAD's own named next step)."""
        log = Log()
        _staff_geometry(log)
        rest = _rest(log, 0, "restWhole",
                    page_box=[500.0, 1000.0, 640.0, 1010.0])
        _notehead(log, 1, "noteheadBlack",
                 page_box=[500.0, 1000.0, 640.0, 1010.0])
        _run(log, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, rest)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")
        self.assertEqual(v.detail.get("rest_overlaps_notehead_resolved"),
                         "rest_stands")
        self.assertTrue(v.detail.get("notehead_reading_should_be_dropped"))

    def test_overlap_resolved_cannot_tell_refuses_neither(self):
        """⚠️ THE CONTROL THAT CAN FAIL. The SAME overlap, but with NO
        `Q.STAFF_LINES`/`Q.STAFF_SPACING` at all (only `Q.CELL_STAFF_SPACE`,
        via `_staff_geometry(log, line_ys=None, spacing=None)`) — rule
        (a)'s shape test cannot run, so it reads `cannot_tell`. Rule 8:
        a cannot-tell case refuses NEITHER reading."""
        log = Log()
        _staff_geometry(log, line_ys=None, spacing=None)
        rest = _rest(log, 0, "restWhole",
                    page_box=[500.0, 1000.0, 640.0, 1010.0])
        _notehead(log, 1, "noteheadBlack",
                 page_box=[500.0, 1000.0, 640.0, 1010.0])
        _run(log, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, rest)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")
        self.assertEqual(v.detail.get("rest_overlaps_notehead_resolved"),
                         "cannot_tell")
        self.assertTrue(v.detail.get("rest_overlaps_notehead_ambiguous"))

    def test_overlap_resolution_two_lines_branch_direct(self):
        """The `two_lines` branch inside the OVERLAP resolution itself is
        unreachable through the full ladder (rule (a) runs earlier and
        would already have refused — the production docstring's own
        claim); this calls `_rest_overlaps_notehead_refusal` DIRECTLY with
        `detail["line_shape"]` pre-seeded, so the defensive branch is
        exercised rather than merely asserted dead."""
        log = Log()
        _staff_geometry(log)
        rest = _rest(log, 0, "restWhole", page_box=_page_box_at_step(4.0))
        _notehead(log, 1, "noteheadBlack", page_box=_page_box_at_step(4.0))
        log.freeze()
        ev = Evidence(log, rest, adjudicate.REGISTRY[Q.REST_IS_NOT_A_REST])
        box_row = ev.rows(Q.GLYPH_BOX)[-1]
        detail = {"class": "restWhole", "line_shape": "two_lines"}
        result = _rest_overlaps_notehead_refusal(ev, box_row, detail)
        self.assertIsNotNone(result)
        self.assertIs(result.value, True)
        self.assertEqual(result.reason, "rest_touches_two_staff_lines")


if __name__ == "__main__":
    unittest.main()
