"""The scan gate must ACCOUNT for page-vs-encoding condensation, every run.

    Sean, 2026-09-06: *"That information is known, but I want to make sure it
    is taken into account when we are running tests."*

`works.json` has carried the hand-read `staves[i].parts` map since the gate was
built — `parts: [0, 1]` IS a printed staff carrying two encoded parts — and
until 2026-09-06 `scan_eval.py` read it only for `note_recall`. The pooled
OMR-NED it distorts never saw it, and no report said how much of the figure was
the condensation convention rather than a misreading.

These are ANTI-DRIFT tests in the shape of `TestEventlessMeasureKeepsItsMarks`:
they assert on the SOURCE that the call sites still exist, because a
behavioural test only exercises whichever path its fixture happens to take, and
a refactor that quietly drops the reporting would leave every other test green.

They also pin the two properties that make `page_normalise` safe to have at
all: it REFUSES a row with no hand map (rather than inferring one from the
encoding, which is circular), and a map that asks for no merging is an
IDENTITY (the property the Dvořák control checks end to end — the first cut of
the transform failed it by dropping spanners).
"""
from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"


def _load(name: str):
    path = SCAN / f"{name}.py"
    if not path.is_file():
        pytest.skip(f"{path} not present")
    if str(SCAN) not in sys.path:
        sys.path.insert(0, str(SCAN))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------- the wiring

class TestScanEvalAccountsForCondensation:
    """⚠️ ANTI-DRIFT. Verified to fail when any of these call sites is removed."""

    @staticmethod
    def _src() -> str:
        path = SCAN / "scan_eval.py"
        if not path.is_file():
            pytest.skip("scan_eval.py not present")
        return path.read_text()

    def test_it_defines_the_two_structural_functions(self):
        src = self._src()
        assert "def structural_divergence(" in src
        assert "def pooled_structural(" in src

    def test_every_row_gets_a_structural_block(self):
        """Per-row, not just pooled — a reader must be able to see WHICH rows
        carry the charge."""
        src = self._src()
        assert 'entry["structural"] = structural_divergence(' in src

    def test_the_pooled_structural_block_is_not_behind_a_flag(self):
        """A figure that needs a flag to be honest gets quoted without it.

        `pooled_structural(...)` must be called unconditionally — not inside an
        `if args.<anything>` — and its result must reach BOTH the printed
        report and the written JSON.
        """
        src = self._src().splitlines()
        call = [i for i, line in enumerate(src)
                if "structural = pooled_structural(" in line]
        assert call, "pooled_structural is never called"
        for i in call:
            # walk back to the enclosing statement's indent; the call must sit
            # at function-body level, not inside a conditional on a flag
            indent = len(src[i]) - len(src[i].lstrip())
            assert indent == 4, (
                "the pooled structural block must be unconditional at function "
                f"body level, found indent {indent} on line {i + 1}")
        joined = "\n".join(src)
        assert '"structural": structural,' in joined, \
            "the structural block must be written into results.json"
        assert "STRUCTURAL ACCOUNTING" in joined, \
            "the structural block must be printed on every run"

    def test_a_row_without_a_hand_map_says_so_rather_than_scoring_zero(self):
        src = self._src()
        assert "NO-MAP" in src, "the per-row table must mark un-mapped rows"
        assert "UNMEASURED, not zero" in src

    def test_the_normalised_arm_is_available_and_labelled_as_its_own_era(self):
        src = self._src()
        assert '"--page-normalised"' in src
        assert "SEPARATE BENCHMARK ERA" in src
        assert "STRUCTURAL CHARGE REMOVED" in src

    def test_structural_divergence_reads_the_hand_map(self):
        mod = _load("scan_eval")
        row = {"staves": [{"name": "Flauti", "parts": [0, 1]},
                          {"name": "Violino I", "parts": [2]}]}
        got = mod.structural_divergence(row, 3)
        assert got["has_hand_map"] is True
        assert got["n_printed_staves_per_system"] == 2
        assert got["n_condensed_staves"] == 1
        assert got["surplus_parts"] == 1
        assert got["orphan_parts"] == []

    def test_structural_divergence_abstains_without_a_hand_map(self):
        mod = _load("scan_eval")
        got = mod.structural_divergence({"staves": None}, 18)
        assert got["has_hand_map"] is False
        assert "UNMEASURED" in got["reason"]
        assert "surplus_parts" not in got, \
            "an unmeasured row must not report a surplus of zero"


# ------------------------------------------------------------- the transform

