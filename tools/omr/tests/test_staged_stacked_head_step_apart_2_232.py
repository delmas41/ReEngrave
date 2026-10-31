"""ROADMAP 2.232 -- `OMR_STACKED_HEAD_STEP_APART`: the stack fit must not name a
head no detector box stands on, and a near-tie keeper is not an answer.

Pure pieces only (no raster, no record): the real places are the lane report's.
Control that can fail: the numbers are Litolff p3 `glyph/3/0/4/3/12` (boxes at
positions 3.24 and 0.88, the fit's single slot at 2.0)."""
import os
from unittest import mock

from tools.omr.staged import gather as G
from tools.omr.staged.adjudicators import notehead_precision as NP


def test_slot_between_two_boxes_is_a_head_nothing_drew():
    off = G.stacked_head_off_every_box([2.0], [3.24, 0.88])
    assert off is not None and abs(off - 1.12) < 1e-9


def test_slot_on_a_box_is_untouched():
    assert G.stacked_head_off_every_box([3.0], [3.24, 0.88]) is None
    # one head boxed twice: both boxes at one place
    assert G.stacked_head_off_every_box([7.0], [6.94, 6.88]) is None


def test_more_than_a_chord_of_thirds_is_out_of_domain():
    assert G.stacked_head_off_every_box([9.0], [10.12, 2.82]) is None


def test_k2_never_abstains_here():
    assert G.stacked_head_off_every_box([1.0, 3.0], [3.24, 0.88]) is None


def test_flags_default_on_and_switch_off():
    with mock.patch.dict(os.environ):
        os.environ.pop("OMR_STACKED_HEAD_STEP_APART", None)
        assert G.stacked_head_step_apart_enabled()
        assert NP.stacked_head_step_apart_enabled()
        os.environ["OMR_STACKED_HEAD_STEP_APART"] = "0"
        assert not G.stacked_head_step_apart_enabled()
        assert not NP.stacked_head_step_apart_enabled()


def test_box_centres_a_step_apart_cut_is_three_quarters_of_a_space():
    sp = 10.0
    upper = ("noteheadHalfInSpace", 0, 0.0, 14, 12)       # centre 6
    twin = ("noteheadBlackInSpace", 0, 3.0, 14, 12)       # centre 9: 0.3 sp
    third = ("noteheadBlackInSpace", 0, 12.0, 14, 12)     # centre 18: 1.2 sp
    assert not NP._box_centres_a_step_apart(upper, twin, sp)
    assert NP._box_centres_a_step_apart(upper, third, sp)
