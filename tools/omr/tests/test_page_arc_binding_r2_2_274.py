"""ROADMAP 2.274 step 2 round 2 (STAGED, flag `OMR_PAGE_ARC_WRITE`, default OFF): the three causes of a wrong binding, fixed where they arise.
(b) a run is cut at a bridged gap of 2 spaces or more (`page_arc_bind.pieces_of`): a short tail is dropped, two long stretches are two arcs;
(c) a chord end: the arc's side names the member (cap = top head, cup = bottom head) in a two-member chord; a stack of three reads the end's height only close to a member;
(d) an end that stands more than 3 spaces on the arc's own side of the head it bound to abstains (a nearer head was never boxed).
Pure functions; no record, no OCR."""
import unittest

from omr.staged import page_arc_bind as PB

SP = 10.0


def _h(key, cx, cy, w=12.0, h=10.0):
    return {"key": key, "cx": cx, "cy": cy, "w": w, "h": h, "cell": 0}


def _detail(xl, yl, xr, yr, sag=-15.0):
    tr = []
    for x in range(int(xl), int(xr) + 1, 2):
        f = (x - xl) / float(xr - xl)
        tr.append([x, yl + f * (yr - yl) + sag * 4 * f * (1 - f) - 1, yl + f * (yr - yl) + sag * 4 * f * (1 - f) + 1])
    return {"space_page_px": SP, "x_left_page": xl, "y_left_page": yl, "x_right_page": xr, "y_right_page": yr, "trace": tr}


def _run(xs, y=100.0):
    return {"points": [[float(x), y] for x in xs], "ends": [[float(xs[0]), y, 0.0], [float(xs[-1]), y, 0.0]], "core_ends": [[float(xs[0]), y], [float(xs[-1]), y]]}


class TestCutAtABridgedGap(unittest.TestCase):
    def test_a_run_with_no_gap_is_itself(self):
        r = _run(range(0, 200, 8))
        (p,) = PB.pieces_of(r, SP)
        self.assertFalse(p["trimmed"])
        self.assertEqual(p["points"], r["points"])

    def test_a_tail_after_a_gap_is_dropped_and_the_end_is_where_the_ink_stops(self):
        xs = list(range(0, 120, 8)) + [150, 158]          # a 3.4-space bridge, then 0.8 spaces of tail
        (p,) = PB.pieces_of(_run(xs), SP)
        self.assertTrue(p["trimmed"])
        self.assertEqual(p["core_ends"][0], [0.0, 100.0])
        self.assertEqual(p["core_ends"][1][0], 112.0)          # the last ink before the gap, not the tail's end

    def test_two_long_stretches_are_two_pieces_each_with_its_own_ends(self):
        xs = list(range(0, 80, 8)) + list(range(110, 200, 8))
        ps = PB.pieces_of(_run(xs), SP)
        self.assertEqual(len(ps), 2)
        self.assertEqual([p["piece"] for p in ps], [0, 1])
        self.assertEqual(ps[0]["core_ends"][1][0], 72.0)
        self.assertEqual(ps[1]["core_ends"][0][0], 110.0)

    def test_a_gap_under_two_spaces_is_bridged_as_before(self):
        xs = list(range(0, 80, 8)) + list(range(88, 200, 8))          # 16 px = 1.6 spaces between the stretches
        (p,) = PB.pieces_of(_run(xs), SP)
        self.assertFalse(p["trimmed"])

    def test_nothing_long_enough_is_no_piece(self):
        self.assertEqual(PB.pieces_of(_run([0, 8, 16, 60, 68]), SP), [])


class TestAChordEnd(unittest.TestCase):
    def _bind(self, heads, d):
        return PB.closest_binder({"left": [], "right": []})(heads, SP, None, True, None, d)

    def test_a_cap_ends_on_the_top_member_of_a_two_note_chord_even_where_the_end_stands_lower(self):
        d = _detail(0, 100, 100, 112, sag=-15.0)          # a cap; its right end comes down to y 112, nearer the LOWER member
        heads = [_h("a", -2, 100), _h("top", 104, 98), _h("bot", 104, 111)]
        b = self._bind(heads, d)
        self.assertEqual(b["right"]["head"], "top")
        self.assertTrue(b["right"].get("chord_by_side"))

    def test_a_cup_ends_on_the_bottom_member(self):
        d = _detail(0, 100, 100, 88, sag=15.0)
        heads = [_h("a", -2, 100), _h("top", 104, 90), _h("bot", 104, 102)]
        self.assertEqual(self._bind(heads, d)["right"]["head"], "bot")

    def test_a_three_note_chord_reads_the_inner_member_only_close_to_the_end(self):
        heads = [_h("a", -2, 100), _h("t", 104, 85), _h("m", 104, 100), _h("b", 104, 115)]
        near = self._bind(heads, _detail(0, 100, 100, 101, sag=-15.0))          # the end stands at the middle member
        self.assertEqual(near["right"]["head"], "m")
        lower = self._bind(heads, _detail(0, 100, 100, 112, sag=-15.0))          # 3 px from b: b is inner for a cap, but the end stands within 1.2 spaces of it
        self.assertEqual(lower["right"]["head"], "b")
        unclear = self._bind(heads, _detail(0, 100, 100, 131, sag=-15.0))          # 16 px from b, 31 from m: no member is read from the height
        self.assertEqual(unclear["right"].get("unbound"), "chord_member_unclear")


class TestAnEndFarBeyondItsHead(unittest.TestCase):
    def test_a_cup_end_far_below_the_head_it_would_bind_abstains(self):
        d = _detail(0, 150, 100, 150, sag=15.0)          # a cup whose ends stand at y 150
        heads = [_h("up", -2, 100), _h("far", 104, 100)]          # the heads stand 5 spaces above the ends: a head between was never boxed
        b = self._bind(heads, d)
        self.assertEqual(b["left"].get("unbound"), "end_far_beyond_head")
        self.assertEqual(b["right"].get("unbound"), "end_far_beyond_head")

    def test_a_head_beside_the_end_binds(self):
        d = _detail(0, 150, 100, 150, sag=15.0)
        heads = [_h("a", -2, 140), _h("b", 104, 140)]
        b = self._bind(heads, d)
        self.assertEqual((b["left"]["head"], b["right"]["head"]), ("a", "b"))

    def _bind(self, heads, d):
        return PB.closest_binder({"left": [], "right": []})(heads, SP, None, True, None, d)


if __name__ == "__main__":
    unittest.main()
