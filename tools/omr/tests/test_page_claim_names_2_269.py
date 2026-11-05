"""ROADMAP 2.269 steps 0+1: the page-wide claims name their PAGE strokes (`page_claim_names`, flag `OMR_PAGE_CLAIM_NAMES`, default OFF) and the page beam
reader skips a stroke another claim names (`page_beams`, step 0). SYNTHETIC page strokes of known geometry; no raster.

Pins: a clef area names the strokes whose centre is inside it (and a stem crossing a word is NOT named: wholly inside); a stroke an earlier layer named is
CONTESTED on the later claim, never taken (the control that can fail: swap the layers and the other claim wins); the same owner twice is a twin, not a
contest; a hairpin names the strokes along its arms; the order is claim order, not row order; the flag off touches nothing; an existing reader of
`unit: ink` rows (`claims.covering`, `stem_end_heads.claims_holding`) does not see the new rows; a page beam on a named stroke is no beam."""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tools.omr.staged import page_beams as PB
from tools.omr.staged import page_claim_names as PN
from tools.omr.staged import record as R
from tools.omr.staged.beam_strokes import StrokeView
from tools.omr.staged.record import Log, Q, READERS


def box(x0, y0, x1, y1):
    return (x0, y0, x1, y1)


def pagemap(boxes, masks=None, scale=1.0):
    strokes = [SimpleNamespace(box=(b[0], b[1], b[2] - b[0], b[3] - b[1]), kind="blob") for b in boxes]
    return SimpleNamespace(strokes=strokes, masks=masks or [(np.zeros((0, 0), bool), 0, 0)] * len(boxes), scale=scale, sp=20.0)


PWS = SimpleNamespace(page=SimpleNamespace(page_index=0))


def area(log, owner, rect, sub=None, cell=0, scope=None):
    log.observe(sub or R.staff(0, 0, 0), Q.CLAIMED_AREA, list(rect), reader=READERS.CV_CLAIMED_REGISTER, frame="cell:%s" % cell, cell=None if scope else cell,
                scope=scope, owner=owner, owner_row=None, owner_glyph=None, unit="area", standing="READ", source="t")


def named(log):
    return [r for r in log.rows(Q.CLAIMED_AREA, R.page(0), scope=R.Scope.SELF_AND_DESCENDANTS) if (r.detail or {}).get("source") == PN.SOURCE
            and (r.detail or {}).get("unit") == PN.UNIT]


def run(log, pm):
    with mock.patch.dict(os.environ, {PN.ENV: "1"}):
        return PN.gather_page_claim_names(log, PWS, [], {}, pm)


class Predicates(unittest.TestCase):
    def test_a_clef_area_names_the_strokes_whose_centre_is_inside(self):
        idx = PN.StrokeIndex([box(10, 10, 30, 60), box(90, 10, 110, 60), box(28, 30, 70, 40)])
        # a cell claim (the clef): centre rule. stroke 0 centre (20, 35) in; stroke 2 centre (49, 35) out of [0..45]? it is in x<=45? 49 > 45 -> out
        self.assertEqual(PN.area_names(idx, [0, 0, 45, 70], page_wide=False), [0])

    def test_a_page_wide_claim_owns_only_what_is_wholly_inside_plus_one_px(self):
        idx = PN.StrokeIndex([box(10, 10, 30, 20), box(10, 10, 30, 90), box(9.5, 10, 30, 20)])
        got = PN.area_names(idx, [10, 10, 30, 20], page_wide=True)
        self.assertEqual(got, [0, 2])                       # 2 pokes out by 0.5 px: inside the +1 px; 1 is a stem crossing the box: keeps its ink
        self.assertEqual(PN.area_names(idx, [12, 12, 28, 18], page_wide=True), [])

    def test_the_index_equals_brute_force(self):
        import random
        rnd = random.Random(3)
        boxes = [(x, y, x + rnd.uniform(1, 80), y + rnd.uniform(1, 40)) for x, y in ((rnd.uniform(0, 1500), rnd.uniform(0, 800)) for _ in range(400))]
        idx = PN.StrokeIndex(boxes)
        for _ in range(60):
            x0, y0 = rnd.uniform(0, 1500), rnd.uniform(0, 800)
            a = (x0, y0, x0 + rnd.uniform(5, 300), y0 + rnd.uniform(5, 200))
            wi = [i for i, b in enumerate(boxes) if a[0] - 1 <= b[0] and b[2] <= a[2] + 1 and a[1] - 1 <= b[1] and b[3] <= a[3] + 1]
            ci = [i for i, b in enumerate(boxes) if a[0] <= (b[0] + b[2]) / 2 <= a[2] and a[1] <= (b[1] + b[3]) / 2 <= a[3]]
            self.assertEqual(idx.wholly_inside(a), wi)
            self.assertEqual(idx.centre_in(a), ci)


