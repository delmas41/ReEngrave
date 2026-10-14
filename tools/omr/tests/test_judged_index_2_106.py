"""ROADMAP 2.106 step 2 -- the index of Sean's answers and the re-scorer.

Every parser case has its twin that must NOT parse (a control that can fail),
and the scorer is run on a tiny synthetic record in which each status
(right / wrong / narrowed / abstained / not_found) is reachable, so a scorer
that returns "right" for everything cannot pass.
"""
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from tools.omr.staged import judged as J


class TestParseAnswer(unittest.TestCase):

    def test_values_become_beats_in_quarters(self):
        for text, want in (("4", 1.0), ("Dot 4", 1.5), ("8th", 0.5),
                           ("Half", 2.0), ("dotted quarter", 1.5),
                           ("16th", 0.25), ("2", 2.0), ("Eighth", 0.5)):
            self.assertEqual(J.parse_answer(text), ("duration", want), text)

    def test_rests_are_rests_not_durations(self):
        self.assertEqual(J.parse_answer("8 rest"), ("rest", 0.5))
        self.assertEqual(J.parse_answer("6. 8 rest"), ("rest", 0.5))
        self.assertEqual(J.parse_answer("Whole rest"), ("rest", 4.0))

    def test_not_a_note_answers(self):
        for text, what in (("Barline", "barline"), ("Ledger lines", "ledger_line"),
                           ("Alto clef", "clef"), ("Slash", "tremolo"),
                           ("Not a note - dynamic p", "dynamic")):
            self.assertEqual(J.parse_answer(text), ("not_a_note", what), text)

    def test_arcs(self):
        self.assertEqual(J.parse_answer("Tie"), ("arc", "tie"))
        self.assertEqual(J.parse_answer("Slur - different notes"), ("arc", "slur"))
        self.assertEqual(J.parse_answer("Tie -- as a rule, wherever the arc sits"),
                         ("arc", "tie"))

    def test_several_values(self):
        self.assertEqual(J.parse_answer("dotted quarter, quarter"),
                         ("duration_multi", [1.5, 1.0]))

    def test_an_explanation_is_never_turned_into_a_value_NEGATIVE_CONTROL(self):
        """The twins of the cases above: said with more words, or a thing the
        parser does not know, they stay `other` with no value (rule 8)."""
        for text in ("2 half notes and a trem slash",
                     "eighth (2 eighths on one beam)",
                     "4 (part of a tuplet: 3 quarters)",
                     "NOTES: the box sits over two different noteheads just "
                     "right of the sf (not the dynamic)",
                     "6/8, two voices. Bottom: 8th, 8th rest",
                     "Connected to note below", "", None, 4):
            kind, value = J.parse_answer(text)
            self.assertEqual(kind, "other", text)
            self.assertIsNone(value, text)


