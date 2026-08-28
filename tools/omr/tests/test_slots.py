"""Stable part identity across systems and pages (tools/omr/slots.py)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tools.omr.slots import (
    REFERENCE_MAX_SIZE_RATIO,
    Slot,
    SystemView,
    align,
    assign_slots,
    build_reference,
    labels_by_staff,
    _looks_merged,
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
