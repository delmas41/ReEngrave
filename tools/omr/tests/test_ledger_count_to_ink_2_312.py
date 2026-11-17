"""ROADMAP 2.312 r2 -- the ledger count to the head's own ink (`OMR_LEDGER_COUNT_TO_INK`), on the REAL page pixels of Sean's judged
2.311 ledger tiles (CLAUDE rule 7; fixture cut by benchmarks/ledger-count-2026-11/r2_fixture.py; his answers in
benchmarks/note-loss-funnel-2026-11/answers-2.311-ledger.json). STAGED GATHER (`far_head_reader.read_absolute_position`).

Tiles 2, 3, 8: the box reading refuses (the box edge misses the line the head sits on); counted to the ink they read as Sean read them.
Tiles 1, 4, 5, 6, 9: already right by count, stay right. Tile 11 (C2, a chord mate hides ledger 1) is not here: it stays unread.
"""
from pathlib import Path

import numpy as np
import pytest

from tools.omr.annotate import far_head_reader as FH
from tools.omr.annotate import ledger_grid as lg

DATA = np.load(Path(__file__).parent / "data_ledger_count_to_ink_2_312.npz")
TILES = sorted({int(k.split("_")[0][1:]) for k in DATA.files})


def _read(t):
    return FH.read_absolute_position(DATA["t%d_gray" % t], [float(v) for v in DATA["t%d_lines" % t]],
                                     tuple(float(v) for v in DATA["t%d_box" % t]), "tile/%d" % t, [], [])


@pytest.mark.parametrize("t", TILES)
def test_on_reads_as_sean_read(t, monkeypatch):
    monkeypatch.setenv(lg.LEDGER_COUNT_TO_INK_ENV, "1")
    pos, reason = _read(t)
    assert pos == int(DATA["t%d_sean" % t]), (t, pos, reason)


def test_control_fails_off(monkeypatch):
    """The control can fail: with the flag OFF the box reading refuses tiles 2, 3 and 8."""
    monkeypatch.delenv(lg.LEDGER_COUNT_TO_INK_ENV, raising=False)
    refused = [t for t in TILES if _read(t)[0] is None]
    assert {2, 3, 8} <= set(refused), refused


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv(lg.LEDGER_COUNT_TO_INK_ENV, raising=False)
    assert not lg.count_to_ink_enabled()
