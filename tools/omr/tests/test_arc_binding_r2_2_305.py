"""ROADMAP 2.305 round 2 (STAGED, the page arc pass, flag `OMR_PAGE_ARC_WRITE` default OFF): controls built from the REAL rows of Sean's r1 tiles
(`data_arc_binding_2_305.json`, cut from the 2305 gathers by the lane's `make_fixture_r2.py`), never drawings. Each fails on the round-1 tree.

  * tile 8 ("it's two ties and it goes one extra note too far"): one traced run over two ties MEETING at a head is cut at that head
    (`page_arc_bind.split_at_meeting_heads`), so each tie binds its own two heads;
  * tile 5 ("no arc between those two notes; one arc goes from the second note into the next measure"): the detector box, cut at its cell's left edge where
    there is no arc ink, witnesses the run that IS its ink when measured against its inked width (`page_arc_bind.inked_witness`).
"""
import json
import pathlib
import unittest

from tools.omr.staged import page_arc_bind as PB
from tools.omr.staged.page_arcs import WITNESS_SHARE

DATA = json.loads((pathlib.Path(__file__).parent / "data_arc_binding_2_305.json").read_text())


class TestTwoTiesMeetingAtAHead(unittest.TestCase):
    def setUp(self):
        self.case = DATA["litolff_p5_run76_sean_tile8"]
        self.run = self.case["run"]
        self.sp = float(self.run["space_page_px"])
        self.heads = [h["box"] for h in self.case["heads"]]

    def test_the_run_is_cut_at_the_head_its_ink_meets(self):
        ps = PB.split_at_meeting_heads(dict(self.run, piece=0), self.heads, self.sp)
        self.assertEqual(len(ps), 2)
        cut = ps[0]["core_ends"][1][0]
        self.assertAlmostEqual(cut, ps[1]["core_ends"][0][0])
        # the cut stands over a notehead box of the staff (the half note both ties meet at)
        self.assertTrue(any(b[0] - 0.5 * self.sp <= cut <= b[2] + 0.5 * self.sp for b in self.heads))

    def test_a_run_with_no_head_under_its_dip_is_one_arc(self):
        # the twin: the same real run with the meeting head taken away stays whole
        ps = PB.split_at_meeting_heads(dict(self.run, piece=0), self.heads, self.sp)
        cut = ps[0]["core_ends"][1][0]
        others = [b for b in self.heads if not (b[0] - 0.5 * self.sp <= cut <= b[2] + 0.5 * self.sp)]
        self.assertEqual(len(PB.split_at_meeting_heads(dict(self.run, piece=0), others, self.sp)), 1)


    def test_the_second_tie_ends_on_the_note_its_ink_lands_on_not_the_next_chord(self):
        # Sean: "it goes one extra note too far" -- the traced end ran on past 5/0/5/4/3 (the tie's note) to the chord 4/2
        ps = PB.split_at_meeting_heads(dict(self.run, piece=0), self.heads, self.sp)
        d = PB.curve_detail(ps[1], self.sp)
        heads = []
        for h in self.case["heads"]:
            x0, y0, x1, y1 = h["box"]
            heads.append({"key": h["key"], "cx": (x0 + x1) / 2.0, "cy": (y0 + y1) / 2.0, "w": x1 - x0, "h": y1 - y0, "cell": h["cell"]})
        b = PB.closest_binder({"left": [], "right": []})(heads, self.sp, None, True, None, d)
        self.assertEqual(b["left"].get("head"), "glyph/5/0/5/3/1")
        self.assertEqual(b["right"].get("head"), "glyph/5/0/5/4/3")


class TestABoxCutAtItsCellEdge(unittest.TestCase):
    def test_the_box_witnesses_the_run_that_is_its_ink(self):
        c = DATA["brahms_p11_box_3_22_sean_tile5"]
        sp = float(c["runs"][0]["space_page_px"])
        pts = [r["points"] for r in c["runs"]]
        self.assertEqual(c["runs"][0]["ordinal"], 69)
        self.assertFalse(c["runs"][0]["witnesses"])          # GATHER's width test left it unwitnessed
        self.assertEqual(PB.inked_witness(c["box"], pts, sp, WITNESS_SHARE), 0)

    def test_an_inked_width_shorter_than_a_piece_names_none(self):
        c = DATA["brahms_p11_box_3_22_sean_tile5"]
        sp = float(c["runs"][0]["space_page_px"])
        x0, y0, x1, y1 = c["box"]
        tiny = [[[x0 + 1, y0], [x0 + 1 + sp, y0]]]
        self.assertIsNone(PB.inked_witness(c["box"], tiny, sp, WITNESS_SHARE))


if __name__ == "__main__":
    unittest.main()