class TestIndex(unittest.TestCase):

    def _gallery(self, root, name, answers, tiles):
        d = root / name
        d.mkdir(parents=True)
        (d / "answers.json").write_text(json.dumps(answers))
        (d / "manifest.json").write_text(json.dumps(tiles))
        return d

    def test_every_answer_shape_joins_its_subject(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            # flat, keyed by number
            self._gallery(root, "a", {"1": "Dot 4", "2": "Tie"},
                          {"tiles": [{"n": 1, "subject": "glyph/1/0/2/3/4",
                                      "doc": "litolff",
                                      "question": "What is the printed value"},
                                     {"n": 2, "subject": "glyph/1/0/2/3/5",
                                      "movement": "brah"}]})
            # `answers` of dicts, keyed tile_NN, hidden.key
            self._gallery(root, "b", {"date": "2026-10-11", "answers":
                          {"tile_01": {"sean": "8", "verdict": "right"}}},
                          {"tiles": [{"id": "tile_01", "hidden": {
                              "key": "glyph/2/0/0/0/0", "movement": "litolff"}}]})
            # a list manifest, answers keyed brahms_01 off the file name
            self._gallery(root, "c", {"brahms_01": "16th"},
                          [{"n": 1, "tile": "brahms_01.png",
                            "subject": "glyph/0/0/10/2/5",
                            "plate": "Breitkopf 317803"}])
            idx = J.build_index(root)
            by = {(r["item"], r["tile"]): r for r in idx["tiles"]}
            self.assertEqual(idx["n_tiles"], 4)
            self.assertEqual(by[("a", "1")]["subject"], "glyph/1/0/2/3/4")
            self.assertEqual(by[("a", "1")]["value"], 1.5)
            self.assertEqual(by[("a", "1")]["doc"], "litolff")
            self.assertEqual(by[("a", "1")]["question_kind"], "duration")
            self.assertEqual(by[("a", "2")]["doc"], "brahms")
            self.assertEqual(by[("a", "2")]["answer_kind"], "arc")
            self.assertEqual(by[("b", "tile_01")]["subject"], "glyph/2/0/0/0/0")
            self.assertEqual(by[("b", "tile_01")]["date"], "2026-10-11")
            self.assertEqual(by[("c", "brahms_01")]["doc"], "brahms")
            self.assertEqual(by[("c", "brahms_01")]["value"], 0.25)

    def test_a_tile_with_no_manifest_row_keeps_its_answer_and_no_subject(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self._gallery(root, "x", {"7": "8th"}, {"tiles": [{"n": 1}]})
            (r,) = J.build_index(root)["tiles"]
            self.assertEqual(r["answer"], "8th")
            self.assertIsNone(r["subject"])
            self.assertEqual(r["subject_kind"], "none")

    def test_the_committed_index_is_current(self):
        """A new `answers.json` with no rebuild fails here: run
        `python3 -m tools.omr.staged.judged build`."""
        if not J.PRINT_DIR.exists() or not J.INDEX_PATH.exists():
            self.skipTest("no out/print or no committed index in this checkout")
        have = json.loads(J.INDEX_PATH.read_text())["tiles"]
        self.assertEqual(have, J.build_index()["tiles"])
        self.assertGreater(len(have), 100)       # the control: it is not empty


def _verdict(i, subject, quantity, outcome, value, reason="r", supersedes=None,
             candidates=(), margin=None):
    return {"id": "vrd:%d" % i, "subject": subject, "quantity": quantity,
            "outcome": outcome, "value": value, "decider": "d", "reason": reason,
            "considered": ["obs:%d" % k for k in range(30)],
            "supersedes": supersedes, "margin": margin,
            "candidates": list(candidates), "detail": {}}


def _dur(beats):
    return {"beats": beats, "written": beats}


class TestScorer(unittest.TestCase):

    def _record(self, tmp, verdicts, boxes=()):
        p = pathlib.Path(tmp) / "rec.json"
        obs = [{"id": "obs:%d" % i, "subject": s, "quantity": "glyph_box",
                "value": ["noteheadBlackInSpace", 1, 2, 3, 4],
                "detail": {"bbox_page_px": b}} for i, (s, b) in enumerate(boxes)]
        p.write_text(json.dumps({"record": {"observations": obs,
                                            "abstentions": [],
                                            "verdicts": verdicts},
                                 "provenance": {}}))
        return p

    def _row(self, tile, subject, answer, doc="litolff", page_box=None, qk="duration"):
        kind, value = J.parse_answer(answer)
        return {"item": "t", "tile": tile, "doc": doc, "subject": subject,
                "subjects": None, "subject_kind": "glyph", "page_box": page_box,
                "answer": answer, "question_kind": qk, "answer_kind": kind,
                "value": value, "date": None, "control": False,
                "followup": False}

    def test_each_status_is_reachable_and_the_scorer_is_not_a_yes_man(self):
        a, b, c, d, e = ("glyph/0/0/0/0/%d" % i for i in range(5))
        vs = [
            _verdict(1, a, "duration", "decided", _dur(1.5)),
            _verdict(2, b, "duration", "decided", _dur(0.5)),
            _verdict(3, c, "duration", "narrowed", None,
                     candidates=[{"value": _dur(0.5), "support": 1},
                                 {"value": _dur(1.0), "support": 1}]),
            _verdict(4, d, "duration", "abstained", None, reason="owned_by_another_staff"),
        ]
        idx = {"tiles": [self._row("1", a, "Dot 4"),     # right
                         self._row("2", b, "4"),         # wrong: decided 0.5
                         self._row("3", c, "4"),         # narrowed, answer in set
                         self._row("4", d, "4"),         # abstained
                         self._row("5", e, "4"),         # not found
                         self._row("6", a, "4", doc="brahms")]}   # other doc
        with tempfile.TemporaryDirectory() as tmp:
            rep = J.score(idx, self._record(tmp, vs), "litolff")
        st = {t["tile"]: t["status"] for t in rep["tiles"]}
        self.assertEqual(st, {"1": "right", "2": "wrong", "3": "narrowed",
                              "4": "abstained", "5": "not_found"})
        self.assertEqual(rep["totals"].get("other_doc"), 1)

    def test_a_narrowing_without_the_answer_is_wrong(self):
        a = "glyph/0/0/0/0/0"
        vs = [_verdict(1, a, "duration", "narrowed", None,
                       candidates=[{"value": _dur(0.5), "support": 1},
                                   {"value": _dur(0.25), "support": 1}])]
        with tempfile.TemporaryDirectory() as tmp:
            rep = J.score({"tiles": [self._row("1", a, "Half")]},
                          self._record(tmp, vs), "litolff")
        self.assertEqual(rep["tiles"][0]["status"], "wrong")

    def test_the_standing_verdict_is_the_unsuperseded_one(self):
        a = "glyph/0/0/0/0/0"
        vs = [_verdict(1, a, "duration", "decided", _dur(0.5)),
              _verdict(2, a, "duration", "decided", _dur(1.0), supersedes="vrd:1")]
        with tempfile.TemporaryDirectory() as tmp:
            rep = J.score({"tiles": [self._row("1", a, "4")]},
                          self._record(tmp, vs), "litolff")
        self.assertEqual(rep["tiles"][0]["status"], "right")

    def test_a_refused_head_where_sean_read_a_note_is_wrong_not_missing(self):
        a = "glyph/0/0/0/0/0"
        vs = [_verdict(1, a, "notehead_is_not_a_notehead", "decided", True,
                       reason="stacked_head_duplicate")]
        with tempfile.TemporaryDirectory() as tmp:
            rep = J.score({"tiles": [self._row("1", a, "Half")]},
                          self._record(tmp, vs), "litolff")
        self.assertEqual(rep["tiles"][0]["status"], "wrong")

    def test_rest_not_a_note_and_arc_comparators(self):
        a, b, c = ("glyph/0/0/0/0/%d" % i for i in (350000, 1, 2))
        vs = [_verdict(1, a, "unboxed_ink_is_a_rest", "decided", "eighth",
                       reason="rest8th_shape", margin=0.12),
              _verdict(2, b, "notehead_is_not_a_notehead", "decided", True,
                       reason="clipped_fragment"),
              _verdict(3, c, "arc_kind", "decided", "slur")]
        idx = {"tiles": [self._row("1", a, "8 rest", qk="unknown"),
                         self._row("2", b, "Barline", qk="identity"),
                         self._row("3", c, "Tie", qk="arc")]}
        with tempfile.TemporaryDirectory() as tmp:
            rep = J.score(idx, self._record(tmp, vs), "litolff")
        st = {t["tile"]: t["status"] for t in rep["tiles"]}
        self.assertEqual(st, {"1": "right", "2": "right", "3": "wrong"})
        self.assertEqual(rep["tiles"][0]["margin"], 0.12)    # the margin rides along

    def test_a_tile_with_no_document_is_kept_only_where_the_page_box_agrees(self):
        a = "glyph/0/0/0/0/0"
        vs = [_verdict(1, a, "duration", "decided", _dur(1.0))]
        row = self._row("1", a, "4", doc=None, page_box=[100.0, 100.0, 140.0, 140.0])
        with tempfile.TemporaryDirectory() as tmp:
            here = self._record(tmp, vs, boxes=[(a, [105.0, 105.0, 135.0, 135.0])])
            rep = J.score({"tiles": [row]}, here, "litolff")
            self.assertEqual(rep["tiles"][0]["status"], "right")
            self.assertEqual(rep["tiles"][0]["doc_by"], "page_box")
            elsewhere = pathlib.Path(tmp) / "other.json"
            elsewhere.write_text(json.dumps({"record": {
                "observations": [{"id": "obs:1", "subject": a, "quantity":
                                  "glyph_box", "value": [], "detail": {
                                      "bbox_page_px": [900.0, 900.0, 940.0, 940.0]}}],
                "abstentions": [], "verdicts": vs}}))
            rep2 = J.score({"tiles": [row]}, elsewhere, "litolff")
            self.assertEqual(rep2["tiles"], [])
            self.assertEqual(rep2["totals"].get("doc_unresolved"), 1)

    def test_the_stream_reads_objects_that_straddle_a_chunk(self):
        vs = [_verdict(i, "glyph/0/0/0/0/%d" % i, "duration", "decided", _dur(1.0))
              for i in range(40)]
        with tempfile.TemporaryDirectory() as tmp:
            p = self._record(tmp, vs)
            got = [v["id"] for v in J.iter_array(p, "verdicts", chunk=257)]
        self.assertEqual(got, ["vrd:%d" % i for i in range(40)])


if __name__ == "__main__":
    unittest.main()
