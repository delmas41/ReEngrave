"""Reading instrument labels out of a PDF text layer (tools/omr/staff_labels.py)."""
from __future__ import annotations

import math

import fitz
import pytest

from tools.omr.preprocessing import render_page
from tools.omr.staff_labels import (
    _pdf_to_pixel_transform,
    _reading_order,
    has_text_layer,
    read_staff_labels,
)
from tools.omr.types import PageWithStaves, Staff

PAGE_W_PT, PAGE_H_PT = 612, 792     # US Letter in points
DPI = 300
ZOOM = DPI / 72.0


# ── reading order ───────────────────────────────────────────────────────────

def test_reading_order_sorts_left_to_right_within_a_line():
    """Sorting on raw (y, x) turned 'Timp.' into 'p. Tim' because OCR gives two
    spans of the same printed line slightly different y."""
    items = [(100.8, 50.0, "p."), (100.2, 20.0, "Tim")]
    assert _reading_order(items, staff_span=48) == ["Tim", "p."]


def test_reading_order_keeps_separate_lines_top_to_bottom():
    items = [(300.0, 10.0, "(Es)"), (100.0, 10.0, "Cor.")]
    assert _reading_order(items, staff_span=48) == ["Cor.", "(Es)"]


def test_reading_order_on_empty_input():
    assert _reading_order([], staff_span=48) == []


# ── coordinate transform ────────────────────────────────────────────────────

def _fake_page(width_pt=PAGE_W_PT, height_pt=PAGE_H_PT):
    doc = fitz.open()
    doc.new_page(width=width_pt, height=height_pt)
    return doc


def test_transform_is_pure_scaling_without_skew():
    doc = _fake_page()
    try:
        w, h = int(PAGE_W_PT * ZOOM), int(PAGE_H_PT * ZOOM)
        f = _pdf_to_pixel_transform(doc[0], DPI, 0.0, w, h)
        x, y = f(100.0, 200.0)
        assert x == pytest.approx(100.0 * ZOOM)
        assert y == pytest.approx(200.0 * ZOOM)
    finally:
        doc.close()


def test_transform_leaves_the_image_centre_fixed_under_skew():
    doc = _fake_page()
    try:
        w, h = int(PAGE_W_PT * ZOOM), int(PAGE_H_PT * ZOOM)
        f = _pdf_to_pixel_transform(doc[0], DPI, 1.5, w, h)
        cx, cy = f(PAGE_W_PT / 2 * (w / (PAGE_W_PT * ZOOM)), PAGE_H_PT / 2)
        # the centre of rotation maps to itself
        assert cx == pytest.approx(w / 2, abs=1.0)
        assert cy == pytest.approx(h / 2, abs=1.0)
    finally:
        doc.close()


def test_skew_moves_a_left_margin_point_vertically():
    """The reason deskew must be replicated: at 1 degree, a label ~1000px left
    of centre shifts ~17px, and staves are only ~150px apart."""
    doc = _fake_page()
    try:
        w, h = int(PAGE_W_PT * ZOOM), int(PAGE_H_PT * ZOOM)
        f0 = _pdf_to_pixel_transform(doc[0], DPI, 0.0, w, h)
        f1 = _pdf_to_pixel_transform(doc[0], DPI, 1.0, w, h)
        x_pt = (w / 2 - 1000) / ZOOM
        _, y0 = f0(x_pt, PAGE_H_PT / 2)
        _, y1 = f1(x_pt, PAGE_H_PT / 2)
        assert abs(y1 - y0) == pytest.approx(1000 * math.sin(math.radians(1.0)), rel=0.05)
    finally:
        doc.close()


# ── end to end over a synthetic PDF with a real text layer ──────────────────

