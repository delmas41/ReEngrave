"""The clef readers' EVIDENCE, as against which of them won.

`staff["clef_source"]` names the winner. It says nothing about the readers that
declined, and this project's most-repeated defect is a number computed at the
moment of a refusal and destroyed by the same expression that refuses. Two such
sites feed `staff["clef_evidence"]`:

* `clef_locator.locate_clef` has taken a `trace` out-parameter since it was
  written, filled it with the branch that ended the call and the geometry of the
  cluster that ended it — and NEITHER pipeline call site passed one, so in
  production the reason was computed and dropped on every staff the locator
  declined.
* the detector's clef argmax in `_detections_for_cell` keeps a running
  `best_clef_conf` and discards it, so a clef won at 0.98 over nothing and one
  won at 0.26 over a 0.25 runner-up were indistinguishable downstream.

⚠️ Every test here was run RED first, with the recording removed, to prove it
exercises the mechanism rather than passing on the shape of an empty dict —
this repo has shipped a test that passed vacuously (the margin-label blob test
asserting on label LENGTH). The wiring tests are the ones that most need it:
an AST assertion that a call site passes an argument fails open if it looks in
the wrong place.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from tools.omr import transcribe as T
from tools.omr.tests.test_clef_locator import (
    blank_page,
    cell_with_c_clef,
    draw_g_clef,
    draw_noteheads,
    make_cell,
)


class _NoDetections:
    """A detector that sees nothing — so the CV locator is reached."""

    def __init__(self, dets=()):
        self._dets = list(dets)

    def detect(self, cell, **kwargs):
        return list(self._dets)


def _run(cell, detector=None, **kwargs):
    """`_detections_for_cell` with an evidence dict attached. Returns it."""
    evidence: dict = {}
    T._detections_for_cell(
        detector or _NoDetections(),
        cell,
        conf_threshold=0.25,
        imgsz=512,
        iou_threshold=0.5,
        agnostic_nms=True,
        active_clef=None,
        active_key_sig={},
        active_time_sig=None,
        read_clef=True,
        clef_evidence=evidence,
        **kwargs,
    )
    return evidence


# ─── the locator's trace reaches the record ────────────────────────────────


class TestLocatorTraceIsRecorded:
    def test_a_located_clef_records_why_it_was_located(self):
        evidence = _run(cell_with_c_clef(4))
        trace = evidence["cv_locator"]
        assert trace["reason"] == "located"
        assert trace["clef"] == "tenor"
        # The geometry the decision was made on, not merely the verdict.
        assert trace["symmetry"] > 0
        assert trace["w_spaces"] > 0 and trace["h_spaces"] > 0

    def test_a_REFUSAL_records_the_branch_that_refused(self):
        """The population that was being lost: the locator says no, and until
        now said nothing about why — including the NUMBER it said no on.

        A G clef in the header reaches the snap and is turned away there, so
        this staff's record now carries the symmetry (0.80) and the size the
        refusal was made on. Those are exactly the quantities
        `benchmarks/omr-clef-geometry/` had to reimplement the locator to see.
        """
        img = blank_page()
        draw_g_clef(img)
        draw_noteheads(img)
        trace = _run(make_cell(img))["cv_locator"]
        assert trace["reason"] == "ambiguous_snap", trace
        assert trace["symmetry"] > 0
        assert trace["w_spaces"] > 0 and trace["h_spaces"] > 0
        assert trace["clusters"], "the geometry it judged, not just the verdict"

    def test_a_refusal_with_nothing_to_measure_says_so(self):
        """Not every refusal has a number behind it, and the record must not
        invent one: a header holding no glyph-sized ink refuses at
        `no_clusters`, with no cluster geometry to report."""
        img = blank_page()
        draw_noteheads(img)          # note ink, all of it past the header strip
        trace = _run(make_cell(img))["cv_locator"]
        assert trace["reason"] == "no_clusters"
        assert trace["clusters"] == []
        assert "symmetry" not in trace

    def test_the_crop_it_read_is_named(self):
        """A rejecting branch is about INK, and the header cell and the measure
        cell do not hold the same ink — so which one was read is part of the
        reading."""
        evidence = _run(cell_with_c_clef(3))
        assert evidence["cv_locator"]["cell"] == "measure"
        header = cell_with_c_clef(3)
        evidence = _run(cell_with_c_clef(3), header_cell=header,
                        prefer_header=True)
        assert evidence["cv_locator"]["cell"] == "header"

    def test_nothing_is_recorded_when_the_locator_is_off(self):
        """Recording must not manufacture a reading. With the locator disabled
        there is no refusal to record, and the key is absent rather than empty.
        """
        evidence = _run(cell_with_c_clef(4), locate_c_clefs=False)
        assert "cv_locator" not in evidence

    def test_the_locator_does_not_run_when_the_detector_already_read_a_clef(self):
        """The gate is unchanged: the locator only ever spoke where
        `clef_source` was still None, and recording must not widen its reach."""
        cell = cell_with_c_clef(4)
        evidence = _run(cell, detector=_NoDetections([_clef_detection(cell)]))
        assert "cv_locator" not in evidence


def _clef_detection(cell, *, name="clefG", conf=0.9, y=118, h=88):
    """A detector output the clef pass will resolve — a G clef straddling the
    staff's second line from the bottom, which is where one belongs."""
    from tools.omr.template_matcher import SymbolDetection

    return SymbolDetection(
        cell=cell,
        smufl_name=name,
        category="clef",
        x_canonical=22,
        y_canonical=y,
        width_canonical=40,
        height_canonical=h,
        confidence=conf,
    )


# ─── the wiring, asserted against the source ───────────────────────────────


class TestBothCallSitesPassATrace:
    """`locate_clef` filling a trace nobody passes is the exact bug this fixes,
    so the test is on the CALL SITES and not on the recorder.

    Run RED by deleting `trace=` from either call — verified for both.
    """

    def test_every_locate_clef_call_in_transcribe_passes_a_trace(self):
        source = Path(inspect.getfile(T)).read_text()
        tree = ast.parse(source)
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "locate_clef"
        ]
        assert len(calls) == 2, (
            "expected the two known call sites — the measure loop's and the "
            f"header pre-pass's — found {len(calls)}"
        )
        for call in calls:
            kwargs = {kw.arg for kw in call.keywords}
            assert "trace" in kwargs, (
                f"locate_clef at line {call.lineno} discards its own reasoning"
            )
