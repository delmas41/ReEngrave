"""lane-farhead-2-9 (Sean 2026-10-07, `farhead_5_6.png` tiles 2 and 9).

Sean: "I don't think it should be assuming there are lines where it can't see them, only looking for them where it thinks
they should be."

TILE 2 (Brahms p18 Flute `18/1/0/5/21`): a head in the second space above the staff. The ledger under it (the first) is
fused into the head's ink, so the walk never found it; the reader had no note line and abstained. Where the staff edge and
the first found rung beyond the head leave a gap with room for exactly one ledger the walk did not find, the row it must be
on is computed and LOOKED at: the ledger's thin flat ends jutting out of the head's ink body, however short. Counted only if
found. The gap alone never makes a ledger (control below).

TILE 9 (Brahms p18 Horn `18/0/5/4/6`): the head belongs to the staff ABOVE (it is on that staff's first ledger below). Read
against the staff below it, the lower arm of an ACCENT under the head was counted as a ledger (1.4 spaces out), so the count
"fit" and the reader answered "2nd ledger above" -- and, both staves now fitting, ownership could not use the ledgers to
choose. A rung counted between the staff and the note's line is refused where it is the stroke of an accent/marcato/tenuto
the detector boxed (the box lies across it and the row's ink ends inside the box): the way an accent's arm stops being a
ledger. A ledger runs on past a mark's box, so a false box on a real ledger changes nothing (control below).

Synthetic page at Brahms scale (28 px spaces, 8 px thick lines/ledgers, a head 40 x 28), ledger_grid level: the walk's rungs
are passed in as the reader would hand them.
"""
import cv2
import numpy as np

from tools.omr.annotate import far_head_reader as FH
from tools.omr.annotate import ledger_grid as lg

SP = 28.0
EDGE = 400.0                       # the staff's top line; the staff runs DOWN from here, the note is ABOVE (sign -1)
CX = 400


def _staff(gray):
    for k in range(5):
        y = int(EDGE + SP * k)
        gray[y - 4:y + 4, 20:780] = 0


def _head(gray, cy):
    cv2.ellipse(gray, (CX, int(cy)), (20, 14), 0, 0, 360, 0, -1)
    return (CX - 20.0, cy - 14.0, CX + 20.0, cy + 14.0)


def _ledger(gray, y, half):
    gray[int(y) - 4:int(y) + 4, CX - half:CX + half] = 0


def _read(gray, box, rungs, on, **kw):
    return lg.derive_note_first_step(gray, box, EDGE, -1.0, SP, list(rungs), flank_refine_bounded=True,
                                     look_where_it_must_be=on, **kw)


# ---- tile 2 --------------------------------------------------------------------------------------------------------
def _tile2(jut_each_side, both=True):
    """head in the second space (ledger 2 at 344 found by the walk with long stubs, ledger 3 at 316); the head's lower rows
    sit on ledger 1 (372), which the walk did not find. `jut_each_side` px of ledger 1 past the head's body each side."""
    gray = np.full((560, 800), 255, np.uint8)
    _staff(gray)
    _ledger(gray, 344, 23)               # touches the head's top, ends 3 px past it (as on the print: a short stub)
    _ledger(gray, 316, 38)
    box = _head(gray, 358.0)
    if jut_each_side:
        gray[368:376, CX - 20 - jut_each_side:CX + 20 + (jut_each_side if both else 0)] = 0   # ledger 1, fused under the head
    return gray, box, [344.0, 316.0]


def test_tile2_hidden_ledger_found_by_its_jut_is_counted():
    gray, box, rungs = _tile2(5)
    got = _read(gray, box, rungs, True)
    assert got["offset"] == 3, got            # in the space beyond ledger 1 (position -3)
    assert got["how"] == "hidden_ledger_jut_looked_for" and got["hidden_ledger_look"]["sides"] == 2


