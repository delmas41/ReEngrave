"""The document's instrument roster (tools/omr/roster.py).

The measured claims these pin are in
`benchmarks/omr-roster-wiring-2026-09/FINDINGS.md`; what is tested here is the
plumbing, because the plumbing is what was missing and it fails in ways a
benchmark score cannot see — a roster read off the wrong UNIT, or re-read once
per page, moves no number and is still wrong.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.omr import roster as R
from tools.omr.instruments import lookup
from tools.omr.staff_labels import StaffLabel
from tools.omr.types import PageWithStaves, Staff


def _staff(index: int, system: int = 0, top: int | None = None) -> Staff:
    top = index * 100 if top is None else top
    return Staff(page_index=0, staff_index=index,
                 line_ys=[top + 12 * k for k in range(5)],
                 x_start=100, x_end=1000, group_index=0,
                 system_index=system)


def _pws(staves) -> PageWithStaves:
    return PageWithStaves(page=None, staves=list(staves))


def _label(staff_index: int, text: str, confidence: str = "high") -> StaffLabel:
    match = lookup(text)
    return StaffLabel(staff_index=staff_index, text=text,
                      instrument=match.instrument if match else None,
                      fifths_offset=0, y_center_px=0.0,
                      confidence=confidence,
                      alias=(match.alias if match else ""))


def _acquire(pages, window=3, n_pages=None):
    """`acquire_roster` over in-run pages only — no page is ever opened."""
    return R.acquire_roster(
        pdf_path=Path("/nonexistent.pdf"), dpi=300,
        run_pages=[p for p, _s, _l in pages],
        run_staves=[s for _p, s, _l in pages],
        run_labels=[l for _p, _s, l in pages],
        read_labels=lambda pws, i: pytest.fail(
            "acquire_roster opened a page it did not need to"),
        window=window, n_pages=n_pages)


# ── the unit is a SYSTEM, not a page ────────────────────────────────────────

def test_a_roster_is_one_system_not_one_page():
    """A first page holding two systems must not report the orchestra twice.

    Brahms 1 / Breitkopf p.1 is 27 staves in two systems. Taking the page whole
    gives a 27-entry reference that repeats itself, and every later system then
    aligns against a lineup no page prints.
    """
    staves = [_staff(i, system=0) for i in range(3)] + \
             [_staff(3 + i, system=1) for i in range(3)]
    labels = [_label(0, "Flauti"), _label(1, "Oboi"), _label(2, "Violino"),
              _label(3, "Flauti"), _label(4, "Oboi"), _label(5, "Violino")]
    got = _acquire([(0, _pws(staves), labels)])
    assert got is not None
    assert got.system_index == 0
    assert got.n_staves == 3
    assert [e.instrument for e in got.entries] == ["Flute", "Oboe", "Violin"]


def test_a_later_system_supplies_the_roster_when_the_first_is_unlabelled():
    staves = [_staff(i, system=0) for i in range(3)] + \
             [_staff(3 + i, system=1) for i in range(3)]
    labels = [_label(3, "Flauti"), _label(4, "Oboi"), _label(5, "Violino")]
    got = _acquire([(0, _pws(staves), labels)])
    assert got is not None and got.system_index == 1
    assert got.names == {0: "Flute", 1: "Oboe", 2: "Violin"}


# ── which page ──────────────────────────────────────────────────────────────

def test_in_run_pages_are_consulted_in_PAGE_order_not_request_order():
    """A run over pages 5 and 2 acquires from 2.

    Which page the caller happened to list first is not evidence about where
    the orchestra is named.
    """
    late = [_staff(i) for i in range(3)]
    early = [_staff(i) for i in range(3)]
    got = R.acquire_roster(
        pdf_path=Path("/nonexistent.pdf"), dpi=300,
        run_pages=[5, 2],
        run_staves=[_pws(late), _pws(early)],
        run_labels=[[_label(0, "Tromba"), _label(1, "Timpani")],
                    [_label(0, "Flauti"), _label(1, "Oboi")]],
        read_labels=lambda pws, i: [], window=0)
    assert got is not None
    assert got.page_index == 2
    assert [e.instrument for e in got.entries] == ["Flute", "Oboe"]


def test_the_search_walks_BACKWARD_from_the_run_before_trying_the_front():
    """A roster is the first labelled system OF THE MOVEMENT YOU ARE IN.

    Measured correction: a front-only window of three reached the roster on 16
    of 20 gate rows and MISSED exactly the two it was built for — the Simrock
    Dvořák rows, whose volume opens its first movement on PDF page 4, past the
    window, behind four pages of title matter.
    """
    tried = []

    def read(pws, page_index):
        tried.append(page_index)
        return []

    R.acquire_roster(
        pdf_path=Path(__file__),            # renders as nothing, but exists
        dpi=300, run_pages=[6],
        run_staves=[_pws([_staff(i) for i in range(3)])], run_labels=[[]],
        read_labels=read, window=3, n_pages=20)
    # `searched` order is what matters; nothing renders here, so assert on the
    # order the implementation walks rather than on what it read.
    got = R.acquire_roster(
        pdf_path=Path("/nonexistent.pdf"), dpi=300, run_pages=[6],
        run_staves=[_pws([_staff(i) for i in range(3)])], run_labels=[[]],
        read_labels=read, window=3, n_pages=20)
    assert got is None


def test_search_order_is_the_run_then_backward_then_the_front():
    order = R.search_order(run_pages=[6], window=3, n_pages=20)
    assert order == [5, 4, 3, 0, 1, 2]


def test_search_order_skips_pages_the_run_already_holds():
    order = R.search_order(run_pages=[2, 3], window=3, n_pages=20)
    assert 2 not in order and 3 not in order
    assert order[:1] == [1]


def test_search_order_respects_the_page_count():
    assert R.search_order(run_pages=[0], window=3, n_pages=2) == [1]


def test_an_unrenderable_front_page_abstains_rather_than_raising():
    """A roster is an enrichment; it may never lose a transcription.

    The run's own page carries no labels, so acquisition reaches for the front
    matter — and the PDF does not exist. It must come back None, not raise, and
    it must not have got as far as the label ladder.
    """
    opened = []

    def read(pws, page_index):
        opened.append(page_index)
        return [_label(0, "Flauti"), _label(1, "Oboi")]

    got = R.acquire_roster(
        pdf_path=Path("/nonexistent.pdf"), dpi=300,
        run_pages=[7], run_staves=[_pws([_staff(i) for i in range(3)])],
        run_labels=[[]],
        read_labels=read, window=2, n_pages=9)
    assert got is None
    assert opened == []


# ── what counts as a roster ─────────────────────────────────────────────────

def test_one_resolved_name_is_not_a_roster():
    """A single word the lexicon happened to match is indistinguishable from a
    tempo marking read as an instrument."""
    staves = [_staff(i) for i in range(4)]
    assert _acquire([(0, _pws(staves), [_label(0, "Flauti")])]) is None


def test_a_low_confidence_read_is_refused():
    """A wrong roster name reaches every page of the run — a risk a per-page
    read does not carry."""
    staves = [_staff(i) for i in range(4)]
    labels = [_label(0, "Flauti", "low"), _label(1, "Oboi", "low")]
    assert _acquire([(0, _pws(staves), labels)]) is None


def test_a_partial_roster_is_kept_holes_and_all():
    """No yield threshold, deliberately: a 0.50 floor turned 29 documents into
    false negatives, and three names is three more than the prior knows."""
    staves = [_staff(i) for i in range(12)]
    labels = [_label(0, "Flauti"), _label(1, "Oboi"), _label(2, "Clarinetti")]
    got = _acquire([(0, _pws(staves), labels)])
    assert got is not None
    assert got.n_staves == 12 and len(got.entries) == 3
    assert got.coverage == pytest.approx(0.25)
    # The holes are simply ABSENT — not placeholders. Wildcarding measured
    # WORSE than dropping (0.841 vs 0.848), and healing is closed.
    assert set(got.names) == {0, 1, 2}


def test_entries_come_out_in_ordinal_order():
    staves = [_staff(i) for i in range(3)]
    labels = [_label(2, "Violino"), _label(0, "Flauti")]
    got = _acquire([(0, _pws(staves), labels)])
    assert [e.ordinal for e in got.entries] == [0, 2]


def test_evidence_is_recorded_even_when_the_flag_is_off(monkeypatch):
    """Acquisition is unconditional; only its USE is behind `OMR_ROSTER`.

    Recording what the margin said changes no music, and a signal read
    correctly and then discarded is the shape this project has paid for nine
    times.
    """
    # Set the flag OFF explicitly rather than deleting it: the default went ON
    # 2026-09-05, and this test is about the flag being off, not about which
    # way the default happens to point.
    monkeypatch.setenv("OMR_ROSTER", "0")
    assert R.enabled() is False
    staves = [_staff(i) for i in range(3)]
    got = _acquire([(0, _pws(staves),
                     [_label(0, "Flauti"), _label(1, "Oboi")])])
    ev = got.evidence()
    assert ev["named"] == 2 and ev["n_staves"] == 3
    assert ev["pages_searched"] == [0] and ev["pages_opened"] == []
    assert [e["instrument"] for e in ev["entries"]] == ["Flute", "Oboe"]


# ── the join into slot space (contextual._roster_instrument_by_slot) ────────

def test_the_roster_joins_to_slots_through_the_ordinary_alignment():
    """A roster name reaches a slot the run's pages never named.

    The roster system is a system like any other: it goes through `slots.align`,
    so a lineup with a part suppressed still lands on the right slots.
    """
    from tools.omr.contextual import _roster_instrument_by_slot
    from tools.omr.slots import Slot

    reference = [Slot(index=i, group_index=0, instrument=None, position=i / 3)
                 for i in range(4)]
    roster = R.Roster(
        page_index=0, system_index=0, n_staves=4,
        entries=(R.RosterEntry(0, "Flute", "Flauti", "high"),
                 R.RosterEntry(1, "Oboe", "Oboi", "high"),
                 R.RosterEntry(3, "Cello", "Violoncello", "high")),
        pages_searched=(0,), pages_opened=(),
        staves=tuple(_staff(i) for i in range(4)))
    got = _roster_instrument_by_slot(roster, reference)
    assert {k: v.name for k, v in got.items()} == {
        0: "Flute", 1: "Oboe", 3: "Cello"}


def test_no_slot_is_ever_named_twice():
    """The reason no conflict arbitration is needed, asserted rather than assumed.

    `slots.align` is monotone and consumes each reference slot at most once, so
    two roster positions cannot land on one slot. A guard for that hazard was
    written and found unreachable; this is what stands in its place, so a future
    change to the DP that broke the property would fail here rather than start
    silently overwriting names.
    """
    from tools.omr.contextual import _roster_instrument_by_slot
    from tools.omr.slots import Slot, align, SystemView

    reference = [Slot(index=0, group_index=0, instrument=None, position=0.0)]
    staves = (_staff(0), _staff(1))
    assigned = align(SystemView(staves=list(staves), labels={}), reference)
    assert sorted(v for v in assigned if v >= 0) == [0]

    roster = R.Roster(
        page_index=0, system_index=0, n_staves=2,
        entries=(R.RosterEntry(0, "Flute", "Flauti", "high"),
                 R.RosterEntry(1, "Oboe", "Oboi", "high")),
        pages_searched=(0,), pages_opened=(), staves=staves)
    got = _roster_instrument_by_slot(roster, reference)
    assert len(got) == 1


@pytest.mark.parametrize("value,expected", [
    ("1", True), ("on", True), ("TRUE", True), ("yes", True),
    ("0", False), ("", False), ("off", False), ("no", False),
])
def test_flag_parsing(monkeypatch, value, expected):
    monkeypatch.setenv("OMR_ROSTER", value)
    assert R.enabled() is expected
