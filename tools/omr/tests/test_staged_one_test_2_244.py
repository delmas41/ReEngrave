"""ROADMAP 2.244 piece 4 -- the combined run (tools.omr.staged.one_test). Pure parts only: the arms, the interactions, the
refusal. Every positive has a twin that must fail."""
from __future__ import annotations

import copy
import unittest

from tools.omr.staged import one_test as T


def fp(**kw):
    base = dict(plate="litolff", tree="abc123abc123:000000000000", mode="adjudicate", tag="20261029-night", pages=[2, 4],
                record=[100, 5], gather_tree=None, cells="saved record's own cells", detector_cache=None, ocr=[])
    base.update(kw)
    return base


def arms(**over):
    a = {lab: {"litolff": fp()} for lab in ("base", "only-OMR_A", "only-OMR_B", "all")}
    for lab, kw in over.items():
        a[lab]["litolff"] = fp(**kw)
    return a


class TestArms(unittest.TestCase):
    FLAGS = [("OMR_A", "0", "1"), ("OMR_B", "0", "2")]

    def test_base_each_alone_and_all(self):
        specs = T.arm_specs(self.FLAGS)
        self.assertEqual([s[0] for s in specs], ["base", "only-OMR_A", "only-OMR_B", "all"])
        by = {s[0]: s for s in specs}
        self.assertEqual(by["base"][2], "off")
        self.assertEqual(by["only-OMR_A"][1], [("OMR_A", "0", "1"), ("OMR_B", "0", "0")])      # B stays at its OFF value
        self.assertEqual(by["only-OMR_B"][1], [("OMR_A", "0", "0"), ("OMR_B", "0", "2")])
        self.assertEqual(by["all"][1], self.FLAGS)
        self.assertEqual(by["all"][2], "on")

    def test_one_flag_is_base_and_all(self):
        self.assertEqual([s[0] for s in T.arm_specs(self.FLAGS[:1])], ["base", "all"])


class TestRefusal(unittest.TestCase):
    def test_identical_arms_print_one_control_line(self):
        line = T.check_same(arms())
        self.assertIn("tree abc123abc123", line)
        self.assertIn("stages adjudicate", line)

    def test_a_planted_stage_mismatch_is_refused(self):       # the control that can fail
        with self.assertRaises(T.ArmMismatch) as cm:
            T.check_same(arms(**{"only-OMR_B": dict(mode="gather")}))
        msg = str(cm.exception)
        self.assertIn("REFUSED", msg)
        self.assertIn("differs from base in mode", msg)
        self.assertIn("control line, arm only-OMR_B", msg)

    def test_other_tree_cells_tag_pages_cache_are_refused(self):
        for field, val in (("tree", "def456def456:000000000000"), ("cells", "cm-other"), ("tag", "20261020-night"),
                           ("pages", [2, 5]), ("detector_cache", "/elsewhere"), ("ocr", [["OMR_SURYA_KEEP_ALIVE", "1"]]),
                           ("record", [101, 5]), ("gather_tree", ["x", False])):
            with self.assertRaises(T.ArmMismatch, msg=field):
                T.check_same(arms(all={field: val}))

    def test_an_unnameable_tree_equals_nothing_not_even_itself(self):
        with self.assertRaises(T.ArmMismatch):
            T.check_same(arms(**{lab: dict(tree=None) for lab in ("base", "only-OMR_A", "only-OMR_B", "all")}))

    def test_a_missing_plate_is_refused(self):
        a = arms()
        del a["all"]["litolff"]
        with self.assertRaises(T.ArmMismatch):
            T.check_same(a)

    def test_the_real_fingerprint_names_the_tree_and_reads_the_stage(self):
        f = T.arm_fingerprint("litolff", "adjudicate", "20261029-night", [4, 2], {}, ["OMR_A"])
        self.assertEqual(f["pages"], [2, 4])
        self.assertEqual(f["mode"], "adjudicate")
        self.assertIsNotNone(f["tree"])


def ch(rg, kind="note", side="gained", value="half", page=3, box=(100, 100, 120, 120)):
    return dict(kind=kind, side=side, page=page, cx=110, cy=110, box=list(box), rg=rg, value=value)


