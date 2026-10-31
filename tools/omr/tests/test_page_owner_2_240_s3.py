"""ROADMAP 2.240 step 2, round 2 (Sean 2026-10-31): a staff's own line / an arc's ink is never a ledger line of the candidate; an arc belongs to the
staff of the notes it binds; a read hairpin between two staves is one more witness. Synthetic geometry; every CONTROL arm can fail."""
import unittest

from tools.omr.staged import page_owner as PO
from tools.omr.tests.test_page_owner_2_240 import A, B, FRAMES, M_A, M_B, Rows, _ledger

STAVES = [dict(key=A, lines=[100.0, 110.0, 120.0, 130.0, 140.0], x0=0.0, x1=1000.0, grid=None),
          dict(key=B, lines=[220.0, 230.0, 240.0, 250.0, 260.0], x0=0.0, x1=1000.0, grid=None)]
TH = 4.0


class NotLedger(unittest.TestCase):
    def test_other_staffs_own_line_is_not_a_ledger(self):
        f = PO.not_ledger_maker([], STAVES)(506.0, A, TH)
        self.assertEqual(f(221.0), "other_staff_line")      # staff B's top line, seen from staff A's reading
        self.assertEqual(f(230.0), "other_staff_line")

    def test_CONTROL_a_real_ledger_row_off_every_staff_line_is_kept(self):
        f = PO.not_ledger_maker([], STAVES)(506.0, A, TH)
        self.assertIsNone(f(155.0))                         # a space below A, no staff's line, no arc
        self.assertIsNone(f(145.0))

    def test_candidates_own_lines_are_not_filtered_by_itself(self):
        f = PO.not_ledger_maker([], STAVES)(506.0, B, TH)
        self.assertIsNone(f(221.0))                         # B's own line is B's business (the rung finder never offers it)
        self.assertEqual(f(140.0), "other_staff_line")

    def test_arc_ink_is_not_a_ledger_tile_11(self):
        # a slur traced from the lower staff, rows 150..153 at x 480..540 (one space under staff A's bottom line)
        obs = [("glyph/0/0/1/3/9", "slur", {"trace": [[x, 150.0, 153.0] for x in range(480, 540)]})]
        f = PO.not_ledger_maker(obs, STAVES)(506.0, A, TH)
        self.assertEqual(f(152.5), "arc_ink")
        self.assertIsNone(f(165.0))                         # a row the arc does not cover
        far = PO.not_ledger_maker(obs, STAVES)(900.0, A, TH)
        self.assertIsNone(far(152.5))                       # the arc does not reach this x

    def test_reader_takes_the_filter(self):
        import inspect
        from tools.omr.annotate import far_head_reader as FH
        self.assertIn("not_ledger", inspect.signature(FH.read_absolute_position).parameters)
        self.assertIn("not_ledger", inspect.signature(FH.FarHeadPage.read).parameters)

    def test_reader_drops_a_rung_the_filter_names_and_keeps_the_rest(self):
        import numpy as np
        from tools.omr.annotate import far_head_reader as FH
        gray = np.full((400, 200), 255, np.uint8)
        for y0 in (150, 166):                               # two rows of ink 1 sp apart below a staff whose lines end at 140
            gray[y0:y0 + 3, 60:140] = 0
        lines = [100.0, 110.0, 120.0, 130.0, 140.0]
        box = (92.0, 172.0, 108.0, 184.0)
        det0, det1 = {}, {}
        FH.read_absolute_position(gray, lines, box, "g", [], [], detail_out=det0, thickness_px=3.0)
        FH.read_absolute_position(gray, lines, box, "g", [], [], detail_out=det1, thickness_px=3.0,
                                  not_ledger=lambda y: "arc_ink" if y < 160 else None)
        self.assertNotIn("not_ledger_dropped", det0)         # the reader without a filter is the reader as it was
        self.assertTrue(det1["not_ledger_dropped"])
        self.assertTrue(all(w == "arc_ink" for _y, w in det1["not_ledger_dropped"]))


