"""The strip marker must be placed by the crop that CUT the strip.

⚠️ TWO DEFECTS, ONE SHAPE. `placeHighlight` in the confirmation UI carried the
comment *"Same arithmetic build_cache.py used to cut the strip"* — and it was a
REIMPLEMENTATION of that arithmetic in JavaScript, not the same thing. Measured
2026-09-07 the two agreed to 0 px, so the reimplementation was not what put the
marker in the wrong place; it is a desync waiting to happen and it is closed
here by shipping the crop origin instead of recomputing it.

What actually put the marker in the wrong place was the JOIN: the overlay
indexed the DETECTED bands by the MAP ENTRY's number (`sys.staves[k]`). Those
are different index spaces the moment a page's map is longer than its detected
band list. Measured on Mahler 5 p2 — 21 map entries against 19 detected bands —
map entry 14 `Kleine Trommel` was marked on the band whose instrument is
`Violin`, 4416 page px away.

`instancesFor` already joins map entry → printed staff BY PARTS through the
hand-read lineup, and abstains where the lineup and the detection disagree
about a system. The overlay must use it, and must abstain with it: works.json
records a real failure from pairing by position (a Trumpet entry silently
claiming the Es-horn staff on Brahms p2).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MAPS = ROOT / "benchmarks" / "omr-staves-map-2026-09"


def _load(name: str):
    path = MAPS / f"{name}.py"
    if not path.is_file():
        pytest.skip(f"{path} not present")
    if str(MAPS) not in sys.path:
        sys.path.insert(0, str(MAPS))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestTheCropOriginIsComputedOnce:

    def test_build_cache_exposes_it_as_a_function(self):
        bc = _load("build_cache")
        got = bc.strip_crop_geometry([{"y0": 100.0, "y1": 200.0},
                                      {"y0": 300.0, "y1": 400.0}])
        assert set(got) == {"y_off", "y_end", "divisor"}
        # top=100, bot=400, band_h=150, pad=90 -> y_off=10
        assert got["y_off"] == 10
        assert got["divisor"] == 2

    def test_the_cutter_uses_it(self):
        src = (MAPS / "build_cache.py").read_text()
        body = src.split("def write_images(", 1)[1].split("\ndef ", 1)[0]
        assert "strip_crop_geometry(" in body, \
            "write_images must cut the strip with the shared geometry"

    def test_the_server_ships_it_rather_than_the_browser_deriving_it(self):
        src = (MAPS / "server.py").read_text()
        assert "strip_crop_geometry" in src, \
            "the server must stamp the crop onto each seed"
        assert "sys.crop.y_off" in src, \
            "the overlay must READ the shipped origin"
        # ⚠️ the reimplementation, gone: no crop arithmetic left in the JS
        for gone in ("Math.trunc(top-pad)", "(bot-top)/ys.length"):
            assert gone not in src, \
                f"the browser is recomputing the crop again ({gone})"

    def test_y_off_reproduces_the_strips_that_were_actually_cut(self):
        """The anti-desync check with teeth: against the built cache.

        Skips where no cache is present — this is a property of a machine that
        has run `build_cache`, not of the repo.
        """
        bc = _load("build_cache")
        idx = Path.home() / ".cache/reengrave-staves-map-completion/index.json"
        if not idx.is_file():
            pytest.skip("no built cache on this machine")
        doc = json.loads(idx.read_text())
        checked = 0
        for row in doc["rows"]:
            for s in row.get("detected", {}).get("systems", []):
                if not s.get("staves"):
                    continue
                got = bc.strip_crop_geometry(s["staves"])
                # the historical arithmetic, inlined, as the thing to match
                top = int(min(st["y0"] for st in s["staves"]))
                bot = int(max(st["y1"] for st in s["staves"]))
                band_h = max(1.0, (bot - top) / max(1, len(s["staves"])))
                assert got["y_off"] == max(0, top - int(band_h * 0.6))
                checked += 1
        assert checked >= 5


class TestTheMarkerIsJoinedByPartsNotByOrdinal:

    def test_the_overlay_goes_through_instances_for(self):
        src = (MAPS / "server.py").read_text()
        body = src.split("function placeHighlight(", 1)[1].split("\nfunction ", 1)[0]
        assert "instancesFor(" in body, \
            "the band must be found by PARTS, the way the rest of the UI does"
        # ⚠️ CODE ONLY. The docstring above the function quotes the defect, and
        # a naive substring test trips on the explanation rather than the bug.
        code = "\n".join(l for l in body.splitlines()
                         if not l.strip().startswith("//"))
        assert "sys.staves[k]" not in code, \
            ("indexing the detected bands by the map entry's number is the "
             "defect — 21 entries against 19 bands marked Kleine Trommel on "
             "a Violin staff")

    def test_it_abstains_rather_than_marking_the_wrong_band(self):
        src = (MAPS / "server.py").read_text()
        body = src.split("function placeHighlight(", 1)[1].split("\nfunction ", 1)[0]
        assert body.count("display='none'") >= 3, \
            ("every way the join can fail must hide the marker: no crop, no "
             "instance, not printed, no band")
        assert "!inst.printed" in body

    def test_an_unplaceable_slot_says_why(self):
        """An unexplained missing marker reads as a broken tool."""
        src = (MAPS / "server.py").read_text()
        assert "is not marked here" in src
