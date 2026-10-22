"""Choir-grouping cues (OMR_CHOIR_GROUPING) — the Brandenburg 3 page, end to end.

The stress row of the scan benchmark (bach-brandenburg3-mvt1-468678-p1): two
systems of twelve staves, indented DIFFERENTLY (system 1 carries full
instrument names), interior barlines drawn per instrument choir. The
page-median scan window lands between the two indentation modes and cuts
system 2's left-edge complex out of the scan, so its choir gaps read
bridging = 0 and the system shatters into 3/3/3/1/2 fragments, whose
rhythm-unison stems then out-vote the barlines: 122 measure-cells against a
true 10. Diagnosis with the page-ink numbers:
benchmarks/omr-choir-grouping-2026-09/FINDINGS.md.

Cue B (pair-local left-edge merge, tools/omr/system_grouping.py) cancels the
window-blind breaks; cue C (tools/omr/measure_extractor.py) keeps the merged
grouped system out of open-score mode so its stem columns are filtered again.
Both ride the one flag, DEFAULT OFF.

Two directions, the test_left_edge_split_e2e pattern:

  * flag ON: the page reads as two 12-staff systems, system 2 exactly its
    printed five bars;
  * flag OFF: the page still shatters — byte-level default behavior is
    untouched, and if this ever fails, upstream grouping has started reading
    bimodal indentation on its own (re-pick the fixture; a finding, not a
    bug).

Marked `omr_smoke`: needs the central score library on disk and ~2 min of CV
(one 600-dpi render + two structural passes). Skips where the PDF is absent.
"""
from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

import pytest

from tools.library.score_library import editions_root
from tools.omr.measure_extractor import detect_barlines, extract_measures
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves

pytestmark = pytest.mark.omr_smoke

PDF_REL = ("bach/brandenburg-concerto-3-in-g-major-bwv1048/"
           "bach--brandenburg-concerto-3-in-g-major-bwv1048--"
           "edition-peters-nr-4412--imslp468678.pdf")
PAGE, DPI = 0, 600

# Hand-read truth (works.json row + VERIFICATION.md, 2026-09-04): two systems
# of 12; system 1 prints a narrow pickup cell + 4 bars (5 cells), system 2
# prints 5 bars. The pipeline reads system 1 as SIX cells — a pre-existing
# spurious split at x=1518 inside printed bar 1 (FINDINGS.md §4), present
# with the flag off and untouched by these cues — so the flag-ON assertion
# pins [6, 5] and must become [5, 5] when that defect is fixed.
TRUTH_SYSTEMS = 2
TRUTH_STAVES = [12, 12]
EXPECTED_MEASURES_FLAG_ON = [6, 5]


def _layout(pdf: Path, *, flag: bool):
    old = os.environ.get("OMR_CHOIR_GROUPING")
    os.environ["OMR_CHOIR_GROUPING"] = "1" if flag else "0"
    try:
        pws = detect_barlines(detect_staves(render_page(pdf, PAGE, dpi=DPI)))
        cells = extract_measures(pws)
    finally:
        if old is None:
            os.environ.pop("OMR_CHOIR_GROUPING", None)
        else:
            os.environ["OMR_CHOIR_GROUPING"] = old
    staves_per_system = Counter(s.system_index for s in pws.staves)
    measures_per_system: dict[int, set[int]] = {}
    for c in cells:
        measures_per_system.setdefault(c.system_index, set()).add(c.measure_index)
    return {
        "n_systems": len(staves_per_system),
        "staves_per_system": [staves_per_system[i]
                              for i in sorted(staves_per_system)],
        "measures_per_system": [len(measures_per_system[i])
                                for i in sorted(measures_per_system)],
    }


_CACHE: dict[bool, dict] = {}


def _run(*, flag: bool) -> dict:
    pdf = editions_root() / PDF_REL
    if not pdf.exists():
        pytest.skip(f"library edition not present: {pdf}")
    if flag not in _CACHE:
        _CACHE[flag] = _layout(pdf, flag=flag)
    return _CACHE[flag]


# ─── flag ON ─────────────────────────────────────────────────────────────────


def test_flag_on_two_systems_of_twelve():
    out = _run(flag=True)
    assert out["n_systems"] == TRUTH_SYSTEMS
    assert out["staves_per_system"] == TRUTH_STAVES


def test_flag_on_measures():
    out = _run(flag=True)
    assert out["measures_per_system"] == EXPECTED_MEASURES_FLAG_ON


# ─── flag OFF: the page must still need the cues ─────────────────────────────


def test_flag_off_still_shatters():
    """Fixture-validity guard, not desired behavior (see module docstring)."""
    out = _run(flag=False)
    assert out["n_systems"] > TRUTH_SYSTEMS
