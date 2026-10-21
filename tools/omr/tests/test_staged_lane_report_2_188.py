"""ROADMAP 2.188 -- the counting logic of the shared lane report. Every positive has a twin that must NOT fire
(a counter that says "changed" for everything, or "nothing" for everything, cannot pass)."""
from __future__ import annotations

import json
import pathlib
import random
import unittest

from tools.omr.staged import lane_report as L

SAMPLE = pathlib.Path(__file__).resolve().parents[3] / "benchmarks" / "lane-report" / "sample.json"


def host(rg, cx, cy, kind="note", typ="quarter", sub=None, blue=False, pitch="C4", page=1):
    return dict(kind=kind, part="P1", measure="1", rg=rg, page=page, cx=cx, cy=cy,
                box=[cx - 5, cy - 5, cx + 5, cy + 5], type=typ, pitch=pitch if kind == "note" else None,
                blue=blue, sub=sub or {}, chord=False)


def arm(hosts, loose=()):
    return dict(hosts=list(hosts), loose=list(loose))


class TestDiff(unittest.TestCase):
    def test_identical_arms_change_nothing(self):
        h = [host("g1", 10, 10, sub={"accidental": ["flat"]}), host("g2", 50, 10, kind="rest")]
        d = L.diff_arms(arm(h), arm(h), tol=8)
        self.assertEqual(d["counts"], {})
        self.assertEqual(d["paired"], 2)
        self.assertEqual(L.format_counts(d["counts"]), "NOTHING CHANGED in the exported file")

    def test_gained_and_lost_hosts_by_kind(self):
        off = arm([host("g1", 10, 10, kind="rest", typ="eighth")])
        on = arm([host("g2", 300, 10, sub={"dot": ["."], "flag": ["eighth"]}, typ="eighth")])
        d = L.diff_arms(off, on, tol=8)
        self.assertEqual(d["counts"]["rest"], {"gained": 0, "lost": 1, "changed": 0})
        self.assertEqual(d["counts"]["note"], {"gained": 1, "lost": 0, "changed": 0})
        self.assertEqual(d["counts"]["dot"]["gained"], 1)
        self.assertEqual(d["counts"]["flag"]["gained"], 1)

    def test_a_rest_that_becomes_a_note_at_one_place_is_lost_plus_gained(self):
        d = L.diff_arms(arm([host("g1", 10, 10, kind="rest")]), arm([host("g1", 10, 10)]), tol=8)
        self.assertEqual((d["counts"]["rest"]["lost"], d["counts"]["note"]["gained"]), (1, 1))

    def test_value_pitch_blue_and_accidental_changes(self):
        off = arm([host("g1", 10, 10, typ="quarter", pitch="C4"), host("g2", 90, 10, sub={"accidental": ["flat"]})])
        on = arm([host("g1", 10, 10, typ="eighth", pitch="D4", blue=True), host("g2", 90, 10, sub={"accidental": ["sharp"]})])
        c = L.diff_arms(off, on, tol=8)["counts"]
        self.assertEqual(c["value"]["changed"], 1)
        self.assertEqual(c["pitch"]["changed"], 1)
        self.assertEqual(c["blue"]["gained"], 1)
        self.assertEqual(c["accidental"]["changed"], 1)
        self.assertNotIn("accidental lost", L.format_counts(c))

    def test_far_apart_hosts_do_not_pair(self):
        d = L.diff_arms(arm([host("g1", 10, 10)]), arm([host("g1", 10 + 40, 10)]), tol=8)
        self.assertEqual(d["paired"], 0)
        self.assertEqual((d["counts"]["note"]["lost"], d["counts"]["note"]["gained"]), (1, 1))

    def test_pairing_is_one_to_one_nearest_first(self):
        off = [host("a", 10, 10), host("b", 14, 10)]
        on = [host("c", 13, 10)]
        pairs, lost, gained = L.pair_hosts(off, on, 8)
        self.assertEqual(pairs, [(1, 0)])
        self.assertEqual((lost, gained), ([0], []))

    def test_a_host_with_no_page_position_never_pairs(self):
        a = host("g1", 10, 10)
        a.update(page=None, cx=None, cy=None, box=None)
        pairs, lost, gained = L.pair_hosts([a], [dict(a)], 8)
        self.assertEqual((pairs, lost, gained), ([], [0], [0]))

    def test_loose_directions_are_a_multiset_per_bar(self):
        d1 = dict(kind="dynamic", part="P1", measure="3", value="p", page=1, cx=1, cy=1, box=[0, 0, 2, 2], rg="g")
        c = L.diff_arms(arm([], [d1]), arm([], [dict(d1), dict(d1, value="f")]), tol=8)["counts"]
        self.assertEqual(c["dynamic"], {"gained": 1, "lost": 0, "changed": 0})
        c = L.diff_arms(arm([], [d1]), arm([], [dict(d1)]), tol=8)["counts"]
        self.assertEqual(c, {})

    def test_unchanged_symbols_feed_the_controls(self):
        h = host("g1", 10, 10, sub={"accidental": ["flat"], "dot": ["."]})
        d = L.diff_arms(arm([h]), arm([dict(h)]), tol=8)
        self.assertEqual({s["kind"] for s in d["same"]}, {"note", "accidental", "dot"})


