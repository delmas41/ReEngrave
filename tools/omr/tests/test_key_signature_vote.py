"""Unit tests for cross-staff / cross-system key-signature reconciliation
(`tools/omr/key_signature_vote.py`).

Each test is a shape that actually occurred on the two ground-truth pages, not
a hypothetical: the bassoon rejected in one system and accepted in the other,
the badly-read lower system setting its own reference, the clarinet that is a
genuine transposition rather than an error.
"""

from __future__ import annotations

import pytest

from tools.omr.key_signature_vote import (
    StaffCandidate,
    VoteConfig,
    consistent_written_set,
    fifths_accidentals,
    reconcile,
)


def _staff(system, ordinal, fifths, weight=1.0, staff_index=None):
    return StaffCandidate(
        staff_index=staff_index if staff_index is not None else system * 100 + ordinal,
        system_index=system,
        ordinal=ordinal,
        fifths=fifths,
        weight=weight,
    )


def _orchestra(system, values, weights=None):
    """One system of staves, `values[i]` being staff i's reading."""
    weights = weights or [3.0] * len(values)
    return [_staff(system, i, v, w) for i, (v, w) in enumerate(zip(values, weights))]


# ─── the transposition relation ─────────────────────────────────────────────

class TestWrittenSet:
    def test_concert_c_covers_the_standard_orchestra(self):
        # C(0), F(+1), Bb(+2), Eb(+3), A(-3) — Sean's example set.
        assert consistent_written_set(0) == {-3, 0, 1, 2, 3}

    def test_reference_is_always_in_its_own_set(self):
        for k in range(-7, 8):
            assert k in consistent_written_set(k)

    def test_accidental_wording(self):
        assert fifths_accidentals(-3) == "3 flats"
        assert fifths_accidentals(1) == "1 sharp"
        assert fifths_accidentals(0) == "no accidentals"


# ─── within one system ──────────────────────────────────────────────────────

class TestSingleSystem:
    def test_agreeing_staves_are_all_kept(self):
        result = reconcile(_orchestra(0, [-3, -3, -3, -3]))
        assert all(v.action == "kept" for v in result.verdicts.values())
        assert all(v.fifths == -3 for v in result.verdicts.values())

    def test_a_weak_departure_is_rejected(self):
        # One staff reads a single flat among three-flat parts, off one glyph.
        # It COULD be a Bb instrument — but a lone accidental is not evidence.
        staves = _orchestra(0, [-3, -3, -3, -1], weights=[3, 3, 3, 1])
        result = reconcile(staves)
        assert result.verdicts[3].action == "rejected"
        assert result.verdicts[3].fifths is None

    def test_a_strong_departure_is_kept_as_a_transposition(self):
        # The same value, read off two matched accidentals, is a real clarinet.
        staves = _orchestra(0, [-3, -3, -3, -1], weights=[3, 3, 3, 2])
        result = reconcile(staves)
        assert result.verdicts[3].action == "kept"
        assert result.verdicts[3].fifths == -1

    def test_a_strong_but_illegal_departure_is_still_rejected(self):
        # 2 sharps cannot be any standard transposition of a 3-flat part, so
        # no amount of confidence in the reading makes it consistent.
        staves = _orchestra(0, [-3, -3, -3, 2], weights=[3, 3, 3, 3])
        assert 2 not in consistent_written_set(-3)
        assert result_action(reconcile(staves), 3) == "rejected"

    def test_no_key_signature_is_a_wildcard(self):
        # A horn part printing nothing is consistent with any key and must never
        # be flagged or overwritten.
        staves = _orchestra(0, [-3, -3, -3, 0])
        result = reconcile(staves)
        assert result.verdicts[3].fifths == 0
        assert result.verdicts[3].action == "kept"

    def test_unread_staff_stays_unread_without_another_system(self):
        staves = _orchestra(0, [-3, -3, None])
        result = reconcile(staves)
        assert result.verdicts[2].action == "unread"
        assert result.verdicts[2].fifths is None

    def test_no_majority_leaves_every_reading_alone(self):
        staves = _orchestra(0, [-3, 1], weights=[1, 1])
        result = reconcile(staves)
        assert all(v.fifths is not None for v in result.verdicts.values())


