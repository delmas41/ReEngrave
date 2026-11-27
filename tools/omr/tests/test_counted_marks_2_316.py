"""ROADMAP 2.316 -- COUNT PRINTED NOTES AND ARCS, NOT BOXES (Sean 2026-11-18). Tooling only. Each control is cut from a REAL case and is shown to fail on the
old way of counting (CLAUDE rule 7); the three judged tiles are the real rows of the 20261117-night records."""
import json
import os
import pathlib
import unittest
from unittest import mock

from tools.omr.staged import counted_marks as CM
from tools.omr.staged import export as SX
from tools.omr.staged import judged as J
from tools.omr.staged import regather_report as RR
from tools.omr.tests.test_staged_export import QUARTER, _one_staff_page

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def H(page, x, y, fate, w=24, h=18):
    return {"page": page, "box": [x, y, x + w, y + h], "fate": fate}


class TestTheCensus(unittest.TestCase):
    def census(self):
        heads = {
            "w1": H(1, 100, 100, "written"),
            "dup_of_w1": H(1, 102, 101, "owned_by_another_staff"),           # a neighbouring staff's copy of a written head
            "dup2_of_w1": H(1, 99, 99, "mark_group_duplicate"),              # a second box on it
            "barline": H(1, 300, 100, "not_a_notehead:claimed_by:barline"),  # ink that is no note
            "lost_alone": H(1, 500, 100, "duration_narrowed"),
            "lost_a": H(1, 700, 100, "no_pitch"),                            # two boxes, one note
            "lost_b": H(1, 704, 102, "not_a_notehead:too_narrow"),
            "orphan_dup": H(1, 900, 100, "not_a_notehead:stacked_head_duplicate"),
            "as_rest": H(1, 1100, 100, "written"),                           # a head-shaped box the file writes as an eighth rest
            "unison": H(1, 1300, 100, "written"),
            "render": H(1, 1500, 100, "written"),                            # placed, its bar was then refused
        }
        return heads, CM.note_census(heads, ["w1", "unison", "unison"], ["as_rest"])

    def test_every_box_is_counted_once_in_the_bucket_it_belongs_to(self):
        heads, c = self.census()
        self.assertTrue(c["identity"]["ok"])
        self.assertEqual(c["identity"]["heads_in_log"], len(heads))
        b = c["boxes"]
        self.assertEqual((b["written"], b["written_as_a_rest"], b["duplicate_of_written"], b["non_note_ink"], b["duplicate_no_written_twin"]),
                         (2, 1, 2, 1, 1))
        self.assertEqual(b["non_note_ink_by_kind"], {"barline": 1})

    def test_notes_are_printed_notes_not_boxes(self):
        _heads, c = self.census()
        n = c["notes"]
        self.assertEqual(n["written"], 2)                      # a head written twice (unison) is one note; a rest is not a note
        self.assertEqual(n["candidate_lost"], 3)               # alone, the two overlapping boxes as ONE, the one dropped at render
        self.assertEqual(n["candidate_lost_by_cause"]["value_undecided"], 1)
        self.assertEqual(n["candidate_lost_by_cause"]["no_pitch"], 1)         # the cluster takes the earlier cause
        self.assertEqual(n["candidate_lost_by_cause"]["dropped_at_render"], 1)
        self.assertEqual(n["printed"], 5)

    def test_the_old_box_count_overstates_the_loss_here(self):
        """The control: boxes not written = 9 of 11; printed notes lost = 3. The old headline would call every duplicate and the barline a note."""
        heads, c = self.census()
        boxes_not_written = len(heads) - c["boxes"]["written"]
        self.assertEqual(boxes_not_written, 9)
        self.assertLess(c["notes"]["candidate_lost"], boxes_not_written / 2)

    def test_a_barline_is_not_a_lost_note_but_the_same_box_with_no_claim_would_be(self):
        heads = {"a": H(1, 10, 10, "not_a_notehead:claimed_by:barline"), "b": H(1, 200, 10, "not_a_notehead:wider_than_a_head")}
        c = CM.note_census(heads, [])
        self.assertEqual((c["notes"]["candidate_lost"], c["boxes"]["non_note_ink"]), (1, 1))

    def test_a_written_twin_on_another_page_is_no_twin(self):
        heads = {"w": H(1, 100, 100, "written"), "x": H(2, 100, 100, "owned_by_another_staff")}
        c = CM.note_census(heads, ["w"])
        self.assertEqual((c["boxes"]["duplicate_of_written"], c["notes"]["candidate_lost"]), (0, 1))

    def test_only_pages_counts_those_pages_only(self):
        heads = {"w": H(2, 100, 100, "written"), "d": H(2, 100, 100, "owned_by_another_staff"), "l": H(2, 900, 100, "no_pitch"),
                 "z": H(1, 100, 100, "written")}
        c = CM.note_census(heads, ["w", "z"], only_pages=[2])
        self.assertEqual((c["notes"]["written"], c["notes"]["candidate_lost"], c["identity"]["heads_in_log"]), (1, 1, 3))
        self.assertEqual(c["boxes"]["duplicate_of_written"], 1)

    def test_fates_are_named_not_guessed(self):
        self.assertEqual(CM.fate_group("not_a_notehead:claimed_by:clef"), "non_note")
        self.assertEqual(CM.fate_group("a_fate_nobody_named"), "other")           # never dropped: a candidate
        self.assertEqual(CM.fate_group(None), "other")


