"""ROADMAP 2.305 r9: the page arc pass stands alone (flag `OMR_PAGE_ARC_WRITE` ON). STAGED. Controls built from REAL marks Sean judged on his fully swept
Brahms page 0 (`data/hand-truth/pages/imslp317803/0.json` + his page-pass arc labels): the numbers below are the r9 gather's own rows (page pixels), copied
unchanged -- never a drawing.

  far_side_ends   page-facts "an arc is OVER its notes". YES: his tie P195 (cup under staff 5's low notes, run obs:029092) lies nearer staff 6; the notes the
                  binder names for both ends (6/1/2, 6/2/5) stand wholly BELOW the cup -> both ends are far-side ends (bind on staff 5: the written tie
                  5/1/2 -> 5/2/5 he labelled). YES: his slur P205 (cap over staff 9, run obs:029055) -- left end "nearer note on another staff", right end's
                  staff-8 note (8/4/2) wholly ABOVE the cap. NEVER: the same P195 cup end with staff 5's own note (5/1/2) above it is this staff's end.
  _heads_under_the_arc   page-facts (Sean 2026-10-29) "spanning multiple notes is always slur". YES: his slur P179 (run obs:029017, under six repeated
                  notes of staff 4): the four heads between stand above the line joining the cup's ends. NEVER: a head of the staff below (5/0/9), which a
                  cup over staff 4's notes does not span.
  _place_arcs     NO OLD READER BESIDE THE NEW ONE (Sean 2026-11-13): the old box path wrote his P179 slur a second time from box 4/0/1 (the page pass had
                  abstained on that ink). With the flag ON a box no reading of ours bound writes nothing; OFF, the old path is unchanged.
  _retire_old_tie_pairs  a tie pair made by the old box rule is dropped with the flag ON; a pair a curve binding traced (`paired_by_page_binding`) stays.
  _page_bound_slur_spans  north star (all ink accounted for one time): his slur P162 (staff 1) read by two detector curves (0/6/5 from staff 0's cell,
                  1/6/5 from staff 1's) bound to the SAME two notes 1/6/3 -> 1/6/2 was written twice; now once. The OFF reader is unchanged.
"""
from __future__ import annotations

import collections

import pytest

from tools.omr.staged import export as SX
from tools.omr.staged import page_arc_bind as PB
from tools.omr.staged.adjudicators import ownership as OW
from tools.omr.staged.record import Q

# --- the r9 gather's own boxes (Brahms 317803 p0, 600 dpi), [x0, y0, x1, y1]
BOX = {
    "glyph/0/0/6/1/2": [2229.76, 3937.76, 2271.36, 3974.88],
    "glyph/0/0/6/2/5": [2712.28, 3970.72, 2754.52, 4007.84],
    "glyph/0/0/5/1/2": [2229.12, 3742.36, 2271.04, 3781.08],
    "glyph/0/0/8/4/2": [3616.4, 4718.04, 3661.2, 4754.84],
    "glyph/0/0/4/0/6": [1649.0, 3241.0, 1696.1, 3279.7],
    "glyph/0/0/4/0/7": [1717.8, 3241.8, 1759.6, 3279.7],
    "glyph/0/0/4/0/9": [1782.7, 3241.4, 1825.4, 3279.3],
    "glyph/0/0/4/0/10": [1855.9, 3241.4, 1895.5, 3279.7],
    "glyph/0/0/4/0/5": [1945.6, 3241.4, 1985.7, 3279.3],
    "glyph/0/0/4/0/8": [2017.5, 3241.0, 2059.7, 3280.2],
    "glyph/0/0/5/0/9": [1651.6, 3741.4, 1694.3, 3780.2],
    "glyph/0/0/1/6/3": [4711.15625, 1918.96875, 4755.5, 1956.09375],
    "glyph/0/0/1/6/2": [5276.625, 1949.21875, 5316.84375, 1986.0],
}
# the runs' ink ends as the binder reads them (`page_arc_bind.curve_detail`)
P195 = {"x_left_page": 2274.0, "y_left_page": 3781.0, "x_right_page": 2726.0, "y_right_page": 3794.0}
P205 = {"x_left_page": 2750.0, "y_left_page": 5003.0, "x_right_page": 3480.0, "y_right_page": 4989.0}
P179 = {"x_left_page": 1662.0, "y_left_page": 3280.0, "x_right_page": 2038.0, "y_right_page": 3297.0}


def _cont(key):
    return {"unbound": "continues_in_another_curve", "candidates": [key], "margin_spaces": None}


class TestFarSideEnds:
    def test_yes_his_tie_p195_cup_nearer_staff_6(self):
        b = {"side": "below", "left": _cont("glyph/0/0/6/1/2"), "right": _cont("glyph/0/0/6/2/5")}
        assert PB.far_side_ends(b, P195, BOX.get) == ["left", "right"]

    def test_yes_his_slur_p205_cap_nearer_staff_8(self):
        b = {"side": "above", "left": {"unbound": "nearer_note_on_another_staff", "candidates": ["glyph/0/0/9/2/4"]},
             "right": _cont("glyph/0/0/8/4/2")}
        assert sorted(PB.far_side_ends(b, P205, BOX.get)) == ["left", "right"]

    def test_never_a_cup_end_under_its_own_note(self):
        b = {"side": "below", "left": _cont("glyph/0/0/5/1/2"), "right": _cont("glyph/0/0/6/2/5")}
        assert PB.far_side_ends(b, P195, BOX.get) == ["right"]          # one end only: no second binding

    def test_never_without_a_side(self):
        b = {"side": None, "left": _cont("glyph/0/0/6/1/2"), "right": _cont("glyph/0/0/6/2/5")}
        assert PB.far_side_ends(b, P195, BOX.get) == []


