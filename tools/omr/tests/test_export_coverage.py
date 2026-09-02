"""A signal the pipeline reads must survive into the file.

Seven times the defect has been the same: recognised correctly, then dropped on
the way out. Six of the seven were found forensically, after a metric bucket had
grown large enough for someone to open it; the seventh was found by comparing
element counts between the truth and our export, in two greps, before anyone
looked at its bucket.

This is that comparison, kept. The point is the eighth: it should be caught the
day it appears rather than after a day of forensics.

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

import pytest

from tools.omr import export_coverage as ec


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
        would list 55 elements and be ignored."""
        truth = ("<a><midi-program>1</midi-program><tenths>7</tenths>"
                 "<software>x</software><voice>1</voice></a>")
        assert ec.compare(truth, "<a></a>") == []

    def test_an_element_only_we_emit_is_not_a_gap(self):
        assert ec.compare("<a></a>", TRUTH) == []

    def test_every_visible_element_carries_its_reason(self):
        assert all(VISIBLE_reason.strip() for VISIBLE_reason in ec.VISIBLE.values())

    def test_every_known_gap_is_a_visible_element(self):
        """A reason for something the check never looks at is dead text."""
        assert set(ec.KNOWN_GAPS) <= set(ec.VISIBLE)

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
        (tmp_path / "w.musicxml").write_text(
            "<score-partwise><beam>1</beam></score-partwise>")
        (tmp_path / "w.omr.json").write_text(json.dumps({"pages": []}))
        (tmp_path / "w.omr.musicxml").write_text(
            "<score-partwise><beam>1</beam></score-partwise>")

        s = ec.survey(fixtures=tmp_path, works=("w",))
        assert "beam" in s.missing
        assert s.runs[0].stale_export is True

    def test_a_work_with_no_transcription_is_skipped_not_guessed(self, tmp_path):
        """No JSON means no fresh export, and reading the leftover instead is
        exactly the silent fallback that would reinstate the defect on the
        machines where nobody would notice."""
        (tmp_path / "w.musicxml").write_text("<a><beam>1</beam></a>")
        (tmp_path / "w.omr.musicxml").write_text("<a><beam>1</beam></a>")
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
            (tmp_path / f"{w}.musicxml").write_text("<a><beam>1</beam></a>")
            (tmp_path / f"{w}.omr.json").write_text(json.dumps({"pages": []}))
        return tmp_path

    def test_a_missing_work_makes_the_survey_incomplete(self, tmp_path):
        self._fixture_dir(tmp_path, ["a"])
        s = ec.survey(fixtures=tmp_path, works=("a", "b"))
        assert s.incomplete and "b" in s.incomplete

    def test_the_whole_set_present_is_complete(self, tmp_path):
        self._fixture_dir(tmp_path, ["a", "b"])
        assert ec.survey(fixtures=tmp_path, works=("a", "b")).incomplete is None


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
        come out. That is the seventh-gap shape aimed at the newest layer."""
        if not any(r.directions_placed for r in self.survey.runs):
            pytest.skip("fixtures written without --direction-text")
        assert "words" not in self.survey.missing, (
            "the direction reader placed words and none reached the export — "
            "the recognised-then-dropped shape, on the direction layer"
        )
