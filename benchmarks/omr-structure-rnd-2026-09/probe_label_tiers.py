"""What the label ladder actually produced per staff, on the mis-joined page.

MEASUREMENT ONLY. Reads committed transcriptions from the reconciliation
worktree's 20-row fixture set; writes nothing.

`contextual` records its own label diagnostics in the result — `label_tiers`,
`labelled_staves`, `low_confidence_labels`, `unresolved_labels`,
`ambiguous_labels_resolved`. Those are what `slots.align` was fed, so they
answer the question the post-hoc `staff["instrument"]` field cannot: did the
aligner ever SEE a label conflict between the two systems of Beethoven 5 p.4?
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

FIXTURES = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation"
    "/benchmarks/omr-scan-e2e-2026-09/fixtures"
)
SUFFIX = ".reconciliation.omr.json"

FIELDS = ("label_tiers", "labelled_staves", "low_confidence_labels",
          "unresolved_labels", "ambiguous_labels_resolved",
          "layout_named_slots", "instruments_from_score_order", "layout")


def main() -> int:
    paths = sorted(FIXTURES.glob(f"*{SUFFIX}"))
    assert paths, f"EMPTY INPUT — no fixtures under {FIXTURES}"
    rows = sys.argv[1:] or ["beethoven-sym5-mvt1-984073-p4",
                            "beethoven-sym5-mvt1-575951-p4"]
    seen = 0
    for row in rows:
        path = FIXTURES / f"{row}{SUFFIX}"
        assert path.exists(), f"MISSING {path}"
        ctx = json.loads(path.read_text()).get("contextual") or {}
        assert ctx, f"no contextual block on {row}"
        seen += 1
        print(f"\n================ {row} ================")
        for field in FIELDS:
            print(f"\n-- {field} --")
            print(json.dumps(ctx.get(field), indent=2, ensure_ascii=False)[:2600])
    assert seen, "EMPTY INPUT — no rows inspected"
    print(f"\nrows inspected: {seen}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
