"""Stable part identity across systems and pages (tools/omr/slots.py)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import os

from tools.omr.slots import (
    REFERENCE_MAX_SIZE_RATIO,
    Slot,
    SystemView,
    align,
    assign_slots,
    build_reference,
    labels_by_staff,
    map_groups,
    reference_candidates,
    reference_view,
    _align_by_span,
    _compose,
    _looks_merged,
    _slots_of,
)
from tools.omr.types import PageImage, PageWithStaves, Staff


def _staff(index: int, group: int = 0, top: int | None = None) -> Staff:
    top = index * 100 if top is None else top
    return Staff(page_index=0, staff_index=index,
                 line_ys=[top + 12 * k for k in range(5)],
                 x_start=100, x_end=1000, group_index=group)


def _view(specs: list[tuple[int, str | None]]) -> SystemView:
    """specs: [(group_index, instrument or None), ...] top to bottom."""
    staves = [_staff(i, group=g) for i, (g, _n) in enumerate(specs)]
    labels = {i: n for i, (_g, n) in enumerate(specs) if n}
    return SystemView(staves=staves, labels=labels)


FULL = [(0, "Flute"), (0, "Oboe"), (0, "Clarinet"), (0, "Bassoon"),
        (1, "Horn"), (1, "Trumpet"),
        (2, None), (2, None), (2, None)]


# ── reference ───────────────────────────────────────────────────────────────

def test_reference_is_the_largest_system():
    """The largest system wins — given that it recurs.

    A full system that appears exactly ONCE among smaller ones is genuinely
    ambiguous: at that point it is indistinguishable from two condensed systems
    that got merged, which is a real failure mode (see the one-off test below).
    Real scores do not pose that question — the orchestra is the same on every
    page, so the full system is the common one and the condensed ones vary.
    """
    condensed = _view(FULL[4:])          # 5 staves — winds tacet
    full = _view(FULL)                   # 9 staves
    ref = build_reference([condensed, full, full])
    assert [s.instrument for s in ref] == [n for _g, n in FULL]
    assert [s.group_index for s in ref] == [g for g, _n in FULL]


def test_reference_positions_span_zero_to_one():
    ref = build_reference([_view(FULL)])
    assert ref[0].position == 0.0
    assert ref[-1].position == 1.0


def test_reference_rejects_a_merged_system():
    """system_grouping fails by MERGING, and a merged 'system' is two systems
    concatenated — exactly the shape that wins a max-size contest."""
    merged = _view(FULL + FULL)
    ref = build_reference([_view(FULL), _view(FULL), merged])
    assert len(ref) == len(FULL), "the concatenation must not become the reference"


def test_looks_merged_detects_a_repeated_instrument():
    assert _looks_merged(_view(FULL + FULL))
    assert not _looks_merged(_view(FULL))


def test_adjacent_duplicate_instruments_are_not_a_merge():
    """Two horns on consecutive staves are normal orchestration, not a merge."""
    v = _view([(0, "Flute"), (1, "Horn"), (1, "Horn"), (1, "Trumpet"), (1, "Trumpet")])
    assert not _looks_merged(v)


def test_a_one_off_oversized_system_loses_to_a_recurring_size():
    """The label-free half of the merged-system guard.

    `_looks_merged` reads instrument names, so it is blind on a score with no
    text layer — which is exactly where a 24-staff concatenation of two 12-staff
    systems became the reference, giving 24 unlabelled slots. A real full system
    recurs across pages because the orchestra does not change; a merged one is a
    one-off.
    """
    plain = [(g, None) for g, _n in FULL]
    real = _view(plain)                     # 9 staves, appears several times
    merged = _view(plain + plain[:4])       # 13 staves, appears once
    ref = build_reference([real, real, real, merged])
    assert len(ref) == len(FULL)


def test_oversized_system_is_capped_out_even_without_labels():
    """With no labels, `_looks_merged` is blind, so the size cap is the only
    guard left against a concatenation becoming the reference."""
    plain = [(g, None) for g, _n in FULL]
    unlabelled_big = _view(plain * 3)
    ref = build_reference([_view(plain), _view(plain), _view(plain), unlabelled_big])
    assert len(ref) == len(FULL)


def test_reference_of_nothing_is_empty():
    assert build_reference([]) == []


# ── alignment ───────────────────────────────────────────────────────────────

def test_identical_system_aligns_one_to_one():
    ref = build_reference([_view(FULL)])
    assert align(_view(FULL), ref) == list(range(len(FULL)))


def test_tacet_parts_are_skipped_not_shifted():
    """A system omitting the winds must map its brass to the BRASS slots, not
    slide everything up to slots 0..n — the failure that makes index matching
    useless on orchestral scores."""
    ref = build_reference([_view(FULL)])
    condensed = _view(FULL[4:])          # brass + strings only
    assert align(condensed, ref) == [4, 5, 6, 7, 8]


def test_labels_override_position():
    """A system whose staves sit at different relative positions still aligns by
    name when names are available."""
    ref = build_reference([_view(FULL)])
    view = _view([(0, "Bassoon"), (1, "Trumpet")])
    assert align(view, ref) == [3, 5]


def test_alignment_is_monotone():
    ref = build_reference([_view(FULL)])
    out = [s for s in align(_view(FULL[::2]), ref) if s >= 0]
    assert out == sorted(out)


def test_staves_beyond_the_reference_are_left_unassigned():
    ref = build_reference([_view(FULL[:3])])
    out = align(_view(FULL), ref)
    assert out.count(-1) == len(FULL) - 3


def test_empty_inputs():
    assert align(_view([]), build_reference([_view(FULL)])) == []
    assert align(_view(FULL), []) == [-1] * len(FULL)


# ── end to end ──────────────────────────────────────────────────────────────

def _page(specs_per_system: list[list[tuple[int, str | None]]]) -> PageWithStaves:
    img = np.full((10, 10), 255, np.uint8)
    page = PageImage(pdf_path=Path("x.pdf"), page_index=0, dpi=300,
                     rgb=np.dstack([img] * 3), binary=img)
    staves, top, idx = [], 0, 0
    for sys_i, specs in enumerate(specs_per_system):
        for g, _n in specs:
            st = _staff(idx, group=g, top=top)
            st.system_index = sys_i
            staves.append(st)
            top += 100
            idx += 1
        top += 400
    return PageWithStaves(page=page, staves=staves)


def test_assign_slots_across_systems_and_pages():
    labels = {i: n for i, (_g, n) in enumerate(FULL) if n}
    page1 = _page([FULL])
    page2 = _page([FULL[4:]])                    # winds tacet in this system
    ref = assign_slots([page1, page2], [labels, {}])
    assert len(ref) == len(FULL)
    assert [s.slot_index for s in page1.staves] == list(range(len(FULL)))
    assert [s.slot_index for s in page2.staves] == [4, 5, 6, 7, 8]


def test_assign_slots_without_labels_falls_back_to_position():
    page = _page([FULL, FULL])
    ref = assign_slots([page], None)
    assert len(ref) == len(FULL)
    first = [s.slot_index for s in page.staves[:len(FULL)]]
    second = [s.slot_index for s in page.staves[len(FULL):]]
    assert first == second == list(range(len(FULL)))


def test_assign_slots_on_no_pages():
    assert assign_slots([], []) == []


def test_labels_by_staff_drops_low_confidence():
    class _Inst:
        name = "Flute"

    class _Lab:
        def __init__(self, idx, conf):
            self.staff_index, self.confidence = idx, conf
            self.instrument = _Inst()
            self.matched = True

    got = labels_by_staff([_Lab(0, "high"), _Lab(1, "medium"), _Lab(2, "low")])
    assert got == {0: "Flute", 1: "Flute"}


# ── reference selection by labels (OMR_REFERENCE_MOST_LABELLED, default off) ──

# Beethoven 5 / Litolff, reduced to what the rule sees: the movement's FIRST
# system prints twelve staves and names them; every system after it prints
# eleven, because `Violoncello e Basso` condense onto one staff. Over a
# multi-page run the eleven-staff shape RECURS and the twelve-staff one does
# not, which is exactly backwards for a reference.
_B5_FULL = [(0, "Flute"), (0, "Oboe"), (0, "Clarinet"), (0, "Bassoon"),
            (1, "Horn"), (1, "Trumpet"), (1, "Timpani"),
            (2, "Violin"), (2, "Violin"), (2, "Viola"), (2, "Cello"),
            (2, "Contrabass")]
_B5_CONDENSED = _B5_FULL[:10] + [(2, "Cello")]      # eleven staves


def _b5_run():
    return [_view(_B5_FULL), _view(_B5_CONDENSED), _view(_B5_CONDENSED),
            _view(_B5_CONDENSED), _view(_B5_CONDENSED)]


def test_default_still_picks_the_recurring_condensed_system():
    """The bug, pinned — so a default flip has to change this test on purpose."""
    ref = build_reference(_b5_run())
    assert len(ref) == 11
    assert ref[-1].instrument == "Cello"


def test_most_labelled_recovers_the_full_system():
    ref = build_reference(_b5_run(), most_labelled="on")
    assert [s.instrument for s in ref] == [n for _g, n in _B5_FULL]


def test_most_labelled_abstains_where_nothing_is_labelled():
    """27 of 234 documents print no names at all; there the label count is 0
    everywhere and the rule must fall back, not pick an arbitrary system."""
    plain = [[(g, None) for g, _n in spec] for spec in (_B5_FULL, _B5_CONDENSED)]
    run = [_view(plain[0])] + [_view(plain[1]) for _ in range(4)]
    assert (build_reference(run, most_labelled="on")
            == build_reference(run, most_labelled="off"))


def test_most_labelled_ties_are_broken_by_size():
    """Litolff names winds and brass on every system and strings never, so the
    full and condensed systems tie on label count. Size decides, and the full
    lineup is the answer either way."""
    partial_full = _B5_FULL[:7] + [(2, None)] * 5
    partial_cond = _B5_CONDENSED[:7] + [(2, None)] * 4
    run = [_view(partial_full)] + [_view(partial_cond) for _ in range(4)]
    ref = build_reference(run, most_labelled="on")
    assert len(ref) == 12


def test_most_labelled_never_shrinks_the_reference():
    """A Bote Dvořák serenade names its opening 5-staff system and prints
    6-staff systems later. A reference shorter than a system cannot name that
    system's overflow at all, so the label winner is refused there — and
    `pure` reproduces the refused arm."""
    small = [(0, "Violin"), (0, "Violin"), (0, "Viola"), (0, "Cello"),
             (0, "Contrabass")]
    big = [(0, None)] * 6
    run = [_view(small)] + [_view(big), _view(big)]
    assert len(build_reference(run, most_labelled="on")) == 6
    assert len(build_reference(run, most_labelled="pure")) == 5


def test_most_labelled_reads_the_env_flag(monkeypatch):
    monkeypatch.delenv("OMR_REFERENCE_MOST_LABELLED", raising=False)
    assert len(build_reference(_b5_run())) == 11
    monkeypatch.setenv("OMR_REFERENCE_MOST_LABELLED", "1")
    assert len(build_reference(_b5_run())) == 12
    monkeypatch.setenv("OMR_REFERENCE_MOST_LABELLED", "0")
    assert len(build_reference(_b5_run())) == 11


def test_align_drops_the_top_staff_when_the_reference_is_condensed():
    """Why the wrong reference misnames rather than merely under-names: `align`
    deletes on the REFERENCE side only, so a twelve-staff system aligned
    against an eleven-slot reference loses its top staff and every name slides
    up one — `Horn` reads as Bassoon."""
    ref = build_reference(_b5_run())                    # eleven slots
    got = align(_view([(g, None) for g, _n in _B5_FULL]), ref)
    assert got[0] == -1 or [ref[i].instrument for i in got[:5] if i >= 0][0] != "Flute"


# ── group ordinals are per-system, and must be mapped before comparing ───────

def _reduced_beethoven5_case():
    """Beethoven 5 / Litolff p23: a twelve-staff system against the finale's
    seventeen-slot reference, with the system's brackets read as TWO groups
    (winds and brass merged) against the reference's three.

    Measured shapes, from `benchmarks/omr-slot-alignment-2026-09/`.
    """
    names = ["Piccolo", "Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon",
             "Horn", "Trumpet", "Timpani", "Trombone", "Trombone", "Trombone",
             "Violin", "Violin", "Viola", "Cello", "Contrabass"]
    groups = [0] * 6 + [1] * 6 + [2] * 5
    ref = [Slot(index=i, group_index=g, instrument=n, position=i / 16)
           for i, (g, n) in enumerate(zip(groups, names))]
    # The system: winds+brass all read as bracket 0, strings as bracket 1.
    staves = [_staff(i, group=g, top=i * 100)
              for i, g in enumerate([0] * 7 + [1] * 5)]
    labels = {0: "Flute", 1: "Oboe", 2: "Clarinet", 3: "Bassoon",
              4: "Horn", 5: "Trumpet", 6: "Timpani"}
    return SystemView(staves=staves, labels=labels), ref


TRUE_SLOTS_P23 = [1, 2, 3, 4, 6, 7, 8, 12, 13, 14, 15, 16]


def test_group_ordinals_are_mapped_not_compared_raw():
    """The strings must not be pulled onto the Trombone slots.

    RED before the fix: comparing `Staff.group_index` to `Slot.group_index`
    raw makes the system's strings (bracket 1) MATCH the reference's brass
    bracket, which is where the Trombones live, and CONFLICT with the real
    string slots. The DP then scores the wrong alignment +8.9489 -- +9.0 of it
    this term -- and three string staves are named Trombone.
    """
    view, ref = _reduced_beethoven5_case()
    assert align(view, ref) == TRUE_SLOTS_P23


def test_the_old_ordinal_comparison_is_what_broke_it():
    """The refused arm, kept runnable so the finding stays reproducible."""
    os.environ["OMR_SLOT_GROUP_MAP"] = "ordinal"
    try:
        view, ref = _reduced_beethoven5_case()
        got = align(view, ref)
    finally:
        del os.environ["OMR_SLOT_GROUP_MAP"]
    assert got != TRUE_SLOTS_P23
    names = {s.index: s.instrument for s in ref}
    assert [names[s] for s in got[7:10]] == ["Trombone", "Trombone", "Trombone"]


def test_a_block_maps_only_where_there_is_room_for_it():
    """Seven staves are not six slots. On the p23 shapes only ONE monotone
    assignment gives the wind-and-brass block room, which is what makes the
    correspondence decidable rather than a tie."""
    view, ref = _reduced_beethoven5_case()
    assert map_groups(view, ref) == {0: {0, 1}, 1: {2}}


def test_a_whole_bracket_may_be_tacet():
    """Untaken reference blocks are free: a system can drop an entire bracket.
    Winds absent, so the reference's first block is taken by nobody."""
    view = _view(FULL[4:])
    ref = build_reference([_view(FULL)])
    assert map_groups(view, ref) == {1: {1}, 2: {2}}


