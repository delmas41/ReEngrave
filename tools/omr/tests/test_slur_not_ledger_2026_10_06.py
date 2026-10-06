"""lane-slur-not-ledger (Sean, 2026-10-06): a slur or tie is not a ledger. Litolff p16 `glyph/16/0/0/0/2` counted the
tip of a slur as a ledger below the staff and so read the head as belonging to the staff above. A counted ledger is a
short, straight, level line at the note's column; a rung whose stroke is curved / tilted (or runs far longer than a
ledger) is refused, with the record's slur/tie boxes as supporting evidence.

Synthetic page as in test_ledger_not_text: staff lines 16 px apart (100..164), the head ON ledger 2 below (y 196), and
on the first ledger's row (y 180) either a real ledger, a rising slur tip, or a level ledger under a tie box.
"""
import cv2
import numpy as np

from tools.omr.annotate import far_head_reader as FH
from tools.omr.annotate import ledger_grid as lg

LINES = [100.0, 116.0, 132.0, 148.0, 164.0]
SUBJ = "glyph/0/0/0/0/0"
CX = 300


def _page(row1):
    """`row1`: 'line' (a printed ledger), 'slur' (a thin stroke rising 17 px over 70 px through y 180 at the column), None."""
    gray = np.full((320, 600), 255, np.uint8)
    for y in LINES:
        gray[int(y) - 1:int(y) + 2, 20:580] = 0
    gray[196 - 1:196 + 2, CX - 22:CX + 22] = 0                       # ledger 2 (the head's own)
    if row1 == "line":
        gray[180 - 1:180 + 2, CX - 22:CX + 22] = 0
    elif row1 == "slur":
        pts = np.array([[x, 180 + (CX - x) * 0.25] for x in range(CX - 35, CX + 36, 4)], np.int32)
        cv2.polylines(gray, [pts], False, 0, 3)
    cv2.ellipse(gray, (CX, 196), (12, 8), 0, 0, 360, 0, -1)
    return gray, (CX - 12.0, 188.0, CX + 12.0, 204.0)


def _read(gray, box, arc_boxes=None, on=True):
    old = FH.READER_KEYWORDS["slur_not_ledger"]
    FH.READER_KEYWORDS["slur_not_ledger"] = on
    try:
        return FH.read_absolute_position(gray, LINES, box, SUBJ, [(SUBJ, box)], [], arc_boxes=arc_boxes)
    finally:
        FH.READER_KEYWORDS["slur_not_ledger"] = old


def test_a_slur_stroke_is_refused_and_a_real_ledger_is_kept():
    slur, _ = _page("slur")
    tie = [(CX - 40.0, 165.0, CX + 40.0, 195.0)]
    kept, rej = lg.ledger_candidates_not_slur(slur, [180.0], float(CX), 16.0, tie)
    assert kept == [] and rej[0]["why"].startswith("not_straight_short_level_curved"), rej
    # no record box across it: shape alone does not refuse (the first out-of-sample read lost 119 geometry-agreeing heads)
    assert lg.ledger_candidates_not_slur(slur, [180.0], float(CX), 16.0, [])[0] == [180.0]
    line, _ = _page("line")
    assert lg.ledger_candidates_not_slur(line, [180.0], float(CX), 16.0, [])[0] == [180.0]


def test_a_level_ledger_under_a_tie_box_is_kept():
    """The record's tie box is evidence, not a verdict: a straight level stroke under it stays (a ledger may sit
    under a real tie)."""
    line, _ = _page("line")
    tie = [(CX - 40.0, 170.0, CX + 40.0, 190.0)]
    assert lg.ledger_candidates_not_slur(line, [180.0], float(CX), 16.0, tie)[0] == [180.0]


def test_the_head_is_not_read_as_ledger_two_off_a_slur_and_the_off_switch_is_bit_identical():
    gray, box = _page("slur")
    tie = [(CX - 40.0, 165.0, CX + 40.0, 195.0)]
    on = _read(gray, box, arc_boxes=tie)
    off = _read(gray, box, arc_boxes=tie, on=False)
    assert off[0] == 8 + 4, off            # the unrepaired reading: the slur counted as ledger 1
    assert on[0] != off[0], on              # the repaired reader no longer counts it
    line, lbox = _page("line")
    assert _read(line, lbox)[0] == 8 + 4    # positive control in the same class: a real ledger still counts


def test_the_keyword_defaults_on_and_a_trace_without_ink_is_untestable_not_refused():
    assert FH.READER_KEYWORDS["slur_not_ledger"] is True
    blank = np.full((320, 600), 255, np.uint8)
    assert lg.rung_shape(blank, 180.0, float(CX), 16.0)["verdict"] == "untestable"
    assert lg.ledger_candidates_not_slur(blank, [180.0], float(CX), 16.0, [])[0] == [180.0]
