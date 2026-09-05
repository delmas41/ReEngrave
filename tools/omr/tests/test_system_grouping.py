"""System grouping from vertical connectivity (tools/omr/system_grouping.py).

Synthetic pages: staves are five horizontal rules; a "barline" is a vertical
rule drawn through a run of staves, which is what the grouping reads.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tools.omr.staff_detector import _coverage_shift, detect_staves
from tools.omr.system_grouping import (
    GROUP_BOUNDARY_RATIO,
    assign_systems,
    gap_bridging_counts,
    _robust_x_window,
)
from tools.omr.types import PageImage, Staff

W, H = 1200, 1400
X0, X1 = 100, 1100
LINE_SPACING = 12


def _blank() -> np.ndarray:
    return np.full((H, W), 255, np.uint8)


def _draw_staff(img: np.ndarray, top: int, x0: int = X0, x1: int = X1) -> list[int]:
    ys = [top + LINE_SPACING * i for i in range(5)]
    for y in ys:
        img[y:y + 2, x0:x1] = 0
    return ys


def _draw_vrule(img: np.ndarray, x: int, y_top: int, y_bot: int, width: int = 3) -> None:
    img[y_top:y_bot, x:x + width] = 0


def _staves_from(line_groups: list[list[int]], x0: int = X0, x1: int = X1) -> list[Staff]:
    return [
        Staff(page_index=0, staff_index=i, line_ys=ys, x_start=x0, x_end=x1)
        for i, ys in enumerate(line_groups)
    ]


def _page(img: np.ndarray) -> PageImage:
    return PageImage(pdf_path=Path("synthetic.pdf"), page_index=0, dpi=300,
                     rgb=np.dstack([img] * 3), binary=img)


def _build(tops: list[int], rules: list[tuple[int, int]], n_rules: int = 6):
    """Draw staves at `tops`; draw `n_rules` vertical rules through each
    (first_staff, last_staff) span in `rules`. Returns (binary, staves)."""
    img = _blank()
    groups = [_draw_staff(img, t) for t in tops]
    for first, last in rules:
        y_top, y_bot = groups[first][0], groups[last][-1]
        for k in range(n_rules):
            _draw_vrule(img, X0 + 60 + k * 150, y_top, y_bot)
    return img, _staves_from(groups)


# ── gap_bridging_counts ─────────────────────────────────────────────────────

def test_bridging_counts_are_zero_across_a_system_break():
    # Two 2-staff systems; rules run through each system but not between them.
    img, staves = _build([100, 200, 500, 600], rules=[(0, 1), (2, 3)])
    counts = gap_bridging_counts(img, staves)
    assert len(counts) == 3
    assert counts[0] > 0, "gap inside system 1 is crossed"
    assert counts[1] == 0, "gap between the two systems is crossed by nothing"
    assert counts[2] > 0, "gap inside system 2 is crossed"


def test_bridging_counts_flag_degenerate_gaps_as_no_evidence():
    # Second staff overlaps the first: no gap band at all.
    img = _blank()
    groups = [_draw_staff(img, 100), _draw_staff(img, 130)]
    staves = _staves_from(groups)
    assert gap_bridging_counts(img, staves) == [-1]


def test_robust_x_window_ignores_a_broken_x_start():
    # Staff.x_start is the longest unbroken ink run, so a degraded scan can put
    # it far right (Beethoven 9 p60 staff 3: 885 against ~275 for neighbours).
    # The window is the median extent widened by WINDOW_MARGIN_SPACINGS, so it
    # must sit near 275/2485 and nowhere near the outlier.
    staves = _staves_from([[100 + LINE_SPACING * i] * 5 for i in range(5)])
    for s in staves:
        s.x_start, s.x_end = 275, 2485
    staves[2].x_start, staves[2].x_end = 885, 1826
    x0, x1 = _robust_x_window(staves)
    assert 200 < x0 <= 275, "outlier x_start must not drag the window right"
    assert 2485 <= x1 < 2560, "outlier x_end must not drag the window left"


def test_robust_x_window_reaches_past_the_staff_extent():
    """The bracket sits left of where the staff lines start and the closing
    barline right of where they end; a window clipped to the staff extent
    misses both (Beethoven 5 p10 at 600 dpi)."""
    staves = _staves_from([[100 + LINE_SPACING * i for i in range(5)]])
    staves[0].x_start, staves[0].x_end = 1000, 2000
    x0, x1 = _robust_x_window(staves)
    assert x0 < 1000 and x1 > 2000


# ── assign_systems ──────────────────────────────────────────────────────────

def test_two_systems_are_split():
    img, staves = _build([100, 200, 500, 600], rules=[(0, 1), (2, 3)])
    out, used = assign_systems(img, staves)
    assert used
    assert [s.system_index for s in out] == [0, 0, 1, 1]


def test_wide_bracket_group_gap_does_not_split_a_system():
    """The regression this module exists for: one system whose winds/brass/
    strings blocks are separated by gaps far larger than the intra-block gaps.
    The gap-size heuristic reports three systems; connectivity reports one."""
    tops = [100, 160, 220,        # block 1
            400, 460, 520,        # block 2 — 180px gap above, vs 60px within
            700, 760, 820]        # block 3
    img, staves = _build(tops, rules=[(0, 8)])
    out, used = assign_systems(img, staves)
    assert used
    assert {s.system_index for s in out} == {0}, "one bracket spans all nine staves"


def test_bracket_groups_are_recovered_within_a_system():
    """Barlines are drawn through every staff of a block but only the bracket
    crosses between blocks — so the between-block gaps bridge much less."""
    tops = [100, 160, 220, 400, 460, 520, 700, 760, 820]
    img = _blank()
    groups = [_draw_staff(img, t) for t in tops]
    # one full-height bracket for the whole system
    _draw_vrule(img, X0 + 20, groups[0][0], groups[-1][-1], width=4)
    # six barlines per block, not crossing between blocks
    for first, last in ((0, 2), (3, 5), (6, 8)):
        for k in range(6):
            _draw_vrule(img, X0 + 120 + k * 150, groups[first][0], groups[last][-1])
    staves = _staves_from(groups)
    out, used = assign_systems(img, staves)
    assert used
    assert {s.system_index for s in out} == {0}
    assert [s.group_index for s in out] == [0, 0, 0, 1, 1, 1, 2, 2, 2]


def test_falls_back_when_nothing_bridges_anywhere():
    """A page whose bracket and barlines are invisible: trusting connectivity
    would make every staff its own system, so the caller must fall back."""
    img = _blank()
    groups = [_draw_staff(img, t) for t in (100, 200, 300)]
    out, used = assign_systems(img, _staves_from(groups))
    assert not used, "no connectivity anywhere -> caller falls back to gap sizes"


def test_multi_column_layout_splits_regardless_of_connectivity():
    img, staves = _build([100, 200], rules=[(0, 1)])
    # Side-by-side columns: the two staves barely share any x range.
    staves[0].x_start, staves[0].x_end = 100, 560
    staves[1].x_start, staves[1].x_end = 640, 1100
    out, used = assign_systems(img, staves)
    assert used
    assert [s.system_index for s in out] == [0, 1]


def test_single_staff_page_is_one_system():
    img = _blank()
    staves = _staves_from([_draw_staff(img, 100)])
    out, used = assign_systems(img, staves)
    assert used
    assert [s.system_index for s in out] == [0]
    assert [s.group_index for s in out] == [0]


def test_staves_are_returned_sorted_by_y():
    img, staves = _build([100, 200, 500, 600], rules=[(0, 1), (2, 3)])
    shuffled = [staves[2], staves[0], staves[3], staves[1]]
    out, _used = assign_systems(img, shuffled)
    assert [s.top_y for s in out] == sorted(s.top_y for s in staves)


def test_group_index_defaults_to_zero_for_small_systems():
    img, staves = _build([100, 200], rules=[(0, 1)])
    out, _used = assign_systems(img, staves)
    assert [s.group_index for s in out] == [0, 0]


# ── end-to-end through detect_staves ────────────────────────────────────────

def test_detect_staves_uses_connectivity_grouping():
    tops = [100, 160, 220, 400, 460, 520, 700, 760, 820]
    img, _ = _build(tops, rules=[(0, 8)])
    pws = detect_staves(_page(img))
    assert len(pws.staves) == 9
    assert {s.system_index for s in pws.staves} == {0}


def test_detect_staves_finds_a_single_line_percussion_staff():
    """A one-line percussion staff is a staff, and the staves below it depend
    on it being counted: `_group_into_staves` accepts only five-peak windows,
    so before this the rule was invisible and every staff under it carried a
    staff_index one lower than its true slot."""
    img = _blank()
    _draw_staff(img, 100)
    _draw_staff(img, 260)
    img[420:422, X0:X1] = 0          # one-line percussion staff
    _draw_staff(img, 560)
    pws = detect_staves(_page(img))
    tops = sorted(s.top_y for s in pws.staves)
    assert len(pws.staves) == 4
    assert 420 in tops
    # It sits in its own slot, in page order, and the staff below it is the
    # fourth — which is the whole point of detecting it.
    perc = [s for s in pws.staves if s.top_y == 420][0]
    assert perc.staff_index == 2
    assert [s for s in pws.staves if s.top_y == 560][0].staff_index == 3
    # It has no spacing of its own, so it carries the page's.
    assert len(perc.line_ys) == 1
    assert perc.line_spacing_px == pytest.approx(LINE_SPACING, abs=1.0)


def test_two_percussion_rules_survive_a_shorter_line_between_them():
    """A trill line between two percussion parts must not take both down.

    The clearance rule rejects EVERY row in a tight cluster, which is right for
    two lines of one broken five-line staff and wrong here. Measured on Mahler 5
    p10: the Gr.Tr. rule (1857 px), the wavy trill printed between the parts
    (1410 px) and the Kl.Tr. rule (1858 px) — the two rules are 62 px apart and
    clear each other easily, but the trill sits 37 px and 25 px away, so all
    three were dropped and the page reported 18 staves instead of 20.
    """
    img = _blank()
    _draw_staff(img, 100)
    _draw_staff(img, 260)
    img[420:422, X0:X1] = 0                       # percussion rule
    img[455:457, X0:X0 + (X1 - X0) * 3 // 4] = 0  # shorter interloper between
    img[490:492, X0:X1] = 0                       # second percussion rule
    _draw_staff(img, 640)
    pws = detect_staves(_page(img))

    tops = sorted(s.top_y for s in pws.staves)
    assert 420 in tops, "first percussion rule lost to the interloper"
    assert 490 in tops, "second percussion rule lost to the interloper"
    assert 455 not in tops, "the short interloper was admitted as a staff"
    assert len(pws.staves) == 5


def test_an_interloper_is_not_charged_twice():
    """The same stray ink must not reject a rule via a second gate.

    An interloper dropped from the cluster used to come straight back as "the
    rest of a five-line staff" — `_has_the_rest_of_a_staff` probes one and two
    staff spaces out and does not care what it finds. Mahler 5 p10: the trill
    line at row 1743 is dropped as an interloper, then reappears two spacings
    above Kl.Tr. (run 1410 against a 929 threshold) and rejects it, so the page
    stopped at 19 staves of 20. Here the interloper sits EXACTLY two spacings
    above the lower rule, which is the position that triggered it.
    """
    img = _blank()
    _draw_staff(img, 100)
    _draw_staff(img, 260)
    rule_a = 420
    rule_b = rule_a + 2 * LINE_SPACING + 26      # clear of the interloper itself
    interloper = rule_b - 2 * LINE_SPACING       # exactly where the gate probes
    img[rule_a:rule_a + 2, X0:X1] = 0
    img[interloper:interloper + 2, X0:X0 + (X1 - X0) * 3 // 4] = 0
    img[rule_b:rule_b + 2, X0:X1] = 0
    _draw_staff(img, 640)
    pws = detect_staves(_page(img))

    tops = sorted(s.top_y for s in pws.staves)
    assert rule_a in tops, "upper percussion rule lost"
    assert rule_b in tops, "lower rule rejected by the interloper via the staff gate"
    assert interloper not in tops
    assert len(pws.staves) == 5


def test_a_cluster_of_equal_length_rules_is_still_rejected():
    """The interloper filter must not weaken the rule it guards. Two rows of
    the SAME length close together really are more likely two lines of one
    five-line staff, and both must still be refused."""
    img = _blank()
    _draw_staff(img, 100)
    _draw_staff(img, 260)
    img[420:422, X0:X1] = 0
    img[450:452, X0:X1] = 0      # same length, within clearance
    _draw_staff(img, 600)
    pws = detect_staves(_page(img))

    tops = sorted(s.top_y for s in pws.staves)
    assert 420 not in tops and 450 not in tops
    assert len(pws.staves) == 3


def test_a_lone_rule_outside_the_staves_is_not_a_staff():
    """A page border, a title rule or a footer is one long inked row too. What
    separates a percussion staff from them is that it stands BETWEEN the
    page's staves, not outside them."""
    img = _blank()
    img[60:62, X0:X1] = 0            # rule above all the music
    _draw_staff(img, 200)
    _draw_staff(img, 360)
    img[900:902, X0:X1] = 0          # rule below all the music
    pws = detect_staves(_page(img))
    assert len(pws.staves) == 2
    assert sorted(s.top_y for s in pws.staves) == [200, 360]


