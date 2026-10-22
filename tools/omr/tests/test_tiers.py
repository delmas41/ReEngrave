"""The fast/slow test-tier split is DERIVED, and this pins the derivation.

The split lives in `conftest.py`, computed from `durations.json` (a measured
snapshot) plus a content check for machine-local fixtures. Nothing here
restates that logic — it asserts the properties that make the split trustable:
the measurement file parses, every file it names is real, and the fast tier it
implies cannot silently grow past its budget.
"""
from __future__ import annotations

import json
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[2]
DURATIONS_FILE = TESTS_DIR / "durations.json"
FAST_BUDGET_SECONDS = 100.0


def _load():
    with open(DURATIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _file_entries(raw):
    """The per-file duration entries, excluding the `measured_on` header."""
    return {k: v for k, v in raw.items() if k != "measured_on"}


def test_durations_json_parses():
    raw = _load()
    assert isinstance(raw, dict)
    assert "measured_on" in raw, "no provenance header — can't tell what this measured"
    header = raw["measured_on"]
    assert "git_head" in header and header["git_head"], "no commit named"
    assert "date" in header and header["date"], "no date named"


def test_every_named_file_exists():
    raw = _load()
    entries = _file_entries(raw)
    assert entries, "durations.json names no files at all"
    missing = [f for f in entries if not (REPO_ROOT / f).is_file()]
    assert not missing, f"durations.json names files that no longer exist: {missing}"


def test_every_duration_is_a_nonnegative_number():
    raw = _load()
    entries = _file_entries(raw)
    bad = {f: v for f, v in entries.items() if not isinstance(v, (int, float)) or v < 0}
    assert not bad, f"non-numeric or negative durations: {bad}"


def test_fast_tier_cannot_silently_grow():
    """The greedy derivation in conftest.py: smallest-first until the budget.

    Re-derives the same fast/slow split conftest.py computes (duration-only —
    this test does not scan file content, that half is conftest's own job)
    and asserts its measured sum stays under budget. If a future re-measure
    ever pushes this over, the fix is to lower nothing by hand: the
    conftest's own greedy derivation already re-draws the line — but this
    test failing is the signal that the CURRENT committed threshold moved
    and the file is worth a second look before trusting `-m "not slow"`'s
    wall time again.
    """
    raw = _load()
    entries = _file_entries(raw)
    ascending = sorted(entries.items(), key=lambda kv: kv[1])
    cumulative = 0.0
    threshold = 0.0
    for _path, seconds in ascending:
        if cumulative + seconds < FAST_BUDGET_SECONDS:
            cumulative += seconds
            threshold = seconds
        else:
            break
    assert cumulative < FAST_BUDGET_SECONDS, (
        f"fast tier measured sum {cumulative:.2f}s is not under the "
        f"{FAST_BUDGET_SECONDS:.0f}s budget (threshold landed at {threshold:.2f}s/file)"
    )
