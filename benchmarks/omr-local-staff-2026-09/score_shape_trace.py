#!/usr/bin/env python3
"""lane-ledger-shape (2026-10-02): re-score the real truth set with the
shape-trace evidence function (`tools/omr/annotate/ledger_shape_trace.
shape_trace_middle_rung_evidence`) substituted for round 8's own box-centre
probe (`ledger_grid.head_middle_rung_evidence`) inside `derive_far_head_
step`. MEASUREMENT ONLY -- the substitution is a monkeypatch local to this
script's own process, never a change to the shipped reader or its default;
nothing here writes back into the pipeline.

Three rows per doc, same shape as `score_four_causes_cd.py`:
  * geometry       -- unchanged control.
  * round8         -- `score_doc(doc_id, four_causes_cd=True)`, UNCHANGED
    (round 8's own box-centre evidence probe).
  * shape_trace    -- the SAME call, with the evidence probe swapped for
    the shape-trace one.

Also reports the two heads that gated this lane
(`glyph/3/0/7/0/7`, `glyph/3/0/7/2/4`) by name, and any regression (right
under round8, not right under shape_trace).

    python3 benchmarks/omr-local-staff-2026-09/score_shape_trace.py
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
from tools.omr.annotate import ledger_grid as lg  # noqa: E402
from tools.omr.annotate import ledger_shape_trace as shtr  # noqa: E402

# The two heads that abstain under round 8 with `no_rung_before_the_head`
# (DECISIONS 2026-10-02 -- "trace the shape around far heads") even though
# geometry and the ledger-measured reader both already land on the
# reference position.
UNDECIDED_TWO = ["glyph/3/0/7/0/7", "glyph/3/0/7/2/4"]


def _by_subject(per_head) -> Dict[str, Dict[str, Any]]:
    return {h["subject"]: h for h in per_head}


def main() -> int:
    overall_ok = True
    for doc_id in ts.DOCS:
        print(f"=== {doc_id} ===")
        round8 = score.score_doc(doc_id, four_causes_cd=True)

        original = lg.head_middle_rung_evidence
        lg.head_middle_rung_evidence = shtr.shape_trace_middle_rung_evidence
        try:
            shape_trace = score.score_doc(doc_id, four_causes_cd=True)
        finally:
            lg.head_middle_rung_evidence = original

        tb, ta = round8["tally"], shape_trace["tally"]
        n = sum(tb.get("geometry", {}).values())
        g = tb.get("geometry", {})
        print(f"  geometry     right={g.get('right',0):>3} wrong={g.get('wrong',0):>3} "
              f"abstain={g.get('abstain',0):>3}  (n={n})")
        r8 = tb.get("rungs_after", {})
        print(f"  round8       right={r8.get('right',0):>3} wrong={r8.get('wrong',0):>3} "
              f"abstain={r8.get('abstain',0):>3}  (n={n})")
        stv = ta.get("rungs_after", {})
        print(f"  shape_trace  right={stv.get('right',0):>3} wrong={stv.get('wrong',0):>3} "
              f"abstain={stv.get('abstain',0):>3}  (n={n})")

        before_by = _by_subject(round8["per_head"])
        after_by = _by_subject(shape_trace["per_head"])

        regressions = [
            sub for sub, hb in before_by.items()
            if hb["v_after"] == "right"
            and after_by.get(sub, {}).get("v_after") != "right"
        ]
        print(f"  regressions (right under round8, not right under shape_trace): "
              f"{len(regressions)} {regressions}")
        if regressions:
            overall_ok = False

        flips = [
            sub for sub, hb in before_by.items()
            if hb["v_after"] != after_by.get(sub, {}).get("v_after")
        ]
        print(f"  all flips (round8 -> shape_trace): {len(flips)}")
        for sub in flips:
            hb, ha = before_by.get(sub), after_by.get(sub)
            print(f"    {sub:<20} round8={hb['v_after']:<10} "
                  f"shape_trace={ha['v_after']:<10} reason={ha['reason']}")

        if doc_id == "beethoven5-litolff":
            print("  the two undecided heads, round8 -> shape_trace:")
            for sub in UNDECIDED_TWO:
                hb, ha = before_by.get(sub), after_by.get(sub)
                vb = hb["v_after"] if hb else "not-in-population"
                va = ha["v_after"] if ha else "not-in-population"
                rb = hb["reason"] if hb else ""
                ra = ha["reason"] if ha else ""
                flip = " <-- FLIPPED" if hb and ha and vb != va else ""
                print(f"    {sub:<20} round8={vb:<10} shape_trace={va:<10}{flip}")
                print(f"      round8 reason:      {rb}")
                print(f"      shape_trace reason: {ra}")
        print()

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
