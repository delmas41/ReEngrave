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
    return {"runs": {ar.PRIMARY_RUN: _run()}}


@pytest.fixture
def record_with_variant():
    return {"runs": {ar.PRIMARY_RUN: _run(),
                     ar.SECONDARY_RUN: dict(_run(), pooled=0.1138,
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
        run = ar._run(ar.load_record(), ar.PRIMARY_RUN)
        assert {w["work_id"] for w in run["works"]} == set(DEFAULT_WORKS)

    def test_the_eval_and_the_record_cannot_hold_separate_work_lists(self):
        """Two copies of the work set would drift the way six copies of the
        figure drifted. The eval reads the definition; it does not restate it."""
        from tools.omr.training.orchestral_eval import DEFAULT_WORKS
        assert DEFAULT_WORKS is ar.BENCHMARK_WORKS

    def test_the_record_is_stamped_with_the_current_definition(self):
        assert ar.definition_problems(ar.load_record()) == []

    def test_boulanger_is_not_in_the_pooled_set(self):
        """Runnable via `--works`, never pooled — it is the one work whose
        structure fails (43 parts of 46), so it measures segmentation and
        dominates any pool it enters. See the note on BENCHMARK_WORKS."""
        assert "boulanger-printemps-mvt1" not in ar.BENCHMARK_WORKS


class TestRendering:

    def test_every_block_moves_when_the_record_moves(self, record):
        """The property that makes a block generated rather than decorative.

        A template that hard-coded its number would render the same text for
        any record, look correct on the day it was written, and go stale in
        exactly the way this module exists to prevent. Not every block states
        the POOLED figure — `per_work` states the per-work ones — so the test
        is that each responds to the record, not that each quotes one field.
        """
        run = record["runs"][ar.PRIMARY_RUN]
        moved = {"runs": {ar.PRIMARY_RUN: dict(
            run, pooled=0.2222, edits=1111, commit="fedcba9",
            works=[dict(w, omr_ned=w["omr_ned"] + 0.1) for w in run["works"]])}}
        for name, (_, render) in ar.BLOCKS.items():
            assert render(record) != render(moved), f"{name} ignores the record"

    def test_the_figure_is_rounded_not_truncated(self, record):
        # 0.13642 -> 0.1364, and a value that rounds up must round up.
        assert ar._fmt(0.13642) == "0.1364"
        assert ar._fmt(0.13648) == "0.1365"

    def test_the_sentence_states_the_spread_best_first(self, record):
        """Eleven works do not fit a sentence and the table already lists them.
        What the sentence carries instead is the range, which is the thing the
        widening showed a pooled figure hides."""
        phrase = ar._spread_phrase(record["runs"][ar.PRIMARY_RUN])
        assert phrase == "Mahler 5 0.0455 at best, Brahms 1 0.1709 at worst"

    def test_the_headline_carries_every_work_s_row(self, record):
        text = ar.BLOCKS["headline"][1](record)
        for work in ("Mahler 5", "Beethoven 5", "Brahms 1"):
            assert f"| {work} |" in text

    def test_the_headline_states_how_many_works_it_pooled(self, record):
        """A sentence saying "three works" over a table of eleven is exactly
        the stale hand-typed fact this module exists to make impossible."""
        assert "over 3 works" in ar.BLOCKS["headline"][1](record)

    def test_no_pre_boundary_baseline_is_quoted_beside_the_figure(self, record):
        """0.3164 was pooled over three works. Standing it beside an 11-work
        figure as "an opening baseline" is the comparison the boundary forbids,
        so the generated block quotes no historical number at all."""
        assert "0.3164" not in ar.BLOCKS["headline"][1](record)


class TestNamingTheWorks:
    """Two Beethovens, two Brahmses, two Mozarts and two Tchaikovskys."""

    def test_the_symphony_number_is_part_of_the_name(self):
        assert ar._short("beethoven-sym5-mvt1") == "Beethoven 5"
        assert ar._short("mozart-sym41-mvt1") == "Mozart 41"

    def test_a_work_that_is_not_a_numbered_symphony_keeps_its_title(self):
        assert ar._short("boulanger-printemps-mvt1") == "Boulanger Printemps"

    def test_every_benchmark_work_gets_a_distinct_label(self):
        """A table with two rows called `Beethoven` looks fine and cannot be
        read. This is the property, not the spelling of any one label."""
        labels = ar._labels(list(ar.BENCHMARK_WORKS))
        assert len(set(labels.values())) == len(ar.BENCHMARK_WORKS)

    def test_two_movements_of_one_work_are_separated_by_movement(self):
        labels = ar._labels(["mahler-sym5-mvt1", "mahler-sym5-mvt4"])
        assert sorted(labels.values()) == ["Mahler 5 mvt1", "Mahler 5 mvt4"]


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
        run = rec["runs"][ar.PRIMARY_RUN]
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
                                        run_name=ar.SECONDARY_RUN,
                                        previous=first, commit="bbb")
        assert set(second["runs"]) == {ar.PRIMARY_RUN, ar.SECONDARY_RUN}
        assert second["runs"][ar.PRIMARY_RUN]["commit"] == "aaa"
        assert second["runs"][ar.SECONDARY_RUN]["commit"] == "bbb"

    def test_the_variant_clause_appears_only_when_it_is_recorded(
            self, record, record_with_variant):
        """One run cannot produce both configurations, so the headline states
        the second only when it is actually on record."""
        alone = ar.BLOCKS["headline"][1](record)
        both = ar.BLOCKS["headline"][1](record_with_variant)
        assert "no-direction-text" not in alone
        assert "0.1138" not in alone
        assert "no-direction-text" in both and "0.1138" in both

    def test_the_headline_leads_with_the_DEFAULT_configuration(self, record):
        """Which is the one that reads direction text, since 2026-09-02. The
        constants are named for the configuration and not for which is the
        default, because `DEFAULT_RUN` stopped naming the default the moment
        the flag flipped."""
        assert ar.PRIMARY_RUN == ar.WITH_DIRECTION_TEXT
        assert "0.1364" in ar.BLOCKS["headline"][1](record)

    def test_a_renamed_key_is_dropped_not_carried(self):
        """The 2026-09-02 rename left `default` holding a real pooled figure
        under a name that had stopped meaning anything, beside the two keys
        that still did. A measured number under a dead label is exactly the
        hazard this module exists to remove."""
        stale = {"runs": {ar.PRIMARY_RUN: _run(), "default": _run()}}
        assert set(ar.prune_unknown_runs(stale)["runs"]) == {ar.PRIMARY_RUN}

    def test_pruning_leaves_a_clean_record_untouched(self):
        clean = {"runs": {ar.PRIMARY_RUN: _run(), ar.SECONDARY_RUN: _run()}}
        assert ar.prune_unknown_runs(clean) is clean

    def test_folding_a_run_in_also_prunes(self):
        """So the next measurement finishes a rename without anyone noticing
        there was one to finish."""
        stale = {"runs": {"default": _run()}}
        out = ar.record_from_results(
            [self._result("a", 0.1, 10)], run_name=ar.PRIMARY_RUN,
            previous=stale, commit="x")
        assert set(out["runs"]) == {ar.PRIMARY_RUN}

    def test_every_known_run_has_a_constant(self):
        """A key the record may hold that the code cannot name would be pruned
        by its own guard the next time anything wrote the file."""
        assert ar.KNOWN_RUNS == {ar.WITH_DIRECTION_TEXT, ar.WITHOUT_DIRECTION_TEXT}
        assert ar.PRIMARY_RUN in ar.KNOWN_RUNS
        assert ar.SECONDARY_RUN in ar.KNOWN_RUNS

    def test_a_record_with_only_the_secondary_run_is_refused(self):
        """It would otherwise publish the no-OCR figure as the headline."""
        with pytest.raises(ValueError, match="direction_text"):
            ar.BLOCKS["headline"][1]({"runs": {ar.SECONDARY_RUN: _run()}})

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

    def test_the_record_is_stamped_with_the_work_set_it_measured(self):
        rec = ar.record_from_results(
            [self._result("b", 0.1, 10), self._result("a", 0.2, 20)],
            commit="c0ffee")
        assert rec["benchmark"]["works"] == ["a", "b"]
        assert rec["benchmark"]["since"] == ar.BENCHMARK_SINCE

    def test_a_run_over_the_old_work_set_is_dropped_not_kept(self):
        """The two configurations are measured in separate commands, so a
        definition change always has a moment where one is re-measured and the
        other is not. Keeping the stale one would render an 11-work default
        beside a 3-work variant in one paragraph, with nothing saying so."""
        old = ar.record_from_results([self._result("a", 0.1, 10)],
                                     run_name=ar.SECONDARY_RUN,
                                     commit="old")
        new = ar.record_from_results(
            [self._result("a", 0.1, 10), self._result("b", 0.2, 20)],
            previous=old, commit="new")
        assert set(new["runs"]) == {ar.PRIMARY_RUN}
        assert new["benchmark"]["works"] == ["a", "b"]


class TestTheDefinitionBoundary:
    """A figure is about a work set as much as about the pipeline.

    `--check` compares the docs to the record. If the record was measured over
    a different set of works, the docs and the record can agree PERFECTLY and
    both describe a benchmark the code no longer runs — which is the quiet
    failure, worse than the loud one.
    """

    def _record(self, works, **stamp):
        run = {"pooled": 0.1, "edits": 1, "truth_symbols": 1,
               "pred_symbols": 1, "commit": "x",
               "works": [{"work_id": w, "omr_ned": 0.1, "edits": 1,
                          "pitch_recall": 1.0, "pitch_precision": 1.0,
                          "duration_rate": 1.0} for w in works]}
        rec = {"runs": {ar.PRIMARY_RUN: run}}
        if stamp.get("stamped", True):
            rec["benchmark"] = {"name": ar.BENCHMARK_NAME,
                                "since": ar.BENCHMARK_SINCE,
                                "works": sorted(stamp.get("stamp", works))}
        return rec

    def test_a_record_with_the_current_work_set_is_clean(self):
        rec = self._record(ar.BENCHMARK_WORKS)
        assert ar.definition_problems(rec) == []

    def test_a_record_with_no_stamp_is_reported_as_pre_boundary(self):
        """Every record written before 2026-09-02 has no `benchmark` key, so
        being pre-boundary is DETECTED rather than assumed."""
        rec = self._record(ar.BENCHMARK_WORKS, stamped=False)
        problems = ar.definition_problems(rec)
        assert len(problems) == 1
        assert "predates the benchmark-definition boundary" in problems[0]

    def test_a_record_over_the_old_three_works_is_refused(self):
        three = ["beethoven-sym5-mvt1", "brahms-sym1-mvt1", "mahler-sym5-mvt1"]
        problems = ar.definition_problems(self._record(three))
        assert problems and "not measured:" in problems[0]

    def test_a_work_no_longer_in_the_benchmark_is_named(self):
        rec = self._record(list(ar.BENCHMARK_WORKS) + ["boulanger-printemps-mvt1"])
        problems = ar.definition_problems(rec)
        assert problems and "no longer in the benchmark" in problems[0]

    def test_a_stamp_that_disagrees_with_its_own_run_is_refused(self):
        """The stamp is written from the works measured, so this can only
        happen by hand-editing — which the record says not to do."""
        rec = self._record(ar.BENCHMARK_WORKS,
                           stamp=list(ar.BENCHMARK_WORKS)[:2])
        assert any("internally inconsistent" in p
                   for p in ar.definition_problems(rec))

    def test_check_surfaces_a_definition_problem_before_any_text_problem(self):
        rec = self._record(ar.BENCHMARK_WORKS, stamped=False)
        assert ar.check(rec)[0].startswith("current-accuracy.json has no")

    def test_update_refuses_to_write_a_figure_from_another_definition(self):
        """The WRITE direction needs its own guard. Writing a 3-work figure
        into the paragraph leaves the docs and the record agreeing perfectly
        about a benchmark the code does not run — and `check()` is then silent,
        because it compares exactly those two things."""
        three = ["beethoven-sym5-mvt1", "brahms-sym1-mvt1", "mahler-sym5-mvt1"]
        with pytest.raises(ValueError, match="refusing to write"):
            ar.update(self._record(three))
