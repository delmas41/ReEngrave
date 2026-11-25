"""ROADMAP 2.349 (STAGED: GATHER `stroke_map.tip_columns` behind `OMR_STEM_TIP_COLUMNS`, ADJUDICATE `beam_strokes.two_bars_at_stem` behind
`OMR_TWO_BEAMS_AT_STEM`; both default OFF). TWO BEAMS ARE READ FROM THE INK AT THE NOTE'S OWN STEM.

Controls are REAL: `fixtures/two_beams_at_stem_2_349/` holds the full-resolution erased-raster crop (600 dpi master cell map) around the tip of each
judged control stem of the 2.318 fixture (Sean's 24 beam tiles of 2.317, Litolff p2 bar 13, and the other judged notes there) plus Brahms p0
2.78-phase2-review tile 5 (Sean 2026-10-10 "16th", 2026-11-24 "are 16ths") with its own stroke rows. The GATHER measurement is run on those
pixels here, joined to the note's real stroke rows, and the count is read with the reader OFF (today) and ON.

What must hold: Sean's five fused sixteenths (B01, B04, B06, B10, tile 5) are narrowed OFF and READ as two beams ON (the control fails on old code);
no judged eighth or quarter moves; L12 -- one beam with a lump as thick as two beams at the stem, Sean "8th" -- stays narrowed (a slab never
decides). No record, no gather, no PDF."""
from __future__ import annotations

import dataclasses
import json
import os
import pathlib
from unittest import mock

import numpy as np
import pytest

from tools.omr.staged import beam_strokes as BS
from tools.omr.staged import stroke_map as SM
from tools.omr.tests.test_staged_one_beam_count_2_318 import NOTES, views

HERE = pathlib.Path(__file__).parent / "fixtures" / "two_beams_at_stem_2_349"
META = json.loads((HERE / "controls.json").read_text())["notes"]
CROPS = np.load(HERE / "tip_crops.npz")
T5 = "glyph/0/0/12/1/1"
SIXTEENTHS = {"glyph/17/0/11/4/3": "B01", "glyph/17/0/12/0/6": "B04", "glyph/4/1/13/5/6": "B06", "glyph/4/1/12/5/4": "B10", T5: "2.78 tile 5"}
L12 = "glyph/6/0/8/0/3"


def note(key):
    return META[key]["note"] if key == T5 else NOTES[key]


def entries(key):
    """The GATHER fact for this note's stem tip(s), measured NOW on the real pixels of the crop."""
    out = []
    for t in META[key]["tips"]:
        h, w = t["shape"]
        ink = np.unpackbits(CROPS[t["crop"]], axis=1)[:, :w].astype(bool)
        erased = np.where(ink, 0, 255).astype(np.uint8)
        ox, oy = t["origin"]
        e = SM.tip_columns(erased, t["x"][0] - ox, t["x"][1] - ox, t["y"] - oy, 1 if t["end"] == "top" else -1, t["sp"])
        # back in the cell's frame, where the count's stem lives
        e["x"] = [t["x"][0], t["x"][1]]
        e["y"] = t["y"]
        out.append(e)
    return tuple(out)


def count(key, on: bool):
    x = note(key)
    vs = views(x)
    vs = [dataclasses.replace(vs[0], tip_columns=entries(key))] + vs[1:]
    roles = BS.roles(vs, face_join=True, trough=True, one_count=True)
    with mock.patch.dict(os.environ, {BS.TWO_BEAMS_AT_STEM_ENV: "1" if on else "0"}):
        return BS.beam_count(vs, roles, tuple(float(v) for v in x["head"]), x["side"] if x["side"] in ("up", "down") else None)


JUDGED = [k for k in META if note(k)["truth"] is not None]