def test_a_tie_of_different_meanings_abstains():
    """Two assignments of equal cost and different meaning are no evidence, so
    the term is withheld rather than guessed."""
    # One system block of 2; reference two blocks of 2. Taking either costs 0.
    view = SystemView(staves=[_staff(i, group=0, top=i * 100) for i in range(2)])
    ref = [Slot(index=i, group_index=g, position=i / 3)
           for i, g in enumerate([1, 1, 2, 2])]
    assert map_groups(view, ref) is None


def test_more_system_blocks_than_reference_blocks_abstains():
    view = SystemView(staves=[_staff(i, group=g, top=i * 100)
                              for i, g in enumerate([0, 1, 2])])
    ref = [Slot(index=i, group_index=0, position=i / 2) for i in range(3)]
    assert map_groups(view, ref) is None


# ── the span composition step (OMR_SPAN_REFERENCE_FIT) ──────────────────────
#
# Reduced from the real Brahms 1 / Breitkopf fault, measured in
# benchmarks/omr-span-composition-2026-09/. A span's own reference is placed
# into the document reference ONCE and every system in the span inherits the
# placement, so a reference whose LINEUP the document cannot express is not a
# small error — it is 149 wrong staff records against 36.
#
# The shape: the span holds two systems of the same SIZE and different lineups.
# One is a one-off that labels every staff (on the real page, a second-movement
# system with a `Viol. Solo` staff) and therefore wins the label tie-break; the
# other recurs and is the movement's real lineup. Only the second is a
# subsequence of the document reference.

