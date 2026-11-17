"""ROADMAP 2.305 (STAGED, the page arc pass, flag `OMR_PAGE_ARC_WRITE` default OFF): an arc is OVER its notes -- an end whose head stands on the arc's FAR side
(a cap's head above its end, a cup's below) is not that ink's note (`page_arc_bind.closest_binder`: `head_on_the_arcs_far_side`), and the pass then binds on the
staff the arc's own side names (`ownership.adjudicate_page_arc_binding`).

Controls built from REAL rows (`data_arc_binding_2_305.json`, cut by the lane's `make_fixture.py` from the 2305 Litolff gather): the page-ink run and the notehead
boxes of the two staves, never a drawing. Each fails on the tree before 2.305 (the binder bound both ends to the far staff's heads).
"""
import json
import pathlib
import unittest

from tools.omr.staged import page_arc_bind as PB

DATA = json.loads((pathlib.Path(__file__).parent / "data_arc_binding_2_305.json").read_text())


def _heads(case, staff):
    out = []
    for h in case["heads"]:
        if "/".join(h["key"].split("/")[1:4]) != staff:
            continue
        x0, y0, x1, y1 = h["box"]
        out.append({"key": h["key"], "cx": (x0 + x1) / 2.0, "cy": (y0 + y1) / 2.0, "w": x1 - x0, "h": y1 - y0, "cell": h["cell"]})
    return out


def _bind(case, staff):
    run = case["run"]
    sp = float(run["space_page_px"])
    d = PB.curve_detail(run, sp)
    return PB.closest_binder({"left": [], "right": []})(_heads(case, staff), sp, None, True, None, d)


class TestAnArcIsOverItsNotes(unittest.TestCase):
    def test_litolff_p13_run31_the_lower_staffs_heads_are_on_the_far_side(self):
        # the cup under staff 8's tied notes; the witnessing box's owner said staff 9, whose own twin tie's heads stand 3.4 sp below the ends
        b = _bind(DATA["litolff_p13_run31_upper_tie"], "13/0/9")
        self.assertEqual(b["side"], "below")
        self.assertEqual(b["left"].get("unbound"), "head_on_the_arcs_far_side")
        self.assertEqual(b["right"].get("unbound"), "head_on_the_arcs_far_side")

    def test_litolff_p13_run31_binds_on_the_staff_its_side_names(self):
        b = _bind(DATA["litolff_p13_run31_upper_tie"], "13/0/8")
        self.assertIn(b["left"].get("head"), ("glyph/13/0/8/0/11", "glyph/13/0/8/0/14"))          # two boxes of the one head (2.290)
        self.assertEqual(b["right"].get("head"), "glyph/13/0/8/1/6")

    def test_sean_tile9_the_lower_slurs_ink_is_not_bound_to_the_upper_staff(self):
        # Sean (2.298 r2 tile 9): the box holds two slurs; the marks were right for the TOP staff's slur -- but the traced ink is the LOWER slur's, so binding it to
        # the top staff's heads wrote the right notes from the wrong ink. The top slur stays the old path's (its own box); this ink no longer claims those heads.
        b = _bind(DATA["litolff_p15_run4_sean_tile9"], "15/1/2")
        self.assertIn("head_on_the_arcs_far_side", (b["left"].get("unbound"), b["right"].get("unbound")))


if __name__ == "__main__":
    unittest.main()