class TestPageNormaliseRefusesAndPreserves:

    def test_it_refuses_without_a_hand_map(self, tmp_path):
        pn = _load("page_normalise")
        with pytest.raises(pn.NoHandMap):
            pn.normalise(tmp_path / "nope.musicxml", None)
        with pytest.raises(pn.NoHandMap):
            pn.normalise(tmp_path / "nope.musicxml", [])

    def test_it_refuses_a_map_that_does_not_name_every_part(self, tmp_path):
        """⚠️ Found by the engraved no-op probe: dropping an unnamed part makes
        the score go DOWN (Dvořák 9 "improved" by 42 edits) because deleting a
        reference part deletes what we could be wrong about."""
        from music21 import note, stream

        pn = _load("page_normalise")
        score = stream.Score()
        for pitch in ("C5", "E5", "G5"):
            part = stream.Part(id=pitch)
            m = stream.Measure(number=1)
            m.append(note.Note(pitch, quarterLength=4.0))
            part.append(m)
            score.append(part)
        src = tmp_path / "src.musicxml"
        score.write("musicxml", fp=str(src))

        with pytest.raises(pn.IncompleteMap):
            pn.normalise(src, [{"name": "A", "parts": [0]},
                               {"name": "B", "parts": [1]}])
        assert issubclass(pn.IncompleteMap, pn.NoHandMap), \
            "a caller that abstains on NoHandMap must abstain on this too"

    def test_the_transform_is_versioned(self):
        pn = _load("page_normalise")
        assert pn.TRANSFORM_VERSION
        assert "divisi" in pn.MERGE_CONVENTION

    def test_a_no_merge_map_is_an_identity(self, tmp_path):
        """The Dvořák control, in miniature.

        ⚠️ This test EXISTS because the first version of the transform failed
        it: it rebuilt the score out of copied measures, which silently dropped
        every SPANNER — Dvořák p5's 14 `<wedge>` became 0 and the row's score
        "improved" by 12 edits from deleting the evidence.
        """
        from music21 import dynamics, note, stream

        pn = _load("page_normalise")
        score = stream.Score()
        for name in ("Flute", "Oboe"):
            part = stream.Part(id=name)
            part.partName = name
            for n in range(1, 3):
                m = stream.Measure(number=n)
                m.append(note.Note("C4", quarterLength=4.0))
                part.append(m)
            score.append(part)
        first = list(score.parts)[0]
        heads = list(first.recurse().notes)
        wedge = dynamics.Crescendo(heads[0], heads[1])
        score.insert(0, wedge)
        src = tmp_path / "src.musicxml"
        score.write("musicxml", fp=str(src))

        out, report = pn.normalise(
            src, [{"name": "Flute", "parts": [0]},
                  {"name": "Oboe", "parts": [1]}])
        assert report["n_output_parts"] == 2
        assert report["divisi_share"] == 0.0
        assert len(out.recurse().getElementsByClass("Crescendo")) == 1, \
            "a spanner must survive a no-merge normalisation"

    def test_two_parts_on_one_staff_become_one_part(self, tmp_path):
        from music21 import note, stream

        pn = _load("page_normalise")
        score = stream.Score()
        for pitch in ("C5", "E5"):
            part = stream.Part(id=pitch)
            m = stream.Measure(number=1)
            m.append(note.Note(pitch, quarterLength=4.0))
            part.append(m)
            score.append(part)
        src = tmp_path / "src.musicxml"
        score.write("musicxml", fp=str(src))

        out, report = pn.normalise(src, [{"name": "Flauti", "parts": [0, 1]}])
        assert report["n_source_parts"] == 2
        assert report["n_output_parts"] == 1
        assert report["measure_census"].get("divisi") == 1
        pitches = {p.nameWithOctave
                   for n in out.recurse().notes for p in n.pitches}
        assert pitches == {"C5", "E5"}, \
            "merging must keep BOTH players' notes, not pick one"

    def test_a_unison_pair_does_not_double_the_notes(self, tmp_path):
        """The measured majority case: 69.8% of condensed staff-measures are
        exact duplication, and the page prints ONE line for them."""
        from music21 import note, stream

        pn = _load("page_normalise")
        score = stream.Score()
        for i in range(2):
            part = stream.Part(id=f"P{i}")
            m = stream.Measure(number=1)
            m.append(note.Note("G4", quarterLength=4.0))
            part.append(m)
            score.append(part)
        src = tmp_path / "src.musicxml"
        score.write("musicxml", fp=str(src))

        out, report = pn.normalise(src, [{"name": "Corni", "parts": [0, 1]}])
        assert report["measure_census"].get("unison") == 1
        assert len(list(out.recurse().notes)) == 1
