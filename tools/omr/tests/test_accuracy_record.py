"""The docs must not drift from the measured accuracy figure.

The failure this guards is not a typo. On 2026-09-01 the pooled figure was
stated in the present tense in six places across four files; two branches landed
within an hour having each edited a different copy; the merge conflicted in
exactly one file, which therefore got resolved with a measurement and came out
RIGHT, while the three that auto-merged cleanly kept text describing one branch
and came out wrong.

`68be549` fixed the bigger half by DELETING the duplication — the figure is
stated in one place now, and three copies that cannot exist cannot go stale.
What is left is that the surviving copy is hand-typed, so measuring and
forgetting to edit it goes quietly wrong with nothing to disagree with. That is
what these guard.

The test that matters is the whole-repo one — `test_claude_md_agrees_with_the_record`
— which is the same `--check` a person runs. The rest pin the machinery it rests
on.
"""
from __future__ import annotations

import json

import pytest

from tools.omr import accuracy_record as ar


@pytest.fixture
def record():
    return {"runs": {ar.DEFAULT_RUN: _run()}}


@pytest.fixture
def record_with_variant():
    return {"runs": {ar.DEFAULT_RUN: _run(),
                     ar.DIRECTION_TEXT_RUN: dict(_run(), pooled=0.1138,
                                                 edits=822, commit="dc74488")}}


def _run():
    return {
        "pooled": 0.13642,
        "edits": 966,
        "truth_symbols": 3696,
        "pred_symbols": 3385,
        "commit": "abc1234",
        "works": [
            {"work_id": "mahler-sym5-mvt1", "omr_ned": 0.0455, "edits": 86,
             "pitch_recall": 0.917, "pitch_precision": 0.917, "duration_rate": 0.864},
            {"work_id": "brahms-sym1-mvt1", "omr_ned": 0.1709, "edits": 675,
             "pitch_recall": 0.956, "pitch_precision": 0.955, "duration_rate": 0.992},
            {"work_id": "beethoven-sym5-mvt1", "omr_ned": 0.1649, "edits": 205,
             "pitch_recall": 1.0, "pitch_precision": 1.0, "duration_rate": 1.0},
        ],
    }


class TestTheRepositoryItself:

    def test_claude_md_agrees_with_the_record(self):
        """Measure, forget to edit the one surviving copy, and this goes red."""
        assert ar.check() == []

    def test_there_is_exactly_one_place_the_figure_is_stated(self):
        """`68be549`'s half of the fix, pinned.

        A second block would mean a second copy, which is the duplication that
        commit removed. If another document needs the number, it points here.
        """
        assert list(ar.BLOCKS) == ["headline"]

    def test_every_block_name_is_used_exactly_once(self):
        from collections import Counter
        seen: Counter = Counter()
        for path in {ar.ROOT / f for f, _ in ar.BLOCKS.values()}:
            for m in ar._BEGIN.finditer(path.read_text()):
                seen[m.group(1)] += 1
        assert dict(seen) == {name: 1 for name in ar.BLOCKS}

    def test_the_record_covers_the_whole_benchmark(self):
        from tools.omr.training.orchestral_eval import DEFAULT_WORKS
        run = ar._run(ar.load_record(), ar.DEFAULT_RUN)
        assert {w["work_id"] for w in run["works"]} == set(DEFAULT_WORKS)


class TestRendering:

    def test_every_block_moves_when_the_record_moves(self, record):
        """The property that makes a block generated rather than decorative.

        A template that hard-coded its number would render the same text for
        any record, look correct on the day it was written, and go stale in
        exactly the way this module exists to prevent. Not every block states
        the POOLED figure — `per_work` states the per-work ones — so the test
        is that each responds to the record, not that each quotes one field.
        """
        run = record["runs"][ar.DEFAULT_RUN]
        moved = {"runs": {ar.DEFAULT_RUN: dict(
            run, pooled=0.2222, edits=1111, commit="fedcba9",
            works=[dict(w, omr_ned=w["omr_ned"] + 0.1) for w in run["works"]])}}
        for name, (_, render) in ar.BLOCKS.items():
            assert render(record) != render(moved), f"{name} ignores the record"

    def test_the_figure_is_rounded_not_truncated(self, record):
        # 0.13642 -> 0.1364, and a value that rounds up must round up.
        assert ar._fmt(0.13642) == "0.1364"
        assert ar._fmt(0.13648) == "0.1365"

    def test_works_are_named_in_ascending_score_order(self, record):
        phrase = ar._works_phrase(record["runs"][ar.DEFAULT_RUN])
        assert phrase == "Mahler 0.0455, Beethoven 0.1649, Brahms 0.1709"

    def test_the_headline_carries_every_work_s_row(self, record):
        text = ar.BLOCKS["headline"][1](record)
        for work in ("Mahler", "Beethoven", "Brahms"):
            assert f"| {work} |" in text


