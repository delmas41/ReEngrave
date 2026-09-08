"""The scan gate's staff lineup must count the same things our part list does.

⚠️ **THIS GUARDS A UNITS ERROR THAT COST 4,815 SYMBOL ROWS.**
`benchmarks/omr-scan-e2e-2026-09/works.json`'s `staves` is one entry per
PRINTED staff — including one-line percussion rules, and including a grand
staff written as one instrument — while our export emits one part per FIVE-LINE
staff we detected. `run_ledger.part_join_for` compared the two counts directly
and declared the difference a guess, so three Mahler rows and one Bach row were
`part_unresolved` in full for a reason that was arithmetic, not evidence.
`benchmarks/omr-part-join-2026-09/FINDINGS.md`.

The two engraving facts are now FIELDS rather than prose: `one_line: true` and
`printed_staves: N`. These tests are what stop the next hand-verified row from
reintroducing the mismatch silently — a new one-line staff added to a lineup
without its flag fails here rather than showing up as an unexplained refusal
weeks later.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
WORKS = ROOT / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"
RUN_LEDGER = (ROOT / "benchmarks" / "omr-symbol-ledger-2026-09" / "run_ledger.py")


def _run_ledger():
    spec = importlib.util.spec_from_file_location("_run_ledger", RUN_LEDGER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rows():
    d = json.loads(WORKS.read_text())
    return {r["row_id"]: r for r in d["rows"]}


def _lineup(row, rows):
    st = row.get("staves")
    seen = set()
    while isinstance(st, str) and st.startswith("same-as:"):
        other = st.split(":", 1)[1].strip()
        if other in seen:
            return None
        seen.add(other)
        st = (rows.get(other) or {}).get("staves")
    return st if isinstance(st, list) else None


@pytest.mark.parametrize("rid", sorted(_rows()))
def test_the_lineup_expands_to_the_five_line_staves_the_page_prints(rid):
    """`expand_lineup` must land on the page's own five-line count PER SYSTEM.

    ⚠️ Asserted only where the systems are UNIFORM (`n_staves % n_systems == 0`).
    A tacet-suppressed page prints a different lineup per system — Beethoven p3
    is 11 then 8 — and `staves` describes one of them, so there is no single
    number to check against. Those rows are skipped by name in the output, not
    silently passed.
    """
    rows = _rows()
    row = rows[rid]
    staves = _lineup(row, rows)
    if not staves:
        pytest.skip(f"{rid}: no staff lineup (that is cause D, a missing fact)")
    page = row.get("page", {})
    n_staves, n_sys = page.get("n_staves"), page.get("n_systems") or 1
    if not n_staves or n_staves % n_sys:
        pytest.skip(f"{rid}: {n_staves} staves over {n_sys} systems is not "
                    f"uniform, so one lineup names no single count")
    slots = _run_ledger().expand_lineup(staves)
    assert len(slots) == n_staves // n_sys, (
        f"{rid}: the lineup expands to {len(slots)} five-line staves but the "
        f"page prints {n_staves // n_sys} per system. Either a one-line "
        f"percussion rule is missing `one_line: true`, or a lineup entry the "
        f"page prints as several staves is missing `printed_staves: N`.")


def test_one_line_entries_reconcile_with_the_prose_count():
    """`len(staves) - page.n_staves` is the DERIVABLE one-line count, and the
    flags must match it. The two facts come from different places — the count
    from two numeric fields, the identity hand-read off `n_staves_note` — so
    agreeing is worth asserting."""
    rows = _rows()
    checked = 0
    for rid, row in rows.items():
        staves = _lineup(row, rows)
        page = row.get("page", {})
        if not staves or not page.get("n_staves") or (page.get("n_systems") or 1) != 1:
            continue
        derivable = len(staves) - page["n_staves"]
        flagged = sum(1 for s in staves if isinstance(s, dict) and s.get("one_line"))
        extra = sum(int(s.get("printed_staves") or 1) - 1
                    for s in staves if isinstance(s, dict) and not s.get("one_line"))
        assert flagged - extra == derivable, (
            f"{rid}: {flagged} entries flagged one_line and {extra} extra "
            f"printed staves, but len(staves) - n_staves = {derivable}")
        checked += 1
    # ⚠️ a positive control: a zero here would pass vacuously
    assert checked >= 4, f"only {checked} single-system rows checked"


def test_a_one_line_staff_emits_no_part_and_an_extra_printed_staff_emits_one():
    m = _run_ledger()
    lineup = [{"name": "Fl", "parts": [0]},
              {"name": "Becken", "parts": [1], "one_line": True},
              {"name": "Cembalo", "parts": [2], "printed_staves": 2},
              {"name": "Vln", "parts": [3]}]
    slots = m.expand_lineup(lineup)
    assert [s["name"] if s else None for s in slots] == \
        ["Fl", "Cembalo", None, "Vln"], \
        "the one-line rule drops out; the grand staff's second staff is a slot " \
        "with no reference part of its own"