class Hairpin(unittest.TestCase):
    HP = [[400.0, 168.0, 600.0, 192.0]]                      # a hairpin between the staves, x 400..600, rows 168..192

    def test_head_above_names_the_upper_staff_below_the_lower(self):
        above = PO.hairpin_reading(506.0, 150.0, (500, 145, 512, 155), FRAMES, "staff/0/0/", self.HP)
        below = PO.hairpin_reading(506.0, 205.0, (500, 200, 512, 210), FRAMES, "staff/0/0/", self.HP)
        self.assertEqual((above, below), (A, B))

    def test_CONTROL_no_hairpin_over_the_head_says_nothing(self):
        self.assertIsNone(PO.hairpin_reading(800.0, 150.0, (794, 145, 806, 155), FRAMES, "staff/0/0/", self.HP))
        self.assertIsNone(PO.hairpin_reading(506.0, 150.0, (500, 145, 512, 155), FRAMES, "staff/0/0/", []))
        self.assertIsNone(PO.hairpin_reading(506.0, 180.0, (500, 175, 512, 185), FRAMES, "staff/0/0/", self.HP))   # level with it

    def test_CONTROL_the_rule_is_local_a_head_outside_the_stretch_of_the_two_staves_says_nothing(self):
        # a head far above staff A (y 40) is above the hairpin too, but it is not in the stretch between A and B: A's owner says nothing here
        self.assertIsNone(PO.hairpin_reading(506.0, 40.0, (500, 35, 512, 45), FRAMES, "staff/0/0/", self.HP))
        self.assertIsNone(PO.hairpin_reading(506.0, 300.0, (500, 295, 512, 305), FRAMES, "staff/0/0/", self.HP))

    def test_names_the_owner_where_ledger_and_stem_name_nobody(self):
        r = PO.mark_owner("head", [M_A], (500, 195, 512, 205), FRAMES, Rows(), self.HP)
        self.assertEqual((r["status"], r["owner"], r["reason"]), ("decided", B, "hairpin"))

    def test_disagreement_is_guessed_with_both_staves(self):
        r = PO.mark_owner("head", [M_A, M_B], (500, 195, 512, 205), FRAMES,
                          Rows({**_ledger(M_A, A), **_ledger(M_B, A)}), self.HP)
        self.assertEqual(r["status"], "guessed")
        self.assertEqual((r["reason"], set(r["candidates"])), ("hairpin_disagrees", {A, B}))
        self.assertEqual(r["owner"], A)                      # the ledger's answer is kept, not overruled

    def test_agreement_changes_nothing_but_the_reason(self):
        r = PO.mark_owner("head", [M_A, M_B], (500, 195, 512, 205), FRAMES,
                          Rows({**_ledger(M_A, B), **_ledger(M_B, B)}), self.HP)
        self.assertEqual((r["status"], r["owner"]), ("decided", B))


def _arc(left, right, belly, staves=(B,)):
    return {"kind": "arc", "staves_seen_from": list(staves),
            "ends": {"left": [left[0], left[1]], "right": [right[0], right[1]], "belly_y": belly}}


def _head(key, cx, cy, owner, system="staff/0/0/"):
    return {"key": key, "box": [cx - 6, cy - 5, cx + 6, cy + 5], "owner": owner, "staff_system": system}


class ArcOwner(unittest.TestCase):
    def test_cap_over_notes_of_the_upper_staff_though_seen_from_the_lower(self):
        # a cap whose ends sit at y 142 over two heads of staff A at y 150, traced from B's crop (tile 5)
        arc = _arc((300, 142), (400, 142), 128)
        r = PO.arc_owner(arc, [_head("h1", 298, 150, A), _head("h2", 402, 150, A)], FRAMES)
        self.assertEqual((r["status"], r["owner"], r["reason"]), ("decided", A, "ends_agree"))

    def test_CONTROL_ends_naming_two_staves_abstain(self):
        arc = _arc((300, 142), (400, 142), 128)
        r = PO.arc_owner(arc, [_head("h1", 298, 150, A), _head("h2", 402, 150, B)], FRAMES)
        self.assertEqual((r["status"], r["reason"]), ("abstain", "ends_disagree"))

    def test_CONTROL_no_head_candidates_abstain_never_the_seen_from_staff(self):
        r = PO.arc_owner(_arc((300, 142), (400, 142), 128), [], FRAMES)
        self.assertEqual((r["status"], r["owner"], r["reason"]), ("abstain", None, "no_end_heads"))

    def test_unowned_end_head_abstains(self):
        r = PO.arc_owner(_arc((300, 142), (400, 142), 128), [_head("h1", 298, 150, A), _head("h2", 402, 150, None)], FRAMES)
        self.assertEqual((r["status"], r["owner"]), ("abstain", None))

    def test_one_end_is_guessed(self):
        r = PO.arc_owner(_arc((300, 142), (400, 142), 128), [_head("h1", 298, 150, A)], FRAMES)
        self.assertEqual((r["status"], r["owner"], r["reason"]), ("guessed", A, "one_end"))

    def test_notes_on_the_wrong_side_of_the_curve_do_not_count(self):
        # a cap is OVER its notes: a head ABOVE its end (y 120) is not under it
        r = PO.arc_owner(_arc((300, 142), (400, 142), 128), [_head("h1", 298, 120, A), _head("h2", 402, 120, A)], FRAMES)
        self.assertEqual(r["reason"], "no_end_heads")

    def test_cup_binds_notes_above_its_ends(self):
        arc = _arc((300, 248), (400, 248), 262, staves=(A,))
        r = PO.arc_owner(arc, [_head("h1", 298, 240, B), _head("h2", 402, 240, B)], FRAMES)
        self.assertEqual((r["owner"], r["reason"]), (B, "ends_agree"))


if __name__ == "__main__":
    unittest.main()
