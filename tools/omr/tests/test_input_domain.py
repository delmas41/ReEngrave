"""The scan-vs-engraved classifier behind weight routing.

Synthetic PDFs are built with PyMuPDF in-test, one per trap the corpus probe
surfaced (benchmarks/omr-weight-routing-2026-09/FINDINGS.md): the OCR text
layer on a scan, the scan tiled into strips, the blank page, the digital
title page whose only content is text, and the scan behind a digital cover.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from tools.omr.input_domain import (
    DEFAULT_CLASSIFY_PAGES,
    ENGRAVED,
    ENGRAVED_MIN_DRAWINGS,
    SCANNED,
    UNKNOWN,
    classify_pdf_domain,
)

A4 = fitz.paper_rect("a4")


def _raster_png() -> bytes:
    return fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 40)).tobytes("png")


def _add_scan_page(doc: fitz.Document, *, tiles: int = 1,
                   text: str = "") -> None:
    """A page whose ink is raster: one full-page image, or `tiles` strips."""
    page = doc.new_page(width=A4.width, height=A4.height)
    png = _raster_png()
    strip_h = A4.height / tiles
    for i in range(tiles):
        page.insert_image(
            fitz.Rect(0, i * strip_h, A4.width, (i + 1) * strip_h),
            stream=png)
    if text:
        page.insert_text(fitz.Point(72, 72), text)


def _add_vector_page(doc: fitz.Document, *, n_lines: int = 200,
                     logo: bool = False) -> None:
    """A page whose ink is drawn paths, the way every typesetter emits music."""
    page = doc.new_page(width=A4.width, height=A4.height)
    for i in range(n_lines):
        y = 40 + (i % 150) * 5
        page.draw_line(fitz.Point(40, y), fitz.Point(A4.width - 40, y))
    if logo:  # a small raster logo must not read as a scan
        page.insert_image(fitz.Rect(10, 10, 60, 60), stream=_raster_png())


def _add_text_page(doc: fitz.Document, text: str = "L'ABC musical") -> None:
    page = doc.new_page(width=A4.width, height=A4.height)
    page.insert_text(fitz.Point(72, 144), text, fontsize=24)


@pytest.fixture()
def make_pdf(tmp_path):
    def _make(name: str, builder) -> Path:
        doc = fitz.open()
        builder(doc)
        path = tmp_path / name
        doc.save(path)
        doc.close()
        return path
    return _make


def test_full_page_raster_is_scanned(make_pdf):
    pdf = make_pdf("scan.pdf", lambda d: _add_scan_page(d))
    c = classify_pdf_domain(pdf)
    assert c.verdict == SCANNED
    assert c.pages[0].total_raster_coverage >= 0.95


def test_scan_with_ocr_text_layer_is_still_scanned(make_pdf):
    # The IMSLP 575951 trap: a text layer must never outvote the raster.
    pdf = make_pdf("scan-ocr.pdf",
                   lambda d: _add_scan_page(d, text="Allegro con brio " * 40))
    assert classify_pdf_domain(pdf).verdict == SCANNED


def test_tiled_scan_is_scanned_by_total_coverage(make_pdf):
    # The Ravel/Durand trap: eight strips, each far below any max threshold.
    pdf = make_pdf("tiled.pdf", lambda d: _add_scan_page(d, tiles=8))
    c = classify_pdf_domain(pdf)
    assert c.verdict == SCANNED
    assert c.pages[0].n_images == 8


def test_vector_page_is_engraved(make_pdf):
    pdf = make_pdf("lily.pdf", lambda d: _add_vector_page(d))
    assert classify_pdf_domain(pdf).verdict == ENGRAVED


def test_small_raster_logo_does_not_make_engraving_a_scan(make_pdf):
    pdf = make_pdf("logo.pdf", lambda d: _add_vector_page(d, logo=True))
    assert classify_pdf_domain(pdf).verdict == ENGRAVED


def test_blank_page_abstains(make_pdf):
    pdf = make_pdf("blank.pdf",
                   lambda d: d.new_page(width=A4.width, height=A4.height))
    assert classify_pdf_domain(pdf).verdict == UNKNOWN


def test_text_only_title_page_abstains(make_pdf):
    # Text is not evidence (Kirchhoff p0): its doc classifies by music pages.
    pdf = make_pdf("title.pdf", _add_text_page)
    assert classify_pdf_domain(pdf).verdict == UNKNOWN


def test_sparse_vector_page_abstains(make_pdf):
    # Below the drawings floor (scan pages measured 0-4 paths).
    pdf = make_pdf("sparse.pdf",
                   lambda d: _add_vector_page(d, n_lines=4))
    c = classify_pdf_domain(pdf)
    assert c.verdict == UNKNOWN
    assert c.pages[0].n_drawings < ENGRAVED_MIN_DRAWINGS


def test_any_scan_page_wins_over_digital_cover(make_pdf):
    # An IMSLP scan behind a generated cover page is a scan.
    def build(d):
        _add_vector_page(d)          # digital cover
        _add_scan_page(d)            # the music
    pdf = make_pdf("cover.pdf", build)
    assert classify_pdf_domain(pdf).verdict == SCANNED


def test_engraved_doc_with_blank_and_title_pages(make_pdf):
    def build(d):
        _add_text_page(d)            # title
        d.new_page(width=A4.width, height=A4.height)  # blank verso
        _add_vector_page(d)          # music
    pdf = make_pdf("typeset.pdf", build)
    assert classify_pdf_domain(pdf).verdict == ENGRAVED


def test_page_indices_restrict_the_evidence(make_pdf):
    def build(d):
        _add_scan_page(d)
        _add_vector_page(d)
    pdf = make_pdf("mixed.pdf", build)
    assert classify_pdf_domain(pdf, page_indices=[1]).verdict == ENGRAVED
    assert classify_pdf_domain(pdf, page_indices=[0]).verdict == SCANNED
    # Out-of-range indices are dropped, not errors.
    assert classify_pdf_domain(pdf, page_indices=[99]).verdict == UNKNOWN


def test_default_page_budget(make_pdf):
    def build(d):
        for _ in range(DEFAULT_CLASSIFY_PAGES + 3):
            d.new_page(width=A4.width, height=A4.height)
    pdf = make_pdf("long-blank.pdf", build)
    assert len(classify_pdf_domain(pdf).pages) == DEFAULT_CLASSIFY_PAGES


def test_unopenable_pdf_abstains_without_raising(tmp_path):
    missing = tmp_path / "missing.pdf"
    c = classify_pdf_domain(missing)
    assert c.verdict == UNKNOWN
    assert "could not open" in c.reason

    garbage = tmp_path / "garbage.pdf"
    garbage.write_bytes(b"not a pdf at all")
    assert classify_pdf_domain(garbage).verdict == UNKNOWN


def test_to_dict_is_json_ready(make_pdf):
    import json

    pdf = make_pdf("scan2.pdf", lambda d: _add_scan_page(d))
    d = classify_pdf_domain(pdf).to_dict()
    json.dumps(d)
    assert d["verdict"] == SCANNED
    assert d["pages"][0]["page_index"] == 0
