"""Left-edge system-split (cue A) regression — SCANNED pages, end to end.

The grouping eval (`benchmarks/omr-system-grouping-2026-08/eval_grouping.py`)
asserts system COUNTS only, and the orchestral OMR-NED benchmark renders its
input through LilyPond, whose systems are always grouped correctly — so cue A
(`OMR_LEFT_EDGE_SPLIT`, tools/omr/system_grouping.py) never fires on any
existing fixture and its end-to-end effect was unmeasured. These tests run the
structural pipeline (render → staves → systems → barlines → measures) on four
scanned pages, three publishers, where the wide connectivity window merges two
stacked systems and cue A recovers the break.

What the split is worth downstream, measured on these pages at 600 dpi: merged,
Eroica p.36 comes out as one 22-staff system of TEN measures where the page
prints two 11-staff systems of eight each — barlines must span the whole merged
block to survive the vote, so most of them don't. Every count asserted here is
hand-read truth (`benchmarks/omr-system-grouping-2026-09/gt/e2e-ground-truth.json`),
not blessed pipeline output.

Two directions are guarded:

  * flag ON (the default): the page reads as two systems with the hand-counted
    staff and measure structure — a grouping change that breaks the split now
    fails four tests instead of shipping silently;
  * flag OFF: the page still MERGES. If this ever fails, upstream grouping has
    started splitting these pages on its own — the fixture then no longer
    stresses cue A and needs re-picking from the sweep
    (`benchmarks/omr-system-grouping-2026-09/fix/diff_leftedge.py`), which is a
    finding, not a bug.

Marked `omr_smoke`: needs the central score library on disk (machine-local,
gitignored) and ~30 s of CV. Skips cleanly where the PDFs are absent.
ORCHESTRAL SCORES ONLY — do not add Nottebohm pages here.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

import pytest

from tools.library.score_library import editions_root
from tools.omr.measure_extractor import detect_barlines, extract_measures
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves

pytestmark = pytest.mark.omr_smoke

GT_PATH = (Path(__file__).resolve().parents[3] / "benchmarks"
           / "omr-system-grouping-2026-09" / "gt" / "e2e-ground-truth.json")
GT = json.loads(GT_PATH.read_text())["pages"]
CASE_IDS = sorted(GT)


def _layout(pdf: Path, page_index: int, dpi: int, *, split: bool):
    """Run the structural pipeline with `OMR_LEFT_EDGE_SPLIT` forced.

    The flag is read from the environment at `assign_systems` call time, so
    forcing it here (and restoring after) keeps the test independent of the
    ambient shell.
    """
    old = os.environ.get("OMR_LEFT_EDGE_SPLIT")
    os.environ["OMR_LEFT_EDGE_SPLIT"] = "1" if split else "0"
    try:
        pws = detect_barlines(detect_staves(render_page(pdf, page_index, dpi=dpi)))
        cells = extract_measures(pws)
    finally:
        if old is None:
            os.environ.pop("OMR_LEFT_EDGE_SPLIT", None)
        else:
            os.environ["OMR_LEFT_EDGE_SPLIT"] = old

    staves_per_system = Counter(s.system_index for s in pws.staves)
    measures_per_staff: dict[tuple[int, int], int] = Counter(
        (c.system_index, c.staff_index) for c in cells)
    measures_per_system: dict[int, set[int]] = {}
    for c in cells:
        measures_per_system.setdefault(c.system_index, set()).add(c.measure_index)
    return {
        "n_systems": len(staves_per_system),
        "staves_per_system": [staves_per_system[i]
                              for i in sorted(staves_per_system)],
        "measures_per_system": [len(measures_per_system[i])
                                for i in sorted(measures_per_system)],
        "measures_per_staff": measures_per_staff,
    }


def _case(case_id: str) -> tuple[dict, Path]:
    gt = GT[case_id]
    pdf = editions_root() / gt["pdf_rel"]
    if not pdf.exists():
        pytest.skip(f"library edition not present: {pdf}")
    return gt, pdf


# One pipeline run per (page, flag), shared by every assertion on it.
_CACHE: dict[tuple[str, bool], dict] = {}


def _run(case_id: str, *, split: bool) -> tuple[dict, dict]:
    gt, pdf = _case(case_id)
    key = (case_id, split)
    if key not in _CACHE:
        _CACHE[key] = _layout(pdf, gt["page"], gt["dpi"], split=split)
    return gt, _CACHE[key]


# ─── flag ON (the default): the split, measured end to end ───────────────────


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_system_count(case_id):
    gt, out = _run(case_id, split=True)
    assert out["n_systems"] == gt["systems"]


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_staves_per_system(case_id):
    gt, out = _run(case_id, split=True)
    assert out["staves_per_system"] == gt["staves_per_system"]


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_measures_per_system(case_id):
    gt, out = _run(case_id, split=True)
    assert out["measures_per_system"] == gt["measures_per_system"]


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_no_single_staff_system(case_id):
    """`_suppress_orphaning_breaks`: cue A may never orphan a lone staff."""
    _gt, out = _run(case_id, split=True)
    assert 1 not in out["staves_per_system"]


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_every_staff_carries_its_system_measure_count(case_id):
    """The split's cash value: barlines survive the vote per REAL system, so
    every staff of a system gets the same, full measure row. Merged, staves
    lose measures unevenly to barlines that fail to span the merged block."""
    gt, out = _run(case_id, split=True)
    for (sys_i, staff_i), n in sorted(out["measures_per_staff"].items()):
        assert n == gt["measures_per_system"][sys_i], (
            f"system {sys_i} staff {staff_i}: {n} measures against "
            f"{gt['measures_per_system'][sys_i]} for the system")


# ─── flag OFF: these pages must still need cue A ─────────────────────────────


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_without_the_split_the_page_still_merges(case_id):
    """Fixture-validity guard, not a desired behavior. If this fails, the wide
    window has started grouping this page correctly on its own — cue A is no
    longer exercised here, and the case must be re-picked from the sweep
    rather than deleted (see the module docstring)."""
    gt, out = _run(case_id, split=False)
    assert out["n_systems"] < gt["systems"], (
        f"{case_id}: grouping now splits this page without cue A — the "
        f"fixture no longer stresses OMR_LEFT_EDGE_SPLIT; re-pick a merged "
        f"page from benchmarks/omr-system-grouping-2026-09/")
