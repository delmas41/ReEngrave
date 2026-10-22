"""lane-owner-from-staves (Sean, 2026-10-06): ownership STARTS FROM THE STAVES WE KNOW.

A notehead lying ON or BETWEEN a known staff's five lines -- measured LOCALLY, centre within the band from the top
line to the bottom line plus half a line thickness -- belongs to that staff: decided, no contest. A box of the same
head found by a NEIGHBOUR's padded cell is a duplicate (the owning staff has its own box) or is named
`staff_band_no_box` (it has none; no box is invented). Only a head in the GAP is left to the ledger witness and the
older tiers. Behind `OMR_OWNER_FROM_STAVES`, default ON since 2026-10-06 (Sean).

RUN RED FIRST against the unrepaired tree (no tier, no flag): every `staff_band` assertion fails there.

Each positive case has a negative control differing in one fixture value, so none passes by the tier firing on
everything: the gap head, the page-wide edge head, the twin whose LOCAL position is outside, and the flag OFF.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401 -- registers decisions
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q

SP = 20.0
LINES_A = [200.0 + SP * i for i in range(5)]      # 200..280
LINES_B = [380.0 + SP * i for i in range(5)]      # 380..460 ; the gap is 100 px = 5 spaces
A_KEY, B_KEY = R.staff(0, 0, 0).to_key(), R.staff(0, 0, 1).to_key()
ENV = "OMR_OWNER_FROM_STAVES"


def _box(cy, h=16.0, x0=300.0, w=24.0):
    return (x0, cy - h / 2.0, x0 + w, cy + h / 2.0)


def _log(cy, *, twin=True, twin_pos=None, local_b=None, own_pos=None, own_cy=None, extra=None):
    """A head filed on staff A (cell 0) whose centre is at page y `cy`. `twin`: B's own cell holds the same ink with
    local position `twin_pos` (half-steps from B's top line). `local_b`: GATHER's `local_position_in_candidate`
    for B on the head's band row. `own_pos`: the head's own local position against A (default: from A's lines)."""
    log = Log()
    for key, lines in ((A_KEY, LINES_A), (B_KEY, LINES_B)):
        s = R.Subject.from_key(key)
        log.observe(s, Q.STAFF_LINES, list(lines), reader="geometry", frame="page")
        log.observe(s, Q.STAFF_SPACING, SP, reader="geometry", frame="page")
        log.observe(s, Q.STAFF_EXTENT, (40.0, 900.0), reader="geometry", frame="page")
        log.observe(s, Q.STAFF_SKEW, 1.0, reader="geometry", frame="page", thickness_px=[2.0] * 5)
    g = R.glyph(0, 0, 0, 0, 0)
    bb = _box(cy)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", 0, 0, 24, 16), reader="detector", frame="cell:0",
                score=0.9, category="notehead", bbox_page_px=list(bb), x_center_page=312.0, y_center_page=cy)
    pos = own_pos if own_pos is not None else (cy - LINES_A[0]) / (SP / 2.0)
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, pos, reader="geometry", frame="cell:0",
                residual=0.0, rounded=int(round(pos)))
    for key, lines, own in ((A_KEY, LINES_A, True), (B_KEY, LINES_B, False)):
        top, bot = min(lines), max(lines)
        dist = 0.0 if top <= cy <= bot else ((top - cy) if cy < top else (cy - bot)) / SP
        det = dict(candidate=key, own=own, position_in_candidate=(cy - top) / (SP / 2.0))
        if key == B_KEY and local_b is not None:
            det["local_position_in_candidate"] = local_b
        log.observe(g, Q.GLYPH_BAND_DISTANCE, dist, reader="geometry", frame="page", **det)
    if twin:
        t = R.glyph(0, 0, 1, 0, 0)
        log.observe(t, Q.GLYPH_BOX, ("noteheadBlackOnLine", 0, 0, 24, 16), reader="detector", frame="cell:0",
                    score=0.9, category="notehead", bbox_page_px=list(bb), x_center_page=312.0, y_center_page=cy)
        tp = twin_pos if twin_pos is not None else (cy - LINES_B[0]) / (SP / 2.0)
        log.observe(t, Q.NOTEHEAD_STAFF_POSITION, tp, reader="geometry", frame="cell:0",
                    residual=0.0, rounded=int(round(tp)))
    for fn in (extra or ()):
        fn(log, g)
    log.freeze()
    return log, g


class _V:
    def __init__(self, outcome, value, reason, detail):
        self.outcome, self.value, self.reason, self.detail = outcome, value, reason, detail


