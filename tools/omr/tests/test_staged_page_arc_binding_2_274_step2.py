"""ROADMAP 2.274 step 2 (`OMR_PAGE_ARC_WRITE`, default OFF): the witnessed page-ink arc runs bound to notes and written, one arc each.

The binder is 2.223's (`ownership._page_binding(page_run=...)`) with 2.271's closest-note rule for an end that stops short; the new parts are the run -> curve detail, the page-wide
decision `adjudicate_page_arc_binding` and the exporter's plan (one mark, one arc). Every guard has a twin that fails without it.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import arc_claim as AC
from tools.omr.staged import export as SX
from tools.omr.staged import page_arc_bind as PB
from tools.omr.staged import page_arcs as PA
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

from .test_staged_tie_pair import _arc, _cells, _head

SP = 10.0


def _h(key, cx, cy, w=12.0, h=10.0):
    return {"key": key, "cx": cx, "cy": cy, "w": w, "h": h, "cell": 0}


def _detail(xl, yl, xr, yr, sag=-15.0):
    tr = []
    for x in range(int(xl), int(xr) + 1, 2):
        f = (x - xl) / float(xr - xl)
        tr.append([x, yl + f * (yr - yl) + sag * 4 * f * (1 - f) - 1, yl + f * (yr - yl) + sag * 4 * f * (1 - f) + 1])
    return {"space_page_px": SP, "x_left_page": xl, "y_left_page": yl, "x_right_page": xr, "y_right_page": yr, "trace": tr}


class TestTheFlag(unittest.TestCase):
    def test_default_off_and_allow_list(self):
        import os
        old = os.environ.pop(PB.ENV_WRITE, None)
        try:
            self.assertFalse(PB.write_enabled())
            for v, want in (("1", True), ("on", True), ("0", False), ("", False), ("typo", False)):
                os.environ[PB.ENV_WRITE] = v
                self.assertEqual(PB.write_enabled(), want, v)
        finally:
            os.environ.pop(PB.ENV_WRITE, None)
            if old is not None:
                os.environ[PB.ENV_WRITE] = old

    def test_it_turns_the_step_one_reader_on(self):
        import os
        old = {k: os.environ.pop(k, None) for k in (PB.ENV_WRITE, PA.ENV)}
        try:
            self.assertFalse(PA.enabled())
            os.environ[PB.ENV_WRITE] = "1"
            self.assertTrue(PA.enabled())
        finally:
            for k, v in old.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v


class TestTheRunIsACurve(unittest.TestCase):
    def test_detail_has_the_ends_and_a_trace(self):
        run = dict(ends=[[0.0, 100.0, 10.0], [100.0, 100.0, -10.0]], points=[[0, 100], [50, 90], [100, 100]], thickness_spaces=0.3)
        d = PB.curve_detail(run, SP)
        self.assertEqual((d["x_left_page"], d["x_right_page"]), (0.0, 100.0))
        self.assertEqual(len(d["trace"]), 3)
        run2 = dict(run, points=[[x, 100 - 15 * 4 * (x / 100.0) * (1 - x / 100.0)] for x in range(0, 101, 10)])
        self.assertEqual(AC.curve_side(PB.curve_detail(run2, SP)["trace"], SP), "above")          # the middle is HIGHER than the chord: a cap, drawn over its notes
        self.assertIsNone(PB.curve_detail(dict(run, ends=None), SP))
        self.assertIsNone(PB.curve_detail(run, 0.0))


class TestClosestNote(unittest.TestCase):
    def test_an_end_that_stops_short_binds_the_closest_head_and_the_twin_does_not(self):
        d = _detail(0, 100, 100, 100)
        heads = [_h("a", -5, 108), _h("b", 130, 108)]          # b stands 3 spaces past the run's end: outside the 1.6-space window
        plain = AC.bind_curve(d, heads, SP)
        self.assertEqual(plain["right"].get("unbound"), "no_head_at_end")          # the twin: 2.223's window alone
        b = PB.closest_binder({"left": [], "right": []})(heads, SP, None, True, None, d)
        self.assertEqual((b["left"]["head"], b["right"]["head"]), ("a", "b"))
        self.assertTrue(b["right"].get("via_closest"))

    def test_two_heads_about_equally_near_abstain_never_a_pick(self):
        d = _detail(0, 100, 100, 100)
        heads = [_h("a", -5, 108), _h("c1", 128, 108), _h("c2", 140, 108)]          # 28 and 40 px: a head width apart, inside the 0.5-space column margin? no: two columns
        b = PB.closest_binder({"left": [], "right": []})(heads, SP, None, True, None, d)
        # the closest column wins by more than the margin here ...
        self.assertEqual(b["right"]["head"], "c1")
        # ... and two columns inside the margin do not: 0.3 spaces apart
        heads2 = [_h("a", -5, 108), _h("c1", 128, 108), _h("c2", 135.5, 100)]          # two columns (7.5 px apart), 36.0 and 35.5 px from the end
        b2 = PB.closest_binder({"left": [], "right": []})(heads2, SP, None, True, None, d)
        self.assertIn(b2["right"].get("unbound"), ("two_columns_at_end", "chord_end_equidistant"))

    def test_the_half_of_an_arc_leaves_the_end_unbound(self):
        d = _detail(0, 100, 100, 100)
        heads = [_h("a", -5, 108), _h("far", 190, 108)]
        # another run of the staff BEGINS 2 px past this one's right end, nearer than the closest head (90 px away)
        b = PB.closest_binder({"left": [], "right": [(104.0, 100.0)]})(heads, SP, None, True, None, d)
        self.assertEqual(b["right"].get("unbound"), "continues_in_another_curve")
        b2 = PB.closest_binder({"left": [], "right": []})(heads, SP, None, True, None, d)          # the twin: nothing begins there
        self.assertEqual(b2["right"]["head"], "far")

    def test_facing_ends_come_from_the_other_runs_of_the_same_staff_only(self):
        runs = [dict(ends=[[0, 0, 0], [50, 0, 0]], staff=[0, 1]), dict(ends=[[60, 5, 0], [120, 5, 0]], staff=[0, 1]), dict(ends=[[55, 9, 0], [90, 9, 0]], staff=[0, 2])]
        f = PB.facing_ends(runs, 0, [0, 1])
        self.assertEqual(f["right"], [(60.0, 5.0)])          # the same-staff run that begins at 60; the other staff's is not
        self.assertEqual(f["left"], [(120.0, 5.0)])


def _scene(heads, run_ends, run_pts, witnesses=True, cls="tie", staff=(0, 0)):
    log = Log()
    _cells(log, 4)
    hs = [_head(log, c, gi, x, y) for (c, gi, x, y) in heads]
    w = None
    if witnesses:
        w = _arc(log, 0, 9, run_pts[0][0], run_pts[-1][0], y0=run_pts[0][1] - 5, y1=run_pts[0][1] + 5, cls=cls)
    log.observe(R.page(0), Q.PAGE_ARC, "run", reader=READERS.CV_PAGE_ARCS, frame="page", score=None, ordinal=0, points=run_pts, ends=run_ends,
                width_spaces=10.0, sagitta_spaces=-1.0, thickness_spaces=0.3, witnesses=[w.to_key()] if w is not None else [], staff=list(staff),
                space_page_px=SP, bbox_page_px=[run_pts[0][0], run_pts[0][1] - 10, run_pts[-1][0], run_pts[0][1] + 10], page_strokes=[])
    return log, hs, w


def _run(log, monkey_flag=True):
    import os
    old = os.environ.get(PB.ENV_WRITE)
    if monkey_flag:
        os.environ[PB.ENV_WRITE] = "1"
    try:
        log.freeze()
        adjudicate.run(log, order=(Q.PAGE_ARC_BINDING,))
    finally:
        os.environ.pop(PB.ENV_WRITE, None)
        if old is not None:
            os.environ[PB.ENV_WRITE] = old
    return log.verdict(Q.PAGE_ARC_BINDING, R.page(0))


PTS = [[float(x), 100.0 - 5.0 * 4 * ((x - 55.0) / 90.0) * (1 - (x - 55.0) / 90.0)] for x in range(55, 146, 10)]          # dense, as the reader's thinned points are (round 2 cuts a run at a gap of 2 spaces)
ENDS = [[55.0, 100.0, 10.0], [145.0, 100.0, -10.0]]


class TestTheDecision(unittest.TestCase):
    def test_a_witnessed_run_over_two_heads_at_one_position_is_a_tie(self):
        log, hs, w = _scene([(0, 0, 40.0, 100.0), (0, 1, 140.0, 100.0)], ENDS, PTS)
        v = _run(log)
        self.assertIsNotNone(v)
        (r,) = v.detail["runs"]
        self.assertEqual((r["status"], r["kind"]), ("written", "tie"), r)
        self.assertEqual((r["start"], r["stop"]), (hs[0].to_key(), hs[1].to_key()))
        self.assertEqual(r["witnesses"], [w.to_key()])

    def test_two_positions_is_a_slur_and_the_detector_class_is_no_input(self):
        for cls in ("tie", "slur"):
            log, hs, w = _scene([(0, 0, 40.0, 100.0), (0, 1, 140.0, 80.0)], ENDS, PTS, cls=cls)
            (r,) = _run(log).detail["runs"]
            self.assertEqual((r["status"], r["kind"]), ("written", "slur"), (cls, r))
        log, hs, w = _scene([(0, 0, 40.0, 100.0), (0, 1, 140.0, 100.0)], ENDS, PTS, cls="slur")
        (r,) = _run(log).detail["runs"]
        self.assertEqual(r["kind"], "tie")          # the detector said slur; the heads say one position

    def test_a_run_no_detector_box_witnesses_is_not_written(self):
        log, hs, w = _scene([(0, 0, 40.0, 100.0), (0, 1, 140.0, 100.0)], ENDS, PTS, witnesses=False)
        v = _run(log)
        self.assertEqual(v.reason, "no_witnessed_run")
        (r,) = v.detail["runs"]
        self.assertEqual(r["status"], PB.NOT_WITNESSED)

    def test_an_end_that_stops_short_is_bound_to_the_closest_head(self):
        log, hs, w = _scene([(0, 0, 40.0, 100.0), (0, 1, 175.0, 100.0)], ENDS, PTS)          # the right head is 3+ spaces past the run's end
        (r,) = _run(log).detail["runs"]
        self.assertEqual(r["status"], "written")
        self.assertEqual(r["closest"], ["right"])

    def test_the_decision_files_nothing_with_the_flag_off(self):
        log, hs, w = _scene([(0, 0, 40.0, 100.0), (0, 1, 140.0, 100.0)], ENDS, PTS)
        self.assertIsNone(_run(log, monkey_flag=False))

    def test_no_head_at_an_end_anywhere_is_a_system_edge_and_is_offered_to_the_join(self):
        log, hs, w = _scene([(0, 0, 40.0, 100.0)], ENDS, PTS)          # nothing beyond the right end
        (r,) = _run(log).detail["runs"]
        self.assertEqual(r["status"], "abstained")
        self.assertEqual((r["why"], r["edge"], r["edge_head"]), ("system_edge", "right", hs[0].to_key()))

    def test_an_unreadable_pair_abstains_and_says_why(self):
        log, hs, w = _scene([(0, 0, 40.0, 100.0), (0, 1, 90.0, 100.0), (0, 2, 140.0, 100.0)], ENDS, PTS)          # one pitch with a head between: not a tie, not claimed a slur
        (r,) = _run(log).detail["runs"]
        self.assertEqual((r["status"], r["why"]), ("abstained", "same_pitch_heads_between"))


class TestThePlan(unittest.TestCase):
    def _runs(self):
        return {"runs": [
            dict(row="a", status="written", kind="tie", start="s", stop="t", witnesses=["box/1", "box/2"]),
            dict(row="b", status="written", kind="slur", start="u", stop="v", witnesses=["box/3"]),
            dict(row="c", status="abstained", why="x", witnesses=["box/3", "box/4"]),
            dict(row="d", status="abstained", why="system_edge", edge="right", edge_head="h", witnesses=["box/5"]),
            dict(row="e", status="not_witnessed", witnesses=[])]}

    def test_a_box_all_of_whose_runs_are_written_is_replaced(self):
        p = PB.plan_of([self._runs()])
        self.assertEqual(p["replaced"], {"box/1", "box/2"})

    def test_a_box_shared_with_an_unwritten_run_keeps_its_old_arc(self):
        p = PB.plan_of([self._runs()])
        self.assertEqual(p["shared_kept"], {"box/3"})
        self.assertNotIn("box/3", p["replaced"])

    def test_edges_and_counts(self):
        p = PB.plan_of([self._runs()])
        self.assertEqual([r["row"] for r in p["edges"]], ["d"])
        self.assertEqual(p["counts"], {"written": 2, "abstained": 2, "not_witnessed": 1})


class _Rec:
    """The least of an export `Record` that `_place_arcs` / `_page_arc_plan` read."""

    def __init__(self, obs, verdicts):
        self._obs, self._vs = obs, verdicts

    def obs_of(self, q):
        return [o for o in self._obs if o["quantity"] == q]

    def verdicts_of(self, q):
        return [v for v in self._vs if v["quantity"] == q]

    def verdict(self, q, sub):
        for v in self._vs:
            if v["quantity"] == q and v["subject"] == sub:
                return v
        return None

    def value(self, q, sub):
        v = self.verdict(q, sub)
        return None if v is None or v["outcome"] != "decided" else v["value"]


class TestTheExportPlan(unittest.TestCase):
    def _rec(self):
        detail = {"runs": [dict(row="a", status="written", kind="tie", start="s", stop="t", witnesses=["glyph/0/0/0/0/9"])]}
        v = {"id": "vrd:1", "subject": "page/0", "quantity": Q.PAGE_ARC_BINDING, "outcome": "decided", "value": {}, "detail": detail}
        obs = [{"id": "obs:1", "subject": "glyph/0/0/0/0/9", "quantity": Q.ARC_BOX, "value": "tie", "detail": {"bbox_page_px": [0, 0, 10, 10]}},
               {"id": "obs:2", "subject": "glyph/0/0/0/0/8", "quantity": Q.ARC_BOX, "value": "tie", "detail": {"bbox_page_px": [0, 0, 10, 10]}}]
        return _Rec(obs, [v])

    def test_off_reads_nothing(self):
        import os
        os.environ.pop(PB.ENV_WRITE, None)
        self.assertIsNone(SX._page_arc_plan(self._rec()))

    def test_on_the_plan_replaces_the_witnessing_box_and_only_that(self):
        import os
        os.environ[PB.ENV_WRITE] = "1"
        try:
            rec = self._rec()
            self.assertEqual(SX._page_arc_plan(rec)["replaced"], {"glyph/0/0/0/0/9"})
            dropped = SX._place_arcs(rec, {})
            self.assertEqual(dropped.get("replaced_by_page_arc"), 1)
            self.assertNotIn("replaced_by_page_arc", SX._place_arcs.__doc__ or "")
        finally:
            os.environ.pop(PB.ENV_WRITE, None)
        dropped_off = SX._place_arcs(self._rec(), {})
        self.assertNotIn("replaced_by_page_arc", dropped_off)          # the twin: flag off, the box is placed (here: counted for having no owner staff)


if __name__ == "__main__":
    unittest.main()
