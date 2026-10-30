"""Hand truth aligned to the master cell map (hand_truth/align.py): the derived file, its --check, and the control.

A synthetic page (two five-line staves, one system, three bars) stands in for the score, exactly as test_cell_map.py does;
the hand-truth page is written from the master's own cells, then edited so each reason an old cell id can disagree with
the master appears once.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.omr.hand_truth import align as AL
from tools.omr.staged import cell_map as CM
from tools.omr.tests.test_cell_map import BARS, plate  # noqa: F401  (the synthetic-page fixture)


def _master_rows(mdir, page):
    return AL._master_cells(mdir, page)[1]


def _label_page(rows, page=3, pdf="plate.score", dpi=600):
    """A hand-truth page whose measure cells are the master's, plus a margin cell, with one box per interesting place."""
    cells = []
    for r in rows:
        cells.append({"id": r["id"], "kind": "measure", "rect": list(r["rect"]), "system": r["system"],
                      "staff": r["page_staff"], "measure": r["cell"], "staff_line_ys": list(r["line_ys"]),
                      "canonical_w": 100, "canonical_h": 100, "inspected": []})
    cells.append({"id": "margin-0", "kind": "margin", "rect": [0, 0, 90, 900], "system": None, "staff": None,
                  "measure": None, "staff_line_ys": None, "canonical_w": 90, "canonical_h": 900, "inspected": []})
    boxes = []

    def add(bid, rect, cell):
        boxes.append({"id": bid, "cls": "noteheadBlackInSpace", "rect": list(rect), "cell_id": cell,
                      "origin": "drawn", "labeler": "sean"})

    a = next(r for r in rows if r["staff"] == 0 and r["cell"] == 1)
    b = next(r for r in rows if r["staff"] == 1 and r["cell"] == 1)
    cx = (a["rect"][0] + a["rect"][2]) / 2
    add("inside", (cx - 5, a["middle"] - 5, cx + 5, a["middle"] + 5), a["id"])                   # agrees
    add("through-margin", (cx - 5, a["middle"] - 5, cx + 5, a["middle"] + 5), "margin-0")        # label-only cell
    add("outside-every-bar", (10, 10, 30, 30), "margin-0")                                       # master has no cell
    add("crosses-staves", (cx - 5, b["middle"] - 5, cx + 5, b["middle"] + 5), a["id"])           # spans-cells
    return {"edition": "synthetic", "pdf_page_index": page, "dpi": dpi, "cells": cells, "boxes": boxes,
            "provenance": {"pdf": pdf}, "staves": [], "flags": [], "queue": [], "state": "labeling",
            "schema_version": 1, "width": 1300, "height": 900}


@pytest.fixture
def world(plate, tmp_path):  # noqa: F811
    src, root, state = plate
    CM.build(src, [3], root=root)
    mdir = AL.find_master(root, "plate.score", 3)
    assert mdir is not None
    pages = tmp_path / "pages" / "synthetic"
    pages.mkdir(parents=True)
    page = _label_page(_master_rows(mdir, 3))
    (pages / "3.json").write_text(json.dumps(page))
    return dict(src=src, root=root, mdir=mdir, pages_dir=tmp_path / "pages", aligned=tmp_path / "aligned",
                page_path=pages / "3.json", page=page, tmp=tmp_path)


def test_a_master_is_found_by_pdf_name_and_page(world):
    assert AL.find_master(world["root"], "plate.score", 3) == world["mdir"]
    assert AL.find_master(world["root"], "plate.score", 9) is None
    assert AL.find_master(world["root"], "another.score", 3) is None


def test_labels_cut_by_the_same_tree_agree_in_frame(world):
    al = AL.build_alignment(world["page_path"], world["mdir"])
    m = al["frame"]["measure_cells"]
    assert m["labels"] == m["master"] == m["same"] > 0
    assert not (m["rect_changed"] or m["only_in_labels"] or m["only_in_master"])
    assert al["frame"]["cell_x_edges_differing_by_system"] == {}
    assert AL.Alignment(al).frame_agrees()


