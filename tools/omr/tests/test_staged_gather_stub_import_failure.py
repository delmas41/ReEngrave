"""ROADMAP 2.61b -- a reader whose IMPORT failed is unavailable, not unwritten.

`gather_cv_lines`, `gather_clef_locator`, `gather_key_signature` and
`gather_meter` each import their reader inside a `try`. When that import
failed, the handler called `_stub_cv_lines` / `_stub_per_staff`, which filed
`ABSTAIN.NOT_IMPLEMENTED` -- the word for "this decision is not written", which
`gather_coverage` counts as build progress. A reader that EXISTS and cannot be
imported is a defect (a blind page), the same fact the 2.60 handlers file as
`READER_UNAVAILABLE` with the exception class in `detail["error"]`.

CLAUDE.md rule 8: a fallback never converts "cannot tell" into an answer; here
it was converting "broken" into "not yet built".

Every class has a positive control: the same call with the import intact files
no `NOT_IMPLEMENTED` row, and a stub called WITHOUT an error (a reader that is
genuinely not written -- `gather_margin_labels` with no `pdf_path`) still files
`NOT_IMPLEMENTED`. Monkeypatched throughout: a cloud container has no weights,
no library and no page (CLAUDE.md section 5a).
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q, READERS


def _cell(staff_index=0, measure_index=0, page=0):
    return SimpleNamespace(page_index=page, system_index=0,
                           staff_index=staff_index,
                           measure_index=measure_index,
                           staff_line_ys_canonical=[0.0, 10.0, 20.0, 30.0,
                                                    40.0],
                           bbox_page_px=(100, 200, 200, 400),
                           upscale_factor=2.0, image=None)


def _pws():
    return SimpleNamespace(page=SimpleNamespace(page_index=0),
                           staves=[SimpleNamespace(system_index=0,
                                                   staff_index=0)])


_LOCAL = {0: (0, 0)}
_STAFF = R.staff(0, 0, 0)
_CELL = R.cell(0, 0, 0, 0)


def _break_import(monkeypatch, name):
    """Make `from ..<name> import ...` raise ModuleNotFoundError."""
    import tools.omr as omr
    monkeypatch.delattr(omr, name, raising=False)
    monkeypatch.setitem(sys.modules, f"tools.omr.{name}", None)


def _rows(log, quantity, subject, reader):
    return [a for a in log.refusals(quantity, subject) if a.reader == reader]


def _no_not_implemented(log, quantity, subject, reader):
    return not [a for a in _rows(log, quantity, subject, reader)
                if a.reason == ABSTAIN.NOT_IMPLEMENTED]


# ── the four sites: import failure -> READER_UNAVAILABLE + error ─────────────


def test_cv_lines_import_failure_is_unavailable(monkeypatch):
    _break_import(monkeypatch, "line_detection")
    log = Log()
    G.gather_cv_lines(log, [_cell()], _LOCAL, {})
    for q in (Q.BEAM_STROKE, Q.STEM):
        rows = _rows(log, q, _CELL, READERS.CV_LINES)
        assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
        assert rows[0].detail["error"] == "ModuleNotFoundError"


def test_clef_locator_import_failure_is_unavailable(monkeypatch):
    _break_import(monkeypatch, "clef_locator")
    log = Log()
    G.gather_clef_locator(log, _pws(), [_cell()], _LOCAL, {})
    rows = _rows(log, Q.CLEF_LOCATED, _STAFF, READERS.CV_LOCATOR)
    assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
    assert rows[0].detail["error"] == "ModuleNotFoundError"


def test_key_signature_import_failure_is_unavailable(monkeypatch):
    _break_import(monkeypatch, "key_signature_locator")
    log = Log()
    G.gather_key_signature(log, _pws(), [_cell()], _LOCAL, {})
    rows = _rows(log, Q.KEYSIG_RUN_POSITION, _STAFF, READERS.CV_HEADER)
    assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
    assert rows[0].detail["error"] == "ModuleNotFoundError"


def test_meter_import_failure_is_unavailable(monkeypatch):
    _break_import(monkeypatch, "time_signature_locator")
    log = Log()
    G.gather_meter(log, _pws(), [_cell()], _LOCAL, {})
    rows = _rows(log, Q.METER_TEMPLATE, _STAFF, READERS.TEMPLATE)
    assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
    assert rows[0].detail["error"] == "ModuleNotFoundError"


def test_any_import_time_exception_names_its_class(monkeypatch):
    """Not only ImportError: a module that raises while IMPORTING is the same
    defect, and the class that was raised is what the row names."""
    import tools.omr as omr
    monkeypatch.delattr(omr, "clef_locator", raising=False)
    monkeypatch.delitem(sys.modules, "tools.omr.clef_locator", raising=False)

    class _Finder:
        @staticmethod
        def find_spec(name, path=None, target=None):
            if name == "tools.omr.clef_locator":
                raise ZeroDivisionError("module body blew up")
            return None

    monkeypatch.setattr(sys, "meta_path", [_Finder] + list(sys.meta_path))
    log = Log()
    G.gather_clef_locator(log, _pws(), [_cell()], _LOCAL, {})
    rows = _rows(log, Q.CLEF_LOCATED, _STAFF, READERS.CV_LOCATOR)
    assert [a.reason for a in rows] == [ABSTAIN.READER_UNAVAILABLE]
    assert rows[0].detail["error"] == "ZeroDivisionError"


# ── positive controls: nothing changes where the import works ────────────────


def test_cv_lines_control_import_ok_files_no_not_implemented(monkeypatch):
    from tools.omr import line_detection

    def _boom(*_a, **_k):
        raise RuntimeError("boom")
    monkeypatch.setattr(line_detection, "detect_lines", _boom)
    log = Log()
    G.gather_cv_lines(log, [_cell()], _LOCAL, {})
    for q in (Q.BEAM_STROKE, Q.STEM):
        assert _no_not_implemented(log, q, _CELL, READERS.CV_LINES)
        rows = _rows(log, q, _CELL, READERS.CV_LINES)
        # the pre-existing per-call handler, untouched
        assert [a.detail["error"] for a in rows] == ["RuntimeError"]


@pytest.fixture
def empty_header_cells(monkeypatch):
    from tools.omr import staff_header
    monkeypatch.setattr(staff_header, "header_cells_for_page",
                        lambda pws: {})


def test_clef_locator_control_import_ok(empty_header_cells):
    log = Log()
    G.gather_clef_locator(log, _pws(), [_cell()], _LOCAL, {})
    assert _no_not_implemented(log, Q.CLEF_LOCATED, _STAFF,
                               READERS.CV_LOCATOR)
    rows = [a for a in _rows(log, Q.CLEF_LOCATED, _STAFF, READERS.CV_LOCATOR)
            if a.frame == G.FRAME_HEADER_WINDOW]
    assert [a.reason for a in rows] == [ABSTAIN.NO_STAFF_GEOMETRY]
    assert "error" not in rows[0].detail


def test_key_signature_control_import_ok(empty_header_cells):
    log = Log()
    G.gather_key_signature(log, _pws(), [_cell()], _LOCAL, {})
    rows = _rows(log, Q.KEYSIG_RUN_POSITION, _STAFF, READERS.CV_HEADER)
    assert [a.reason for a in rows] == [ABSTAIN.NO_STAFF_GEOMETRY]
    assert "error" not in rows[0].detail


def test_meter_control_import_ok(empty_header_cells):
    log = Log()
    G.gather_meter(log, _pws(), [_cell()], _LOCAL, {})
    rows = _rows(log, Q.METER_TEMPLATE, _STAFF, READERS.TEMPLATE)
    assert [a.reason for a in rows] == [ABSTAIN.NO_STAFF_GEOMETRY]
    assert "error" not in rows[0].detail


# ── a reader that is genuinely not written keeps NOT_IMPLEMENTED ─────────────


def test_stub_without_error_stays_not_implemented():
    log = Log()
    G._stub_per_staff(log, [_cell()], _LOCAL, Q.CLEF_LOCATED,
                      READERS.CV_LOCATOR, G.FRAME_HEADER_WINDOW, "unwritten")
    G._stub_cv_lines(log, [_cell()], _LOCAL, "unwritten")
    rows = _rows(log, Q.CLEF_LOCATED, _STAFF, READERS.CV_LOCATOR)
    assert [a.reason for a in rows] == [ABSTAIN.NOT_IMPLEMENTED]
    assert "error" not in rows[0].detail
    for q in (Q.BEAM_STROKE, Q.STEM):
        rows = _rows(log, q, _CELL, READERS.CV_LINES)
        assert [a.reason for a in rows] == [ABSTAIN.NOT_IMPLEMENTED]
        assert "error" not in rows[0].detail


def test_margin_labels_without_pdf_path_stays_not_implemented():
    """The one remaining `_stub_per_staff` caller is a precondition (no
    `pdf_path` supplied), not an import: unchanged."""
    log = Log()
    G.gather_margin_labels(log, _pws(), [_cell()], _LOCAL, pdf_path=None)
    rows = _rows(log, Q.MARGIN_LABEL, _STAFF, READERS.TEXT_LAYER)
    assert [a.reason for a in rows] == [ABSTAIN.NOT_IMPLEMENTED]
    assert "error" not in rows[0].detail
