"""`OMR_CONTEST_DUMP` records the DISTANCES it decides on.

The dump already carried both confidences and the deciding tier. It did not
carry the band distances — the quantity that decides 94.1% of the 4,521 contests
on the scan gate, and the one this project has already caught behaving like a
coin flip: three of Mahler's four hairpins were misattributed at 5-62 px, against
25 px the other way for the one kept correctly (CLAUDE.md, hairpins).

"Decided by distance" without the margin cannot be read as anything but
"decided". These tests pin the margin, and pin that recording it moved no
verdict.

⚠️ Every test here was run RED with the three distance fields removed from the
dump. The verdict-neutrality test was run red differently — by making the dump
reach into the detection list — because a test that only reads the dump cannot
notice the pipeline moving underneath it. ⚠️ The FIRST attempt at that mutation
(swapping `loser`/`winner` inside the dump block) left it green, and correctly
so: `verdicts.append` happens above the dump, so the swap changed nothing. A
mutation that does not mutate proves nothing.
"""

from __future__ import annotations

import pytest

from tools.omr.transcribe import _dedupe_cross_staff_detections


def _note(y, pitch="C4", conf=0.9):
    box = [50, y - 15, 30, 30]
    return {"category": "notehead", "class": "noteheadBlackOnLine",
            "confidence": conf, "bbox": box, "bbox_page": box, "pitch": pitch}


def _ledger(y):
    box = [45, y - 2, 40, 4]
    return {"category": "other", "class": "ledgerLine",
            "confidence": 0.9, "bbox": box, "bbox_page": box}


def _page(a_dets, b_dets, ledger_dets=()):
    def staff(idx, dets):
        return {"staff_index": idx,
                "measures": [{"measure_index": 0, "detections": list(dets)}]}
    extra = {"staff_index": 2,
             "measures": [{"measure_index": 0, "detections": list(ledger_dets)}]}
    return {"page_index": 0,
            "systems": [{"staves": [staff(0, a_dets), staff(1, b_dets), extra]}]}


BANDS = {0: (100, 200, 25), 1: (400, 500, 25), 2: (700, 800, 25)}


@pytest.fixture()
def dump_on(monkeypatch):
    monkeypatch.setenv("OMR_CONTEST_DUMP", "1")


class TestTheDumpCarriesTheDistances:
    def test_a_distance_decided_contest_records_both_distances_and_the_margin(
            self, dump_on):
        """The glyph sits at y=350: 150 px below staff 0's bottom line and
        50 px above staff 1's top. Distance decides, and now says by how much.
        """
        pg = _page([_note(350)], [_note(350)])
        assert _dedupe_cross_staff_detections(pg, BANDS) == 1
        contest, = pg["contested_notehead_pairs"]
        assert contest["decided_by"] == "distance"
        assert contest["band_distance_i"] == pytest.approx(150.0)
        assert contest["band_distance_j"] == pytest.approx(50.0)
        assert contest["band_distance_margin"] == pytest.approx(100.0)
        assert contest["distance_prefers"] == 1
        assert contest["loser_staff"] == 0

    def test_a_NEAR_TIE_is_now_distinguishable_from_a_clear_call(self, dump_on):
        """The whole point. Two contests decided the same way, one on 100 px
        and one on 4, and before this they were the same row."""
        pg = _page([_note(299)], [_note(299)])   # 99 px below / 101 px above
        assert _dedupe_cross_staff_detections(pg, BANDS) == 1
        contest, = pg["contested_notehead_pairs"]
        assert contest["decided_by"] == "distance"
        assert contest["band_distance_margin"] == pytest.approx(2.0)

    def test_a_LADDER_decided_contest_still_records_what_distance_would_say(
            self, dump_on):
        """Recorded even where a stronger tier won — otherwise there is no way
        to ask, later, how often the tiers agree. Here they DISAGREE: the
        ladder joins the glyph to the far staff."""
        rungs = [_ledger(200 + k * 25) for k in range(1, 7)]
        pg = _page([_note(350)], [_note(350)], ledger_dets=rungs)
        assert _dedupe_cross_staff_detections(pg, BANDS) == 1
        contest, = pg["contested_notehead_pairs"]
        assert contest["decided_by"] == "ladder"
        assert contest["loser_staff"] == 1
        assert contest["distance_prefers"] == 1     # ...and distance disagreed
        assert contest["band_distance_margin"] == pytest.approx(100.0)


class TestRecordingChangesNoVerdict:
    def test_the_dump_removes_exactly_the_same_detection_either_way(
            self, monkeypatch):
        """The dump's own docstring promises this and nothing asserted it.

        Run RED by having the dump clear one side's detection list.
        """
        def survivors(dump: str):
            monkeypatch.setenv("OMR_CONTEST_DUMP", dump)
            rungs = [_ledger(200 + k * 25) for k in range(1, 7)]
            pg = _page([_note(350)], [_note(350)], ledger_dets=rungs)
            removed = _dedupe_cross_staff_detections(pg, BANDS)
            kept = [len(s["measures"][0]["detections"])
                    for s in pg["systems"][0]["staves"]]
            return removed, kept

        assert survivors("0") == survivors("1")

    def test_the_dump_key_is_absent_when_the_dump_is_off(self, monkeypatch):
        monkeypatch.setenv("OMR_CONTEST_DUMP", "0")
        pg = _page([_note(350)], [_note(350)])
        _dedupe_cross_staff_detections(pg, BANDS)
        assert "contested_notehead_pairs" not in pg
