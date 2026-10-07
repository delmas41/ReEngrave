"""ROADMAP 2.57: `OMR_CELL_LINE_FIND` finds the five printed lines in the cell
instead of sliding the recorded comb under a cap.

Synthetic: the printed staff is one whole spacing (20 px) below the recorded
lines, past the 0.75 sp cap, where a capped comb still has four of five rows on
a printed line and stays put (the Litolff defect, 21 bars).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tools.omr import measure_extractor as me
from tools.omr.types import PageImage, PageWithStaves, Staff

W, H, SP = 900, 400, 20
RECORDED = [100, 120, 140, 160, 180]


def _pws(printed_shift: int, extras=()):
    binary = np.full((H, W), 255, dtype=np.uint8)
    for y in RECORDED:
        binary[y + printed_shift - 1:y + printed_shift + 2, 50:850] = 0
    # a slur-like smear above the staff and a stem + head inside it
    binary[60 + printed_shift:66 + printed_shift, 300:520:2] = 0
    binary[110 + printed_shift:170 + printed_shift, 400:402] = 0
    binary[150 + printed_shift:162 + printed_shift, 388:412] = 0
    for e in extras:
        e(binary)
    rgb = np.full((H, W, 3), 255, dtype=np.uint8)
    rgb[binary == 0] = 0
    page = PageImage(pdf_path=Path("s.pdf"), page_index=0, dpi=300, rgb=rgb, binary=binary)
    staff = Staff(page_index=0, staff_index=0, line_ys=list(RECORDED), x_start=50, x_end=850)
    return PageWithStaves(page=page, staves=[staff], barlines=[]), staff


@pytest.fixture
def find_on(monkeypatch):
    monkeypatch.setenv("OMR_CELL_LINE_FIND", "1")


@pytest.mark.parametrize("shift", [20, -20, 22])
def test_off_locks_one_line_over_on_finds_it(shift, monkeypatch):
    pws, staff = _pws(shift)
    monkeypatch.delenv("OMR_CELL_LINE_FIND", raising=False)
    off = me._cell_line_offset(pws, staff, 250, 600)
    assert off is None or abs(off[0] - shift) > 8, off     # the control FAILS here
    monkeypatch.setenv("OMR_CELL_LINE_FIND", "1")
    on = me._cell_line_offset(pws, staff, 250, 600)
    assert on is not None and abs(on[0] - shift) <= 2, on
    assert on[1]["line_grid_found"] is True


def test_a_comb_already_on_five_lines_is_left_alone(find_on):
    pws, staff = _pws(0)
    assert me._cell_line_offset(pws, staff, 250, 600) is None


def test_small_tilt_keeps_the_capped_answer(find_on, monkeypatch):
    pws, staff = _pws(5)
    on = me._cell_line_offset(pws, staff, 250, 600)
    monkeypatch.delenv("OMR_CELL_LINE_FIND", raising=False)
    off = me._cell_line_offset(pws, staff, 250, 600)
    assert on == off and on is not None and abs(on[0] - 5) <= 1


def test_nothing_to_find_falls_back_and_says_so(find_on):
    """A cell with a beam where lines should be: no five lines found, the
    capped rule answers and the provenance carries `line_grid_found: False`."""
    def wipe(b):
        b[90:200, 250:600] = 255
        b[95:105, 250:600] = 0           # one thick beam only
    pws, staff = _pws(5, extras=(wipe,))
    got = me._cell_line_offset(pws, staff, 250, 600)
    assert got is None or got[1].get("line_grid_found") is False


def test_flag_default_off_is_the_old_function(monkeypatch):
    monkeypatch.delenv("OMR_CELL_LINE_FIND", raising=False)
    pws, staff = _pws(20)
    assert me._cell_line_offset(pws, staff, 250, 600) == me._cell_line_offset_capped(pws, staff, 250, 600)
