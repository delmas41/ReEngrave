"""The constant-size lineup SWAP, and the boundary rule that is blind to it.

`lineup_spans` keys on staff COUNT, on the axiom that a system may omit tacet
parts but never invent one. Brahms 4 / Breitkopf breaks that axiom: movements
III and IV both print sixteen staves and their lineups differ, so both land in
one span and every movement-IV wind is named one slot low.

The fixture is that document in miniature — sixteen staves either side, the
piccolo and triangle of movement III replaced by the two trombones of movement
IV — plus the small-swap and tie cases that must NOT fire.

⚠️ These tests are about DETECTION only. `OMR_LINEUP_SWAP_SPLIT` is default
OFF because acting on the detection is measured WORSE
(`benchmarks/omr-lineup-swap-2026-09/FINDINGS.md`): the document reference is
one printed system and cannot name two lineups that each hold an instrument the
other lacks, so splitting the span moves the staves and leaves the names
unsayable.
"""
from __future__ import annotations

from tools.omr import movement_reference as mr

MVT3 = ["Flute", "Piccolo", "Oboe", "Clarinet", "Bassoon", "Contrabassoon",
        "Horn", "Horn", "Trumpet", "Timpani", "Percussion",
        "Violin", "Violin", "Viola", "Cello", "Contrabass"]
MVT4 = ["Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon",
        "Horn", "Horn", "Trumpet", "Trombone", "Trombone", "Timpani",
        "Violin", "Violin", "Viola", "Cello", "Contrabass"]
#: Movement I: a smaller lineup, so the COUNT rule takes this boundary itself.
MVT1 = ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Horn", "Trumpet",
        "Timpani", "Violin", "Violin", "Viola", "Cello", "Contrabass"]


def _doc(*blocks):
    """`(page_systems, page_labels)` from `(n_pages, lineup)` blocks."""
    page_systems, page_labels, page = [], [], 0
    for n_pages, lineup in blocks:
        for _ in range(n_pages):
            page_systems.append((page, [len(lineup)]))
            page_labels.append((page, [list(lineup)]))
            page += 1
    return page_systems, page_labels


def _ranges(spans):
    return [[s[0], s[-1]] for s in spans if s]


def _on(monkeypatch):
    monkeypatch.setenv("OMR_LINEUP_SWAP_SPLIT", "1")


def _off(monkeypatch):
    monkeypatch.setenv("OMR_LINEUP_SWAP_SPLIT", "0")


# ── the case the count axiom cannot reach ───────────────────────────────────

def test_a_swap_at_constant_size_is_one_span_to_the_count_rule(monkeypatch):
    _off(monkeypatch)
    ps, pl = _doc((10, MVT3), (10, MVT4))
    assert _ranges(mr.lineup_spans(ps, pl)) == [[0, 19]]


def test_the_printed_names_find_the_swap(monkeypatch):
    _on(monkeypatch)
    ps, pl = _doc((10, MVT3), (10, MVT4))
    assert _ranges(mr.lineup_spans(ps, pl)) == [[0, 9], [10, 19]]


def test_it_refines_a_count_boundary_rather_than_replacing_it(monkeypatch):
    _on(monkeypatch)
    ps, pl = _doc((10, MVT1), (10, MVT3), (10, MVT4))
    # The count rule takes 10 (the lineup GREW 13 -> 16); the swap split adds 20.
    assert _ranges(mr.lineup_spans(ps, pl)) == [[0, 9], [10, 19], [20, 29]]


# ── inertness, asserted in both directions ──────────────────────────────────

def test_the_flag_is_off_by_default(monkeypatch):
    monkeypatch.delenv("OMR_LINEUP_SWAP_SPLIT", raising=False)
    assert not mr.swap_split_enabled()
    ps, pl = _doc((10, MVT3), (10, MVT4))
    assert _ranges(mr.lineup_spans(ps, pl)) == [[0, 19]]


def test_evidence_without_the_flag_changes_nothing(monkeypatch):
    """⚠️ Both halves, or this passes vacuously on a fixture that never splits.

    The same fixture must be shown to split under the flag; otherwise "off is
    inert" is a statement about the fixture, not about the flag.
    """
    _off(monkeypatch)
    ps, pl = _doc((10, MVT3), (10, MVT4))
    assert mr.lineup_spans(ps, pl) == mr.lineup_spans(ps)
    _on(monkeypatch)
    assert mr.lineup_spans(ps, pl) != mr.lineup_spans(ps)


def test_the_flag_without_evidence_changes_nothing(monkeypatch):
    _on(monkeypatch)
    ps, pl = _doc((10, MVT3), (10, MVT4))
    assert _ranges(mr.lineup_spans(ps)) == [[0, 19]]
    assert _ranges(mr.lineup_spans(ps, None)) == [[0, 19]]


def test_a_publisher_that_labels_nothing_keeps_todays_answer(monkeypatch):
    _on(monkeypatch)
    ps, pl = _doc((10, MVT3), (10, MVT4))
    blank = [(p, [[None] * len(sys_) for sys_ in systems])
             for (p, systems) in pl]
    assert _ranges(mr.lineup_spans(ps, blank)) == [[0, 19]]


# ── the refusals ────────────────────────────────────────────────────────────

