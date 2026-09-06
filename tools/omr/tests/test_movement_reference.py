"""Lineup spans, and the two-level alignment they feed (`movement_reference`).

The fixture is Beethoven 5 / Litolff in miniature, because that is the shape the
bug has: a movement-1 lineup of twelve, a finale lineup of seventeen that adds
piccolo, contrabassoon and three trombones, and a publisher whose movement
OPENING names every staff while every page after it names only the winds and
brass. Under one document-wide reference each ordinary movement-1 page has to
decide for itself which five of the finale's seventeen slots it omits, and a
page whose bracket groups did not resolve puts its Violin I on a trombone.

⚠️ The fixture carries that degraded case explicitly (`flat_groups`), because
the fix is INERT on a page that still has its bracket evidence — the aligner
gets those right already. What the fix changes is that the decision is made
ONCE, on the movement's own opening system, where the evidence is complete.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from tools.omr import movement_reference as mr
from tools.omr.slots import assign_slots
from tools.omr.types import PageImage, PageWithStaves, Staff

STRINGS = [(2, "Violin"), (2, "Violin"), (2, "Viola"), (2, "Cello"),
           (2, "Contrabass")]
#: The movement-1 opening: winds, brass, and the strings named in full.
MVT1_OPENING = [(0, "Flute"), (0, "Oboe"), (0, "Clarinet"), (0, "Bassoon"),
                (1, "Horn"), (1, "Trumpet"), (1, "Timpani")] + STRINGS
#: The finale adds a piccolo, a contrabassoon and three trombones.
FINALE_OPENING = (MVT1_OPENING[:1] + [(0, "Piccolo")] + MVT1_OPENING[1:4]
                  + [(0, "Contrabassoon")] + MVT1_OPENING[4:7]
                  + [(1, "Trombone")] * 3 + STRINGS)

_STRING_NAMES = {n for _g, n in STRINGS}


def _ordinary(opening):
    """A page that is not a movement opening: the strings go unnamed."""
    return [(g, None if n in _STRING_NAMES else n) for g, n in opening]


def _page(page_index: int, system, *, flat_groups: bool) -> PageWithStaves:
    img = np.full((10, 10), 255, np.uint8)
    page = PageImage(pdf_path=Path("x.pdf"), page_index=page_index, dpi=300,
                     rgb=np.dstack([img] * 3), binary=img)
    staves, top = [], 0
    for idx, (group, _name) in enumerate(system):
        st = Staff(page_index=page_index, staff_index=idx,
                   line_ys=[top + 12 * k for k in range(5)],
                   x_start=100, x_end=1000,
                   group_index=0 if flat_groups else group)
        st.system_index = 0
        staves.append(st)
        top += 100
    return PageWithStaves(page=page, staves=staves)


def _document(*, flat_groups: bool, n_mvt1: int = 12, n_finale: int = 12):
    """A movement opening followed by ordinary pages, twice over."""
    systems = []
    if n_mvt1:
        systems += [MVT1_OPENING] + [_ordinary(MVT1_OPENING)] * (n_mvt1 - 1)
    if n_finale:
        systems += [FINALE_OPENING] + [_ordinary(FINALE_OPENING)] * (n_finale - 1)
    pages = [_page(i, s, flat_groups=flat_groups) for i, s in enumerate(systems)]
    labels = [{i: n for i, (_g, n) in enumerate(s) if n} for s in systems]
    return pages, labels


def _named(reference, page):
    return [reference[s.slot_index].instrument if s.slot_index >= 0 else None
            for s in page.staves]


TRUE_MVT1 = [n for _g, n in MVT1_OPENING]
TRUE_FINALE = [n for _g, n in FINALE_OPENING]


# ── the segmentation ────────────────────────────────────────────────────────

def test_the_boundary_is_where_the_lineup_grows():
    pages = [(i, [12]) for i in range(12)] + [(i, [17]) for i in range(12, 24)]
    assert mr.lineup_spans(pages) == [list(range(12)), list(range(12, 24))]


def test_a_tacet_dip_is_not_a_boundary():
    """A page printing FEWER staves has parts resting, not a new orchestra."""
    pages = [(0, [12]), (1, [8]), (2, [12]), (3, [5, 7]), (4, [12]),
             (5, [12]), (6, [12]), (7, [12])]
    assert mr.lineup_spans(pages) == [list(range(8))]


def test_a_one_off_larger_system_is_a_merge_not_a_movement():
    """One page reading 24 among pages of 12 is two systems glued together.

    Both guards fire: 24 is over `MERGE_CAP_RATIO` x the median, and it never
    recurs. It must neither become a boundary NOR raise the running maximum, or
    the real level that follows could never be seen to exceed it.
    """
    pages = ([(i, [12]) for i in range(6)] + [(6, [24])]
             + [(i, [12]) for i in range(7, 12)]
             + [(i, [17]) for i in range(12, 20)])
    assert [span[0] for span in mr.lineup_spans(pages)] == [0, 12]


def test_a_two_page_run_offers_no_recurrence_and_is_left_alone():
    """`--pages 1,44`: each level appears once, so neither is proved a lineup.

    This is what protects the case where widening the reference HELPS, and it
    is the same rule rather than an exemption.
    """
    assert mr.lineup_spans([(1, [12]), (44, [17])]) == [[1, 44]]
    assert mr.lineup_spans([(10, [13, 14]), (75, [16])]) == [[10, 75]]


def test_a_thin_span_refuses_to_split():
    pages = [(i, [12]) for i in range(2)] + [(i, [17]) for i in range(2, 12)]
    assert mr.lineup_spans(pages) == [list(range(12))]


def test_pages_with_no_staves_join_the_span_around_them():
    pages = [(0, [])] + [(i, [12]) for i in range(1, 8)]
    assert mr.lineup_spans(pages) == [list(range(8))]


# ── end to end, through assign_slots ────────────────────────────────────────

def test_the_document_reference_puts_a_string_on_a_trombone(monkeypatch):
    """The bug, reproduced: what ships today, on a page with no bracket groups.

    Kept as a live failure rather than a remembered one — if the aligner ever
    stops making this mistake unaided, this test fails and says so.
    """
    monkeypatch.delenv("OMR_MOVEMENT_REFERENCE", raising=False)
    pages, labels = _document(flat_groups=True)
    reference = assign_slots(pages, labels)
    assert len(reference) == len(FINALE_OPENING)
    assert _named(reference, pages[5])[7] == "Trombone"


def test_a_movement_local_reference_names_the_strings(monkeypatch):
    monkeypatch.setenv("OMR_MOVEMENT_REFERENCE", "1")
    pages, labels = _document(flat_groups=True)
    reference = assign_slots(pages, labels)
    assert len(reference) == len(FINALE_OPENING)
    for page in pages[:12]:
        assert _named(reference, page) == TRUE_MVT1
    for page in pages[12:]:
        assert _named(reference, page) == TRUE_FINALE


def test_it_is_inert_where_the_page_still_has_its_brackets(monkeypatch):
    """With bracket groups resolved the aligner is already right, and stays so.

    The fix is not a second opinion about a page that has evidence; it is one
    decision taken where the evidence is, and given to the movement.
    """
    out = {}
    for flag in ("0", "1"):
        monkeypatch.setenv("OMR_MOVEMENT_REFERENCE", flag)
        pages, labels = _document(flat_groups=False)
        reference = assign_slots(pages, labels)
        out[flag] = [_named(reference, p) for p in pages]
    assert out["0"] == out["1"]
    assert out["1"][5] == TRUE_MVT1


def test_one_span_is_identical_to_today(monkeypatch):
    """A run inside one movement must not change at all.

    Not a hope but a guarantee: with one span the span reference IS the document
    reference, and aligning m staves onto m slots has exactly one
    order-preserving answer.
    """
    seen = []
    for flag in ("0", "1"):
        monkeypatch.setenv("OMR_MOVEMENT_REFERENCE", flag)
        pages, labels = _document(flat_groups=True, n_finale=0)
        assign_slots(pages, labels)
        seen.append([[s.slot_index for s in p.staves] for p in pages])
    assert seen[0] == seen[1]


def test_the_flag_is_off_by_default(monkeypatch):
    monkeypatch.delenv("OMR_MOVEMENT_REFERENCE", raising=False)
    assert not mr.enabled()
    monkeypatch.setenv("OMR_MOVEMENT_REFERENCE", "1")
    assert mr.enabled()