class TestBrahmsPage0AgainstSeansLabels(unittest.TestCase):
    """The real control. Brahms p0 (imslp317803 page 0), the 20261117-night record's exporter fates, against Sean's labelled heads (data/hand-truth): the
    labels hold 382 heads in the inspected cells; the page has 486 head boxes (439 in those cells). The old way (a box is a note) disagrees with the labels by
    57; the printed-note count agrees within 12."""

    @classmethod
    def setUpClass(cls):
        from tools.omr.hand_truth import score as S, store
        fx = json.loads((HERE / "data" / "counted_marks_2_316_brahms_p0.json").read_text())
        cls.heads = {k: {"page": v[0], "box": v[1], "fate": v[2]} for k, v in fx["heads"].items()}
        cls.written = fx["written"]
        page = store.load(ROOT / "data" / "hand-truth" / "pages" / "imslp317803" / "0.json")
        cls.scope = S.Scope(S.cells_inspected_for(page, "notehead"))
        items = S.truth_items(page)
        cls.labelled = [i for i in items if i.family == "notehead" and cls.scope.holds(i.rect)]
        cls.census = CM.note_census(cls.heads, cls.written, keep_lists=True)

    def test_the_labels_hold_382_heads(self):
        self.assertEqual(len(self.labelled), 382)

    def test_printed_notes_in_the_inspected_cells_agree_with_the_labels(self):
        wb = [self.heads[k]["box"] for k in set(self.written) if k in self.heads]
        written_in = sum(1 for b in wb if self.scope.holds(b))
        lost_in = sum(1 for ks in self.census["lost_lists"].values() for mem in ks if any(self.scope.holds(self.heads[m]["box"]) for m in mem))
        printed = written_in + lost_in
        self.assertLessEqual(abs(printed - len(self.labelled)), 12, (written_in, lost_in, printed))
        self.assertLessEqual(abs(written_in - 376), 4)           # the labels: 376 of the 382 have a written head at their place by this tool's place rule

    def test_the_old_box_count_would_fail_this_control(self):
        """The same labels against the old figure: every head box in those cells is a 'note'. It is off by 57; that is the fault this lane fixes."""
        boxes_in = sum(1 for h in self.heads.values() if self.scope.holds(h["box"]))
        self.assertGreater(abs(boxes_in - len(self.labelled)), 12)

    def test_the_labelled_heads_not_written_are_found_among_the_candidate_lost(self):
        from tools.omr.staged.judged import boxes_overlap
        wb = [self.heads[k]["box"] for k in set(self.written) if k in self.heads]
        lost = [self.heads[m]["box"] for ks in self.census["lost_lists"].values() for mem in ks for m in mem]
        unwritten = [h for h in self.labelled if not any(boxes_overlap(h.rect, b)[0] for b in wb)]
        found = [h for h in unwritten if any(boxes_overlap(h.rect, b)[0] for b in lost)]
        self.assertGreaterEqual(len(found), len(unwritten) - 1)  # all but one of the labelled heads not written sit in a candidate-lost cluster


