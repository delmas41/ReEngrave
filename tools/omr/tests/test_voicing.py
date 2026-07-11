"""Unit tests for tools/omr/voicing.py — Phase 4e chord grouping +
Phase 4h voice splitting.
"""

from __future__ import annotations

import pytest

from tools.omr.voicing import (
    group_chords_in_measure,
    split_events_into_voices,
)


def _nh(
    pitch: str,
    x: int,
    *,
    y: int = 200,
    w: int = 30,
    h: int = 20,
    duration_beats: float = 1.0,
    duration_type: str = "quarter",
    dots: int = 0,
    stem_direction: str | None = None,
):
    """Build a notehead detection dict matching transcribe.py's schema."""
    d = {
        "category": "notehead",
        "class": "noteheadBlackOnLine",
        "bbox": [x, y, w, h],
        "bbox_page": [x, y, w, h],
        "confidence": 0.9,
        "pitch": pitch,
        "duration_beats": duration_beats,
        "duration_type": duration_type,
        "dots": dots,
    }
    if stem_direction is not None:
        d["stem_direction"] = stem_direction
    return d


def _rest(x: int, *, duration_beats: float = 1.0, duration_type: str = "quarter"):
    return {
        "category": "rest",
        "class": "restQuarter",
        "bbox": [x, 200, 30, 30],
        "bbox_page": [x, 200, 30, 30],
        "confidence": 0.9,
        "pitch": None,
        "duration_beats": duration_beats,
        "duration_type": duration_type,
        "dots": 0,
    }


