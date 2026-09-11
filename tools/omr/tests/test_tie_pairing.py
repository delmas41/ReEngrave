"""`_pair_ties_in_staff` chooses its two sides TOGETHER, at one staff position.

The defect (`benchmarks/omr-tie-pairing-2026-09/FINDINGS.md`): each side was
chosen independently by minimum dx inside a y window three notehead heights
tall, so on a dense staff several positions qualified and nothing preferred the
one the arc actually binds — the "distance is nearly a coin flip" shape this
project has recorded for noteheads, hairpins and dynamic letters.

⚠️ Every test here asserts on WHICH HEADS are flagged, never on how many arcs
paired. Counting pairs cannot see a mispairing at all: a wrong pair is still one
pair. That is the same lesson the arc-export session paid for with a frame error
its span counts could not detect.
"""
from __future__ import annotations

import pytest

from tools.omr.export import _tie_flank_pair
from tools.omr.transcribe import (TIE_SAME_POSITION_MAX_SPACES,
                                  _pair_ties_in_staff)

#: One staff space. The heads below are 10 px tall, so the rule's own
#: `avg_nh_h` is 10 and a diatonic step is 5 px.
_H = 10
_STEP = _H / 2.0


def head(x, y, *, pitch="C4", width=10):
    return {"category": "notehead", "class": "noteheadBlack", "pitch": pitch,
            "bbox": [x, y, width, _H], "bbox_page": [x, y, width, _H],
            "confidence": 0.9}


def tie(x0, x1, y):
    """A tie arc flanking its heads — it spans the GAP between them."""
    return {"category": "structural", "class": "tie",
            "bbox": [x0, y, x1 - x0, 4], "bbox_page": [x0, y, x1 - x0, 4]}


def staff(*detections):
    return {"measures": [{"detections": list(detections)}]}


def flagged(st):
    """`{(x, key)}` for every flag actually set — the heads, not the count."""
    return {(d["bbox_page"][0], k)
            for m in st["measures"] for d in m["detections"]
            for k in ("tied_to_next", "tied_from_prev") if d.get(k)}


class TestThePositivesStillPair:
    """A battery that only REFUSES can pass by refusing everything."""

    def test_a_plain_tie_between_two_heads_at_one_position_still_pairs(self):
        a, b = head(0, 100), head(60, 100)
        st = staff(a, b, tie(12, 58, 100))
        assert _pair_ties_in_staff(st) == 1
        assert flagged(st) == {(0, "tied_to_next"), (60, "tied_from_prev")}

    def test_an_arc_with_no_head_on_one_side_pairs_nothing(self):
        st = staff(head(0, 100), head(20, 100), tie(60, 90, 100))
        assert _pair_ties_in_staff(st) == 0
        assert flagged(st) == set()