# the 20261117-night Litolff whole-movement export report, cut to the arc rows (`written` counters and `arcs_not_written`)
LIT_1117_ARCS = {
    "arcs_not_written": {"old_box_path_retired": 1194, "replaced_by_page_arc": 1575, "not_an_arc:ink_is_a_staff_line": 519,
                         "not_an_arc:claimed_by:key_signature": 8, "kind_arc_ends_unread": 15, "kind_same_pitch_accidental_unread": 5,
                         "kind_stack_slur_over_two_same_pitch_notes": 1, "tie_pitch_contradiction": 15, "tie_ends_in_two_voices": 23,
                         "slur_bound_end_not_in_file": 49, "tie_pair_no_start_head": 70, "tie_pair_no_head_near_the_arc": 71,
                         "tie_pair_no_stop_head": 39, "tie_pair_enters_from_previous_system": 47, "tie_pair_no_pair_at_one_position": 52,
                         "tie_pair_runs_off_the_system": 38, "tie_pair_not_adjacent": 58, "tie_pair_spans_a_whole_bar": 4,
                         "tie_end_not_in_file": 20, "arc_ends_in_one_chord": 7},
    "written": {"page_arc_runs": 1332, "page_arc_runs_not_witnessed": 249, "page_arc_runs_abstained": 515,
                "page_arc_runs_kind_unread_nothing_written": 27, "page_arc_boxes_replaced": 1575, "page_arc_slurs_in_file": 138,
                "page_arc_slurs_not_in_file": 18, "page_arc_ties_in_file": 331, "page_arc_ties_not_in_file": 19},
}


class TestArcsAreCountedNotBoxes(unittest.TestCase):
    def test_a_box_a_written_page_arc_replaced_is_not_counted_and_a_run_read_but_not_written_is(self):
        a = CM.arcs_count(LIT_1117_ARCS)
        # the OLD row: every reason but not_an_arc -- boxes the page pass replaced / the old path retired included, page runs read-and-unwritten absent
        self.assertEqual(a["old_figure_boxes"], 3283)
        self.assertEqual(a["apart"]["replaced_by_page_arc_boxes"], 1575)
        self.assertEqual(a["apart"]["old_box_path_retired_boxes"], 1194)
        # NEW: refusals that are still refusals (a bound curve not in the file is one page arc, counted below not twice) ...
        # ROADMAP 2.360: 477 were refusals before; 379 of them are the OLD tie pairing's (`tie_pair_*`), which writes nothing with the page pass on -- named apart
        self.assertEqual(a["old_box_refusals"], 98)
        self.assertEqual(a["old_tie_pairing_refusals"], 379)
        # ... plus the page runs read and not written: 515 abstained + 18 slurs + 19 ties planned and not in the file
        self.assertEqual(a["page_runs_not_written"], 552)
        self.assertEqual(a["not_written_total"], 650)              # 2.316 said 1029 (= 477 + 552)
        self.assertEqual(a["apart"]["unwitnessed_page_runs"], 249)
        self.assertEqual(a["with_unwitnessed"], 899)
        self.assertEqual(a["with_unwitnessed_and_old_pairing"], 1278)   # nothing dropped: the upper bound is the old with_unwitnessed

    def test_the_replaced_box_does_not_move_the_count_and_a_new_unwritten_run_does(self):
        base = CM.arcs_count(LIT_1117_ARCS)["not_written_total"]
        more_replaced = json.loads(json.dumps(LIT_1117_ARCS))
        more_replaced["arcs_not_written"]["replaced_by_page_arc"] += 400
        more_replaced["arcs_not_written"]["old_box_path_retired"] += 400
        self.assertEqual(CM.arcs_count(more_replaced)["not_written_total"], base)
        more_unread = json.loads(json.dumps(LIT_1117_ARCS))
        more_unread["written"]["page_arc_runs_abstained"] += 7
        self.assertEqual(CM.arcs_count(more_unread)["not_written_total"], base + 7)

    def test_the_kind_unread_runs_are_part_of_the_abstained_never_added_again(self):
        more = json.loads(json.dumps(LIT_1117_ARCS))
        more["written"]["page_arc_runs_kind_unread_nothing_written"] += 50
        self.assertEqual(CM.arcs_count(more)["not_written_total"], CM.arcs_count(LIT_1117_ARCS)["not_written_total"])

    def test_a_record_gathered_without_the_page_pass_says_none_not_zero(self):
        a = CM.arcs_count({"arcs_not_written": {"tie_pair_no_start_head": 3, "replaced_by_page_arc": 0}, "written": {}})
        self.assertIsNone(a["page_runs_not_written"])
        self.assertIsNone(a["apart"]["unwitnessed_page_runs"])
        self.assertEqual(a["not_written_total"], 3)

    def test_the_double_count_guard_never_goes_negative(self):
        a = CM.arcs_count({"arcs_not_written": {"slur_bound_end_not_in_file": 2}, "written": {"page_arc_runs": 5, "page_arc_slurs_not_in_file": 9}})
        self.assertEqual(a["old_box_refusals"], 0)
        self.assertEqual(a["page_runs_not_written"], 9)