class TestParse(unittest.TestCase):
    XML = ('<score-partwise><part id="P1"><measure number="1"><attributes><key><fifths>-2</fifths></key>'
           '<time><beats>2</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>'
           '<direction><direction-type><dynamics><p/></dynamics></direction-type></direction>'
           '<note rg="glyph/1/0/0/0/1" color="#1F6FEB"><pitch><step>E</step><alter>-1</alter><octave>4</octave></pitch>'
           '<type>eighth</type><dot/><accidental>flat</accidental><tie type="start"/></note>'
           '<note rg="glyph/1/0/0/0/2"><rest/><type>quarter</type></note></measure></part></score-partwise>')
    BOXES = {"glyph/1/0/0/0/1": dict(page=1, box=[0, 0, 10, 10], cls="x"), "glyph/1/0/0/0/2": dict(page=1, box=[20, 0, 30, 10], cls="y")}

    def test_notes_marks_and_directions(self):
        s = L.parse_symbols(self.XML, self.BOXES)
        n, r = s["hosts"]
        self.assertEqual((n["kind"], n["pitch"], n["blue"], n["page"]), ("note", "E-14", True, 1))
        self.assertEqual(n["sub"], {"accidental": ["flat"], "dot": ["."], "flag": ["eighth"], "tie": ["start"]})
        self.assertEqual(r["kind"], "rest")
        kinds = {(d["kind"], d["value"]) for d in s["loose"]}
        self.assertEqual(kinds, {("key", "-2"), ("time", "2/4"), ("clef", "G2"), ("dynamic", "p")})
        dyn = [d for d in s["loose"] if d["kind"] == "dynamic"][0]
        self.assertEqual(dyn["rg"], "glyph/1/0/0/0/1")     # anchored to the next note

    def test_a_beamed_eighth_has_a_beam_and_no_flag(self):
        xml = self.XML.replace("<dot/>", "<beam number=\"1\">begin</beam>")
        sub = L.parse_symbols(xml, self.BOXES)["hosts"][0]["sub"]
        self.assertIn("beam", sub)
        self.assertNotIn("flag", sub)


class TestJudged(unittest.TestCase):
    def t(self, status, i=1):
        return dict(item="x", tile=i, subject="glyph/1", answer="8", status=status, note="n")

    def test_moves(self):
        off = [self.t("right", 1), self.t("right", 2), self.t("wrong", 3), self.t("right", 4), self.t("not_found", 5)]
        on = [self.t("wrong", 1), self.t("narrowed", 2), self.t("right", 3), self.t("right", 4), self.t("not_found", 5)]
        m = L.compare_judged(off, on)
        self.assertEqual([w["tile"] for w in m["worse"]], [1])
        self.assertEqual([w["tile"] for w in m["lost"]], [2])
        self.assertEqual([w["tile"] for w in m["better"]], [3])
        self.assertEqual(m["scored"], 4)

    def test_nothing_moves(self):
        t = [self.t("right", 1), self.t("wrong", 2)]
        m = L.compare_judged(t, [dict(x) for x in t])
        self.assertEqual((m["worse"], m["lost"], m["better"]), ([], [], []))