def test_two_surviving_lines_of_one_staff_are_not_two_percussion_staves():
    """The dangerous confusion: a five-line staff printed too lightly to group
    can leave one or two of its lines behind, and those look exactly like a
    percussion rule. Rows within a staff's height of each other are therefore
    both refused."""
    img = _blank()
    _draw_staff(img, 100)
    _draw_staff(img, 700)
    # Two lines of a would-be staff between them, one staff space apart.
    img[400:402, X0:X1] = 0
    img[400 + LINE_SPACING:402 + LINE_SPACING, X0:X1] = 0
    pws = detect_staves(_page(img))
    assert len(pws.staves) == 2, "neither stray line may become a staff"


def test_the_rest_of_a_staff_is_looked_for_on_the_page():
    """The veto that carries this rule, tested directly.

    A lone inked row is what a percussion staff looks like AND what is left of
    a five-line staff whose other lines failed the peak gates — measured on
    Beethoven 5 at 300 DPI, where a clarinet staff and a first-violin staff
    both arrived as one full-width row. The lines are still printed, so the
    question is asked of the page.
    """
    from tools.omr.staff_detector import _has_the_rest_of_a_staff

    img = _blank()
    ys = _draw_staff(img, 400)
    assert _has_the_rest_of_a_staff(img, ys[2], LINE_SPACING, X0, X1) is True

    lone = _blank()
    lone[400:402, X0:X1] = 0
    assert _has_the_rest_of_a_staff(lone, 400, LINE_SPACING, X0, X1) is False


