"""A signal the pipeline reads must survive into the file.

Seven times the defect has been the same: recognised correctly, then dropped on
the way out. Six of the seven were found forensically, after a metric bucket had
grown large enough for someone to open it; the seventh was found by comparing
element counts between the truth and our export, in two greps, before anyone
looked at its bucket.

This is that comparison, kept. The point is the eighth: it should be caught the
day it appears rather than after a day of forensics.

⚠️ AND THE TENTH WAS THE CHECK'S OWN. `<ornaments>` — truth 12 engraved, 131
scan, ours ZERO — was reported by nothing, because `compare()` iterated a
hand-written 19-name `VISIBLE` dict and an element in neither `VISIBLE` nor
`KNOWN_GAPS` failed nothing. The set is now DERIVED from the truth documents,
inside `<measure>`, rolled up to the shallowest missing element, with a
three-name `NOT_NOTATION` deny-list for what survives and is still invisible.
The tests below are written against that: `TestTheSetIsDerived` is the new
half, and `test_the_old_allow_list_is_gone` is the one that would go green
again if someone reinstated it.

THE COMPARISON'S OWN SIDE IS GENERATED HERE. `export_coverage` exports the
stored transcription itself rather than reading the `.omr.musicxml` beside it,
because that file is a gitignored artifact of whatever tree last ran the eval —
which made these tests both falsely RED (a `--direction-text` run leaves
`<words>`) and, worse and unnamed at the time, falsely GREEN (break the exporter
and they read yesterday's file and pass). `test_the_leftover_export_is_not_a_
fallback` is the guard on that, and it is the test to read first if this file
ever starts looking too clever.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.omr import export_coverage as ec


#: ⚠️ EVERY FIXTURE HERE PUTS ITS NOTATION INSIDE A `<measure>`, because that
#: is now the check's scope and not an incidental detail of the sample. A
#: fragment outside one is the file's header, which this check does not watch.
TRUTH = """<score-partwise>
  <part><measure>
    <note><pitch><step>C</step><octave>4</octave></pitch>
      <type>quarter</type><dot/><accidental>sharp</accidental>
      <beam number="1">begin</beam>
      <notations><slur number="1" type="start"/><fermata type="upright"/></notations>
    </note>
    <barline><bar-style>light-heavy</bar-style></barline>
  </measure></part>
