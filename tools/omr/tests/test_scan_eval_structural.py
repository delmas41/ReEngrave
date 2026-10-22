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


# ------------------------------- the three faults the Mahler maps ran into

class TestPageNormaliseOnOrchestralShapesTheGateHadNotSeen:
    """⚠️ Each of these is a bar no row that already carries a hand map
    contains, and two of them blocked a HAND-CONFIRMED map from being merged.

    Diagnosed in `benchmarks/omr-staves-map-completion-2026-09/FINDINGS.md` §4
    with the exact reproducing bar; fixed and priced in
    `benchmarks/omr-page-normalise-fixes-2026-09/FINDINGS.md`. Every fixture
    below is WRITTEN AND RE-PARSED rather than merged in memory, because one
    of the faults is a property of what `converter.parse` hands back — built
    in memory it does not fire.
    """

    def test_a_rest_and_a_note_at_one_offset_do_not_raise(self, tmp_path):
        """FAULT A — `_tokens` sorted a heterogeneous key.

        A rest's body was the bare `str` "R" beside a note's `tuple`, and the
        key is sorted, so two events sharing `(offset, duration)` compared
        `str` against `tuple`: `TypeError` on Python 3. It needs both in ONE
        measure, i.e. a part whose bar already has two `Voice`s with one
        resting where the other sounds — Mahler 5's `Vier Trompeten in B.`,
        p3 mm 12 and 14 and p4 mm 17-19.
        """
        from music21 import note, stream

        pn = _load("page_normalise")

        def trumpets(pitch):
            part = stream.Part(id=f"T{pitch}")
            m = stream.Measure(number=12)
            v1 = stream.Voice(id="1")
            v1.insert(0.0, note.Note(pitch, quarterLength=4.0))
            v2 = stream.Voice(id="2")
            v2.insert(0.0, note.Rest(quarterLength=4.0))   # the SAME offset
            m.insert(0.0, v1)
            m.insert(0.0, v2)
            part.append(m)
            return part

        score = stream.Score()
        score.append(trumpets("C5"))
        score.append(trumpets("E5"))
        src = tmp_path / "src.musicxml"
        score.write("musicxml", fp=str(src))

        out, report = pn.normalise(src,
                                   [{"name": "Vier Trompeten", "parts": [0, 1]}])
        assert report["n_output_parts"] == 1
        pitches = {p.nameWithOctave
                   for n in out.recurse().notes for p in n.pitches}
        assert pitches == {"C5", "E5"}, "both players must survive the merge"

    def test_every_token_body_is_a_tuple_so_the_key_can_always_sort(self):
        """The mechanism, not just the symptom: no body may be a bare string."""
        from music21 import note, stream

        pn = _load("page_normalise")
        m = stream.Measure(number=1)
        m.insert(0.0, note.Note("C4", quarterLength=1.0))
        m.insert(1.0, note.Rest(quarterLength=1.0))
        for _off, _dur, body in pn._tokens(m):
            assert isinstance(body, tuple), \
                "a str body cannot be sorted against a tuple one"

    def test_unaligned_divisi_becomes_stacked_voices_and_keeps_every_event(
            self, tmp_path):
        """FAULT B — `_voice_merge` inserted a copy still pointing at its old
        parent.

        A deepcopied `Chord` comes back with `activeSite` set to the SOURCE
        measure while its own `sites` dict holds only `None`, so `insert`'s
        is-this-still-sorted check calls `sortTuple()` and raises a bare
        `KeyError`. Mahler 5 p3's `Sechs Hörner in F.` mm 15-16 — two parts in
        different rhythms, so the chord path cannot be taken.
        """
        from music21 import chord, note, stream

        pn = _load("page_normalise")
        score = stream.Score()
        upper = stream.Part(id="Horn135")
        m = stream.Measure(number=15)
        m.append(chord.Chord(["E4", "G#4", "B4"], quarterLength=1.0))
        m.append(chord.Chord(["E4", "G#4"], quarterLength=1.0))
        m.append(chord.Chord(["C#5", "E4"], quarterLength=2.0))
        upper.append(m)
        score.append(upper)
        lower = stream.Part(id="Horn246")
        m = stream.Measure(number=15)
        m.append(note.Note("B3", quarterLength=2.0))      # a DIFFERENT rhythm
        m.append(note.Note("A3", quarterLength=2.0))
        lower.append(m)
        score.append(lower)
        src = tmp_path / "src.musicxml"
        score.write("musicxml", fp=str(src))

        out, report = pn.normalise(src,
                                   [{"name": "Sechs Hörner", "parts": [0, 1]}])
        assert report["measure_census"].get("divisi_voiced") == 1
        voices = list(out.recurse().getElementsByClass(stream.Voice))
        assert len(voices) == 2, "one voice per SOUNDING source part"
        assert len(list(out.recurse().notes)) == 5, \
            "stacking voices must lose no event"
        assert {float(n.offset) for n in voices[1].notes} == {0.0, 2.0}, \
            "an event keeps the offset it had on the page"

    def test_a_condensed_percussion_staff_keeps_both_players(self, tmp_path):
        """FAULTS C and D — an `Unpitched` note is neither `Note` nor `Chord`.

        `_is_silent` read a bar of percussion as SILENT, so condensing two
        rules onto one printed staff would DISCARD one player without a word
        (the quiet half), and `_tokens` reached for `.pitch` on an `Unpitched`
        (the loud half). ⚠️ No map in the gate — hand-read or candidate — puts
        an `Unpitched`-bearing part on a condensed staff today, so this test is
        the only thing guarding it, and it is why the fix is a correctness
        floor rather than a measurable change.
        """
        from music21 import note, stream

        pn = _load("page_normalise")
        score = stream.Score()
        for step, ql in (("E", 1.0), ("G", 2.0)):        # different rhythms
            part = stream.Part(id=f"perc{step}")
            m = stream.Measure(number=1)
            for _ in range(int(4 / ql)):
                u = note.Unpitched()
                u.displayStep = step
                u.duration.quarterLength = ql
                m.append(u)
            part.append(m)
            score.append(part)
        src = tmp_path / "src.musicxml"
        score.write("musicxml", fp=str(src))

        out, report = pn.normalise(
            src, [{"name": "Becken u. Gr.Trommel", "parts": [0, 1]}])
        assert report["measure_census"].get("silent_all") is None, \
            "a bar of percussion notes is not a silent bar"
        assert len(list(out.recurse().notesAndRests)) == 6, \
            "4 + 2 unpitched events, and none of them dropped"