class TestTheTwoSidesAreChosenTogether:

    def test_the_pair_at_one_staff_position_beats_the_pair_nearest_in_x(self):
        """The Mozart 41 / Beethoven 5 geometry, in miniature.

        Two heads stand left of the arc: one a step BELOW it and nearer in x,
        one at the arc's own position and further. The old rule took the nearer
        and bound a third; this one binds the position the stop head is at.
        """
        near_wrong = head(40, 100 + _STEP, pitch="A3")
        far_right = head(22, 100, pitch="C4")
        stop = head(80, 100, pitch="C4")
        st = staff(near_wrong, far_right, stop, tie(55, 75, 100))
        _pair_ties_in_staff(st)
        assert flagged(st) == {(22, "tied_to_next"), (80, "tied_from_prev")}

    def test_the_stop_side_is_re_chosen_too_not_only_the_start(self):
        """Both sides, or the repair is half a repair — which is exactly the
        survivor the chord-tie session's battery found: every assertion named
        only the START."""
        start = head(20, 100, pitch="C4")
        near_wrong = head(58, 100 + _STEP, pitch="A3")
        far_right = head(78, 100, pitch="C4")
        st = staff(start, near_wrong, far_right, tie(35, 55, 100))
        _pair_ties_in_staff(st)
        assert flagged(st) == {(20, "tied_to_next"), (78, "tied_from_prev")}

    def test_with_no_candidate_pair_at_one_position_the_old_answer_stands(self):
        """ABSTAINING is a different, unpriced decision. Where the evidence
        does not discriminate the rule keeps the nearest-in-x answer, so the
        set of arcs that pair is untouched and every delta is a relocation."""
        left = head(20, 100, pitch="C4")
        right = head(78, 100 + _STEP, pitch="A3")
        st = staff(left, right, tie(35, 55, 100))
        assert _pair_ties_in_staff(st) == 1
        assert flagged(st) == {(20, "tied_to_next"), (78, "tied_from_prev")}

    def test_it_never_creates_a_pair_the_old_rule_refused(self):
        """The same-position branch runs only AFTER both sides have found a
        head by the old windows. Here nothing stands within the stop window,
        so the arc pairs nothing even though a same-position head sits just
        beyond it — a joint argmin over the product set would have rescued it.
        That would be a second change and it is deliberately not made: the
        exported tie COUNT must be provably unmoved."""
        st = staff(head(20, 100, pitch="C4"), head(40, 100 + _STEP,
                                                   pitch="A3"),
                   head(200, 100, pitch="C4"), tie(55, 75, 100))
        assert _pair_ties_in_staff(st) == 0
        assert flagged(st) == set()

    def test_it_reads_boxes_and_never_a_pitch(self):
        """The same claim off `pitch` would be `OMR_ARC_RECLASS`'s tie->slur
        veto, measured and REFUSED on scans. Relabelling both heads leaves the
        pairing identical."""
        st_a = staff(head(40, 100 + _STEP, pitch="A3"),
                     head(22, 100, pitch="C4"), head(80, 100, pitch="C4"),
                     tie(55, 75, 100))
        st_b = staff(head(40, 100 + _STEP, pitch="X9"),
                     head(22, 100, pitch="Q1"), head(80, 100, pitch="Z2"),
                     tie(55, 75, 100))
        _pair_ties_in_staff(st_a)
        _pair_ties_in_staff(st_b)
        assert flagged(st_a) == flagged(st_b)


class TestTheConstant:

    def test_half_a_step_is_inside_the_window_and_a_step_is_not(self):
        """The constant is half a staff space and a diatonic step is half a
        staff space, so the window admits ONE position and not two. Asserted
        against the value rather than restated: a sweep that moved it past a
        step would fail here even with every behavioural test green."""
        assert 0 < TIE_SAME_POSITION_MAX_SPACES < 0.5

    def test_a_head_beyond_the_window_does_not_win_the_pair(self):
        """The positive control for the assertion above: at just inside the
        window the same-position branch fires, at just outside it does not."""
        for offset, expect_far in ((TIE_SAME_POSITION_MAX_SPACES * _H * 0.5,
                                    True),
                                   (TIE_SAME_POSITION_MAX_SPACES * _H * 2.0,
                                    False)):
            st = staff(head(40, 100 + _STEP), head(22, 100 + offset),
                       head(80, 100), tie(55, 75, 100))
            _pair_ties_in_staff(st)
            start = 22 if expect_far else 40
            assert flagged(st) == {(start, "tied_to_next"),
                                   (80, "tied_from_prev")}, offset


class TestTheExportMirrorAgrees:
    """`export._tie_flank_pair` re-derives this relation for the
    `OMR_ARC_RECLASS` veto's bookkeeping. If the two drift, the veto clears one
    pair's flags while the export keeps another's.

    ⚠️ `test_export.TestArcReclass.test_flank_pair_mirrors_transcribes_pairing`
    already pins the mirror — on a fixture whose heads are all at ONE y, which
    the same-position branch cannot distinguish. That test is a name reaching
    only half its hazard; this one builds the case that separates them.
    """

    @pytest.mark.parametrize("arc,heads_spec", [
        ((55, 75), ((40, _STEP), (22, 0), (80, 0))),
        ((35, 55), ((20, 0), (58, _STEP), (78, 0))),
        ((35, 55), ((20, 0), (78, _STEP))),
    ])
    def test_the_mirror_agrees_where_the_branch_fires(self, arc, heads_spec):
        heads = [head(x, 100 + dy) for x, dy in heads_spec]
        st = staff(*[dict(h) for h in heads], tie(arc[0], arc[1], 100))
        _pair_ties_in_staff(st)
        mine = flagged(st)
        pair = _tie_flank_pair([arc[0], 100, arc[1] - arc[0], 4], heads)
        assert pair is not None
        left, right = pair
        assert mine == {(left["bbox_page"][0], "tied_to_next"),
                        (right["bbox_page"][0], "tied_from_prev")}
