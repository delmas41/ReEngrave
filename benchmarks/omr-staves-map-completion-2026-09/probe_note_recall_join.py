"""Does giving Mahler a `staves` map break `scan_eval.note_recall`?

That is the objection works.json records, and it is a REAL one — `note_recall`
joins `staves[i]` to `pred.parts[i]` by ordinal, and Mahler's map has entries
the prediction structurally cannot contain.

But the map itself carries the repair. A one-line percussion staff is exactly
the entry with no predicted part, and it is exactly the entry works.json's own
Mahler idiom already marks `"lines": 1`. So the question is arithmetic: does
`len([e for e in staves if e.lines != 1])` equal the prediction's part count?

Measured here on the canonical run's own exports, per row.
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
sys.path.insert(0, str(HERE))

import candidate_maps                                     # noqa: E402

REC = (MAIN / ".claude/worktrees/reconciliation/benchmarks"
       "/omr-scan-e2e-2026-09/fixtures")


def main() -> int:
    rows = []
    for rid, spec in candidate_maps.CANDIDATES.items():
        pred = REC / f"{rid}.reconciliation.omr.musicxml"
        root = ET.parse(pred).getroot()
        n_pred = len(root.findall(".//part-list/score-part"))
        n_all = len(spec)
        n_five = len([s for s in spec if s.get("lines", 5) != 1])
        rows.append({
            "row_id": rid,
            "map_entries": n_all,
            "map_entries_five_line": n_five,
            "map_entries_one_line": n_all - n_five,
            "predicted_parts": n_pred,
            "ordinal_join_over_all_entries_valid": n_all == n_pred,
            "ordinal_join_over_five_line_entries_valid": n_five == n_pred,
        })
        print(json.dumps(rows[-1]))
    (HERE / "note-recall-join.json").write_text(
        json.dumps({"rows": rows}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