def test_a_lone_line_of_a_printed_staff_is_not_a_percussion_staff():
    """End to end: a staff printed too faintly for four of its five lines to
    clear the peak gates must not have its survivor promoted to a staff of its
    own. The faint lines here are one pixel of grey, below the ink threshold
    the row pass works on, but still visibly line."""
    img = _blank()
    _draw_staff(img, 100)
    _draw_staff(img, 900)
    # A staff at 500 whose middle line is fully printed and whose other four
    # arrive as 4px dashes — a third of the ink the row pass demands, so it
    # never sees them, but unmistakably line to anything that looks at the
    # page. Checked by mutation: with the veto disabled this fixture reports a
    # one-line staff at y=524.
    for i in range(5):
        y = 500 + LINE_SPACING * i
        if i == 2:
            img[y:y + 2, X0:X1] = 0
        else:
            for x in range(X0, X1, 16):
                img[y:y + 1, x:x + 4] = 0
    pws = detect_staves(_page(img))
    assert [len(s.line_ys) for s in pws.staves] == [5, 5], (
        "the survivor of a five-line staff was promoted to a staff of its own"
    )


def test_a_short_rule_between_staves_is_not_a_staff():
    """A percussion rule is as long as the page's staves. A hairpin, a bracket
    edge or a fragment of text is not."""
    img = _blank()
    _draw_staff(img, 100)
    _draw_staff(img, 700)
    # 460px against a 1000px staff: long enough to clear the peak pass's own
    # length gate (35% of the page), so it is this rule's width test that has
    # to refuse it.
    img[400:402, X0:X0 + 460] = 0
    pws = detect_staves(_page(img))
    assert len(pws.staves) == 2


