"""ROADMAP 2.12g — collapse role-twin detector channels before NMS.

Unit-level: exercises `yolo_detector._collapse_role_twins` directly, no
model load and no real `MeasureCell` — the function only reads
`cell.staff_line_ys_canonical` via `getattr`, so a tiny stand-in with just
that attribute is the whole fixture.
"""
from __future__ import annotations

from types import SimpleNamespace

from tools.omr.template_matcher import SymbolDetection
from tools.omr import yolo_detector as yd


def _cell(spacing_px: float | None = 20.0):
    """A stand-in `cell` with staff lines CANONICAL_SPACE px apart -- or no
    staff lines at all when `spacing_px` is None."""
    if spacing_px is None:
        return SimpleNamespace(staff_line_ys_canonical=[])
    ys = [0, spacing_px, spacing_px * 2, spacing_px * 3, spacing_px * 4]
    return SimpleNamespace(staff_line_ys_canonical=ys)


def _det(smufl_name, x, y, w=20, h=20, conf=0.5, category="notehead"):
    return SymbolDetection(
        cell=None, smufl_name=smufl_name, category=category,
        x_canonical=x, y_canonical=y, width_canonical=w, height_canonical=h,
        confidence=conf,
    )


def test_twin_pair_collapses_to_one_box_keeping_higher_score():
    """Two role-twin boxes on the SAME ink (near-identical position) ->
    one box after the collapse, carrying the higher score and recording
    the dropped twin's class on `detector_role`."""
    a = _det("noteheadBlackOnLine", 100, 200, conf=0.40)
    b = _det("noteheadBlackInSpace", 101, 201, conf=0.83)
    out = yd._collapse_role_twins([a, b], _cell())
    assert len(out) == 1
    survivor = out[0]
    assert survivor.smufl_name == "noteheadBlackInSpace"  # higher score kept
    assert survivor.confidence == 0.83
    assert survivor.detector_role == "noteheadBlackOnLine"  # dropped twin recorded


def test_iou_near_full_overlap_different_suffix_also_collapses():
    """A near-exact IoU-0.94-style pair (the audit's own fixture shape) —
    not just a tiny jitter — still collapses to one box."""
    a = _det("noteheadHalfOnLine", 50, 50, w=24, h=24, conf=0.60)
    b = _det("noteheadHalfInSpace", 51, 50, w=24, h=24, conf=0.55)
    out = yd._collapse_role_twins([a, b], _cell())
    assert len(out) == 1
    assert out[0].smufl_name == "noteheadHalfOnLine"
    assert out[0].detector_role == "noteheadHalfInSpace"


def test_different_shapes_overlapping_are_untouched():
    """Two genuinely different shapes (not a twin pair) overlapping must
    NOT be merged — only the role-suffix twin test may collapse a pair."""
    a = _det("noteheadBlackOnLine", 100, 200, conf=0.5)
    b = _det("restWhole", 100, 200, conf=0.5, category="rest")
    out = yd._collapse_role_twins([a, b], _cell())
    assert len(out) == 2
    assert {d.smufl_name for d in out} == {"noteheadBlackOnLine", "restWhole"}
    assert all(d.detector_role is None for d in out)


def test_real_chord_second_different_y_is_untouched():
    """Two heads of a real chord, same shape family but at DIFFERENT staff
    positions (not the same mark twice) — must survive as two boxes, same
    as `notehead_precision._same_mark_centres` (2.30) requires for an
    ownership-side duplicate test."""
    # A chord second a third away: one staff space (20px here) of y
    # separation is far more than the 0.25-space gate allows.
    a = _det("noteheadBlackOnLine", 100, 200, conf=0.5)
    b = _det("noteheadBlackOnLine", 100, 230, conf=0.5)  # same suffix even
    out = yd._collapse_role_twins([a, b], _cell())
    assert len(out) == 2


def test_chord_second_offset_in_x_is_untouched():
    """A twin-suffix pair at the SAME y but far apart in x (two distinct
    heads in the bar, not one piece of ink) must not merge."""
    a = _det("noteheadBlackOnLine", 100, 200, w=20, conf=0.5)
    b = _det("noteheadBlackInSpace", 300, 200, w=20, conf=0.5)
    out = yd._collapse_role_twins([a, b], _cell())
    assert len(out) == 2


def test_no_staff_geometry_abstains_the_whole_cell_from_merging():
    """CLAUDE.md rule 8: cannot measure locally -> leave untouched, never
    guess a merge."""
    a = _det("noteheadBlackOnLine", 100, 200, conf=0.4)
    b = _det("noteheadBlackInSpace", 101, 201, conf=0.8)
    out = yd._collapse_role_twins([a, b], _cell(spacing_px=None))
    assert len(out) == 2


def test_same_suffix_pair_is_not_this_rule_s_job():
    """Two boxes of the SAME role spelling on the same ink (not a role
    TWIN — a plain same-class duplicate) are untouched here: that is
    `notehead_precision._notehead_duplicate_box_refusal` (ROADMAP 2.30)'s
    question in ADJUDICATE, not a role-twin question in GATHER."""
    a = _det("noteheadBlackInSpace", 100, 200, conf=0.3)
    b = _det("noteheadBlackInSpace", 101, 200, conf=0.9)
    out = yd._collapse_role_twins([a, b], _cell())
    assert len(out) == 2


def test_total_count_never_falls_below_the_distinct_ink_population():
    """The GATE (ROADMAP 2.12g): collapsing N boxes that are M distinct
    pieces of ink (M < N twins + K untouched) must leave exactly the
    distinct-ink count, never fewer — merge, never delete beyond the
    twin itself."""
    pairs_and_singles = [
        _det("noteheadBlackOnLine", 0, 0, conf=0.4),
        _det("noteheadBlackInSpace", 1, 1, conf=0.9),   # twin of the above
        _det("noteheadBlackOnLine", 500, 0, conf=0.7),  # lone box, no twin
        _det("restWhole", 900, 0, conf=0.6, category="rest"),
    ]
    out = yd._collapse_role_twins(pairs_and_singles, _cell())
    assert len(out) == 3  # 4 boxes, 1 twin pair merged -> 3 distinct pieces of ink
