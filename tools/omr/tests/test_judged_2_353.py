"""ROADMAP 2.353 -- the judged scorer knows "this is a notehead" and does not silently choose between a tile's boxes.

Both cases are REAL rows of `benchmarks/acceptance/judged-tiles.json` (CLAUDE.md rule 7), not drawings of what we think the case is:
  A. Litolff `2.347-leaves` tile 1, glyph/10/1/9/0/5, Sean: "That is a notehead but the stem ink is broken".
  B. Brahms `2.78-phase2-review` tile 5, boxes glyph/0/0/12/1/1 (the written sixteenth) and glyph/0/0/12/1/15 (a second head-sized box at the
     stem's far end, narrowed, dropped by EXPORT as `duration_narrowed`; benchmarks/no-value-notes-2026-11/FINDINGS.md, 2.349 tile 5 trace).
The standing verdicts are the ones those findings name.
"""
from __future__ import annotations

import json
import pathlib
import unittest

from tools.omr.staged import judged as J

INDEX = pathlib.Path(__file__).resolve().parents[3] / "benchmarks" / "acceptance" / "judged-tiles.json"


def _row(item: str, tile: str):
    rows = [r for r in json.loads(INDEX.read_text())["tiles"] if r["item"] == item and r["tile"] == tile]
    assert len(rows) == 1, (item, tile, len(rows))
    return rows[0]


def _v(outcome, value=None, reason="x", cands=None):
    return {"id": 1, "outcome": outcome, "value": value, "reason": reason, "margin": None, "candidates": cands}


def _beats(b):
    return {"beats": b, "written": b, "dots": 0, "beam_levels": 1}


class TestAnswerIsANotehead(unittest.TestCase):
    def test_the_real_row_is_kept_as_an_is_a_note_answer_with_its_place(self):
        r = _row("2.347-leaves", "1")
        self.assertEqual((r["answer_kind"], r["value"]), ("is_a_note", True))
        self.assertEqual(r["answer"], "That is a notehead but the stem ink is broken")     # his words stay verbatim
        self.assertEqual(J.row_place(r), (10, 1, 9, 0))
        self.assertIsNotNone(r["page_box"])
        self.assertEqual(J.row_box(r), r["page_box"])

    def test_only_this_row_was_rekinded(self):
        rows = [r for r in json.loads(INDEX.read_text())["tiles"] if r["answer_kind"] == "is_a_note"]
        self.assertEqual([(r["item"], r["tile"]) for r in rows], [("2.347-leaves", "1")])

    def test_kept_and_written_is_right_refused_is_wrong(self):
        r = _row("2.347-leaves", "1")
        s = r["subject"]
        kept = {(s, "notehead_is_not_a_notehead"): _v("decided", False, "notehead"),
                (s, "duration"): _v("decided", _beats(0.5), "head_and_marks")}
        self.assertEqual(J.score_row(r, kept)[0], "right")
        refused = {(s, "notehead_is_not_a_notehead"): _v("decided", True, "head_box_on_accidental_ink")}
        self.assertEqual(J.score_row(r, refused)[0], "wrong")          # the control: it can fail
        self.assertEqual(J.score_row(r, {})[0], "not_found")
        narrowed = {(s, "notehead_is_not_a_notehead"): _v("decided", False), (s, "duration"): _v("narrowed")}
        self.assertEqual(J.score_row(r, narrowed)[0], "narrowed")       # a kept but unvalued head is not written: never "right"

    def test_pitch_and_value_are_not_judged(self):
        """Any decided value is right: Sean named neither."""
        r = _row("2.347-leaves", "1")
        s = r["subject"]
        for b in (0.25, 0.5, 1.0):
            S = {(s, "notehead_is_not_a_notehead"): _v("decided", False), (s, "duration"): _v("decided", _beats(b))}
            self.assertEqual(J.score_row(r, S)[0], "right", b)


class TestTileWithTwoBoxes(unittest.TestCase):
    A, B = "glyph/0/0/12/1/1", "glyph/0/0/12/1/15"

    def test_the_real_row_lists_two_boxes(self):
        r = _row("2.78-phase2-review", "5")
        self.assertEqual(r["subjects"], [self.A, self.B])
        self.assertEqual(r["value"], 0.25)

    def test_the_written_sixteenth_is_right_and_the_dropped_second_box_does_not_make_it_wrong(self):
        r = _row("2.78-phase2-review", "5")
        S = {(self.A, "duration"): _v("decided", _beats(0.25), "head_and_marks"),
             (self.B, "duration"): _v("narrowed", None, "beams_ambiguous",
                                      [{"value": _beats(1.0)}, {"value": _beats(0.5)}])}
        st, note, _m = J.score_row(r, S)
        self.assertEqual(st, "right", note)

    def test_decided_boxes_that_disagree_are_reported_not_chosen(self):
        r = _row("2.78-phase2-review", "5")
        S = {(self.A, "duration"): _v("decided", _beats(0.25)), (self.B, "duration"): _v("decided", _beats(0.5))}
        st, note, _m = J.score_row(r, S)
        self.assertEqual(st, "unscored")
        self.assertIn("SUBJECTS DISAGREE", note)

    def test_a_decided_box_with_the_wrong_value_still_fails(self):
        """The control: with the second box dropped the written one is judged, and a wrong written value is wrong."""
        r = _row("2.78-phase2-review", "5")
        S = {(self.A, "duration"): _v("decided", _beats(0.5)), (self.B, "duration"): _v("narrowed", None, "beams_ambiguous", [])}
        self.assertEqual(J.score_row(r, S)[0], "wrong")

    def test_no_box_decided_keeps_both_and_says_they_disagree(self):
        r = _row("2.78-phase2-review", "5")
        S = {(self.A, "duration"): _v("narrowed", None, "beams_ambiguous", [{"value": _beats(0.25)}, {"value": _beats(0.5)}]),
             (self.B, "duration"): _v("narrowed", None, "beams_ambiguous", [{"value": _beats(1.0)}, {"value": _beats(0.5)}])}
        st, note, _m = J.score_row(r, S)
        self.assertEqual(st, "unscored", note)


if __name__ == "__main__":
    unittest.main()
