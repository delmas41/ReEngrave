"""ONE place for the staged pipeline's per-page time-budget constants —
ROADMAP 1.2b and 3.3's second half (the web job budget).

`benchmarks/acceptance/gather_movement.sh` step 5 used to spell the GATHER
half of this arithmetic inline (`n * 93`, `n * (93 + 267)`) and said nothing
about the rest of the pipeline — the exact defect 1.2b named: the estimate
that actually mattered, because ADJUDICATE/EVALUATE/INFER/write turned a
25-minute GATHER into a 12.8-hour run on 16 Beethoven pages, was never
printed anywhere. `backend/modules/staged_omr.py` (the web app's job budget)
and `gather_movement.sh` both call `estimate_job_budget_s` here rather than
restating any of these numbers a second or third time (CLAUDE.md rule 9).

⚠️⚠️ THE POST-GATHER FIGURE IS AN UPPER BOUND, NOT A MEASUREMENT OF TODAY'S
TREE, AND THIS FUNCTION SAYS SO IN ITS OWN OUTPUT. It comes from exactly one
data point — the 16-page Litolff whole-movement run (CLAUDE.md §5b /
ROADMAP.md 1.2b) — taken BEFORE roadmap 1.2's own two fixes (the clean-tree
guard and this module). A number that predates the fix meant to speed up the
thing it measures can only overstate the cost, never understate it, which is
why it is safe to use for a REFUSAL threshold (roadmap 3.3's job budget) even
though it is not safe to quote as "how long this will take". It stays this
way until a 16-page re-run on the fixed tree replaces it — CLAUDE.md rule 7:
a number that is exactly another number, carried forward unmeasured, is a
computation, not a measurement, and must say so.
"""
from __future__ import annotations

from typing import Any, Dict

# ─────────────────────────────────────────────────────────────────────────
# The constants (CLAUDE.md §5b), in ONE place.
# ─────────────────────────────────────────────────────────────────────────

#: Measured on Litolff Beethoven 5 p.1-4 (scan, margin labels present):
#: GATHER alone, with `OMR_DIRECTION_TEXT_SCAN_GATE=1` skipping the
#: direction-word reader on a page already proved a scan.
GATHER_S_PER_PAGE_WITH_DIRECTION_GATE = 93.0

#: The same GATHER stage if the gate never fires and the direction-word
#: reader runs on every page too (CLAUDE.md §5b: ~267 s/page more) — the
#: conservative upper bound `gather_movement.sh` has always printed
#: alongside the expected figure.
GATHER_S_PER_PAGE_WITHOUT_DIRECTION_GATE = 93.0 + 267.0

#: ROADMAP 1.2b's one data point: the 16-page Litolff whole-movement run.
#: GATHER measured ~25 minutes over 16 pages (~93.75 s/page — consistent
#: with the constant above); the REST of the pipeline (ADJUDICATE,
#: EVALUATE, INFER, write) measured ~12.3 HOURS over the same 16 pages,
#: single core. See the module docstring for why this is an upper bound.
_LITOLFF_16PAGE_RUN_PAGES = 16
_LITOLFF_16PAGE_RUN_GATHER_MINUTES = 25.0
_LITOLFF_16PAGE_RUN_POST_GATHER_HOURS = 12.3

POST_GATHER_S_PER_PAGE_UPPER_BOUND = (
    _LITOLFF_16PAGE_RUN_POST_GATHER_HOURS * 3600.0 / _LITOLFF_16PAGE_RUN_PAGES)

#: Printed beside every estimate this module produces — never left implicit,
#: because "12.3 h for the rest" read without this sentence is a measurement
#: and read with it is a bound. See the module docstring's second paragraph.
POST_GATHER_UPPER_BOUND_CAVEAT = (
    "the post-GATHER figure (ADJUDICATE/EVALUATE/INFER/write) is a single "
    f"{_LITOLFF_16PAGE_RUN_PAGES}-page Litolff data point that PREDATES "
    "roadmap 1.2's two fixes, and is therefore an UPPER BOUND -- not a "
    "measurement of today's tree -- until a 16-page re-run on the fixed "
    "tree replaces it")


def estimate_job_budget_s(n_pages: int, *,
                          direction_text_scan_gate: bool = True
                          ) -> Dict[str, Any]:
    """Seconds, over `n_pages`, for a whole staged run: GATHER through
    EXPORT. A COMPUTATION from the constants above, never a measurement of
    the requested document — see the module docstring.

    `direction_text_scan_gate` mirrors `OMR_DIRECTION_TEXT_SCAN_GATE`
    (CLAUDE.md §5b, default on for a page already proved a scan): True (the
    expected case) uses the WITH-gate GATHER constant; False is the
    conservative bound if the gate never fires on any page.
    """
    if n_pages < 0:
        raise ValueError(f"n_pages must be >= 0, got {n_pages}")
    gather_with_gate = n_pages * GATHER_S_PER_PAGE_WITH_DIRECTION_GATE
    gather_without_gate = n_pages * GATHER_S_PER_PAGE_WITHOUT_DIRECTION_GATE
    post_gather = n_pages * POST_GATHER_S_PER_PAGE_UPPER_BOUND
    gather_expected = gather_with_gate if direction_text_scan_gate else gather_without_gate
    return {
        "n_pages": n_pages,
        "direction_text_scan_gate": direction_text_scan_gate,
        "gather_s_with_direction_gate": gather_with_gate,
        "gather_s_without_direction_gate": gather_without_gate,
        "post_gather_s_upper_bound": post_gather,
        # ⚠️ THE FIGURE A CALLER SHOULD ACT ON. Expected uses the gate this
        # run will actually apply; upper_bound is the same total if the gate
        # never fires anywhere -- both carry the post-GATHER upper bound,
        # since no better figure for that half exists yet.
        "total_s_expected": gather_expected + post_gather,
        "total_s_upper_bound": gather_without_gate + post_gather,
        "data_point": (
            f"{_LITOLFF_16PAGE_RUN_PAGES}-page Litolff run: GATHER ~"
            f"{_LITOLFF_16PAGE_RUN_GATHER_MINUTES:.0f} min, ~"
            f"{_LITOLFF_16PAGE_RUN_POST_GATHER_HOURS} h for the rest, "
            "single core"),
        "caveat": POST_GATHER_UPPER_BOUND_CAVEAT,
    }


def _fmt_s(seconds: float) -> str:
    return f"{seconds:.0f}s (~{seconds / 60:.1f} min, ~{seconds / 3600:.2f} h)"


def format_budget_report(estimate: Dict[str, Any]) -> str:
    """A plain-words rendering of `estimate_job_budget_s`'s output, for a
    human reading a terminal — shared by the CLI-adjacent scripts
    (`gather_movement.sh`) and anywhere else this needs to be READ rather
    than stored."""
    n = estimate["n_pages"]
    lines = [
        f"── budget estimate over {n} pages"
        + ("" if estimate["direction_text_scan_gate"]
           else " (direction-text scan gate OFF)") + ":",
        f"   expected: {_fmt_s(estimate['total_s_expected'])}",
        f"   upper bound (direction-text gate never fires on any page): "
        f"{_fmt_s(estimate['total_s_upper_bound'])}",
        f"   data point: {estimate['data_point']}",
        f"   ⚠️ {estimate['caveat']}",
    ]
    return "\n".join(lines)