def test_each_reason_an_old_cell_id_disagrees_appears_once_and_agreement_is_not_hidden(world):
    al = AL.build_alignment(world["page_path"], world["mdir"])
    b = al["boxes"]
    assert b["inside"]["ok"] and b["inside"]["master_id"] == b["inside"]["old"] and "why" not in b["inside"]
    assert not b["through-margin"]["ok"] and b["through-margin"]["why"] == "label-only-cell"
    assert b["through-margin"]["master"] is not None            # the ink lies in a measure cell
    assert b["outside-every-bar"]["why"] == "label-only-cell" and b["outside-every-bar"]["master"] is None
    assert b["crosses-staves"]["why"] == "spans-cells" and b["crosses-staves"]["staff"] == 1
    s = al["summary"]
    assert s["boxes"] == 4 and s["agree"] == 1 and s["disagree"] == 3
    assert s["boxes_with_no_master_cell"] == 1


def test_the_master_cell_comes_from_the_rect_not_the_old_id(world):
    page = json.loads(world["page_path"].read_text())
    for bx in page["boxes"]:
        bx["cell_id"] = "s0-st9-m9"                              # an id no cell has
    world["page_path"].write_text(json.dumps(page))
    al = AL.build_alignment(world["page_path"], world["mdir"])
    assert al["boxes"]["inside"]["master"] == "cell/3/0/0/1" and al["boxes"]["inside"]["why"] == "old-cell-not-on-page"


def test_a_barline_the_master_has_elsewhere_makes_frame_changed(world, plate):  # noqa: F811
    """Labels cut with the barline at BARS[1]; a master cut with it elsewhere: the cells differ and the boxes between move."""
    src, root, state = plate
    other_root = world["tmp"] / "maps2"
    state["bars"] = (BARS[0], BARS[1] + 60)
    CM.build(src, [3], root=other_root)
    mdir2 = AL.find_master(other_root, "plate.score", 3)
    rows = _master_rows(world["mdir"], 3)
    page = _label_page(rows)
    # a box in the strip the barline moved across, labelled through the cell that then held it
    strip_x = BARS[1] + 30
    old_cell = next(r for r in rows if r["staff"] == 0 and r["rect"][0] <= strip_x < r["rect"][2])
    page["boxes"].append({"id": "strip", "cls": "stem", "rect": [strip_x - 3, old_cell["middle"] - 5, strip_x + 3,
                                                                 old_cell["middle"] + 5], "cell_id": old_cell["id"],
                          "origin": "drawn", "labeler": "sean"})
    world["page_path"].write_text(json.dumps(page))
    al = AL.build_alignment(world["page_path"], mdir2)
    assert al["frame"]["measure_cells"]["rect_changed"], "the cell edges moved"
    assert al["frame"]["cell_x_edges_differing_by_system"]
    assert not AL.Alignment(al).frame_agrees()
    row = al["boxes"]["strip"]
    assert not row["ok"] and row["why"] == "frame-changed" and row["label_old_cell_rect"] != row["master_old_cell_rect"]


def test_write_then_check_passes_and_is_byte_identical(world):
    kw = dict(pages_dir=world["pages_dir"], aligned_dir=world["aligned"], root=world["root"])
    (dest,) = AL.write_all(**kw)
    first = dest.read_text()
    ok, msgs, _ = AL.check(**kw)
    assert ok, msgs
    AL.write_all(**kw)
    assert dest.read_text() == first
    al = AL.Alignment.load("synthetic", 3, world["aligned"])
    assert al.cell_of("inside") == "cell/3/0/0/1" and al.key_of_label_cell(world["page"]["cells"][0]["id"]) is not None
    assert al.key_of_label_cell("margin-0") is None


def test_check_fails_when_the_aligned_file_is_missing_or_edited(world):
    kw = dict(pages_dir=world["pages_dir"], aligned_dir=world["aligned"], root=world["root"])
    ok, msgs, _ = AL.check(**kw)
    assert not ok and "no aligned file" in msgs[0]
    (dest,) = AL.write_all(**kw)
    d = json.loads(dest.read_text())
    d["boxes"]["inside"]["master"] = "cell/3/0/1/1"                # someone hand-edits the derived file
    dest.write_text(AL.dumps(d))
    ok, msgs, moved = AL.check(**kw)
    assert not ok and "STALE" in msgs[0] and any(r.startswith("box inside") for r in moved["synthetic:3"])


def test_check_fails_when_a_label_is_edited(world):
    kw = dict(pages_dir=world["pages_dir"], aligned_dir=world["aligned"], root=world["root"])
    AL.write_all(**kw)
    page = json.loads(world["page_path"].read_text())
    page["boxes"][0]["rect"][0] += 40                             # Sean drags a box in the labeling tool
    world["page_path"].write_text(json.dumps(page))
    ok, msgs, _ = AL.check(**kw)
    assert not ok
    al = AL.Alignment.load("synthetic", 3, world["aligned"])
    assert "labels changed" in al.stale_against(world["page_path"])


