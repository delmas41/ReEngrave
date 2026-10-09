"""ROADMAP 2.68 (Sean, DECISIONS 2026-10-08 and 2026-10-09): *"It sits below the
staff it belongs to."* A dynamic belongs to the staff it is printed BELOW; a
dynamic in the gap between two staves of a system is the UPPER staff's, and
distance or an instrument range never moves it to the staff beneath.

Measured on the small re-gather (main 404285f3): 43 of 213 kept letters on
Litolff and 23 of 94 on Brahms stood in the zone of the staff above their cell,
and `Q.GLYPH_OWNER` gave them to the staff below by `distance` (tile 1: 3.29 vs
3.02 spaces), `range_veto` (tile 5) or `tied`; the 2.27c band rule that should
have moved the rest read `Q.DYNAMIC_BAND_POSITION`, which is gathered only under
an OFF flag (zero rows on the record).

The input is the letter's own position against its neighbours' staves, measured
LOCALLY (each staff's cell grid at the letter's x, CLAUDE.md §10) and filed on
the letter row by GATHER: `local_position_in_staves`, half-steps from each
staff's TOP line, keyed by the staff's offset from the cell's own (-1, 0, +1).

Each refusal sits beside the case it must leave alone (rule 7): a letter inside
the lower staff's lines stays the lower staff's, a letter under a system's last
staff stays that staff's, a letter above a system's first staff is left to the
old chain, a record with no local positions behaves as before.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q, READERS

UPPER = R.staff(0, 0, 0)
LOWER = R.staff(0, 0, 1)
CELL_U = R.cell(0, 0, 0, 0)
CELL_L = R.cell(0, 0, 1, 0)

BELOW_UPPER = 11.0      # half-steps from UPPER's top line: 3 steps below its bottom line (8)
ABOVE_LOWER = -3.0      # 1.5 spaces above LOWER's top line


def _letter(log, glyph, letter, *, positions, x0=100.0, x1=110.0, y=100.0):
    return log.observe(
        glyph, Q.DYNAMIC_LETTER, "dynamic" + letter.upper(),
        reader=READERS.DETECTOR, frame=G.FRAME_PAGE, score=0.8,
        letter=letter, cell_frame="cell:0",
        bbox_page_px=[x0, y - 5.0, x1, y + 5.0],
        x_center_page=(x0 + x1) / 2.0, y_center_page=y,
        staff_bottom_line_page=90.0, staff_spacing_px=10.0,
        band_offset_spaces=(y - 90.0) / 10.0, in_hairpin_band=True,
        **({} if positions is None else {"local_position_in_staves": positions}))


def _contest(log, glyph, *, winner, loser, near=1.0, far=4.0):
    """A real cross-staff contest, so `Q.GLYPH_OWNER` is decided by the real
    adjudicator (a stub would test this file's own fixture)."""
    log.observe(glyph, Q.GLYPH_BAND_DISTANCE, far, reader=READERS.GEOMETRY,
                frame=G.FRAME_PAGE, candidate=loser.to_key(), own=True,
                position_in_candidate=2.0)
    log.observe(glyph, Q.GLYPH_BAND_DISTANCE, near, reader=READERS.GEOMETRY,
                frame=G.FRAME_PAGE, candidate=winner.to_key(), own=False,
                position_in_candidate=2.0)


def _twins(positions_upper, positions_lower, *, owner_by_contest=LOWER, tied=False):
    """ONE printed letter detected in both cells (UPPER's pad reaches down into
    the gap, LOWER's reaches up), contested, with the contest's winner named."""
    log = Log()
    g_u, g_l = R.glyph(0, 0, 0, 0, 0), R.glyph(0, 0, 1, 0, 0)
    _letter(log, g_u, "p", positions=positions_upper)
    _letter(log, g_l, "p", positions=positions_lower)
    loser = UPPER if owner_by_contest == LOWER else LOWER
    near, far = (2.0, 2.0) if tied else (1.0, 4.0)
    _contest(log, g_u, winner=owner_by_contest, loser=loser, near=near, far=far)
    _contest(log, g_l, winner=owner_by_contest, loser=loser, near=near, far=far)
    return log


def _run(log):
    log.freeze()
    adjudicate.run(log)
    return log


GAP_U = {"0": BELOW_UPPER, "1": ABOVE_LOWER}     # as UPPER's cell sees the letter
GAP_L = {"-1": BELOW_UPPER, "0": ABOVE_LOWER}    # as LOWER's cell sees the SAME ink


class TestADynamicBelongsToTheStaffItIsPrintedBelow(unittest.TestCase):

    def test_a_letter_in_the_gap_that_distance_gave_to_the_lower_staff_is_the_uppers(self):
        """Tile 1 (Litolff): the contest by `distance` said LOWER (3.29 vs 3.02
        spaces). RED before: LOWER wrote it, UPPER lost it."""
        log = _run(_twins(GAP_U, GAP_L, owner_by_contest=LOWER))
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, R.glyph(0, 0, 0, 0, 0)).value,
                         LOWER.to_key(), "the premise: the contest DOES say LOWER")
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_U).value, ["p"])
        lost = log.verdict(Q.DYNAMIC, CELL_L)
        self.assertEqual(lost.value, [])
        self.assertEqual(lost.reason, "owned_elsewhere")

    def test_a_tied_contest_does_not_write_it_on_both_staves(self):
        """Tile 3 shape: the owner ABSTAINED `tied`; the old chain then kept the
        letter on each cell it was cut from, so it was written twice (and the
        lower copy was the leak). RED before."""
        log = _run(_twins(GAP_U, GAP_L, tied=True))
        self.assertIsNone(log.verdict(Q.GLYPH_OWNER, R.glyph(0, 0, 0, 0, 0)).value)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_U).value, ["p"])
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_L).value, [])

    def test_a_letter_seen_only_from_the_lower_cell_is_still_the_uppers(self):
        """No twin on UPPER's cell (the dedupe or the pad never re-detected it),
        no contest, no band row (that quantity is gathered only under an OFF
        flag): the leak the 2.27c rule could not reach. It MOVES to UPPER, it is
        not dropped as UPPER's 'duplicate'. RED before."""
        log = Log()
        g = R.glyph(0, 0, 1, 0, 0)
        _letter(log, g, "f", positions=GAP_L)
        log.abstain(CELL_U, Q.DYNAMIC_LETTER, reader=READERS.DETECTOR, frame="cell:0",
                    reason=ABSTAIN.NO_GLYPH_OF_THIS_KIND)
        _run(log)
        self.assertIsNone(log.verdict(Q.GLYPH_OWNER, g))
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_U).value, ["f"])
        moved = log.verdict(Q.DYNAMIC, CELL_L)
        self.assertEqual(moved.value, [])
        self.assertEqual(moved.detail["letters_moved_out"], 1)

    def test_a_letter_seen_only_from_the_upper_cell_stays_the_uppers(self):
        log = Log()
        _letter(log, R.glyph(0, 0, 0, 0, 0), "f", positions=GAP_U)
        log.abstain(CELL_L, Q.DYNAMIC_LETTER, reader=READERS.DETECTOR, frame="cell:0",
                    reason=ABSTAIN.NO_GLYPH_OF_THIS_KIND)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_U).value, ["f"])
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_L).value, [])

    def test_the_counts_say_which_rule_decided(self):
        log = _run(_twins(GAP_U, GAP_L))
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_U).detail["letters_placed_below_their_staff"], 1)


