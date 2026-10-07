"""lane-farhead-5-6 (Sean 2026-10-07, `brahms_1007_worse_cases.png` tile 6, Brahms p25 horn): the line a head rests on was
measured on the head's own flank (the ledger stub jutting out of it), then `refine_line_on_flanks` moved it onto an
AUGMENTATION DOT beside the head (9 px away on a 28 px staff) because the stub is shorter than the 0.6-coverage flank
window while the dot passes it. The line then lay 0.6 spaces from the staff edge and the reader abstained
`line_not_beyond_the_staff_edge`, where the print plainly shows the head ON the first ledger below the staff.

The line a jut measured is already read on the flank columns: refining it again can only move it onto other ink. A
walk rung may still be refined, but only within half the page's line thickness.

Synthetic page at Brahms scale: five lines 28 px apart (y 100..212), 8 px thick; ledger 1 at y=238; head 40x28.
"""
import cv2
import numpy as np

from tools.omr.annotate import far_head_reader as FH

SP = 28
LINES = [100.0 + SP * k for k in range(5)]
SUBJ = "glyph/0/0/0/0/0"
CX = 400


def _page(dot=True, ledger_half=30):
    gray = np.full((420, 800), 255, np.uint8)
    for y in LINES:
        gray[int(y) - 4:int(y) + 4, 20:780] = 0
    ly = 238   # Brahms prints its first ledger ~0.93 of a staff space out
    gray[ly - 4:ly + 4, CX - ledger_half:CX + ledger_half] = 0       # ledger 1: 10 px stubs past the head
    cv2.ellipse(gray, (CX, ly), (20, 14), 0, 0, 360, 0, -1)
    if dot:   # an augmentation dot (Brahms' are ~0.5 space wide) up a half space, a 2 px gap clear of the stub's end
        gray[224:233, CX + 32:CX + 48] = 0
    box = (CX - 20.0, ly - 14.0, CX + 20.0, ly + 14.0)
    return gray, box


def _read(gray, box, bounded):
    old = FH.READER_KEYWORDS.get("flank_refine_bounded")
    FH.READER_KEYWORDS["flank_refine_bounded"] = bounded
    try:
        return FH.read_absolute_position(gray, LINES, box, SUBJ, [(SUBJ, box)], [])
    finally:
        if old is None:
            FH.READER_KEYWORDS.pop("flank_refine_bounded", None)
        else:
            FH.READER_KEYWORDS["flank_refine_bounded"] = old


def test_head_on_the_first_ledger_with_a_dot_beside_it():
    gray, box = _page(dot=True)
    pos, why = _read(gray, box, True)
    assert pos == 8 + 2, (pos, why)


def test_the_control_can_fail_the_unbounded_refine_moves_onto_the_dot():
    gray, box = _page(dot=True)
    pos, why = _read(gray, box, False)
    assert pos is None and "line_not_beyond_the_staff_edge" in why, (pos, why)


def test_positive_control_no_dot_both_arms_agree():
    gray, box = _page(dot=False)
    assert _read(gray, box, True)[0] == _read(gray, box, False)[0] == 8 + 2