#: The document reference: the finale's lineup, with two slots the earlier
#: movements do not use (Trombone and its unnamed neighbour).
_DOC = [(0, "Flute"), (0, "Oboe"), (0, "Horn"), (0, None), (0, "Trumpet"),
        (0, "Trombone"), (0, None), (0, "Timpani"),
        (1, "Violin"), (1, "Violin"), (1, "Viola")]

#: The one-off, fully labelled, with an extra string staff and one horn staff.
_SOLO = [(0, "Flute"), (0, "Oboe"), (0, "Horn"), (0, "Trumpet"),
         (0, "Timpani"),
         (1, "Violin"), (1, "Violin"), (1, "Violin"), (1, "Viola")]

#: The movement's real lineup: same SIZE, one label fewer (the second horn
#: staff carries only a crook), and a subsequence of the document reference.
_REAL = [(0, "Flute"), (0, "Oboe"), (0, "Horn"), (0, None), (0, "Trumpet"),
         (0, "Timpani"),
         (1, "Violin"), (1, "Violin"), (1, "Viola")]


def _span_fixture():
    document = build_reference([_view(_DOC), _view(_DOC)])
    span = [_view(_SOLO)] + [_view(_REAL) for _ in range(3)]
    return document, span


def test_reference_view_is_the_head_of_reference_candidates():
    """The document-wide path reads element 0 and nothing else, so the head of
    the candidate list IS the old rule. Drift here changes every score."""
    for views in ([_view(_SOLO)] + [_view(_REAL) for _ in range(3)],
                  [_view(FULL), _view(FULL), _view(FULL[4:])],
                  [_view(FULL)], []):
        ranked = reference_candidates(views)
        assert reference_view(views) is (ranked[0] if ranked else None)


