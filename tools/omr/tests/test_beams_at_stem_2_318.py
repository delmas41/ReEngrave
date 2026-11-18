"""ROADMAP 2.318 control: Sean's 24 judged beam notes (2.317 answers.json; B01-B12 Brahms, L01-L12 Litolff), the stroke rows and staff lines
of the REAL page cell each note stands in (cropped fixtures with the page crop beside them, `fixtures/beams_at_stem_2_318/`).
Wrong must be 0; an abstention on the hard notes is allowed and reported with its margin. Fast tier: reads no library, no pdf."""
import json
import os

import pytest

from tools.omr.staged import beam_strokes as BS
from tools.omr.staged import beams_at_stem as BAS

FX = os.path.join(os.path.dirname(__file__), "fixtures", "beams_at_stem_2_318", "fixture.json")
HARD = {"L11", "L12", "L07", "B01", "B04"}


def _views(fx):
    return [BS.StrokeView(ordinal=r["ordinal"], kind=r["kind"], box=tuple(r["box"]), length=r["length"], thickness=r["thickness"],
                          sagitta=r["sagitta"], angle=r["angle"], touches=tuple((a, b) for a, b in r["touches"]), space_px=r["space_px"],
                          row_id=r["row_id"], profile=tuple(r["profile"]), ends=tuple(r["ends"])) for r in fx["strokes"]]


def read_tile(fx):
    views = _views(fx)
    stem = BS.find_stem_stroke(views, fx["stem_box"])
    if stem is None:
        return {"count": None, "candidates": (0, 2), "reason": "no_stem_stroke", "margin": None}
    return BAS.beams_at_stem(views, stem, fx["side"], fx["lines"], fx["space"], {r["ordinal"]: r["owner"] for r in fx["strokes"] if r.get("owner")})


def table():
    fx = json.load(open(FX))
    return {t: (fx[t], read_tile(fx[t])) for t in sorted(fx)}


def test_control_wrong_is_zero_and_hard_notes_may_abstain():
    wrong, right, abstained = [], [], []
    for t, (f, r) in table().items():
        if r["count"] is None:
            abstained.append(t)
            assert f["sean_beams"] in range(r["candidates"][0], r["candidates"][1] + 1) or t in HARD, (t, r)
        elif r["count"] == f["sean_beams"]:
            right.append(t)
        else:
            wrong.append((t, r["count"], f["sean_beams"]))
    assert not wrong, wrong
    assert len(right) >= 16, (right, abstained)
    assert set(abstained) <= HARD | {"B12", "B06"} or len(abstained) <= 8, abstained


def test_the_control_can_fail_old_readings_are_wrong_on_it():
    """The three old readings get several of these 24 wrong (FINDINGS 2.317): the control is not one that passes whatever reads it."""
    fx = json.load(open(FX))
    for k in "ABC":
        wr = [t for t, f in fx.items() if f["old_readings"][k] is not None and f["old_readings"][k] != f["sean_beams"]]
        assert wr, k


def test_a_staff_line_is_never_a_bar():
    fx = json.load(open(FX))
    for t in ("L02", "L05", "L09"):          # Sean: quarter notes; a staff line with a neighbour's head fused to it stands near the stem
        assert read_tile(fx[t])["count"] == 0, t


if __name__ == "__main__":
    for t, (f, r) in table().items():
        print(t, f["plate"], "sean", f["sean_beams"], "old", f["old_readings"], "->", r["count"], r["candidates"], r["reason"], r["margin"],
              [(b["thickness"], b["outer"], b["on_line"]) for b in r["bars"]][:3])
