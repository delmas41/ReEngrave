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


# ROADMAP 2.312 r3 -- the Brahms p0 half note hanging under its fourth ledger (glyph/0/0/5/5/6), read right (17) by the box count;
# r2's ink count lost it: the shared trim took the top of the oval, fused to the ledger, as line pixels, so the ink found was the
# head's lower part and no line touched it. Where the ink finds no line, the box reading stands (fixture: r3_fixture_brahms.py).
BRA = np.load(Path(__file__).parent / "data_ledger_count_to_ink_2_312_brahms.npz")


def _read_bra():
    return FH.read_absolute_position(BRA["b1_gray"], [float(v) for v in BRA["b1_lines"]],
                                     tuple(float(v) for v in BRA["b1_box"]), "brahms/p0/b1", [], [])


@pytest.mark.parametrize("on", ["0", "1"])
def test_brahms_hanging_half_note_stays_read(on, monkeypatch):
    monkeypatch.setenv(lg.LEDGER_COUNT_TO_INK_ENV, on)
    pos, reason = _read_bra()
    assert pos == int(BRA["b1_truth"]), (on, pos, reason)


def test_brahms_control_ink_alone_finds_no_line():
    """The control can fail: the ink alone (r2's path, no box fallback) finds only part of the head and no line at it."""
    gray = BRA["b1_gray"]
    box = tuple(float(v) for v in BRA["b1_box"])
    lines = [float(v) for v in BRA["b1_lines"]]
    sp = (lines[-1] - lines[0]) / 4.0
    ink = lg.head_ink_box(gray, box, sp, None, 1.0)
    assert ink["ok"] and (ink["box"][3] - ink["box"][1]) < 0.7 * sp, ink
    y0 = int(3485.2 - 3 * (3614.8 - 3485.2) / 4.0)      # the crop's top on the page (r3_fixture_brahms.py)
    rungs = [v - y0 for v in (3645.5, 3677.5, 3706.5, 3737.0)]      # the walk's four ledgers in the real run (r2 re-read)
    ln = lg.find_note_line_on_ink(gray, box, ink["box"], lines[-1], 1.0, sp, rungs)
    assert not ln["ok"], ln
