"""lane-ledger-exclusion (2026-10-04): what `_exclude_other_heads_ink` may blank
of THIS head's evidence.  Three default-OFF rules, found by tracing Sean's tiles
2, 7, 9 (`benchmarks/omr-local-staff-2026-09/FINDINGS.md`, "lane-ledger-exclusion"):

  * `exclusion_boxes_for(..., drop_same_ink_other_staff=True)`: a box owned by
    ANOTHER staff that overlaps the subject's by more than half of the smaller
    box -- without coinciding with it -- is this same ink detected twice, not
    another note, and is not blanked (tiles 7 and 9).
  * `exclusion_rules(one_sided=True)`: a row of another head's box is kept when
    a thin, flat line, connected to its ink, juts out of ONE side (Sean 10-01)
    -- tile 2's second ledger.
  * `exclusion_rules(own_box=...)`: the subject's own box is never blanked
    (measured, REFUSED as a default: it breaks two right heads; the keyword stays).

Synthetic arrays only (no record read).  Every refusal test has a positive
control in the same class.
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate import ledger_grid as lg  # noqa: E402
from tools.omr.annotate.ledger_grid import (  # noqa: E402
    _exclude_other_heads_ink,
    _thin_flat_one_sided_jut,
    exclusion_boxes_for,
    exclusion_rules,
)

SP = 20.0
H, W = 200, 260
BOX = (100.0, 90.0, 126.0, 110.0)          # the NEIGHBOUR head's detector box


def _page(ledger=None, round_tip=False, gap=False) -> "np.ndarray":
    """255 = paper.  A neighbour head body inside BOX, plus (optionally) a
    ledger row band jutting out of its right side, or a rounded tip."""
    img = np.full((H, W), 255, dtype=np.uint8)
    img[92:108, 102:124] = 0                       # the head body
    if ledger:
        r0, r1, x_end = ledger
        x_start = 131 if gap else 100
        img[r0:r1, x_start:x_end] = 0              # a ledger, out of ONE side only
    if round_tip:
        yy, xx = np.mgrid[0:H, 0:W]
        img[((xx - 115) / 24.0) ** 2 + ((yy - 100) / 10.0) ** 2 <= 1.0] = 0
    return img


def _jut(img, row=100) -> bool:
    ink = img <= 0
    return _thin_flat_one_sided_jut(ink, 0, 0, img, 0, row, 100, 127, SP)


# ───────────────────────────── one_sided ─────────────────────────────────

@pytest.mark.omr_annotate
def test_a_thin_flat_connected_jut_on_one_side_is_a_ledger() -> None:
    img = _page(ledger=(99, 103, 140))             # 4 px thick, 13 px beyond the box
    assert _jut(img, 100) is True


@pytest.mark.omr_annotate
def test_a_rounded_head_tip_beyond_the_box_is_not() -> None:
    # same class as the positive above: ink beyond the box on one side, but
    # its thickness (13 px) is a head's, not a ledger's
    assert _jut(_page(round_tip=True), 100) is False


@pytest.mark.omr_annotate
def test_too_short_too_thick_or_behind_a_white_gap_is_not() -> None:
    assert _jut(_page(ledger=(99, 103, 131)), 100) is False      # 4 px beyond: < 0.35 sp
    assert _jut(_page(ledger=(96, 106, 140)), 100) is False      # 10 px thick
    assert _jut(_page(ledger=(99, 103, 150), gap=True), 100) is False   # white gap


@pytest.mark.omr_annotate
def test_the_jut_works_off_the_window_when_no_page_is_given() -> None:
    img = _page(ledger=(99, 103, 140))
    ink = img <= 0
    assert _thin_flat_one_sided_jut(ink, 0, 0, None, None, 100, 100, 127, SP) is True


@pytest.mark.omr_annotate
def test_exclusion_keeps_the_jutting_row_only_when_the_rule_is_on() -> None:
    img = _page(ledger=(99, 103, 140))
    ink = img <= 0
    # RED today: the row is blanked (no ink on the LEFT, so not "both sides")
    off = _exclude_other_heads_ink(ink, [BOX], 0, 0, SP, img, 0)
    assert not off[100, 100:127].any()
    with exclusion_rules(one_sided=True):
        on = _exclude_other_heads_ink(ink, [BOX], 0, 0, SP, img, 0)
    assert on[100, 100:127].all()                  # the ledger row survives ...
    assert not on[95, 104:122].any()               # ... the head's own body still goes
    assert not on[106, 104:122].any()


@pytest.mark.omr_annotate
def test_the_rule_does_not_leak_out_of_its_context() -> None:
    img = _page(ledger=(99, 103, 140))
    ink = img <= 0
    with exclusion_rules(one_sided=True, own_box=(0, 0, 10, 10)):
        pass
    again = _exclude_other_heads_ink(ink, [BOX], 0, 0, SP, img, 0)
    assert not again[100, 100:127].any()


# ──────────────────────────── own_box ────────────────────────────────────

@pytest.mark.omr_annotate
def test_the_subjects_own_box_is_never_blanked_when_asked() -> None:
    img = _page()
    ink = img <= 0
    subject = (105.0, 95.0, 120.0, 105.0)          # inside the neighbour's box
    base = _exclude_other_heads_ink(ink, [BOX], 0, 0, SP, img, 0)
    assert not base[100, 106:119].any()            # RED today: blanked
    with exclusion_rules(own_box=subject):
        got = _exclude_other_heads_ink(ink, [BOX], 0, 0, SP, img, 0)
    assert got[96:105, 106:120].all()              # the subject's box kept ...
    assert not got[93, 103:123].any()              # ... what is outside it still blanked


# ──────────────────────── drop_same_ink_other_staff ──────────────────────

SUBJ = "glyph/3/0/7/7/0"
SBOX = (100.0, 100.0, 125.0, 121.0)


def _boxes(*rows):
    return list(rows)


@pytest.mark.omr_annotate
def test_default_exclusion_list_is_every_other_notehead_plus_accidentals() -> None:
    nh = _boxes((SUBJ, SBOX), ("glyph/3/0/8/7/1", (100.0, 109.0, 126.0, 121.0)),
                ("glyph/3/0/7/6/2", (10.0, 10.0, 30.0, 30.0)))
    acc = [("glyph/3/0/7/7/1", (80.0, 90.0, 90.0, 130.0))]
    got = exclusion_boxes_for(SUBJ, SBOX, nh, acc)
    assert got == [nh[1][1], nh[2][1], acc[0][1]]


@pytest.mark.omr_annotate
def test_a_partial_overlap_by_another_staffs_box_is_the_same_ink_not_a_note() -> None:
    dup = ("glyph/3/0/8/7/1", (100.0, 109.0, 126.0, 121.0))     # half the head, staff 8
    nh = _boxes((SUBJ, SBOX), dup)
    assert exclusion_boxes_for(SUBJ, SBOX, nh, drop_same_ink_other_staff=True) == []
    assert exclusion_boxes_for(SUBJ, SBOX, nh) == [dup[1]]       # RED today


@pytest.mark.omr_annotate
def test_the_same_staff_a_coincident_box_and_a_small_overlap_are_kept() -> None:
    same_staff = ("glyph/3/0/7/7/2", (100.0, 109.0, 126.0, 121.0))
    coincident = ("glyph/3/0/8/7/1", (100.5, 100.5, 125.5, 120.5))     # IoU > 0.9: the box itself
    sliver = ("glyph/3/0/8/7/3", (120.0, 100.0, 146.0, 121.0))        # next head of a chord
    nh = _boxes((SUBJ, SBOX), same_staff, coincident, sliver)
    got = exclusion_boxes_for(SUBJ, SBOX, nh, drop_same_ink_other_staff=True)
    assert got == [same_staff[1], coincident[1], sliver[1]]


@pytest.mark.omr_annotate
def test_accidental_boxes_are_never_dropped_by_the_duplicate_rule() -> None:
    acc = [("glyph/3/0/8/7/5", (100.0, 109.0, 126.0, 121.0))]
    got = exclusion_boxes_for(SUBJ, SBOX, [(SUBJ, SBOX)], acc, drop_same_ink_other_staff=True)
    assert got == [acc[0][1]]