class TheCarvedRule(unittest.TestCase):
    """M1 carves ONE `barline` stroke per column, the height of the whole system; the staff-high barline claim's centre rule cannot name it."""

    def test_a_barline_claim_names_the_system_tall_rule_through_its_column_and_the_centre_rule_cannot(self):
        boxes = [box(2102, 1584, 2122, 6872), box(2300, 1590, 2320, 6872), box(2105, 1600, 2118, 1700)]
        idx = PN.StrokeIndex(boxes, ["barline", "barline", "vertical"])
        claim = [2097.5, 1584.0, 2126.5, 1713.0]
        self.assertEqual(idx.centre_in(claim), [2])                                   # the rule's centre is far below this staff
        self.assertEqual(PN.area_names(idx, claim, page_wide=False, owner="barline"), [0, 2])
        self.assertEqual(PN.area_names(idx, claim, page_wide=False, owner="clef"), [2])    # only a barline claim reaches the rule; and not the column at x 2300

    def test_the_census_counts_the_rule_strokes_named(self):
        pm = pagemap([box(2102, 1584, 2122, 6872), box(2300, 1590, 2320, 6872)])
        pm.strokes[0].kind = pm.strokes[1].kind = "barline"
        log = Log()
        area(log, "barline", [2097.5, 1584.0, 2126.5, 1713.0])
        res = run(log, pm)
        self.assertEqual((res["rule_strokes"], res["rule_strokes_named"]), (2, 1))


class Order(unittest.TestCase):
    def test_first_claim_wins_and_the_later_one_is_contested_not_taken(self):
        res = PN.settle([dict(owner="word", layer=3, ids=[5, 6]), dict(owner="clef", layer=2, ids=[6, 7])])
        word, clef = res["claims"]
        self.assertEqual(clef["won"], [6, 7])               # layer 2 comes first although its row stands second
        self.assertEqual(word["won"], [5])
        self.assertEqual(word["contested"], [[6, "clef"]])
        self.assertEqual(res["double"], 1)

    def test_the_control_can_fail_swap_the_layers_and_the_other_wins(self):
        res = PN.settle([dict(owner="word", layer=2, ids=[6]), dict(owner="clef", layer=3, ids=[6])])
        self.assertEqual(res["claims"][0]["won"], [6])
        self.assertEqual(res["claims"][1]["contested"], [[6, "word"]])

    def test_the_same_owner_twice_is_a_twin_not_a_contest(self):
        res = PN.settle([dict(owner="barline", layer=1, ids=[1, 2]), dict(owner="barline", layer=1, ids=[2, 3])])
        self.assertEqual(res["claims"][1]["won"], [3])
        self.assertEqual(res["claims"][1]["twins"], 1)
        self.assertEqual(res["claims"][1]["contested"], [])
        self.assertEqual(res["double"], 0)


