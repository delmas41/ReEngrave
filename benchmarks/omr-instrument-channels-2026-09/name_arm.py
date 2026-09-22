"""WHAT IS THE PART ACTUALLY CALLED? -- the question the file answers.

⚠️⚠️ THE SLOT IS NOT THE NAME, AND THIS ARM EXISTS BECAUSE THE TWO ARE
ROUTINELY CONFLATED. `export.to_musicxml` takes a part's `<part-name>` from
the FIRST staff of that part carrying one (`export.py:2897`), and a staff's
name is `Q.PART_NAME`, written by `consequences.name_part` from
`Q.INSTRUMENT`. So a staff whose instrument ABSTAINED still lands in a named
part the moment its SLOT joins it to a staff that was named -- and a part
where no staff was ever named falls back to `_default_name`, the coordinate
`Staff p1-s0-3` Sean reads in the file.

This counts, per arm: how many parts the file would name, and how many fall
back to a coordinate.
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
from tools.omr.staged.adjudicators import identity                 # noqa: E402
from tools.omr.staged.record import Q, Subject                     # noqa: E402
from slot_arm import Branches                                      # noqa: E402


def parts(log):
    """`{slot or fragment key: [staff subjects]}` -- the exporter's own join."""
    named = {}
    for v in log.to_json()["verdicts"]:
        if v["quantity"] == Q.INSTRUMENT and isinstance(v.get("value"), dict):
            named[v["subject"]] = v["value"].get("name")
    slots = {}
    for v in log.to_json()["verdicts"]:
        if v["quantity"] != Q.SLOT_INDEX:
            continue
        cur = log.verdict(Q.SLOT_INDEX, Subject.from_key(v["subject"]))
        if cur is None or cur.id != v["id"] or v["outcome"] != "decided":
            continue
        slots.setdefault(int(v["value"]), []).append(v["subject"])
    return slots, named


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "name-arm.json"))
    a = ap.parse_args()
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc

    out = {}
    for label, block, constraints, run_infer in (
            ("control (both branches off)", False, False, False),
            ("base  (family block + INFER)", True, False, True),
            ("arm   (+ constraints)", True, True, True)):
        log = reinfer.rebuild(rec, skip_verdicts=frozenset({Q.SLOT_INDEX}))
        with Branches(block, constraints):
            adjudicate.run(log, order=(Q.SLOT_INDEX,))
            if run_infer:
                infer.run(log, evaluate.Report(fired=[], skipped=[], stubs=[]))
        slots, named = parts(log)
        rows = []
        for slot, subs in sorted(slots.items()):
            names = {named.get(s) for s in subs} - {None}
            rows.append({"slot": slot, "staves": len(subs),
                         "name": sorted(names)[0] if names else None,
                         "conflict": sorted(names) if len(names) > 1 else None})
        # ⚠️ THE CURRENT VERDICT, NEVER EVERY ROW. INFER SUPERSEDES a
        # narrowing rather than deleting it, so counting rows charges every
        # collapsed narrowing as an unplaced staff -- the first run of this
        # arm reported 20 where the truth is 5.
        seen, unplaced = set(), 0
        for v in log.to_json()["verdicts"]:
            if v["quantity"] != Q.SLOT_INDEX or v["subject"] in seen:
                continue
            cur = log.verdict(Q.SLOT_INDEX, Subject.from_key(v["subject"]))
            seen.add(v["subject"])
            if cur is None or cur.outcome.value != "decided":
                unplaced += 1
        out[label] = {"parts": len(rows),
                      "named": sum(1 for r in rows if r["name"]),
                      "unnamed": sum(1 for r in rows if not r["name"]),
                      "staves_with_no_slot": unplaced,
                      "rows": rows}
        print("── %s" % label)
        print("   parts joined by slot   %d" % len(rows))
        print("   of those, NAMED        %d" % out[label]["named"])
        print("   of those, a COORDINATE %d" % out[label]["unnamed"])
        print("   staves with NO slot at all (held out of the file) %d"
              % unplaced)
        for r in rows:
            if r["conflict"]:
                print("      ⚠️ slot %d names disagree: %s"
                      % (r["slot"], r["conflict"]))
        print()
    Path(a.json).write_text(json.dumps(out, indent=1))
    print("wrote", a.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
