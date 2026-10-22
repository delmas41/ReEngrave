"""lane-through-head-on (2026-10-04, Sean on tile 3 `glyph/3/0/8/6/10`).

Convention (Sean): outside the staff, a thin flat ledger passing THROUGH a far
head (head ink on both sides of it) means the head is ON that line. Fix 1
(`near_edge_ledgers`) handles the grazing case (head hangs in the space beyond
the line) and refuses a both-sides head; `through_head_on_rung=True` takes that
refused rung as the head's own line. Default off = bit-identical.

Synthetic pages, spacing 20 px, head BELOW the staff (sign +1), staff bottom
line y=300, ledger 1 at y=320 (4 px thick).
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate.ledger_grid import (  # noqa: E402
    derive_far_head_step,
    through_head_on_rung_evidence,
)

SP, SIGN, EDGE_Y = 20.0, 1.0, 300.0
RUNGS = [319.5]


def _page(head_rows):
    img = np.full((420, 300), 255, dtype=np.uint8)
    img[318:322, 70:157] = 0                    # ledger 1
    r0, r1 = head_rows
    img[r0:r1, 100:127] = 0                     # the head
    return img


def _box(head_rows):
    # the detector box is a little taller than the ink (as on the real page),
    # so the box MIDDLE is not on the ledger
    return (100.0, float(head_rows[0]) - 4.0, 126.0, float(head_rows[1]) + 10.0)


def _derive(head_rows, **kw):
    box = _box(head_rows)
    return derive_far_head_step(
        list(RUNGS), EDGE_Y, SIGN, box[1], SP, img_gray=_page(head_rows),
        head_box=box, near_edge_ledgers=True, **kw)


THROUGH = (314, 330)    # ledger crosses the head near its top: ~0.34 of its ink staff-side
GRAZING = (321, 337)    # head hangs below the ledger


def test_through_head_is_on_the_line_when_on():
    r = _derive(THROUGH, through_head_on_rung=True)
    assert (r["offset"], r["kind"]) == (2, "line"), r


def test_through_head_default_off_is_the_old_answer():
    r = _derive(THROUGH)
    assert r["offset"] != 2 or r["kind"] != "line", r


def test_default_off_equals_explicit_false():
    for rows in (THROUGH, GRAZING):
        assert _derive(rows) == _derive(rows, through_head_on_rung=False)


def test_grazing_head_still_in_the_space_beyond_with_rule_on():
    """positive control in the same class: fix 1's own case is untouched."""
    r = _derive(GRAZING, through_head_on_rung=True)
    assert (r["offset"], r["kind"]) == (3, "space"), r


def test_evidence_refuses_a_grazing_head():
    ev = through_head_on_rung_evidence(_page(GRAZING), 319.5, _box(GRAZING), SIGN, SP)
    assert not ev["ok"]


def test_evidence_accepts_through_head_and_reports_frac():
    ev = through_head_on_rung_evidence(_page(THROUGH), 319.5, _box(THROUGH), SIGN, SP)
    assert ev["ok"] and ev["frac_stf"] >= 0.245, ev


def test_no_image_is_not_ok():
    assert not through_head_on_rung_evidence(None, 319.5, _box(THROUGH), SIGN, SP)["ok"]
