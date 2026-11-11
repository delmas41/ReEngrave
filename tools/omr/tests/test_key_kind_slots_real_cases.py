"""ROADMAP 2.299 controls from REAL judged cases (CLAUDE rule 7): the rows of Sean's 2.292 staff-start tiles, cut from a saved Litolff / Brahms gather.

`benchmarks/key-kind-from-slots-2026-11/data/tile_fixtures.json` holds, per tile, the staff's key-object row (measured slots), its READ clef and Sean's
own words. A staff where he read three flats must come out READ flats 3 or ABSTAIN for a named reason -- never another key; a staff where he saw no
accidentals must not gain a key; tile 11 (cut off by our crop, unjudged) is excluded. Every other tile abstains by name: that is the reach.
"""
import json
import pathlib

import pytest

from tools.omr.staged import key_kind_slots as K

FIX = pathlib.Path(__file__).resolve().parents[3] / "benchmarks" / "key-kind-from-slots-2026-11" / "data" / "tile_fixtures.json"
TILES = json.loads(FIX.read_text())
JUDGED = {n: t for n, t in TILES.items() if t["sean_fifths"] is not None}      # tile 11 is cut off: not judged


def test_the_fixture_is_real_and_complete():
    assert len(TILES) == 12 and "11" in TILES and "11" not in JUDGED and len(JUDGED) == 11
    assert all(t["key_row"] for t in TILES.values())


@pytest.mark.parametrize("n", sorted(JUDGED, key=int))
def test_never_a_key_other_than_seans(n):
    t = JUDGED[n]
    res = K.read(t["key_row"], t["clef_read"])
    got = K.fifths_of(res)
    if got is not None:
        assert got == t["sean_fifths"], (n, res)
    else:
        assert res["why"] and res["standing"] is None


@pytest.mark.parametrize("n", sorted(n for n, t in JUDGED.items() if t["sean_fifths"] == 0))
def test_a_staff_with_no_accidentals_gains_no_key(n):
    t = JUDGED[n]
    assert K.fifths_of(K.read(t["key_row"], t["clef_read"])) is None


def test_tile_1_is_read_three_flats():
    t = TILES["1"]
    res = K.read(t["key_row"], t["clef_read"])
    assert (t["sean_clef"], t["sean_fifths"]) == ("F", -3)
    assert K.fifths_of(res) == -3 and res["standing"] == "READ" and res["kind"] == "flat"


def test_the_unread_clef_tiles_abstain_for_the_clef():
    for n in ("2", "6"):
        t = TILES[n]
        assert t["clef_read"] is None
        assert K.read(t["key_row"], t["clef_read"])["why"] == "no_clef"


def test_the_control_can_fail():
    # the same real rows read against the WRONG sign (flats mirrored to sharps' steps) must not come out as Sean's answer
    t = TILES["1"]
    row = json.loads(json.dumps(t["key_row"]))
    for p in row["ko"]["read_pieces"]:
        p["step"] = 8.0 - p["step"]
    assert K.fifths_of(K.read(row, t["clef_read"])) != -3