class TestWhatTheRuleMustLeaveAlone(unittest.TestCase):

    def test_CONTROL_a_letter_inside_the_lower_staffs_lines_stays_the_lowers(self):
        """The mirror, in the same class: ink INSIDE the lower staff's five
        lines is that staff's, even where the contest says UPPER."""
        inside = 4.0                                      # the middle line of LOWER
        log = _run(_twins({"0": 14.0, "1": inside}, {"-1": 14.0, "0": inside},
                          owner_by_contest=UPPER))
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, R.glyph(0, 0, 0, 0, 0)).value,
                         UPPER.to_key(), "the premise: the contest says UPPER")
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_L).value, ["p"])
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_U).value, [])

    def test_CONTROL_a_letter_under_the_systems_last_staff_stays_that_staffs(self):
        log = Log()
        _letter(log, R.glyph(0, 0, 1, 0, 0), "p", positions={"-1": 22.0, "0": 11.0})
        log.abstain(CELL_U, Q.DYNAMIC_LETTER, reader=READERS.DETECTOR, frame="cell:0",
                    reason=ABSTAIN.NO_GLYPH_OF_THIS_KIND)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_L).value, ["p"])

    def test_CONTROL_a_letter_above_the_systems_first_staff_is_left_to_the_old_chain(self):
        """Nothing above it in this system to belong to: CANNOT TELL (rule 8), so
        it stays where it was cut."""
        log = Log()
        _letter(log, R.glyph(0, 0, 0, 0, 0), "p", positions={"0": -4.0})
        _run(log)
        v = log.verdict(Q.DYNAMIC, CELL_U)
        self.assertEqual(v.value, ["p"])
        self.assertEqual(v.detail["letters_placed_below_their_staff"], 0)

    def test_CONTROL_a_record_without_local_positions_behaves_as_before(self):
        """The rule is not universal (a rule that fires on everything passes any
        test by refusing everything): with no positions the contest decides."""
        log = _run(_twins(None, None, owner_by_contest=LOWER))
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_L).value, ["p"])
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_U).value, [])

    def test_CONTROL_a_neighbour_that_was_not_measured_does_not_decide(self):
        """The letter is above its own cell's top line but the staff above has
        no cell at its x (no `-1` key): CANNOT TELL, the old chain stands."""
        log = Log()
        _letter(log, R.glyph(0, 0, 1, 0, 0), "p", positions={"0": ABOVE_LOWER})
        log.abstain(CELL_U, Q.DYNAMIC_LETTER, reader=READERS.DETECTOR, frame="cell:0",
                    reason=ABSTAIN.NO_GLYPH_OF_THIS_KIND)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_L).value, ["p"])
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_U).value, [])

    def test_CONTROL_two_letters_of_one_word_both_follow_the_rule(self):
        """`ff` under the upper staff, cut from LOWER's cell: one word, written once."""
        log = Log()
        _letter(log, R.glyph(0, 0, 1, 0, 0), "f", positions=GAP_L, x0=100.0, x1=110.0)
        _letter(log, R.glyph(0, 0, 1, 0, 1), "f", positions=GAP_L, x0=112.0, x1=122.0)
        log.abstain(CELL_U, Q.DYNAMIC_LETTER, reader=READERS.DETECTOR, frame="cell:0",
                    reason=ABSTAIN.NO_GLYPH_OF_THIS_KIND)
        _run(log)
        self.assertEqual(log.verdict(Q.DYNAMIC, CELL_U).value, ["ff"])


