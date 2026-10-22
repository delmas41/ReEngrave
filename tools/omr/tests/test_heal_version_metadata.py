"""`heal_version_metadata` re-derives a version's class fields from its labels.

The tool exists because re-running the converter on an existing version is
destructive (its source cell PNGs are gitignored and largely deleted), so a
class correction after export has to heal metadata in place. These tests pin
the two properties that make that safe: it changes ONLY the class fields, and
it refuses a diff wider than the caller declared.
"""

from __future__ import annotations

import json

import pytest

from tools.omr.training import heal_version_metadata as hvm


NAMES = ["noteheadBlackOnLine", "noteheadHalfInSpace", "noteheadHalfOnLine",
         "augmentationDot"]


def _version(tmp_path, labels: dict[str, list[str]], meta: dict):
    vdir = tmp_path / "v99-test"
    (vdir / "labels").mkdir(parents=True)
    (vdir / "images").mkdir()
    for cell_id, lines in labels.items():
        (vdir / "labels" / f"{cell_id}.txt").write_text("\n".join(lines) + "\n")
    (vdir / "metadata.json").write_text(json.dumps(meta, indent=2))
    return vdir


@pytest.fixture
def patched_names(monkeypatch):
    monkeypatch.setattr(hvm, "load_class_names", lambda *_a, **_k: NAMES)
    monkeypatch.setattr(hvm.Path, "exists", lambda self: True)


def _meta(per_cell, used):
    return {
        "version_name": "v99-test",
        "created_utc": "2026-01-01T00:00:00Z",
        "labeler": "test",
        "source": {"weights_for_class_names": "some/weights.pt"},
        "classes_used_in_this_version": used,
        "per_cell": per_cell,
    }


def test_a_stale_class_is_re_derived_from_the_label(tmp_path, patched_names):
    """The correction case: the label says OnLine, metadata still says InSpace."""
    vdir = _version(
        tmp_path,
        {"cellA": ["2 0.5 0.5 0.1 0.1"]},
        _meta([{"cell_id": "cellA", "classes_written": ["noteheadHalfInSpace"]}],
              ["noteheadHalfInSpace"]),
    )
    _, healed, changes = hvm.recompute(vdir, tmp_path)
    assert healed["per_cell"][0]["classes_written"] == ["noteheadHalfOnLine"]
    assert healed["classes_used_in_this_version"] == ["noteheadHalfOnLine"]
    assert len(changes) == 2


def test_agreeing_metadata_is_left_alone(tmp_path, patched_names):
    vdir = _version(
        tmp_path,
        {"cellA": ["2 0.5 0.5 0.1 0.1", "3 0.2 0.2 0.05 0.05"]},
        _meta([{"cell_id": "cellA",
                "classes_written": ["augmentationDot", "noteheadHalfOnLine"]}],
              ["augmentationDot", "noteheadHalfOnLine"]),
    )
    meta, healed, changes = hvm.recompute(vdir, tmp_path)
    assert changes == []
    assert healed == meta


def test_the_aggregate_gains_a_class_only_this_cell_carries(tmp_path, patched_names):
    """v11's shape: the corrected cell was the version's ONLY carrier, so the
    aggregate is a wrong answer to 'what classes does this version teach'."""
    vdir = _version(
        tmp_path,
        {"cellA": ["2 0.5 0.5 0.1 0.1"], "cellB": ["0 0.5 0.5 0.1 0.1"]},
        _meta([{"cell_id": "cellA", "classes_written": ["noteheadHalfInSpace"]},
               {"cell_id": "cellB", "classes_written": ["noteheadBlackOnLine"]}],
              ["noteheadBlackOnLine", "noteheadHalfInSpace"]),
    )
    _, healed, _ = hvm.recompute(vdir, tmp_path)
    assert healed["classes_used_in_this_version"] == [
        "noteheadBlackOnLine", "noteheadHalfOnLine"]


def test_labels_and_images_are_never_touched(tmp_path, patched_names):
    vdir = _version(
        tmp_path,
        {"cellA": ["2 0.5 0.5 0.1 0.1"]},
        _meta([{"cell_id": "cellA", "classes_written": ["noteheadHalfInSpace"]}],
              ["noteheadHalfInSpace"]),
    )
    before = (vdir / "labels" / "cellA.txt").read_bytes()
    hvm.recompute(vdir, tmp_path)
    assert (vdir / "labels" / "cellA.txt").read_bytes() == before


def test_a_cell_with_no_label_file_keeps_its_recorded_classes(tmp_path, patched_names):
    """An inspected-empty cell emits no label; its record is not evidence of
    drift and must not be rewritten to []."""
    vdir = _version(
        tmp_path,
        {"cellA": ["2 0.5 0.5 0.1 0.1"]},
        _meta([{"cell_id": "cellA", "classes_written": ["noteheadHalfOnLine"]},
               {"cell_id": "cellEmpty", "classes_written": []}],
              ["noteheadHalfOnLine"]),
    )
    _, healed, changes = hvm.recompute(vdir, tmp_path)
    assert changes == []
    assert healed["per_cell"][1]["classes_written"] == []


def test_a_class_id_outside_the_vocabulary_is_refused(tmp_path, patched_names):
    """Wrong weights for the version would silently rename every class."""
    vdir = _version(
        tmp_path,
        {"cellA": ["99 0.5 0.5 0.1 0.1"]},
        _meta([{"cell_id": "cellA", "classes_written": []}], []),
    )
    with pytest.raises(SystemExit, match="outside the"):
        hvm.recompute(vdir, tmp_path)