def _decide(log, g, *, on=True):
    env = {ENV: "1"} if on else {ENV: "0"}   # default ON since 2026-10-06: OFF must be explicit
    with mock.patch.dict(os.environ, env):
        spec = adjudicate.REGISTRY[Q.GLYPH_OWNER]
        # the decision body on its declared evidence, as `adjudicate_one` runs it (a second arm on one log would be
        # refused as a second adjudication)
        r = spec.fn(adjudicate.Evidence(log, g, spec))
        assert r.reason in spec.reasons, r.reason
        return _V(Outcome.DECIDED if r.value is not None else Outcome.ABSTAINED, r.value, r.reason, r.detail)


class TestTheDeclaration(unittest.TestCase):
    def test_reasons_and_inputs_are_declared(self):
        spec = adjudicate.REGISTRY[Q.GLYPH_OWNER]
        for r in ("staff_band", "staff_band_no_box"):
            self.assertIn(r, spec.reasons)
        for q in (Q.STAFF_EXTENT, Q.STAFF_SKEW, Q.GLYPH_BOX, Q.NOTEHEAD_STAFF_POSITION):
            self.assertIn(q, spec.wants)


class TestAHeadInAnotherStaffsBand(unittest.TestCase):
    CY = 420.0          # the middle line of B, filed on A (cell cut with a 4-space pad)

    def test_it_belongs_to_the_staff_it_lies_in_and_the_copy_is_a_duplicate(self):
        log, g = _log(self.CY)
        v = _decide(log, g)
        self.assertEqual((v.outcome, v.value, v.reason), (Outcome.DECIDED, B_KEY, "staff_band"))
        self.assertEqual(v.detail["owner_box"], R.glyph(0, 0, 1, 0, 0).to_key())
        self.assertEqual(v.detail["measured"], "local_twin_cell")

    def test_without_a_box_on_the_owning_staff_it_is_named_and_none_is_invented(self):
        log, g = _log(self.CY, twin=False)          # 420 is 1.75 sp inside B by the page lines
        v = _decide(log, g)
        self.assertEqual((v.outcome, v.value, v.reason), (Outcome.DECIDED, B_KEY, "staff_band_no_box"))
        self.assertIsNone(v.detail["owner_box"])
        self.assertEqual(v.detail["measured"], "page_wide_margin")
        # no box is invented: the log gained no glyph on staff B
        self.assertEqual(log.rows(Q.GLYPH_BOX, R.glyph(0, 0, 1, 0, 0)), ())

    def test_the_flag_off_is_the_old_behaviour(self):
        """The control that can fail: the arm moves nothing when OFF."""
        log, g = _log(self.CY)
        v = _decide(log, g, on=False)
        self.assertNotIn(v.reason, ("staff_band", "staff_band_no_box"))

    def test_it_goes_ahead_of_the_ledger_witness(self):
        """A note-first reading that fits ONLY staff A must not outvote the staff the head lies in."""
        def witness_for_a(log, g):
            log.observe(g, Q.FAR_HEAD_OWNER_LEDGER, 12, reader="ledger_owner_note_first", frame="cell:0",
                        candidate=A_KEY, ledger_reason="x", how="note_first")
        log, g = _log(self.CY, extra=[witness_for_a])
        self.assertEqual(_decide(log, g, on=False).reason, "ledger_note_first")      # the older tier says A
        v = _decide(log, g, on=True)
        self.assertEqual((v.value, v.reason), (B_KEY, "staff_band"))


class TestTheGapStaysContested(unittest.TestCase):
    def test_a_head_between_two_staves_is_not_decided_by_this_tier(self):
        log, g = _log(330.0, twin=False)             # 2.5 sp below A's last line, 2.5 sp above B's first
        v = _decide(log, g)
        self.assertNotIn(v.reason, ("staff_band", "staff_band_no_box"))

    def test_the_first_space_outside_a_staff_is_not_inside_it(self):
        log, g = _log(290.0, twin=False)             # in A's first space below its last line: outside the band
        v = _decide(log, g)
        self.assertNotIn(v.reason, ("staff_band", "staff_band_no_box"))


