"""ROADMAP 2.306 (cut) -- `OMR_STEM_STUB_CUT`: a stem's stub at a head's side stays stem however short (`stroke_map._is_stem_stub`).

Real pixels only (`data_stem_stub_cut_2_306.npz`, cut from the staff-erased page canvas the page stroke map reads; Brahms p0 windows around
Sean's hand-labelled boxes, Litolff p16 windows around written notes). NO real head-plus-stub piece was found on the six touched pages (Litolff
2, 6, 16; Brahms 0, 4, 5): the flag changes no stroke there, so the positive side has no real control yet -- it is not drawn. What is pinned:
the never side holds with the flag ON (clef, rests, whole rest, a ledger-line head, a half head, a fused stem-and-flag, an oval's rim), the
fused stem-and-flag keeps its upright either way, and the upright test is what holds the Litolff oval rim (the control that fails without it).
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from tools.omr.staged import stroke_map as SM

DATA = pathlib.Path(__file__).with_name("data_stem_stub_cut_2_306.npz")


class _Staff:
    """Five level lines a space apart: only the measured fields read it, never the kinds or the cuts."""
    local = False

    def __init__(self, sp: float):
        self.sp = sp

    def lines_at(self, x, y=None):
        return [i * self.sp for i in range(5)]


def _windows():
    z = np.load(DATA)
    meta = json.loads(str(z["meta"]))
    for name, m in meta.items():
        h, w = m["shape"]
        ink = np.unpackbits(z[name], axis=1)[:, :w].astype(bool)
        yield name, ink, float(m["sp"])


def _map(ink, sp, on, monkeypatch, collect=None):
    monkeypatch.setenv(SM.STEM_STUB_ENV, "1" if on else "0")
    erased = np.where(ink, 0, 255).astype(np.uint8)
    scale = min(1.0, SM.TARGET_SP_PX / sp)
    res = SM.map_strokes(erased, sp, [], erased, staff_override=_Staff(SM.TARGET_SP_PX if scale < 1.0 else sp))
    return {(s.kind, tuple(s.box)) for s in res.strokes}


def test_flag_off_by_default(monkeypatch):
    monkeypatch.delenv(SM.STEM_STUB_ENV, raising=False)
    assert not SM.stem_stub_cut_enabled()
    monkeypatch.setenv(SM.STEM_STUB_ENV, "1")
    assert SM.stem_stub_cut_enabled()


@pytest.mark.parametrize("name", [n for n, _i, _s in _windows()])
def test_never_side_holds_with_the_flag_on(name, monkeypatch):
    """Clef, rests, whole rest, ledger-line head, half head, fused stem-and-flag, an oval's rim: no stroke changes with the flag ON."""
    ink, sp = next((i, s) for n, i, s in _windows() if n == name)
    assert _map(ink, sp, False, monkeypatch) == _map(ink, sp, True, monkeypatch)


def test_fused_stem_and_flag_keeps_its_upright(monkeypatch):
    """Sean's Brahms p0 eighth (stem labelled beside a flag8thDown): the stem is a `vertical` stroke, flag OFF and ON (the brief's
    'no thin upright where the stem is fused to its flag' does not reproduce here: 37 of 37 labelled flagged stems on p0 have one)."""
    ink, sp = next((i, s) for n, i, s in _windows() if n == "brahms_p0_flagged_stem")
    for on in (False, True):
        kinds = [k for k, _b in _map(ink, sp, on, monkeypatch)]
        assert "vertical" in kinds


def test_the_upright_test_holds_the_litolff_oval_rim(monkeypatch):
    """The control that can fail: on Litolff p16 an oval's bottom rim (7 px wide, 2 rows) stands flush with a head the vertical opening
    had cut in two, outside its rows, at the piece's edge -- conditions (1)-(3) pass. Only the upright test refuses it."""
    ink, sp = next((i, s) for n, i, s in _windows() if n == "litolff_p16_ledger_head_rim")
    import cv2
    seen = []
    orig = SM._split_thin_wide

    def spy(m, thin, wide, spx, refused, context):
        nt, tl = cv2.connectedComponents(thin.astype(np.uint8), connectivity=8)
        _nw, wl = cv2.connectedComponents(wide.astype(np.uint8), connectivity=8)
        for i in range(1, nt):
            ys = np.nonzero((tl == i).any(axis=1))[0]
            if (ys[-1] - ys[0] + 1) < SM.STEM_PART_MIN_SPACES * spx:
                seen.append((SM._beside_one_head(tl == i, wl, wide, spx), SM._is_stem_stub(tl == i, wl, wide, spx)))
        return orig(m, thin, wide, spx, refused, context)
    monkeypatch.setattr(SM, "_split_thin_wide", spy)
    _map(ink, sp, True, monkeypatch)
    assert any(beside and not stub for beside, stub in seen), seen
    assert not any(stub for _b, stub in seen)
