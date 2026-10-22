"""The snap grid beyond the staff anchors on MEASURED ledger rungs.

Sean's hollow-campaign defect: click-to-box suggested on-line for in-space
notes on ledger lines — never inside the staff. Cause: inside the staff the
grid uses the cell's own measured line positions, but beyond it the grid
extrapolated at the staff spacing, and ledger pitch is a fact about the
engraving (Litolff ~1.10x the staff spacing, Peters ~0.975x — measured in
benchmarks/omr-snap-ledger-2026-09/FINDINGS.md, where the wrong-suggestion
rate was 38-39% at the 2nd ledger and beyond vs 4.6% inside).

The fix is ledger_grid.measure_ledger_rungs + snap_to_staff(ledger_rungs=).
These tests pin its three contracts:

  1. the in-staff grid and the no-rungs behaviour are UNTOUCHED,
  2. measured rungs re-anchor the outside grid (the defect case flips),
  3. an incomplete ladder abstains beyond its reach instead of extrapolating
     from a lone rung.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate.ledger_grid import measure_ledger_rungs  # noqa: E402
from tools.omr.annotate.server import snap_to_staff  # noqa: E402

YS = [100, 200, 300, 400, 500]  # spacing 100 — one grid step is 50


def triple(got: dict) -> tuple:
    return (got["step"], got["snapped_y"], got["position"])


# --- contract 1: nothing inside the staff, and nothing without rungs -------


@pytest.mark.omr_annotate
def test_empty_rungs_match_the_two_arg_call_everywhere() -> None:
    empty = {"above": [], "below": []}
    for y in range(-80, 1101, 7):
        assert triple(snap_to_staff(YS, y)) == triple(
            snap_to_staff(YS, y, ledger_rungs=empty)
        )


@pytest.mark.omr_annotate
def test_in_staff_snapping_ignores_any_rungs() -> None:
    """The in-staff grid is measured-correct (CLAUDE.md) — rungs, however
    aggressive, may only ever move LEDGER territory."""
    wild = {"above": [30.0, -80.0], "below": [572.0, 690.0]}
    for y in range(100, 501, 3):
        assert triple(snap_to_staff(YS, y)) == triple(
            snap_to_staff(YS, y, ledger_rungs=wild)
        )


@pytest.mark.omr_annotate
def test_measured_rungs_key_only_appears_when_rungs_were_passed() -> None:
    assert "measured_rungs" not in snap_to_staff(YS, 250)
    got = snap_to_staff(YS, 250, ledger_rungs={"below": [615.0]})
    assert got["measured_rungs"] == {"above": 0, "below": 1}


# --- contract 2: the defect case flips --------------------------------------


@pytest.mark.omr_annotate
def test_wide_ledger_pitch_no_longer_flips_the_variant() -> None:
    """Litolff-shaped geometry: rungs 15% wider than the staff spacing.

    A click ON the true 2nd ledger (y=730) sits nearer the OLD grid's
    in-space slot (750) than its line slot (700) — the defect, pinned here
    as the baseline — and the measured grid puts the line back under it.
    """
    rungs = {"above": [], "below": [615.0, 730.0]}
    assert snap_to_staff(YS, 730)["position"] == "in_space"  # the defect
    got = snap_to_staff(YS, 730, ledger_rungs=rungs)
    assert (got["position"], got["step"], got["snapped_y"]) == ("on_line", 12, 730.0)
    # The space BETWEEN the measured rungs is their midpoint, not the
    # extrapolated one.
    mid = snap_to_staff(YS, 672, ledger_rungs=rungs)
    assert (mid["position"], mid["step"], mid["snapped_y"]) == (
        "in_space", 11, 672.5,
    )
    assert mid["ledger"] is True


# --- contract 3: a lone rung does not steer the deep grid ------------------


@pytest.mark.omr_annotate
def test_incomplete_ladder_abstains_beyond_its_reach() -> None:
    """One measured rung, a click 3.5 spaces out: real ledgers run all the
    way to a real note, so a ladder that stopped at rung 1 has lost the
    trail — beyond it the snap must behave exactly as it always did."""
    rungs = {"above": [], "below": [615.0]}
    deep = 850.0
    assert triple(snap_to_staff(YS, deep, ledger_rungs=rungs)) == triple(
        snap_to_staff(YS, deep)
    )
    # ...while within reach the rung still anchors the grid.
    near = snap_to_staff(YS, 610, ledger_rungs=rungs)
    assert (near["step"], near["snapped_y"]) == (10, 615.0)


# --- the rung reader itself -------------------------------------------------


def _synthetic_cell() -> "np.ndarray":
    """A staff, two wide-pitch ledgers above, and a hollow head ON the outer
    one whose counter SPLITS the rung — the case that made contiguous-run
    detection blind (see ledger_grid's module docstring)."""
    img = np.full((800, 300), 255, dtype=np.uint8)
    ys = [300, 400, 500, 600, 700]
    for ly in ys:
        img[ly - 2 : ly + 3, 10:290] = 0
    # Ledgers at pitch 1.12x: 300-112=188 and 300-224=76.
    img[186:191, 80:221] = 0
    yy, xx = np.ogrid[:800, :300]
    outer = ((xx - 150) / 86.0) ** 2 + ((yy - 76) / 50.0) ** 2 <= 1.0
    counter = ((xx - 150) / 40.0) ** 2 + ((yy - 76) / 28.0) ** 2 <= 1.0
    img[outer & ~counter] = 0
    # The rung THROUGH the head stops at the counter on both sides.
    img[74:79, 80:111] = 0
    img[74:79, 190:221] = 0
    return img


@pytest.mark.omr_annotate
def test_reader_measures_rungs_through_a_hollow_head() -> None:
    rungs = measure_ledger_rungs(_synthetic_cell(), [300, 400, 500, 600, 700], 150.0)
    assert rungs["below"] == []
    assert len(rungs["above"]) == 2
    assert abs(rungs["above"][0] - 188) <= 4
    assert abs(rungs["above"][1] - 76) <= 4


@pytest.mark.omr_annotate
def test_reader_abstains_on_blank_ink_and_bad_geometry() -> None:
    blank = np.full((200, 200), 255, dtype=np.uint8)
    assert measure_ledger_rungs(blank, [50, 60, 70, 80, 90], 100.0) == {
        "above": [], "below": [],
    }
    assert measure_ledger_rungs(blank, [], 100.0) == {"above": [], "below": []}
    # A probe column against the image edge has no room for a rung.
    assert measure_ledger_rungs(blank, [50, 60, 70, 80, 90], 2.0) == {
        "above": [], "below": [],
    }


# --- end to end through the endpoint ----------------------------------------


@pytest.mark.omr_annotate
def test_snap_endpoint_reads_the_cells_own_ledgers(tmp_path: Path) -> None:
    """The API answer changes where the page's ledgers say so, and falls
    back to the old grid where the cell shows no rungs at all."""
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    PIL_Image = pytest.importorskip("PIL.Image")
    from tools.omr.annotate.server import create_app

    root = tmp_path / "bench"
    (root / "cells").mkdir(parents=True)
    (root / "detections").mkdir()
    (root / "verdicts").mkdir()

    def entry(cell_id: str) -> dict:
        return {
            "cell_id": cell_id,
            "pdf": "synthetic.pdf",
            "page": 0,
            "system_index": 0,
            "staff_index": 0,
            "measure_index": 0,
            "cell_png_path": f"cells/{cell_id}.png",
            "nostaff_png_path": None,
            "staff_line_ys_canonical": YS,
            "clef": "treble",
            "source_tag": "synth",
            "cell_canonical_w": 300,
            "cell_canonical_h": 900,
        }

    (root / "cells.json").write_text(json.dumps([entry("ledgers"), entry("blank")]))
    for cid in ("ledgers", "blank"):
        (root / "detections" / f"{cid}.json").write_text(
            json.dumps({"cell_id": cid, "detections": []})
        )
    (root / "batch_config.json").write_text(json.dumps({
        "pass_name": "hollow",
        "classes": [{
            "label": "half notehead",
            "on_line": "noteheadHalfOnLine",
            "in_space": "noteheadHalfInSpace",
            "click_box": True,
        }],
    }))

    img = np.full((900, 300), 255, dtype=np.uint8)
    for ly in YS:
        img[ly - 2 : ly + 3, 10:290] = 0
    img[613:618, 60:241] = 0  # rungs below at pitch 1.15x
    img[728:733, 60:241] = 0
    PIL_Image.fromarray(img).save(root / "cells" / "ledgers.png")
    PIL_Image.fromarray(
        np.full((900, 300), 255, dtype=np.uint8)
    ).save(root / "cells" / "blank.png")

    client = fastapi_testclient.TestClient(create_app(root))
    on_rung = client.get(
        "/api/cell/ledgers/snap", params={"x": 150, "y": 730, "slot": 0}
    ).json()
    assert on_rung["class"]["name"] == "noteheadHalfOnLine"
    assert on_rung["measured_rungs"]["below"] == 2
    assert on_rung["snapped_y"] == pytest.approx(730, abs=2)

    fallback = client.get(
        "/api/cell/blank/snap", params={"x": 150, "y": 730, "slot": 0}
    ).json()
    assert fallback["class"]["name"] == "noteheadHalfInSpace"  # old grid: 750 wins
    assert fallback["measured_rungs"] == {"above": 0, "below": 0}