def result_action(result, staff_ordinal, system=0):
    return result.verdicts[system * 100 + staff_ordinal].action


# ─── across systems ─────────────────────────────────────────────────────────

class TestAcrossSystems:
    def test_a_read_part_fills_in_the_same_part_elsewhere(self):
        # The oboe is the oboe in every system; reading it once is enough.
        staves = _orchestra(0, [-3, -3, -3]) + _orchestra(1, [-3, None, -3])
        result = reconcile(staves)
        assert result.verdicts[101].action == "carried"
        assert result.verdicts[101].fifths == -3

    def test_the_fuller_reading_wins(self):
        # Under-counting is the failure mode; the reader never invents an
        # accidental, so three flats beats one flat for the same part.
        staves = _orchestra(0, [-3, -3, -3]) + _orchestra(1, [-3, -3, -1], weights=[3, 3, 1])
        result = reconcile(staves)
        assert result.verdicts[102].fifths == -3
        assert result.verdicts[102].action == "carried"

    def test_a_reading_too_weak_to_keep_is_too_weak_to_carry(self):
        # THE bug this guard exists for: a bassoon misread as one sharp among
        # one-flat parts was rejected in the system that read it, then exported
        # to the next system and accepted there as an unchallenged fact.
        staves = _orchestra(0, [-1, -1, 1], weights=[3, 3, 1]) + _orchestra(1, [-1, -1, None])
        result = reconcile(staves)
        assert result.verdicts[2].action == "rejected"
        assert result.verdicts[102].fifths is None

    def test_sharp_flat_conflict_abstains_on_both(self):
        staves = _orchestra(0, [-3, -3, -2]) + _orchestra(1, [-3, -3, 2])
        result = reconcile(staves)
        assert result.verdicts[2].action == "rejected"
        assert result.verdicts[102].action == "rejected"
        assert "sharps vs flats" in result.verdicts[2].reason

    def test_a_badly_read_system_does_not_set_its_own_reference(self):
        # Beethoven 5 p.2: the lower system read so poorly that its own modal
        # signature came out as one flat on a page of three-flat parts, and its
        # wrong readings were then kept for agreeing with a reference they had
        # set themselves. Pooling lets the well-read system decide for the page,
        # after which the weak readings lose to the full ones for the same part.
        good = _orchestra(0, [-3, -3, -3, -3], weights=[3, 3, 3, 3])
        bad = _orchestra(1, [-1, -1, None, None], weights=[1, 1, 0, 0])
        result = reconcile(good + bad)
        assert set(result.reference_written_by_system.values()) == {-3}
        assert result.verdicts[100].fifths == -3
        assert result.verdicts[101].fifths == -3

    def test_a_weak_wrong_reading_loses_to_a_full_one_elsewhere(self):
        # Same shape with no well-read counterpart for that part: nothing to
        # carry, so the weak departure is simply rejected.
        good = _orchestra(0, [-3, -3, -3, None], weights=[3, 3, 3, 0])
        bad = _orchestra(1, [None, None, None, -1], weights=[0, 0, 0, 1])
        result = reconcile(good + bad)
        assert result.verdicts[103].fifths is None
        assert result.verdicts[103].action == "rejected"

    def test_systems_of_different_heights_are_not_aligned(self):
        # Position identifies the instrument only when the systems line up. A
        # condensed system is left alone rather than matched by guesswork.
        staves = _orchestra(0, [-3, -3, -3]) + _orchestra(1, [-3, None])
        result = reconcile(staves)
        assert result.verdicts[101].action == "unread"


# ─── configuration ──────────────────────────────────────────────────────────

class TestConfig:
    def test_strong_weight_governs_when_a_departure_is_believed(self):
        staves = _orchestra(0, [-3, -3, -3, -1], weights=[3, 3, 3, 2])
        strict = reconcile(staves, VoteConfig(strong_weight=3.0))
        lenient = reconcile(staves, VoteConfig(strong_weight=2.0))
        assert strict.verdicts[3].action == "rejected"
        assert lenient.verdicts[3].action == "kept"

    def test_empty_input(self):
        result = reconcile([])
        assert result.verdicts == {}