</score-partwise>"""


def _ours(**drop):
    """The same content, with named elements removed."""
    xml = TRUTH
    for name in drop:
        xml = xml.replace(f"<{name}", "<dropped")
    return xml


def _run(work="w", *, truth=TRUTH, ours=TRUTH, direction=None, stale=False):
    """A `Run` built by hand, so the configuration logic is testable offline."""
    result = {"pages": []}
    if direction is not None:
        result["direction_text"] = direction
    return ec.Run(work=work, truth=truth, ours=ours, result=result,
                  stale_export=stale)


RAN = {"available": True, "n_placed": 3, "pages": []}
RAN_SILENT = {"available": True, "n_placed": 0, "pages": []}
ABSTAINED = {"available": False, "reason": "ImportError: no surya",
             "error_class": "ImportError", "looks_like_a_bug": False}


class TestTheComparison:

    def test_identical_files_have_no_gap(self):
        assert ec.compare(TRUTH, TRUTH) == []

    def test_an_element_we_emit_none_of_is_a_gap(self):
        gaps = ec.compare(TRUTH, _ours(accidental=1))
        assert ("accidental", 1, 0) in gaps

    def test_emitting_FEWER_is_not_a_gap(self):
        """The distinction the whole check rests on.

        Truth 5, ours 3 is a recognition shortfall and belongs to the accuracy
        metric. Truth 5, ours 0 is categorical — nothing consumes it — and that
        is what every one of the seven looked like. Conflating them would make
        this fire on every page and get it deleted.
        """
        truth = "<a><beam>1</beam><beam>2</beam><beam>3</beam></a>"
        ours = "<a><beam>1</beam></a>"
        assert ec.compare(truth, ours) == []

    def test_metadata_and_layout_are_out_of_scope(self):
        """A MusicXML file is mostly not notation, and a check that said so
        would list 55 elements and be ignored.

        ⚠️ NOW A STRUCTURAL FACT rather than a curated one: MusicXML puts the
        header — `<identification>`, `<defaults>`, `<part-list>` and the MIDI
        blocks inside it — OUTSIDE `<measure>`, and the check reads the music
        subtree. Nothing was hand-listed to make this pass.
        """
        truth = ("<score-partwise><identification><midi-program>1"
                 "</midi-program><tenths>7</tenths><software>x</software>"
                 "</identification><part><measure><note/></measure></part>"
                 "</score-partwise>")
        ours = "<score-partwise><part><measure><note/></measure></part>"
        assert ec.compare(truth, ours) == []

    def test_an_element_only_we_emit_is_not_a_gap(self):
        assert ec.compare("<a></a>", TRUTH) == []

    def test_every_known_gap_carries_a_reason(self):
        for name, why in ec.KNOWN_GAPS.items():
            assert len(why) > 40, f"{name}'s reason is too thin to act on"

    def test_every_flag_dependent_gap_is_a_known_gap(self):
        """A flag can only ever SPEND an explanation that exists."""
        assert ec.FLAG_DEPENDENT <= set(ec.KNOWN_GAPS)

    def test_metronome_is_NOT_flag_dependent(self):
        """Measured, not reasoned: on a `--direction-text` run of the whole
        benchmark `<metronome>` is still absent, because the reader writes a
        tempo mark as <words> and the structured form is not built. Exempting
        it would hide the regression on the day somebody builds it."""
        assert "metronome" not in ec.FLAG_DEPENDENT
        assert "metronome" in ec.KNOWN_GAPS


def _truth_with(inner: str) -> str:
    """A minimal well-formed truth carrying `inner` inside a `<measure>`."""
    return (f"<score-partwise><part><measure>{inner}</measure></part>"
            "</score-partwise>")


class TestTheSetIsDerived:
    """THE HOLE THE TENTH GAP FELL THROUGH, and the rules that close it.

    `compare()` used to iterate a hand-written 19-name `VISIBLE` dict, so an
    element in neither `VISIBLE` nor `KNOWN_GAPS` was checked by NOTHING — and
    nobody had to write anything down for that to be true. The default is now
    "fails until someone writes down why".
    """

    def test_the_old_allow_list_is_gone(self):
        """⚠️ The regression guard on the whole rewrite. Reinstating a curated
        set of names to check reinstates the blind spot."""
        assert not hasattr(ec, "VISIBLE"), (
            "a hand-written allow-list is back — that is the mechanism that "
            "hid <ornaments> from the module built to report it")

    def test_an_element_NOBODY_hand_listed_is_reported(self):
        """The tenth gap, in miniature. `<ornaments>` was in no list."""
        truth = _truth_with("<note><notations><ornaments><trill-mark/>"
                            "</ornaments></notations></note>")
        ours = _truth_with("<note><notations/></note>")
        assert ("ornaments", 1, 0) in ec.compare(truth, ours)

    def test_the_old_rule_would_have_MISSED_it(self):
        """The non-vacuity check on the test above: the same input under a
        19-name allow-list that did not contain `ornaments` reports nothing.
        Written out rather than asserted against deleted code."""
        truth = _truth_with("<note><notations><ornaments><trill-mark/>"
                            "</ornaments></notations></note>")
        ours = _truth_with("<note><notations/></note>")
        old_visible = {"accidental", "articulations", "beam", "slur", "wedge"}
        t, o = ec.element_counts(truth), ec.element_counts(ours)
        old_answer = [n for n in sorted(old_visible) if t[n] > 0 and o[n] == 0]
        assert old_answer == []

    def test_a_child_of_a_missing_element_is_ROLLED_UP(self):
        """The ornaments/tremolo arithmetic, made structural.

        The handoff listed `<ornaments>` 12 and `tremolo` 12 as two findings.
        They are the same twelve elements — the engraved truth holds twelve
        `<ornaments>` containing twelve `<tremolo>` and nothing else. An
        element whose own parent is also missing is that gap seen from the
        inside, and reporting both is what turns this into the 55-line report
        nobody reads.
        """
        truth = _truth_with("<note><notations><ornaments>"
                            '<tremolo type="single">1</tremolo>'
                            "</ornaments></notations></note>")
        ours = _truth_with("<note><notations/></note>")
        names = [n for n, _, _ in ec.compare(truth, ours)]
        assert names == ["ornaments"]

    def test_a_child_whose_parent_we_DO_emit_is_reported(self):
        """The other half of the rollup, and the one that keeps it from being
        a suppression rule: `<tremolo>` is a gap in its own right once
        `<ornaments>` comes out."""
        truth = _truth_with("<note><notations><ornaments>"
                            '<tremolo type="single">1</tremolo>'
                            "</ornaments></notations></note>")
        ours = _truth_with("<note><notations><ornaments><trill-mark/>"
                           "</ornaments></notations></note>")
        names = [n for n, _, _ in ec.compare(truth, ours)]
        assert names == ["tremolo"]

    def test_the_rollup_tests_EVERY_ancestor_not_just_the_parent(self):
        """⚠️ THIS TEST WAS VACUOUS WHEN FIRST WRITTEN, and the RED run is what
        said so. The first version nested `tuplet-number` under `tuplet-actual`
        under `tuplet` with none of the three emitted — and an
        immediate-parent-only rollup gives the SAME answer there, because each
        intermediate is missing too and the suppression chains.

        The two rules differ in exactly one situation, which is the one built
        here: a MIDDLE ancestor that we emit SOMEWHERE ELSE in the document.
        Counts are document-wide, so `<tuplet-actual>` is "present" on our
        side while the `<tuplet>` above this instance of it is not.
        Immediate-parent rollup then reports `tuplet-number`; testing every
        ancestor suppresses it, because the gap is `<tuplet>`.
        """
        truth = _truth_with("<note><notations><tuplet><tuplet-actual>"
                            "<tuplet-number>3</tuplet-number></tuplet-actual>"
                            "</tuplet></notations></note>")
        ours = _truth_with("<note><notations><tuplet-actual/></notations>"
                           "</note>")
        assert [n for n, _, _ in ec.compare(truth, ours)] == ["tuplet"]

    def test_bookkeeping_is_a_DENY_list_not_an_allow_list(self):
        """`NOT_NOTATION` removes what a reader never sees. The property that
        matters is the direction: an element in NEITHER table FAILS, where
        under `VISIBLE` an element in neither was silently unchecked."""
        truth = _truth_with("<print/><harmony/>")
        ours = _truth_with("")
        names = [n for n, _, _ in ec.compare(truth, ours)]
        assert "print" in names and "harmony" in names
        s = _survey_of(truth, ours)
        assert [g[0] for g in s.bookkeeping] == ["print"]
        assert [g[0] for g in s.unexplained] == ["harmony"]

    def test_the_failure_message_needs_no_hand_written_blurb(self):
        """Deriving the set means there is no description for an element
        nobody has met. Where it SITS is derived and says more."""
        truth = _truth_with("<note><notations><ornaments><trill-mark/>"
                            "</ornaments></notations></note>")
        assert (ec.gap_locations(truth)["ornaments"]
                == "measure > note > notations > ornaments")

    def test_every_bookkeeping_entry_carries_a_reason(self):
        for name, why in ec.NOT_NOTATION.items():
            assert len(why) > 40, f"{name}'s reason is too thin to act on"

    def test_the_two_tables_are_disjoint(self):
        """They are different claims — "no reader sees this" against "a reader
        sees it and we deliberately drop it". An element in both means one of
        them is wrong."""
        assert not (set(ec.NOT_NOTATION) & set(ec.KNOWN_GAPS))

    def test_several_truths_pool_without_a_parse_error(self):
        """`survey` concatenates the works' truths so the rollup is computed
        over the POOL. An XML declaration and a DOCTYPE are legal only at the
        head of a document, so they have to come off first."""
        doc = ('<?xml version="1.0"?>\n<!DOCTYPE score-partwise PUBLIC "x" "y">'
               + _truth_with("<note/>"))
        pooled = "<pool>" + ec._strip_prolog(doc) * 2 + "</pool>"
        assert ec.notation_index(pooled)["note"].count == 2


def _survey_of(truth: str, ours: str) -> ec.Survey:
    return ec.Survey(runs=[], gaps=ec.compare(truth, ours),
                     expected=ec.KNOWN_GAPS, disagreement=None,
                     where=ec.gap_locations(truth),
                     ours_counts=ec.element_counts(ours))


class TestStalenessIsAskedOfOurOwnOutput:
    """⚠️ REDEFINED WITH THE DERIVED SET, and the old definition was right by
    luck. `expected - missing` called an entry stale in three situations and
    meant it in one; with a curated `VISIBLE` the other two could not arise,
    because every entry named something all three canonical truths printed."""

    def test_an_entry_for_something_we_now_emit_is_stale(self):
        truth = _truth_with("<note><lyric><text>a</text></lyric></note>")
        ours = _truth_with("<note><lyric><text>a</text></lyric></note>")
        assert "lyric" in _survey_of(truth, ours).stale_entries

    def test_an_entry_the_TRUTH_never_prints_is_not_stale(self):
        """`<grace>` and `<unpitched>` are gaps on the SCAN truths and absent
        from the engraved ones. A truth that does not print an element says
        nothing about whether we emit it — and the old rule called that stale
        and would have failed the suite on Sean's machine."""
        truth = _truth_with("<note/>")
        ours = _truth_with("<note/>")
        assert _survey_of(truth, ours).stale_entries == []

    def test_an_entry_ROLLED_UP_under_a_missing_parent_is_not_stale(self):
        """It is reported through its parent, not closed."""
        truth = _truth_with("<barline><bar-style>light-heavy</bar-style>"
                            "<repeat/></barline>")
        ours = _truth_with("")
        s = _survey_of(truth, ours)
        assert [g[0] for g in s.gaps] == ["barline"]
        assert "barline" not in s.stale_entries

    def test_a_bookkeeping_entry_the_truth_never_shows_is_flagged(self):
        """The same discipline, on the other table: an exclusion for an element
        nobody prints is dead text."""
        s = _survey_of(_truth_with("<note/>"), _truth_with("<note/>"))
        assert set(s.stale_bookkeeping) == set(ec.NOT_NOTATION)