# ── step 3d: windows that locked onto a beam ────────────────────────────────

class TestMisalignedWindow:
    """A five-line window that slid onto a beam reads every note a space low.

    Measured on the engraved Brahms 1 fixture, staff 20 (Contrabass): an 18 px
    "line" against 5 px for the rest, window internally consistent (spacing 41,
    span 164, both normal), and every note a third flat — truth 42 x C3 read as
    Ab2. That one staff produced 42 of the page's 65 wrong pitches.

    The synthetic beams below are 5-6 px against 2 px lines, which keeps the
    ratio near the real 18:5. Scaling it up breaks the peak grouper instead,
    which is a different failure and not what this is about.
    """

    def test_a_thick_end_line_slides_the_window_back(self):
        img = _blank()
        _draw_staff(img, 100)
        _draw_staff(img, 260)
        # A real five-line staff, plus a thick beam one spacing ABOVE it. The
        # grouper takes beam + the first four lines and misses the real fifth.
        top = 500
        for k in range(5):
            y = top + k * LINE_SPACING
            img[y:y + 2, X0:X1] = 0
        img[top - LINE_SPACING:top - LINE_SPACING + 5, X0:X1] = 0
        pws = detect_staves(_page(img))

        near = [s for s in pws.staves if abs(s.top_y - top) <= LINE_SPACING]
        assert near, "the staff under the beam was not detected at all"
        staff = near[0]
        assert staff.top_y == top, (
            f"window still sitting on the beam: top_y={staff.top_y}, want {top}")
        assert staff.line_thickness_px == [2.0, 2.0, 2.0, 2.0, 2.0]

    def test_a_thick_MIDDLE_line_is_left_alone(self):
        """A thick line with real lines either side is a beam crossing a staff
        that is placed correctly — Brahms staff 8. Moving it would be the bug."""
        img = _blank()
        _draw_staff(img, 100)
        top = 400
        for k in range(5):
            y = top + k * LINE_SPACING
            img[y:y + (6 if k == 2 else 2), X0:X1] = 0
        _draw_staff(img, 700)
        pws = detect_staves(_page(img))

        near = [s for s in pws.staves if abs(s.top_y - top) <= 2]
        assert near, "staff with a fat middle line was lost"
        assert near[0].top_y == top, "a pinned middle outlier moved the window"
        assert near[0].line_thickness_px[2] == 6.0, "the fat line was not kept"

    def test_no_replacement_line_means_no_move(self):
        """The row a slid window would need must actually carry a printed line.
        With nothing there the staff is left as it was, because a staff invented
        in the wrong place is worse than one read a space low."""
        img = _blank()
        _draw_staff(img, 100)
        top = 500
        for k in range(5):
            y = top + k * LINE_SPACING
            img[y:y + 2, X0:X1] = 0
        img[top - LINE_SPACING:top - LINE_SPACING + 5, X0:X1] = 0
        # Blank the row the slid window would need.
        img[top + 5 * LINE_SPACING - 3:top + 5 * LINE_SPACING + 6, :] = 255
        pws = detect_staves(_page(img))
        assert pws.staves, "page lost all staves"
        near = [s for s in pws.staves if abs(s.top_y - top) <= LINE_SPACING]
        assert near, "staff disappeared entirely"
        # It stays where it was — on the beam — rather than being invented lower.
        assert near[0].top_y != top + LINE_SPACING


