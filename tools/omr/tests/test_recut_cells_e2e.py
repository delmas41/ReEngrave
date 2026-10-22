"""End-to-end: a real cut, thrown away, and re-cut from the manifest alone.

The unit tests inject the cut, so they pin the tool's decisions but say
nothing about whether a re-cut actually REPRODUCES a batch. That is the whole
claim, and it needs real phase 1 on a real page: render, detect staves, find
barlines, extract and canonicalize cells. The page is synthesized here rather
than taken from the score library, which is machine-local and gitignored — so
this runs anywhere the pipeline's own dependencies are installed.

⚠️ The staves are deliberately ~5 staff spaces apart. `measure_extractor`
GROWS the pad where the neighbouring staff is further than 6 spaces away
(CLAUDE.md, "the cell pad is 4 spaces or 6, never in between"), so on a sparse
page the two padding modes produce the SAME frame and a fixture built that way
cannot tell them apart — the first draft of this file had staves 33 spaces
apart and both modes returned h=1209. Crowding them is what makes the padding
mode observable, and therefore what makes the mode-detection testable at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("skimage", reason="pipeline needs scikit-image")
pytest.importorskip("pymupdf", reason="fixture needs PyMuPDF to draw a page")

from tools.omr.annotate import recut_cells as rc  # noqa: E402


DPI = 300


def _draw_page(path: Path) -> None:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)

    def staff(y0: float) -> None:
        for i in range(5):
            y = y0 + i * 6
            page.draw_line(pymupdf.Point(60, y), pymupdf.Point(550, y), width=0.6)
        for bx in (60, 220, 380, 550):
            page.draw_line(pymupdf.Point(bx, y0), pymupdf.Point(bx, y0 + 24), width=0.9)
        for nx in (120, 180, 280, 340, 440):
            page.draw_circle(pymupdf.Point(nx, y0 + 12), 2.6, fill=(0, 0, 0))

    for y in (200, 254, 308, 362):   # ~5 staff spaces apart — see the module note
        staff(y)
    doc.save(str(path))
    doc.close()


@pytest.fixture(scope="module")
def page_pdf(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("synth") / "page.pdf"
    _draw_page(p)
    return p


def _build_batch(bench: Path, pdf: Path, mode: str, cells=None) -> list[dict]:
    """Cut the page and record it the way the real cutters record a batch.

    Pass `cells` to record an already-made cut instead — the localization
    tests use it to build a batch exactly as a pre-flag cutter did, without
    `cut_page`'s own localization posture in the way.
    """
    from tools.omr.annotate.select_cells_orchestral import _save_cell_png

    cells_dir = bench / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    if cells is None:
        cells = rc.cut_page(pdf, 0, dpi=DPI, mode=mode)
    for c in cells:
        cid = f"synth-p1-sys{c.system_index}-s{c.staff_index}-m{c.measure_index}"
        _save_cell_png(c, cells_dir / f"{cid}.png", no_staff=False)
        # The real cutters save the staff-line-removed variant beside it, and
        # so does the re-cut; a fixture that skips it reports 12 spurious
        # extra files rather than the difference it is looking for.
        if c.image_no_staff is not None:
            _save_cell_png(c, cells_dir / f"{cid}_nostaff.png", no_staff=True)
        manifest.append({
            "cell_id": cid,
            "pdf": str(pdf),
            "page": 0,
            "system_index": c.system_index,
            "staff_index": c.staff_index,
            "measure_index": c.measure_index,
            "cell_canonical_w": c.width,
            "cell_canonical_h": c.height,
            "staff_line_ys_canonical": list(c.staff_line_ys_canonical),
        })
    (bench / "cells.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def _png_bytes(bench: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted((bench / "cells").glob("*.png"))}


@pytest.mark.parametrize("mode", ["pipeline", "orchestral"])
def test_a_deleted_batch_is_recut_byte_identically(tmp_path, page_pdf, mode):
    bench = tmp_path / f"batch-{mode}"
    manifest = _build_batch(bench, page_pdf, mode)
    assert len(manifest) >= 8, "fixture should produce a few cells per staff"

    before = _png_bytes(bench)
    for p in (bench / "cells").glob("*.png"):
        p.unlink()
    assert _png_bytes(bench) == {}

    report = rc.recut(bench, repo_root=tmp_path, dpi=DPI, log=lambda *_: None)

    assert report.clean, (report.missing, report.mismatched)
    assert sorted(report.written) == sorted(e["cell_id"] for e in manifest)
    # The claim in full: not merely "some image", the SAME image.
    assert _png_bytes(bench) == before


def test_the_padding_mode_is_recovered_from_the_manifest(tmp_path, page_pdf):
    # The two modes frame this page differently, and nothing records which was
    # used — the manifest's own numbers are the only evidence.
    pipe = rc.cut_page(page_pdf, 0, dpi=DPI, mode="pipeline")[0].height
    orch = rc.cut_page(page_pdf, 0, dpi=DPI, mode="orchestral")[0].height
    assert pipe != orch, "fixture cannot distinguish the modes"

    for mode in ("pipeline", "orchestral"):
        bench = tmp_path / f"m-{mode}"
        _build_batch(bench, page_pdf, mode)
        report = rc.recut(bench, repo_root=tmp_path, dpi=DPI, dry_run=True,
                          log=lambda *_: None)
        assert report.clean
        assert set(report.modes.values()) == {mode}


def test_a_manifest_frame_that_does_not_match_the_page_is_refused(tmp_path, page_pdf):
    bench = tmp_path / "tampered"
    manifest = _build_batch(bench, page_pdf, "pipeline")
    for p in (bench / "cells").glob("*.png"):
        p.unlink()
    # One cell claims a frame no padding mode produces — the shape of a batch
    # cut by code that has since changed. Nothing may be written.
    manifest[0]["cell_canonical_h"] = int(manifest[0]["cell_canonical_h"]) + 40
    (bench / "cells.json").write_text(json.dumps(manifest, indent=2))

    report = rc.recut(bench, repo_root=tmp_path, dpi=DPI, log=lambda *_: None)

    assert not report.clean
    assert [cid for cid, _ in report.mismatched] == [manifest[0]["cell_id"]]
    assert report.written == []
    assert _png_bytes(bench) == {}, "a refusal writes nothing at all"


def test_allow_partial_writes_the_rest_when_one_cell_is_tampered(tmp_path, page_pdf):
    bench = tmp_path / "partial"
    manifest = _build_batch(bench, page_pdf, "pipeline")
    for p in (bench / "cells").glob("*.png"):
        p.unlink()
    bad = manifest[0]["cell_id"]
    manifest[0]["cell_canonical_h"] = int(manifest[0]["cell_canonical_h"]) + 40
    (bench / "cells.json").write_text(json.dumps(manifest, indent=2))

    report = rc.recut(bench, repo_root=tmp_path, dpi=DPI, allow_partial=True,
                      log=lambda *_: None)

    assert bad not in report.written
    assert len(report.written) == len(manifest) - 1
    assert f"{bad}.png" not in _png_bytes(bench)


# ---------------------------------------------------------------- localization
#
# `OMR_CELL_LINE_TRACE` (default off) slides a cell's STORED five rows onto
# the ink beneath it and touches nothing else about the frame — one frame,
# two grids, measured 360/360 byte-identical cell images in
# benchmarks/omr-cell-grid-tilt-2026-09/RESULTS_TILT_COST.md. These tests pin
# what that means for a re-cut: the ys check identifies the FRAME, so a batch
# whose manifest was written under either flag state must re-cut
# byte-identically, whatever the flag says in the re-cutting environment.
#
# The fixture page RAMPS its two staves in opposite directions — opposite so
# the page's net skew is ~zero and preprocessing's deskew cannot straighten
# the ramp away — by 1.2pt across the width. Phase 1 fits each staff's five
# rows as ideal horizontals, so end-of-measure-row cells sit a measurable
# fraction of a space off their own print: exactly the geometry the flag
# exists for, on a page small enough for a test. 1.2pt is also near the most
# this detector still reads as a staff (1.8pt loses the staves entirely).


def _draw_tilted_page(path: Path) -> None:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)

    def staff(y0: float, ramp: float) -> None:
        def y_at(x: float, i: int) -> float:
            return y0 + i * 6 + ramp * (x - 60) / 490.0

        for i in range(5):
            page.draw_line(pymupdf.Point(60, y_at(60, i)),
                           pymupdf.Point(550, y_at(550, i)), width=0.6)
        for bx in (60, 220, 380, 550):
            page.draw_line(pymupdf.Point(bx, y_at(bx, 0)),
                           pymupdf.Point(bx, y_at(bx, 4)), width=0.9)
        for nx in (120, 180, 280, 340, 440):
            page.draw_circle(pymupdf.Point(nx, y_at(nx, 2)), 2.6, fill=(0, 0, 0))

    staff(200, +1.2)
    staff(254, -1.2)
    doc.save(str(path))
    doc.close()


@pytest.fixture(scope="module")
def tilted_page_pdf(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("synth-tilt") / "tilted.pdf"
    _draw_tilted_page(p)
    return p


def _cut_flag_off(pdf: Path, mode: str):
    """Cut the way every pre-flag batch was cut: localization genuinely off."""
    import os

    from tools.omr.annotate.select_cells_orchestral import _run_phase1_on_page

    before = os.environ.get("OMR_CELL_LINE_TRACE")
    os.environ["OMR_CELL_LINE_TRACE"] = "0"
    try:
        with rc.padding_mode(mode):
            return _run_phase1_on_page(pdf, 0, dpi=DPI)
    finally:
        if before is None:
            os.environ.pop("OMR_CELL_LINE_TRACE", None)
        else:
            os.environ["OMR_CELL_LINE_TRACE"] = before


def test_one_frame_two_grids_and_the_fixture_actually_localizes(tilted_page_pdf):
    # The invariant everything below rests on, end to end through real
    # phase 1: localization moves the stored grid and nothing else about the
    # frame, and the unlocalized stash IS the flag-off grid. Asserting the
    # fixture localizes at least one cell is what keeps the two batch tests
    # from passing vacuously on a page the comb abstains on — the trap
    # RESULTS_TILT_COST.md records under "One trap".
    off = {rc.cell_key(c.system_index, c.staff_index, c.measure_index): c
           for c in _cut_flag_off(tilted_page_pdf, "pipeline")}
    on = {rc.cell_key(c.system_index, c.staff_index, c.measure_index): c
          for c in rc.cut_page(tilted_page_pdf, 0, dpi=DPI, mode="pipeline")}
    assert off.keys() == on.keys()

    localized = [k for k, c in on.items()
                 if getattr(c, "line_grid_localized", None) is not None]
    assert localized, "the fixture page must localize, or these tests are vacuous"

    for k, a in off.items():
        b = on[k]
        assert a.bbox_page_px == b.bbox_page_px
        assert a.upscale_factor == b.upscale_factor
        assert (a.image == b.image).all()
        if k in localized:
            got_unloc = list(b.staff_line_ys_canonical_unlocalized)
            assert got_unloc == [int(y) for y in a.staff_line_ys_canonical]
            assert list(b.staff_line_ys_canonical) != got_unloc
        else:
            assert list(a.staff_line_ys_canonical) == list(b.staff_line_ys_canonical)


def test_a_localized_grid_batch_recuts_byte_identically(tmp_path, tilted_page_pdf):
    # A batch cut with the flag ON records MOVED rows in its manifest — the
    # manifest a cutter writes once the flag ships. The rows are metadata
    # about the same frame, so a re-cut must verify every cell and reproduce
    # every image, `_nostaff.png` included (its erasure follows the manifest's
    # own grid, via _restore_manifest_grid).
    bench = tmp_path / "localized-grid"
    manifest = _build_batch(bench, tilted_page_pdf, "pipeline")

    unloc = {}
    for c in rc.cut_page(tilted_page_pdf, 0, dpi=DPI, mode="pipeline"):
        key = rc.cell_key(c.system_index, c.staff_index, c.measure_index)
        unloc[key] = [int(y) for y in getattr(
            c, "staff_line_ys_canonical_unlocalized", c.staff_line_ys_canonical)]
    moved = [e["cell_id"] for e in manifest
             if [int(y) for y in e["staff_line_ys_canonical"]]
             != unloc[rc.entry_key(e)]]
    assert moved, "the manifest must carry a localized grid, or this test is vacuous"

    before = _png_bytes(bench)
    for p in (bench / "cells").glob("*.png"):
        p.unlink()

    report = rc.recut(bench, repo_root=tmp_path, dpi=DPI, log=lambda *_: None)

    assert report.clean, (report.missing, report.mismatched)
    assert sorted(report.written) == sorted(e["cell_id"] for e in manifest)
    assert _png_bytes(bench) == before


def test_a_pre_flag_batch_recuts_under_a_flag_on_environment(
        tmp_path, tilted_page_pdf, monkeypatch):
    # The hazard RESULTS_TILT_COST.md names: every existing batch was cut
    # before the flag existed, so its manifest records the frame's own rows.
    # A re-cut in an environment that has since turned the flag on must not
    # read the moved rows as a different frame — and must still erase the
    # staff lines where the batch's own images did.
    bench = tmp_path / "pre-flag"
    manifest = _build_batch(bench, tilted_page_pdf, "pipeline",
                            cells=_cut_flag_off(tilted_page_pdf, "pipeline"))

    before = _png_bytes(bench)
    for p in (bench / "cells").glob("*.png"):
        p.unlink()

    monkeypatch.setenv("OMR_CELL_LINE_TRACE", "1")
    report = rc.recut(bench, repo_root=tmp_path, dpi=DPI, log=lambda *_: None)

    assert report.clean, (report.missing, report.mismatched)
    assert sorted(report.written) == sorted(e["cell_id"] for e in manifest)
    assert _png_bytes(bench) == before