class TestTheConfigurationIsReadOffTheArtifact:
    """`transcribe` records what it was asked to do inside the result it
    returns, so the configuration travels with the transcription instead of in
    a sidecar that can drift out of step with it."""

    def test_a_default_run_leaves_no_direction_block(self):
        assert _run().direction_reader_ran is False
        assert _run().directions_placed == 0

    def test_a_direction_text_run_says_so(self):
        assert _run(direction=RAN).direction_reader_ran is True
        assert _run(direction=RAN).directions_placed == 3

    def test_asked_for_but_ABSTAINED_reads_as_not_run(self):
        """No `.venv-surya` and no Tesseract means no words, so `words` is
        still an honest gap rather than a promise the exporter broke."""
        assert _run(direction=ABSTAINED).direction_reader_ran is False

    def test_words_is_a_gap_when_the_reader_did_not_run(self):
        assert "words" in ec.expected_gaps([_run(), _run()])

    def test_words_STOPS_being_a_gap_once_words_were_placed(self):
        """The entry says "off by default, so this is a flag decision". Once
        the flag is on and the reader placed something, that explanation is
        spent — and a missing <words> is the recognised-then-dropped shape."""
        assert "words" not in ec.expected_gaps([_run(direction=RAN)])

    def test_a_reader_that_ran_and_placed_NOTHING_leaves_the_gap_standing(self):
        """Measured on a real scan: the reader proposes candidates, the lexicon
        refuses all of them, nothing is placed. Nothing to export is not the
        same as something dropped."""
        assert "words" in ec.expected_gaps([_run(direction=RAN_SILENT)])

    def test_metronome_stays_a_gap_under_BOTH_configurations(self):
        """`--direction-text` emits <words> for a tempo mark; the structured
        <metronome> form is not built either way."""
        assert "metronome" in ec.expected_gaps([_run(direction=RAN)])
        assert "metronome" in ec.expected_gaps([_run()])

    def test_mixed_configurations_are_refused_rather_than_pooled(self):
        """`--works mahler-sym5-mvt1` leaves the other two from an earlier
        configuration. The survey adds their counts together, so pooling a
        direction-text run with a default one makes <words> mean nothing."""
        why = ec.configuration_disagreement(
            [_run("a", direction=RAN), _run("b")])
        assert why and "different configurations" in why

    def test_one_configuration_throughout_is_not_a_disagreement(self):
        assert ec.configuration_disagreement([_run("a"), _run("b")]) is None
        assert ec.configuration_disagreement(
            [_run("a", direction=RAN), _run("b", direction=RAN)]) is None

    def test_the_configuration_line_names_what_wrote_the_artifact(self):
        """A red should start by saying what produced the files it read."""
        line = _run(direction=RAN, stale=True).configuration
        assert "direction-text=on" in line and "older tree" in line


