"""Unit tests for cross-staff time-signature agreement
(`transcribe._flag_time_signature_disagreement`).

Every staff of a system shares one meter, so genuinely-DETECTED meters that
disagree are a mis-read. Back-filled / propagated meters (source-tagged) are
inference, not evidence, and never participate.
"""

from __future__ import annotations

from tools.omr.transcribe import _flag_time_signature_disagreement


def _staff(i, ts):
    """`ts`: (num, den) for a detected meter, (num, den, source) for a
    back-filled one, or None."""
    if ts is None:
        t = None
    elif len(ts) == 2:
        t = {"numerator": ts[0], "denominator": ts[1], "raw": f"{ts[0]}/{ts[1]}"}
    else:
        t = {"numerator": ts[0], "denominator": ts[1], "raw": f"{ts[0]}/{ts[1]}", "source": ts[2]}
    return {"staff_index": i, "time_signature": t, "measures": []}


def _system(specs):
    return {"staves": [_staff(i, ts) for i, ts in enumerate(specs)]}


def _warns(system):
    _flag_time_signature_disagreement(system)
    return {st["staff_index"]: st.get("time_signature_disagreement") for st in system["staves"]}


class TestTimeSignatureDisagreement:
    def test_all_detected_agree_no_flag(self):
        assert all(v is None for v in _warns(_system([(4, 4), (4, 4), (4, 4)])).values())

    def test_single_staff_noop(self):
        assert _warns(_system([(4, 4)])) == {0: None}

    def test_fewer_than_two_detected_noop(self):
        # One detected, the rest null -> nothing to cross-check.
        assert all(v is None for v in _warns(_system([(4, 4), None, None])).values())

    def test_backfilled_meters_are_ignored(self):
        # One genuinely detected 4/4 + a back-filled 3/4 -> only one detected
        # meter participates, so no disagreement.
        assert all(v is None for v in _warns(_system([(4, 4), (3, 4, "inferred")])).values())

    def test_outlier_flagged_against_majority(self):
        w = _warns(_system([(4, 4), (4, 4), (4, 4), (3, 4)]))
        assert all(w[i] is None for i in range(3))
        assert w[3] == {
            "staff_time_signature": "3/4",
            "system_detected_meters": ["3/4", "4/4"],
            "majority_meter": "4/4",
            "agreement": "3/4",
            "confidence": 0.75,
            "confidence_label": "medium",
        }

    def test_strong_majority_high_confidence(self):
        w = _warns(_system([(4, 4)] * 5 + [(3, 4)]))
        assert w[5]["confidence_label"] == "high"
        assert w[5]["confidence"] == round(5 / 6, 3)

    def test_even_split_flags_both_low_no_majority(self):
        # 1-1: can't say which meter is right -> both flagged low, majority null.
        w = _warns(_system([(4, 4), (3, 4)]))
        assert w[0] is not None and w[1] is not None
        for i in (0, 1):
            assert w[i]["confidence_label"] == "low"
            assert w[i]["majority_meter"] is None
            assert w[i]["system_detected_meters"] == ["3/4", "4/4"]

    def test_ignores_partial_meter_dicts(self):
        # A time_signature missing a numerator/denominator isn't a usable
        # detected meter.
        sysd = _system([(4, 4), (4, 4)])
        sysd["staves"][1]["time_signature"] = {"numerator": None, "denominator": 4}
        assert all(v is None for v in _warns(sysd).values())
