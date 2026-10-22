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

⚠️⚠️ 2026-09-28 RECALIBRATION (ROADMAP item 0 / 1.2b). The constant this
module shipped with (`_LITOLFF_09_22_POST_GATHER_S_PER_PAGE`, ~623 s/page)
came from exactly ONE data point — the 16-page Litolff run taken BEFORE
roadmap 1.2's two fixes — and it OVER-REFUSED: scaled to a 27-page Brahms
job it priced ~21 hours against a 14-hour default budget, and that job
actually ran in 1 h 11 m. The overnight re-gather (ROADMAP.md START HERE
item 0, `benchmarks/acceptance/manifest.json`, commit `c19cbca7`, clean
tree) is the 16-page Litolff re-run this module's own docstring said it was
waiting for, PLUS a 27-page Brahms whole-movement run, and both replace the
stale data point below:

  * beethoven5-litolff, 16 pages (1-16): driver-log bracket
    2026-09-28T06:36:32Z – 07:08:53Z = 1941 s wall (32 m 21 s).
  * brahms1-breitkopf, 27 pages (0-26): driver-log bracket
    2026-09-28T04:07:02Z – 06:36:32Z = 8970 s wall (2 h 29 m 30 s). ⚠️ RAN
    UNDER HEAVY MACHINE CONTENTION from other sessions that night — the
    same document alone measured 1 h 11 m nine days earlier (ROADMAP.md
    1.1, commit `275641c0`) on the SAME 27 pages. Its per-page figure is
    therefore already padded well past a quiet-machine number, which is
    the right direction for an UPPER bound and the wrong direction to read
    as "how long this actually takes."

