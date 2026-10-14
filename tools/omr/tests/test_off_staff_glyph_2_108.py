"""ROADMAP 2.108 (Sean, 2026-10-13, hand-labelling Brahms 317803 pdf 0): *"the
title text like symphonie is showing up as noteheads but there is no staff
anywhere near"*.

CAUSE. The hand-truth session (`tools/omr/hand_truth/session.py`) cuts every bit
of ink outside the measure cells into `top` / `margin` / `bottom` region cells and
runs the DETECTOR on them, so a title letter's bowl comes back `noteheadBlack*`
and is queued as a pre-fill (Brahms pdf 0: 1,610 of 2,221 queued heads are 8+
staff spaces from every staff). The STAGED gather cuts no region cells (a cell is
a staff band plus a 4-6 space pad), so nothing in the title reaches it; its
farthest kept head on Brahms pdf 0-1 is 4.95 spaces out. The staged rule is the
guard against a cell that ever reaches farther.

RULE. A pitch-bearing glyph (head, rest, accidental, dot) `OFF_STAFF_REACH_SPACES`
(8) or more from EVERY staff at its x is not music: STAGED `off_staff_glyph` on
the notehead decider, and the pre-fill queue never offers it. Positive controls:
real far notes (a head 5 spaces out, a head with a ledger rung, a head beside
another staff), and Sean's own labels.

RED first: against the unrepaired tree the title head is kept as `notehead`.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import geometry as G
from tools.omr.staged import margins
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests.test_staged_notehead_precision import (
    SPACING, _cell_geometry, _ledger, _notehead, _run)

SP_PAGE = 20.0
LINES = [1000.0, 1020.0, 1040.0, 1060.0, 1080.0]      # page px, spacing 20
STAFF0 = R.staff(0, 0, 0)
STAFF1 = R.staff(0, 0, 1)


def _staff(log, staff=STAFF0, lines=LINES, extent=(400.0, 2400.0)):
    log.observe(staff, Q.STAFF_LINES, list(lines), reader=READERS.GEOMETRY, frame="page")
    log.observe(staff, Q.STAFF_SPACING, SP_PAGE, reader=READERS.GEOMETRY, frame="page")
    if extent is not None:
        log.observe(staff, Q.STAFF_EXTENT, extent, reader=READERS.GEOMETRY, frame="page")


def _head(log, gi, *, spaces_above_top, x=1200.0, **kw):
    """A head whose centre is `spaces_above_top` staff spaces above the top line."""
    cy = LINES[0] - spaces_above_top * SP_PAGE
    return _notehead(log, gi, cls="noteheadBlackInSpace", page_box=[x - 14, cy - 10, x + 14, cy + 10],
                     **kw)


def _verdict(log, g):
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)


class TestStagedOffStaffGlyph(unittest.TestCase):

    def _run(self, spaces, **kw):
        log = Log()
        _cell_geometry(log)
        _staff(log)
        g = _head(log, 0, spaces_above_top=spaces, **kw)
        return _run(log), g

    def test_a_head_with_no_staff_near_is_refused_RED(self):
        """The title letter: 15 spaces above the top staff."""
        log, g = self._run(15.0)
        v = _verdict(log, g)
        self.assertEqual((v.value, v.reason), (True, "off_staff_glyph"))

    def test_the_margin_is_the_distance_past_the_reach(self):
        log, g = self._run(15.0)
        v = _verdict(log, g)
        # centre 15 sp above the top line, minus the reach
        self.assertAlmostEqual(v.margin, 15.0 - G.OFF_STAFF_REACH_SPACES, places=2)
        self.assertEqual(v.detail["margin_axis"], "nearest_staff_spaces")

    def test_CONTROL_a_real_far_ledger_note_is_kept(self):
        """5 spaces out is the farthest real head on the acceptance pages."""
        log, g = self._run(5.0)
        self.assertEqual(_verdict(log, g).reason, "notehead")

    def test_CONTROL_just_inside_the_reach_is_kept_just_outside_is_not(self):
        log, g = self._run(G.OFF_STAFF_REACH_SPACES - 0.5)
        self.assertFalse(_verdict(log, g).value)
        log, g = self._run(G.OFF_STAFF_REACH_SPACES + 0.5)
        self.assertTrue(_verdict(log, g).value)

    def test_CONTROL_a_head_far_from_its_filed_staff_but_beside_another_is_kept(self):
        """The cell's pad reaches the next staff: 14 spaces from the filed staff,
        1 from its neighbour. Not off-staff; `belongs_to_a_nearer_staff` owns it."""
        log = Log()
        _cell_geometry(log)
        _staff(log)
        _staff(log, staff=STAFF1, lines=[l - 17 * SP_PAGE for l in LINES])
        g = _head(log, 0, spaces_above_top=14.0)
        log = _run(log)
        self.assertNotEqual(_verdict(log, g).reason, "off_staff_glyph")

    def test_CONTROL_a_ledger_rung_beside_a_far_head_keeps_it(self):
        """The ledger lines name the owner: a kept rung under the head."""
        log = Log()
        _cell_geometry(log)
        _staff(log)
        g = _head(log, 0, spaces_above_top=9.0)
        # the head's canonical box: x_c 200, y_c 200, w 140, h 100 -> rung on it
        _ledger(log, 1, x_c=200.0, y_c=240.0)
        log = _run(log)
        self.assertNotEqual(_verdict(log, g).reason, "off_staff_glyph")

    def test_CONTROL_missing_staff_extent_never_calls_a_head_far(self):
        """Rule 8: no staff measured on the page is not 'no staff near'."""
        log = Log()
        _cell_geometry(log)
        _staff(log, extent=None)
        g = _head(log, 0, spaces_above_top=15.0)
        log = _run(log)
        self.assertNotEqual(_verdict(log, g).reason, "off_staff_glyph")

    def test_CONTROL_a_head_beside_the_staff_but_off_its_x_is_judged_by_the_gap(self):
        """The staff has a left end: a head 40 spaces left of it on the staff's own
        height is as far from it as one 40 spaces above."""
        log = Log()
        _cell_geometry(log)
        _staff(log, extent=(2000.0, 4000.0))
        g = _head(log, 0, spaces_above_top=-2.0, x=2000.0 - 40 * SP_PAGE)
        log = _run(log)
        self.assertEqual(_verdict(log, g).reason, "off_staff_glyph")


class TestRegistered(unittest.TestCase):
    def test_the_reason_is_a_threshold_that_files_a_margin(self):
        problems, _ = margins.check_margins()
        self.assertEqual(problems, [])
        self.assertIn("off_staff_glyph",
                      margins.threshold_reasons("adjudicate_notehead_is_not_a_notehead"))

    def test_the_audit_counts_a_marginless_off_staff_verdict(self):
        """The control can fail: a verdict of the reason with no margin is counted."""
        probe = [{"decider": "adjudicate_notehead_is_not_a_notehead",
                  "reason": "off_staff_glyph", "margin": None, "outcome": "decided"}]
        self.assertEqual(margins.audit(probe)["without_margin"], 1)


class TestGeometryStick(unittest.TestCase):
    BANDS = [(0.0, 100.0, 1000.0, 1080.0, 20.0)]

    def test_inside_the_band_is_zero(self):
        self.assertEqual(G.distance_to_staff_spaces(50.0, 1040.0, self.BANDS), 0.0)

    def test_vertical_gap_in_that_staffs_spaces(self):
        self.assertAlmostEqual(G.distance_to_staff_spaces(50.0, 900.0, self.BANDS), 5.0)

    def test_past_the_end_it_is_the_straight_line_gap(self):
        self.assertAlmostEqual(G.distance_to_staff_spaces(160.0, 1160.0, self.BANDS), 5.0)

    def test_no_staff_is_none_never_far(self):
        self.assertIsNone(G.distance_to_staff_spaces(0.0, 0.0, []))


# ---------------------------------------------------------------- the pre-fill queue
import pytest  # noqa: E402

cv2 = pytest.importorskip("cv2")

from tools.omr.hand_truth import session as S  # noqa: E402
from tools.omr.hand_truth import store  # noqa: E402
from tools.omr.tests.test_hand_truth_session import synth_page  # noqa: E402


class _Det:
    def __init__(self, name, x0, y0, x1, y1, conf=0.8):
        self.smufl_name, self.confidence = name, conf
        self.x_canonical, self.y_canonical = x0, y0
        self.width_canonical, self.height_canonical = x1 - x0, y1 - y0


@pytest.fixture(scope="module")
def cut():
    return S.build_page(synth_page(), edition="synthetic", pdf="synthetic")


def _fake_detector(monkeypatch, per_cell):
    """A detector that returns, for each cell id, boxes given in PAGE pixels
    (converted to the cell's canonical frame), so a test chooses what 'the
    detector saw' on the title, the page number and the staves."""
    import tools.omr.yolo_detector as Y

    class Fake:
        def __init__(self, weights):
            pass

        def detect(self, mc, conf_threshold=0.25):
            x0, y0 = mc.bbox_page_px[0], mc.bbox_page_px[1]
            up = mc.upscale_factor
            out = []
            for name, (a, b, c, d) in per_cell(mc):
                out.append(_Det(name, (a - x0) * up, (b - y0) * up, (c - x0) * up, (d - y0) * up))
            return out

    monkeypatch.setattr(Y, "YoloDetector", Fake)


def _prefill(cut, monkeypatch, boxes_by_page_point):
    page, images, mcells = cut
    page = store.PageTruth.from_json(__import__("json").loads(__import__("json").dumps(page.to_json())))
    regions = {c.id: images[c.id] for c in page.cells if c.kind != "measure"}

    def per_cell(mc):
        x0, y0, x1, y1 = mc.bbox_page_px
        return [(n, r) for n, r in boxes_by_page_point
                if x0 <= (r[0] + r[2]) / 2 <= x1 and y0 <= (r[1] + r[3]) / 2 <= y1]

    _fake_detector(monkeypatch, per_cell)
    rep = S.prefill_detector(page, mcells, regions, "weights.pt")
    return page, rep


TITLE_HEAD = ("noteheadBlackInSpace", (1000.0, 90.0, 1040.0, 130.0))      # the S of SYMPHONY
PAGE_NUMBER_HEAD = ("noteheadBlackOnLine", (1180.0, 1700.0, 1210.0, 1730.0))
REAL_HEAD = ("noteheadBlackInSpace", (487.0, 330.0, 513.0, 350.0))        # on staff 0


def test_a_title_letter_read_as_a_notehead_is_never_queued_RED(cut, monkeypatch):
    page, rep = _prefill(cut, monkeypatch, [TITLE_HEAD, PAGE_NUMBER_HEAD, REAL_HEAD])
    assert rep["refused_off_staff"] == 2 and rep["boxes_queued"] == 1
    assert rep["refused_off_staff_by_cell_kind"] == {"top": 1, "bottom": 1}
    assert [q.cls for q in page.queue] == ["noteheadBlackInSpace"]
    assert page.queue[0].rect[1] > 300, "only the head standing on the staff is offered"


def test_CONTROL_a_real_head_on_a_ledger_line_in_the_pad_is_still_queued(cut, monkeypatch):
    page, _, _ = cut
    bands = S.page_staff_bands(page)
    top = min(b[2] for b in bands)
    five_above = ("noteheadBlackInSpace", (487.0, top - 5 * SP_PAGE - 10, 513.0, top - 5 * SP_PAGE + 10))
    page, rep = _prefill(cut, monkeypatch, [five_above])
    assert rep["refused_off_staff"] == 0 and rep["boxes_queued"] == 1


def test_CONTROL_a_title_flag_or_beam_is_not_this_rules_to_refuse(cut, monkeypatch):
    """Only pitch-bearing classes are measured; a stray text-ink beam/stem is left
    for Sean to reject as before (the rule never widens past what it measured)."""
    page, rep = _prefill(cut, monkeypatch, [("beam", TITLE_HEAD[1]), ("flag8thUp", TITLE_HEAD[1])])
    assert rep["refused_off_staff"] == 0 and rep["boxes_queued"] == 2


def test_the_staff_bands_come_from_the_cells_alone(cut):
    page, _, _ = cut
    bands = S.page_staff_bands(page)
    assert len(bands) == 6
    for x0, x1, top, bot, sp in bands:
        assert sp == pytest.approx(SP_PAGE, rel=0.05) and bot - top == pytest.approx(4 * sp)
        assert x0 <= 500 and x1 >= 2100


def test_prune_off_staff_never_touches_truth_or_sean_old_labels(cut):
    page, _, _ = cut
    page = store.PageTruth.from_json(__import__("json").loads(__import__("json").dumps(page.to_json())))
    page.propose(TITLE_HEAD[0], TITLE_HEAD[1], source="detector:w.pt", score=0.9)
    page.propose(PAGE_NUMBER_HEAD[0], PAGE_NUMBER_HEAD[1], source="sean-v12", score=None)   # his own label
    page.propose(*REAL_HEAD, source="detector:w.pt", score=0.9)
    cell = next(c for c in page.cells if c.kind == "top")
    page.draw(cell.id, "noteheadBlack", (10, 10, 40, 40))        # a truth box on the title (Sean drew it)
    n_truth = len(page.boxes)
    dry = S.prune_off_staff(page)
    assert dry["off_staff"] == 1 and not dry["applied"] and len(page.queue) == 3
    done = S.prune_off_staff(page, apply=True)
    assert done["off_staff"] == 1
    assert [q.source for q in page.queue] == ["sean-v12", "detector:w.pt"]
    assert len(page.boxes) == n_truth
    assert S.prune_off_staff(page, apply=True)["off_staff"] == 0     # idempotent


if __name__ == "__main__":
    unittest.main()