@pytest.mark.parametrize("key", sorted(SIXTEENTHS))
def test_seans_fused_sixteenths_read_two_beams(key):
    off, on = count(key, False), count(key, True)
    assert (off["state"], off["certain"], off["possible"]) == ("narrowed", 1, 2), SIXTEENTHS[key]     # the control fails on today's code
    assert (on["state"], on["certain"], on["possible"]) == ("read", 2, 2), (SIXTEENTHS[key], [s.get("two_bars") for s in on["stems"]])


@pytest.mark.parametrize("key", JUDGED)
def test_no_judged_note_is_read_wrong(key):
    """Every judged note: a count read OFF is read the same ON; a count the reader moves lands on Sean's value (or still holds it)."""
    truth = note(key)["truth"]
    off, on = count(key, False), count(key, True)
    if off["state"] == "read":
        assert (on["state"], on["certain"], on["possible"]) == ("read", off["certain"], off["possible"]), (key, off, on)
    elif (on["state"], on["certain"], on["possible"]) != (off["state"], off["certain"], off["possible"]):
        # a count the reader moved: read, Sean's value; or narrower, still holding it (a flagged note's value is the flag reader's, not this count's)
        assert (on["certain"] == truth) if on["state"] == "read" else (on["certain"] <= truth <= on["possible"]), (key, off, on)


def test_a_slab_alone_never_decides_l12():
    """Sean's L12 (Litolff p6, "8th"): a slab 1.27-1.33 sp thick at the stem, as thick as two fused beams, never opening into two bars. It stays
    narrowed with the reader ON -- thickness at the stem cannot tell it from tile 5's fused pair (1.37), only the paper between two bars can."""
    on = count(L12, True)
    assert (on["state"], on["certain"], on["possible"]) == ("narrowed", 1, 2)
    assert on["stems"][0]["two_bars"]["sides"]["L"] == "slab"


def test_the_paper_between_the_beams_is_what_reads_tile_5():
    """Tile 5: one slab where the two beams meet the stem (0.15-0.75 sp out), the paper between them from 0.9 sp on. The side reading is `two`
    only because the walk passes the slab and finds the two bars; cut the columns at 0.75 sp and the same ink stays a slab."""
    e = entries(T5)[0]
    side = "L"
    assert BS._side_verdict(e[side], set()) == "two"
    assert BS._side_verdict(e[side][:5], set()) == "slab"


def test_a_second_bar_held_by_another_mark_is_not_a_beam():
    """B01's second bar, its ink handed to a claimed stroke: the column says `claimed`, the side is unread, and the stem is not read two."""
    e = entries("glyph/17/0/11/4/3")[0]
    owners = {int(r[2]) for c in e["R"] if c for r in c}
    claimed_all = owners | {-1}
    assert BS._side_verdict(e["R"], set()) == "two"
    assert BS._side_verdict(e["R"], claimed_all) != "two"


def test_off_files_nothing_and_on_files_the_columns(monkeypatch):
    """GATHER: with `OMR_STEM_TIP_COLUMNS` off a stroke carries no `tip_columns` (the row is byte-identical); on, a stem-length vertical whose end a
    beam touches carries them. On B01's real crop."""
    t = META["glyph/17/0/11/4/3"]["tips"][0]
    h, w = t["shape"]
    ink = np.unpackbits(CROPS[t["crop"]], axis=1)[:, :w].astype(bool)
    erased = np.where(ink, 0, 255).astype(np.uint8)
    sp = t["sp"]
    lines = [t["y"] - t["origin"][1] - k * sp for k in (5, 4, 3, 2, 1)]
    monkeypatch.setenv(SM.STEM_TIP_COLUMNS_ENV, "0")
    off = SM.map_strokes(erased, sp, lines, None, split_joins=False)
    assert all(not s.tip_columns for s in off.strokes)
    monkeypatch.setenv(SM.STEM_TIP_COLUMNS_ENV, "1")
    on = SM.map_strokes(erased, sp, lines, None, split_joins=False)
    got = [e for s in on.strokes if s.kind == "vertical" for e in s.tip_columns]
    assert got and any(BS._side_verdict(e["R"], set()) == "two" for e in got if e["end"] == "bottom")