class TestOurSideIsExportedNow:

    def test_the_leftover_export_is_not_a_fallback(self, tmp_path):
        """The defect this module was rewritten to remove.

        A `.omr.musicxml` full of beams sits on disk beside a transcription
        that has none. The survey must report `beam` missing — if it reads the
        leftover file instead, it reports a healthy exporter that isn't.
        """
        (tmp_path / "w.musicxml").write_text(_truth_with("<beam>1</beam>"))
        (tmp_path / "w.omr.json").write_text(json.dumps({"pages": []}))
        (tmp_path / "w.omr.musicxml").write_text(_truth_with("<beam>1</beam>"))

        s = ec.survey(fixtures=tmp_path, works=("w",))
        assert "beam" in s.missing
        assert s.runs[0].stale_export is True

    def test_a_work_with_no_transcription_is_skipped_not_guessed(self, tmp_path):
        """No JSON means no fresh export, and reading the leftover instead is
        exactly the silent fallback that would reinstate the defect on the
        machines where nobody would notice."""
        (tmp_path / "w.musicxml").write_text(_truth_with("<beam>1</beam>"))
        (tmp_path / "w.omr.musicxml").write_text(_truth_with("<beam>1</beam>"))
        assert ec.load_run("w", tmp_path) is None
        assert ec.survey(fixtures=tmp_path, works=("w",)).runs == []

    def test_no_fixtures_is_reported_rather_than_passed_off_as_clean(self,
                                                                    tmp_path):
        s = ec.survey(fixtures=tmp_path, works=("w",))
        assert s.runs == [] and s.gaps == []
        assert s.incomplete