class TestShortEndLineWindow:
    """The same fault told by COVERAGE, which is the half thickness misses.

    Brahms's Violin 1 locked onto two LEDGER LINES above its staff. They are
    printed at staff weight — thickness ratio 1.8, no outlier — but they cover
    4% and 6% of the staff's width where a real line covers all of it. The
    window sat two spaces high and 35 of that part's 39 notes came out four
    staff positions low, at a cost of 263 OMR-NED edits.

    Measured over 270 staves and 5 editions, the worse end line's coverage
    divided by the staff's median is 0.041-0.112 for the six misfitted windows
    and 0.682 or more for every correctly placed staff.
    """

    @staticmethod
    def _staff_with_stubs(top: int, n_stubs: int, stub_frac: float = 0.05):
        """A real five-line staff with `n_stubs` short rows above it, spaced
        like lines. The grouper takes the stubs plus the staff's first
        `5 - n_stubs` lines and misses the rest."""
        img = _blank()
        _draw_staff(img, 100)
        for k in range(5):
            y = top + k * LINE_SPACING
            img[y:y + 2, X0:X1] = 0
        stub_end = X0 + int((X1 - X0) * stub_frac)
        for i in range(1, n_stubs + 1):
            y = top - i * LINE_SPACING
            img[y:y + 2, X0:stub_end] = 0
        return img

    def test_one_short_end_line_slides_the_window_by_one(self):
        top = 500
        pws = detect_staves(_page(self._staff_with_stubs(top, 1)))
        near = [s for s in pws.staves if abs(s.top_y - top) <= 2 * LINE_SPACING]
        assert near, "the staff under the stub was not detected at all"
        assert near[0].top_y == top, (
            f"window still on the stub: top_y={near[0].top_y}, want {top}")

    def test_two_short_end_lines_slide_the_window_by_two(self):
        """Brahms Violin 1's case. The old rule could only ever slide by one,
        so even a thickness outlier would have left this two-space misfit."""
        top = 500
        pws = detect_staves(_page(self._staff_with_stubs(top, 2)))
        near = [s for s in pws.staves if abs(s.top_y - top) <= 3 * LINE_SPACING]
        assert near, "the staff under the stubs was not detected at all"
        assert near[0].top_y == top, (
            f"window still on the stubs: top_y={near[0].top_y}, want {top}")

    def test_a_faint_but_full_length_line_is_left_alone(self):
        """A correctly placed staff on a poor scan has SHORTER lines, not short
        ones — lamer-p25 staff 16 covers 0.51-0.88 and must not move. The test
        is relative to the staff's own median, which is why it survives."""
        img = _blank()
        _draw_staff(img, 100)
        top = 500
        width = X1 - X0
        for k in range(5):
            y = top + k * LINE_SPACING
            # Every line partial, the end ones a little more so — the shape of
            # a faint scan rather than of a misfit.
            end = X0 + int(width * (0.6 if k in (0, 4) else 0.8))
            img[y:y + 2, X0:end] = 0
        pws = detect_staves(_page(img))
        near = [s for s in pws.staves if abs(s.top_y - top) <= 2 * LINE_SPACING]
        assert near, "faint staff was lost"
        assert near[0].top_y == top, "a faint but correctly placed staff moved"

    # A dropout in the MIDDLE cannot be tested end-to-end: a middle line short
    # enough to be coverage-bad is also short enough that the peak gates never
    # group the staff at all, so there is no window to leave alone. The rule
    # itself is pinned directly in TestCoverageShift.