def test_the_one_off_fully_labelled_system_still_wins_the_head():
    """The candidate list must not quietly re-rank the primary pick: the
    one-off that labels every staff is still element 0, which is exactly why
    the composition needs a check of its own."""
    _document, span = _span_fixture()
    ranked = reference_candidates(span)
    assert [s.instrument for s in _slots_of(ranked[0])] == [n for _g, n in _SOLO]


def test_compose_counts_a_contradicted_placement():
    """`align` places this reference whole — every local gets a global — and
    the placement asserts that a Timpani staff is a Trombone."""
    document, span = _span_fixture()
    to_global, bad = _compose(_view(_SOLO), document)
    assert all(g >= 0 for g in to_global)      # "placed whole" says yes
    assert bad >= 1                            # and it is still wrong
    good_global, good_bad = _compose(_view(_REAL), document)
    assert good_bad == 0
    assert good_global == [0, 1, 2, 3, 4, 7, 8, 9, 10]


def test_compose_reports_a_reference_too_small_to_hold_the_system():
    document = build_reference([_view(_DOC[:4]), _view(_DOC[:4])])
    _to_global, bad = _compose(_view(_SOLO), document)
    assert bad is None


def test_span_fit_off_reproduces_the_contradicted_placement(monkeypatch):
    """The pre-2026-09-06 behaviour, kept reachable: the Timpani-labelled staff
    of every system in the span lands on the Trombone slot."""
    monkeypatch.setenv("OMR_SPAN_REFERENCE_FIT", "off")
    document, span = _span_fixture()
    assert _align_by_span([span], document) is True
    real = span[1]                              # a _REAL system
    timpani = [st for st in real.staves
               if real.labels.get(st.staff_index) == "Timpani"][0]
    assert document[timpani.slot_index].instrument != "Timpani"


