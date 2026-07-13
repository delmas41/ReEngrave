"""Unit tests for the transposition-aware cross-staff key-signature check
(`transcribe._flag_key_signature_inconsistency`).

The check knows that transposing instruments print DIFFERENT written key
signatures for one concert key (a fixed circle-of-fifths offset), so it flags a
staff only when no single concert key reconciles it with the majority via a
standard transposition. See the module comment in transcribe.py.
"""

from __future__ import annotations

import pytest

from tools.omr.transcribe import (
    _flag_key_signature_inconsistency,
    _staff_key_fifths,
    _fifths_key_name,
    _fifths_accidentals,
)


def _staff(i, fifths):
    """Staff dict with a key signature at circle-of-fifths position `fifths`
    (+N = N sharps, -N = N flats)."""
    sharps, flats = (fifths, 0) if fifths >= 0 else (0, -fifths)
    return {"staff_index": i, "key_signature": {"sharps": sharps, "flats": flats}}


def _system(fifths_list):
    return {"staves": [_staff(i, c) for i, c in enumerate(fifths_list)]}


def _warns(system):
    _flag_key_signature_inconsistency(system)
    return {st["staff_index"]: st.get("key_signature_warning") for st in system["staves"]}


# ─── circle-of-fifths helpers ───────────────────────────────────────────────

class TestFifthsHelpers:
    def test_staff_key_fifths_sharps(self):
        assert _staff_key_fifths({"key_signature": {"sharps": 3, "flats": 0}}) == 3

    def test_staff_key_fifths_flats(self):
        assert _staff_key_fifths({"key_signature": {"sharps": 0, "flats": 2}}) == -2

    def test_staff_key_fifths_missing(self):
        assert _staff_key_fifths({}) == 0

    @pytest.mark.parametrize("c, name", [(0, "C major"), (2, "D major"), (-3, "Eb major"), (1, "G major")])
    def test_fifths_key_name(self, c, name):
        assert _fifths_key_name(c) == name

    @pytest.mark.parametrize("c, s", [(0, "no accidentals"), (1, "1 sharp"), (3, "3 sharps"),
                                      (-1, "1 flat"), (-3, "3 flats")])
    def test_fifths_accidentals(self, c, s):
        assert _fifths_accidentals(c) == s


# ─── _flag_key_signature_inconsistency ──────────────────────────────────────

class TestKeySignatureConsistency:
    def test_concert_c_orchestra_is_consistent(self):
        # Sean's example: concert C -> C(0), Bb->D(2#), A->Eb(3b), Eb->A(3#),
        # F->G(1#). All five distinct written sigs are mutually consistent.
        assert all(v is None for v in _warns(_system([0, 2, -3, 3, 1])).values())

    def test_all_c_instruments_consistent(self):
        assert all(v is None for v in _warns(_system([0, 0, 0])).values())

    def test_mixed_sharps_and_flats_reconciled_by_transposition(self):
        # THE transposition win (the real ravel sys0 shape): staves at +1 sharp
        # and -1 flat look like a disagreement to a naive check, but both are
        # consistent with concert F major -> no flag.
        assert all(v is None for v in _warns(_system([0, 0, 1, 1, -1, -1])).values())

    def test_zero_is_wildcard_never_flags(self):
        # A no-key-signature staff (horn/trumpet/modern score) is consistent
        # with any concert key; it neither flags nor constrains the concert key.
        w = _warns(_system([2, 2, 0]))   # two Bb instruments + a no-key-sig part
        assert all(v is None for v in w.values())

    def test_single_nonzero_is_noop(self):
        # Only one staff carries a key signature -> nothing to cross-check.
        assert all(v is None for v in _warns(_system([0, 0, 3])).values())

    def test_single_staff_system_is_noop(self):
        assert all(v is None for v in _warns(_system([5])).values())

    def test_outlier_flagged_high(self):
        # Four staves consistent with concert C (2#,3#,1#,3b) + one 5# staff
        # that no concert key can include alongside them.
        w = _warns(_system([2, 3, 1, -3, 5]))
        assert all(w[i] is None for i in range(4))
        assert w[4] == {
            "staff_key": "5 sharps", "staff_fifths": 5, "concert_key": "C major",
            "consistent_written_fifths": [-3, 0, 1, 2, 3], "agreement": "4/5",
            "circle_distance": 2, "confidence": 0.8, "confidence_label": "high",
        }

    def test_borderline_transposition_distance1_capped_to_medium(self):
        # A staff at -2 (a D instrument's written key vs concert C) is one fifth
        # outside the common set -> flagged, but only MEDIUM (might be a rarer
        # transposition, not an error), even though consensus is 0.8.
        w = _warns(_system([2, 3, 1, -3, -2]))
        assert w[4]["circle_distance"] == 1
        assert w[4]["confidence"] == 0.8          # strong consensus…
        assert w[4]["confidence_label"] == "medium"  # …but capped for distance 1

    def test_two_nonzero_disagreement_abstains(self):
        # 2# vs 5b, no majority -> can't say which is wrong -> abstain.
        assert all(v is None for v in _warns(_system([2, -5])).values())

    def test_scattered_signatures_abstain(self):
        # No single concert key covers a strict majority of these four.
        assert all(v is None for v in _warns(_system([2, -3, 5, -5])).values())

    def test_multiple_outliers_when_majority_agrees(self):
        # Six staves consistent with concert C + two irreconcilable outliers.
        w = _warns(_system([2, 3, 1, -3, 2, 1, 5, -6]))
        # indices 0..5 fit concert C; 6 (5#) and 7 (6b) are outliers.
        assert w[6] is not None and w[7] is not None
        assert all(w[i] is None for i in range(6))
        assert w[6]["concert_key"] == "C major"

    def test_reports_inferred_concert_key(self):
        # Majority are B-flat instruments (2#) + trumpets (also 2#) beside an
        # E-flat instrument (3#): all consistent with concert C; an outlier at
        # 6# is reported against concert C.
        w = _warns(_system([2, 2, 3, 1, 6]))
        assert w[4]["concert_key"] == "C major"
        assert w[4]["staff_fifths"] == 6
