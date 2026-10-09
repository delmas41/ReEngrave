"""ROADMAP 1.7: the generated hand-label inventory and the weights lineage, on the real tree."""
from __future__ import annotations

import pytest

from tools.omr.hand_truth import inventory


@pytest.fixture(scope="module")
def inv():
    return inventory.build()


def test_the_inventory_is_deterministic(inv):
    assert inventory.render(inv) == inventory.render(inventory.build())


def test_every_label_version_on_disk_has_a_declared_tier(inv):
    undeclared = [v["version"] for v in inv["label_versions"] if v["tier"] == "undeclared"]
    assert undeclared == [], f"declare a tier in inventory.TIERS for {undeclared}"


def test_v22_is_the_one_drawn_from_scratch_over_a_recorded_palette(inv):
    v22 = next(v for v in inv["label_versions"] if v["version"].startswith("v22-"))
    assert v22["tier"] == "1-drawn-palette-recorded"
    # 109 of 110 carry the stamp: dvorak9-p19-sys0-s0-m0 holds 7 drawn boxes
    # but saved an EMPTY inspected_passes, so nothing proves it was swept.
    assert (v22["inspected_passes"]["draw-rich"], v22["cells"]) == (109, 110)


def test_the_final_fine_tune_was_almost_half_teacher_boxes(inv):
    (d25,) = inv["weights_lineage"]["round5-sweep/distill25/epoch0.pt"]["corpora"]
    assert (d25["boxes_from_label_files"], d25["boxes_added_by_teacher_model"]) == (3871, 3417)


def test_the_leak_check_finds_trained_pages_and_only_those(inv):
    prod = inv["production_scan_weights"]
    seen = inventory.pages_seen(inv["weights_lineage"], prod)
    assert ("imslp317803", 1) in seen        # v18's 19 Brahms count-page cells
    assert ("imslp317803", 0) not in seen    # the control: no label was ever drawn there
    assert "imslp317803:1" in inv["held_out_pages_seen_by_production"]
    assert "imslp317803:0" not in inv["held_out_pages_seen_by_production"]


def test_the_clean_test_pages_are_clean_and_the_count_pages_name_their_trained_cells(inv):
    seen = set(inv["held_out_pages_seen_by_production"])
    for clean in ("imslp317803:0", "imslp984073:2", "imslp405834:4"):
        assert clean not in seen
    trained = inv["held_out_cells_trained_by_production"]
    assert set(trained) == seen == {"imslp317803:1", "imslp984073:3"}
    assert len(trained["imslp317803:1"]) == 19 and len(trained["imslp984073:3"]) == 7
    assert all(c.startswith("s") and "-st" in c and "-m" in c for v in trained.values() for c in v)


def test_who_judged_comes_from_the_file_never_a_guess(inv):
    by_file = {a["file"]: a["labeler"] for a in inv["adjudications"]}
    assert by_file["benchmarks/omr-stem-crop-pass-2026-09/ADJUDICATION-litolff.json"] == "claude"
    assert by_file["benchmarks/omr-accidental-2026-09/out/print/ADJUDICATION-sean-2026-09-27.json"] == "sean"
    assert by_file["benchmarks/omr-label-contradiction-2026-09/out/adjudication.json"] == "unrecorded"


def test_a_prefilled_queue_is_not_counted_as_human_work(inv):
    sets = {s["dir"]: s for s in inv["verdict_sets"]}
    acc = sets["benchmarks/omr-queue-accidentals-2026-09/verdicts"]
    assert acc["cells_with_human_action"] == 0 and acc["cells"] == 155
    rests = sets["benchmarks/omr-queue-rests-2026-09/verdicts"]
    assert rests["cells_with_human_action"] > 0  # the positive control in the same class
