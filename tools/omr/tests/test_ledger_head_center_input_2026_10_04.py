"""lane-ledger-r8-main (2026-10-04): `head_middle_rung_evidence` takes an
optional explicit `head_center_y` (page px, same frame as the box).

Why: a Litolff detector box often covers only the TOP of a half note, so
"the box middle" is not the head's middle and the middle-row probe misses
the line that really runs through the head. A caller that can trace the
head's true centre (later: the template matcher) supplies it. `None`
keeps today's box-middle behaviour bit-identically.

Synthetic page, no record read. The head's TRUE extent is rows 100..200
(centre 150); the box covers only its top half, rows 100..150 (box middle
125). A 5px ledger runs through the true centre and juts out of both sides.
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate.ledger_grid import (  # noqa: E402
    collapse_head_edge_rungs_to_middle,
    derive_far_head_step,
    head_middle_rung_evidence,
    measure_ledger_rungs,
)

SPACING = 100.0
TOP_HALF_BOX = (120.0, 100.0, 180.0, 150.0)   # covers only the top half
TRUE_CENTRE = 150.0


def _page() -> "np.ndarray":
    img = np.full((400, 300), 255, dtype=np.uint8)
    img[100:200, 120:181] = 0         # the head's whole body, true extent
    img[148:153, 60:241] = 0          # ledger through the true middle
    return img


@pytest.mark.omr_annotate
def test_box_middle_probe_misses_the_line_through_the_true_middle() -> None:
    """Control that can fail: the default probes at 125, where only the
    head's own body is inked -- no jut -> not through."""
    assert head_middle_rung_evidence(_page(), TOP_HALF_BOX, SPACING) is False


@pytest.mark.omr_annotate
def test_supplied_true_centre_finds_the_line() -> None:
    assert head_middle_rung_evidence(
        _page(), TOP_HALF_BOX, SPACING, head_center_y=TRUE_CENTRE) is True


@pytest.mark.omr_annotate
def test_none_is_bit_identical_to_omitting_it() -> None:
    img = _page()
    assert head_middle_rung_evidence(
        img, TOP_HALF_BOX, SPACING, None, None
    ) == head_middle_rung_evidence(img, TOP_HALF_BOX, SPACING)
    full = (120.0, 100.0, 180.0, 200.0)   # centre 150 either way
    assert head_middle_rung_evidence(
        img, full, SPACING, head_center_y=150.0
    ) == head_middle_rung_evidence(img, full, SPACING)


@pytest.mark.omr_annotate
def test_derive_far_head_step_threads_the_centre() -> None:
    """Head above the staff (sign -1): staff edge at y=400-ish is out of
    frame here, so use a frame where the head sits well above `edge_y`.
    One rung at the true centre; the rung touches the head, so it is a
    through-candidate that only the evidence can confirm."""
    img = _page()
    rungs = [150.0]
    kw = dict(rungs_y=rungs, edge_y=300.0, sign=-1.0,
              head_near_y=TOP_HALF_BOX[3], spacing=SPACING,
              img_gray=img, head_box=TOP_HALF_BOX)
    without = derive_far_head_step(**kw)
    with_c = derive_far_head_step(**kw, head_center_y=TRUE_CENTRE)
    assert with_c["reason"] != without["reason"]
    assert with_c["kind"] == "line"
    assert derive_far_head_step(**kw, head_center_y=None) == without


@pytest.mark.omr_annotate
def test_collapse_threads_the_centre() -> None:
    """Fake edge rungs at the box's top and bottom; the genuine one is put
    back at the supplied centre when the page shows the line there."""
    img = _page()
    box = (120.0, 100.0, 180.0, 200.0)
    edge_rungs = [100.0, 200.0]
    default = collapse_head_edge_rungs_to_middle(
        edge_rungs, 1.0, box, img, SPACING)
    assert default == [150.0]   # full box: middle == true centre
    short = (120.0, 100.0, 180.0, 130.0)
    img2 = _page()
    d = collapse_head_edge_rungs_to_middle([100.0, 130.0], 1.0, short, img2,
                                           SPACING)
    c = collapse_head_edge_rungs_to_middle([100.0, 130.0], 1.0, short, img2,
                                           SPACING, head_center_y=150.0)
    assert d == []
    assert c == [150.0]   # put back at the supplied centre, not the box middle


@pytest.mark.omr_annotate
def test_measure_ledger_rungs_accepts_the_parameter() -> None:
    import inspect
    sig = inspect.signature(measure_ledger_rungs)
    assert sig.parameters["head_center_y"].default is None
