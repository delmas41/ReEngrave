"""lane-ledger-template-centre (2026-10-04): the template centre reaches the
through-the-middle probe, and None leaves the reader's output identical.

The probe-level `head_center_y` is covered by
test_ledger_head_center_input_2026_10_04.py; this pins the READER-level
wiring (`reader_absolute_position(head_center_y=...)` -> `measure_ledger_rungs`
-> the probe) and the arm gate used by the scorer. Synthetic page; no record.
The wiring existed on the base (lane-ledger-r8-main), so there is no RED
against an unrepaired tree -- the control is the first test, which fails if
the centre is dropped on the way.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

BENCH = Path(__file__).resolve().parents[3] / "benchmarks" / "omr-local-staff-2026-09"
sys.path.insert(0, str(BENCH))

from tools.omr.annotate import ledger_grid as lg  # noqa: E402


def _reader():
    import score_truth_set_rungs as score
    return score.reader_absolute_position


def _page_and_lines():
    img = np.full((600, 400), 255, dtype=np.uint8)
    lines = [400.0, 420.0, 440.0, 460.0, 480.0]   # spacing 20
    for y in lines:
        img[int(y):int(y) + 2, :] = 0
    return img, lines


@pytest.mark.omr_annotate
def test_reader_forwards_head_center_y_to_the_ledger_walk(monkeypatch) -> None:
    seen = []
    real = lg.measure_ledger_rungs

    def spy(*a, **k):
        seen.append(k.get("head_center_y"))
        return real(*a, **k)

    monkeypatch.setattr(lg, "measure_ledger_rungs", spy)
    img, lines = _page_and_lines()
    box = (180.0, 360.0, 206.0, 380.0)
    _reader()(img, lines, box, "glyph/x", [], four_causes_cd=True, head_center_y=371.5)
    _reader()(img, lines, box, "glyph/x", [], four_causes_cd=True)
    assert seen == [371.5, None]


@pytest.mark.omr_annotate
def test_none_is_identical_to_omitting_it() -> None:
    img, lines = _page_and_lines()
    box = (180.0, 360.0, 206.0, 380.0)
    a = _reader()(img, lines, box, "glyph/x", [], four_causes_cd=True, head_center_y=None)
    b = _reader()(img, lines, box, "glyph/x", [], four_causes_cd=True)
    assert a == b


@pytest.mark.omr_annotate
def test_arm_gate_uses_the_template_centre_only_where_stated() -> None:
    import score_template_centre as stc
    import template_centre as tc
    fit_ok = dict(tmpl_cy=10.0, trusted=True)
    fit_bad = dict(tmpl_cy=20.0, trusted=False)
    census = dict(subject=tc.CENSUS_9[0])
    other = dict(subject="glyph/9/9/9/9/9")
    assert stc.centre_for("F0", other, fit_ok) is None
    assert stc.centre_for("F1", other, fit_bad) == 20.0           # every head
    assert stc.centre_for("F2", other, fit_ok) == 10.0
    assert stc.centre_for("F2", other, fit_bad) is None           # untrusted fit refused
    assert stc.centre_for("F3", census, fit_bad) == 20.0
    assert stc.centre_for("F3", other, fit_ok) is None
    assert tc.GATE_IOU_MIN == 0.70 and tc.GATE_OFFSET_MAX_SP == 0.15
