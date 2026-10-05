#!/usr/bin/env python3
"""lane-ledger-r8 (2026-10-01): score causes C and D of DECISIONS
2026-10-01's "four causes behind the 8 far heads neither reader gets
right" against `score_truth_set_rungs.py`'s own real-data truth set.

Three rows per doc:
  * `geometry`         -- UNCHANGED control (`score_truth_set_rungs`'s own).
  * `rungs_before`      -- `score_doc(doc_id)` (the as-shipped reader,
    `four_causes_cd=False` -- cause D's distance guess is already retired
    at the `derive_far_head_step` primitive level, so this is "no
    evidence wired in" rather than the literal pre-10-01 heuristic; see
    FINDINGS for the baseline numbers that heuristic produced).
  * `rungs_after`       -- `score_doc(doc_id, four_causes_cd=True)`:
    accidental-ink exclusion + edge-rung collapse (cause C) and the
    image-evidenced line-vs-space decision (cause D) both wired in.

Also reports, by name, the 8 Litolff heads from the neither-right sheet
(`out/print/ledgers/neither_right_sheet.png`) that gated this lane, and
any head that was right before and is wrong after (a regression this
lane must not have).

MEASUREMENT ONLY -- writes nothing back into the pipeline.

    python3 benchmarks/omr-local-staff-2026-09/score_four_causes_cd.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import score_truth_set_rungs as score  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402

# The 8 Litolff heads neither geometry nor rungs got right (DECISIONS
# 2026-10-01, "four causes"), tiles 1-8 of the neither-right sheet in
# that order.
NEITHER_RIGHT_8 = [
    "glyph/1/0/10/7/1",
    "glyph/3/0/0/2/1",
    "glyph/3/0/0/6/2",
    "glyph/3/0/0/7/1",
    "glyph/3/0/0/7/2",
    "glyph/3/0/8/9/0",
    "glyph/3/0/9/2/0",
    "glyph/3/0/9/3/5",
]


def _by_subject(per_head) -> Dict[str, Dict[str, Any]]:
    return {h["subject"]: h for h in per_head}


def main() -> int:
    overall_ok = True
    for doc_id in ts.DOCS:
        print(f"=== {doc_id} ===")
        before = score.score_doc(doc_id, four_causes_cd=False)
        after = score.score_doc(doc_id, four_causes_cd=True)

        tb, ta = before["tally"], after["tally"]
        n = sum(tb.get("geometry", {}).values())
        g = tb.get("geometry", {})
        print(f"  geometry        right={g.get('right',0):>3} wrong={g.get('wrong',0):>3} "
             f"abstain={g.get('abstain',0):>3}  (n={n})")
        rb = tb.get("rungs_after", {})
        print(f"  rungs_before    right={rb.get('right',0):>3} wrong={rb.get('wrong',0):>3} "
             f"abstain={rb.get('abstain',0):>3}  (n={n})")
        ra = ta.get("rungs_after", {})
        print(f"  rungs_after     right={ra.get('right',0):>3} wrong={ra.get('wrong',0):>3} "
             f"abstain={ra.get('abstain',0):>3}  (n={n})")

        before_by = _by_subject(before["per_head"])
        after_by = _by_subject(after["per_head"])

        regressions = [
            sub for sub, hb in before_by.items()
            if hb["v_after"] == "right"
            and after_by.get(sub, {}).get("v_after") != "right"
        ]
        print(f"  regressions (right before, not right after): {len(regressions)} {regressions}")
        if regressions:
            overall_ok = False

        if doc_id == "beethoven5-litolff":
            print("  neither-right-8, before -> after:")
            for sub in NEITHER_RIGHT_8:
                hb, ha = before_by.get(sub), after_by.get(sub)
                vb = hb["v_after"] if hb else "not-in-population"
                va = ha["v_after"] if ha else "not-in-population"
                flip = " <-- FLIPPED" if hb and ha and vb != va else ""
                print(f"    {sub:<20} before={vb:<10} after={va:<10}{flip}")
        print()

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
