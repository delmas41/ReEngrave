"""ROADMAP 1.7 (stems): the CV stem source and the per-head attachment in the hand-truth scorer.

SYNTHETIC page, synthetic record: nothing here reads a score, a weights file or the library, so this file stays in
the fast tier (CLAUDE.md §6c).

Rule 7: a control that has only ever passed has proved nothing. ``TestEachStemControlCanFail`` seeds the bug each
control exists to catch into the scorer (a matcher that ignores the column, a tolerance widened until a stem pairs
with its neighbour, a scorer that forgets the canonical-to-page conversion, an attachment judge that always says
"right" ...) and requires the control to go RED. Every refusal sits beside a positive control of its own class.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from tools.omr.hand_truth import score as S
from tools.omr.hand_truth import score_controls as C
from tools.omr.hand_truth import score_stems as SS
from tools.omr.tests.test_hand_truth_score import BAR_W, SP, STAVES, _top, synth_truth


@pytest.fixture(scope="module")
def page():
    return synth_truth()


@pytest.fixture(scope="module")
def items(page):
    return S.truth_items(page, derive=True)


def stem_report(page, items, **kw):
    kw.setdefault("up", C.STEM_CONTROL_UP)
    return S.score(page, C.run_of(C.synthetic_result(page, items, **kw)), derive=True, items=items, trained_cells=())


# ─────────────────────────────────────────────────────────────────────────────
# the CV source: Q.STEM in the cell's canonical frame -> page pixels
# ─────────────────────────────────────────────────────────────────────────────


class TestCvStemsInPagePixels:
    def test_the_factor_is_read_back_from_the_detector_boxes_and_the_stems_land_on_the_truth(self, page, items):
        run = C.run_of(C.synthetic_result(page, items, up=2.5))
        cv = SS.read_cv_stems(run, 0)
        truth = [it for it in items if it.family == "stem"]
        assert cv.ran and len(cv.stems) == len(truth) == STAVES * 3 and cv.declined == 0
        by_cell = {}
        for t in truth:
            by_cell.setdefault(t.cell_id, t)
        for st in cv.stems:
            assert abs(st.up - 2.5) < 1e-9
            t = next(x for x in truth if tuple(x.rect) == pytest.approx(st.rect, abs=1e-6))
            assert t is not None

    def test_a_scorer_that_forgot_the_conversion_would_misplace_every_stem(self, page, items, monkeypatch):
        """Positive control of the same class: with the factor forced to 1 the stems are NOT where the truth is."""
        run = C.run_of(C.synthetic_result(page, items, up=2.5))
        good = {tuple(round(v, 3) for v in st.rect) for st in SS.read_cv_stems(run, 0).stems}
        real = SS.cell_frames
        monkeypatch.setattr(SS, "cell_frames", lambda r, p: ({k: (1.0, "forced") for k in real(r, p)[0]},
                                                             real(r, p)[1], real(r, p)[2]))
        bad = {tuple(round(v, 3) for v in st.rect) for st in SS.read_cv_stems(run, 0).stems}
        assert good != bad

    def test_a_row_in_a_cell_with_no_measurable_frame_is_declined_and_counted_never_dropped_silently(self, page, items):
        res = C.synthetic_result(page, items, up=1.0)
        # a Q.STEM row on a cell that holds no detector box and no staff space: the factor cannot be measured
        res["record"]["observations"].append({
            "id": "obs:zz1", "subject": "cell/0/0/0/99", "quantity": "stem", "value": [10, 10, 5, 100],
            "reader": "cv_lines", "frame": "cell:99", "score": None, "detail": {}, "basis": []})
        cv = SS.read_cv_stems(C.run_of(res), 0)
        assert cv.declined == 1 and cv.ran

    def test_the_two_ways_of_measuring_the_factor_agree_or_the_cell_is_distrusted(self, page, items):
        """Positive control: a record that carries only the detector boxes is measured one way; the cross-check
        needs the staff-space pair, which the synthetic record does not file -- and says so."""
        run = C.run_of(C.synthetic_result(page, items, up=2.5))
        _frames, info, _sp = SS.cell_frames(run, 0)
        assert info["cells_with_a_factor"] > 0 and info["cells_checked_two_ways"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# matching: column + vertical overlap, not IoU
# ─────────────────────────────────────────────────────────────────────────────


def _it(idx, rect, family="stem", cell="c"):
    return S.TruthItem(idx=idx, id=f"t{idx}", cls=family, family=family, rect=tuple(rect), origin="drawn", cell_id=cell)


def _cv(idx, rect):
    return SS.CvStem(idx, f"obs:{idx}", (0, 0, 0), tuple(rect), (0, 0, 0, 0), 1.0, SP)


class TestColumnMatching:
    def test_a_thin_stem_two_pixels_off_is_the_same_stem_though_its_iou_is_below_the_matcher_threshold(self):
        t = _it(0, (100, 0, 104, 80))
        c = _cv(0, (102.5, 0, 106.5, 80))
        assert S._iou(t.rect, c.rect) < S.MIN_IOU  # box IoU would call this a miss: it is a 7-pixel mark
        m = SS.match_stems([t], [c], {0: SP})
        assert m.found == [0] and m.valid == [0]

    def test_one_head_width_to_the_side_is_NOT_the_same_stem(self):
        t = _it(0, (100, 0, 104, 80))
        c = _cv(0, (100 + 1.3 * SP, 0, 104 + 1.3 * SP, 80))
        m = SS.match_stems([t], [c], {0: SP})
        assert m.found == [] and m.invented == [0] and m.missed == [0]

    def test_the_tolerance_sits_inside_the_empty_interval_of_the_data(self):
        # measured 2026-10-10 on Brahms 317803 pdf 0: nothing between 0.15 and 0.40 spaces, neighbours >= 1.57 apart
        assert 0.15 < SS.STEM_MATCH_DX_SPACES < 0.40 < 1.57

    def test_a_cv_stem_that_covers_under_half_of_the_truth_stem_is_a_fragment_not_a_find(self):
        t = _it(0, (100, 0, 104, 100))
        m = SS.match_stems([t], [_cv(0, (100, 0, 104, 40))], {0: SP})
        assert m.found == [] and m.in_column[0] == [0] and m.cover_t[0] == pytest.approx(0.4)
        full = SS.match_stems([t], [_cv(0, (100, 0, 104, 40)), _cv(1, (100, 40, 104, 100))], {0: SP})
        assert full.found == [0]  # positive control: two pieces that together cover it ARE a find

    def test_two_cv_rows_on_one_stem_are_one_find_and_not_an_invention(self):
        t = _it(0, (100, 0, 104, 100))
        m = SS.match_stems([t], [_cv(0, (100, 0, 104, 100)), _cv(1, (101, 2, 105, 98))], {0: SP})
        assert m.found == [0] and m.invented == [] and SS.view(m)["truth_stems_with_more_than_one_cv_row"] == 1

    def test_a_long_cv_run_through_a_short_truth_stem_is_not_valid_unless_truth_covers_it(self):
        t = _it(0, (100, 40, 104, 60))
        m = SS.match_stems([t], [_cv(0, (100, 0, 104, 200))], {0: SP})
        assert m.valid == [] and m.invented == [0]


# ─────────────────────────────────────────────────────────────────────────────
# the scored report: sources side by side, scope, refusal
# ─────────────────────────────────────────────────────────────────────────────


class TestStemReport:
    def test_the_detector_class_number_and_the_cv_number_are_reported_separately(self, page, items):
        # the detector-class stems are the truth's own boxes here (recall 1), the CV reader found only some
        rep = stem_report(page, items, cv_drop={it.idx for it in items if it.family == "stem"
                                                and it.cell_id.endswith("m0")})
        st = rep["stems"]
        assert st["detector_class"]["gather"]["recall"] == 1.0
        assert st["cv_stem"]["recall"] == pytest.approx(2 / 3, abs=1e-3)
        assert rep["families"]["stem"]["gather"]["recall"] == 1.0   # the existing family row is not touched
        assert st["either_source"]["found"] == st["either_source"]["truth"]

    def test_the_text_report_shows_both_and_the_per_staff_rows(self, page, items):
        txt = S.render(stem_report(page, items))
        assert "detector class `stem`" in txt and "CV stems (Q.STEM)" in txt and "stem (CV Q.STEM)" in txt
        assert "per staff" in txt and "STEMS PER HEAD" in txt

    def test_a_record_with_no_stem_row_and_no_abstention_is_refused_not_scored_zero(self, page, items):
        cv = stem_report(page, items, stem_reader_ran=False)["stems"]["cv_stem"]
        assert cv["status"].startswith("REFUSED")
        ran = stem_report(page, items, cv_stems=False)["stems"]["cv_stem"]  # positive control
        assert ran["status"] == "scored" and ran["recall"] == 0.0 and ran["precision"] is None

    def test_cv_stems_outside_the_fully_labeled_cells_are_unscored_not_invented(self, page, items):
        rep = stem_report(page, items)
        before = rep["stems"]["cv_stem"]["read"]
        # a stem drawn far from every cell: ``Scope`` holds no cell there, so it is counted as outside, not as invented
        far = ((5.0, 5.0, 8.0, 60.0), 0, 0, 0)
        res = C.synthetic_result(page, items, up=2.5, cv_spurious=[far])
        rep2 = S.score(page, C.run_of(res), derive=True, items=items, trained_cells=())
        assert rep2["stems"]["cv_stem"]["read"] == before
        assert rep2["stems"]["cv_stem"]["rows_outside_scored_cells"] == 1

    def test_invented_stems_say_what_lies_under_them(self, page, items):
        c = next(c for c in S.fully_labeled(page) if c.kind == "measure")
        clef = next(it for it in items if it.family == "clef" and it.cell_id == c.id)
        x, y0, _x1, y1 = clef.rect
        rep = S.score(page, C.run_of(C.synthetic_result(
            page, items, up=2.5, cv_spurious=[((x + 3, y0 + 4, x + 6, y0 + 4 + 3 * SP), c.system, c.staff, c.measure)])),
            derive=True, items=items, trained_cells=())
        assert rep["stems"]["cv_stem"]["invented_on"] == {"lies on a truth clef": 1}

    def test_the_report_is_json_safe(self, page, items):
        json.dumps(S.public(stem_report(page, items)), default=str)


# ─────────────────────────────────────────────────────────────────────────────
# per head
# ─────────────────────────────────────────────────────────────────────────────


class TestPerHead:
    def test_a_head_with_no_stem_box_is_not_judged_and_never_a_false_positive(self, page, items):
        h = stem_report(page, items)["stems"]["heads"]
        assert h["truth_heads_without_a_truth_stem"] == STAVES * 3 * 4   # the 3 other heads and the far head of each bar
        assert h["truth_heads_with_a_truth_stem"] == STAVES * 3
        assert h["attach"] == {"right": STAVES * 3}

    def test_the_head_with_a_stem_whose_cv_stem_was_dropped_is_counted_as_stem_not_found(self, page, items):
        drop = {it.idx for it in items if it.family == "stem" and it.cell_id == "s0-st0-m0"}
        h = stem_report(page, items, cv_drop=drop)["stems"]["heads"]
        assert h["attach"].get("abstained_stem_not_found") == 1 and h["attach"]["right"] == STAVES * 3 - 1
        assert any("stem not found by CV" in k for k in h["heads_without_the_right_stem_by_cause"])
        assert h["direction"].get("abstained") == 1

    def test_a_head_attached_to_another_stem_is_wrong_not_missing(self, page, items):
        h = stem_report(page, items, attach="swap")["stems"]["heads"]
        assert h["attach"].get("right", 0) == 0 and h["attach"]["wrong_other_stem"] == STAVES * 3

    def test_a_head_attached_to_a_stroke_that_is_not_a_stem_is_wrong_and_says_where_it_lies(self, page, items):
        """The 5 heads of the real page named the right rim of a stacked pair; here, a stroke on a clef."""
        c = next(c for c in S.fully_labeled(page) if c.id == "s0-st0-m0")
        h0 = next(it for it in items if it.family == "notehead" and it.cell_id == c.id and S._cy(it.rect) < _top(0) + 30)
        clef = next(it for it in items if it.family == "clef" and it.cell_id == c.id)
        res = C.synthetic_result(page, items, up=2.5, cv_drop={it.idx for it in items if it.family == "stem"
                                                              and it.cell_id == c.id},
                                 cv_spurious=[((clef.rect[0] + 3, clef.rect[1] + 5, clef.rect[0] + 6,
                                                clef.rect[1] + 5 + 3 * SP), 0, 0, 0)])
        run = C.run_of(res)
        # file a Q.HEAD_STEM verdict on h0 naming the stroke on the clef
        spur = next(o for o in res["record"]["observations"] if o["quantity"] == "stem"
                    and o["subject"] == "cell/0/0/0/0" and o["value"][2] < 10 * 2.5 and o["id"].startswith("obs:")
                    and abs(o["value"][0] - (clef.rect[0] + 3 - c.rect[0]) * 2.5) < 1e-6)
        for v in res["record"]["verdicts"]:
            if v["quantity"] == "head_stem" and v["decider"] == "adjudicate_head_stem" and v["value"] is None:
                v["outcome"], v["value"] = "decided", spur["id"]
        rep = S.score(page, C.run_of(res), derive=True, items=items, trained_cells=())
        heads = rep["stems"]["heads"]
        assert heads["attach"].get("wrong_invented_stem", 0) >= 1
        assert "lies on a truth clef" in heads["wrongly_attached_to"]

    def test_direction_flipped_is_wrong_and_ambiguous_truth_is_not_judged(self, page, items):
        h = stem_report(page, items, direction_flip=True)["stems"]["heads"]
        assert h["direction"].get("wrong") == STAVES * 3 and h["direction_right_of_judged"] == 0.0

    def test_truth_direction_is_ambiguous_where_the_side_rule_disagrees(self):
        head = (100, 100, 124, 120)
        down_left = (96, 105, 100, 170)      # extends below, stands left: down by both
        assert SS.truth_direction(head, down_left)[2] == "judged" and SS.truth_direction(head, down_left)[0] == "down"
        displaced = (124, 105, 128, 170)     # extends below but stands RIGHT of the head (a displaced second)
        assert SS.truth_direction(head, displaced)[2] == "ambiguous"
        up_right = (122, 40, 126, 108)
        assert SS.truth_direction(head, up_right)[:2] == ("up", "up")

    def test_duration_standing_and_reach_are_reported_without_a_judgement(self, page, items):
        h = stem_report(page, items)["stems"]["heads"]
        assert set(h["duration_standing_by_attach"]) == {"right stem", "no right stem"}
        assert h["reach_beside_the_head"]["heads_with_a_reach_row"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# the misses, by cause
# ─────────────────────────────────────────────────────────────────────────────


def _run(rect, outcome, frame=(0, 0, 0)):
    return {"rect": tuple(rect), "outcome": outcome, "frame": frame}


TOO_WIDE = "too WIDE (w > 0.6 spaces)"
PAIRED = "PAIRED with a neighbour (the accidental rule)"


class TestMissedStemCauses:
    def _missed(self, rect=(100, 0, 104, 100)):
        t = _it(0, rect)
        return SS.match_stems([t], [], {0: SP}), t

    def test_a_run_a_space_wide_and_centred_off_the_stem_is_still_the_runs_at_the_stems_column(self):
        """RED against the first version, which matched a run by the distance of its CENTRE: a stem fused with the
        head beside it is a run whose centre is half a space from the stem, and 45 of 54 misses read 'no run'."""
        m, t = self._missed()
        fused = _run((100, 0, 100 + 1.1 * SP, 100), TOO_WIDE)     # centre 0.55 spaces right of the stem
        assert SS.runs_at(t.rect, SP, [fused]) == [fused]
        out = SS.explain_missed(m, [t], {"runs": [fused]})
        assert out["by_cause"] == {"stem opening produced a run and refused it: too WIDE": 1}

    def test_the_centre_distance_version_misses_it_which_is_why_the_test_above_exists(self, monkeypatch):
        m, t = self._missed()
        fused = _run((100, 0, 100 + 1.1 * SP, 100), TOO_WIDE)
        monkeypatch.setattr(SS, "runs_at", lambda rect, sp, runs: [r for r in runs if SS._y_overlap(rect, r["rect"]) > 0
                                                                   and SS._same_column(rect, r["rect"], sp)])
        out = SS.explain_missed(m, [t], {"runs": [fused]})
        assert "produced no run" in next(iter(out["by_cause"]))

    def test_no_run_at_all_is_its_own_cause(self):
        m, t = self._missed()
        far = _run((900, 0, 904, 100), TOO_WIDE)
        out = SS.explain_missed(m, [t], {"runs": [far]})
        assert out["by_cause"] == {"the stem opening produced no run at its column": 1}

    def test_paired_names_the_strokes_the_pair_rule_saw_and_whether_they_are_stems(self):
        t = _it(0, (100, 0, 104, 100))
        other = _it(1, (400, 0, 404, 100))
        m = SS.match_stems([t, other], [], {0: SP, 1: SP})
        stem = _run((100, 0, 104, 100), PAIRED)
        partner = _run((100 + 0.5 * SP, 0, 100 + 0.5 * SP + 3, 2.3 * SP), "accepted")
        out = SS.explain_missed(m, [t, other], {"runs": [stem, partner]})
        row = next(r for r in out["facts"]["missed"] if r["id"] == "t0")
        assert row["run_refused_for"] == ["PAIRED"]
        assert row["paired_with"] == [{"centre_offset_spaces": pytest.approx(0.475, abs=0.01),
                                       "height_spaces": 2.3, "is_a_truth_stem": False, "lies_on": "no truth box"}]

    def test_paired_plus_too_wide_is_reported_as_both(self):
        m, t = self._missed()
        out = SS.explain_missed(m, [t], {"runs": [_run((100, 0, 104, 100), PAIRED),
                                                  _run((100, 0, 100 + 1.1 * SP, 100), TOO_WIDE)]})
        assert next(iter(out["by_cause"])).endswith("PAIRED + too WIDE")

    def test_every_refusal_word_names_its_code_path_and_constant(self):
        for word in ("too SHORT", "too TALL", "too WIDE", "at a CELL EDGE", "too little AREA", "ASPECT", "PAIRED"):
            assert SS.RUN_REFUSALS[word][1].startswith("line_detection.")
        assert SS.run_refusal_word(TOO_WIDE) == "too WIDE" and SS.run_refusal_word("accepted") == "accepted"

    def test_without_the_runs_the_cause_says_the_filter_is_not_on_the_record(self):
        m, t = self._missed()
        assert "not on the record" in next(iter(SS.explain_missed(m, [t], {})["by_cause"]))

    def test_a_fragment_in_the_column_is_a_fragment_not_a_filter_refusal(self):
        t = _it(0, (100, 0, 104, 100))
        m = SS.match_stems([t], [_cv(0, (100, 0, 104, 30))], {0: SP})
        out = SS.explain_missed(m, [t], {"runs": [_run((100, 0, 104, 30), "accepted")]})
        assert out["by_cause"] == {"a CV stem covers only a fragment of it": 1}

    def test_chord_and_stacked_facts_come_from_the_truth_heads_and_the_found_stems_are_the_baseline(self):
        t = _it(0, (100, 0, 104, 100))
        heads = [_it(1, (80, 60, 104, 80), "notehead"), _it(2, (80, 80, 104, 100), "notehead"),
                 _it(3, (500, 0, 524, 20), "notehead")]
        f = SS.stem_facts(t, SP, heads, [], [])
        assert f["heads_on_it"] == 2 and f["chord"] and f["stacked_heads"] and f["closest_heads_apart_in_steps"] == 2
        table = SS.feature_table([f], [dict(f, chord=False, stacked_heads=False)])
        assert table["chord (2+ heads on it)"] == {"missed": 1, "found": 0, "found_share": 0.0}
        assert table["closest two heads a third apart (2 steps)"]["missed"] == 1

    def test_staff_lines_crossed_counts_the_lines_inside_the_stems_extent_and_is_unread_without_them(self):
        lines = [20.0, 40.0, 60.0, 80.0, 100.0]
        assert SS.stem_facts(_it(0, (100, 10, 104, 90)), SP, [], [], [], lines)["staff_lines_crossed"] == 4
        assert SS.stem_facts(_it(0, (100, 110, 104, 160)), SP, [], [], [], lines)["staff_lines_crossed"] == 0
        assert SS.stem_facts(_it(0, (100, 0, 104, 120)), SP, [], [], [], lines)["staff_lines_crossed"] == 5
        assert SS.stem_facts(_it(0, (100, 10, 104, 90)), SP, [], [], [])["staff_lines_crossed"] is None  # not 0
        table = SS.feature_table([{"length_spaces": 4.0, "chord": False, "stacked_heads": False,
                                   "touches_a_beam_box": False, "touches_a_slur_or_tie_box": False, "heads_on_it": 1,
                                   "closest_heads_apart_in_steps": None, "heads_on_both_sides_of_the_stem": False,
                                   "staff_lines_crossed": 5}], [])
        assert table["crosses all five staff lines"]["missed"] == 1 and table["crosses no staff line (wholly outside the staff)"]["missed"] == 0

    def test_stem_sets_equal_refuses_a_record_whose_stems_differ(self, page, items):
        a = C.run_of(C.synthetic_result(page, items, up=2.5))
        same = C.synthetic_result(page, items, up=2.5)
        assert SS.stem_sets_equal(a, same, 0)[0]
        different = C.synthetic_result(page, items, up=2.5, cv_dx=3.0)
        assert not SS.stem_sets_equal(a, different, 0)[0]

    def test_vertical_runs_are_read_in_page_pixels_with_their_refusal(self):
        rec = {"record": {"observations": [
            {"quantity": "vertical_run", "subject": "glyph/0/1/2/3/300000",
             "detail": {"run_outcome": TOO_WIDE, "run_bbox_page_px": [1, 2, 30, 90]}},
            {"quantity": "vertical_run", "subject": "glyph/1/1/2/3/300000",
             "detail": {"run_outcome": "accepted", "run_bbox_page_px": [1, 2, 3, 4]}},
            {"quantity": "stem", "subject": "cell/0/1/2/3", "value": [1, 2, 3, 4], "detail": {}}]}}
        assert SS.read_vertical_runs(rec, 0) == [{"rect": (1.0, 2.0, 30.0, 90.0), "outcome": TOO_WIDE,
                                                  "frame": (1, 2, 3)}]


class TestInkColumns:
    def _ink(self, gap=None):
        a = np.zeros((300, 200), bool)
        a[50:250, 100:107] = True
        if gap:
            a[gap[0]:gap[1], 100:107] = False
        return a

    def test_an_unbroken_stem_reads_its_whole_length_and_a_gap_cuts_it(self):
        rect = (100, 50, 107, 250)
        whole = SS.InkColumns(self._ink())
        assert whole.longest_run_spaces(rect, 20.0) == pytest.approx(10.0)
        assert whole.ink_share(rect, 20.0) == pytest.approx(1.0)
        cut = SS.InkColumns(self._ink(gap=(140, 160)))
        assert cut.longest_run_spaces(rect, 20.0) == pytest.approx(4.5, abs=0.1)
        assert cut.ink_share(rect, 20.0) < 0.95

    def test_no_ink_at_the_column_reads_zero(self):
        assert SS.InkColumns(np.zeros((300, 200), bool)).longest_run_spaces((100, 50, 107, 250), 20.0) == 0.0


class TestCli:
    def test_stem_runs_from_a_record_with_different_stems_is_refused(self, page, items, tmp_path, monkeypatch):
        pg = tmp_path / "0.json"
        pg.write_text(json.dumps(page.to_json()))
        rec = tmp_path / "rec.json"
        rec.write_text(json.dumps(C.synthetic_result(page, items, up=2.5)))
        other = tmp_path / "other.json"
        other.write_text(json.dumps(C.synthetic_result(page, items, up=2.5, cv_dx=3.0)))
        with pytest.raises(SystemExit):
            S.main(["--page", str(pg), "--record", str(rec), "--derive", "--stem-runs", str(other)])


# ─────────────────────────────────────────────────────────────────────────────
# D2 for the stems: each control passes on the clean scorer ...
# ─────────────────────────────────────────────────────────────────────────────

STEM_CONTROLS = [c for c in C.CONTROLS if c.__name__.startswith("control_stems_")]


def test_there_are_six_stem_controls():
    assert len(STEM_CONTROLS) == 6


@pytest.mark.parametrize("control", STEM_CONTROLS, ids=lambda c: c.__name__)
def test_each_stem_control_passes_on_the_clean_scorer(control, page):
    res = control(page, True)
    assert res["passes"], json.dumps(res, default=str)


def test_the_shift_the_stem_control_uses_is_about_one_head_width_and_clears_the_neighbours(items):
    dx = C.clear_stem_shift(items, SP)
    assert dx == pytest.approx(C.HEAD_WIDTH_SPACES * SP)
    stems = [it for it in items if it.family == "stem"]
    assert not any(a is not b and abs(S._cx(a.rect) + dx - S._cx(b.rect)) <= 0.3 * SP
                   and min(a.rect[3], b.rect[3]) - max(a.rect[1], b.rect[1]) > 0 for a in stems for b in stems)


# ... and each goes RED when the bug it exists to catch is seeded in.


class TestEachStemControlCanFail:
    def red(self, control, page):
        res = control(page, True)
        assert not res["passes"], f"{control.__name__} stayed GREEN with the bug seeded: {res}"

    def test_a_matcher_that_ignores_the_column_is_caught_by_the_shift_control(self, page, monkeypatch):
        monkeypatch.setattr(SS, "_same_column", lambda t, c, sp: True)
        assert C.control_stems_self(page, True)["passes"]       # the self-score cannot tell: that is why the shift exists
        self.red(C.control_stems_shift, page)

    def test_a_tolerance_widened_until_a_stem_pairs_with_its_neighbour_is_caught_by_the_shift_control(self, page,
                                                                                                    monkeypatch):
        monkeypatch.setattr(SS, "STEM_MATCH_DX_SPACES", 6.0)
        self.red(C.control_stems_shift, page)

    def test_a_scorer_that_forgets_the_canonical_conversion_is_caught_by_the_self_score(self, page, monkeypatch):
        real = SS.cell_frames
        monkeypatch.setattr(SS, "cell_frames", lambda r, p: ({k: (1.0, "forced") for k in real(r, p)[0]},
                                                             real(r, p)[1], real(r, p)[2]))
        self.red(C.control_stems_self, page)

    def test_a_matcher_that_links_nothing_is_caught_by_the_self_score(self, page, monkeypatch):
        monkeypatch.setattr(SS, "_linked", lambda t, c, sp: False)
        self.red(C.control_stems_self, page)

    def test_an_attachment_judge_that_always_says_right_is_caught_by_the_swap(self, page, monkeypatch):
        monkeypatch.setattr(SS, "_same_stem_judge", lambda named, mine, m: "right")
        self.red(C.control_stems_attach_swap, page)

    def test_an_attachment_judge_that_never_says_right_is_caught_by_the_self_score(self, page, monkeypatch):
        monkeypatch.setattr(SS, "_same_stem_judge", lambda named, mine, m: "other")
        self.red(C.control_stems_self, page)

    def test_a_direction_judge_that_always_says_right_is_caught_by_the_flip(self, page, monkeypatch):
        monkeypatch.setattr(SS, "_direction_judge", lambda read, truth: True)
        self.red(C.control_stems_direction_flip, page)

    def test_a_direction_judge_that_never_says_right_is_caught_by_the_self_score(self, page, monkeypatch):
        monkeypatch.setattr(SS, "_direction_judge", lambda read, truth: False)
        self.red(C.control_stems_self, page)

    def test_rates_that_are_always_one_are_caught_by_drop_and_add(self, page, monkeypatch):
        monkeypatch.setattr(SS, "_rate", lambda n, d: 1.0)
        self.red(C.control_stems_drop_and_add, page)

    def test_a_reader_that_never_ran_counted_as_ran_is_caught_by_the_refusal_control(self, page, monkeypatch):
        real = SS.read_cv_stems

        def always_ran(run, page_index):
            out = real(run, page_index)
            out.ran = True
            return out
        monkeypatch.setattr(SS, "read_cv_stems", always_ran)
        self.red(C.control_stems_reader_not_run, page)

    def test_positive_control_the_unseeded_scorer_is_green_on_every_stem_control(self, page):
        assert all(c(page, True)["passes"] for c in STEM_CONTROLS)


def test_the_first_hand_truth_scorer_numbers_did_not_move(page, items):
    """The stem work is additive: the detector-class stem row and every other family read as before."""
    rep = stem_report(page, items)
    assert rep["families"]["stem"]["gather"]["recall"] == 1.0
    assert rep["families"]["notehead"]["gather"]["precision"] == 1.0
    assert rep["frame_control"]["ok"]
