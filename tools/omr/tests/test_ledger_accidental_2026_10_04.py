"""lane-ledger-accidental (2026-10-04, Sean on tiles 5/6 of the 10-wrong sheet).

Two default-OFF rules, both found by tracing the real tiles
(`benchmarks/omr-local-staff-2026-09/FINDINGS.md`, "lane-ledger-accidental"):

  * `exclusion_rules(connected=True)`: a neighbouring head's row is kept as
    "a ledger continuing past it" only where the ink beyond its box is
    CONNECTED to the head's own ink (Sean 10-01: ink separated from a head by
    a white gap -- an accidental -- is never a ledger stub). Tile
    `glyph/3/0/0/7/1`: accidental ink 5 px left of the lower head's box, with
    a white gap, supplied the "left side" of a false rung.
  * `derive_far_head_step(drop_rungs_beyond_head=True)`: a rung beyond the
    head's own far edge is another head's ledger, never counted for it. Tile
    `glyph/3/0/0/7/2`: a head ON ledger 1 was credited with the stack above.

Synthetic arrays only (no record read).
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate import ledger_grid as lg  # noqa: E402
from tools.omr.annotate.ledger_grid import (  # noqa: E402
    _exclude_other_heads_ink,
    derive_far_head_step,
    exclusion_rules,
)

SP = 20.0
SIGN = -1.0
EDGE_Y = 300.0


# ───────────────────────── drop_rungs_beyond_head ─────────────────────────

def _stack_page() -> "np.ndarray":
    img = np.full((400, 300), 255, dtype=np.uint8)
    for r in (280, 260, 240, 220):               # four ledgers, 20 px apart
        img[r - 2:r + 2, 70:157] = 0
    img[250:270, 100:127] = 0                    # a head ON ledger 2
    return img


RUNGS = [279.5, 259.5, 239.5, 219.5]


@pytest.mark.omr_annotate
def test_rungs_beyond_the_head_are_not_counted_for_it() -> None:
    img = _stack_page()
    box = (100.0, 250.0, 126.0, 270.0)
    base = derive_far_head_step(RUNGS, EDGE_Y, SIGN, box[3], SP,
                                img_gray=img, head_box=box)
    # RED (today): the through line at its middle is evidenced, so the LAST
    # rung -- 2.5 sp beyond the head -- is taken as the one through it.
    assert base["offset"] == 8 and base["kind"] == "line"
    got = derive_far_head_step(RUNGS, EDGE_Y, SIGN, box[3], SP, img_gray=img,
                               head_box=box, drop_rungs_beyond_head=True)
    assert got["offset"] == 4 and got["kind"] == "line"


@pytest.mark.omr_annotate
def test_a_head_that_is_on_the_outermost_rung_keeps_all_of_them() -> None:
    """Positive control, same class: the head sits on ledger 4 (nothing is
    beyond it), so the rule removes nothing and the answer is unchanged."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    for r in (280, 260, 240, 220):
        img[r - 2:r + 2, 70:157] = 0
    img[210:230, 100:127] = 0
    box = (100.0, 210.0, 126.0, 230.0)
    base = derive_far_head_step(RUNGS, EDGE_Y, SIGN, box[3], SP,
                                img_gray=img, head_box=box)
    on = derive_far_head_step(RUNGS, EDGE_Y, SIGN, box[3], SP, img_gray=img,
                              head_box=box, drop_rungs_beyond_head=True)
    assert base["offset"] == on["offset"] == 8


@pytest.mark.omr_annotate
def test_drop_rungs_default_off_is_bit_identical() -> None:
    img = _stack_page()
    box = (100.0, 250.0, 126.0, 270.0)
    a = derive_far_head_step(RUNGS, EDGE_Y, SIGN, box[3], SP,
                             img_gray=img, head_box=box)
    b = derive_far_head_step(RUNGS, EDGE_Y, SIGN, box[3], SP, img_gray=img,
                             head_box=box, drop_rungs_beyond_head=False)
    assert a == b


@pytest.mark.omr_annotate
def test_drop_needs_a_head_box_and_never_empties_into_a_guess() -> None:
    """No head box -> nothing to measure against -> unchanged."""
    img = _stack_page()
    a = derive_far_head_step(RUNGS, EDGE_Y, SIGN, 270.0, SP, img_gray=img)
    b = derive_far_head_step(RUNGS, EDGE_Y, SIGN, 270.0, SP, img_gray=img,
                             drop_rungs_beyond_head=True)
    assert a == b


# ───────────────────────── exclusion_rules(connected) ─────────────────────

def _ink() -> "np.ndarray":
    ink = np.zeros((40, 100), dtype=bool)
    # neighbour head box (40, 10, 60, 30): cols 40..60, rows 10..30
    ink[20, 45:61] = True           # head row: ink to the box's right edge...
    ink[20, 61:64] = True           # ...continuing right (connected)
    ink[20, 38:40] = True           # an accidental 2 px left, WHITE GAP 40..44
    ink[24, 38:61] = True           # positive control row: connected on the left
    ink[24, 61:64] = True           # ... and on the right
    return ink


BOXES = [(40.0, 10.0, 60.0, 30.0)]


@pytest.mark.omr_annotate
def test_default_counts_a_separated_accidental_as_a_continuation() -> None:
    """RED (today): ink 2 px left of the box -- across a white gap -- is the
    'left side', so the row survives the neighbour's blanking."""
    out = _exclude_other_heads_ink(_ink(), BOXES, 0, 0, SP)
    assert out[20, 45:61].all()


@pytest.mark.omr_annotate
def test_connected_rule_blanks_the_separated_row_and_keeps_the_real_one() -> None:
    with exclusion_rules(connected=True):
        out = _exclude_other_heads_ink(_ink(), BOXES, 0, 0, SP)
    assert not out[20, 40:61].any()            # accidental behind a gap: blanked
    assert out[24, 38:61].all()                # positive control: a true ledger
    assert out[24, 61:64].all()                # (connected both sides) survives


@pytest.mark.omr_annotate
def test_rules_default_off_and_restored_after_the_block() -> None:
    assert lg._EXCL_RULES == {"connected": False, "own_box": None, "one_sided": False,
                               "jut_from_ink": False}
    with exclusion_rules(connected=True):
        assert lg._EXCL_RULES["connected"] is True
    assert lg._EXCL_RULES == {"connected": False, "own_box": None, "one_sided": False,
                               "jut_from_ink": False}
    a = _exclude_other_heads_ink(_ink(), BOXES, 0, 0, SP)
    with exclusion_rules(connected=False):
        b = _exclude_other_heads_ink(_ink(), BOXES, 0, 0, SP)
    assert (a == b).all()
