"""`Barline` carries the evidence `detect_barlines` weighed, not just an x.

Until 2026-09-06 all five `Barline` fields were coordinates, and the vote
count, the inter-system connectivity, the span-ink score and which of four
acceptance prongs fired were all computed and then dropped at the constructor.
These tests pin that each is now recorded, and — as importantly — that the
fields still default to `None` so an unannotated construction site keeps
working.

⚠️ **Every assertion here was run RED first** by deleting the `_record(...)`
calls in `detect_barlines` (and, for the compatibility test, by making a field
required). A test that passes with the mechanism removed is worse than no
test; this repo has had one.

Synthetic fixtures only — no PDF on disk, so these run in a default
`pytest tools/omr/tests` invocation.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tools.omr.measure_extractor import detect_barlines
from tools.omr.types import Barline, PageImage, PageWithStaves, Staff

EVIDENCE_FIELDS = (
    "n_votes", "n_staves_in_system", "min_votes", "connectivity",
    "span_ink", "accept_prong", "barlines_cross_gaps",
    "choir_cue_c_override",
)

ACCEPT_PRONGS = {
    "vote_small_system", "span_rescue_small_system", "vote_open_score",
    "vote_and_connectivity", "connectivity_rescue",
}


def _five(top: int, spacing: int = 20) -> list[int]:
    return [top + spacing * i for i in range(5)]


def _page(img: np.ndarray, staves: list[Staff]) -> PageWithStaves:
    page = PageImage(pdf_path=Path("synthetic.pdf"), page_index=0, dpi=300,
                     rgb=np.dstack([img] * 3), binary=img)
    return PageWithStaves(page=page, staves=staves)


def _orchestral_page(n_staves: int = 6) -> PageWithStaves:
    """One system of `n_staves`, barlines drawn through every staff AND
    through the gaps between them — the conductor's-page shape, which is what
    makes connectivity meaningful and puts acceptance on prong A."""
    tops = [100 + 100 * i for i in range(n_staves)]
    all_ys = [_five(t) for t in tops]
    img = np.full((tops[-1] + 300, 1000), 255, np.uint8)
    for ys in all_ys:
        for y in ys:
            img[y:y + 2, 40:960] = 0
    for x in (60, 260, 460, 660, 860):
        img[all_ys[0][0]:all_ys[-1][-1] + 2, x:x + 3] = 0
    staves = []
    for i, ys in enumerate(all_ys):
        s = Staff(page_index=0, staff_index=i, line_ys=ys,
                  x_start=40, x_end=960, system_index=0)
        staves.append(s)
    return _page(img, staves)


def _open_score_page(n_staves: int = 6) -> PageWithStaves:
    """The same lineup, but every barline stops at its own staff — the open
    score. `barlines_cross_gaps` must come back False and acceptance must be
    on the votes alone."""
    tops = [100 + 100 * i for i in range(n_staves)]
    all_ys = [_five(t) for t in tops]
    img = np.full((tops[-1] + 300, 1000), 255, np.uint8)
    for ys in all_ys:
        for y in ys:
            img[y:y + 2, 40:960] = 0
        for x in (60, 260, 460, 660, 860):
            img[ys[0]:ys[-1] + 2, x:x + 3] = 0
    staves = [Staff(page_index=0, staff_index=i, line_ys=ys,
                    x_start=40, x_end=960, system_index=0)
              for i, ys in enumerate(all_ys)]
    return _page(img, staves)


def _braced_pair(stem_on_lower: bool) -> PageWithStaves:
    """A two-staff braced system: n_staves < 3, so acceptance takes the
    small-system path (vote first, span rescue second).

    With `stem_on_lower` the lower staff also carries a full-height stroke a
    little LEFT of each barline. Per-staff thinning keeps the leftmost
    candidate, so the lower staff votes for the stem instead of the barline,
    the barline's cluster is left one vote short of the two a 2-staff system
    needs — and only `_spans_system` can rescue it. That is the WTC prelude
    failure this branch of the code exists for.
    """
    ys0, ys1 = _five(100), _five(240)
    img = np.full((500, 1000), 255, np.uint8)
    for ys in (ys0, ys1):
        for y in ys:
            img[y:y + 2, 40:960] = 0
    for x in (200, 400, 600, 800):
        img[ys0[0] - 5:ys1[-1] + 7, x:x + 3] = 0          # spans the system
        if stem_on_lower:
            img[ys1[0]:ys1[-1] + 2, x - 40:x - 37] = 0    # decoy on staff 1
    staves = [
        Staff(page_index=0, staff_index=0, line_ys=ys0,
              x_start=40, x_end=960, system_index=0),
        Staff(page_index=0, staff_index=1, line_ys=ys1,
              x_start=40, x_end=960, system_index=0),
    ]
    return _page(img, staves)


# ─── the compatibility guarantee ────────────────────────────────────────────


def test_the_five_coordinates_are_still_the_whole_constructor():
    """Every field added is optional. The four existing construction sites
    (three test modules and `staff_header`'s fixture) pass five positional
    facts and nothing else; if any new field were required they would break,
    and so would every future caller that only knows where the line is."""
    bl = Barline(page_index=0, x=100, y_top=10, y_bottom=90, system_index=0)
    for name in EVIDENCE_FIELDS:
        assert getattr(bl, name) is None, (
            f"{name} must default to None — an unannotated barline is one "
            f"whose evidence was NOT measured, which is not the same as zero")


# ─── the evidence, per field ────────────────────────────────────────────────


def test_every_accepted_barline_carries_a_full_evidence_record():
    pws = detect_barlines(_orchestral_page())
    assert pws.barlines, "fixture produced no barlines"
    for bl in pws.barlines:
        assert bl.accept_prong in ACCEPT_PRONGS, (
            f"barline at x={bl.x} has no acceptance prong recorded — the "
            f"constructor is dropping evidence again")
        assert bl.n_votes is not None and bl.n_votes >= 1
        assert bl.n_staves_in_system is not None
        assert bl.min_votes is not None
        assert bl.barlines_cross_gaps is not None
        assert bl.choir_cue_c_override is not None


def test_vote_count_is_the_staves_that_saw_it_out_of_the_system():
    """A barline drawn through all six staves is voted for by all six, and
    the denominator is the system's own five-line staff count. Both numbers
    reached the acceptance rule and neither survived it before."""
    pws = detect_barlines(_orchestral_page(n_staves=6))
    assert pws.barlines
    for bl in pws.barlines:
        assert bl.n_staves_in_system == 6
        assert bl.n_votes == 6, f"x={bl.x}: {bl.n_votes} votes of 6"
        assert 1 <= bl.min_votes <= bl.n_staves_in_system


def test_connectivity_is_recorded_on_a_conductors_page():
    """Prong A's own threshold value. A barline inked through every gap
    scores at or near 1.0; the number was compared against 0.4 and then
    thrown away."""
    pws = detect_barlines(_orchestral_page())
    assert pws.barlines
    for bl in pws.barlines:
        assert bl.accept_prong == "vote_and_connectivity"
        assert bl.connectivity is not None, "connectivity dropped again"
        assert bl.connectivity >= 0.4, (
            "prong A cannot accept below its own threshold")
        assert bl.barlines_cross_gaps is True


def test_open_score_is_recorded_as_a_different_regime():
    """The system-level verdict, stamped on each barline because nothing else
    carries a system. On an open score connectivity filtered NOTHING, and a
    consumer comparing two columns' connectivity across the two regimes would
    be comparing incommensurable numbers — which is precisely what this field
    exists to prevent.
    """
    pws = detect_barlines(_open_score_page())
    assert pws.barlines, "fixture produced no barlines"
    for bl in pws.barlines:
        assert bl.barlines_cross_gaps is False
        assert bl.accept_prong == "vote_open_score"
        assert bl.n_votes >= bl.min_votes


def test_open_score_connectivity_is_a_real_number_that_gated_nothing():
    """⚠️ THE CORRECTION. An earlier draft of the `connectivity` docstring
    said open-score rows carry `None` — "open-score systems skip it". They do
    not: the number is computed for the open-score TEST and kept, and on this
    fixture every row carries a real `0.0`.

    So the live hazard is the INVERSE of the one first documented. `None` (not
    measured) is the secondary trap; the primary one is a genuine `0.0` that
    filtered nothing and is indistinguishable by value from "measured and
    terrible". ⚠️ **The discriminator is `barlines_cross_gaps`, never
    `connectivity is None`.**
    """
    pws = detect_barlines(_open_score_page())
    assert pws.barlines
    for bl in pws.barlines:
        assert bl.connectivity is not None, (
            "the docstring's original claim, back again: open-score rows DO "
            "carry a measured connectivity")
        assert bl.barlines_cross_gaps is False


def test_connectivity_is_anti_correlated_with_correctness_on_an_open_score():
    """The standing warning for whoever consumes this evidence, pinned.

    Every barline on this page is REAL and carries a UNANIMOUS vote, and every
    one scores connectivity 0.0 — because an open score bars per staff, so the
    inter-staff gap ink a conductor's page shows is simply not printed. A
    consumer that ranked columns by `connectivity` alone would cull all of
    them. Measured the same way on the real pages this branch was gated on:
    engraved Brahms 1 culls 7 of 8 unanimous barlines at a 0.4 threshold, the
    Beethoven 5 scan culls 0 of 17.
    """
    pws = detect_barlines(_open_score_page())
    assert pws.barlines
    unanimous_but_unconnected = [
        b for b in pws.barlines
        if b.n_votes == b.n_staves_in_system and (b.connectivity or 0.0) < 0.4
    ]
    assert len(unanimous_but_unconnected) == len(pws.barlines), (
        "fixture no longer exhibits the inversion this warns about")


def test_small_system_records_the_vote_prong():
    pws = detect_barlines(_braced_pair(stem_on_lower=False))
    assert pws.barlines
    for bl in pws.barlines:
        assert bl.n_staves_in_system == 2
        assert bl.accept_prong == "vote_small_system"
        # The span score is not computed on this branch, and `None` says so
        # rather than claiming a floor of zero.
        assert bl.span_ink is None


def test_span_rescue_records_the_span_score_it_was_rescued_by():
    """The one place `_spans_system` is computed. A barline the busy staff
    failed to vote for is admitted on span ink alone, and the number that
    admitted it is now on the record — so a later outlier pass can tell a
    rescued barline from a consensus one."""
    pws = detect_barlines(_braced_pair(stem_on_lower=True))
    rescued = [b for b in pws.barlines
               if b.accept_prong == "span_rescue_small_system"]
    assert rescued, (
        "fixture failed to exercise the span rescue: prongs seen = "
        + repr(sorted({b.accept_prong for b in pws.barlines})))
    for bl in rescued:
        assert bl.span_ink is not None, "the rescuing score was dropped"
        assert 0.0 <= bl.span_ink <= 1.0
        assert bl.n_votes < bl.min_votes, (
            "a span rescue is by definition a column the vote refused")


@pytest.mark.parametrize("flag,expected", [("0", False), ("1", True)])
def test_choir_cue_c_override_is_recorded(monkeypatch, flag, expected):
    """`OMR_CHOIR_GROUPING`'s cue C flips a system out of open-score mode.
    Whether it fired is a fact about how much the connectivity number was
    trusted, and it was invisible downstream.

    The fixture is the choir-barred page: two 3-staff choirs, real barlines
    through each choir but never across the choir gap, plus unison stems that
    out-vote them. Flag off, the gate reads it as an open score; flag on, cue
    C overrides.
    """
    monkeypatch.setenv("OMR_CHOIR_GROUPING", flag)
    tops = [100, 200, 300, 460, 560, 660]
    all_ys = [_five(t) for t in tops]
    img = np.full((1200, 1000), 255, np.uint8)
    for ys in all_ys:
        for y in ys:
            img[y:y + 2, 40:960] = 0
    for x in (60, 260, 460, 660, 860):
        img[all_ys[0][0]:all_ys[2][-1] + 2, x:x + 3] = 0
        img[all_ys[3][0]:all_ys[5][-1] + 2, x:x + 3] = 0
    for x in (130, 195, 330, 395, 530, 595, 730, 795, 925):
        for ys in all_ys:
            img[ys[0]:ys[-1] + 2, x:x + 2] = 0
    staves = []
    for i, ys in enumerate(all_ys):
        s = Staff(page_index=0, staff_index=i, line_ys=ys,
                  x_start=40, x_end=960, system_index=0)
        s.group_index = 0 if i < 3 else 1
        staves.append(s)
    pws = detect_barlines(_page(img, staves))
    assert pws.barlines
    assert all(b.choir_cue_c_override is expected for b in pws.barlines), (
        "cue C's verdict is not reaching the barlines it decided")
    assert all(b.barlines_cross_gaps is expected for b in pws.barlines)


def test_evidence_survives_the_close_outlier_filter():
    """`_drop_close_outliers` thins the accepted x list before any `Barline`
    exists, so the evidence map is read back by x AFTER it runs. A survivor
    must still carry its own record — not a neighbour's, and not none.

    ⚠️ This is also the standing note on the filter itself: it is handed a
    `list[int]` and cannot see any of these fields. Making it evidence-aware
    is a separate, measured change.
    """
    pws = detect_barlines(_orchestral_page(n_staves=8))
    assert len(pws.barlines) >= 2
    xs = [b.x for b in pws.barlines]
    assert xs == sorted(xs)
    for bl in pws.barlines:
        assert bl.accept_prong is not None
        assert bl.n_votes is not None
