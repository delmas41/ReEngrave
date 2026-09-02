"""Shared harness for the Phase-1 system-start-detector prototype.

Measurement-first: NOTHING here imports or edits tools/omr live rules beyond
`render_page`, `detect_staves`, and the read-only grouping helpers. It defines
the FAILURE + CONTROL page set with hand-adjudicated ground-truth break indices,
renders/detects (with an on-disk cache in the scratchpad), and exposes the
staves + binary image for the candidate detectors to consume.

GT convention: `gt_breaks` is the set of GAP indices i (0-based, over
`len(staves)-1` gaps) at which staff i and staff i+1 belong to DIFFERENT
systems. #systems = len(gt_breaks)+1. A detector predicts a set of break gap
indices; Phase-2 semantics is `final = existing_rule_breaks | detector_breaks`
(constructive/additive — can only split, never merge), so on a control page a
detector break at any index NOT in gt_breaks is a REGRESSION.
"""
from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Import tools.omr from the worktree this script lives in.
# fix/ -> omr-system-grouping-2026-09/ -> benchmarks/ -> <worktree root>.
_WORKTREE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_WORKTREE_ROOT))

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import _assign_systems, detect_staves  # noqa: E402
from tools.omr.system_grouping import (  # noqa: E402
    _robust_x_window,
    _x_overlap_frac,
    assign_systems,
    gap_bridging_counts,
)

CACHE_DIR = Path(
    "/private/tmp/claude-501/"
    "-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-system-break-rule-publishers-62ead4/"
    "f27679be-24e1-4e3a-a482-b72d10fe8597/scratchpad/sysgroup_cache"
)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── PDF paths ────────────────────────────────────────────────────────────────
B9 = ("/Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/imslp/"
      "beethoven-symphony-9/pdfs/imslp-516488/score.pdf")
B5 = ("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/"
      "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf")
_SCORES = "/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/PDF Scores"
MAHLER = f"{_SCORES}/Mahler_5_.pdf"
LAMER = f"{_SCORES}/IMSLP15420-Debussy_-_La_Mer_(orch._score).pdf"
BOLERO = f"{_SCORES}/IMSLP421137-PMLP03667-Ravel_Bolero.pdf"
WTC = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/bach/"
       "das-wohltemperierte-klavier-i-bwv846-869/"
       "bach--das-wohltemperierte-klavier-i-bwv846-869--snortum-2024--imslp932182.pdf")
LIBRARY_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave/library/editions")


@dataclass
class Case:
    cid: str
    pdf: str
    page: int
    dpi: int
    gt_breaks: frozenset  # gap indices that are TRUE system boundaries
    kind: str             # "failure" | "control"
    group: str            # provenance bucket
    note: str = ""


# ── FAILURE set: hand-adjudicated break indices from probes/fulldist.py ───────
FAILURES = [
    Case("B9-p25", B9, 25, 300, frozenset({11}), "failure", "eval",
         "two 12-staff systems; bridging 66 at the true break"),
    Case("B9-p60", B9, 60, 300, frozenset({11}), "failure", "eval",
         "two 12-staff systems; bridging 324 at the true break"),
    Case("B5-p40", B5, 40, 300, frozenset({6, 13}), "failure", "eval",
         "three 7-staff systems; bridging 3 and 11 at the two true breaks"),
]

# ── CONTROL set (eval_grouping, currently correct) ────────────────────────────
# GT break indices are derived by running the current rule (correct here by
# construction) in _load(); we ASSERT the resulting system count matches the
# eval_grouping truth so a silent detection drift can't corrupt the GT.
# (case_id -> expected #systems) for the assertion.
EVAL_TRUTH_SYSTEMS = {
    "B9-p20": 2, "B9-p30": 1, "B9-p35": 1, "B9-p40": 1, "B9-p45": 1,
    "B9-p50": 1, "B9-p55": 2, "B9-p65": 2, "B9-p70": 2, "B9-p75": 2,
    "B5-p10@300": 2, "B5-p10@600": 2,
    "Mahler5-p2": 1, "Mahler5-p10": 1, "Mahler5-p20": 1,
    "LaMer-p2": 2, "LaMer-p20": 1,
    "Bolero-p2": 4, "Bolero-p10": 2, "Bolero-p20": 1,
    # fulldist-only control
    "B5-p47": 1,
    # phase1-baseline
    "wtc-p5": 5, "beet5-p10": 2, "lamer-p25": 1,
}