class TestInteractions(unittest.TestCase):
    def test_all_equals_the_union_of_the_singles_has_no_interaction(self):
        a, b = [ch("glyph/3/0/1/4/1")], [ch("glyph/3/0/1/5/1", kind="rest", value="quarter")]
        it = T.interactions({"A": a, "B": b}, a + b)
        self.assertEqual((it["only_together"], it["only_alone"]), ([], []))

    def test_the_same_change_in_two_singles_counts_once(self):
        c = ch("glyph/3/0/1/4/1")
        it = T.interactions({"A": [c], "B": [dict(c)]}, [dict(c)])
        self.assertEqual((it["only_together"], it["only_alone"]), ([], []))

    def test_a_change_only_the_combination_makes(self):
        a = [ch("glyph/3/0/1/4/1")]
        extra = ch("glyph/3/0/1/6/9", kind="dot", value="dot")
        it = T.interactions({"A": a, "B": []}, a + [extra])
        self.assertEqual(it["only_together"], [extra])
        self.assertEqual(it["only_alone"], [])

    def test_a_change_a_single_made_that_the_combination_loses(self):
        a, b = [ch("glyph/3/0/1/4/1")], [ch("glyph/3/0/1/5/1", kind="rest", value="quarter")]
        it = T.interactions({"A": a, "B": b}, a)
        self.assertEqual(it["only_together"], [])
        self.assertEqual([(c["arm"], c["kind"]) for c in it["only_alone"]], [("B", "rest")])

    def test_multiset_not_set(self):      # two identical changes in A, one in all: one is lost
        c = ch("glyph/3/0/1/4/1")
        it = T.interactions({"A": [c, dict(c)], "B": []}, [c])
        self.assertEqual(len(it["only_alone"]), 1)

    def test_interaction_judged_damage_is_the_combinations_own(self):
        w = lambda k: {"judged": {"worse": [dict(item="i", tile=k)], "unwritten_wrong": []}}
        meas = {"base": {}, "only-A": w("1"), "only-B": {"judged": {"worse": [], "unwritten_wrong": []}}, "all": {"judged": {
            "worse": [dict(item="i", tile="1"), dict(item="i", tile="2")], "unwritten_wrong": []}}}
        self.assertEqual(T.interaction_worse(meas), [("worse", "i", "2")])


class TestTiles(unittest.TestCase):
    def pool(self, n, off=0):
        return [ch("glyph/3/0/1/%d/1" % (i + off), box=(100 + 300 * i, 100 + 400 * (off > 0), 120 + 300 * i, 120 + 400 * (off > 0)))
                for i in range(n)]

    def test_tiles_are_split_across_lanes_and_say_their_arm(self):
        items = T.pick_lane_tiles({"A": {"litolff": self.pool(6)}, "B": {"litolff": self.pool(6, 40)}}, {"litolff": []},
                                  {"litolff": [dict(kind="note", page=3, box=[900, 900, 920, 920], rg="glyph/3/0/1/90/1", value="half")]},
                                  seed=1, n_cases=6, n_controls=3)
        cases = [i for i in items if i.get("role") == "case"]
        self.assertEqual(sorted({i["arm"] for i in cases}), ["A", "B"])
        self.assertEqual(sum(i["arm"] == "A" for i in cases), 3)
        self.assertTrue(all(i["plate"] == "litolff" for i in items))

    def test_a_lane_with_no_change_draws_no_tile(self):
        items = T.pick_lane_tiles({"A": {"litolff": self.pool(4)}, "B": {"litolff": []}}, {"litolff": []}, {"litolff": []}, seed=1,
                                  n_cases=4, n_controls=0)
        self.assertEqual({i["arm"] for i in items}, {"A"})


class TestLanding(unittest.TestCase):
    def test_a_judged_right_to_wrong_fails_that_arm_only(self):
        m = {"litolff": {"base": {}, "only-A": {"judged": {"worse": [1], "unwritten_wrong": []}},
                         "only-B": {"judged": {"worse": [], "unwritten_wrong": []}}}}
        out = T.landing(m, ["base", "only-A", "only-B"])
        self.assertIn("FAILS", out["only-A"])
        self.assertNotIn("FAILS", out["only-B"])


if __name__ == "__main__":
    unittest.main()