class TestGroupChords:
    def test_empty_input(self):
        assert group_chords_in_measure([]) == []

    def test_single_notehead_becomes_chord_of_one(self):
        events = group_chords_in_measure([_nh("C4", 100)])
        assert len(events) == 1
        assert events[0]["kind"] == "chord"
        assert events[0]["duration_beats"] == 1.0
        assert [n["pitch"] for n in events[0]["noteheads"]] == ["C4"]

    def test_same_x_noteheads_grouped(self):
        # Two notes at the same x → one chord with both pitches.
        events = group_chords_in_measure([
            _nh("C4", 100), _nh("E4", 100), _nh("G4", 100),
        ])
        assert len(events) == 1
        assert events[0]["kind"] == "chord"
        pitches = [n["pitch"] for n in events[0]["noteheads"]]
        assert set(pitches) == {"C4", "E4", "G4"}

    def test_distant_noteheads_separate_chords(self):
        events = group_chords_in_measure([
            _nh("C4", 100), _nh("D4", 500),
        ])
        assert len(events) == 2
        assert events[0]["noteheads"][0]["pitch"] == "C4"
        assert events[1]["noteheads"][0]["pitch"] == "D4"

    def test_events_sorted_by_x_position(self):
        # Even when input is out of order, output is left-to-right.
        events = group_chords_in_measure([
            _nh("D4", 500), _nh("C4", 100), _nh("E4", 300),
        ])
        x_positions = [e["x_position"] for e in events]
        assert x_positions == sorted(x_positions)

    def test_chord_duration_is_mode(self):
        # If chord members have mixed durations, use the most common.
        events = group_chords_in_measure([
            _nh("C4", 100, duration_beats=1.0, duration_type="quarter"),
            _nh("E4", 100, duration_beats=1.0, duration_type="quarter"),
            _nh("G4", 100, duration_beats=2.0, duration_type="half"),
        ])
        assert events[0]["duration_beats"] == 1.0
        assert events[0]["duration_type"] == "quarter"

    def test_rest_emitted_separately(self):
        events = group_chords_in_measure([
            _nh("C4", 100),
            _rest(300),
        ])
        assert len(events) == 2
        # Sorted by x — chord first, rest second
        assert events[0]["kind"] == "chord"
        assert events[1]["kind"] == "rest"

    def test_rest_with_no_noteheads(self):
        events = group_chords_in_measure([_rest(100, duration_beats=4.0, duration_type="whole")])
        assert len(events) == 1
        assert events[0]["kind"] == "rest"
        assert events[0]["duration_beats"] == 4.0

    def test_skips_unpitched_noteheads(self):
        # Noteheads with pitch=None aren't included in chord events.
        nh = _nh("C4", 100)
        bad = _nh("X4", 100)
        bad["pitch"] = None
        events = group_chords_in_measure([nh, bad])
        # Only the good one should be present.
        assert len(events) == 1
        pitches = [n["pitch"] for n in events[0]["noteheads"]]
        assert pitches == ["C4"]

    def test_stem_direction_aggregated(self):
        # All members share the same explicit direction (or are unknown) —
        # still one chord, aggregate direction = up.
        events = group_chords_in_measure([
            _nh("C4", 100, stem_direction="up"),
            _nh("E4", 100, stem_direction="up"),
            _nh("G4", 100),  # unknown direction — doesn't block the merge
        ])
        assert len(events) == 1
        assert events[0]["stem_direction"] == "up"

    # ── Divisi guard (audit follow-up, 2026-07) ─────────────────────────────
    # Noteheads at (near-)identical x with OPPOSITE, explicit stem
    # directions are two independent voices (e.g. divisi strings), not one
    # chord — merging them corrupted duration via chord-duration mode-vote.
    # Same-x + same-direction (or unknown) must still group as one chord.

    def test_same_x_opposite_stem_splits_into_two_events(self):
        events = group_chords_in_measure([
            _nh("C5", 100, stem_direction="up"),
            _nh("C4", 100, stem_direction="down"),
        ])
        assert len(events) == 2
        assert {events[0]["stem_direction"], events[1]["stem_direction"]} == {"up", "down"}
        # Each event keeps its own single notehead — no merged chord.
        assert all(len(ev["noteheads"]) == 1 for ev in events)

    def test_same_x_same_stem_direction_stays_one_chord(self):
        events = group_chords_in_measure([
            _nh("C4", 100, stem_direction="up"),
            _nh("E4", 100, stem_direction="up"),
            _nh("G4", 100, stem_direction="up"),
        ])
        assert len(events) == 1
        assert events[0]["stem_direction"] == "up"
        assert len(events[0]["noteheads"]) == 3

    def test_divisi_preserves_each_voices_own_duration(self):
        # The core bug: x-only grouping used to mode-vote a single
        # duration across both voices. Each divisi voice must keep its
        # own independently-resolved duration after the split.
        events = group_chords_in_measure([
            _nh("C5", 100, stem_direction="up",
                duration_beats=1.0, duration_type="quarter"),
            _nh("C4", 100, stem_direction="down",
                duration_beats=0.5, duration_type="eighth"),
        ])
        assert len(events) == 2
        by_pitch = {ev["noteheads"][0]["pitch"]: ev for ev in events}
        assert by_pitch["C5"]["duration_beats"] == 1.0
        assert by_pitch["C4"]["duration_beats"] == 0.5

    def test_same_x_multiple_noteheads_per_direction_split_cleanly(self):
        # A 2-up / 2-down divisi cluster at the same x, interleaved in
        # input order (not pre-sorted by direction) — both up-notes must
        # land together and both down-notes must land together, not four
        # separate one-note events.
        events = group_chords_in_measure([
            _nh("C5", 100, stem_direction="up"),
            _nh("C4", 100, stem_direction="down"),
            _nh("E5", 100, stem_direction="up"),
            _nh("E4", 100, stem_direction="down"),
        ])
        assert len(events) == 2
        up_ev = next(ev for ev in events if ev["stem_direction"] == "up")
        down_ev = next(ev for ev in events if ev["stem_direction"] == "down")
        assert {n["pitch"] for n in up_ev["noteheads"]} == {"C5", "E5"}
        assert {n["pitch"] for n in down_ev["noteheads"]} == {"C4", "E4"}

    def test_unknown_direction_notehead_joins_nearest_compatible_group(self):
        # An unknown-direction notehead at the same x as a divisi pair
        # should not force a third event — it merges into whichever
        # group it reaches first (conservative default: doesn't split).
        events = group_chords_in_measure([
            _nh("C5", 100, stem_direction="up"),
            _nh("C4", 100, stem_direction="down"),
            _nh("G4", 100),  # unknown
        ])
        assert len(events) == 2


class TestSplitVoices:
    def test_single_voice_when_no_directions(self):
        events = group_chords_in_measure([
            _nh("C4", 100), _nh("D4", 200), _nh("E4", 300),
        ])
        voices = split_events_into_voices(events)
        assert len(voices) == 1

    def test_single_voice_all_up_or_all_down(self):
        events = group_chords_in_measure([
            _nh("C4", 100, stem_direction="up"),
            _nh("D4", 200, stem_direction="up"),
        ])
        voices = split_events_into_voices(events)
        assert len(voices) == 1

    def test_two_voices_when_both_directions_present(self):
        # Voices that interleave temporally (different x positions) — the
        # natural case where one voice is the melody and the other is a
        # secondary line. Chord-grouping won't merge them since x differs.
        events = group_chords_in_measure([
            _nh("C5", 100, stem_direction="up"),
            _nh("D4", 200, stem_direction="down"),
            _nh("D5", 300, stem_direction="up"),
            _nh("C4", 400, stem_direction="down"),
        ])
        voices = split_events_into_voices(events)
        assert len(voices) == 2
        v1_pitches = {n["pitch"] for ev in voices[0] for n in ev.get("noteheads", [])}
        v2_pitches = {n["pitch"] for ev in voices[1] for n in ev.get("noteheads", [])}
        # Voice 1 = stem-up; Voice 2 = stem-down
        assert "C5" in v1_pitches and "D5" in v1_pitches
        assert "D4" in v2_pitches and "C4" in v2_pitches
