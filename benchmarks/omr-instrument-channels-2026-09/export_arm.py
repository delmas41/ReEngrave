"""THE 2.1 GATE — `staff_not_identified` on Litolff, base vs arm.

The manager session's acceptance criterion for roadmap item 2.1 is
`staff_not_identified` **783 -> under 100 on Litolff with ZERO grafts against
the print**, and it is explicitly not a reach count. This measures exactly
that, on one gather exported twice.

⚠️ `OMR_HOLD_OUT_UNIDENTIFIED` (default ON, Sean's *"hold out -- I want
truth"*) drops a staff the join could not place and counts its music under
`staff_not_identified`. The gate it reads is `Q.SLOT_INDEX`, so this number
moves when a staff gains a SLOT -- not when it gains a name.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-infer-stage-2026-09"))
sys.path.insert(0, str(ROOT / "benchmarks/omr-unnamed-block-slot-2026-09"))

import reinfer                                                    # noqa: E402
from tools.omr.staged import adjudicate, evaluate, infer           # noqa: E402
from tools.omr.staged import adjudicators, inferences              # noqa: E402,F401
from tools.omr.staged import export as EX                          # noqa: E402
from tools.omr.staged.record import Q                              # noqa: E402
from slot_arm import Branches                                      # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "export-arm.json"))
    a = ap.parse_args()
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc
    print("record provenance:", doc.get("provenance"))

    out = {}
    for label, block, constraints in (
            ("control (both branches off)", False, False),
            ("base  (family block, shipped)", True, False),
            ("arm   (+ constraints)", True, True)):
        log = reinfer.rebuild(rec, skip_verdicts=frozenset({Q.SLOT_INDEX}))
        with Branches(block, constraints):
            adjudicate.run(log, order=(Q.SLOT_INDEX,))
            infer.run(log, evaluate.Report(fired=[], skipped=[], stubs=[]))
        result = {"record": log.to_json(), "source": {}}
        xml, report = EX.to_musicxml(result)
        drops = report.get("notes_not_written") or {}
        row = {"staff_not_identified": int(drops.get("staff_not_identified", 0)),
               "events_written": int((report.get("balance") or {}).get(
                   "events_written", 0)),
               "notes_not_written_total": int(
                   report.get("notes_not_written_total", 0)),
               "parts": xml.count("<score-part "),
               "part_names_that_are_a_coordinate": xml.count("<part-name>Staff p"),
               "balanced": bool((report.get("balance") or {}).get("balanced")),
               "drops": {k: v for k, v in sorted(drops.items())}}
        out[label] = row
        print()
        print("── %s" % label)
        for k in ("staff_not_identified", "events_written",
                  "notes_not_written_total", "parts",
                  "part_names_that_are_a_coordinate", "balanced"):
            print("   %-34s %s" % (k, row[k]))
    Path(a.json).write_text(json.dumps(out, indent=1))
    print()
    print("wrote", a.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
