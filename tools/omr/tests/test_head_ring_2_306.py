"""ROADMAP 2.306 -- A HOLLOW NOTEHEAD'S OUTLINE COVERS THE WHOLE RING. STAGED GATHER, `head_extent.strip_line_rows` (via `ink_extent`), riding the
page stem reader's flag `OMR_PAGE_STEMS` (default OFF).

The rule, as a musician says it: a notehead is its whole oval, the ring and the hole together; a hollow head is as wide as a filled one. NEVER the
stem, an accidental, a dot or the other head of a second in the head's width; never wider than the head's own ink over blank paper.

Real pixels (CLAUDE.md rule 7), `data_head_ring_2_306.npz`, cut by benchmarks/page-ledger-2026-11/2306/r19_ring_fixture.py from Brahms 317803
page 0 (Sean's swept, hand-labelled page, data/hand-truth/pages/imslp317803/0.json) around the detector boxes of written notes:
  * `ring`: Sean's half notes beside a staff line whose outline the old reading cut to one side of the ring (the run through the head's
    centre column stops at the hole) -- they must reach the full ring, and are cut with the rule off;
  * `second`: two black heads of a second fused on the page; `slash`: half notes with a tremolo slash on their stem; `ledger`: black heads
    whose line rows are stripped -- none may move.
The 2.327 judged-head tiles (Litolff, `data_head_own_ink_2_327.npz`) must not move either."""
import os
import pathlib

import numpy as np
import pytest

from tools.omr.staged import head_extent as HE

HERE = pathlib.Path(__file__).parent
FX = np.load(HERE / "data_head_ring_2_306.npz")
FX327 = np.load(HERE / "data_head_own_ink_2_327.npz")


def _tile(fx, key):
    shape = tuple(int(v) for v in fx[key + "_shape"])
    ink = np.unpackbits(fx[key + "_ink"])[: shape[0] * shape[1]].reshape(shape).astype(bool)
    return np.where(ink, 0, 255).astype(np.uint8), [float(v) for v in fx[key + "_box"]], float(fx[key + "_sp"])


def _keys(kind):
    return sorted(k[: -len("_kind")] for k in FX.files if k.endswith("_kind") and str(FX[k]) == kind)


def _extent(fx, key, on):
    page, box, sp = _tile(fx, key)
    old = os.environ.get(HE.RING_WIDTH_ENV)
    try:
        if on:
            os.environ[HE.RING_WIDTH_ENV] = "1"
        else:
            os.environ.pop(HE.RING_WIDTH_ENV, None)
        return HE.ink_extent(page, box, sp), page, box, sp
    finally:
        if old is None:
            os.environ.pop(HE.RING_WIDTH_ENV, None)
        else:
            os.environ[HE.RING_WIDTH_ENV] = old


@pytest.mark.parametrize("key", _keys("ring"))
def test_a_hollow_head_is_as_wide_as_its_whole_ring(key):
    got, page, box, sp = _extent(FX, key, True)
    x0, y0, x1, y1 = got["extent"]
    assert got["why"] is None, got
    assert (x1 - x0) >= 1.2 * sp, (key, got)                     # a head's width, not one side of its ring
    assert x0 <= box[0] + 2 and x1 >= box[2] - 2, (key, got)     # the whole oval the detector boxed ...
    assert x0 >= box[0] - 2 and x1 <= box[2] + 3, (key, got)     # ... and nothing beside it
    # both sides of the ring are inside the outline: ink left and right of the hole on the middle row
    ym = int((y0 + y1) / 2)
    row = page[ym, int(x0):int(x1) + 1] == 0
    cx = len(row) // 2
    assert row[:cx].any() and row[cx:].any() and not row[cx - 2:cx + 3].all(), key


@pytest.mark.parametrize("key", _keys("ring"))
def test_CONTROL_rule_off_the_ring_is_cut_to_one_side(key):
    got, _, box, sp = _extent(FX, key, False)
    x0, _, x1, _ = got["extent"]
    assert (x1 - x0) < 1.05 * sp and (x0 > box[0] + 3 or x1 < box[2] - 3), (key, got)


@pytest.mark.parametrize("key", _keys("second") + _keys("slash") + _keys("ledger"))
def test_NEVER_a_second_a_slashed_head_or_a_ledger_head_moves(key):
    on, _, _, _ = _extent(FX, key, True)
    off, _, _, _ = _extent(FX, key, False)
    assert on["extent"] == off["extent"] and on["why"] == off["why"], (key, on, off)


def test_NEVER_the_second_takes_its_neighbours_head():
    """The two black heads of a fused second: each one's outline holds its own box centre and never the other's."""
    a, b = _keys("second")
    for me, other in ((a, b), (b, a)):
        got, _, box, _ = _extent(FX, me, True)
        # the other head's box centre in this crop's frame (each crop is cut around its own head)
        ob = [float(v) for v in FX[other + "_box"]]
        dx = float(FX[other + "_origin"][0]) - float(FX[me + "_origin"][0])
        ocx = (ob[0] + ob[2]) / 2.0 + dx
        x0, _, x1, _ = got["extent"]
        assert x0 <= (box[0] + box[2]) / 2.0 <= x1, (me, got)
        assert not (x0 <= ocx <= x1), (me, got, ocx)


@pytest.mark.parametrize("key", sorted({k.rsplit("_", 1)[0] for k in FX327.files if k.endswith("_box")}))
def test_the_2_327_judged_head_tiles_do_not_move(key):
    on, _, _, _ = _extent(FX327, key, True)
    off, _, _, _ = _extent(FX327, key, False)
    assert on["extent"] == off["extent"] and on["why"] == off["why"], (key, on, off)
