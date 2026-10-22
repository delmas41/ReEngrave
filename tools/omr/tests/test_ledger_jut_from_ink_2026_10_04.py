"""lane-jut-from-ink (2026-10-04): `head_middle_rung_evidence(jut_from_ink=True)` measures the ledger's
jut from the head's own INK edge, not from the detector box edge.

Why: the frame-drop investigation found the box-edge test (needs 0.25 sp = 4 px past the BOX) flips ~5
of 41 Litolff far heads for 2 px of box placement. Here the head is a 30 x 16 px body (spacing 16 px),
a 4 px ledger runs through its middle and juts 6 px out of each side; the box is drawn 4 px too wide, so
from the box edge the line juts only 2 px (under the 4 px cut) while from the ink it juts 6.

Synthetic page, no record read.
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate.ledger_grid import (  # noqa: E402
    exclusion_rules,
    head_middle_rung_evidence,
)

SPACING = 16.0
HEAD = (100, 92, 130, 108)            # x0, y0, x1, y1 of the head's own ink
BOX = (96.0, 92.0, 134.0, 108.0)      # detector box: 4 px wider than the head each side


def _page(jut_px: int = 6, ledger: bool = True, stem: bool = False) -> "np.ndarray":
    img = np.full((200, 240), 255, dtype=np.uint8)
    x0, y0, x1, y1 = HEAD
    img[y0:y1, x0:x1] = 0
    if ledger:
        img[98:102, x0 - jut_px:x1 + jut_px] = 0     # 4 px ledger through the middle
    if stem:
        img[40:92, x1 - 2:x1] = 0
    return img


def _shifted(box, dx, dy):
    return (box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy)


@pytest.mark.omr_annotate
def test_box_edge_test_misses_a_line_that_juts_from_the_ink() -> None:
    """The control that can fail (RED on the unrepaired tree: there is no `jut_from_ink` keyword)."""
    assert head_middle_rung_evidence(_page(), BOX, SPACING, jut_from_ink=False) is False


@pytest.mark.omr_annotate
def test_ink_edge_test_finds_it() -> None:
    assert head_middle_rung_evidence(_page(), BOX, SPACING, jut_from_ink=True) is True


@pytest.mark.omr_annotate
def test_answer_does_not_move_when_the_box_shifts() -> None:
    img = _page()
    answers = {head_middle_rung_evidence(img, _shifted(BOX, dx, dy), SPACING, jut_from_ink=True)
               for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)}
    assert answers == {True}


@pytest.mark.omr_annotate
def test_no_ledger_is_never_a_line() -> None:
    """Negative control in the same class: the same head and box with no ledger."""
    assert head_middle_rung_evidence(_page(ledger=False), BOX, SPACING, jut_from_ink=True) is False


@pytest.mark.omr_annotate
def test_a_stub_too_short_is_not_a_line() -> None:
    """1 px of ink past the head is its outline, not a ledger (floor = RUNG_STUB_MIN_SPACES * 16 = 2.4)."""
    assert head_middle_rung_evidence(_page(jut_px=1), BOX, SPACING, jut_from_ink=True) is False


@pytest.mark.omr_annotate
def test_one_side_is_enough() -> None:
    img = _page()
    img[98:102, 94:100] = 255      # blank the left jut
    assert head_middle_rung_evidence(img, BOX, SPACING, jut_from_ink=True) is True


@pytest.mark.omr_annotate
def test_default_and_module_rule_keep_the_old_behaviour() -> None:
    img = _page()
    assert head_middle_rung_evidence(img, BOX, SPACING) is False                  # default OFF
    with exclusion_rules(jut_from_ink=True):
        assert head_middle_rung_evidence(img, BOX, SPACING) is True               # rule ON
    assert head_middle_rung_evidence(img, BOX, SPACING) is False                  # restored


@pytest.mark.omr_annotate
def test_no_image_cannot_tell() -> None:
    assert head_middle_rung_evidence(None, BOX, SPACING, jut_from_ink=True) is False
