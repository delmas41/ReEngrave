"""Unit tests for clef-reader PRECEDENCE inside `transcribe._detections_for_cell`.

Three readers can name a staff's clef: the production detector, the optional
staff-header specialist (`--clef-weights`), and the classical-CV C-clef
locator. Bug: the specialist used to set `clef_source` unconditionally,
which — because the locator only runs `if clef_source is None` — meant a
locator finding was silently discarded whenever the specialist also had an
opinion, even a wrong one. Measured end to end on Beethoven 5, IMSLP score
imslp-575951, page_index 68 (dpi 600): staves 4 and 5 both read as a C clef
by the locator ("tenor") but flipped to an incorrect "bass" by the
specialist under the old ordering. Fix: the locator runs BEFORE the
specialist now, and the specialist's clef is applied only when the locator
did not already claim the staff (`clef_source != "cv_locator"`) — see the
"Classical-CV C-clef locator" / "Decoupled staff-header specialist" comments
in transcribe.py.

These tests exercise that precedence directly with fakes, independent of any
real weights — same style as test_header_reader.py.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from tools.omr import transcribe as transcribe_mod
from tools.omr.transcribe import _detections_for_cell
from tools.omr.types import MeasureCell


def _cell(width=800, height=400):
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=np.zeros((height, width, 3), np.uint8), image_no_staff=None,
        bbox_page_px=(0, 0, width, height), staff_line_ys_canonical=[],
        upscale_factor=1.0,
    )


class _FakeDetector:
    """Stands in for the production YOLO detector: no detections, so the
    per-notehead pitch/rhythm passes below the clef block are all no-ops."""

    def detect(self, cell, **kwargs):
        return []


def _det(category, smufl, x=100, y=40, w=60, h=80, conf=0.9):
    return SimpleNamespace(
        category=category, smufl_name=smufl, confidence=conf,
        x_canonical=x, y_canonical=y, width_canonical=w, height_canonical=h,
    )


class _FakeSpecialist:
    """Stands in for the clef-weights YoloDetector: always reads `clef`."""

    def __init__(self, smufl):
        self.smufl = smufl

    def detect(self, cell, **kwargs):
        return [_det("clef", self.smufl)]


def _run(monkeypatch, *, located_clef: str | None, specialist_smufl: str):
    """Call `_detections_for_cell` with a fake locator result and a fake
    specialist read, and return (active_clef, clef_source)."""
    if located_clef is None:
        monkeypatch.setattr(transcribe_mod, "locate_clef", lambda cell, **kw: None)
    else:
        located = SimpleNamespace(read=SimpleNamespace(name=located_clef))
        monkeypatch.setattr(transcribe_mod, "locate_clef", lambda cell, **kw: located)

    _, active_clef, _, _, clef_source, _ = _detections_for_cell(
        _FakeDetector(),
        _cell(),
        conf_threshold=0.25,
        imgsz=None,
        iou_threshold=0.5,
        agnostic_nms=True,
        active_clef=None,
        active_key_sig={},
        active_time_sig=None,
        clef_reader=_FakeSpecialist(specialist_smufl),
        header_cell=None,
        read_clef=True,
        locate_c_clefs=True,
    )
    return active_clef, clef_source


def test_locator_finding_wins_over_a_disagreeing_specialist(monkeypatch):
    # Locator (shape-measured) says alto; specialist (appearance model) says
    # bass, same shape as the Beethoven 5 p.68 regression. The locator wins.
    active_clef, clef_source = _run(
        monkeypatch, located_clef="alto", specialist_smufl="clefF",
    )
    assert active_clef == "alto"
    assert clef_source == "cv_locator"


def test_specialist_still_applies_when_the_locator_abstains(monkeypatch):
    # The locator only recognises C clefs and abstains on everything else —
    # that must not silence the specialist, which is the whole point of it.
    active_clef, clef_source = _run(
        monkeypatch, located_clef=None, specialist_smufl="clefF",
    )
    assert active_clef == "bass"
    assert clef_source == "specialist"


def test_locator_and_specialist_agreeing_still_reports_the_locator(monkeypatch):
    # Not just the right clef — the more specific reader gets credit for it,
    # since clef_source drives which staves count as "detector accuracy" vs
    # "locator accuracy" in benchmarks/omr-clef-geometry/eval_pipeline_clefs.py.
    active_clef, clef_source = _run(
        monkeypatch, located_clef="alto", specialist_smufl="clefCAlto",
    )
    assert active_clef == "alto"
    assert clef_source == "cv_locator"


# ─── The specialist must not overwrite a reader that already spoke ──────────


class _FakeDetectorWithClef:
    """Production detector that DOES read a clef, so `clef_source` is set to
    "detector" before the specialist block runs."""

    def __init__(self, smufl):
        self.smufl = smufl

    def detect(self, cell, **kwargs):
        # y places the glyph on the middle line, which clef_geometry reads as
        # the ordinary treble/bass position for its family.
        return [_det("clef", self.smufl, x=20, y=180, w=60, h=140)]


def _cell_with_lines(width=800, height=400):
    cell = _cell(width, height)
    return MeasureCell(
        page_index=cell.page_index, system_index=cell.system_index,
        staff_index=cell.staff_index, measure_index=cell.measure_index,
        image=cell.image, image_no_staff=None, bbox_page_px=cell.bbox_page_px,
        staff_line_ys_canonical=[150, 200, 250, 300, 350],
        upscale_factor=1.0,
    )


def _run_with_detector(monkeypatch, *, detector_smufl: str, specialist_smufl: str):
    monkeypatch.setattr(transcribe_mod, "locate_clef", lambda cell, **kw: None)
    _, active_clef, _, _, clef_source, _ = _detections_for_cell(
        _FakeDetectorWithClef(detector_smufl),
        _cell_with_lines(),
        conf_threshold=0.25, imgsz=None, iou_threshold=0.5, agnostic_nms=True,
        active_clef=None, active_key_sig={}, active_time_sig=None,
        clef_reader=_FakeSpecialist(specialist_smufl),
        header_cell=None, read_clef=True, locate_c_clefs=True,
    )
    return active_clef, clef_source


def test_specialist_does_not_overwrite_the_detector(monkeypatch):
    """GAP-FILL ONLY, and this is the case with the most staves behind it.

    Measured over 179 pages of the corpus sweep, a specialist allowed to
    overwrite takes 90% of WTC's staves and 83% of handel-red's away from a
    detector that was already reading 100% of their clefs — and on the
    52-staff hand-read set it scores 96% against that detector's 97%. Every
    one of those substitutions is a slightly losing trade for no gain, because
    all of the specialist's value is in staves nobody read at all.
    """
    active_clef, clef_source = _run_with_detector(
        monkeypatch, detector_smufl="clefG", specialist_smufl="clefF",
    )
    assert clef_source == "detector", "the specialist must not displace the detector"
    assert active_clef == "treble"


def test_specialist_fills_the_gap_when_the_detector_is_silent(monkeypatch):
    """The other half of the rule: where nothing else read a clef, it applies.

    This is the population the specialist exists for — 30% of staves
    corpus-wide, 79% on Beethoven 5, where the positional default answers
    "treble" every time (benchmarks/omr-clef-geometry/eval_blind_page_clefs.py).
    """
    active_clef, clef_source = _run(
        monkeypatch, located_clef=None, specialist_smufl="clefF",
    )
    assert clef_source == "specialist"
    assert active_clef == "bass"