class TestAPartialSetIsRefusedRatherThanPooled:
    """The counts are POOLED, so a missing work removes truth and ours together
    and every conclusion moves the way that looks like good news.

    Found by running these tests against an eval that was still mid-flight:
    with only Beethoven written, `accent`, `wedge`, `bar-style`, `barline` and
    `articulations` all read as gaps somebody had CLOSED, because the works
    whose truth carries them were not on disk yet. `--works mahler-sym5-mvt1`
    reaches the same state deliberately.
    """

    def _fixture_dir(self, tmp_path, works):
        for w in works:
            (tmp_path / f"{w}.musicxml").write_text(_truth_with("<beam>1</beam>"))
            (tmp_path / f"{w}.omr.json").write_text(json.dumps({"pages": []}))
        return tmp_path

    def test_a_missing_work_makes_the_survey_incomplete(self, tmp_path):
        self._fixture_dir(tmp_path, ["a"])
        s = ec.survey(fixtures=tmp_path, works=("a", "b"))
        assert s.incomplete and "b" in s.incomplete

    def test_the_whole_set_present_is_complete(self, tmp_path):
        self._fixture_dir(tmp_path, ["a", "b"])
        assert ec.survey(fixtures=tmp_path, works=("a", "b")).incomplete is None


def test_it_surveys_every_work_the_benchmark_writes():
    """The check reads whatever the eval left in FIXTURES, so a work in the
    benchmark and not in WORKS is a fixture nobody looks at. Widening the
    benchmark from 3 works to 11 on 2026-09-02 is exactly the move that would
    have left eight of them unsurveyed.

    Deliberately outside `TestTheRepositoryItself`, whose autouse fixture skips
    when no fixtures are built — this is a fact about the code and holds on a
    clean checkout.
    """
    from tools.omr import accuracy_record as ar
    assert ec.WORKS == ar.BENCHMARK_WORKS


