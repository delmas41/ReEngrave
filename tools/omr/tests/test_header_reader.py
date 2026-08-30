"""Unit tests for the decoupled staff-header specialist reader
(`transcribe._read_staff_header`).

The real clef/time-sig gains depend on the specialist WEIGHTS detecting those
glyphs, but the reader's plumbing — crop the header, pull the highest-confidence
clef, parse stacked time-sig digits, and preserve canonical coords through the
crop — is exercised here with a fake detector, independent of any weights. (On
real scans today the clef specialist reads clefs; NO available checkpoint detects
real time-sig digits — the DSv2 domain gap — so the time-sig path stays dormant
until a time-sig-trained specialist is dropped in. This test guards the wiring so
that drop-in "just works".)
"""
from types import SimpleNamespace

import numpy as np

from tools.omr.transcribe import _read_staff_header
from tools.omr.types import MeasureCell


def _det(category, smufl, x, y, w=60, h=80, conf=0.9):
    return SimpleNamespace(
        category=category, smufl_name=smufl, confidence=conf,
        x_canonical=x, y_canonical=y, width_canonical=w, height_canonical=h,
    )


class _FakeReader:
    """Stands in for a YoloDetector: returns canned detections, records the
    (cropped) cell it was handed so tests can assert the crop geometry."""

    def __init__(self, dets):
        self._dets = dets
        self.seen_cell = None

    def detect(self, cell, **kwargs):
        self.seen_cell = cell
        return self._dets


def _cell(width=2048, height=100):
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=np.zeros((height, width, 3), np.uint8), image_no_staff=None,
        bbox_page_px=(0, 0, width, height), staff_line_ys_canonical=[],
        upscale_factor=1.0,
    )


def _read(reader, cell, frac=0.42):
    return _read_staff_header(
        reader, cell, conf=0.30, imgsz=640, header_frac=frac,
        iou_threshold=0.5, agnostic_nms=True,
    )


def test_reads_clef_and_stacked_time_signature():
    # clefF (→ bass) + a stacked 2/4 (numerator 2 on top, denominator 4 below).
    dets = [
        _det("clef", "clefF", 100, 40),
        _det("time_sig_digit", "timeSig2", 400, 20),
        _det("time_sig_digit", "timeSig4", 400, 60),
    ]
    clef, ts = _read(_FakeReader(dets), _cell())
    assert clef == "bass"
    assert ts == {"numerator": 2, "denominator": 4, "raw": "2/4"}


def test_common_time_glyph():
    dets = [_det("clef", "clefG", 100, 40),
            _det("time_sig_digit", "timeSigCommon", 400, 40)]
    clef, ts = _read(_FakeReader(dets), _cell())
    assert clef == "treble"
    assert ts == {"numerator": 4, "denominator": 4, "raw": "C"}


def test_highest_confidence_clef_wins():
    dets = [
        _det("clef", "clefG", 90, 40, conf=0.4),
        _det("clef", "clefCAlto", 110, 40, conf=0.95),
    ]
    clef, ts = _read(_FakeReader(dets), _cell())
    assert clef == "alto"
    assert ts is None


def test_no_header_glyphs_returns_none():
    dets = [_det("notehead", "noteheadBlackOnLine", 500, 50)]
    clef, ts = _read(_FakeReader(dets), _cell())
    assert clef is None
    assert ts is None


def test_crop_geometry_left_header_fraction():
    reader = _FakeReader([])
    _read(reader, _cell(width=2048), frac=0.42)
    # the specialist must see only the left 42% of the cell
    assert reader.seen_cell.width == round(2048 * 0.42)
    assert reader.seen_cell.height == 100  # full height preserved


def test_none_image_is_safe():
    cell = _cell()
    object.__setattr__(cell, "image", None)
    clef, ts = _read(_FakeReader([_det("clef", "clefF", 100, 40)]), cell)
    assert clef is None and ts is None


# ── DPI re-render (Blocker 1 fix) — default-off, guarded ───────────────────
#
# `_read_staff_header` gained `pdf_path` / `page_dpi` kwargs so it can
# re-render the header window straight from the PDF at a fixed reference DPI
# (see `_rerender_header_at_reference_dpi`'s docstring in transcribe.py for
# why). None of the tests above pass them, and they still pass unchanged —
# that IS the no-clef-weights / no-caller-support invariant: the specialist's
# input is untouched unless a caller opts in with both a path and a DPI. The
# tests here pin the guard conditions directly.

from tools.omr.transcribe import _rerender_header_at_reference_dpi  # noqa: E402


def test_rerender_is_a_noop_without_pdf_path():
    cell = _cell()
    assert _rerender_header_at_reference_dpi(
        cell, pdf_path=None, page_dpi=600,
    ) is None


def test_rerender_is_a_noop_without_page_dpi():
    cell = _cell()
    assert _rerender_header_at_reference_dpi(
        cell, pdf_path="some/score.pdf", page_dpi=None,
    ) is None


def test_rerender_is_a_noop_at_or_below_the_reference_dpi():
    cell = _cell()
    # dpi 300 is the reference itself (see HEADER_SPECIALIST_REFERENCE_DPI) —
    # nothing to normalize toward, so this is a no-op, same as a lower dpi.
    assert _rerender_header_at_reference_dpi(
        cell, pdf_path="some/score.pdf", page_dpi=300,
    ) is None
    assert _rerender_header_at_reference_dpi(
        cell, pdf_path="some/score.pdf", page_dpi=150,
    ) is None


def test_rerender_is_a_noop_with_no_image():
    cell = _cell()
    object.__setattr__(cell, "image", None)
    assert _rerender_header_at_reference_dpi(
        cell, pdf_path="some/score.pdf", page_dpi=600,
    ) is None


def test_rerender_is_a_noop_on_a_nonexistent_pdf():
    # Guard conditions all pass (dpi 600 > reference, real image) so this
    # actually reaches the fitz.open() call — which must fail closed, not
    # raise, since a texture fix for one opt-in reader is never a reason to
    # break a transcription.
    cell = _cell()
    assert _rerender_header_at_reference_dpi(
        cell, pdf_path="/nonexistent/path/does-not-exist.pdf", page_dpi=600,
    ) is None
