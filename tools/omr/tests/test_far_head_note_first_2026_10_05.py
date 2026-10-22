"""lane-farhead-note-first (Sean, DECISIONS 2026-10-05): a far head is read in his ORDER -- the staff's edge, then the
NOTE's own line (through its middle, or on its staff-side edge), then the ledgers counted strictly between the edge and
that line, which must fit the gap. A line that is not at the note's box can never be the answer, and a count that
disagrees with the gap abstains. The run-2 reader (`note_first` False) stays reproducible.

Synthetic page: five staff lines 16 px apart (y 100..164), ledgers below at 180, 196, 212 ..., a filled head 24x16.
"""
import cv2
import numpy as np
import pytest

from tools.omr.annotate import far_head_reader as FH

LINES = [100.0, 116.0, 132.0, 148.0, 164.0]
SUBJ = "glyph/0/0/0/0/0"


def _page(ledgers, head_cy, head_cx=300):
    gray = np.full((320, 600), 255, np.uint8)
    for y in LINES:
        gray[int(y) - 1:int(y) + 2, 20:580] = 0
    for k in ledgers:                       # ledger k, k spaces below the bottom line
        y = int(164 + 16 * k)
        gray[y - 1:y + 2, head_cx - 22:head_cx + 22] = 0
    cv2.ellipse(gray, (head_cx, int(head_cy)), (12, 8), 0, 0, 360, 0, -1)
    box = (head_cx - 12.0, head_cy - 8.0, head_cx + 12.0, head_cy + 8.0)
    return gray, box


def _read(gray, box, note_first=True):
    old = FH.READER_KEYWORDS["note_first"]
    FH.READER_KEYWORDS["note_first"] = note_first
    try:
        return FH.read_absolute_position(gray, LINES, box, SUBJ, [(SUBJ, box)], [])
    finally:
        FH.READER_KEYWORDS["note_first"] = old


def test_head_on_the_second_ledger_through_its_middle():
    gray, box = _page([1, 2], 164 + 32)
    assert _read(gray, box)[0] == 8 + 4


def test_head_in_the_space_beyond_the_first_ledger_on_its_staff_side_edge():
    gray, box = _page([1], 164 + 16 + 8)
    assert _read(gray, box)[0] == 8 + 3


def test_head_on_the_first_ledger():
    gray, box = _page([1], 164 + 16)
    assert _read(gray, box)[0] == 8 + 2


def test_a_line_not_at_the_note_box_is_never_the_answer():
    """The head floats 1.5 spaces past ledger 2 (no line at its box). The run-2 reader counts outward and
    answers; note-first must abstain, naming that no line is at the note."""
    gray, box = _page([1, 2], 164 + 32 + 24)
    old_pos, _ = _read(gray, box, note_first=False)
    assert old_pos is not None            # the control can fail: the old path answers here
    pos, why = _read(gray, box)
    assert pos is None and "no_line_at_the_note_box" in why


def test_a_count_that_does_not_fit_the_gap_abstains():
    """The head is ON the third ledger but the second was never printed: the gap holds room for a ledger that is
    not there -> abstain, never pick a count."""
    gray, box = _page([1, 3], 164 + 48)
    pos, why = _read(gray, box)
    assert pos is None and "count_does_not_fit" in why


def test_positive_control_same_class_with_every_ledger_printed():
    gray, box = _page([1, 2, 3], 164 + 48)
    assert _read(gray, box)[0] == 8 + 6


def test_a_head_above_the_staff_counts_upward():
    gray = np.full((320, 600), 255, np.uint8)
    for y in LINES:
        gray[int(y) - 1:int(y) + 2, 20:580] = 0
    gray[int(100 - 16) - 1:int(100 - 16) + 2, 278:322] = 0
    cv2.ellipse(gray, (300, 84), (12, 8), 0, 0, 360, 0, -1)
    assert _read(gray, (288.0, 76.0, 312.0, 92.0))[0] == -2


def test_the_old_path_is_still_reproducible():
    gray, box = _page([1, 2], 164 + 32)
    assert _read(gray, box, note_first=False)[0] == 8 + 4


def test_the_keyword_is_on_in_this_reader():
    assert FH.READER_KEYWORDS["note_first"] is True


@pytest.mark.parametrize("ledgers,cy", [([1, 2, 3, 4], 164 + 64), ([1, 2], 164 + 40)])
def test_deep_stacks_count_to_the_note(ledgers, cy):
    gray, box = _page(ledgers, cy)
    pos, _ = _read(gray, box)
    assert pos == 8 + int(round(2 * (cy - 164) / 16))