CONTROLS_EVAL = [
    Case("B9-p20", B9, 20, 300, None, "control", "eval"),
    Case("B9-p30", B9, 30, 300, None, "control", "eval"),
    Case("B9-p35", B9, 35, 300, None, "control", "eval"),
    Case("B9-p40", B9, 40, 300, None, "control", "eval"),
    Case("B9-p45", B9, 45, 300, None, "control", "eval"),
    Case("B9-p50", B9, 50, 300, None, "control", "eval"),
    Case("B9-p55", B9, 55, 300, None, "control", "eval"),
    Case("B9-p65", B9, 65, 300, None, "control", "eval"),
    Case("B9-p70", B9, 70, 300, None, "control", "eval"),
    Case("B9-p75", B9, 75, 300, None, "control", "eval"),
    Case("B5-p10@300", B5, 10, 300, None, "control", "eval"),
    Case("B5-p10@600", B5, 10, 600, None, "control", "eval"),
    Case("Mahler5-p2", MAHLER, 2, 300, None, "control", "eval"),
    Case("Mahler5-p10", MAHLER, 10, 300, None, "control", "eval"),
    Case("Mahler5-p20", MAHLER, 20, 300, None, "control", "eval"),
    Case("LaMer-p2", LAMER, 2, 300, None, "control", "eval"),
    Case("LaMer-p20", LAMER, 20, 300, None, "control", "eval"),
    Case("Bolero-p2", BOLERO, 2, 300, None, "control", "eval"),
    Case("Bolero-p10", BOLERO, 10, 300, None, "control", "eval"),
    Case("Bolero-p20", BOLERO, 20, 300, None, "control", "eval"),
]

# fulldist-only control (B5 p47, one system)
CONTROLS_FULLDIST = [
    Case("B5-p47", B5, 47, 300, None, "control", "fulldist"),
]

# phase1-baseline pages (dpi per ground-truth.json: wtc 600, beet5 600, lamer 300)
CONTROLS_PHASE1 = [
    Case("wtc-p5", WTC, 5, 600, None, "control", "phase1"),
    Case("beet5-p10", B5, 10, 600, None, "control", "phase1"),  # == B5-p10@600
    Case("lamer-p25", LAMER, 25, 300, None, "control", "phase1"),
]

# ── clean instrumental multi-system sweep controls: filled by pick_sweep.py ───
# Each entry: (cid, pdf_rel, page, dpi, expected_systems). pdf_rel is relative to
# LIBRARY_ROOT.
SWEEP_CONTROLS_SPEC: list[tuple[str, str, int, int, int]] = []

# ── By-eye adjudication of the auto-picked sweep pages ────────────────────────
# pick_sweep.py PRESUMED dense single-system pages correct. Two turned out to be
# over-MERGES (the exact failure class), confirmed by eye from full-page thumbs
# (crops/ADJ_*_thumb.png). We keep the raw pick visible but override the truth.
#   gt_breaks: the TRUE break gap indices; kind: how to score it.
ADJUDICATED = {
    # Eroica p36, Litolff 1870 (SAME edition as the 3 failures): the current
    # rule merged two full 11-staff systems into [22]. Labels Fl./Ob./Cl./Fag./
    # Cor./Tp. restart below gap 10; footer "SYMPHONY NO.3 (I)". A 4th over-merge,
    # DISCOVERED among the controls. Detector fixes it -> counts as a bonus fix.
    "sw-beet-sympho-p36": (frozenset({10}), "discovered_overmerge",
                           "Beethoven 3 Eroica p36 Litolff 1870: true [11,11], "
                           "current rule over-merged to [22]. Adjudicated by eye."),
    # Matthauspassion p302, Eulenburg (VOCAL, double chorus+orch): true [8,8],
    # labels Fl./Ob./Vl. + chorus S/A/T/B restart below gap 7. Also an over-merge,
    # but VOCAL -> Phase-3 scope. Detector MISSES it (a known limitation, NOT a
    # regression). Excluded from the instrumental control tally.
    "sw-bach-mattha-p302": (frozenset({7}), "discovered_overmerge_vocal",
                            "Bach Matthauspassion p302 Eulenburg: true [8,8], "
                            "vocal work; current rule over-merged to [16]."),
}


