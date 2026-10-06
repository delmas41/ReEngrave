"""lane-edge-vs-through (2026-10-06, Sean on out-of-sample tiles 9 and 10 of the night sample).

Convention (Sean): outside the staff, a head is ON a ledger only if that ledger is a line
the page SHOWS; a thin line touching the head's STAFF-SIDE edge, with the whole head beyond
it, puts the head in the space beyond. Tiles 9 (`brahms 13/0/9/0/4`) and 10
(`brahms 3/1/3/7/9`) printed exactly that, and the note-first reader read them ON a
second "rung" at the box's middle: a row of the black head's own body that the ink walk
reported as a line, with nothing of a line beside the head on either side
(`how = through_the_box_middle`). The visible line was the other rung, at the head's edge.

Synthetic pages, spacing 20 px, head BELOW the staff (sign +1), staff bottom line y=300,
ledger 1 printed at y=318..321 (4 px) with the head hanging under it.
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate import ledger_grid as lg  # noqa: E402

SP, SIGN, EDGE_Y = 20.0, 1.0, 300.0


def _page(head_rows=(322, 341), ledger=True):
    img = np.full((420, 300), 255, dtype=np.uint8)
    if ledger:
        img[318:322, 70:157] = 0               # ledger 1, longer than the head on both sides
    img[head_rows[0]:head_rows[1], 100:127] = 0  # the head
    return img


BOX = (100.0, 321.0, 127.0, 341.0)   # middle row 331
EDGE_RUNG, MIDDLE_RUNG = 320.0, 331.0


def _note_line(img, rungs, **kw):
    return lg.find_note_line(img, BOX, EDGE_Y, SIGN, SP, list(rungs), **kw)


def test_bug_reproduced_with_the_rule_off():
    """RED on the unrepaired tree: the middle row of the black head is read as the head's line."""
    r = _note_line(_page(), [EDGE_RUNG, MIDDLE_RUNG])
    assert (r["kind"], r["how"]) == ("on", "through_the_box_middle"), r


def test_visible_edge_line_wins_over_a_hidden_middle_rung():
    r = _note_line(_page(), [EDGE_RUNG, MIDDLE_RUNG], edge_vs_through=True)
    assert r["ok"] and r["kind"] == "space" and abs(r["y"] - EDGE_RUNG) < 1e-6, r


def test_derive_note_first_step_reads_the_space_beyond_ledger_one():
    on = lg.derive_note_first_step(_page(), BOX, EDGE_Y, SIGN, SP, [EDGE_RUNG, MIDDLE_RUNG],
                                   edge_vs_through=True)
    off = lg.derive_note_first_step(_page(), BOX, EDGE_Y, SIGN, SP, [EDGE_RUNG, MIDDLE_RUNG])
    assert on["offset"] == 3 and on["kind"] == "space", on          # in the space below ledger 1
    # off: the middle row is taken as the head's line (here the two rungs are too close for the count
    # to fit, so it abstains; on the real tiles it answered -4 / 10): never the space below ledger 1
    assert off["how"] == "through_the_box_middle" and off["offset"] != 3, off


def test_default_off_equals_explicit_false():
    a = _note_line(_page(), [EDGE_RUNG, MIDDLE_RUNG])
    b = _note_line(_page(), [EDGE_RUNG, MIDDLE_RUNG], edge_vs_through=False)
    assert a == b


def test_positive_control_a_middle_line_the_page_shows_stays_on():
    """The same two rungs, but the middle row IS a line that runs out past the head on both
    sides: the head is on it, the edge rung is not preferred (the rule must be able to say no)."""
    img = _page(head_rows=(322, 341))
    img[329:333, 70:157] = 0                       # a real line through the head's middle
    ev = lg.edge_vs_through_evidence(img, BOX, SIGN, SP, [EDGE_RUNG, MIDDLE_RUNG], MIDDLE_RUNG)
    assert not ev["ok"] and ev["why"] == "the_middle_rung_is_a_line_the_page_shows", ev
    r = _note_line(img, [EDGE_RUNG, MIDDLE_RUNG], edge_vs_through=True)
    assert r["kind"] == "on", r


def test_edge_rung_that_is_no_line_beside_the_head_is_not_preferred():
    """No ledger printed beside the head (the edge 'rung' is the head's own outline): the rule
    has nothing visible to prefer and leaves the old answer (a fallback never invents)."""
    img = _page(ledger=False)
    ev = lg.edge_vs_through_evidence(img, BOX, SIGN, SP, [EDGE_RUNG, MIDDLE_RUNG], MIDDLE_RUNG)
    assert not ev["ok"], ev


def test_head_that_crosses_the_edge_line_is_not_hanging_beyond_it():
    """A head with ink well on the staff side of the line (the line crosses it): excess > the
    limit, so the edge rung is not 'the head hangs beyond it'."""
    img = _page(head_rows=(310, 331))
    box = (100.0, 311.0, 127.0, 335.0)
    ev = lg.edge_vs_through_evidence(img, box, SIGN, SP, [EDGE_RUNG, 327.0], 327.0)
    assert not ev["ok"], ev
    assert lg.head_ink_staff_excess(img, EDGE_RUNG, box, SIGN, SP, 4.0) > \
        lg.EDGE_VS_THROUGH_STAFF_EXCESS_MAX_SPACES


def test_excess_of_a_head_hanging_beyond_the_line_is_about_zero():
    ex = lg.head_ink_staff_excess(_page(), EDGE_RUNG, BOX, SIGN, SP, 4.0)
    assert ex is not None and abs(ex) <= 0.05, ex


def test_no_image_is_not_ok():
    assert not lg.edge_vs_through_evidence(None, BOX, SIGN, SP, [EDGE_RUNG], MIDDLE_RUNG)["ok"]


def test_the_fraction_is_unchanged_by_the_refactor():
    """`head_ink_staff_fraction` keeps its value (same run, same arithmetic)."""
    img = _page(head_rows=(310, 331))
    f = lg.head_ink_staff_fraction(img, 320.0, (100.0, 311.0, 127.0, 335.0), SIGN, SP)
    assert f == pytest.approx((320.0 - 310.0) / (331.0 - 310.0), abs=0.06), f
