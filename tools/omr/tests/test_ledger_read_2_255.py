"""ROADMAP 2.255 (STAGED GATHER, flag OMR_LEDGER_READ, default OFF): the ledger READ.

1. `measure_ledger_rungs(outline_free_walk=True)`: the head's own outline row is taken out of the walk's candidates
   before the walk, so a ledger a few px past it is not lost (Litolff `glyph/6/1/7/11/0`).
2. `snap_rung_in_gap`: a ledger hidden in a wide gap is found by its thin flat ends (both sides of the column) or as
   one level stroke; a slanted stroke touching one side is not one (Brahms `glyph/5/0/6/6/0`).
3. The flag is read at call time, allow-list only.
"""
import numpy as np

from tools.omr.annotate import far_head_reader as FH
from tools.omr.annotate import ledger_grid as lg

SP = 16


def blank(h=400, w=300):
    return np.full((h, w), 255, dtype=np.uint8)


def hline(img, y, x0, x1, t=3):
    img[y - t // 2:y - t // 2 + t, x0:x1] = 0


def staff(img, top=300, x0=0, x1=300):
    for i in range(5):
        hline(img, top + i * SP, x0, x1)
    return [float(top + i * SP) for i in range(5)]


def test_flag_allow_list(monkeypatch):
    monkeypatch.delenv(FH.LEDGER_READ_ENV, raising=False)
    assert not FH.ledger_read_enabled()
    for v in ("0", "false", "off", "", "2"):
        monkeypatch.setenv(FH.LEDGER_READ_ENV, v)
        assert not FH.ledger_read_enabled()
    for v in ("1", "true", "yes", "on", "ON"):
        monkeypatch.setenv(FH.LEDGER_READ_ENV, v)
        assert FH.ledger_read_enabled()


def test_flat_stroke_level_vs_slanted():
    img = blank()
    hline(img, 100, 120, 160)                       # a level ledger, 2.5 sp long
    for i, x in enumerate(range(120, 160)):          # a slanted stroke (a tie's end)
        img[200 + i // 3:203 + i // 3, x] = 0
    assert lg.flat_stroke_on_row(img, 100.0, (130.0, 150.0), SP)
    assert not lg.flat_stroke_on_row(img, 206.0, (130.0, 150.0), SP)
    assert not lg.flat_stroke_on_row(img, 150.0, (130.0, 150.0), SP)   # white


def test_snap_finds_a_ledger_behind_a_chord_mate():
    img = blank()
    # gap from y=200 to y=234 (2.1 sp): a head blob in the middle hides the ledger, only its ends jut out both sides
    img[210:224, 130:152] = 0                       # the chord-mate head's body
    hline(img, 217, 125, 157)                       # the ledger through it: 5 px ends each side
    got = lg.snap_rung_in_gap(img, 200.0, 234.0, -1.0, (130.0, 152.0), SP)
    assert got is not None and abs(got - 217) <= 1.5


def test_snap_refuses_a_slanted_stroke_on_one_side():
    img = blank()
    for i, x in enumerate(range(100, 131)):          # a slanted stroke ending at the column's left edge
        img[214 + i // 4:217 + i // 4, x] = 0
    assert lg.snap_rung_in_gap(img, 200.0, 240.0, -1.0, (130.0, 152.0), SP) is None


def test_snap_refuses_a_split_that_is_not_one_pitch_each():
    img = blank()
    hline(img, 224, 120, 162)                       # a level line half-way across a 3-pitch gap
    assert lg.snap_rung_in_gap(img, 200.0, 248.0, -1.0, (130.0, 152.0), SP) is None


def _head_with_ledgers():
    """A head above the staff; ledger 1 at 1.3 sp out, ledger 2 SHORT just under the head, and the head's own flat
    bottom outline row (as wide as the box) a few px NEARER the expected pitch than ledger 2 (the Litolff shape:
    `glyph/6/1/7/11/0`, outline 3016 vs ledger 3025, expected 3020)."""
    img = blank()
    lines = staff(img, top=300)
    x0, x1 = 130, 160                               # head box x
    hline(img, 279, 126, 158)                       # ledger 1 (21 px = 1.3 sp out)
    hline(img, 265, 126, 158)                       # ledger 2 (14 px further)
    img[240:256, x0 + 4:x1 - 4] = 0                 # the head body ...
    img[256:259, x0:x1] = 0                         # ... its flat bottom outline row, box-wide, at the expected pitch
    return img, lines, (float(x0), 239.0, float(x1), 259.0)


def test_outline_free_walk_off_is_the_default():
    img, lines, box = _head_with_ledgers()
    kw = dict(head_y=(box[1] + box[3]) / 2, head_box_x=(box[0], box[2]), collapse_edges_box=box, outline_margin_px=2.0)
    a = lg.measure_ledger_rungs(img, lines, (box[0] + box[2]) / 2, **kw)
    b = lg.measure_ledger_rungs(img, lines, (box[0] + box[2]) / 2, outline_free_walk=False, **kw)
    assert a == b


def test_outline_free_walk_never_loses_a_rung_the_plain_walk_keeps():
    img, lines, box = _head_with_ledgers()
    kw = dict(head_y=(box[1] + box[3]) / 2, head_box_x=(box[0], box[2]), collapse_edges_box=box, outline_margin_px=2.0)
    off = lg.measure_ledger_rungs(img, lines, (box[0] + box[2]) / 2, **kw)["above"]
    on = lg.measure_ledger_rungs(img, lines, (box[0] + box[2]) / 2, outline_free_walk=True, **kw)["above"]
    assert all(any(abs(r - o) <= 1.0 for o in on) for r in off)
    assert any(abs(r - 265) <= 2 for r in on)       # ledger 2 is found
    assert not any(abs(r - 265) <= 2 for r in off)  # the plain walk stepped onto the outline and lost it