def _heads(keys):
    out = {}
    for k in keys:
        x0, y0, x1, y1 = BOX[k]
        out[k] = {"key": k, "cx": (x0 + x1) / 2.0, "cy": (y0 + y1) / 2.0, "w": x1 - x0, "h": y1 - y0}
    return out


class TestSamePitchNotesUnderTheArc:
    BETWEEN = ["glyph/0/0/4/0/7", "glyph/0/0/4/0/9", "glyph/0/0/4/0/10", "glyph/0/0/4/0/5"]

    def test_yes_his_slur_p179_six_repeated_notes(self):
        assert OW._heads_under_the_arc(self.BETWEEN, _heads(self.BETWEEN), P179, "below")

    def test_never_a_head_the_cup_does_not_span(self):
        keys = self.BETWEEN + ["glyph/0/0/5/0/9"]
        assert not OW._heads_under_the_arc(keys, _heads(keys), P179, "below")

    def test_never_the_wrong_side(self):
        assert not OW._heads_under_the_arc(self.BETWEEN, _heads(self.BETWEEN), P179, "above")


class _Rec:
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


def _p179_record():
    """his P179's ink: the page run abstained (`same_pitch_heads_between` before r9) and witnessed by box 4/0/1; a written run elsewhere on the page."""
    runs = [dict(row="obs:029017", status="abstained", why="same_pitch_heads_between", witnesses=["glyph/0/0/4/0/1"]),
            dict(row="obs:029018", status="written", kind="slur", start="glyph/0/0/13/0/13", stop="glyph/0/0/13/0/17", witnesses=["glyph/0/0/13/0/16"])]
    v = [{"id": "vrd:1", "subject": "page/0", "quantity": Q.PAGE_ARC_BINDING, "outcome": "decided", "value": {}, "detail": {"runs": runs}},
         {"id": "vrd:2", "subject": "glyph/0/0/4/0/1", "quantity": Q.ARC_KIND, "outcome": "decided", "value": "slur", "reason": "slur", "detail": {}}]
    obs = [{"id": "obs:1", "subject": "glyph/0/0/4/0/1", "quantity": Q.ARC_BOX, "value": "slur",
            "detail": {"bbox_page_px": [1673.83984375, 3283.646484375, 2038.828125, 3331.9921875]}}]
    return _Rec(obs, v)


class TestTheOldBoxPathIsRetired:
    def test_on_the_box_no_reading_of_ours_bound_writes_nothing(self, monkeypatch):
        monkeypatch.setenv(PB.ENV_WRITE, "1")
        dropped = SX._place_arcs(_p179_record(), {})
        assert dropped.get("old_box_path_retired") == 1

    def test_off_the_old_path_is_unchanged(self, monkeypatch):
        monkeypatch.delenv(PB.ENV_WRITE, raising=False)
        dropped = SX._place_arcs(_p179_record(), {})
        assert "old_box_path_retired" not in dropped
        assert dropped.get("arc_owner_staff_has_no_measures") == 1          # placed by the old path (no staff run in this stub)


class TestTheOldTiePairingIsRetired:
    def test_a_box_pairing_is_dropped_and_a_traced_one_kept(self):
        rt = {"pairs": {("glyph/0/0/5/0/13", "glyph/0/0/5/1/16"): ["glyph/0/0/5/0/17"],
                        ("glyph/0/0/13/4/2", "glyph/0/0/13/5/0"): ["glyph/0/0/13/5/2"]},
              "reasons": {("glyph/0/0/5/0/13", "glyph/0/0/5/1/16"): {"paired_by_page_binding"},
                          ("glyph/0/0/13/4/2", "glyph/0/0/13/5/0"): {"paired"}}}
        assert SX._retire_old_tie_pairs(rt) == 1
        assert list(rt["pairs"]) == [("glyph/0/0/5/0/13", "glyph/0/0/5/1/16")]       # his tie P180, traced by a curve


def _measures():
    dets = []
    for k in ("glyph/0/0/1/6/3", "glyph/0/0/1/6/2"):
        x0, y0, x1, y1 = BOX[k]
        dets.append({"glyph": k, "category": "notehead", "bbox_page": [x0, y0, x1 - x0, y1 - y0]})
    return [{"detections": dets, "bbox_page_px": None}]


class TestOnePrintedSlurIsWrittenOnce:
    BOUND = {"glyph/0/0/0/6/5": {"start": "glyph/0/0/1/6/3", "stop": "glyph/0/0/1/6/2", "pieces": 1},
             "glyph/0/0/1/6/5": {"start": "glyph/0/0/1/6/3", "stop": "glyph/0/0/1/6/2", "pieces": 1}}

    def _spans(self):
        counters = collections.Counter()
        out = SX._page_bound_slur_spans(_measures(), dict(self.BOUND), {}, set(), set(), counters)
        return out, counters

    def test_on_two_readings_of_his_p162_are_one_slur(self, monkeypatch):
        monkeypatch.setenv(PB.ENV_WRITE, "1")
        out, counters = self._spans()
        assert len(out) == 1
        assert counters["slur_bound_same_two_notes_as_another_reading"] == 1

    def test_off_unchanged(self, monkeypatch):
        monkeypatch.delenv(PB.ENV_WRITE, raising=False)
        out, _ = self._spans()
        assert len(out) == 2
