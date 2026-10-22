"""ROADMAP 1.7: the page-truth store — page pixels, one box per mark, pre-fills are a queue."""
from __future__ import annotations

import json

import numpy as np
import pytest

from tools.omr.hand_truth import completeness, export_yolo
from tools.omr.hand_truth.store import (
    ALL_INK, Cell, PageTruth, StaffCheck, StoreError, edition_key, load,
)


def _page(**kw) -> PageTruth:
    p = PageTruth(edition="imslp317803", pdf_page_index=5, dpi=600, width=400, height=200, **kw)
    # Two OVERLAPPING measure cells, as padded cells are on a real page: A spans
    # x 0..200, B spans x 150..350. Canonical frames at half and full scale.
    p.add_cell(Cell(id="A", kind="measure", rect=(0, 0, 200, 100), canonical_w=400, canonical_h=200))
    p.add_cell(Cell(id="B", kind="measure", rect=(150, 0, 350, 100), canonical_w=200, canonical_h=100))
    return p


# ------------------------------------------------------------------ geometry
def test_cell_box_is_stored_in_page_pixels_and_maps_back_exactly():
    p = _page()
    b = p.draw("A", "noteheadBlackOnLine", (40, 20, 60, 40))  # canonical frame of A (x0.5)
    assert b.rect == (20.0, 10.0, 30.0, 20.0)
    assert p.cell("A").to_cell(b.rect) == (40.0, 20.0, 60.0, 40.0)


def test_a_mark_in_the_overlap_is_one_box_seen_from_both_cells():
    p = _page()
    b = p.draw("A", "restQuarter", (340, 20, 360, 60))  # page x 170..180 — inside A AND B
    in_b = p.boxes_in_cell("B")
    assert [x[0].id for x in in_b] == [b.id]
    box, rect_in_b, clipped = in_b[0]
    assert rect_in_b == (20.0, 10.0, 30.0, 30.0) and clipped is False
    assert len(p.boxes) == 1


def test_a_box_across_the_cell_edge_is_reported_clipped():
    p = _page()
    p.draw("A", "slur", (200, 20, 398, 40))  # page x 100..199; B starts at page x 150
    (box, r, clipped), = p.boxes_in_cell("B")
    assert clipped is True
    assert r == (0.0, 10.0, 49.0, 20.0)  # cut at B's left edge, in B's frame


# ------------------------------------------------------------------ truth = human acts
def test_a_prefill_is_not_truth_until_sean_acts_on_it():
    p = _page()
    q = p.propose("noteheadBlackInSpace", (10, 10, 20, 20), source="production", score=0.6)
    assert p.boxes == [] and [x.id for x in p.queue] == [q.id]
    b = p.confirm_prefill(q.id, "A")
    assert b.origin == "prefill-confirmed" and p.queue == []
    q2 = p.propose("accidentalDoubleSharp", (30, 30, 40, 40), source="production")
    fixed = p.fix_prefill(q2.id, "A", cls="accidentalSharp")
    assert fixed.origin == "prefill-fixed" and fixed.cls == "accidentalSharp"
    q3 = p.propose("restWhole", (50, 50, 60, 55), source="production")
    p.reject_prefill(q3.id)
    assert [b.origin for b in p.boxes] == ["prefill-confirmed", "prefill-fixed"] and p.queue == []


def test_claude_cannot_write_truth():
    # Claude's double-check only FLAGS (plan C5, rule 7); a box labeled by
    # anyone but Sean is refused at the store.
    with pytest.raises(StoreError):
        _page().draw("A", "noteheadBlackOnLine", (1, 1, 5, 5), labeler="claude")


def test_a_text_box_must_carry_its_text():
    with pytest.raises(StoreError):
        _page().draw("A", "text", (1, 1, 5, 5))


def test_states_advance_one_step_at_a_time():
    p = _page()
    with pytest.raises(StoreError):
        p.advance("verified")
    p.advance("checked")
    p.advance("verified")
    with pytest.raises(StoreError):
        p.advance("labeling")


def test_save_and_load_round_trip(tmp_path):
    p = _page()
    p.draw("A", "text", (0, 0, 80, 20), text="Flauti")
    p.mark_inspected("A", [ALL_INK])
    p.staves.append(StaffCheck(system=0, staff=0, lines_right=True))
    path = p.save(tmp_path)
    assert path == tmp_path / "imslp317803" / "5.json"
    assert load(path).to_json() == p.to_json()
    assert json.loads(path.read_text())["boxes"][0]["rect"] == [0.0, 0.0, 40.0, 10.0]


def test_edition_key_meets_the_manifest_pdf_names():
    assert edition_key("IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7") == "imslp984073"
    assert edition_key("brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803") == "imslp317803"
    assert edition_key("Mahler_5_") == "mahler_5_"


# ------------------------------------------------------------------ completeness
def test_a_family_is_complete_only_when_every_cell_was_inspected_for_it():
    p = _page()
    p.mark_inspected("A", [ALL_INK])
    p.mark_inspected("B", ["rest"])
    st = completeness.family_status(p, ["rest", "notehead"])
    assert st["rest"]["complete"] is True
    assert st["notehead"]["complete"] is False and st["notehead"]["cells_missing"] == ["B"]
    p.mark_inspected("B", [ALL_INK])  # the control: now it must pass
    assert completeness.family_status(p, ["notehead"])["notehead"]["complete"] is True