⚠️⚠️ NEITHER LOG CARRIES A TIMESTAMP PER LINE (checked: every progress line
in both is a bare counter — "N verdicts so far" — printed once per decision
kind, not on a clock; GATHER's own per-cell detection lines are the same).
So GATHER cannot be split from ADJUDICATE/EVALUATE/INFER/write inside
either run — only the DRIVER LOG's start/exit bracket around the whole
document is a real measurement. What follows is a COMPUTATION, not a
independent measurement of GATHER and post-GATHER: it takes the
GATHER-alone constants below as given (unchanged by this recalibration —
1.2's fixes targeted ADJUDICATE/EVALUATE/INFER, not GATHER, and 93 s/page
is itself an independent, already-validated figure, consistent with the
09-22 Litolff data point's own ~25 min / 16 pages ≈ 93.75 s/page GATHER
half) and attributes EVERY remaining second of each document's bracket to
post-GATHER. Where GATHER actually took less than 93 s/page this run, that
inflates the post-GATHER figure it derives — again, the safe direction for
a refusal threshold.

The two documents' derived post-GATHER-per-page figures are NOT the same
(Litolff ≈ 28 s/page, Brahms ≈ 239 s/page) — expected, since 1.2's own
finding was that the pre-fix cost scaled with system/glyph density, not
page count alone, and Brahms's own ROADMAP entry calls it "27 DENSER
pages." Per this item's brief ("take the slower document per page"), the
new `POST_GATHER_S_PER_PAGE_UPPER_BOUND` is the MAX of the two — Brahms,
already padded by contention on top of that.

⚠️⚠️ THE POST-GATHER FIGURE IS STILL AN UPPER BOUND, NOT A MEASUREMENT OF
ANY ONE JOB'S REAL COST, for three independent reasons, compounding: (1) it
is a computation (total minus an assumed GATHER share), never a direct
timestamp-based measurement, as above; (2) it takes the slower of two
documents; (3) that slower document ran under contention. It stays this way
until a quiet, single-purpose, timestamped re-run replaces it — CLAUDE.md
rule 7: a number that is exactly another number, carried forward
unmeasured, is a computation, not a measurement, and must say so.
"""
from __future__ import annotations

from typing import Any, Dict

# ─────────────────────────────────────────────────────────────────────────
# The constants (CLAUDE.md §5b), in ONE place.
# ─────────────────────────────────────────────────────────────────────────

#: Measured on Litolff Beethoven 5 p.1-4 (scan, margin labels present):
#: GATHER alone, with `OMR_DIRECTION_TEXT_SCAN_GATE=1` skipping the
#: direction-word reader on a page already proved a scan. UNCHANGED by the
#: 2026-09-28 recalibration below: roadmap 1.2's fixes targeted
#: ADJUDICATE/EVALUATE/INFER, not GATHER, and this figure is independently
#: consistent with the 09-22 Litolff data point's own GATHER half (~25 min
#: / 16 pages ≈ 93.75 s/page).
GATHER_S_PER_PAGE_WITH_DIRECTION_GATE = 93.0

#: The same GATHER stage if the gate never fires and the direction-word
#: reader runs on every page too (measured, see `DIRECTION_READER_S_PER_PAGE`) — the
#: conservative upper bound `gather_movement.sh` has always printed
#: alongside the expected figure.
#: The direction-word reader's cost on a scan, MEASURED 2026-10-08 on the 10
#: held-out pages with the width-scaled token cap, tight crops and the fast-rung
#: gate (`benchmarks/omr-direction-text-2026-09/FINDINGS.md`): mean 17.5 s per
#: page, 3.5-28 s, rounded up. It was 267 s before those; the reader now runs on
#: scans (no script sets `OMR_DIRECTION_TEXT_SCAN_GATE`), so this is the
#: EXPECTED figure and `direction_text_scan_gate` defaults to False.
DIRECTION_READER_S_PER_PAGE = 18.0
GATHER_S_PER_PAGE_WITHOUT_DIRECTION_GATE = 93.0 + DIRECTION_READER_S_PER_PAGE

# ─────────────────────────────────────────────────────────────────────────
# post-GATHER (ADJUDICATE/EVALUATE/INFER/write): the 2026-09-28 recalibration.
# Superseded data point kept for the record, never deleted (CLAUDE.md rule
# 9's own "findings kept" habit applied to a docstring rather than a
# FINDINGS.md, since this module has no benchmark directory of its own):
#   `_LITOLFF_09_22_RUN_PAGES = 16`, GATHER ~25 min, post-GATHER ~12.3 h,
#   single core — PRE-1.2, superseded by the pages listed below.
# ─────────────────────────────────────────────────────────────────────────

#: 2026-09-28, commit `c19cbca7`, clean tree (ROADMAP.md START HERE item 0;
#: driver `.claude/worktrees/regather-20260928-driver.log`).
_LITOLFF_20260928_PAGES = 16
_LITOLFF_20260928_WALL_S = 1941.0  # 06:36:32Z -> 07:08:53Z, 32 m 21 s

_BRAHMS_20260928_PAGES = 27
_BRAHMS_20260928_WALL_S = 8970.0  # 04:07:02Z -> 06:36:32Z, 2 h 29 m 30 s
#: ⚠️ measured under heavy contention from other sessions that night; the
#: same 27 pages alone measured 1 h 11 m on 2026-09-23 (commit `275641c0`,
#: ROADMAP.md 1.1) -- this run's per-page figure is a padded upper bound
#: even before the "take the slower document" step below pads it again.


def _post_gather_s_per_page(total_wall_s: float, n_pages: int) -> float:
    """Every second of `total_wall_s` NOT attributed to GATHER, per page.

    A COMPUTATION (module docstring): neither log carries a timestamp that
    would let GATHER be measured separately from ADJUDICATE/EVALUATE/INFER/
    write, so this assumes the independently-measured GATHER rate
    (`GATHER_S_PER_PAGE_WITH_DIRECTION_GATE` — both 2026-09-28 runs set
    `OMR_DIRECTION_TEXT_SCAN_GATE=1`, confirmed in each record's own
    provenance) and charges everything else to post-GATHER. Where GATHER
    actually ran faster than that this run, the excess is folded into
    post-GATHER too — the safe direction for an upper bound.
    """
    return (total_wall_s / n_pages) - GATHER_S_PER_PAGE_WITH_DIRECTION_GATE


_LITOLFF_20260928_POST_GATHER_S_PER_PAGE = _post_gather_s_per_page(
    _LITOLFF_20260928_WALL_S, _LITOLFF_20260928_PAGES)
_BRAHMS_20260928_POST_GATHER_S_PER_PAGE = _post_gather_s_per_page(
    _BRAHMS_20260928_WALL_S, _BRAHMS_20260928_PAGES)

#: ROADMAP item 0 / 1.2b's own instruction: "take the slower document per
#: page." Brahms wins (≈239 s/page vs Litolff's ≈28 s/page) — expected,
#: since 1.2's own finding was that the pre-fix cost scaled with system/
#: glyph density, not page count alone, and Brahms is the denser plate.
POST_GATHER_S_PER_PAGE_UPPER_BOUND = max(
    _LITOLFF_20260928_POST_GATHER_S_PER_PAGE,
    _BRAHMS_20260928_POST_GATHER_S_PER_PAGE)


#: Printed beside every estimate this module produces — never left implicit,
#: because a bound read without this sentence is mistaken for a measurement.
#: See the module docstring's three compounding reasons.
POST_GATHER_UPPER_BOUND_CAVEAT = (
    "the post-GATHER figure is a computation (total document wall time minus "
    "the independently-measured GATHER rate -- neither 2026-09-28 log carries "
    "a timestamp that would let the two be measured separately), taken as the "
    "SLOWER of two documents (Brahms, itself measured under heavy machine "
    "contention that night) -- not a measurement of any one job's real cost. "
    "See tools/omr/staged/budget.py's module docstring for the full chain")


def estimate_job_budget_s(n_pages: int, *,
                          direction_text_scan_gate: bool = False
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
            "2026-09-28 whole-movement re-gather, commit c19cbca7: "
            f"litolff {_LITOLFF_20260928_PAGES} pages/{_LITOLFF_20260928_WALL_S:.0f}s, "
            f"brahms {_BRAHMS_20260928_PAGES} pages/{_BRAHMS_20260928_WALL_S:.0f}s "
            "(brahms ran under heavy machine contention); post-GATHER upper "
            f"bound {POST_GATHER_S_PER_PAGE_UPPER_BOUND:.1f} s/page is the "
            "slower of the two, GATHER-share subtracted"),
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