def test_span_fit_refuse_falls_back_to_the_document_wide_path(monkeypatch):
    """`refuse` prices the refusal alone: it takes the same pick and declines
    rather than asserting the contradiction."""
    monkeypatch.setenv("OMR_SPAN_REFERENCE_FIT", "refuse")
    document, span = _span_fixture()
    assert _align_by_span([span], document) is False


def test_span_fit_search_takes_the_sibling_that_composes(monkeypatch):
    """The shipped default: a candidate further down the list composes without
    contradicting a label, and every staff of the span then lands right."""
    monkeypatch.setenv("OMR_SPAN_REFERENCE_FIT", "search")
    document, span = _span_fixture()
    assert _align_by_span([span], document) is True
    for view in span[1:]:
        got = [document[st.slot_index].instrument for st in view.staves]
        assert got == ["Flute", "Oboe", "Horn", None, "Trumpet", "Timpani",
                       "Violin", "Violin", "Viola"]


def test_span_fit_is_a_no_op_where_the_first_candidate_composes(monkeypatch):
    """The Beethoven 5 shape, and the control that matters: where
    `reference_view`'s own pick contradicts nothing, all three arms agree."""
    document = build_reference([_view(_DOC), _view(_DOC)])
    out = {}
    for mode in ("off", "refuse", "search"):
        monkeypatch.setenv("OMR_SPAN_REFERENCE_FIT", mode)
        span = [_view(_REAL) for _ in range(3)]
        assert _align_by_span([span], document) is True
        out[mode] = [st.slot_index for v in span for st in v.staves]
    assert out["off"] == out["refuse"] == out["search"]


def test_span_fit_reads_the_env_flag(monkeypatch):
    from tools.omr.slots import span_reference_mode
    monkeypatch.delenv("OMR_SPAN_REFERENCE_FIT", raising=False)
    assert span_reference_mode() == "search"
    monkeypatch.setenv("OMR_SPAN_REFERENCE_FIT", "nonsense")
    assert span_reference_mode() == "search"
    for v in ("off", "refuse", "search"):
        monkeypatch.setenv("OMR_SPAN_REFERENCE_FIT", v)
        assert span_reference_mode() == v
