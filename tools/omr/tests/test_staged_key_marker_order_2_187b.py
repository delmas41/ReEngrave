"""ROADMAP 2.187b: the key MARKER RUN (the key a staff's header prints) keeps only markers that stand in the fixed order at their clef's steps.

CAUSE (lane 2.197's census, via the coordinator): `gather._gather_keysig_markers` reads the whole first MEASURE, so an in-bar natural or sharp just
after the signature joins the run and the key abstains `mixed_marker_kinds` (13 of 131 Brahms staves on pages 0-3; INFER then fills it, only as a
guess). Sean 2026-10-22: slot k holds only the k-th accidental of the fixed order, at a fixed step for the clef. POSITION decides; the detector's
key*/accidental* label is not consulted. Every test has a twin that must not fire.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from tools.omr.staged import key_object as KO
from tools.omr.staged.adjudicators import header as H

SP = 20.0                      # staff space in the cell frame
PITCH_X = 24.0
FLAT_OFF = KO.ANCHOR_OFFSET_STEPS["flat"]


def marker(kind, slot_x, step, **kw):
    return SimpleNamespace(value=kind, detail=dict(x=slot_x, y_center=0.0, step=step, **kw), frame="cell:0", id="m%s_%s" % (kind, slot_x))


def flat_run(clef, n, x0=100.0):
    return [marker("keyFlat", x0 + PITCH_X * i, KO.expected_step(clef, "b", i + 1) - FLAT_OFF) for i in range(n)]


def sharp_run(clef, n, x0=100.0):
    return [marker("keySharp", x0 + PITCH_X * i, KO.expected_step(clef, "#", i + 1)) for i in range(n)]


class TestInBarAccidentalsAreNotTheRun(unittest.TestCase):
    def test_a_natural_after_three_flats_no_longer_makes_the_key_abstain(self):
        for clef in ("treble", "bass", "alto"):
            marks = flat_run(clef, 3) + [marker("keyNatural", 100.0 + PITCH_X * 3.2, 5.0)]
            self.assertEqual(H._marker_run(marks, SP)[1], "mixed_marker_kinds", clef)          # without the clef: today's abstention (the cause)
            fifths, reason, detail = H._marker_run(marks, SP, clef)
            self.assertEqual((fifths, reason), (-3, "markers"), clef)
            self.assertEqual(detail["keysig_markers_off_the_fixed_order"], 1, clef)

    def test_TWIN_a_fourth_FLAT_at_its_own_step_is_the_signature_not_an_in_bar_mark(self):
        for clef in ("treble", "bass", "alto"):
            marks = flat_run(clef, 4)
            self.assertEqual(H._marker_run(marks, SP, clef)[:2], (-4, "markers"), clef)

    def test_a_run_of_ONE_kind_is_never_shortened_even_where_a_marker_is_off_its_step(self):
        # a crushed plate's boxes are not tight enough to cut a correct run (Litolff: 3 read as 1): only a MIXED run is judged
        for clef in ("treble", "bass", "alto"):
            marks = flat_run(clef, 3) + [marker("keyFlat", 100.0 + PITCH_X * 3, KO.expected_step(clef, "b", 4) - FLAT_OFF + 3.0)]
            self.assertEqual(H._marker_run(marks, SP, clef)[:2], (-4, "markers"), clef)               # today's reading, unchanged
            marks = flat_run(clef, 3)
            marks[1].detail["step"] += 3.0
            self.assertEqual(H._marker_run(marks, SP, clef)[:2], (-3, "markers"), clef)

    def test_a_sharp_after_flats_off_the_orders_step_is_excluded(self):
        for clef in ("treble", "bass", "alto"):
            marks = flat_run(clef, 2) + [marker("keySharp", 100.0 + PITCH_X * 2.1, KO.expected_step(clef, "#", 3) + 3.0)]
            self.assertEqual(H._marker_run(marks, SP, clef)[:2], (-2, "markers"), clef)

    def test_TWIN_the_same_sharp_in_a_run_of_flats_AT_a_sharp_slots_step_is_still_refused_as_mixed_kinds(self):
        # a sharp that stands exactly where slot 3's SHARP would be is still not a flat run's third accidental: the kinds disagree and
        # the flats win only because they came first; a run that STARTS with a sharp is a sharp run (next test)
        clef = "treble"
        marks = flat_run(clef, 2) + [marker("keySharp", 100.0 + PITCH_X * 2, KO.expected_step(clef, "#", 3))]
        fifths, reason, _ = H._marker_run(marks, SP, clef)
        self.assertEqual((fifths, reason), (-2, "markers"))

    def test_two_sharps_then_an_in_bar_natural_read_two_sharps(self):
        for clef in ("treble", "bass", "alto"):
            marks = sharp_run(clef, 2) + [marker("keyNatural", 100.0 + PITCH_X * 2.5, 2.0)]
            self.assertEqual(H._marker_run(marks, SP, clef)[:2], (2, "markers"), clef)
            self.assertEqual(H._marker_run(sharp_run(clef, 2), SP, clef)[:2], (2, "markers"), clef)        # TWIN: without the stray, the same

    def test_in_a_mixed_run_the_prefix_ends_at_the_first_slot_off_its_step(self):
        # three flats, the SECOND 3 steps off, then an in-bar natural: the run is the first flat; the off-step flat and the natural are not members
        marks = flat_run("treble", 3) + [marker("keyNatural", 172.0, 5.0)]
        marks[1].detail["step"] += 3.0
        fifths, reason, detail = H._marker_run(marks, SP, "treble")
        self.assertEqual((fifths, reason), (-1, "markers"))
        self.assertEqual(detail["keysig_markers_off_the_fixed_order"], 3)
        marks = flat_run("treble", 3) + [marker("keyNatural", 172.0, 5.0)]                          # TWIN: the same run, the flat ON its step
        self.assertEqual(H._marker_run(marks, SP, "treble")[:2], (-3, "markers"))

    def test_a_mixed_run_whose_flat_is_off_its_step_inside_the_run_is_not_judged(self):
        # an excluded marker LEFT of a kept one is no in-bar accidental: nothing is judged, the run stays mixed as today
        marks = flat_run("treble", 3) + [marker("keyNatural", 172.0, 5.0)]
        marks[0].detail["step"] += 3.0
        marks[1].detail["step"] += 3.0
        self.assertEqual(H._marker_run(marks, SP, "treble")[1], "mixed_marker_kinds")

    def test_both_glyph_anchors_pass_a_crushed_bowl_boxed_alone(self):
        marks = [marker("keyFlat", 100.0 + PITCH_X * i, KO.expected_step("treble", "b", i + 1)) for i in range(3)]       # centres ON the pitch
        self.assertEqual(H._marker_run(marks, SP, "treble")[:2], (-3, "markers"))


class TestWhereItCannotJudgeItChangesNothing(unittest.TestCase):
    def test_a_record_with_no_measured_step_reads_exactly_as_before(self):
        marks = flat_run("treble", 3) + [marker("keyNatural", 172.0, 5.0)]
        for m in marks:
            del m.detail["step"]
        self.assertEqual(H._marker_run(marks, SP, "treble")[1], "mixed_marker_kinds")

    def test_no_clef_reads_exactly_as_before(self):
        marks = flat_run("treble", 3) + [marker("keyNatural", 172.0, 5.0)]
        self.assertEqual(H._marker_run(marks, SP, None)[1], "mixed_marker_kinds")

    def test_an_all_natural_run_is_still_a_cancellation(self):
        marks = [marker("keyNatural", 100.0 + PITCH_X * i, 4.0) for i in range(2)]
        self.assertEqual(H._marker_run(marks, SP, "treble")[1], "natural_markers")

    def test_a_run_none_of_whose_slots_match_falls_back_to_today(self):
        marks = [marker("keyFlat", 100.0 + PITCH_X * i, 50.0) for i in range(3)]
        self.assertEqual(H._marker_run(marks, SP, "treble")[:2], (-3, "markers"))


class TestMembershipAgreesWithTheReading(unittest.TestCase):
    def test_the_in_bar_natural_is_not_a_member_of_the_run(self):
        nat = marker("keyNatural", 172.0, 5.0)
        marks = flat_run("treble", 3) + [nat]
        members = H.marker_run_members(marks, SP, "treble")
        self.assertEqual(len(members), 3)
        self.assertNotIn(nat, members)
        self.assertEqual(H.marker_run_members(marks, SP), ())                       # TWIN: no clef, the mixed run, no member (today)


if __name__ == "__main__":
    unittest.main()