class TestMeasuredLocally(unittest.TestCase):
    def test_a_page_wide_edge_reading_is_silent_without_a_local_one(self):
        log, g = _log(386.0, twin=False)             # 0.3 sp inside B's top line by the page-wide lines
        v = _decide(log, g)
        self.assertNotIn(v.reason, ("staff_band", "staff_band_no_box"))

    def test_gathers_local_position_settles_the_edge_inside(self):
        log, g = _log(386.0, twin=False, local_b=0.5)        # B's own cell grid: 0.5 half-steps under its top line
        v = _decide(log, g)
        self.assertEqual((v.value, v.reason), (B_KEY, "staff_band_no_box"))
        self.assertEqual(v.detail["measured"], "local_candidate_grid")

    def test_gathers_local_position_settles_the_edge_outside(self):
        log, g = _log(386.0, twin=False, local_b=-1.0)       # the local grid puts it ABOVE B's top line
        v = _decide(log, g)
        self.assertNotIn(v.reason, ("staff_band", "staff_band_no_box"))

    def test_the_twins_local_position_beats_the_page_wide_lines(self):
        """420 is inside B by the page-wide lines (1.75 sp), but B's own cell says the ink is 1.5 half-steps ABOVE its
        top line: the local grid wins, and the head is not B's."""
        log, g = _log(420.0, twin=True, twin_pos=-1.5)
        v = _decide(log, g)
        self.assertNotIn(v.reason, ("staff_band", "staff_band_no_box"))

    def test_half_a_line_thickness_counts_as_inside(self):
        log, g = _log(386.0, twin=True, twin_pos=-0.05)      # 0.05 half-steps over the line; thickness 2 px = 0.2
        self.assertEqual(_decide(log, g).reason, "staff_band")
        log, g = _log(386.0, twin=True, twin_pos=-0.5)       # 0.5 over: outside
        self.assertNotEqual(_decide(log, g).reason, "staff_band")


class TestAHeadOnItsOwnStaff(unittest.TestCase):
    def test_a_head_inside_its_own_band_is_its_own_staffs(self):
        log, g = _log(240.0, twin=False)
        v = _decide(log, g)
        self.assertEqual((v.outcome, v.value, v.reason), (Outcome.DECIDED, A_KEY, "staff_band"))
        self.assertEqual(v.detail["measured"], "local_own_cell")


# ------------------------------------------------------------------- the gather
class _Det:
    def __init__(self, name, x, y, w, h):
        self.smufl_name, self.category, self.confidence = name, "notehead", 0.8
        self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical = x, y, w, h


class _Staff:
    def __init__(self, i, ys):
        self.staff_index, self.line_ys, self.x_start, self.x_end = i, ys, 40.0, 900.0


class _Cell:
    def __init__(self, i, local_ys):
        self.page_index, self.staff_index, self.measure_index = 0, i, 0
        self.bbox_page_px = [0.0, 0.0, 2000.0, 2000.0]
        self.upscale_factor = 1.0
        self.staff_line_ys_canonical = list(local_ys)


class _P:
    page_index = 0


class _PWS:
    def __init__(self, staves):
        self.staves, self.page = staves, _P()


def _gather(cy, *, on, with_twin):
    log = Log()
    staves = [_Staff(0, LINES_A), _Staff(1, LINES_B)]
    # staff B's own cell grid is 6 px LOWER than its page-wide fit (a tilted scan)
    cells = [_Cell(0, LINES_A), _Cell(1, [y + 6.0 for y in LINES_B])]
    dets = {R.cell(0, 0, 0, 0).to_key(): [_Det("noteheadBlackOnLine", 300.0, cy - 8.0, 24.0, 16.0)]}
    if with_twin:
        dets[R.cell(0, 0, 1, 0).to_key()] = [_Det("noteheadBlackOnLine", 300.0, cy - 8.0, 24.0, 16.0)]
    env = {ENV: "1"} if on else {ENV: "0"}   # default ON since 2026-10-06: OFF must be explicit
    with mock.patch.dict(os.environ, env):
        G.gather_ownership_evidence(log, _PWS(staves), cells, {0: (0, 0), 1: (0, 1)}, dets)
    return [r for r in log.all_rows() if getattr(r, "quantity", None) == Q.GLYPH_BAND_DISTANCE]


class TestTheGather(unittest.TestCase):
    def test_off_files_no_local_position_and_no_extra_candidate(self):
        rows = _gather(420.0, on=False, with_twin=False)
        self.assertEqual({r.detail["candidate"] for r in rows}, {A_KEY})
        self.assertTrue(all("local_position_in_candidate" not in r.detail for r in rows))

    def test_on_names_the_staff_the_head_lies_in_as_a_candidate_with_its_local_position(self):
        rows = _gather(420.0, on=True, with_twin=False)
        by = {r.detail["candidate"]: r for r in rows}
        self.assertEqual(set(by), {A_KEY, B_KEY})
        # B's local grid starts 6 px lower than its page-wide top line: 420 is (420-386)/10 = 3.4 half-steps in
        self.assertAlmostEqual(by[B_KEY].detail["local_position_in_candidate"], 3.4, places=6)
        self.assertAlmostEqual(by[B_KEY].detail["position_in_candidate"], 4.0, places=6)    # the page-wide fit

    def test_a_head_in_the_gap_adds_no_candidate(self):
        """The negative control: 330 is 2.5 sp from either staff -- beyond the page-wide margin."""
        rows = _gather(330.0, on=True, with_twin=False)
        self.assertEqual({r.detail["candidate"] for r in rows}, {A_KEY})


if __name__ == "__main__":
    unittest.main()
