"""THE FLIP — does turning `OMR_SLOT_FAMILY_BLOCK` on change what a DEFAULT
run does, and does it change anything else?

⚠️⚠️ THIS IS NOT `block_arm.py` AND MUST NOT BE READ AS A RE-RUN OF IT. That
arm measures THE RULE against the print (25 of 25, 0 grafts) and its control
is *the committed record's own verdicts, reproduced*. That control **fails on
today's tree, 12 of 75**, and correctly: `adjudicate_slot_index` gained its
short-system pairing rule AFTER the shared record was gathered, so the record
is a snapshot of an older reader. CLAUDE.md records exactly this on
2026-09-21 -- *"the shared records can no longer license a rebuild ... any
future A/B must be base-vs-arm on ONE tree"* -- and widening that arm's
control until it passed would be this repository's own
*a control that computes the wrong thing*, applied on purpose.

So this arm asks the SMALLER question the flip actually raises, on ONE tree:

    BASE   `OMR_SLOT_FAMILY_BLOCK=0` -- the state before tonight.
    ARM    the shipped default -- nothing set.

Both from the SAME rebuild and the same ADJUDICATE pass, so the only
difference between them is the switch. What the rule is WORTH is already
measured and is not re-derived here; what was never measured is that the
DEFAULT reaches it, and that it reaches nothing else.

⚠️ WHAT IT IS BLIND TO: a GATHER change (it rebuilds from a saved record),
and the EXPORT (it stops at the verdicts). It says which verdicts move, not
what the file then looks like.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-infer-stage-2026-09"))

import reinfer                                                    # noqa: E402
from tools.omr.staged import adjudicate, evaluate, infer          # noqa: E402
from tools.omr.staged import adjudicators, inferences             # noqa: E402,F401
from tools.omr.staged.record import Q                             # noqa: E402


def _slots(log):
    return {v["subject"]: (v["outcome"], v.get("value"), v["reason"],
                           v.get("decider"))
            for v in log.to_json()["verdicts"]
            if v["quantity"] == Q.SLOT_INDEX}


def _all_verdicts(log):
    return {(v["quantity"], v["subject"]): (v["outcome"], v.get("value"))
            for v in log.to_json()["verdicts"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "flip-arm.json"))
    a = ap.parse_args()

    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc
    print(f"record provenance: {doc.get('provenance')}")

    # ── REACH FIRST. A flip that reaches nothing and a flip that changes
    #    nothing are the same number, and this repository has burned a
    #    session on that exact zero. ───────────────────────────────────────
    log = reinfer.rebuild(rec, skip_verdicts=frozenset({Q.SLOT_INDEX}))
    adjudicate.run(log, order=(Q.SLOT_INDEX,))
    before = _slots(log)
    reach = collections.Counter(o for o, _, _, _ in before.values())
    narrowed = [k for k, v in before.items() if v[0] == "narrowed"]
    print(f"\nafter ADJUDICATE (today's tree): {len(before)} slot verdicts "
          f"{dict(reach)}")
    print(f"REACH -- narrowed verdicts the rule may speak into: "
          f"{len(narrowed)}")
    if not narrowed:
        print("⚠️ DEAD: nothing narrowed, so this arm cannot tell a working "
              "flip from a broken one.", file=sys.stderr)
        return 2

    every_before = _all_verdicts(log)

    # ── BASE: the switch explicitly off ────────────────────────────────────
    base_log = reinfer.rebuild(rec, skip_verdicts=frozenset({Q.SLOT_INDEX}))
    adjudicate.run(base_log, order=(Q.SLOT_INDEX,))
    os.environ["OMR_SLOT_FAMILY_BLOCK"] = "0"
    base_rep = infer.run(base_log, evaluate.Report([], [], []))
    base = _slots(base_log)
    print(f"\nBASE  (OMR_SLOT_FAMILY_BLOCK=0): inferred={len(base_rep.inferred)} "
          f"disabled={base_rep.disabled}")

    # ── ARM: the shipped default ─────────────────────────────────────────
    arm_log = reinfer.rebuild(rec, skip_verdicts=frozenset({Q.SLOT_INDEX}))
    adjudicate.run(arm_log, order=(Q.SLOT_INDEX,))
    os.environ.pop("OMR_SLOT_FAMILY_BLOCK", None)
    os.environ.pop("OMR_INFER", None)
    arm_rep = infer.run(arm_log, evaluate.Report([], [], []))
    arm = _slots(arm_log)
    print(f"ARM   (shipped default):        inferred={len(arm_rep.inferred)} "
          f"disabled={arm_rep.disabled}")

    # ── THE DELTA ────────────────────────────────────────────────────────
    moved = {k for k in set(base) | set(arm) if base.get(k) != arm.get(k)}
    print(f"\nslot_index verdicts that MOVE: {len(moved)}")
    print(f"  base outcomes: {dict(collections.Counter(o for o,_,_,_ in base.values()))}")
    print(f"  arm  outcomes: {dict(collections.Counter(o for o,_,_,_ in arm.values()))}")

    deciders = collections.Counter(arm[k][3] for k in moved if k in arm)
    print(f"  every moved verdict's decider: {dict(deciders)}")

    # ⚠️ THE CONTROL THAT MATTERS FOR A FLIP: nothing OUTSIDE the target
    #    quantity may move. A stage that runs by default and quietly touches
    #    a duration is the thing this whole two-flag split exists to prevent.
    every_arm = _all_verdicts(arm_log)
    off_target = [k for k in set(every_before) | set(every_arm)
                  if k[0] != Q.SLOT_INDEX
                  and every_before.get(k) != every_arm.get(k)]
    print(f"\nCONTROL -- verdicts outside slot_index that moved: "
          f"{len(off_target)}")
    if off_target:
        print("⚠️ THE DEFAULT STAGE TOUCHED SOMETHING IT MAY NOT:",
              off_target[:10], file=sys.stderr)

    out = {
        "record": a.record,
        "provenance": doc.get("provenance"),
        "reach_narrowed": len(narrowed),
        "base": {"inferred": len(base_rep.inferred),
                 "disabled": [list(d) for d in base_rep.disabled],
                 "outcomes": dict(collections.Counter(
                     o for o, _, _, _ in base.values()))},
        "arm": {"inferred": len(arm_rep.inferred),
                "disabled": [list(d) for d in arm_rep.disabled],
                "outcomes": dict(collections.Counter(
                    o for o, _, _, _ in arm.values()))},
        "moved": len(moved),
        "deciders_of_moved": dict(deciders),
        "off_target_moves": len(off_target),
    }
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(out, indent=2))
    print(f"\nwrote {a.json}")
    return 1 if off_target else 0


if __name__ == "__main__":
    raise SystemExit(main())