@pytest.fixture
def labelled_pdf(tmp_path):
    """A page with four instrument labels down the left margin."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W_PT, height=PAGE_H_PT)
    labels = [("Fl.", 100), ("Ob.", 200), ("Cl. B", 300), ("Vc.", 400)]
    for text, y in labels:
        page.insert_text((40, y), text, fontsize=11)
    # something out in the music area that must NOT be read as a label
    page.insert_text((400, 200), "sempre pp", fontsize=11)
    path = tmp_path / "labelled.pdf"
    doc.save(path)
    doc.close()
    return path, labels


def _pws_for(path, labels):
    page_img = render_page(path, 0, dpi=DPI)
    staves = []
    for i, (_text, y_pt) in enumerate(labels):
        top = int(y_pt * ZOOM) - 30
        staves.append(Staff(page_index=0, staff_index=i,
                            line_ys=[top + 12 * k for k in range(5)],
                            x_start=int(90 * ZOOM), x_end=int(560 * ZOOM)))
    return PageWithStaves(page=page_img, staves=staves)


def test_labels_join_to_the_right_staves(labelled_pdf):
    path, labels = labelled_pdf
    out = read_staff_labels(_pws_for(path, labels))
    got = {l.staff_index: l.instrument.name for l in out if l.matched}
    assert got == {0: "Flute", 1: "Oboe", 2: "Clarinet", 3: "Cello"}


def test_transposition_survives_the_round_trip(labelled_pdf):
    path, labels = labelled_pdf
    out = {l.staff_index: l for l in read_staff_labels(_pws_for(path, labels))}
    assert out[2].fifths_offset == 2      # "Cl. B" -> clarinet in B-flat
    assert out[0].fifths_offset == 0


def test_text_inside_the_music_area_is_not_read_as_a_label(labelled_pdf):
    path, labels = labelled_pdf
    out = read_staff_labels(_pws_for(path, labels))
    assert not any("sempre" in l.text for l in out)


def test_has_text_layer(labelled_pdf, tmp_path):
    path, _labels = labelled_pdf
    # The synthetic page carries ~27 characters; the 40-char default is tuned
    # for real score pages, so this asserts against an explicit threshold.
    assert has_text_layer(path, 0, min_chars=10)
    assert not has_text_layer(path, 0, min_chars=500)
    assert not has_text_layer(path, 5, min_chars=10)     # out of range
    blank = fitz.open()
    blank.new_page(width=PAGE_W_PT, height=PAGE_H_PT)
    p = tmp_path / "blank.pdf"
    blank.save(p)
    blank.close()
    assert not has_text_layer(p, 0, min_chars=10)


def test_no_text_layer_returns_empty(tmp_path, labelled_pdf):
    _path, labels = labelled_pdf
    blank = fitz.open()
    blank.new_page(width=PAGE_W_PT, height=PAGE_H_PT)
    p = tmp_path / "blank2.pdf"
    blank.save(p)
    blank.close()
    assert read_staff_labels(_pws_for(p, labels)) == []


def test_no_staves_returns_empty(labelled_pdf):
    path, _labels = labelled_pdf
    pws = PageWithStaves(page=render_page(path, 0, dpi=DPI), staves=[])
    assert read_staff_labels(pws) == []


class TestPartialTextLayerStillAsksTheMarginReader:
    """A patchy OCR layer used to suppress the margin reader exactly as a
    complete one did — any label at all and it stopped.

    That is the case that matters most, because a scanned score's text layer is
    routinely partial rather than absent. Measured on the Pastoral: 4 staves of
    10 from the text layer, 10 of 10 from the margin
    (`benchmarks/omr-margin-labels-2026-08/VISION_CEILING_2026-08-30.md`), and
    the six it adds are what carry the part-join down past the winds.
    """

    def _covered(self, n_staves: int, labelled: int) -> bool:
        from types import SimpleNamespace
        from tools.omr.contextual import _well_covered
        from tools.omr.instruments import lookup

        # `_well_covered` reads only system_index and staff_index off a staff,
        # so stubs keep this test off the Staff constructor.
        pws = SimpleNamespace(staves=[SimpleNamespace(staff_index=i, system_index=0)
                                      for i in range(n_staves)])
        flute = lookup("Fl.").instrument
        labels = [SimpleNamespace(staff_index=i, matched=True, instrument=flute)
                  for i in range(labelled)]
        return _well_covered(labels, pws)

    def test_a_thin_text_layer_is_not_enough(self):
        assert self._covered(10, 4) is False, "4 of 10 must still ask the margin"

    def test_a_nearly_complete_text_layer_stands_alone(self):
        assert self._covered(10, 10) is True
        assert self._covered(10, 8) is True

    def test_no_labels_at_all_is_not_covered(self):
        assert self._covered(10, 0) is False


class TestUnresolvedLabelsAreReported:
    """A label the lexicon cannot match must not vanish quietly.

    It produces no label, which is indistinguishable from a staff that carries
    none — and the two want opposite responses. One is the engraving telling you
    nothing; the other is a missing alias, with the string you need sitting right
    there. Mahler 5 p.4 lost eight labels this way in silence
    (`benchmarks/omr-part-staff-join-2026-08/RESULTS.md`).
    """

    def test_a_label_that_matches_nothing_is_not_silently_matched(self):
        from tools.omr.instruments import lookup
        from tools.omr.staff_labels import StaffLabel

        hit = lookup("Zzyzx.")
        assert hit is None, "the premise: this resolves to nothing"
        lab = StaffLabel(staff_index=0, text="Zzyzx.", instrument=None,
                         fifths_offset=0, y_center_px=0.0)
        assert lab.matched is False
        assert lab.text == "Zzyzx.", "and the text survives, to be reported"

    def test_the_summary_carries_the_unmatched_text(self):
        """`apply_contextual_analysis` reports `unresolved_labels`, which is what
        turns 'this page looks unlabelled' into 'add these to instruments.py'."""
        import inspect
        from tools.omr import contextual
        src = inspect.getsource(contextual.apply_contextual_analysis)
        assert "unresolved_labels=unresolved" in src
        assert "NOT MATCHED by the lexicon" in src