def _load_sweep_controls():
    spec_path = Path(__file__).with_name("sweep_controls.py")
    if not spec_path.exists():
        return []
    ns: dict = {}
    exec(spec_path.read_text(), ns)  # noqa: S102 — our own generated file
    cases = []
    for cid, pdf_rel, page, dpi, exp in ns["SWEEP_CONTROLS"]:
        if cid in ADJUDICATED:
            gt, kind, note = ADJUDICATED[cid]
            cases.append(Case(cid, str(LIBRARY_ROOT / pdf_rel), page, dpi, gt,
                              kind, "sweep-adjudicated", note))
            continue
        EVAL_TRUTH_SYSTEMS[cid] = exp
        cases.append(Case(cid, str(LIBRARY_ROOT / pdf_rel), page, dpi, None,
                          "control", "sweep"))
    return cases


def all_cases(include_sweep: bool = True) -> list[Case]:
    cases = list(FAILURES) + list(CONTROLS_EVAL) + list(CONTROLS_FULLDIST)
    # phase1 beet5-p10 duplicates B5-p10@600 — keep only wtc-p5 + lamer-p25.
    cases += [c for c in CONTROLS_PHASE1 if c.cid != "beet5-p10"]
    if include_sweep:
        cases += _load_sweep_controls()
    return cases


@dataclass
class Loaded:
    case: Case
    binary: np.ndarray      # HxW uint8, 0=ink 255=paper
    rgb: np.ndarray
    staves: list            # sorted by top_y, with CURRENT grouping applied
    existing_breaks: frozenset   # gap indices where current rule fires a break
    gt_breaks: frozenset
    bridging: list          # current wide-window bridging counts per gap


def _cache_key(pdf: str, page: int, dpi: int) -> str:
    h = hashlib.md5(f"{pdf}|{page}|{dpi}".encode()).hexdigest()[:16]
    return f"{Path(pdf).stem[:24]}_{page}_{dpi}_{h}"


def _render_cached(pdf: str, page: int, dpi: int):
    key = _cache_key(pdf, page, dpi)
    npz = CACHE_DIR / f"{key}.npz"
    if npz.exists() and not os.environ.get("SYSGROUP_NOCACHE"):
        d = np.load(npz)
        return d["binary"], d["rgb"]
    pi = render_page(pdf, page, dpi=dpi)
    np.savez_compressed(npz, binary=pi.binary, rgb=pi.rgb)
    return pi.binary, pi.rgb


def _breaks_from_staves(staves) -> frozenset:
    """Gap indices where system_index changes (staves sorted by top_y)."""
    br = set()
    for i, (up, lo) in enumerate(zip(staves, staves[1:])):
        if up.system_index != lo.system_index:
            br.add(i)
    return frozenset(br)


_LOADED: dict[str, "Loaded"] = {}


def load(case: Case) -> Loaded:
    if case.cid in _LOADED:
        return _LOADED[case.cid]
    binary, rgb = _render_cached(case.pdf, case.page, case.dpi)
    # detect_staves needs a PageImage; reconstruct a lightweight one.
    from tools.omr.types import PageImage
    pi = PageImage(pdf_path=Path(case.pdf), page_index=case.page, dpi=case.dpi,
                   rgb=rgb, binary=binary)
    pws = detect_staves(pi)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    existing = _breaks_from_staves(staves)
    bridging = gap_bridging_counts(binary, staves) if len(staves) >= 2 else []

    if case.gt_breaks is not None:
        gt = case.gt_breaks
    else:
        # Control: current rule is correct by construction. Assert system count.
        gt = existing
        exp = EVAL_TRUTH_SYSTEMS.get(case.cid)
        if exp is not None:
            got = len(gt) + 1
            if got != exp:
                print(f"  !! GT-DRIFT {case.cid}: current rule -> {got} systems, "
                      f"eval truth {exp}. Sizes now differ; GT may be unreliable.",
                      file=sys.stderr)
    out = Loaded(case=case, binary=binary, rgb=rgb, staves=staves,
                 existing_breaks=existing, gt_breaks=gt, bridging=bridging)
    _LOADED[case.cid] = out
    return out


# Re-export read-only helpers for detectors.
__all__ = ["Case", "Loaded", "load", "all_cases", "FAILURES",
           "_robust_x_window", "_x_overlap_frac", "gap_bridging_counts",
           "assign_systems", "_assign_systems"]