class TestTheCommittedFixtureCopy:
    """A COMMITTED 11-work truth pool, so the tables are checked on a clean
    clone instead of only where `orchestral_eval` has run.

    ⚠️ `TestTheRepositoryItself` below SKIPS on any machine with no
    `benchmarks/omr-orchestral-e2e/fixtures/` — which is every fresh checkout,
    every worktree and every container. That skip is why `<ornaments>` could be
    absent from the exporter and from `VISIBLE` for as long as it was: the one
    test that would have looked never ran. `benchmarks/omr-margin-window-
    truncation-2026-09/out/fixtures-control/` holds all eleven works' truth
    AND that run's export, in git.

    ⚠️ WHAT THIS MAY AND MAY NOT ASSERT. The `.omr.musicxml` beside each truth
    was written by an OLDER tree, and reading a leftover export is the exact
    defect the module was rewritten to remove — a broken exporter would pass
    against it. So this asserts on the TABLES (does every gap head the truth
    pool shows have an entry) and never on the exporter. The exporter is
    covered by `TestOurSideIsExportedNow`, which exports here and now.
    """

    FIXTURES = (Path(__file__).resolve().parents[3] / "benchmarks"
                / "omr-margin-window-truncation-2026-09" / "out"
                / "fixtures-control")

    def _pool(self):
        from tools.omr import accuracy_record as ar
        truths, ours = [], []
        for work in ar.BENCHMARK_WORKS:
            t = self.FIXTURES / f"{work}.musicxml"
            o = self.FIXTURES / f"{work}.omr.musicxml"
            if not (t.is_file() and o.is_file()):
                pytest.skip(f"committed fixture copy is missing {work}")
            truths.append(ec._strip_prolog(t.read_text()))
            ours.append(o.read_text())
        return "<pool>" + "".join(truths) + "</pool>", "".join(ours), len(truths)

    def test_the_pool_is_the_whole_benchmark(self):
        """A positive control on everything below: an empty or partial pool
        would make every assertion here vacuously true."""
        from tools.omr import accuracy_record as ar
        truth, ours, n = self._pool()
        assert n == len(ar.BENCHMARK_WORKS) == 11
        index = ec.notation_index(truth)
        assert len(index) > 60, f"only {len(index)} in-measure elements — thin"
        assert index["note"].count > 1000, "the pool has almost no notes in it"
        assert len(ec.element_counts(ours)) > 40

    def test_every_gap_head_is_accounted_for_by_one_of_the_two_tables(self):
        """⚠️ RUN RED BEFORE BELIEVING GREEN: removing `ornaments` from
        KNOWN_GAPS fails this, and the pre-2026-09-08 `compare()` did not
        report it at all. That is the whole of the tenth gap, pinned."""
        truth, ours, _ = self._pool()
        gaps = ec.compare(truth, ours)
        unexplained = [g for g in gaps
                       if g[0] not in ec.KNOWN_GAPS and g[0] not in ec.NOT_NOTATION]
        assert unexplained == [], (
            "the committed 11-work truth shows these and that run's export had "
            f"none, and neither table explains them: {unexplained}")

    def test_ornaments_IS_one_of_them(self):
        """The non-vacuity check on the test above. If `<ornaments>` ever stops
        being a gap here this test fails and says to look — the committed
        artifacts are frozen, so it can only change if someone edits them."""
        truth, ours, _ = self._pool()
        assert ("ornaments", 12, 0) in ec.compare(truth, ours)

    def test_the_engraved_ornaments_are_ALL_tremolo(self):
        """⚠️ THE ARITHMETIC THAT CHOSE WHAT TO WIRE, pinned so it cannot be
        re-derived wrongly. The handoff listed `<ornaments>` 12 and `tremolo`
        12 as two findings; they are the same twelve elements. So on the
        engraved side "close the ornaments gap" means emit `<tremolo>`, and
        wiring trills alone would move nothing here."""
        import re
        text = (self.FIXTURES / "beethoven-sym3-mvt1.musicxml").read_text()
        blocks = re.findall(r"<ornaments>(.*?)</ornaments>", text, re.S)
        assert len(blocks) == 12
        kinds = {tuple(sorted(set(re.findall(r"<([a-z][a-z0-9-]*)", b))))
                 for b in blocks}
        assert kinds == {("tremolo",)}

    def test_the_rollup_is_what_keeps_the_report_readable(self):
        """The answer to the docstring's own objection — "55 elements, be
        ignored, then be deleted" — as a number rather than a claim."""
        truth, ours, _ = self._pool()
        index = ec.notation_index(truth)
        counts = ec.element_counts(ours)
        categorical = [n for n in index if counts[n] == 0]
        heads = ec.compare(truth, ours)
        reported = [g for g in heads if g[0] not in ec.NOT_NOTATION]
        assert len(index) > 4 * len(reported), (
            f"{len(index)} in-measure elements -> {len(categorical)} "
            f"categorical -> {len(heads)} heads -> {len(reported)} reported")
        assert len(categorical) >= 2 * len(heads)