def test_tile2_the_old_reader_abstains_the_control_can_fail():
    gray, box, rungs = _tile2(5)
    got = _read(gray, box, rungs, False)
    assert got["offset"] is None and got["reason"] == "no_line_at_the_note_box", got


def test_tile2_no_jut_no_ledger_the_gap_alone_never_counts():
    gray, box, rungs = _tile2(0)             # same gap, same room for a ledger, nothing printed there
    got = _read(gray, box, rungs, True)
    assert got["offset"] is None, got
    assert got["hidden_ledger_look"] is not None and got["hidden_ledger_look"]["ok"] is False   # it LOOKED, and said so


def test_tile2_a_short_jut_on_one_side_only_is_not_enough():
    gray, box, rungs = _tile2(4, both=False)
    got = _read(gray, box, rungs, True)
    assert got["offset"] is None, got


# ---- tile 9 --------------------------------------------------------------------------------------------------------
def _tile9(accent):
    """the head is ON a line 2.85 spaces out (ledger stubs through it, so the walk's jut reads it); under it, 1.43 spaces
    out, either an ACCENT's arm (a '>' whose lower arm the walk takes for a rung) or a real ledger."""
    gray = np.full((560, 800), 255, np.uint8)
    _staff(gray)
    cy = EDGE - 2.85 * SP
    _ledger(gray, cy, 30)
    box = _head(gray, cy)
    ry = EDGE - 1.43 * SP
    if accent:
        pts_top = np.array([[CX - 16, int(ry) - 14], [CX + 30, int(ry)]], np.int32)
        pts_bot = np.array([[CX - 16, int(ry) + 14], [CX + 30, int(ry)]], np.int32)
        cv2.line(gray, tuple(pts_top[0]), tuple(pts_top[1]), 0, 7)
        cv2.line(gray, tuple(pts_bot[0]), tuple(pts_bot[1]), 0, 7)
    else:
        _ledger(gray, ry, 38)
    return gray, box, [float(ry)], [(CX - 18.0, ry - 14.0, CX + 32.0, ry + 14.0)]     # the detector's articAccentBelow box


def test_tile9_an_accents_arm_is_not_a_ledger():
    gray, box, rungs, ab = _tile9(accent=True)
    got = _read(gray, box, rungs, True, artic_boxes=ab)
    assert got["offset"] is None and got["reason"].startswith("count_does_not_fit"), got
    assert got["between"] == []


def test_tile9_the_old_reader_counts_the_accent_the_control_can_fail():
    gray, box, rungs, ab = _tile9(accent=True)
    got = _read(gray, box, rungs, False, artic_boxes=ab)
    assert got["offset"] == 4 and got["between"], got        # "on ledger 2": the wrong answer Sean ruled on


def test_tile9_positive_control_a_real_ledger_there_still_counts():
    gray, box, rungs, ab = _tile9(accent=False)          # a false accent box lies across a REAL ledger: it runs on past the box
    on, off = _read(gray, box, rungs, True, artic_boxes=ab), _read(gray, box, rungs, False, artic_boxes=ab)
    assert on["offset"] == off["offset"] == 4 and on["between"], (on, off)


def test_the_reader_has_the_look_on_by_default():
    assert FH.READER_KEYWORDS.get("look_where_it_must_be") is True


def test_a_box_beside_another_head_at_the_same_row_does_not_refuse_this_heads_rung():
    gray, box, rungs, ab = _tile9(accent=True)
    far = [(b[0] + 400, b[1], b[2] + 400, b[3]) for b in ab]          # an accent box of a neighbouring bar, same row
    got = _read(gray, box, rungs, True, artic_boxes=far)
    assert got["offset"] == 4 and got["between"], got


def test_a_tenuto_is_not_a_wedge_a_flat_dash_may_be_a_stub_ledger():
    assert lg.is_articulation_class("articAccentBelow") and lg.is_articulation_class("articMarcatoAbove")
    assert not lg.is_articulation_class("articTenutoBelow") and not lg.is_articulation_class("articStaccatoAbove")
