"""ROADMAP 2.355 -- the head's own ink is read from the head, not from a stem stub or a fragment beside it (flag `OMR_HEAD_OWN_INK`, OFF).

As a musician says it: a black head is black whatever touches its edge; a half note is hollow even where a line runs along its rim; the stem,
the ledger line and the staff line are not the head. NEVER fill read off the paper between a head and its stem; never a staff line through a
hollow head counted as fill; never a hollow head made black by cleaning its walls away; never "cannot tell" turned into filled or hollow.

Every control is cut from a REAL mark Sean vouched for (rule 7): his judged tiles, his hand-labelled Brahms page 0, the heads he called "easily
seen as noteheads with stems", and marks he said are not heads (lane 2.354 step 0 population, 20261123-night records). The page raster around
each mark is stored whole (every window the reader reads fits inside), and the fixture was checked to read exactly as on the page.
  cause A  black Brahms heads abstaining because the slit counted the paper between the head and its stem  -> filled with the flag ON
  cause B  thin-walled halves whose rim runs along a staff line, trimmed to a fragment                      -> hollow
  cause C  real heads read "too wide" with a slur end or the stem counted in their width                  -> one head, its fill
  control  good hollow heads on a line and in a space, good black heads, a dotted half, halves with a stroke beside them: unchanged
  non-head marks Sean said are not heads: the flag never makes one read as a head where it did not before
"""
import json
import os
import pathlib

import numpy as np
import pytest

from tools.omr.staged import head_ink as HI
from tools.omr.staged.gather import head_interior_white, notehead_ink_under

FIX = pathlib.Path(__file__).parent / "fixtures" / "head_own_ink_2_355"
META = json.loads((FIX / "marks.json").read_text())
ARR = np.load(FIX / "marks.npz")
ONE = ("hollow", "filled")


def _raster(m):
    bits = np.unpackbits(ARR[m["name"]])[: m["shape"][0] * m["shape"][1]].reshape(m["shape"]).astype(bool)
    return np.where(bits, 0, 255).astype(np.uint8)


def _read(m, on):
    old = os.environ.get(HI.OWN_INK_ENV)
    os.environ[HI.OWN_INK_ENV] = "1" if on else "0"
    try:
        g = HI.read_head_ink(_raster(m), m["box"], m["sp"], m["foreign"], head_interior_white, notehead_ink_under)
    finally:
        if old is None:
            os.environ.pop(HI.OWN_INK_ENV, None)
        else:
            os.environ[HI.OWN_INK_ENV] = old
    return None if g is None else (g.get("value") or g.get("not_one_head") or g.get("why"))


def _group(name):
    return [m for m in META if m["group"] == name]


def test_flag_is_off_by_default(monkeypatch):
    monkeypatch.delenv(HI.OWN_INK_ENV, raising=False)
    assert HI.own_ink() is False


@pytest.mark.parametrize("cause", ["A", "B", "C"])
def test_each_cause_has_real_cases(cause):
    ms = _group(cause)
    assert len(ms) >= 6, (cause, len(ms))


@pytest.mark.parametrize("m", [m for m in META if m["group"] in ("A", "B", "C")], ids=lambda m: m["group"] + ":" + m["plate"] + ":" + m["sub"])
def test_failing_case_fails_off_and_reads_right_on(m):
    """Off, the reader does not say one head (the control can fail); on, it says the fill Sean's answer or label gives (a head he called
    "easily seen as a notehead" without naming its value: one head, the fill as the print shows it, `truth` from our look, labelled ours)."""
    off, on = _read(m, False), _read(m, True)
    assert off not in ONE, (m["sub"], off)
    assert on == m["truth"], (m["sub"], off, on, m["truth"])


@pytest.mark.parametrize("m", _group("control"), ids=lambda m: m["plate"] + ":" + m["sub"] + ":" + str(m.get("who"))[:30])
def test_good_heads_keep_their_reading(m):
    """A good hollow head (on a line, in a space, dotted, a stroke beside it) and a good black head read the same with the flag on: never a
    hollow head made black, never a staff line through a hollow head counted as fill."""
    off, on = _read(m, False), _read(m, True)
    assert off == m["truth"] and on == m["truth"], (m["sub"], off, on, m["truth"])


@pytest.mark.parametrize("m", _group("nonhead"), ids=lambda m: m["plate"] + ":" + m["sub"])
def test_non_heads_not_made_worse(m):
    """A mark Sean says is not a head never starts reading as one head with the flag on."""
    off, on = _read(m, False), _read(m, True)
    assert not (off not in ONE and on in ONE), (m["sub"], off, on)


@pytest.mark.parametrize("m", _group("ours"), ids=lambda m: m["plate"] + ":" + m["sub"])
def test_a_hollow_head_is_never_made_black_by_moving_its_box(m):
    """OUR LOOK, not Sean's (a dotted half, Brahms 25/0/8/0/10): where the flag moves the box (a rim carried across its line, a stroke
    left out) the slit read only the rim and said black; a black head's middle is solid, this one's is not -- never read filled."""
    assert _read(m, True) != "filled"


def test_fixtures_match_their_recorded_readings():
    for m in META:
        assert _read(m, False) == m["off"], m["sub"]
        assert _read(m, True) == m["on"], m["sub"]


# ---- the pure pieces ----

def test_slit_without_stem_equals_the_slit():
    """With no stem pixels the head's own slit is 2.148's `rows_share` exactly, on every fixture."""
    for m in META:
        img = _raster(m)
        b = m["box"]
        x0, y0, x1, y1 = (int(round(v)) for v in b)
        ink = img[y0:y1, x0:x1] == 0
        if ink.shape[0] < 4 or ink.shape[1] < 4:
            continue
        ref = head_interior_white(img, (x0, y0, x1 - x0, y1 - y0))["rows_share"]
        got, _n, _g = HI.slit_rows_share(ink, np.zeros_like(ink))
        assert round(got, 4) == ref, m["sub"]


def test_paper_between_head_and_stem_is_not_the_inside():
    """A black oval with its stem beside it and a sliver of paper between them: the sliver counts on the plain slit, not off the stem."""
    ink = np.zeros((20, 20), bool)
    ink[4:16, 6:18] = True
    ink[:, 1:3] = True                          # the stem
    ink[4:16, 3:4] = False                      # paper between stem and head ...
    ink[4:16, 3:6] = False
    stem = np.zeros_like(ink)
    stem[:, 1:3] = ink[:, 1:3]
    plain, _, g0 = HI.slit_rows_share(ink, np.zeros_like(ink))
    own, _, g1 = HI.slit_rows_share(ink, stem)
    assert plain > HI.SLIT_HOLLOW_MIN and own == 0.0 and g0 == 0 and g1 == 3


def test_rim_bridge_never_across_paper():
    """Two runs join only where every gap column holds ink AND had line ink taken out of it; an accidental and its head stand apart on paper."""
    ink = np.zeros((10, 12), bool)
    bare = np.zeros((10, 12), bool)
    ink[:, 0:4] = True
    ink[:, 6:10] = True
    bare[2, :] = True
    assert HI.bridge_rim_on_line([(0, 4), (6, 10)], ink, bare, 5)[1] == 0      # gap columns 4-5 are paper
    ink[6:9, 4:6] = True                                                        # the rim's lower wall runs on under the line
    assert HI.bridge_rim_on_line([(0, 4), (6, 10)], ink, bare, 5) == ([(0, 10)], 1)
    assert HI.bridge_rim_on_line([(0, 4), (6, 10)], ink, bare, 1)[1] == 0      # wider than the gap a rim can leave