class TestTheRepositoryItself:

    @pytest.fixture(autouse=True)
    def _survey(self):
        """The benchmark's artifacts, with our side exported by THIS tree.

        The transcriptions are still gitignored output of whatever run last
        wrote them, so a mixed-configuration set is skipped rather than pooled
        (see `configuration_disagreement`); what is no longer unpinned is the
        exporter, which runs here and now.
        """
        s = ec.survey()
        if not s.runs:
            pytest.skip("benchmark fixtures not built — run orchestral_eval")
        if s.incomplete:
            pytest.skip(f"fixtures are partial: {s.incomplete}")
        if s.disagreement:
            pytest.skip(f"fixtures are mixed: {s.disagreement}")
        self.survey = s

    def test_no_unexplained_export_gap(self):
        """The one that matters. Every element the truth shows and we emit none
        of must be written down in KNOWN_GAPS with a reason — so the list is an
        inventory someone reviewed, and anything new fails here."""
        assert self.survey.unexplained == [], (
            "a visible element the truth shows is missing from our export and "
            f"is not explained: {self.survey.unexplained}\n"
            f"what wrote these artifacts:\n{self.survey.provenance}"
        )

    def test_the_inventory_has_no_stale_entries(self):
        """A gap that has been CLOSED must leave KNOWN_GAPS, or the list stops
        describing the exporter and starts describing its history.

        `cbd8ca2` subtracted FLAG_DEPENDENT here, to stop this reporting which
        flags someone last ran with. No subtraction is needed once the
        configuration is known, and the arithmetic says why: `expected` already
        drops `words` on a run that PLACED words, and on a run that did not,
        `words` is genuinely missing and so is not stale either. Both arms come
        out right without an exemption, and the run where the exporter really
        did drop them is caught instead of excused.
        """
        assert self.survey.stale_entries == [], (
            "these are emitted now and should come out of KNOWN_GAPS: "
            f"{self.survey.stale_entries}\n"
            f"what wrote these artifacts:\n{self.survey.provenance}"
        )

    def test_the_seven_that_were_fixed_stay_fixed(self):
        """Regression guard for the actual history: each of these was once
        `truth N, ours 0`. It now guards THIS TREE's exporter rather than
        whichever one last ran the eval."""
        for name in ("accidental", "beam", "dot", "dynamics", "fermata",
                     "slur", "tuplet", "notations", "tied"):
            assert name not in self.survey.missing, (
                f"<{name}> has stopped being exported\n"
                f"what wrote these artifacts:\n{self.survey.provenance}"
            )

    def test_words_placed_by_the_reader_reach_the_file(self):
        """The other direction of the same question, and the one the old check
        could not ask: when the direction reader HAS placed words, they must
        come out. That is the recognised-then-dropped shape aimed at the newest
        layer.

        ⚠️ WHAT IT CANNOT SEE, because I claimed more for it than it earns.
        This compares COUNTS over the benchmark, so it fires only where the
        benchmark contains the failing case. A real instance of exactly this
        shape lives one branch away — a measure the detector found NO events in
        takes the whole-measure-rest path, which never calls the function that
        emits `<direction>`, dropping directions and dynamics both — and a probe
        over the eleven works counts **zero** bars that trigger it, in either
        configuration. Beethoven's `Allegro con brio` sits on a rests-only bar,
        which looks like the case and is not: a rest IS an event and the
        detector finds it. Rests-only is the shape; nothing-at-all is the
        trigger, and it takes a scan — 2 such bars across the five verified rows
        of `benchmarks/omr-scan-e2e-2026-09`.

        ⚠️ AND THE FIX WAS NOT WHERE THE LEDGER SAID. An earlier draft of this
        docstring credited `46e42a4` with having fixed it. That commit's message
        says so — "Both export sites had it", "Both are covered by tests now" —
        and its diff is ONE FILE, a Surya determinism probe; so is its duplicate
        `a907e41`. The branch was still live on main on 2026-09-03, found by
        looking at the code rather than at the log, and fixed then in
        `export._mxl_empty_measure` with the unit tests in `test_export.py` that
        the message had promised. THE TREE OUTRANKS THE LEDGER.

        So this guards the count and the unit tests guard the path. A green here
        is evidence about this corpus's coverage, not about the exporter.
        """
        if not any(r.directions_placed for r in self.survey.runs):
            pytest.skip("fixtures written without --direction-text")
        assert "words" not in self.survey.missing, (
            "the direction reader placed words and none reached the export — "
            "the recognised-then-dropped shape, on the direction layer"
        )
