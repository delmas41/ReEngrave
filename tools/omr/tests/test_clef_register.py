"""Unit tests for the advisory clef-from-pitch register-inversion check
(`transcribe._flag_clef_register_inversion`) and its pitch helpers.

A wrong clef shifts a staff's whole register, so a lower staff resolving an
octave+ above the staff above it is a possible clef error (advisory only — it
can also be voice-crossing or a high instrument). See the module comment in
transcribe.py.
"""

from __future__ import annotations

import pytest

from tools.omr.transcribe import (
    _flag_clef_register_inversion,
    _pitch_to_midi,
    _staff_notehead_midis,
    _percentile,
)

_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def _pitch(midi):
    return f"{_NAMES[midi % 12]}{midi // 12 - 1}"


def _nh(midi):
    return {"category": "notehead", "pitch": _pitch(midi)}


def _staff(i, midis, clef="treble"):
    return {"staff_index": i, "clef": clef,
            "measures": [{"measure_index": 0, "detections": [_nh(m) for m in midis]}]}


def _system(staff_midis, clefs=None):
    staves = []
    for i, midis in enumerate(staff_midis):
        staves.append(_staff(i, midis, clef=(clefs[i] if clefs else "treble")))
    return {"staves": staves}


def _warns(system):
    _flag_clef_register_inversion(system)
    return {st["staff_index"]: st.get("clef_register_warning") for st in system["staves"]}


# ─── pitch helpers ──────────────────────────────────────────────────────────

class TestPitchHelpers:
    @pytest.mark.parametrize("p, m", [
        ("C4", 60), ("C-1", 0), ("A4", 69),
        ("F#3", 54), ("Bb5", 82), ("Eb4", 63), ("Cb4", 59), ("B#3", 60),
    ])
    def test_pitch_to_midi(self, p, m):
        assert _pitch_to_midi(p) == m

    @pytest.mark.parametrize("p", [None, "", "H4", "X", "C", "C#"])
    def test_pitch_to_midi_unparseable(self, p):
        assert _pitch_to_midi(p) is None

    def test_staff_notehead_midis_skips_non_noteheads_and_unresolved(self):
        staff = {"measures": [{"detections": [
            {"category": "notehead", "pitch": "C4"},
            {"category": "rest", "pitch": None},
            {"category": "notehead", "pitch": None},       # unresolved
            {"category": "notehead", "pitch": "G4"},
        ]}]}
        assert sorted(_staff_notehead_midis(staff)) == [60, 67]

    def test_percentile(self):
        xs = [10, 20, 30, 40]
        assert _percentile(xs, 0.0) == 10
        assert _percentile(xs, 0.5) == 30
        assert _percentile(xs, 0.75) == 40


# ─── _flag_clef_register_inversion ──────────────────────────────────────────

def _cluster(center, n=8):
    """n noteheads tightly around `center` (a stable register)."""
    return [center + (i % 3) - 1 for i in range(n)]


class TestClefRegisterInversion:
    def test_normal_order_no_flag(self):
        # Upper staff high (72), lower low (48) — correct ordering.
        assert all(v is None for v in _warns(_system([_cluster(72), _cluster(48)])).values())

    def test_gross_inversion_flags_lower_staff_advisory(self):
        # Lower staff sits an octave+ above the upper -> advisory flag on the lower.
        w = _warns(_system([_cluster(50), _cluster(74)]))
        assert w[0] is None
        assert w[1] is not None
        assert w[1]["confidence_label"] == "advisory"
        assert w[1]["lower_staff_index"] == 1 and w[1]["upper_staff_index"] == 0
        assert w[1]["register_gap_semitones"] >= 12
        assert w[1]["lower_staff_median_midi"] > w[1]["upper_staff_median_midi"]

    def test_mild_inversion_below_octave_no_flag(self):
        # Lower only ~6 semitones above upper -> within benign overlap, no flag.
        assert all(v is None for v in _warns(_system([_cluster(60), _cluster(66)])).values())

    def test_too_few_noteheads_skipped(self):
        # Lower staff is high but has < 6 noteheads -> unreliable register, skip.
        sysd = _system([_cluster(50), []])
        sysd["staves"][1]["measures"][0]["detections"] = [_nh(80), _nh(81), _nh(82)]
        assert all(v is None for v in _warns(sysd).values())

    def test_single_staff_is_noop(self):
        assert _warns(_system([_cluster(80)])) == {0: None}

    def test_percentile_absorbs_a_crossing_note(self):
        # One stray high note in the upper staff must NOT suppress a real
        # inversion (p75 is robust to a single outlier).
        w = _warns(_system([_cluster(50)[:6] + [95], _cluster(74)]))
        assert w[1] is not None and w[1]["register_gap_semitones"] >= 12

    def test_only_adjacent_pairs_compared(self):
        # staff0 high, staff1 low, staff2 high: staff2 is grossly above its
        # neighbour staff1 -> flagged; staff1 (below the high staff0) is not.
        w = _warns(_system([_cluster(74), _cluster(50), _cluster(74)]))
        assert w[0] is None
        assert w[1] is None          # staff1 is correctly LOWER than staff0
        assert w[2] is not None      # staff2 grossly above staff1

    def test_carries_clefs_for_context(self):
        w = _warns(_system([_cluster(50), _cluster(74)], clefs=["treble", "bass"]))
        assert w[1]["lower_staff_clef"] == "bass"
        assert w[1]["upper_staff_clef"] == "treble"