class TestCoverageShift:
    """`_coverage_shift` alone, on the exact coverage vectors that were measured."""

    @pytest.mark.parametrize("coverage, expected", [
        # brahms-e2e staff 16 — two ledger lines on top, slide down two.
        ([0.041, 0.055, 1.0, 1.0, 1.0], 2),
        # bolero-p31 staff 11 — same shape.
        ([0.055, 0.026, 1.0, 1.0, 1.0], 2),
        # bolero-p5 staff 12 — one, slide down one.
        ([0.107, 1.0, 1.0, 1.0, 1.0], 1),
        # beet5-p2 staff 18 — one, on a faint scan where the real lines are 0.7.
        ([0.05, 0.655, 0.694, 0.758, 0.659], 1),
        # A bad line at the BOTTOM slides the other way.
        ([1.0, 1.0, 1.0, 1.0, 0.05], -1),
        # lamer-p25 staff 16 — correctly placed, last row 2px off its line.
        ([0.746, 0.743, 0.878, 0.773, 0.509], 0),
        # beet5-p2 staff 2 — a faint scan, correctly placed.
        ([0.485, 0.664, 0.573, 0.619, 0.645], 0),
        # A clean staff.
        ([1.0, 1.0, 1.0, 1.0, 1.0], 0),
        # A dropout in the middle: no slide fixes it.
        ([1.0, 1.0, 0.04, 1.0, 1.0], 0),
        # Bad at BOTH ends: not a misplaced window, so no verdict.
        ([0.04, 1.0, 1.0, 1.0, 0.04], 0),
        # Three off one end is past MISFIT_MAX_SHIFT — no line in common with
        # the true staff, so no evidence it is the same staff.
        ([0.04, 0.04, 0.04, 1.0, 1.0], 0),
    ])
    def test_shift(self, coverage, expected):
        assert _coverage_shift(coverage) == expected


