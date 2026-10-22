"""lane-ledger-far-side-rule (2026-10-04, Sean on the far-edge crop sheet).

Convention (Sean): outside the staff, a thin line touching the FAR side of a
head (the side away from the staff) with NO other note farther out means the
head is ON that line. With a chord partner farther out the rule does not
apply (that line is the partner's, or the head is in a space).

`derive_far_head_step(far_side_ledger=True, far_side_partner_boxes=...)`;
default off = bit-identical.

Synthetic pages, no record read. Spacing 20 px, head ABOVE the staff (sign
-1), staff top line y=300 so ledgers sit at 280, 260, 240 (n = 1, 2, 3).
Ledgers 4 px thick (0.2 sp; thin cap 7 px), stub minimum 3 px.
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate.ledger_grid import (  # noqa: E402
    derive_far_head_step,
    far_side_ledger_evidence,
)

SP = 20.0
SIGN = -1.0
EDGE_Y = 300.0
# the head: rows 236..257; ledger 3 (rows 237..240) lies along its TOP (far)
# side -- 0.43 sp above the box middle, 0.125 sp inside the far edge.
BOX = (100.0, 236.0, 126.0, 258.0)
RUNGS = [279.5, 259.5, 238.5]


def _page(*, ledger3=True, partner=False, arc=False) -> "np.ndarray":
    img = np.full((400, 300), 255, dtype=np.uint8)
    img[278:282, 70:157] = 0                    # ledger 1
    img[258:262, 70:157] = 0                    # ledger 2
    img[236:258, 100:127] = 0                   # the head
    if ledger3:
        img[237:241, 70:157] = 0                # ledger 3, through the top
    if partner:
        img[214:234, 100:127] = 0               # a head farther out
    if arc:
        # a slur: 3 px thick, bowing hard across the head's top (rows 237..)
        for x in range(70, 157):
            y = int(round(250 - 14 * np.sin(np.pi * (x - 70) / 86.0)))
            img[y:y + 3, x] = 0
    return img


PARTNER_BOX = (100.0, 214.0, 126.0, 234.0)


def _derive(img, *, far=False, partners=None, rungs=None):
    kw = {}
    if far:
        kw = dict(far_side_ledger=True, far_side_partner_boxes=partners)
    return derive_far_head_step(
        list(RUNGS[:2] if rungs is None else rungs), EDGE_Y, SIGN, BOX[3], SP,
        img_gray=img, head_box=BOX, exclude_boxes=partners, **kw)


@pytest.mark.omr_annotate
def test_far_side_jut_no_partner_means_the_head_is_on_that_line() -> None:
    """Default (today): the far-side line is not a counted rung, the head is
    read in the SPACE beyond ledger 2 (offset 5). With the rule: ON ledger 3
    (offset 6, a line)."""
    img = _page()
    assert _derive(img)["offset"] == 5                     # control: the bug
    got = _derive(img, far=True, partners=[])
    assert got["offset"] == 6 and got["kind"] == "line"


@pytest.mark.omr_annotate
def test_chord_partner_farther_out_leaves_the_answer_unchanged() -> None:
    """Same page and same line, plus a head farther out in the column: the
    rule does not apply. (Positive control: the previous test, same line.)"""
    img = _page(partner=True)
    ev = far_side_ledger_evidence(
        img, BOX, SIGN, SP, EDGE_Y, [PARTNER_BOX], [PARTNER_BOX])
    assert ev["ok"] is False and ev["why"] == "a_chord_partner_sits_farther_out"
    on = _derive(img, far=True, partners=[PARTNER_BOX])
    assert on["offset"] == _derive(img)["offset"] == 5


@pytest.mark.omr_annotate
def test_partner_must_be_in_the_column_and_within_a_stem() -> None:
    """A head NEAR the staff (not farther out), or one in a far-away column,
    or one a whole staff beyond is not a partner."""
    img = _page()
    nearer = (100.0, 270.0, 126.0, 290.0)         # between head and staff
    other_col = (220.0, 214.0, 246.0, 234.0)       # same height, another column
    too_far = (100.0, 100.0, 126.0, 120.0)         # > one stem length out
    for b in (nearer, other_col, too_far):
        assert _derive(img, far=True, partners=[b])["offset"] == 6, b


@pytest.mark.omr_annotate
def test_slur_arc_across_the_far_edge_is_not_a_ledger() -> None:
    """No ledger 3; instead a curved arc crossing the head's top. It is not
    flat, so nothing counts: the answer is today's (offset 5)."""
    img = _page(ledger3=False, arc=True)
    assert _derive(img, far=True, partners=[])["offset"] == 5
    ev = far_side_ledger_evidence(img, BOX, SIGN, SP, EDGE_Y, [], [])
    assert ev["ok"] is False


@pytest.mark.omr_annotate
def test_no_line_at_the_far_side_leaves_the_answer_unchanged() -> None:
    """Positive-control twin: the same head with no ledger 3 at all."""
    img = _page(ledger3=False)
    assert _derive(img, far=True, partners=[])["offset"] == 5


@pytest.mark.omr_annotate
def test_default_off_is_bit_identical() -> None:
    for img in (_page(), _page(partner=True), _page(ledger3=False, arc=True)):
        base = derive_far_head_step(
            RUNGS[:2], EDGE_Y, SIGN, BOX[3], SP, img_gray=img, head_box=BOX)
        assert _derive(img) == base
        assert derive_far_head_step(
            RUNGS[:2], EDGE_Y, SIGN, BOX[3], SP, img_gray=img, head_box=BOX,
            far_side_ledger=False, far_side_partner_boxes=[PARTNER_BOX]) == base


@pytest.mark.omr_annotate
def test_a_line_through_the_middle_is_still_the_through_rule() -> None:
    """The middle-row test goes first: a head with a line at its own middle
    keeps the unchanged through answer whether or not the rule is on."""
    img = np.full((400, 300), 255, dtype=np.uint8)
    img[278:282, 70:157] = 0
    img[258:262, 70:157] = 0
    img[236:258, 100:127] = 0
    img[245:249, 70:157] = 0                    # a line at the head's middle
    rungs = [279.5, 259.5, 246.5]
    off = derive_far_head_step(rungs, EDGE_Y, SIGN, BOX[3], SP,
                               img_gray=img, head_box=BOX)
    on = derive_far_head_step(rungs, EDGE_Y, SIGN, BOX[3], SP, img_gray=img,
                              head_box=BOX, far_side_ledger=True,
                              far_side_partner_boxes=[])
    assert on == off