class TestTheTappedExportChangesNoByte(unittest.TestCase):
    F = {"numerator": 4, "denominator": 4, "raw": "4/4"}

    def _page(self, notes):
        return _one_staff_page(notes=notes, meter=self.F)

    def test_the_file_is_byte_identical_to_the_untraced_export_and_the_census_counts_it(self):
        notes = [("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)]
        with mock.patch.dict(os.environ, {"OMR_RED_BARS": "1", "OMR_PARTIAL_BARS": "on"}):
            plain, _ = SX.to_musicxml(self._page(notes))
            xml, report, census = CM.tapped_export(self._page(notes))
            kept, _r, _c = CM.tapped_export(self._page(notes), strip=False)
        self.assertEqual(plain, xml)
        self.assertNotEqual(plain, kept)                       # the control: the stamps are really there when kept
        self.assertEqual(CM.strip_trace(kept), plain)
        self.assertEqual((census["notes"]["written"], census["notes"]["candidate_lost"]), (3, 0))
        self.assertTrue(census["identity"]["ok"])

    def test_a_held_bar_is_counted_as_lost_notes_not_dropped(self):
        notes = [("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)]
        with mock.patch.dict(os.environ, {"OMR_RED_BARS": "0", "OMR_PARTIAL_BARS": "on"}):
            plain, _ = SX.to_musicxml(self._page(notes))
            xml, report, census = CM.tapped_export(self._page(notes))
        self.assertEqual(plain, xml)
        self.assertEqual(census["notes"]["written"], 0)
        self.assertEqual(census["notes"]["candidate_lost"], 3)

    def test_the_stamps_are_restored_even_when_the_export_raises(self):
        before = SX._place_notes
        with mock.patch.object(SX, "build", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                CM.tapped_export(self._page([("C4", QUARTER)]))
        self.assertIs(SX._place_notes, before)


class TestMissingExportReportIsNamed(unittest.TestCase):
    def test_a_night_file_that_does_not_hold_the_movement_raises_a_clear_message(self):
        import tempfile
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "current.json").write_text(json.dumps({"documents": {"beethoven5-litolff": {"export": {"report": {"written": {}}}}}}))
        with self.assertRaises(RR.MissingExportReport) as cm:
            RR.load_export_report(d / "current.json", "brahms1-breitkopf")
        msg = str(cm.exception)
        self.assertIn("brahms1-breitkopf", msg)
        self.assertIn("beethoven5-litolff", msg)               # what the file holds
        self.assertIn("current.json", msg)
        # the control: the document that IS there still loads
        self.assertEqual(RR.load_export_report(d / "current.json", "beethoven5-litolff"), {"written": {}})

    def test_a_document_whose_export_step_failed_is_not_answered_with_an_empty_report(self):
        import tempfile
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "current.json").write_text(json.dumps({"documents": {"x": {"status": "error", "export": {"ok": False}}}}))
        with self.assertRaises(RR.MissingExportReport):
            RR.load_export_report(d / "current.json", "x")


# ── the three judged tiles (20261117-night records): the verdict rows and the run rows as the record holds them ──

def _v(outcome, value, reason):
    return {"outcome": outcome, "value": value, "reason": reason, "margin": None}


class TestJudgedMatchesWhatTheFileWritesAtThePlace(unittest.TestCase):
    def test_litolff_2_78_tile_11_one_note_written_right_scores_right_though_its_neighbour_box_is_the_barlines_ink(self):
        eighth, barline = "glyph/6/1/10/9/5", "glyph/6/1/10/9/9"
        S = {(eighth, "duration"): _v("decided", {"beats": 0.5}, "head_and_marks"),
             (eighth, "notehead_is_not_a_notehead"): _v("decided", False, "notehead"),
             (barline, "duration"): _v("decided", {"beats": 2.0}, "whole_class_on_a_stem"),
             (barline, "notehead_is_not_a_notehead"): _v("decided", True, "claimed_by:barline")}
        row = {"item": "2.78-phase2-review", "tile": "11", "answer_kind": "duration", "value": 0.5, "question_kind": "duration", "subject_kind": "glyph",
               "subject": None, "subjects": [eighth, barline]}
        self.assertEqual(J.score_row(row, S)[0], "right")
        # the old scoring: every named box must match, so the refused one made the tile wrong
        self.assertEqual(J._duration(barline, 0.5, S)[0], "wrong")

    def test_the_tile_still_scores_wrong_where_the_written_note_is_wrong_or_nothing_is_written(self):
        a, b = "glyph/1/0/0/0/1", "glyph/1/0/0/0/2"
        S = {(a, "duration"): _v("decided", {"beats": 1.0}, "head_and_marks"), (a, "notehead_is_not_a_notehead"): _v("decided", False, "notehead"),
             (b, "notehead_is_not_a_notehead"): _v("decided", True, "claimed_by:barline"), (b, "duration"): _v("decided", {"beats": 0.5}, "x")}
        row = {"answer_kind": "duration", "value": 0.5, "question_kind": "duration", "subject_kind": "glyph", "subject": None, "subjects": [a, b]}
        self.assertEqual(J.score_row(row, S)[0], "wrong")                       # the written note is a quarter
        S[(a, "notehead_is_not_a_notehead")] = _v("decided", True, "claimed_by:clef")
        self.assertEqual(J.score_row(row, S)[0], "wrong")                       # both refused: no note is written

    # run rows as the Brahms 20261117-night record holds them (Q.PAGE_ARC bbox/ends; the standing PAGE_ARC_BINDING verdict's kind)
    TIE_2_250 = dict(row="obs:029171", kind="tie", bbox=[4036.0, 5496.0, 4186.0, 5553.0], ends=[(4036.0, 5521.0), (4186.0, 5547.0)], space=32.0,
                     start="glyph/0/0/10/4/7", stop="glyph/0/0/10/5/1", witnesses=[])
    SLUR_2_250 = dict(row="obs:029183", kind="slur", bbox=[3624.0, 5436.0, 4598.0, 5553.0], ends=[(3624.0, 5490.0), (4598.0, 5547.0)], space=32.0,
                      start="glyph/0/0/10/4/4", stop="glyph/0/0/10/5/3", witnesses=[])
    TIE_2_166 = dict(row="obs:094442", kind="tie", bbox=[2780.9, 1136.1, 3100.6, 1185.9], ends=[(2780.9, 1151.6), (3100.6, 1142.1)], space=27.5,
                     start="glyph/1/0/2/2/3", stop="glyph/1/0/2/3/9", witnesses=["glyph/1/0/2/2/25"])

    def test_brahms_2_250_tile_2_a_tie_asked_through_the_head_it_ends_on_is_the_tie_not_the_wide_slur_over_it(self):
        tile = [4145.4, 5532.08, 4187.96, 5569.2]                               # the head the tie ends on
        runs = [self.SLUR_2_250, self.TIE_2_250]
        run, how = J.arc_written_at(tile, runs)
        self.assertEqual((run["kind"], run["row"]), ("tie", "obs:029171"))
        self.assertIn("end", how)
        # the old rule: ANY overlap is the place, and the wide slur's box takes the tile's centre -- the fault
        self.assertTrue(J.boxes_overlap(self.SLUR_2_250["bbox"], tile)[0])
        # the control: a slur whose end really is at that head is found as a slur
        slur_at = dict(self.SLUR_2_250, ends=[(3624.0, 5490.0), (4170.0, 5547.0)])
        self.assertEqual(J.arc_written_at(tile, [slur_at])[0]["kind"], "slur")

    def test_a_run_that_only_passes_over_the_mark_is_not_at_its_place(self):
        tile = [4145.4, 5532.08, 4187.96, 5569.2]
        self.assertIsNone(J.arc_written_at(tile, [self.SLUR_2_250]))

    def test_brahms_2_166_tile_14_the_box_says_slur_the_page_arc_on_the_same_ink_is_written_a_tie(self):
        tile = [2763.275, 1148.3, 3017.375, 1185.15]                            # the old detector box of the tie's own ink
        run, how = J.arc_written_at(tile, [self.TIE_2_166, self.SLUR_2_250])
        self.assertEqual(run["kind"], "tie")
        self.assertIn("extent", how)
        # the old scoring read the box's own arc_kind verdict: slur -> wrong
        S = {("glyph/1/0/2/2/25", "arc_kind"): _v("decided", "slur", "slur")}
        self.assertEqual(J._arc("glyph/1/0/2/2/25", "tie", S)[0], "wrong")

    def test_two_runs_far_from_the_mark_find_nothing(self):
        self.assertIsNone(J.arc_written_at([0, 0, 40, 40], [self.TIE_2_250, self.TIE_2_166]))


if __name__ == "__main__":
    unittest.main()
