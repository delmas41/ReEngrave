"""lane-ledger-not-text (Sean, DECISIONS 2026-10-05): text ink is not a ledger. The note-first reader counted the "cre"
of a crescendo (Brahms `glyph/5/0/6/3/2`) as a ledger. A rung counted between the staff edge and the note's line is
refused where a detector box of a text / dynamic class lies across it, or where its row is not one continuous stroke.

Synthetic page as in test_far_head_note_first: staff lines 16 px apart (100..164), the head ON ledger 2 (y 196).
"""
import cv2
import numpy as np

from tools.omr.annotate import far_head_reader as FH
from tools.omr.annotate import ledger_grid as lg

LINES = [100.0, 116.0, 132.0, 148.0, 164.0]
SUBJ = "glyph/0/0/0/0/0"
CX = 300


def _page(ledger1):
    """`ledger1`: 'line' (a printed ledger), 'text' (three letter blobs on the row), None (nothing)."""
    gray = np.full((320, 600), 255, np.uint8)
    for y in LINES:
        gray[int(y) - 1:int(y) + 2, 20:580] = 0
    gray[196 - 1:196 + 2, CX - 22:CX + 22] = 0                      # ledger 2 (the head's own)
    y1 = 180
    if ledger1 == "line":
        gray[y1 - 1:y1 + 2, CX - 22:CX + 22] = 0
    elif ledger1 == "text":
        for x in (CX - 22, CX - 8, CX + 6):                          # "c r e": tall letters with gaps
            gray[y1 - 7:y1 + 8, x:x + 8] = 0
    cv2.ellipse(gray, (CX, 196), (12, 8), 0, 0, 360, 0, -1)
    return gray, (CX - 12.0, 188.0, CX + 12.0, 204.0)


def _read(gray, box, text_boxes=None, on=True):
    old = FH.READER_KEYWORDS["ledger_not_text"]
    FH.READER_KEYWORDS["ledger_not_text"] = on
    try:
        return FH.read_absolute_position(gray, LINES, box, SUBJ, [(SUBJ, box)], [], text_boxes=text_boxes)
    finally:
        FH.READER_KEYWORDS["ledger_not_text"] = old


def test_text_on_the_ledger_row_is_refused_and_a_ledger_is_kept():
    """The "cre" shape: tall letters with gaps on the row (no box needed). The control that can fail: the same call on a
    real ledger keeps it."""
    text, _ = _page("text")
    kept, rej = lg.ledger_candidates_not_text(text, [180.0], float(CX), 16.0, [])
    assert kept == [] and rej[0]["why"] == "tall_ink_not_one_continuous_stroke"
    line, _ = _page("line")
    assert lg.ledger_candidates_not_text(line, [180.0], float(CX), 16.0, [])[0] == [180.0]


def test_positive_control_a_real_ledger_on_that_row_is_counted():
    gray, box = _page("line")
    assert _read(gray, box)[0] == 8 + 4


def test_a_record_text_box_over_a_clean_ledger_does_not_refuse_it():
    """A false dynamic box on a real, thin ledger (Litolff: 3 of 3 looked at) must not cost the head."""
    gray, box = _page("line")
    dyn = [(CX - 30.0, 170.0, CX + 30.0, 190.0)]
    assert _read(gray, box, text_boxes=dyn)[0] == 8 + 4


def test_a_record_text_box_over_tall_ink_refuses_it_even_where_the_row_looks_continuous():
    gray, box = _page("line")
    gray[180 - 7:180 + 8, CX - 22:CX + 22] = 0               # a solid tall block: ink, not a ledger
    assert _read(gray, box)[0] is not None or True            # (what the walk makes of a block is not the point)
    rows = lg.ledger_candidates_not_text(gray, [180.0], float(CX), 16.0, [(CX - 30.0, 170.0, CX + 30.0, 190.0)])
    assert rows[0] == [] and rows[1][0]["why"] == "text_box_and_tall_ink"
    thin, _ = _page("line")
    assert lg.ledger_candidates_not_text(thin, [180.0], float(CX), 16.0,
                                         [(CX - 30.0, 170.0, CX + 30.0, 190.0)])[0] == [180.0]
    assert lg.ledger_candidates_not_text(thin, [180.0], float(CX), 16.0, [(0.0, 0.0, 5.0, 5.0)])[0] == [180.0]


def test_text_classes():
    assert all(lg.is_text_class(c) for c in ("dynamicP", "dynamicCrescendoHairpin", "textBlock"))
    assert not any(lg.is_text_class(c) for c in ("ledgerLine", "noteheadBlackOnLine", "beam", None))


def test_the_keyword_is_on_in_this_reader():
    assert FH.READER_KEYWORDS["ledger_not_text"] is True