def test_an_old_partial_pass_completes_no_family():
    p = _page()
    for c in ("A", "B"):
        p.mark_inspected(c, ["hollow noteheads", "rests+accidentals"])
    st = completeness.family_status(p, ["notehead", "rest", "accidental"])
    assert st["notehead"]["complete"] is False  # the black heads were never swept
    assert st["rest"]["complete"] is True and st["accidental"]["complete"] is True


def test_family_of_never_drops_a_class():
    assert completeness.family_of("noteheadHalfInSpace") == "notehead"
    assert completeness.family_of("ledgerLine") == "ledger_line"
    assert completeness.family_of("stem") == "stem"
    assert completeness.family_of("fingering1") == "class:fingering1"


def _ink_page():
    p = PageTruth(edition="e", pdf_page_index=0, dpi=600, width=60, height=40)
    p.add_cell(Cell(id="A", kind="measure", rect=(0, 0, 60, 40), canonical_w=60, canonical_h=40))
    ink = np.zeros((40, 60), bool)
    ink[5:10, 5:10] = True     # blob 1
    ink[5:10, 25:30] = True    # blob 2
    ink[5:10, 45:50] = True    # blob 3
    ink[30, 2] = True          # a speck
    return p, ink


def test_ink_coverage_lists_the_mark_nobody_boxed():
    p, ink = _ink_page()
    p.draw("A", "noteheadBlackInSpace", (4, 4, 11, 11))
    p.draw("A", "noise", (24, 4, 31, 11))
    rep = completeness.ink_coverage(p, ink)
    assert (rep.components, rep.covered, rep.specks_below_min_area) == (4, 2, 1)
    assert [u["rect"] for u in rep.uncovered] == [(45, 5, 50, 10)]
    p.draw("A", "restQuarter", (44, 4, 51, 11))  # the control: box it and it clears
    assert completeness.ink_coverage(p, ink).clean


def test_staff_lines_are_removed_before_components_are_counted():
    p, ink = _ink_page()
    ink[7, :] = True  # a staff line through all three blobs joins them into one component
    staff = np.zeros_like(ink)
    staff[7, :] = True
    assert completeness.ink_coverage(p, ink).components == 2  # the line + the speck
    assert completeness.ink_coverage(p, ink, staff).components >= 4


def test_a_page_is_not_complete_when_the_ink_control_was_not_run():
    p, ink = _ink_page()
    p.mark_inspected("A", [ALL_INK])
    p.staves.append(StaffCheck(system=0, staff=0, lines_right=True))
    p.draw("A", "noise", (0, 0, 60, 40))
    assert completeness.page_complete(p)["complete"] is False
    assert completeness.page_complete(p, completeness.ink_coverage(p, ink))["complete"] is True


# ------------------------------------------------------------------ export to training
def test_a_held_out_page_never_trains(tmp_path):
    p = _page()
    p.advance("checked")
    with pytest.raises(StoreError, match="HELD OUT"):
        export_yolo.export_page(p, None, tmp_path, held_out={("imslp317803", 5)})


def test_a_page_still_being_labeled_never_trains(tmp_path):
    with pytest.raises(StoreError, match="still being labeled"):
        export_yolo.export_page(_page(), None, tmp_path, held_out=set())


def test_only_whole_ink_cells_train_and_lines_use_the_catalog_vocabulary(tmp_path):
    p = _page()
    b = p.draw("B", "noteheadBlackOnLine", (50, 25, 60, 35))  # canonical of B (x1)
    p.draw("B", "noise", (0, 0, 5, 5))
    p.mark_inspected("B", [ALL_INK])          # A stays partly swept: it must NOT train
    p.mark_inspected("A", ["rest"])
    p.advance("checked")
    idx = export_yolo.class_index()
    s = export_yolo.export_page(p, np.zeros((200, 400), np.uint8), tmp_path, held_out=set(), index=idx)
    assert s["cells_written"] == 1 and s["cells_skipped_not_whole_ink"] == ["A"]
    assert s["boxes_not_written"] == {"not_a_detector_class:noise": 1}
    line = (tmp_path / "labels" / "imslp317803-p5-B.txt").read_text().split()
    assert int(line[0]) == idx["noteheadBlackOnLine"]
    assert [float(v) for v in line[1:]] == pytest.approx([55 / 200, 30 / 100, 10 / 200, 10 / 100])
    assert b.rect == (200.0, 25.0, 210.0, 35.0)
    import cv2
    assert cv2.imread(str(tmp_path / "images" / "imslp317803-p5-B.png")).shape[:2] == (100, 200)


def test_the_committed_held_out_list_holds_the_first_and_count_pages():
    held = export_yolo.held_out_pages()
    assert {("imslp317803", 0), ("imslp317803", 1), ("imslp984073", 2), ("imslp984073", 3),
            ("imslp405834", 4)} <= held
    assert ("imslp984073", 1) not in held  # production trained on part of it: no longer a test page