def test_a_small_swap_is_left_alone(monkeypatch):
    """Two instruments trading places supports 2 ordinals, under the bar.

    Under-splitting is the safe direction: a boundary in the wrong place is
    inherited by every system after it. Measured on Brahms 1, whose second
    movement swaps a horn staff for a solo violin — the detector puts its best
    candidate on exactly the right page and scores 2.
    """
    _on(monkeypatch)
    swapped = list(MVT3)
    swapped[9], swapped[10] = swapped[10], swapped[9]
    ps, pl = _doc((10, MVT3), (10, swapped))
    assert _ranges(mr.lineup_spans(ps, pl)) == [[0, 19]]


def test_a_tie_refuses_rather_than_picking(monkeypatch):
    """Two candidate pages with equal support do not LOCATE the boundary.

    Here the middle block belongs to neither lineup, so the split at its start
    and the split at its end score alike and neither is the answer.
    """
    _on(monkeypatch)
    ps, pl = _doc((6, MVT3), (6, MVT4), (6, MVT3))
    assert _ranges(mr.lineup_spans(ps, pl)) == [[0, 17]]


def test_a_side_with_too_few_full_systems_cannot_speak(monkeypatch):
    _on(monkeypatch)
    ps, pl = _doc((10, MVT3), (2, MVT4))
    assert _ranges(mr.lineup_spans(ps, pl)) == [[0, 11]]


def test_a_span_too_short_to_stand_alone_is_not_created(monkeypatch):
    """`MIN_SPAN_PAGES` guards the swap split exactly as it guards the count
    rule — a three-page span is not a movement worth referencing."""
    _on(monkeypatch)
    ps, pl = _doc((10, MVT3), (3, MVT4))
    assert _ranges(mr.lineup_spans(ps, pl)) == [[0, 12]]


def test_reduced_systems_do_not_vote(monkeypatch):
    """A system with tacet staves suppressed has no ordinal correspondence.

    Its names look like a slide of the full lineup, which is the exact shape
    the detector fires on, so it must be excluded rather than down-weighted.
    """
    _on(monkeypatch)
    ps, pl = _doc((10, MVT3), (10, MVT3))
    reduced = MVT3[2:]                      # the two top winds tacet
    for p in range(3, 8):
        ps[p] = (p, [len(reduced)])
        pl[p] = (p, [list(reduced)])
    assert _ranges(mr.lineup_spans(ps, pl)) == [[0, 19]]


# ── the width the detector measures against ─────────────────────────────────

def test_a_one_page_oversize_read_is_not_the_span_width(monkeypatch):
    """⚠️ Measured on Brahms 1: its finale span reads 17 staves on ONE page
    against a printed 16, and taking the maximum left the span with a single
    full system and no detector at all over 41 pages. The width must RECUR —
    `build_reference`'s own test, for `build_reference`'s own reason."""
    _on(monkeypatch)
    ps, pl = _doc((10, MVT3), (10, MVT4))
    wobble = MVT3 + ["Violin"]
    ps[4] = (4, [len(wobble)])
    pl[4] = (4, [list(wobble)])
    assert _ranges(mr.lineup_spans(ps, pl)) == [[0, 9], [10, 19]]


def test_a_merged_system_is_not_the_span_width(monkeypatch):
    """Two systems read as one must not define the lineup.

    ⚠️ The guard that actually catches this is RECURRENCE, not the merge cap:
    a merge is two systems of whatever sizes the page happens to hold, so its
    total differs page to page and is seen once. `MERGE_CAP_RATIO` is the
    second line, and it is `<=` (as in `_peaks`), so an exactly-doubled system
    passes it — which is why both guards are here.
    """
    _on(monkeypatch)
    ps, pl = _doc((10, MVT3), (10, MVT4))
    for page, extra in ((2, 13), (12, 14)):
        merged = pl[page][1][0] + ["Violin"] * extra
        ps[page] = (page, [len(merged)])
        pl[page] = (page, [merged])
    assert _ranges(mr.lineup_spans(ps, pl)) == [[0, 9], [10, 19]]


# ── three lineups in one count-span ─────────────────────────────────────────

THIRD = ["Flute", "Piccolo", "Oboe", "Clarinet", "Bassoon", "Contrabassoon",
         "Horn", "Horn", "Trumpet", "Trombone", "Trombone",
         "Violin", "Violin", "Viola", "Cello", "Contrabass"]


def test_a_span_holding_three_lineups_is_split_twice(monkeypatch):
    _on(monkeypatch)
    ps, pl = _doc((12, MVT3), (12, MVT4), (6, THIRD))
    assert _ranges(mr.lineup_spans(ps, pl)) == [[0, 11], [12, 23], [24, 29]]


def test_an_EVEN_three_way_mixture_defeats_it_and_that_is_recorded(monkeypatch):
    """⚠️ A limitation, asserted rather than hidden.

    Each pass asks one question — do the two sides have DIFFERENT majorities —
    so the side holding two lineups in equal measure has no majority to state.
    Three equal blocks therefore yield nothing, while the same three at
    12/12/6 split twice (above). The failure is toward NOT splitting, which is
    the safe direction, and the fix is a smaller unit than the page rather than
    a lower bar.
    """
    _on(monkeypatch)
    ps, pl = _doc((10, MVT3), (10, MVT4), (10, THIRD))
    assert _ranges(mr.lineup_spans(ps, pl)) == [[0, 29]]
