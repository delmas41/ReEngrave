"""ROADMAP 2.306 (waist) -- `OMR_STACK_TWO_HEADS`: two filled heads a third apart on one stem, fused into one block with no neck, are cut
where the two ovals meet (`stroke_map._two_heads_row`, read in `_cut_stack` when no neck is found).

Real pixels only (`data_stack_two_heads_2_306.npz`, cut from the staff-erased page canvas the page stroke map reads). Positive: four Litolff
pairs under written notes (p16 C5/E5 and B3/C4, p6 A3/C4 with ledger stubs, p16 G5/B5) and the Brahms p0 pair Sean labelled as two heads.
Never: Sean's tile 3 (Litolff glyph/6/1/8/11, "two half notes with a tremolo slash ... a sharp and a natural"), his tile 2 (glyph/2/0/7/4,
"three quarter notes with a half note on top"), one large head on ledger ink (p16 D6), one head with an accidental beside it (p6 A3), F-clef
bodies (p16), a bold letter (Brahms p5).
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from tools.omr.staged import stroke_map as SM

DATA = pathlib.Path(__file__).with_name("data_stack_two_heads_2_306.npz")
PAIRS = ["litolff_p16_pair_C5_E5", "litolff_p16_pair_B3_C4", "litolff_p6_pair_A3_C4_ledgers", "litolff_p16_pair_G5_B5",
         "brahms_p0_pair_hand_labelled"]
NEVER = ["litolff_p6_tile3_slashed_halves_sharp_natural", "litolff_p2_tile2_four_heads", "litolff_p16_large_head_D6",
         "litolff_p6_head_with_accidental_A3", "litolff_p16_f_clef", "brahms_p5_bold_letter"]


class _Staff:
    """Five level lines a space apart: only the measured fields read it, never the kinds or the cuts."""
    local = False

    def __init__(self, sp: float):
        self.sp = sp

    def lines_at(self, x, y=None):
        return [i * self.sp for i in range(5)]


def _window(name):
    z = np.load(DATA)
    m = json.loads(str(z["meta"]))[name]
    h, w = m["shape"]
    return np.unpackbits(z[name], axis=1)[:, :w].astype(bool), float(m["sp"])


def _map(name, on, monkeypatch):
    monkeypatch.setenv(SM.STACK_TWO_HEADS_ENV, "1" if on else "0")
    ink, sp = _window(name)
    erased = np.where(ink, 0, 255).astype(np.uint8)
    scale = min(1.0, SM.TARGET_SP_PX / sp)
    return SM.map_strokes(erased, sp, [], erased, staff_override=_Staff(SM.TARGET_SP_PX if scale < 1.0 else sp)), sp


def _head_blobs(res, sp):
    """Blobs at least a head wide (the head parts), as (w_sp, h_sp)."""
    return [(s.box[2] / sp, s.box[3] / sp) for s in res.strokes if s.kind == "blob" and s.box[2] / sp >= SM.PAIR_MIN_W_SP]


def test_flag_off_by_default(monkeypatch):
    monkeypatch.delenv(SM.STACK_TWO_HEADS_ENV, raising=False)
    assert not SM.stack_two_heads_enabled()
    monkeypatch.setenv(SM.STACK_TWO_HEADS_ENV, "1")
    assert SM.stack_two_heads_enabled()


@pytest.mark.parametrize("name", PAIRS)
def test_a_fused_pair_is_two_heads_only_with_the_flag(name, monkeypatch):
    """OFF: the pair is ONE block taller than a head (the head claim refuses it: neither head claims ink). ON: two head-sized blobs, each
    no taller than one head (`page_heads.CLAIM_MAX_H_SP` 1.6), the halved count filed."""
    off, sp = _map(name, False, monkeypatch)
    tall = [b for b in _head_blobs(off, sp) if SM.PAIR_MIN_H_SP <= b[1] <= SM.PAIR_MAX_H_SP]
    assert len(tall) == 1, _head_blobs(off, sp)
    on, sp = _map(name, True, monkeypatch)
    assert on.split_refused.get(SM.STACK_HALVED) == 1
    assert not [b for b in _head_blobs(on, sp) if SM.PAIR_MIN_H_SP <= b[1] <= SM.PAIR_MAX_H_SP], _head_blobs(on, sp)
    halves = [b for b in _head_blobs(on, sp) if b not in _head_blobs(off, sp)]
    assert len(halves) == 2 and all(0.8 <= h <= 1.6 for _w, h in halves), halves


@pytest.mark.parametrize("name", NEVER)
def test_never_side_holds_with_the_flag_on(name, monkeypatch):
    off, _sp = _map(name, False, monkeypatch)
    on, _sp = _map(name, True, monkeypatch)
    assert {(s.kind, tuple(s.box)) for s in off.strokes} == {(s.kind, tuple(s.box)) for s in on.strokes}
    assert SM.STACK_HALVED not in on.split_refused


@pytest.mark.parametrize("name, guards", [("litolff_p6_tile3_slashed_halves_sharp_natural", ("PAIR_STEM_MIN_SP",)),
                                          ("brahms_p5_bold_letter", ("PAIR_STEM_MIN_SP",))])
def test_the_guard_is_what_holds_it(name, guards, monkeypatch):
    """The controls that can fail: without the stem test the sharp's body (tile 3) and the letter's bar are cut as two heads. (The F-clef
    bodies the head-width floor held on the whole p16 canvas do not reach `_cut_stack` in a window; that floor is pinned by the pure test.)"""
    for g in guards[:-1]:
        monkeypatch.setattr(SM, g, 0.0)
        on, _sp = _map(name, True, monkeypatch)
        assert SM.STACK_HALVED not in on.split_refused
    monkeypatch.setattr(SM, guards[-1], 0.0)
    on, _sp = _map(name, True, monkeypatch)
    assert on.split_refused.get(SM.STACK_HALVED, 0) >= 1


def test_two_heads_row_pure():
    """A solid block two heads tall is cut at its middle; a block one head plus a stub tall, a narrow one, or one with white inside is not."""
    sp = 16.0
    block = np.ones((38, 21), bool)
    assert SM._two_heads_row(block, block, sp) in range(16, 22)
    assert SM._two_heads_row(np.ones((30, 21), bool), np.ones((30, 21), bool), sp) is None       # 1.9 sp: one head with ink fused
    assert SM._two_heads_row(np.ones((38, 12), bool), np.ones((38, 12), bool), sp) is None       # 0.75 sp wide: a clef's body
    ring = block.copy()
    ring[6:32, 5:16] = False
    assert SM._two_heads_row(ring, ring, sp) is None                                              # hollow inside
