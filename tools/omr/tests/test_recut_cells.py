"""Tests for the cell re-cut repair tool.

The point of the tool is that it REFUSES more often than it writes, so most of
what is worth pinning is the refusing: a frame that disagrees with the
manifest, an id the cut does not produce, a PDF that is not on this machine.
None of it needs a PDF — the cut is injected.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.omr import measure_extractor as _me
from tools.omr.annotate import recut_cells as rc


class FakeCell:
    """Enough of a MeasureCell for the join, the frame check and the save."""

    def __init__(self, sys_i, staff_i, meas_i, w=2048, h=1185, ys=(507, 591, 675, 759, 847)):
        self.system_index = sys_i
        self.staff_index = staff_i
        self.measure_index = meas_i
        self.width = w
        self.height = h
        self.staff_line_ys_canonical = list(ys)
        self.image = object()
        self.image_no_staff = object()


def entry(cid="b-p2-sys0-s0-m1", sys_i=0, staff_i=0, meas_i=1,
          w=2048, h=1185, ys=(507, 591, 675, 759, 847), pdf="/mac/score.pdf", page=1):
    return {
        "cell_id": cid,
        "pdf": pdf,
        "page": page,
        "system_index": sys_i,
        "staff_index": staff_i,
        "measure_index": meas_i,
        "cell_canonical_w": w,
        "cell_canonical_h": h,
        "staff_line_ys_canonical": list(ys),
    }


# ---------------------------------------------------------------- the join

def test_entry_and_cell_join_on_the_position_triple():
    e = entry(sys_i=1, staff_i=13, meas_i=4)
    idx = rc.index_cells([FakeCell(1, 13, 4), FakeCell(0, 0, 0)])
    assert idx[rc.entry_key(e)].staff_index == 13


def test_a_cell_the_cut_does_not_produce_is_missing_not_matched():
    found = rc.assess([entry()], rc.index_cells([FakeCell(9, 9, 9)]))
    assert [e["cell_id"] for e in found.missing] == ["b-p2-sys0-s0-m1"]
    assert not found.matched
    assert not found.ok


# --------------------------------------------------------- the frame guard

def test_matching_frame_passes():
    assert rc.frame_mismatch(entry(), FakeCell(0, 0, 1)) is None


@pytest.mark.parametrize("kwargs,word", [
    ({"h": 1400}, "height"),
    ({"w": 1900}, "width"),
    ({"ys": (500, 590, 675, 759, 847)}, "staff lines"),
])
def test_a_different_frame_is_reported_not_tolerated(kwargs, word):
    why = rc.frame_mismatch(entry(), FakeCell(0, 0, 1, **kwargs))
    assert why is not None and word in why


def test_one_pixel_of_height_is_a_mismatch():
    # Not a tolerance: the boxes are in this frame, so "nearly" is wrong.
    assert rc.frame_mismatch(entry(), FakeCell(0, 0, 1, h=1186)) is not None


def test_a_wrong_frame_is_mismatched_rather_than_matched():
    found = rc.assess([entry()], rc.index_cells([FakeCell(0, 0, 1, h=1400)]))
    assert not found.matched
    assert len(found.mismatched) == 1
    assert not found.ok


def test_a_manifest_without_frame_fields_cannot_be_checked_and_passes():
    bare = {"cell_id": "x", "system_index": 0, "staff_index": 0, "measure_index": 0}
    assert rc.frame_mismatch(bare, FakeCell(0, 0, 0)) is None


# ------------------------------------------------------------ padding mode

def test_padding_mode_restores_the_globals_it_changed():
    before = (_me.PAD_ABOVE_STAFF_LINES, _me.PAD_BELOW_STAFF_LINES)
    with rc.padding_mode("orchestral"):
        assert _me.PAD_ABOVE_STAFF_LINES == rc.ORCH_PAD_STAFF_LINES
    assert (_me.PAD_ABOVE_STAFF_LINES, _me.PAD_BELOW_STAFF_LINES) == before


def test_padding_mode_restores_even_when_the_body_raises():
    before = (_me.PAD_ABOVE_STAFF_LINES, _me.PAD_BELOW_STAFF_LINES)
    with pytest.raises(RuntimeError):
        with rc.padding_mode("orchestral"):
            raise RuntimeError("cut failed")
    assert (_me.PAD_ABOVE_STAFF_LINES, _me.PAD_BELOW_STAFF_LINES) == before


def test_pipeline_mode_leaves_the_pipeline_values_alone():
    with rc.padding_mode("pipeline"):
        assert _me.PAD_ABOVE_STAFF_LINES != rc.ORCH_PAD_STAFF_LINES


def test_unknown_padding_mode_is_refused():
    with pytest.raises(ValueError):
        with rc.padding_mode("whatever"):
            pass


def test_the_mode_the_manifest_agrees_with_is_the_one_chosen(monkeypatch):
    entries = [entry()]
    cuts = {
        "pipeline": [FakeCell(0, 0, 1, h=1400)],   # wrong frame
        "orchestral": [FakeCell(0, 0, 1)],          # right frame
    }
    monkeypatch.setattr(rc, "cut_page", lambda p, pg, dpi, mode: cuts[mode])
    mode, found = rc.choose_mode_and_cut(
        Path("/x.pdf"), 1, entries, dpi=600, log=lambda *_: None
    )
    assert mode == "orchestral"
    assert found.ok


def test_when_no_mode_matches_the_best_attempt_is_reported(monkeypatch):
    entries = [entry()]
    monkeypatch.setattr(
        rc, "cut_page", lambda p, pg, dpi, mode: [FakeCell(0, 0, 1, h=1400)]
    )
    mode, found = rc.choose_mode_and_cut(
        Path("/x.pdf"), 1, entries, dpi=600, log=lambda *_: None
    )
    assert not found.ok
    assert len(found.mismatched) == 1


# ------------------------------------------------------------- pdf finding

def test_an_absolute_path_that_exists_is_used(tmp_path):
    pdf = tmp_path / "score.pdf"
    pdf.write_bytes(b"%PDF")
    assert rc.resolve_pdf(str(pdf), pdf_root=None, repo_root=tmp_path) == pdf


def test_another_machines_path_is_rerooted_on_the_library_tail(tmp_path):
    # The manifest records the Mac's absolute path; the library layout is what
    # the two machines share.
    here = tmp_path / "library" / "editions" / "brahms" / "s.pdf"
    here.parent.mkdir(parents=True)
    here.write_bytes(b"%PDF")
    raw = "/Users/someone/Desktop/ReEngrave/library/editions/brahms/s.pdf"
    assert rc.resolve_pdf(raw, pdf_root=None, repo_root=tmp_path) == here


def test_pdf_root_is_tried_before_the_repo_root(tmp_path):
    other = tmp_path / "other"
    (other / "library").mkdir(parents=True)
    pdf = other / "library" / "s.pdf"
    pdf.write_bytes(b"%PDF")
    raw = "/elsewhere/library/s.pdf"
    assert rc.resolve_pdf(raw, pdf_root=other, repo_root=tmp_path) == pdf


def test_a_pdf_that_is_nowhere_resolves_to_none(tmp_path):
    assert rc.resolve_pdf("/nope/library/s.pdf", pdf_root=None, repo_root=tmp_path) is None


# --------------------------------------------------------------- grouping

def test_pages_are_grouped_so_phase_1_runs_once_each():
    m = [entry(cid="a", page=1), entry(cid="b", page=1, staff_i=2), entry(cid="c", page=3)]
    groups = rc.group_sources(m)
    assert len(groups) == 2
    assert len(groups[("/mac/score.pdf", 1)]) == 2


# ------------------------------------------------------- the write refusal

def _bench(tmp_path, manifest):
    bench = tmp_path / "batch"
    (bench / "cells").mkdir(parents=True)
    (bench / "cells.json").write_text(json.dumps(manifest))
    return bench


def test_a_mismatched_frame_refuses_to_write_anything(tmp_path, monkeypatch):
    # Two cells, one of which comes back at the wrong frame: the GOOD one is
    # not written either. A half-repaired batch is worse than an unrepaired
    # one, because the blank canvas is at least an obvious symptom.
    manifest = [entry(cid="good"), entry(cid="bad", staff_i=1)]
    bench = _bench(tmp_path, manifest)
    monkeypatch.setattr(rc, "resolve_pdf", lambda *a, **k: Path("/x.pdf"))
    monkeypatch.setattr(rc, "cut_page", lambda p, pg, dpi, mode: [
        FakeCell(0, 0, 1), FakeCell(0, 1, 1, h=1400)
    ])
    saved: list = []
    monkeypatch.setattr(rc, "_save", lambda c, png, no_staff: saved.append(png) or True)

    report = rc.recut(bench, repo_root=tmp_path, log=lambda *_: None)

    assert saved == []
    assert report.written == []
    assert not report.clean
    assert [cid for cid, _ in report.mismatched] == ["bad"]


def test_allow_partial_writes_the_verified_cells_only(tmp_path, monkeypatch):
    manifest = [entry(cid="good"), entry(cid="bad", staff_i=1)]
    bench = _bench(tmp_path, manifest)
    monkeypatch.setattr(rc, "resolve_pdf", lambda *a, **k: Path("/x.pdf"))
    monkeypatch.setattr(rc, "cut_page", lambda p, pg, dpi, mode: [
        FakeCell(0, 0, 1), FakeCell(0, 1, 1, h=1400)
    ])
    monkeypatch.setattr(rc, "_save", lambda c, png, no_staff: True)

    report = rc.recut(bench, repo_root=tmp_path, allow_partial=True, log=lambda *_: None)

    assert report.written == ["good"]
    assert [cid for cid, _ in report.mismatched] == ["bad"]


def test_a_clean_recut_writes_every_cell(tmp_path, monkeypatch):
    manifest = [entry(cid="a"), entry(cid="b", staff_i=1)]
    bench = _bench(tmp_path, manifest)
    monkeypatch.setattr(rc, "resolve_pdf", lambda *a, **k: Path("/x.pdf"))
    monkeypatch.setattr(rc, "cut_page", lambda p, pg, dpi, mode: [
        FakeCell(0, 0, 1), FakeCell(0, 1, 1)
    ])
    monkeypatch.setattr(rc, "_save", lambda c, png, no_staff: True)

    report = rc.recut(bench, repo_root=tmp_path, log=lambda *_: None)

    assert sorted(report.written) == ["a", "b"]
    assert report.clean


def test_an_existing_png_is_left_alone_unless_overwrite(tmp_path, monkeypatch):
    manifest = [entry(cid="a")]
    bench = _bench(tmp_path, manifest)
    (bench / "cells" / "a.png").write_bytes(b"already here")
    monkeypatch.setattr(rc, "resolve_pdf", lambda *a, **k: Path("/x.pdf"))
    monkeypatch.setattr(rc, "cut_page", lambda p, pg, dpi, mode: [FakeCell(0, 0, 1)])
    monkeypatch.setattr(rc, "_save", lambda c, png, no_staff: True)

    report = rc.recut(bench, repo_root=tmp_path, log=lambda *_: None)
    assert report.skipped_existing == ["a"] and report.written == []

    report = rc.recut(bench, repo_root=tmp_path, overwrite=True, log=lambda *_: None)
    assert report.written == ["a"]


def test_a_dry_run_writes_nothing(tmp_path, monkeypatch):
    manifest = [entry(cid="a")]
    bench = _bench(tmp_path, manifest)
    monkeypatch.setattr(rc, "resolve_pdf", lambda *a, **k: Path("/x.pdf"))
    monkeypatch.setattr(rc, "cut_page", lambda p, pg, dpi, mode: [FakeCell(0, 0, 1)])
    saved: list = []
    monkeypatch.setattr(rc, "_save", lambda c, png, no_staff: saved.append(png) or True)

    report = rc.recut(bench, repo_root=tmp_path, dry_run=True, log=lambda *_: None)

    assert saved == []
    assert report.written == ["a"]          # what it WOULD write
    assert not (bench / "cells" / "a.png").exists()


def test_an_unfindable_pdf_is_reported_and_nothing_is_written(tmp_path, monkeypatch):
    manifest = [entry(cid="a")]
    bench = _bench(tmp_path, manifest)
    monkeypatch.setattr(rc, "resolve_pdf", lambda *a, **k: None)
    saved: list = []
    monkeypatch.setattr(rc, "_save", lambda c, png, no_staff: saved.append(png) or True)

    report = rc.recut(bench, repo_root=tmp_path, log=lambda *_: None)

    assert saved == []
    assert report.unresolved_pdfs and not report.clean
    # The cells are accounted to the unfound file, not re-reported one by one
    # as cells the cut failed to produce — that is a different fault with a
    # different fix, and 56 of them would bury the line that names the file.
    assert report.missing == []
    assert report.unreachable == 1


def test_one_missing_pdf_is_reported_once_however_many_pages_use_it(tmp_path, monkeypatch):
    manifest = [entry(cid="a", page=1), entry(cid="b", page=2), entry(cid="c", page=3)]
    bench = _bench(tmp_path, manifest)
    monkeypatch.setattr(rc, "resolve_pdf", lambda *a, **k: None)

    report = rc.recut(bench, repo_root=tmp_path, log=lambda *_: None)

    assert report.unresolved_pdfs == ["/mac/score.pdf"]
    assert report.unreachable == 3


def test_the_batchs_own_files_are_never_touched(tmp_path, monkeypatch):
    # The whole reason this tool exists rather than re-running the cutter.
    manifest = [entry(cid="a")]
    bench = _bench(tmp_path, manifest)
    for name in ("verdicts", "detections", "prefill"):
        (bench / name).mkdir()
        (bench / name / "keep.json").write_text('{"human": "work"}')
    before = (bench / "cells.json").read_text()

    monkeypatch.setattr(rc, "resolve_pdf", lambda *a, **k: Path("/x.pdf"))
    monkeypatch.setattr(rc, "cut_page", lambda p, pg, dpi, mode: [FakeCell(0, 0, 1)])
    monkeypatch.setattr(rc, "_save", lambda c, png, no_staff: True)

    rc.recut(bench, repo_root=tmp_path, log=lambda *_: None)

    assert (bench / "cells.json").read_text() == before
    for name in ("verdicts", "detections", "prefill"):
        assert (bench / name / "keep.json").read_text() == '{"human": "work"}'