# ── cue B: pair-local left-edge merge (OMR_CHOIR_GROUPING) ──────────────────
#
# The Brandenburg-3 family (benchmarks/omr-choir-grouping-2026-09/FINDINGS.md):
# two systems indented DIFFERENTLY, interior barlines drawn per instrument
# choir. The page-median window lands between the two indentation modes and
# cuts the full-width system's left-edge complex out of the scan, so its choir
# gaps read bridging = 0 and the system shatters — while the same page still
# prints a systemic barline through every within-system gap, at the pair's own
# left edge, where cue B looks.

def _choir_page():
    """Two 6-staff systems: system 1 indented (x_start 500), system 2 full
    width (x_start 120). Interior barlines per 3-staff choir; one systemic
    barline at each system's own left edge crossing all six of its staves.
    The page-median window ([~262, ...]) sees system 1's left rule (x 510)
    but not system 2's (x 130)."""
    img = _blank()
    tops = [100, 200, 300, 400, 500, 600,     # system 1 (indented)
            800, 900, 1000, 1100, 1200, 1300]  # system 2 (full width)
    groups = [_draw_staff(img, t, x0=(500 if i < 6 else 120), x1=X1)
              for i, t in enumerate(tops)]
    staves = [
        Staff(page_index=0, staff_index=i, line_ys=ys,
              x_start=(500 if i < 6 else 120), x_end=X1)
        for i, ys in enumerate(groups)
    ]
    # systemic barline at each system's own left edge, through all its staves
    _draw_vrule(img, 510, groups[0][0], groups[5][-1])
    _draw_vrule(img, 130, groups[6][0], groups[11][-1])
    # interior barlines per choir: staves 0-2 / 3-5 of each system
    for first, last in ((0, 2), (3, 5), (6, 8), (9, 11)):
        for k in range(5):
            _draw_vrule(img, 560 + k * 100, groups[first][0], groups[last][-1])
    return img, staves


def test_choir_page_shatters_without_cue_b():
    """Fixture-validity guard (the disease, not desired behavior): with cue B
    off, the wide window cannot see system 2's left rule, so system 2 splits
    at its choir gap. If this starts passing as two systems, upstream grouping
    has begun handling bimodal indentation on its own and the fixture must be
    re-picked — a finding, not a bug."""
    img, staves = _choir_page()
    out, used = assign_systems(img, staves, left_edge_split=False,
                               choir_grouping=False)
    assert used
    sys2 = {s.system_index for s in out if s.staff_index >= 6}
    assert len(sys2) > 1, "system 2 must still shatter without cue B"
    sys1 = {s.system_index for s in out if s.staff_index < 6}
    assert len(sys1) == 1, "the indented system's left rule is in-window; it holds"


def test_cue_b_merges_the_window_blind_break():
    img, staves = _choir_page()
    out, used = assign_systems(img, staves, left_edge_split=False,
                               choir_grouping=True)
    assert used
    assert [s.system_index for s in out] == [0] * 6 + [1] * 6


def test_cue_b_never_merges_the_true_system_break():
    """The gap between the two systems is crossed by nothing, in any window —
    cue B must leave it alone (it is also >1 gap wide in the pair band)."""
    img, staves = _choir_page()
    out, _ = assign_systems(img, staves, left_edge_split=False,
                            choir_grouping=True)
    assert out[5].system_index != out[6].system_index


def test_cue_b_marks_merged_choir_gaps_as_group_boundaries():
    """bridging[] stays 0 at a merged gap, so _assign_groups reads the choirs
    as bracket groups of one system — the true structure."""
    img, staves = _choir_page()
    out, _ = assign_systems(img, staves, left_edge_split=False,
                            choir_grouping=True)
    sys2_groups = [s.group_index for s in out if s.system_index == 1]
    assert sys2_groups == [0, 0, 0, 1, 1, 1]