class TestTilesAndSample(unittest.TestCase):
    def changes(self):
        def mk(kind, i):
            return dict(kind=kind, side="gained", page=1, cx=1, cy=1, box=[0, 0, 5, 5], rg="g%s%d" % (kind, i), value="v")
        return {"litolff": [mk("rest", i) for i in range(10)] + [mk("dot", i) for i in range(10)],
                "brahms": [mk("accidental", i) for i in range(10)]}

    def same(self):
        return {"litolff": [dict(kind=k, page=1, cx=1, cy=1, box=[0, 0, 5, 5], rg="s%s%d" % (k, i), value="v")
                            for k in ("rest", "dot", "accidental") for i in range(6)], "brahms": []}

    def test_nine_cases_stratified_and_three_controls(self):
        items = L.pick_tiles(self.changes(), self.same(), seed=7)
        cases = [i for i in items if i["role"] == "case"]
        ctrl = [i for i in items if i["role"] == "control"]
        self.assertEqual((len(cases), len(ctrl)), (9, 3))
        self.assertEqual({c["kind"] for c in cases}, {"rest", "dot", "accidental"})
        self.assertEqual([sum(c["kind"] == k for c in cases) for k in ("rest", "dot", "accidental")], [3, 3, 3])
        self.assertTrue(all(c["rg"].startswith("s") for c in ctrl))          # controls are unchanged symbols
        self.assertEqual(L.pick_tiles(self.changes(), self.same(), seed=7), items)   # seeded
        self.assertNotEqual([i["rg"] for i in L.pick_tiles(self.changes(), self.same(), seed=8)], [i["rg"] for i in items])

    def test_no_changes_gives_no_cases(self):
        items = L.pick_tiles({"litolff": []}, self.same(), seed=1)
        self.assertEqual([i for i in items if i["role"] == "case"], [])

    def test_a_symbol_with_no_place_is_never_a_tile(self):
        ch = {"litolff": [dict(kind="note", side="gained", page=None, box=None, rg="x", value="q")]}
        self.assertEqual(L.pick_tiles(ch, self.same(), seed=1), [i for i in L.pick_tiles(ch, self.same(), seed=1) if i["role"] == "control"])

    def test_draw_is_deterministic_and_inside_candidates(self):
        cands = {"litolff": list(range(1, 17)), "brahms": list(range(27))}
        a, b = L.draw_sample(cands, 2188, 8), L.draw_sample(cands, 2188, 8)
        self.assertEqual(a, b)
        self.assertTrue(all(len(v) == 8 and set(v) <= set(cands[k]) for k, v in a.items()))
        self.assertNotEqual(a, L.draw_sample(cands, 2189, 8))

    def test_the_committed_sample_is_the_draw_of_its_own_candidates(self):
        s = json.loads(SAMPLE.read_text())
        cands = {p: v["candidates"] for p, v in s["plates"].items()}
        want = L.draw_sample(cands, s["seed"], s["n_per_plate"])
        self.assertEqual({p: v["pages"] for p, v in s["plates"].items()}, want)


class TestFlags(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(L.parse_flags(["OMR_A", "OMR_B=2", "OMR_C=5:7"]),
                         [("OMR_A", "0", "1"), ("OMR_B", "0", "2"), ("OMR_C", "5", "7")])

    def test_unknown_flag_is_refused_unless_allowed(self):
        with self.assertRaises(SystemExit):
            L.decide_from("auto", [("OMR_NO_SUCH_FLAG_ANYWHERE", "0", "1")], False)
        mode, notes = L.decide_from("auto", [("OMR_NO_SUCH_FLAG_ANYWHERE", "0", "1")], True)
        self.assertEqual(mode, "adjudicate")

    def test_a_gather_flag_cannot_be_replayed_from_adjudicate(self):
        self.assertTrue(L.acts_in_gather(["staged/gather.py"]))
        self.assertFalse(L.acts_in_gather(["staged/adjudicators/rhythm.py"]))
        self.assertFalse(L.acts_in_gather(["transcribe.py"]))
        homes = L.flag_homes("OMR_DOT_POSITION_OVER_WEDGE")
        self.assertTrue(homes and not L.acts_in_gather(homes))
        with self.assertRaises(SystemExit):
            orig = L.flag_homes
            L.flag_homes = lambda f, root=None: ["staged/gather.py"]
            try:
                L.decide_from("adjudicate", [("OMR_X", "0", "1")], False)
            finally:
                L.flag_homes = orig


class TestIds(unittest.TestCase):
    def test_row_ids_do_not_make_two_verdicts_differ(self):
        a = dict(outcome="decided", value={"shared_stem": "obs:064845", "w": 1}, reason="r")
        b = dict(outcome="decided", value={"shared_stem": "obs:048953", "w": 1}, reason="r")
        c = dict(outcome="decided", value={"shared_stem": "obs:048953", "w": 2}, reason="r")
        self.assertEqual(L._brief(a), L._brief(b))
        self.assertNotEqual(L._brief(a), L._brief(c))

    def test_page_of(self):
        self.assertEqual(L.page_of("glyph/10/0/1/2/3"), 10)
        self.assertIsNone(L.page_of("document"))
        self.assertIsNone(L.page_of("roster/3"))


if __name__ == "__main__":
    unittest.main()
