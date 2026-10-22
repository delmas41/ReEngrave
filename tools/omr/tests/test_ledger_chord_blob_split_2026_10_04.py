"""lane-chord-blob-split (2026-10-04): a merged chord blob (two heads a third
apart) is split into two page-standard head boxes with the stacked-thirds
ledger between them.  Synthetic page; no library / weights."""
import cv2
import numpy as np
import pytest

from tools.omr.annotate import ledger_grid as lg

SP = 16.0
W_SP, H_SP, TILT = 1.5, 1.05, 0.0


def _page(centres, with_ledger_stubs=False):
    img = np.full((260, 220), 255, np.uint8)
    for cy in centres:
        cv2.ellipse(img, (100, int(round(cy))), (int(W_SP * SP / 2), int(H_SP * SP / 2)),
                    0, 0, 360, 0, -1)
    # a stem on the left edge of the lowest head, running down
    cv2.rectangle(img, (88, int(centres[-1])), (91, int(centres[-1]) + 45), 0, -1)
    if with_ledger_stubs:
        for y in (int(np.mean(centres)),):
            cv2.line(img, (80, y), (130, y), 0, 2)
    return img


def _detector_boxes(centres):
    # two sloppy detector boxes: too tall, shifted left (as on Litolff p3)
    return [(86.0, cy - 11.0, 112.0, cy + 11.0) for cy in centres]


def test_two_stacked_heads_split_to_standard_boxes_a_space_apart():
    centres = (100.0, 116.0)
    img = _page(centres)
    out = lg.split_chord_blob(img, _detector_boxes(centres), SP, W_SP, H_SP, TILT)
    assert out["split"], out
    (t, b) = out["boxes"]
    cys = [(t[1] + t[3]) / 2, (b[1] + b[3]) / 2]
    assert cys[0] == pytest.approx(100.0, abs=2.0)
    assert cys[1] == pytest.approx(116.0, abs=2.0)
    for box in (t, b):
        assert (box[3] - box[1]) == pytest.approx(H_SP * SP, abs=1.0)
        assert (box[2] - box[0]) == pytest.approx(W_SP * SP, abs=1.0)
    assert (t[0] + t[2]) / 2 == pytest.approx(100.0, abs=2.0)   # centred on the ink, not the box
    assert out["rung_y"] == pytest.approx(108.0, abs=2.0)
    # the pieces the lane reuses agree with each other
    assert lg.heads_are_a_third_apart(t, b, SP)


def test_single_head_is_not_split():
    img = _page((100.0,))
    out = lg.split_chord_blob(img, [(86.0, 90.0, 112.0, 112.0)], SP, W_SP, H_SP, TILT)
    assert out["split"] is False and out["reason"] == "below_trigger"


def test_three_stacked_heads_are_declined_not_guessed():
    centres = (84.0, 100.0, 116.0)
    img = _page(centres)
    out = lg.split_chord_blob(img, _detector_boxes(centres), SP, W_SP, H_SP, TILT)
    assert out["split"] is False and out["reason"] == "separation_not_a_third"


def test_cluster_takes_boxes_on_the_same_blob_only():
    a = (830.0, 383.0, 854.0, 405.0)
    b = (830.0, 398.0, 854.0, 418.0)      # same x, overlaps a in y
    far_x = (900.0, 390.0, 924.0, 410.0)   # a different chord
    far_y = (830.0, 460.0, 854.0, 480.0)   # next beat's head below, not touching
    assert lg.chord_blob_cluster(a, [b, far_x, far_y]) == [a, b]