def test_cue_b_never_touches_a_multi_column_break():
    """Two side-by-side columns share almost no x range and are different
    systems whatever crosses at the left column's edge."""
    img, staves = _build([100, 200], rules=[(0, 1)])
    staves[0].x_start, staves[0].x_end = 100, 560
    staves[1].x_start, staves[1].x_end = 640, 1100
    # a vertical rule crossing the gap at the pair's min x_start — bait cue B
    _draw_vrule(img, 105, 100, 200 + LINE_SPACING * 5)
    out, used = assign_systems(img, staves, left_edge_split=False,
                               choir_grouping=True)
    assert used
    assert [s.system_index for s in out] == [0, 1]


def test_cue_b_is_on_by_default(monkeypatch):
    # Shipped default-ON 2026-09-05, coupled with Bach's pool re-admission.
    monkeypatch.delenv("OMR_CHOIR_GROUPING", raising=False)
    img, staves = _choir_page()
    out, _ = assign_systems(img, staves, left_edge_split=False)
    assert [s.system_index for s in out] == [0] * 6 + [1] * 6


def test_cue_b_explicit_off_restores_the_old_grouping(monkeypatch):
    monkeypatch.setenv("OMR_CHOIR_GROUPING", "0")
    img, staves = _choir_page()
    out, _ = assign_systems(img, staves, left_edge_split=False)
    sys2 = {s.system_index for s in out if s.staff_index >= 6}
    assert len(sys2) > 1, "explicit 0 means cue B must not run"


def test_cue_b_env_flag_enables(monkeypatch):
    monkeypatch.setenv("OMR_CHOIR_GROUPING", "1")
    img, staves = _choir_page()
    out, _ = assign_systems(img, staves, left_edge_split=False)
    assert [s.system_index for s in out] == [0] * 6 + [1] * 6


def _bimodal_page_where_cue_a_would_resplit():
    """Cue A's gate passes (most interior gaps crossed at the page-median
    band) while one cue-B-merged gap reads empty there — the Mozart 40 p32
    shape. Four indented staves (x_start 500, systemic rule at 510 = inside
    the page-median band) over three full-width staves (x_start 120, systemic
    rule at 130, choir-barred: an interior barline at 510 crosses the first
    of its gaps but nothing in-window crosses the second)."""
    img = _blank()
    tops = [100, 200, 300, 400,      # system 1, indented
            700, 800, 900]           # system 2, full width
    groups = [_draw_staff(img, t, x0=(500 if i < 4 else 120), x1=X1)
              for i, t in enumerate(tops)]
    staves = [
        Staff(page_index=0, staff_index=i, line_ys=ys,
              x_start=(500 if i < 4 else 120), x_end=X1)
        for i, ys in enumerate(groups)
    ]
    _draw_vrule(img, 510, groups[0][0], groups[3][-1])    # sys1 systemic rule
    _draw_vrule(img, 130, groups[4][0], groups[6][-1])    # sys2 systemic rule
    # sys1 interior barlines (keep its gaps clearly bridged in the window)
    for k in range(4):
        _draw_vrule(img, 620 + k * 110, groups[0][0], groups[3][-1])
    # sys2 interior barline at the page-median band's x, crossing ONLY the
    # first of its two gaps (choir-barred below)
    _draw_vrule(img, 510, groups[4][0], groups[5][-1])
    return img, staves


def test_cue_b_merge_is_exempt_from_cue_a_resplit():
    img, staves = _bimodal_page_where_cue_a_would_resplit()
    # flag off: the second gap of system 2 is broken (its only witness, the
    # rule at x=130, is left of the page-median window) — with cue A active.
    out, _ = assign_systems(img, staves, left_edge_split=True,
                            choir_grouping=False)
    assert out[5].system_index != out[6].system_index, (
        "fixture validity: without cue B the choir-barred gap must break")
    # flag on: cue B merges it on the pair-local rule at x=130, and cue A —
    # whose page-median band cannot see that x — must not re-split it.
    out, _ = assign_systems(img, staves, left_edge_split=True,
                            choir_grouping=True)
    assert [s.system_index for s in out] == [0, 0, 0, 0, 1, 1, 1]
