"""ONE GATHER, `slot_index` DECIDED FOUR WAYS — base vs arm on ONE TREE.

⚠️⚠️ BASE-VS-ARM, NEVER RECORD-VS-ARM. CLAUDE.md records that a
`readjudicate`-style control against the committed verdicts of
`library/_shared-records/` now FAILS on today's tree -- 2,760 of 2,993
durations -- because seven commits have touched `rhythm.py` since those
records were gathered. A shared record is a snapshot of the reader that made
it. So every figure here is one tree decided four ways, and the only thing
compared against the committed record is `slot_index` itself, which no commit
since has touched until this one.

    CONTROL   both branches disabled -- must reproduce the committed
              `slot_index` verdicts EXACTLY, or nothing below means anything.
    BASE      the shipped ADJUDICATE: `_place_in_family_block` only.
    ARM       + the three channels as constraints (`OMR_SLOT_CONSTRAINTS`).
    each + INFER, because `collapse_slot_index_to_family_block` is default ON
              and is what finishes the shipped path's narrowings.

⚠️ THE HELPERS ARE IMPORTED FROM THE ARM THAT MEASURED THE FAMILY BLOCK, not
restated: same truth file, same spelling bridge, same `classify`. Two copies
of a scoring rule is how one of them drifts.
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

import block_arm                                                  # noqa: E402
import reinfer                                                    # noqa: E402
from tools.omr.staged import adjudicate, evaluate, infer           # noqa: E402
from tools.omr.staged import adjudicators, inferences              # noqa: E402,F401
from tools.omr.staged.adjudicators import identity                 # noqa: E402
from tools.omr.staged.record import Q                              # noqa: E402


class Branches:
    """Turn either branch off IN PROCESS, so one interpreter runs every arm.

    ⚠️ The constraints branch is disabled through `slot_constraints_enabled`
    rather than through `os.environ`, because the flag is read inside the
    decision and an env change mid-process is exactly the kind of state a
    later arm inherits silently.
    """

    def __init__(self, block: bool, constraints: bool):
        self.block, self.constraints = block, constraints

    def __enter__(self):
        self._block = identity._place_in_family_block
        self._flag = identity.slot_constraints_enabled
        if not self.block:
            identity._place_in_family_block = lambda *a, **k: None
        if not self.constraints:
            identity.slot_constraints_enabled = lambda: False
        return self

    def __exit__(self, *exc):
        identity._place_in_family_block = self._block
        identity.slot_constraints_enabled = self._flag
        return False


def decide(rec, *, block: bool, constraints: bool, run_infer: bool):
    log = reinfer.rebuild(rec, skip_verdicts=frozenset({Q.SLOT_INDEX}))
    with Branches(block, constraints):
        adjudicate.run(log, order=(Q.SLOT_INDEX,))
        if run_infer:
            infer.run(log, evaluate.Report(fired=[], skipped=[], stubs=[]))
    return log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--truth", default=None)
    ap.add_argument("--json", default=str(HERE / "out" / "slot-arm.json"))
    a = ap.parse_args()

    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc
    print("record provenance:", doc.get("provenance"))
    lineups = block_arm.printed_lineups(a.truth)
    if lineups is None:
        print("⚠️ NO --truth: REACH only, and not one placement is classified.",
              file=sys.stderr)

    committed = {v["subject"]: v for v in rec["verdicts"]
                 if v["quantity"] == Q.SLOT_INDEX}
    print("committed slot_index verdicts: %d %s"
          % (len(committed),
             dict(collections.Counter(v["outcome"] for v in committed.values()))))

    # ── CONTROL ─────────────────────────────────────────────────────────────
    control = decide(rec, block=False, constraints=False, run_infer=False)
    got = {v["subject"]: v for v in control.to_json()["verdicts"]
           if v["quantity"] == Q.SLOT_INDEX}
    same = sum(1 for k, w in committed.items()
               if k in got and got[k]["outcome"] == w["outcome"]
               and got[k].get("value") == w.get("value")
               and got[k]["reason"] == w["reason"])
    print("CONTROL (both branches off): %d of %d reproduced exactly"
          % (same, len(committed)))
    if same != len(committed) or len(got) != len(committed):
        print("⚠️ THE REBUILD IS NOT THE RECORD — every number below would be "
              "a measurement of the harness.", file=sys.stderr)
        return 2

    ref_names = block_arm.reference_names(control)
    print("reference lineup:", ref_names)

    arms = {}
    for name, block, constraints, run_infer in (
            ("base", True, False, False),
            ("base+infer", True, False, True),
            ("arm", True, True, False),
            ("arm+infer", True, True, True)):
        log = decide(rec, block=block, constraints=constraints,
                     run_infer=run_infer)
        rows = block_arm.slot_rows(log, lineups, ref_names)
        arms[name] = rows
        t = block_arm.tally(rows)
        print()
        print("── %s" % name)
        for k in sorted(t, key=lambda x: (-t[x], str(x))):
            print("   %-46s %d" % ("/".join(str(p) for p in k), t[k]))
        graft = sum(n for k, n in t.items() if k[0] == "decided"
                    and k[1] == "graft")
        print("   ** GRAFTS %d **" % graft)

    # ⚠️ THE ZERO THAT MATTERS: no staff the base DECIDED may come out
    # differently under the arm. The branch is additive by construction and
    # this is the assertion of it, per staff rather than in aggregate.
    base = {r["subject"]: r for r in arms["base+infer"]}
    moved, gained = [], []
    for r in arms["arm+infer"]:
        b = base.get(r["subject"])
        if b is None:
            continue
        if b["outcome"] == "decided" and (r["outcome"] != "decided"
                                          or r["slot"] != b["slot"]):
            moved.append({"subject": r["subject"], "was": b["slot"],
                          "now": r["slot"], "outcome": r["outcome"]})
        if b["outcome"] != "decided" and r["outcome"] == "decided":
            gained.append({"subject": r["subject"], "slot": r["slot"],
                           "reason": r["reason"], "class": r["class"]})
    print()
    print("A DECIDED STAFF THAT MOVED: %d   (must be 0)" % len(moved))
    for m in moved:
        print("   ", m)
    print("STAVES THE ARM DECIDES THAT THE BASE DID NOT: %d" % len(gained))
    print("   by reason:",
          dict(collections.Counter(g["reason"] for g in gained)))
    print("   by class :",
          dict(collections.Counter(str(g["class"]) for g in gained)))

    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(
        {"record": a.record, "truth": a.truth,
         "provenance": doc.get("provenance"),
         "control_reproduced": same, "reference": ref_names,
         "tallies": {k: {"/".join(str(p) for p in kk): vv
                         for kk, vv in block_arm.tally(v).items()}
                     for k, v in arms.items()},
         "decided_staff_that_moved": moved,
         "gained": gained,
         "rows": arms["arm+infer"]}, indent=1))
    print()
    print("wrote", a.json)
    return 0 if not moved else 1


if __name__ == "__main__":
    raise SystemExit(main())
