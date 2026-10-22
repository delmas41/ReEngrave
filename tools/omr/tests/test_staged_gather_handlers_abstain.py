"""ROADMAP 2.60 -- GATHER handlers abstain, never default.

CLAUDE.md rule 8: *a fallback never converts "cannot tell" into an answer.*
Before this item, a dozen `except Exception` handlers in
`tools/omr/staged/gather.py` caught a reader's crash and fell back to a
default that the record then carried as a FINDING: a header window that
could not be cut was filed `no_staff_geometry`; a catalog that threw was
filed `not_in_catalog` ("no edition matches this PDF"); a staff-metrics
reader that threw was filed `no_detections` ("the detector fired nothing
here"); a key-signature fit that threw on every candidate clef was filed
`no_clusters` ("no slot table fits this header"); and several crashes left
no row at all.

Each test below makes the INNER call raise and asserts the row the record
now carries: the reader's own quantity, on the subject the reader was
working on, `reason == ABSTAIN.READER_UNAVAILABLE` and the exception class
in `detail["error"]` -- the exact shape of the sixteen handlers that already
did this (`gather_wedge_boxes`, `gather_cv_lines`, `gather_clef_locator`'s
per-crop handler, ...). The reason word is NOT the exception class: the
abstention vocabulary is CLOSED (`ABSTAIN.check` raises on any other word),
and an open vocabulary is what makes a typo indistinguishable from a reading.

⚠️ EVERY CLASS CARRIES A POSITIVE CONTROL: the same call NOT raising files
exactly the row it filed before this item, with no `error` key -- the record
is bit-identical where nothing throws.

All of it is monkeypatched: a cloud container has no weights, no library and
no page to gather (CLAUDE.md §5a).
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q, READERS


def _boom(*_a, **_k):
    raise RuntimeError("boom")


def _cell(staff_index=0, measure_index=0, page=0):
    return SimpleNamespace(page_index=page, system_index=0,
                           staff_index=staff_index,
                           measure_index=measure_index,
                           staff_line_ys_canonical=[0.0, 10.0, 20.0, 30.0,
                                                    40.0],
                           bbox_page_px=(100, 200, 200, 400),
                           upscale_factor=2.0, image=None)


def _pws(n_staves=1):
    staves = [SimpleNamespace(system_index=0, staff_index=i)
              for i in range(n_staves)]
    return SimpleNamespace(page=SimpleNamespace(page_index=0), staves=staves)


_LOCAL = {0: (0, 0)}
_STAFF = R.staff(0, 0, 0)


def _refusals(log, quantity, subject, *, frame=None, reader=None):
    return [a for a in log.refusals(quantity, subject)
            if (frame is None or a.frame == frame)
            and (reader is None or a.reader == reader)]


def _unavailable(rows):
    return [a for a in rows if a.reason == ABSTAIN.READER_UNAVAILABLE]


# ─────────────────────────────────────────────────────────────────────────────
# 1. `_lowconf_rescue_witnesses`: the stem witness reader threw (was `stems=[]`)
# ─────────────────────────────────────────────────────────────────────────────


def _rescue_run(monkeypatch, detect_lines):
    from tools.omr import line_detection
    monkeypatch.setattr(line_detection, "detect_lines", detect_lines)
    monkeypatch.setenv(G.INK_ENV, "0")      # no rest search to order against
    log = Log()
    G.gather_lowconf_rescue(log, [_cell(0, 1)], _LOCAL, {},
                            detector=SimpleNamespace(detect=_boom))
    return log, R.cell(0, 0, 0, 1)


def test_rescue_stem_witness_crash_abstains_on_the_cell(monkeypatch):
    log, cell = _rescue_run(monkeypatch, _boom)
    rows = _unavailable(_refusals(log, Q.GLYPH_BOX, cell,
                                  reader=READERS.RESCUE_LOWCONF))
    assert len(rows) == 1
    assert rows[0].detail["error"] == "RuntimeError"
    assert rows[0].detail["witness_kind"] == "stem_end"
    assert rows[0].frame == G.frame_cell(1)
    # the default still holds: no witness, so the existing no-witness row
    # is filed and the detector is never re-run (`_boom` would raise)
    assert any(a.reason == ABSTAIN.NO_DETECTIONS
               for a in log.refusals(Q.GLYPH_BOX, cell))


def test_rescue_stem_witness_control_no_raise_no_new_row(monkeypatch):
    log, cell = _rescue_run(monkeypatch, lambda *a, **k: {"stems": []})
    assert not _unavailable(log.refusals(Q.GLYPH_BOX, cell))
    assert [a.reason for a in log.refusals(Q.GLYPH_BOX, cell)] \
        == [ABSTAIN.NO_DETECTIONS]


# ─────────────────────────────────────────────────────────────────────────────
# 2. `header_cells_for_page` threw (was `header_cells = {}`) -- three readers
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def header_cells(monkeypatch):
    from tools.omr import staff_header

    def _set(fn):
        monkeypatch.setattr(staff_header, "header_cells_for_page", fn)
    return _set


@pytest.fixture
def quiet_locator(monkeypatch):
    from tools.omr import clef_locator
    monkeypatch.setattr(clef_locator, "locate_clef", lambda *a, **k: None)


def test_clef_locator_header_crash_abstains_unavailable(header_cells,
                                                        quiet_locator):
    header_cells(_boom)
    log = Log()
    G.gather_clef_locator(log, _pws(), [_cell(0, 0)], _LOCAL, {})
    rows = _refusals(log, Q.CLEF_LOCATED, _STAFF,
                     frame=G.FRAME_HEADER_WINDOW, reader=READERS.CV_LOCATOR)
    assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
    assert rows[0].detail["error"] == "RuntimeError"
    # the default still holds: the cell-0 crop is read as before
    assert _refusals(log, Q.CLEF_LOCATED, _STAFF, frame=G.frame_cell(0))


def test_clef_locator_header_control_no_crop_is_still_no_geometry(
        header_cells, quiet_locator):
    header_cells(lambda pws: {})
    log = Log()
    G.gather_clef_locator(log, _pws(), [_cell(0, 0)], _LOCAL, {})
    rows = _refusals(log, Q.CLEF_LOCATED, _STAFF,
                     frame=G.FRAME_HEADER_WINDOW)
    assert [a.reason for a in rows] == [ABSTAIN.NO_STAFF_GEOMETRY]
    assert "error" not in rows[0].detail


def test_key_signature_header_crash_abstains_unavailable(header_cells):
    header_cells(_boom)
    log = Log()
    G.gather_key_signature(log, _pws(), [_cell(0, 0)], _LOCAL, {})
    rows = _refusals(log, Q.KEYSIG_RUN_POSITION, _STAFF,
                     reader=READERS.CV_HEADER)
    assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
    assert rows[0].detail["error"] == "RuntimeError"


def test_key_signature_header_control(header_cells):
    header_cells(lambda pws: {})
    log = Log()
    G.gather_key_signature(log, _pws(), [_cell(0, 0)], _LOCAL, {})
    rows = _refusals(log, Q.KEYSIG_RUN_POSITION, _STAFF)
    assert [a.reason for a in rows] == [ABSTAIN.NO_STAFF_GEOMETRY]
    assert "error" not in rows[0].detail


def test_meter_header_crash_abstains_unavailable(header_cells):
    header_cells(_boom)
    log = Log()
    G.gather_meter(log, _pws(), [_cell(0, 0)], _LOCAL, {})
    rows = _refusals(log, Q.METER_TEMPLATE, _STAFF, reader=READERS.TEMPLATE)
    assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
    assert rows[0].detail["error"] == "RuntimeError"


def test_meter_header_control(header_cells):
    header_cells(lambda pws: {})
    log = Log()
    G.gather_meter(log, _pws(), [_cell(0, 0)], _LOCAL, {})
    rows = _refusals(log, Q.METER_TEMPLATE, _STAFF)
    assert [a.reason for a in rows] == [ABSTAIN.NO_STAFF_GEOMETRY]
    assert "error" not in rows[0].detail


# ─────────────────────────────────────────────────────────────────────────────
# 3. Key-signature fits per candidate clef threw (was a bare `continue`)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def keysig_crop(header_cells):
    crop = SimpleNamespace(image=None, staff_line_ys_canonical=[])
    header_cells(lambda pws: {0: crop})
    return crop


def test_keysig_locator_crash_per_candidate(monkeypatch, keysig_crop):
    from tools.omr import key_signature_locator, key_signature_template
    monkeypatch.setattr(key_signature_locator, "locate_key_signature", _boom)
    monkeypatch.setattr(key_signature_template, "read_key_signature",
                        lambda *a, **k: None)
    log = Log()
    G.gather_key_signature(log, _pws(), [_cell(0, 0)], _LOCAL, {})
    fits = _unavailable(_refusals(log, Q.KEYSIG_CLEF_FIT, _STAFF,
                                  reader=READERS.CV_HEADER))
    assert sorted(a.detail["candidate"] for a in fits) \
        == sorted(G._SLOT_TABLE_CLEFS)
    assert {a.detail["error"] for a in fits} == {"RuntimeError"}
    # ...and the run is NOT filed as "no slot table fits" -- nothing was fitted
    run = _refusals(log, Q.KEYSIG_RUN_POSITION, _STAFF)
    assert [a.reason for a in run] == [ABSTAIN.READER_UNAVAILABLE]
    assert run[0].detail["error"] == "RuntimeError"
    assert not log.rows(Q.KEYSIG_RUN_POSITION, _STAFF)


def test_keysig_locator_control_no_fit_is_still_no_clusters(monkeypatch,
                                                            keysig_crop):
    from tools.omr import key_signature_locator, key_signature_template
    monkeypatch.setattr(key_signature_locator, "locate_key_signature",
                        lambda *a, **k: None)
    monkeypatch.setattr(key_signature_template, "read_key_signature",
                        lambda *a, **k: None)
    log = Log()
    G.gather_key_signature(log, _pws(), [_cell(0, 0)], _LOCAL, {})
    assert not log.refusals(Q.KEYSIG_CLEF_FIT, _STAFF)
    assert not log.refusals(Q.KEYSIG_TEMPLATE_FIT, _STAFF)
    run = _refusals(log, Q.KEYSIG_RUN_POSITION, _STAFF)
    assert [a.reason for a in run] == [ABSTAIN.NO_CLUSTERS]
    assert "error" not in run[0].detail


def test_keysig_template_crash_per_candidate(monkeypatch):
    from tools.omr import key_signature_template
    monkeypatch.setattr(key_signature_template, "read_key_signature", _boom)
    log = Log()
    G._gather_keysig_template(log, _STAFF, SimpleNamespace())
    rows = _unavailable(_refusals(log, Q.KEYSIG_TEMPLATE_FIT, _STAFF,
                                  reader=READERS.TEMPLATE,
                                  frame=G.FRAME_HEADER_WINDOW))
    assert sorted(a.detail["candidate"] for a in rows) \
        == sorted(G._SLOT_TABLE_CLEFS)
    assert {a.detail["error"] for a in rows} == {"RuntimeError"}
    assert not log.rows(Q.KEYSIG_TEMPLATE_FIT, _STAFF)


def test_keysig_template_import_failure_abstains_once(monkeypatch):
    import tools.omr as omr
    monkeypatch.delattr(omr, "key_signature_template", raising=False)
    monkeypatch.setitem(sys.modules, "tools.omr.key_signature_template", None)
    log = Log()
    G._gather_keysig_template(log, _STAFF, SimpleNamespace())
    rows = _refusals(log, Q.KEYSIG_TEMPLATE_FIT, _STAFF,
                     reader=READERS.TEMPLATE)
    assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
    assert rows[0].detail["error"] == "ModuleNotFoundError"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Meter OCR at a bar head (research arm): import and staff-metrics crashes
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def ocr_at_bar(monkeypatch):
    monkeypatch.setenv(G.METER_OCR_AT_BAR_ENV, "1")
    monkeypatch.setenv(G.RESEARCH_ENV, G.METER_OCR_AT_BAR_ENV)


def _ocr_at_bar_run():
    log = Log()
    G.gather_meter_ocr_at_bars(log, [_cell(0, 0), _cell(0, 1)], _LOCAL, {})
    return log, R.cell(0, 0, 0, 1)


def test_meter_ocr_at_bar_import_failure_names_the_error(monkeypatch,
                                                         ocr_at_bar):
    import tools.omr as omr
    monkeypatch.delattr(omr, "meter_digit_ocr", raising=False)
    monkeypatch.setitem(sys.modules, "tools.omr.meter_digit_ocr", None)
    log, cell = _ocr_at_bar_run()
    rows = _refusals(log, Q.METER_OCR_AT_BAR, cell, reader=READERS.TESSERACT)
    assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
    assert rows[0].detail["error"] == "ModuleNotFoundError"


def test_meter_ocr_at_bar_control_not_installed_has_no_error(monkeypatch,
                                                             ocr_at_bar):
    from tools.omr import meter_digit_ocr
    monkeypatch.setattr(meter_digit_ocr, "available", lambda: False)
    log, cell = _ocr_at_bar_run()
    rows = _refusals(log, Q.METER_OCR_AT_BAR, cell)
    assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
    assert "error" not in rows[0].detail


def test_meter_ocr_at_bar_metrics_crash_is_not_no_detections(monkeypatch,
                                                             ocr_at_bar):
    from tools.omr import header_ink, meter_digit_ocr
    monkeypatch.setattr(meter_digit_ocr, "available", lambda: True)
    monkeypatch.setattr(header_ink, "staff_metrics", _boom)
    log, cell = _ocr_at_bar_run()
    rows = _refusals(log, Q.METER_OCR_AT_BAR, cell, reader=READERS.TESSERACT)
    assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
    assert rows[0].detail["error"] == "RuntimeError"


def test_meter_ocr_at_bar_metrics_control(monkeypatch, ocr_at_bar):
    from tools.omr import header_ink, meter_digit_ocr
    monkeypatch.setattr(meter_digit_ocr, "available", lambda: True)
    monkeypatch.setattr(header_ink, "staff_metrics", lambda cell: None)
    log, cell = _ocr_at_bar_run()
    rows = _refusals(log, Q.METER_OCR_AT_BAR, cell)
    assert [a.reason for a in rows] == [ABSTAIN.NO_DETECTIONS]
    assert "error" not in rows[0].detail


# ─────────────────────────────────────────────────────────────────────────────
# 5. Margin-label rung availability threw (was `ok = False`)
# ─────────────────────────────────────────────────────────────────────────────


def _labels_run(monkeypatch, surya_available):
    from tools.omr import contextual, staff_labels_surya
    monkeypatch.setattr(staff_labels_surya, "available", surya_available)
    monkeypatch.setattr(contextual, "_labels_for_page",
                        lambda *a, **k: [])
    log = Log()
    G.gather_margin_labels(log, _pws(), [_cell(0, 0)], _LOCAL,
                           pdf_path="no-such-score", surya_fallback=True)
    return log


def test_label_rung_availability_crash_names_the_error(monkeypatch):
    log = _labels_run(monkeypatch, _boom)
    rows = _refusals(log, Q.MARGIN_LABEL, R.page(0), reader=READERS.SURYA)
    assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
    assert rows[0].detail["error"] == "RuntimeError"
    assert rows[0].detail["rungs_unavailable"] == ["surya"]


def test_label_rung_control_not_installed_has_no_error(monkeypatch):
    log = _labels_run(monkeypatch, lambda: False)
    rows = _refusals(log, Q.MARGIN_LABEL, R.page(0), reader=READERS.SURYA)
    assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
    assert "error" not in rows[0].detail


# ─────────────────────────────────────────────────────────────────────────────
# 6. The catalog threw (was `facts = {}`, filed as `not_in_catalog`)
# ─────────────────────────────────────────────────────────────────────────────


def _identity_run(monkeypatch, edition_for_pdf):
    from tools.omr import positional_store
    monkeypatch.setenv(G.DOCUMENT_IDENTITY_ENV, "1")
    monkeypatch.setattr(positional_store, "edition_for_pdf", edition_for_pdf)
    log = Log()
    G.gather_document_identity(log, "/nowhere/no-such-score")
    return _refusals(log, Q.DOCUMENT_IDENTITY, R.DOCUMENT,
                     reader=READERS.CATALOG)


def test_document_identity_catalog_crash_is_not_not_in_catalog(monkeypatch):
    rows = _identity_run(monkeypatch, _boom)
    assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
    assert rows[0].detail["error"] == "RuntimeError"


def test_document_identity_control_unheld_pdf(monkeypatch):
    rows = _identity_run(monkeypatch, lambda path: {})
    assert [a.reason for a in rows] == [ABSTAIN.NOT_IN_CATALOG]
    assert "error" not in rows[0].detail
