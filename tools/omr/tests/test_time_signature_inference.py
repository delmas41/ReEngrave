"""Unit tests for time-signature inference (rhythm.py, 2026-07 audit lever).

Covers the length->meter map, the pure majority vote, per-measure length
measurement, per-column page extraction, and the back-fill that feeds both
the rhythm-sum check and export.
"""

from __future__ import annotations

import pytest

from tools.omr.rhythm import (
    _meter_for_length,
    measure_length_beats,
    infer_time_signature_from_lengths,
    infer_page_time_signature,
    backfill_page_time_signatures,
)


# ── detection-dict builders (mirror transcribe.py's measure schema) ──────────

def _nh(x: int, *, duration_beats: float = 1.0, stem_direction: str | None = None):
    d = {
        "category": "notehead",
        "class": "noteheadBlackOnLine",
        "bbox": [x, 200, 30, 20],
        "bbox_page": [x, 200, 30, 20],
        "confidence": 0.9,
        "pitch": "C4",
        "duration_beats": duration_beats,
        "duration_type": "quarter",
        "dots": 0,
    }
    if stem_direction is not None:
        d["stem_direction"] = stem_direction
    return d


def _rest(x: int, *, duration_beats: float = 1.0):
    return {
        "category": "rest",
        "class": "restQuarter",
        "bbox": [x, 200, 30, 30],
        "bbox_page": [x, 200, 30, 30],
        "confidence": 0.9,
        "pitch": None,
        "duration_beats": duration_beats,
        "duration_type": "quarter",
        "dots": 0,
    }


def _measure(detections, *, measure_index=0, time_signature=None, phase1=False):
    m = {"measure_index": measure_index, "detections": detections,
         "time_signature": time_signature}
    if phase1:
        m["phase1_warning"] = "fused"
    return m


def _quarters(n, *, start_x=100, step=40):
    """n quarter-note noteheads spread across the bar (length == n beats)."""
    return [_nh(start_x + i * step, duration_beats=1.0) for i in range(n)]


def _page(systems):
    return {"systems": systems}


def _system(staves):
    return {"staves": [{"staff_index": i, "measures": ms} for i, ms in enumerate(staves)]}


# ── _meter_for_length ────────────────────────────────────────────────────────

class TestMeterForLength:
    @pytest.mark.parametrize("length,meter", [
        (4.0, (4, 4)), (3.0, (3, 4)), (2.0, (2, 4)), (5.0, (5, 4)),
        (6.0, (6, 4)), (7.0, (7, 4)),
        (1.5, (3, 8)), (2.5, (5, 8)), (3.5, (7, 8)), (4.5, (9, 8)), (5.5, (11, 8)),
    ])
    def test_standard_meters(self, length, meter):
        assert _meter_for_length(length) == meter

    def test_snaps_small_rhythm_error(self):
        # A measure that resolved a hair short/long still maps to 4/4.
        assert _meter_for_length(3.97) == (4, 4)
        assert _meter_for_length(4.12) == (4, 4)

    @pytest.mark.parametrize("length", [8.5, 12.0, 16.5, 0.0, 1.0, 8.0, 7.75])
    def test_non_meter_lengths_rejected(self, length):
        # Fused-measure lengths and things that don't snap to a standard
        # meter get no vote. (1.0 = 1/4 and 8.0 = 8/4 are intentionally
        # excluded as implausible-as-a-page-meter; 7.75 snaps to 8.0.)
        assert _meter_for_length(length) is None

    def test_half_beat_snapping_is_nearest_neighbor(self):
        # 4.375 is within a quarter-beat of 4.5, so it snaps to 9/8. This
        # is accepted noise: near-miss lengths vote for their nearest meter,
        # and the strong-plurality gate keeps stray votes from winning.
        assert _meter_for_length(4.375) == (9, 8)


# ── infer_time_signature_from_lengths (the pure vote) ────────────────────────

class TestInferFromLengths:
    def test_strong_mode_fires(self):
        r = infer_time_signature_from_lengths([4.0] * 8 + [2.0, 3.0])
        assert r["numerator"] == 4 and r["denominator"] == 4
        assert r["raw"] == "4/4" and r["source"] == "inferred"
        assert r["votes"] == 8 and r["voters"] == 10
        assert r["confidence"] == 0.8

    def test_three_four(self):
        r = infer_time_signature_from_lengths([3.0] * 7 + [1.5])
        assert (r["numerator"], r["denominator"]) == (3, 4)

    def test_compound_surfaces_as_simple_equivalent(self):
        # 6/8 bars resolve to 3.0 quarters -> reported as 3/4 (same length).
        r = infer_time_signature_from_lengths([3.0] * 6)
        assert (r["numerator"], r["denominator"]) == (3, 4)

    def test_split_vote_abstains(self):
        assert infer_time_signature_from_lengths([4.0] * 3 + [3.0] * 3) is None

    def test_too_few_votes_abstains(self):
        assert infer_time_signature_from_lengths([4.0] * 3) is None

    def test_all_noise_abstains(self):
        assert infer_time_signature_from_lengths([8.5, 12.0, 16.5, 7.25, 5.375]) is None

    def test_empty_abstains(self):
        assert infer_time_signature_from_lengths([]) is None

    def test_fraction_boundary(self):
        # 6 of 10 == 0.6 exactly -> fires (>= threshold).
        r = infer_time_signature_from_lengths([4.0] * 6 + [3.0] * 4)
        assert r is not None and r["confidence"] == 0.6

    def test_just_below_fraction_abstains(self):
        # 5 of 10 == 0.5 < 0.6 -> abstains even though 4/4 is the plurality.
        assert infer_time_signature_from_lengths([4.0] * 5 + [3.0] * 5) is None