class TestADynamicWordFollowsTheSameRule(unittest.TestCase):
    """`cresc.` / `dim.`: a word in the gap is the UPPER staff's (the band that
    finds it is the upper staff's whole gap). Only TEMPO and TECHNIQUE words,
    printed ABOVE their staff, move to the staff beneath -- untouched here."""

    def _gap(self, category, terms, text):
        from tools.omr import direction_text as DT
        from tools.omr.tests.test_direction_word_boxes_2026_10_08 import _two_staff_reading
        pws, page_dict, cands, accepted = _two_staff_reading(category, terms, text)
        DT._give_tempo_to_the_staff_below(pws, page_dict, cands, accepted)
        return accepted[0]

    def test_a_crescendo_word_in_the_gap_is_the_upper_staffs(self):
        d = self._gap("dynamic", ("cresc",), "cresc.")
        self.assertEqual((d.staff_index, d.placement), (0, "below"))

    def test_CONTROL_a_tempo_word_in_the_same_gap_is_still_the_lower_staffs(self):
        d = self._gap("tempo", ("adagio",), "Adagio.")
        self.assertEqual((d.staff_index, d.placement), (1, "above"))

    def test_CONTROL_a_technique_word_in_the_same_gap_is_still_the_lower_staffs(self):
        d = self._gap("expression", ("pizz",), "pizz.")
        self.assertEqual((d.staff_index, d.placement), (1, "above"))


# ── GATHER: the position is measured against each staff's OWN cell grid ─────