def test_check_without_a_master_still_catches_edited_labels(world):
    kw = dict(pages_dir=world["pages_dir"], aligned_dir=world["aligned"])
    AL.write_all(root=world["root"], **kw)
    empty = world["tmp"] / "no-maps"
    empty.mkdir()
    ok, msgs, _ = AL.check(root=empty, **kw)
    assert ok and "no master cell map" in msgs[0]                  # nothing to align to: reported, not failed
    page = json.loads(world["page_path"].read_text())
    page["boxes"][1]["rect"][1] += 25
    world["page_path"].write_text(json.dumps(page))
    ok, msgs, _ = AL.check(root=empty, **kw)
    assert not ok and any("STALE" in m for m in msgs)


def test_control_moving_one_master_barline_fails_the_check_and_names_the_boxes(world):
    """The control that can fail: a master with one barline moved is a different master, and the boxes beside it change cell."""
    kw = dict(pages_dir=world["pages_dir"], aligned_dir=world["aligned"])
    AL.write_all(root=world["root"], **kw)
    page = json.loads(world["page_path"].read_text())
    strip_x = BARS[1] + 30                                        # just right of the inner barline
    cell = next(r for r in _master_rows(world["mdir"], 3) if r["staff"] == 0 and r["rect"][0] <= strip_x < r["rect"][2])
    page["boxes"].append({"id": "strip", "cls": "stem", "rect": [strip_x - 3, cell["middle"] - 5, strip_x + 3, cell["middle"] + 5],
                          "cell_id": cell["id"], "origin": "drawn", "labeler": "sean"})
    world["page_path"].write_text(json.dumps(page))
    AL.write_all(root=world["root"], **kw)
    assert AL.check(root=world["root"], **kw)[0], "green before the perturbation"
    inner = sorted({r["rect"][0] for r in _master_rows(world["mdir"], 3)})
    xv = int(next(v for v in inner if v > BARS[0] + 50))
    pdir, x = AL.perturb_barline(world["mdir"], world["tmp"] / "moved", 3, x=xv, dx=int(strip_x - xv) + 40)
    ok, msgs, moved = AL.check(root=pdir.parent, **kw)
    assert not ok, "a check that stays green on a moved barline cannot fail"
    assert any("different master cell" in m for m in msgs)
    assert any(r.startswith("box strip") for r in moved["synthetic:3"])
    rows = _master_rows(pdir, 3)
    assert any(abs(r["rect"][0] - xv) < 1 for r in _master_rows(world["mdir"], 3))
    assert not any(abs(r["rect"][0] - xv) < 1 for r in rows), "the barline really moved in every cell that spelled it"
    # the original master is untouched
    assert AL.check(root=world["root"], **kw)[0]


def test_the_control_command_passes_on_a_synthetic_world(world, capsys):
    ok, lines = AL.control(pages_dir=world["pages_dir"], aligned_dir=world["aligned"], root=world["root"], dx=80)
    assert ok, lines
    assert any("FAILED (as it must)" in ln for ln in lines)


def test_score_frame_control_keys_cells_by_the_master_cell(world):
    """`frame_control` looks a truth cell up under the MASTER cell key when it is handed an alignment."""
    from tools.omr.hand_truth import score as S
    from tools.omr.hand_truth import store

    page = store.load(world["page_path"])
    al = AL.Alignment(AL.build_alignment(world["page_path"], world["mdir"]))
    rows = _master_rows(world["mdir"], 3)
    # the record's cell boxes under the MASTER's keys; the label's own keys are (system, page-wide staff, cell)
    rec = {(r["system"], r["staff"], r["cell"]): tuple(r["rect"]) for r in rows}
    fv = S.frame_control(page, 600, rec, {}, [], [], aligned=al)
    assert fv.detail["cells"]["compared"] == len(rows) and fv.detail["cells"]["max_abs_diff_px"] == 0
    assert fv.detail["master_cell_map"]["master"] == al.version
    # a record whose cell boxes sit one pixel-block away from the master's: the cells part of the control fails
    shifted = {k: (v[0] + 9, v[1], v[2] + 9, v[3]) for k, v in rec.items()}
    fv2 = S.frame_control(page, 600, shifted, {}, [], [], aligned=al)
    assert any(r.startswith("cells: rectangles differ") for r in fv2.reasons)
