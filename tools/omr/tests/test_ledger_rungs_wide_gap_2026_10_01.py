"""lane-ledger-rungs (2026-10-01) — three fixes to `measure_ledger_rungs`
(`tools/omr/annotate/ledger_grid.py`), all from Sean's reading of the
15-head rung sheet (DECISIONS 2026-10-01):

  (a) the walk must not stop at an unusually wide gap between two hand-
      drawn ledgers while the head it is reading FOR is still farther out
      (`glyph/3/0/0/1/2`: "There is a larger space between the lower
      ledger lines and the one right underneath the note").
  (b) a head in the first space just outside the staff (-1 or 9 half-steps)
      is ON-STAFF — no ledger read applies there at all
      (`glyph/3/0/1/2/0`: "there is no ledger line... should probably be
      treated as a note on the staff").
  (c) a band that is long but lopsided — most of its length on one side
      of the probed head, barely touching the other — is not a ledger
      drawn THROUGH that head and must not be counted ("it should have a
      line that extends on either side of the notehead").

MEASUREMENT-ONLY module (`tools/omr/annotate/ledger_grid.py` is a stand-
alone CV reader, not STAGED's own production ledger reader
`gather._observe_ledger_rung_ink`/`ownership.py` — no product-path default
is touched here). Fast tier: no `library/`, no weights, no PDFs.
"""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate.ledger_grid import (  # noqa: E402
    _walk_ladder,
    far_head_needs_ledger_read,
    measure_ledger_rungs,
)

YS = [300, 400, 500, 600, 700]  # spacing 100, "above" edge = 300


# ─────────────────────────────────────────────────────────────────────────
# (a) do not stop at a wide gap while the head is still farther out
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_wide_gap_without_a_target_still_stops_old_behaviour() -> None:
    """Control: with no target, the walk keeps its old, unchanged shape —
    a gap this wide (150 vs the window's 135 cap) is simply the end of the
    ladder, exactly as before this fix."""
    bands = [200.0, 50.0]  # 100 then a 150 gap
    assert _walk_ladder(300.0, -1.0, bands, 100.0) == [200.0]


@pytest.mark.omr_annotate
def test_wide_gap_is_crossed_when_the_head_sits_beyond_it() -> None:
    """RED before the fix: the walk stopped at [200.0] and never reached
    the rung at 50.0, even though the head it is reading for (target_y)
    sits right there. GREEN after: the window widens just enough to catch
    it, one rung at a time."""
    bands = [200.0, 50.0]
    rungs = _walk_ladder(300.0, -1.0, bands, 100.0, target_y=50.0)
    assert rungs == [200.0, 50.0]


@pytest.mark.omr_annotate
def test_widening_never_reaches_past_a_head_with_no_rung_there() -> None:
    """The widened window is capped at the head's own distance plus a
    little slack — it must not go on inventing rungs far beyond a head
    that has none near it at all."""
    bands = [200.0, -400.0]  # the second band is WAY past any real target
    rungs = _walk_ladder(300.0, -1.0, bands, 100.0, target_y=50.0)
    assert rungs == [200.0]  # the far band is never reached


@pytest.mark.omr_annotate
def test_wide_gap_reader_finds_the_through_head_rung(monkeypatch=None) -> None:
    """End-to-end on a synthetic cell: a staff, a normally-spaced first
    ledger, then an unusually wide gap to the second ledger — which is
    the one the head sits on. `measure_ledger_rungs` must reach it when
    told where the head is."""
    img = np.full((800, 300), 255, dtype=np.uint8)
    for ly in YS:
        img[ly - 2: ly + 3, 10:290] = 0
    # First ledger at the normal pitch (100 above the top line, y=200).
    img[198:203, 70:231] = 0
    # Second ledger an unusually wide 150px above THAT (y=50), well past
    # WALK_WINDOW's 135px cap from a 100px anchor pitch, with stubs on
    # both sides of the probe column (x=150).
    img[48:53, 70:231] = 0

    without_target = measure_ledger_rungs(img, YS, 150.0)
    assert without_target["above"] == pytest.approx([200.0], abs=2)

    with_target = measure_ledger_rungs(img, YS, 150.0, head_y=50.0)
    assert len(with_target["above"]) == 2
    assert with_target["above"][0] == pytest.approx(200.0, abs=2)
    assert with_target["above"][1] == pytest.approx(50.0, abs=2)


# ─────────────────────────────────────────────────────────────────────────
# (b) the first space outside the staff is ON-STAFF, no ledger read
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_first_space_outside_the_staff_needs_no_ledger_read() -> None:
    assert far_head_needs_ledger_read(-1) is False
    assert far_head_needs_ledger_read(9) is False


@pytest.mark.omr_annotate
def test_first_ledger_line_and_beyond_does_need_a_read() -> None:
    assert far_head_needs_ledger_read(-2) is True
    assert far_head_needs_ledger_read(10) is True


@pytest.mark.omr_annotate
def test_on_staff_positions_are_unaffected() -> None:
    for pos in range(0, 9):
        assert far_head_needs_ledger_read(pos) is False


# ─────────────────────────────────────────────────────────────────────────
# (c) a through-head rung counts only with stubs on BOTH sides
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_through_head_rung_with_stubs_both_sides_is_counted() -> None:
    """A clean rung at one ledger spacing out, drawn with ink on both
    sides of the probe column — the ordinary, correct case."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for ly in YS[:2]:  # just need a 2-line "staff" for spacing
        img[ly - 2: ly + 3, 10:290] = 0
    # A rung 100px above the first line (y=198), spanning well past the
    # probe column (x=150) on both sides.
    img[198:203, 60:241] = 0
    out = measure_ledger_rungs(img, [300, 400], 150.0)
    assert out["above"] == pytest.approx([200.0], abs=3)


@pytest.mark.omr_annotate
def test_lopsided_band_touching_only_one_side_is_refused() -> None:
    """Same y, same total span length as the control above, but almost
    all of it sits to the LEFT of the probe column — the band barely
    reaches past x=150 on the right. This is not a ledger drawn through
    the head at x=150 and must not be read as one."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for ly in YS[:2]:
        img[ly - 2: ly + 3, 10:290] = 0
    # A long span, but almost entirely left of the probe column (x=150):
    # it only just crosses onto the right side by 10px, well under the
    # required stub.
    img[198:203, 0:160] = 0
    out = measure_ledger_rungs(img, [300, 400], 150.0)
    assert out["above"] == []


@pytest.mark.omr_annotate
def test_evenly_spaced_ledgers_unchanged_control() -> None:
    """Regression control: a normal, evenly spaced ladder (no wide gap,
    no target needed) reads exactly as it always did."""
    img = np.full((800, 300), 255, dtype=np.uint8)
    for ly in YS:
        img[ly - 2: ly + 3, 10:290] = 0
    img[198:203, 70:231] = 0
    img[98:103, 70:231] = 0
    out_before = measure_ledger_rungs(img, YS, 150.0)
    out_after = measure_ledger_rungs(img, YS, 150.0, head_y=100.0)
    assert out_before["above"] == pytest.approx([200.0, 100.0], abs=2)
    assert out_after["above"] == out_before["above"]
