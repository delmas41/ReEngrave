"""ROADMAP 2.172 follow-up: the export coverage report counts detector-view boxes by view."""
from tools.omr.staged import export as SX
from tools.omr.staged.record import Q


class _Rec:
    def __init__(self, obs, abst):
        self.observations, self.abstentions = obs, abst

    def obs_of(self, q):
        return [o for o in self.observations if o["quantity"] == q]


def test_census_counts_by_view():
    box = lambda v, fam, ph: {"quantity": Q.GLYPH_BOX, "detail": {"view": v, "family": fam, "phases_found": ph}}
    near = {"quantity": Q.GLYPH_BOX, "detail": {"view": "close", "candidate_class": "noteheadBlack",
                                                 "box_canonical": [1, 2, 3, 4]}}
    plain = {"quantity": Q.GLYPH_BOX, "detail": {"category": "x"}}
    c = SX._detector_view_census(_Rec([box("small", "notehead", 3), box("small", "notehead", 2),
                                       box("close", "accidental", 3), plain], [near]))
    assert c["kept_by_view_family"] == {"small": {"notehead": 2}, "close": {"accidental": 1}}
    assert c["phases_found_by_view"]["small"] == {"3": 1, "2": 1}
    assert c["refused_near_miss_by_view_class"] == {"close": {"noteheadBlack": 1}}
    assert c["refused_with_canonical_box"] == 1
