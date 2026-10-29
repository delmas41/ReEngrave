"""lane-scorer-blue -- the lane report's judged scorer missed a real right->wrong (Litolff p10, 2.220-plan tile 5: a half
written blue OFF, a quarter written blue ON, scored 0 over 132 tiles). Two causes, one test each:
  1. the 2.220 galleries have no manifest.json, so their tiles had no subject and were never scored (the index reads key.json);
  2. the verdict scorer reads DECIDED durations only; a blue (INFER-collapsed, `narrowed`) note that changes value moves
     nothing in it. The written value at the place is scored too, plain or blue alike."""
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from tools.omr.staged import judged as J
from tools.omr.staged import lane_report as L

SUB = "glyph/10/0/9/6/3"


def host(typ, blue, dots=(), rg=SUB, pitch="E-14"):
    return dict(kind="note", part="P10", measure="7", rg=rg, page=10, cx=100, cy=200, box=[90, 190, 110, 210],
                type=typ, pitch=pitch, blue=blue, sub={"dot": list(dots)}, chord=False, onset="0", voice="1")


def row(answer="half", value=2.0):
    return dict(item="2.220-plan", tile="5", doc="litolff", subject=SUB, subjects=None, subject_kind="glyph",
                answer=answer, answer_kind="duration", value=value, followup=False)


def moves(off, on, r=None, rep=None):
    idx = {"tiles": [r or row()]}
    rep = rep or dict(worse=[], lost=[], better=[])
    return L.written_moves(rep, idx, "litolff", lambda rec, subs: {}, (None, None), off, on)


class TestWrittenValueScoring(unittest.TestCase):
    def test_blue_half_off_blue_quarter_on_is_right_to_wrong(self):
        r = moves([host("half", True)], [host("quarter", True)])
        self.assertEqual(len(r["worse"]), 1)
        self.assertTrue(r["worse"][0]["blue"])
        self.assertEqual(L.blue_count(r["worse"]), "1 (1 blue)")

    def test_plain_half_to_plain_quarter_is_right_to_wrong_not_blue(self):
        r = moves([host("half", False)], [host("quarter", False)])
        self.assertEqual((len(r["worse"]), L.blue_count(r["worse"])), (1, "1"))

    def test_toward_sean_is_wrong_to_right(self):
        r = moves([host("quarter", True)], [host("half", True)])
        self.assertEqual((r["worse"], len(r["better"])), ([], 1))

    def test_unchanged_value_counts_nothing(self):
        r = moves([host("half", True)], [host("half", False)])
        self.assertEqual((r["worse"], r["better"]), ([], []))

    def test_wrong_to_wrong_counts_nothing(self):
        r = moves([host("quarter", True)], [host("eighth", True)])
        self.assertEqual((r["worse"], r["better"]), ([], []))

    def test_a_different_pitch_at_the_place_is_not_a_value_change(self):
        r = moves([host("half", True)], [host("quarter", True, pitch="F-14")])
        self.assertEqual(r["worse"], [])

    def test_a_row_the_verdict_scorer_has_keeps_one_entry_and_gains_blue(self):
        have = dict(worse=[dict(item="2.220-plan", tile="5", subject=SUB, answer="half", now="decided 1 beats")], lost=[], better=[])
        r = moves([host("half", True)], [host("quarter", True)], rep=have)
        self.assertEqual((len(r["worse"]), r["worse"][0]["blue"]), (1, True))

    def test_landing_line_reports_the_blue_count(self):
        w = moves([host("half", True)], [host("quarter", True)])["worse"]
        line = L.landing_line(dict(plates={"litolff": dict(judged=dict(worse=w, unwritten_wrong=[], unwritten_right=[], better=[]))}))
        self.assertIn("FAILS", line)
        self.assertIn("1 (1 blue)", line)


class TestKeyJsonIsTheManifest(unittest.TestCase):
    def test_a_gallery_without_manifest_gets_its_subjects_from_key_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            g = root / "2.220-plan"
            g.mkdir()
            (g / "answers.json").write_text(json.dumps({"answered": "2026-10-28", "tiles": [
                {"tile": 5, "plate": "litolff", "page": 10, "seans_answer": "half", "written": "quarter"}]}))
            (g / "key.json").write_text(json.dumps([
                {"tile": 5, "plate": "litolff", "page": 10, "box": [1, 2, 3, 4], "subject": SUB, "written": "quarter"}]))
            rows = J.item_rows(g / "answers.json", root)
            self.assertEqual(len(rows), 1)
            self.assertEqual((rows[0]["subject"], rows[0]["doc"], rows[0]["answer_kind"], rows[0]["value"]),
                             (SUB, "litolff", "duration", 2.0))

    def test_a_key_that_is_not_a_value_question_is_not_read_as_one(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            g = root / "owner"
            g.mkdir()
            (g / "answers.json").write_text(json.dumps({"tiles": [{"tile": 1, "sean": "2"}]}))
            (g / "key.json").write_text(json.dumps([{"tile": 1, "rg": SUB, "plate": "litolff", "side": "upper"}]))
            self.assertIsNone(J.item_rows(g / "answers.json", root)[0]["subject"])

    def test_the_committed_index_scores_the_p10_tile(self):
        idx = json.loads(J.INDEX_PATH.read_text())
        r = [t for t in idx["tiles"] if t["item"] == "2.220-plan" and t["tile"] == "5"][0]
        self.assertEqual((r["subject"], r["answer_kind"], r["value"]), (SUB, "duration", 2.0))


if __name__ == "__main__":
    unittest.main()