class OnTheLog(unittest.TestCase):
    def test_a_clef_and_a_word_name_page_strokes_once_in_claim_order(self):
        pm = pagemap([box(10, 10, 30, 60), box(40, 10, 60, 60), box(100, 100, 150, 112)])
        log = Log()
        area(log, "word", [0, 0, 70, 70], sub=R.system(0, 0), cell=0, scope="system")      # page-wide: wholly inside -> strokes 0, 1
        area(log, "clef", [0, 0, 35, 70])                                                   # cell claim: centre rule -> stroke 0
        res = run(log, pm)
        rows = {r.detail["owner"]: r for r in named(log)}
        self.assertEqual(list(rows["clef"].value), [0])
        self.assertEqual(list(rows["word"].value), [1])                                    # stroke 0 is the clef's: the word does not take it
        self.assertEqual(rows["word"].detail["contested"], [[0, "clef"]])
        self.assertEqual(rows["clef"].detail["page_strokes"], [0])
        self.assertEqual(res["double_named"], 1)
        self.assertEqual(res["named"], 2)

    def test_the_rows_are_not_unit_ink_so_no_existing_reader_takes_page_ids_for_cell_ordinals(self):
        from tools.omr.staged import claims as CL
        from tools.omr.staged import stem_end_heads as SEH
        pm = pagemap([box(10, 10, 30, 60)])
        log = Log()
        area(log, "clef", [0, 0, 35, 70])
        run(log, pm)
        rows = list(log.rows(Q.CLAIMED_AREA, R.page(0), scope=R.Scope.SELF_AND_DESCENDANTS))
        self.assertTrue(named(log))
        # the box of a cell whose strokes are [0]: it must not be held by the page-id row (it is held only by the area row, which names no box here)
        self.assertEqual([r.detail["unit"] for r, _ in CL.covering(rows, "k", box_strokes=[0], cell=0)], [])
        self.assertEqual([r for r, _ in SEH.claims_holding(rows, "k", None, [0], 0)], [])

    def test_a_hairpin_names_the_strokes_along_its_arms(self):
        # a crescendo box 100 x 20 px at (100, 100): arms run from (100, 110) to (200, 100) and (200, 120)
        # build real masks: stroke 0 = the upper arm (a 1 px line along it), stroke 1 = a vertical stem crossing it (few px on the arm)
        h, w = 40, 120
        upper = np.zeros((h, w), bool)
        for x in range(100):
            upper[int(round(10 - 10 * x / 100.0)) + 10, x] = True
        stem = np.zeros((h, w), bool)
        stem[:, 60] = True
        pm = SimpleNamespace(strokes=[SimpleNamespace(box=(100, 100, 100, 20), kind="blob"), SimpleNamespace(box=(160, 90, 1, 40), kind="blob")],
                             masks=[(upper, 100, 90), (stem, 160, 90)], scale=1.0, sp=20.0)
        log = Log()
        log.observe(R.staff(0, 0, 0), Q.WEDGE_BOX, "crescendo", reader=READERS.CV_HAIRPINS, frame="page", reach=True,
                    bbox_page_px=[100.0, 100.0, 200.0, 120.0], staff_spacing_px=20.0)
        run(log, pm)
        rows = [r for r in named(log) if r.detail["owner"] == "hairpin"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(list(rows[0].value), [0])                       # the arm, not the stem crossing it

    def test_the_flag_off_touches_nothing(self):
        class NoLog:
            def __getattr__(self, n):
                raise AssertionError("flag off: the log must not be touched (%s)" % n)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(PN.ENV, None)
            self.assertFalse(PN.enabled())
            self.assertIsNone(PN.gather_page_claim_names(NoLog(), PWS, [], {}, pagemap([box(0, 0, 1, 1)])))

    def test_an_existing_arc_claim_takes_part_in_the_order_but_is_not_filed_again(self):
        pm = pagemap([box(10, 10, 30, 60), box(40, 10, 60, 60)])
        log = Log()
        log.observe(R.staff(0, 0, 0), Q.CLAIMED_AREA, [[0, 3]], reader=READERS.CV_CLAIMED_REGISTER, frame="page", owner="arc", unit="ink",
                    standing="READ", source="system_arc", page_strokes=[0, 1])
        area(log, "clef", [0, 0, 35, 70])
        run(log, pm)
        rows = named(log)
        self.assertEqual([r.detail["owner"] for r in rows], ["clef"])    # the arc row is not re-filed; the clef (layer 2) beat it to stroke 0
        census = [r for r in log.rows(Q.CLAIMED_AREA, R.page(0), scope=R.Scope.SELF_AND_DESCENDANTS) if (r.detail or {}).get("unit") == PN.UNIT_CENSUS][0]
        self.assertEqual(census.detail["by_owner"]["arc"]["contested"], 1)


class StepZeroTheBeamReaderSkipsNamedStrokes(unittest.TestCase):
    SP = 20.0

    def views(self):
        sp = self.SP
        a = StrokeView(ordinal=0, kind="vertical", box=(98.5, 100, 3.0, 60), length=3.0, thickness=0.15, sagitta=None, angle=90.0, touches=((2, 1.0),),
                       space_px=sp, ends=(100, 100, 100, 160))
        b = StrokeView(ordinal=1, kind="vertical", box=(198.5, 100, 3.0, 60), length=3.0, thickness=0.15, sagitta=None, angle=90.0, touches=((2, 1.0),),
                       space_px=sp, ends=(200, 100, 200, 160))
        beam = StrokeView(ordinal=2, kind="horizontal", box=(98.5, 99.5, 103.0, 13.0), length=5.15, thickness=0.65, sagitta=0.0, angle=0.0,
                          touches=((0, 1.0), (1, 1.0)), space_px=sp, ends=(98.5, 106, 201.5, 106))
        return [a, b, beam], [dict(box=a.box, row="s0"), dict(box=b.box, row="s1")]

    def test_unclaimed_it_is_a_beam(self):
        vs, st = self.views()
        self.assertEqual([x["role"] for x in PB.read_page(vs, st, self.SP)["beams"]], ["beam"])

    def test_named_by_an_earlier_claim_it_is_no_beam_and_the_census_says_whose(self):
        vs, st = self.views()
        res = PB.read_page(vs, st, self.SP, claimed={2: "arc"})
        self.assertEqual(res["beams"], [])
        self.assertEqual(res["census"]["claimed_not_read"], {"arc": 1})
        self.assertTrue(all(len(t["beams"]) == 0 for t in res["tips"]))

    def test_claim_order_names_the_owner_not_row_order(self):
        class L(Log):
            pass
        log = Log()
        for owner, ids in (("arc", [2]), ("clef", [2])):
            log.observe(R.staff(0, 0, 0), Q.CLAIMED_AREA, ids, reader=READERS.CV_CLAIMED_REGISTER, frame="page", owner=owner, unit="page_ink",
                        standing="READ", source="page_names", page_strokes=ids)
        vs, st = self.views()
        pm = SimpleNamespace(strokes=[SimpleNamespace(box=v.box, kind=v.kind, length_sp=v.length, thickness_sp=v.thickness, sagitta_sp=None,
                                                      angle_deg=v.angle, touches=v.touches, staff_space_local=self.SP, profile=(), ends=((v.ends[0], v.ends[1]), (v.ends[2], v.ends[3])))
                                      for v in vs], sp=self.SP, staff_of=[(0, 0)] * 3)
        with mock.patch.dict(os.environ, {PB.ENV: "1"}):
            res = PB.gather_page_beams(log, PWS, [], {}, pm, None)
        self.assertEqual(res["census"]["claimed_not_read"], {"clef": 1})      # layer 2 (clef) outranks layer 4 (arc) although its row stands second


if __name__ == "__main__":
    unittest.main()