class TestRewriting:

    def _doc(self, body="anything at all"):
        return (f"before\n<!-- accuracy:begin name=headline -->\n{body}\n"
                f"<!-- accuracy:end -->\nafter\n")

    def test_a_block_is_replaced_and_its_surroundings_are_not(self, record):
        new, seen = ar._rewrite(self._doc(), record, "x.md")
        assert seen == ["headline"]
        assert new.startswith("before\n") and new.endswith("after\n")
        assert "0.1364" in new and "anything at all" not in new

    def test_rewriting_is_idempotent(self, record):
        once, _ = ar._rewrite(self._doc(), record, "x.md")
        twice, _ = ar._rewrite(once, record, "x.md")
        assert once == twice

    def test_a_document_with_no_block_is_untouched(self, record):
        text = "nothing to see\n"
        assert ar._rewrite(text, record, "x.md")[0] == text

    def test_an_unknown_block_name_is_an_error(self, record):
        text = "<!-- accuracy:begin name=invented -->\nx\n<!-- accuracy:end -->\n"
        with pytest.raises(ValueError, match="unknown accuracy block"):
            ar._rewrite(text, record, "x.md")

    def test_a_block_with_no_end_marker_is_an_error(self, record):
        with pytest.raises(ValueError, match="no end marker"):
            ar._rewrite("<!-- accuracy:begin name=headline -->\nx\n", record, "x.md")


class TestBuildingTheRecord:

    def _result(self, work_id, ned, ed, truth=100, pred=90):
        return {
            "work_id": work_id,
            "omr_ned": {"omr_ned": ned, "omr_ed": ed,
                        "truth_symbols": truth, "pred_symbols": pred},
            "notes": {"pitch_recall": 0.9, "pitch_precision": 0.9,
                      "duration_rate": 0.9},
        }

    def test_pooled_is_edits_over_both_symbol_counts(self):
        rec = ar.record_from_results(
            [self._result("a", 0.1, 10), self._result("b", 0.2, 20)],
            commit="deadbee")
        run = rec["runs"][ar.DEFAULT_RUN]
        assert run["edits"] == 30
        assert run["truth_symbols"] == 200 and run["pred_symbols"] == 180
        assert run["pooled"] == pytest.approx(30 / 380)

    def test_recording_one_run_leaves_the_other_alone(self):
        """`--direction-text` is a second configuration, measured separately.

        One run cannot produce both, so recording either must not clobber the
        other — otherwise the surviving paragraph would quote a stale figure for
        whichever configuration was not measured last.
        """
        first = ar.record_from_results([self._result("a", 0.1, 10)],
                                       commit="aaa")
        second = ar.record_from_results([self._result("a", 0.2, 20)],
                                        run_name=ar.DIRECTION_TEXT_RUN,
                                        previous=first, commit="bbb")
        assert set(second["runs"]) == {ar.DEFAULT_RUN, ar.DIRECTION_TEXT_RUN}
        assert second["runs"][ar.DEFAULT_RUN]["commit"] == "aaa"
        assert second["runs"][ar.DIRECTION_TEXT_RUN]["commit"] == "bbb"

    def test_the_variant_clause_appears_only_when_it_is_recorded(
            self, record, record_with_variant):
        assert "--direction-text" not in ar.BLOCKS["headline"][1](record)
        assert "--direction-text" in ar.BLOCKS["headline"][1](record_with_variant)

    def test_an_unscored_work_refuses_the_record(self):
        """A pooled figure over a subset would be stated as the whole thing."""
        results = [self._result("a", 0.1, 10)]
        results.append({"work_id": "b", "omr_ned": None,
                        "notes": {"pitch_recall": 0, "pitch_precision": 0,
                                  "duration_rate": 0}})
        with pytest.raises(ValueError, match="no OMR-NED score"):
            ar.record_from_results(results)

    def test_the_record_round_trips_through_json(self):
        rec = ar.record_from_results([self._result("a", 0.1, 10)], commit="c0ffee")
        assert json.loads(json.dumps(rec)) == rec