PAGE_W, PAGE_H = 3000, 1000


class _Det:
    def __init__(self, name, x, y, w, h, origin_y):
        self.smufl_name, self.category = name, "dynamic"
        self.x_canonical, self.y_canonical = x, y - origin_y
        self.width_canonical, self.height_canonical = w, h
        self.confidence = 0.8
        self.x_center, self.y_center = x + w / 2, y + h / 2


def _gather_one(local_shift_lower=0.0, letter_page_y=650.0, with_upper_cell=True):
    """Two staves of one system (spacing 20 px). UPPER's lines y 400..480, LOWER's
    page-wide lines y 700..780; LOWER's CELL grid (the local one) is shifted by
    `local_shift_lower` px. A `p` is detected in LOWER's cell at `letter_page_y`."""
    up = SimpleNamespace(staff_index=0, system_index=0, line_ys=[400, 420, 440, 460, 480],
                         top_y=400, bottom_y=480, x_start=0, x_end=PAGE_W,
                         line_thickness_px=None, line_wander_px=None)
    lo = SimpleNamespace(staff_index=1, system_index=0, line_ys=[700, 720, 740, 760, 780],
                         top_y=700, bottom_y=780, x_start=0, x_end=PAGE_W,
                         line_thickness_px=None, line_wander_px=None)
    pws = SimpleNamespace(page=SimpleNamespace(page_index=0, binary=None,
                                               rgb=np.full((PAGE_H, PAGE_W, 3), 255, np.uint8)),
                          staves=[up, lo])
    cu = SimpleNamespace(staff_index=0, page_index=0, measure_index=0,
                         bbox_page_px=[0.0, 300.0, float(PAGE_W), 600.0], upscale_factor=1.0,
                         image_no_staff=None,
                         staff_line_ys_canonical=[100.0, 120.0, 140.0, 160.0, 180.0])
    cl = SimpleNamespace(staff_index=1, page_index=0, measure_index=0,
                         bbox_page_px=[0.0, 600.0, float(PAGE_W), 900.0], upscale_factor=1.0,
                         image_no_staff=None,
                         staff_line_ys_canonical=[100.0 + local_shift_lower + 20.0 * i for i in range(5)])
    det = _Det("dynamicP", 1000, letter_page_y - 10, 12, 20, origin_y=600.0)
    log = Log()
    G.gather_dynamic_letters(log, pws, [cu, cl] if with_upper_cell else [cl],
                             {0: (0, 0), 1: (0, 1)}, {R.cell(0, 0, 1, 0).to_key(): [det]})
    rows = log.rows(Q.DYNAMIC_LETTER, R.cell(0, 0, 1, 0), scope=R.Scope.SELF_AND_DESCENDANTS)
    return [r for r in rows if isinstance(r, R.Observation)][0]


class TestGatherMeasuresEachStaffLocally(unittest.TestCase):

    def test_the_letter_row_carries_its_position_against_its_own_and_the_staff_above(self):
        row = _gather_one()
        pos = row.detail["local_position_in_staves"]
        # centre y 650: LOWER's top line 700 -> (650-700)/10 half-steps; UPPER's top 400 -> 25
        self.assertAlmostEqual(pos["0"], -5.0, places=6)
        self.assertAlmostEqual(pos["-1"], 25.0, places=6)
        self.assertNotIn("1", pos, "no staff below LOWER in this system")

    def test_the_position_is_the_CELL_grid_not_the_page_wide_lines(self):
        """The control that can fail: LOWER's cell grid is 6 px lower than its
        page-wide lines (a tilted scan); the position must follow the cell."""
        flat, tilted = _gather_one(0.0), _gather_one(6.0)
        a, b = flat.detail["local_position_in_staves"]["0"], tilted.detail["local_position_in_staves"]["0"]
        self.assertAlmostEqual(a - b, 0.6, places=6)

    def test_a_staff_with_no_cell_at_the_letters_x_is_left_out_not_defaulted(self):
        pos = _gather_one(with_upper_cell=False).detail["local_position_in_staves"]
        self.assertIn("0", pos)
        self.assertNotIn("-1", pos)


if __name__ == "__main__":
    unittest.main()