# ── measure_length_beats ─────────────────────────────────────────────────────

class TestMeasureLength:
    def test_four_quarters(self):
        length, has_note = measure_length_beats(_quarters(4))
        assert length == 4.0 and has_note is True

    def test_empty_measure(self):
        assert measure_length_beats([]) == (0.0, False)

    def test_rest_only_has_no_note(self):
        length, has_note = measure_length_beats([_rest(100, duration_beats=4.0)])
        assert has_note is False  # a whole rest fills any bar -> no meter evidence

    def test_takes_fullest_voice(self):
        # stem-up voice = 4 quarters (full), stem-down = 2 quarters (sparse).
        dets = ([_nh(100 + i * 40, stem_direction="up") for i in range(4)]
                + [_nh(120 + i * 80, stem_direction="down") for i in range(2)])
        length, has_note = measure_length_beats(dets)
        assert length == 4.0 and has_note is True


# ── page-level inference + back-fill ─────────────────────────────────────────

class TestPageInference:
    def test_per_column_recovers_sparse_orchestral(self):
        # Two staves per system: one always sparse (2 beats), one full (4).
        # Per-measure voting would split 2.0/4.0; per-column max recovers 4.0.
        systems = []
        for _ in range(4):
            full = [_measure(_quarters(4), measure_index=i) for i in range(2)]
            sparse = [_measure(_quarters(2), measure_index=i) for i in range(2)]
            systems.append(_system([full, sparse]))
        r = infer_page_time_signature(_page(systems))
        assert r is not None and (r["numerator"], r["denominator"]) == (4, 4)

    def test_backfill_fills_only_nulls(self):
        # 8 measures of 4 beats, one already detected as 3/4 (a wrong-looking
        # outlier we must NOT overwrite), rest null.
        detected = {"numerator": 3, "denominator": 4, "raw": "3/4"}
        ms = [_measure(_quarters(4), measure_index=i) for i in range(8)]
        ms[0]["time_signature"] = detected
        page = _page([_system([ms])])
        inferred = backfill_page_time_signatures(page)
        assert inferred is not None and inferred["raw"] == "4/4"
        # detected measure untouched
        assert page["systems"][0]["staves"][0]["measures"][0]["time_signature"] is detected
        # null measures back-filled with inferred
        for m in page["systems"][0]["staves"][0]["measures"][1:]:
            assert m["time_signature"]["raw"] == "4/4"
            assert m["time_signature"]["source"] == "inferred"
        # staff-level null back-filled + page records it
        assert page["systems"][0]["staves"][0]["time_signature"]["raw"] == "4/4"
        assert page["inferred_time_signature"]["raw"] == "4/4"

    def test_backfill_noop_when_unconfident(self):
        # Scattered lengths -> abstain -> nothing touched, returns None.
        ms = [_measure(_quarters(n), measure_index=i)
              for i, n in enumerate([4, 3, 2, 5, 6, 7])]
        page = _page([_system([ms])])
        assert backfill_page_time_signatures(page) is None
        assert "inferred_time_signature" not in page
        for m in ms:
            assert m["time_signature"] is None

    def test_fused_and_restonly_excluded_from_vote(self):
        # 6 good 4/4 bars (min_votes) + fused/rest-only noise that must not
        # derail the vote.
        ms = [_measure(_quarters(4), measure_index=i) for i in range(6)]
        ms.append(_measure(_quarters(12), measure_index=6, phase1=True))   # fused
        ms.append(_measure([_rest(100, duration_beats=4.0)], measure_index=7))  # rest-only
        page = _page([_system([ms])])
        inferred = backfill_page_time_signatures(page)
        assert inferred is not None and inferred["raw"] == "4/4"
        # confidence is 1.0 — the fused (phase1) and rest-only bars never
        # voted, so all 6 valid voters agree on 4/4.
        assert inferred["confidence"] == 1.0 and inferred["voters"] == 6
        # back-fill still fills the fused measure's null meter (harmless — the
        # rhythm-sum check then flags its 12-beat content against 4/4).
        assert ms[6]["time_signature"]["raw"] == "4/4"
