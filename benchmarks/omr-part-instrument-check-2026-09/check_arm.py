"""`part_partition`'s SECOND DECLARED CHECK, performed — and what it says.

The decorator has declared *"each part carries ONE instrument across every
system it appears on"* since the decision was written.
`benchmarks/omr-convention-coverage-2026-09/` counted **16 of 32 declared
checks not actually performed** and named this one first, on the ground that
the damage it describes is already on the record: the Phase 2 part-join
measurement found **12 of 75 staff-systems filed under a part carrying a
different instrument**, a Timpani part holding the Viola's staff.

⚠️ THIS IS AN ADJUDICATE CHANGE, so `readjudicate`'s isolation is the RIGHT
instrument and not a blind one: the check reads `Q.INSTRUMENT` **verdicts**,
which a saved record carries. It would be blind to a GATHER change and this
is not one — no row, field or frame moves.

⚠️ THE CONTROL COMES FIRST AND IT IS NOT A FORMALITY. The check must change
NOTHING: same join, same reason, same value, on every document. A rebuild
that moves the join is measuring the harness, and an arm that reports a
contested part while having silently re-decided the partition is worse than
no arm. `--control` exits non-zero on any difference.

⚠️ REACH BEFORE ACCURACY. A document where no instrument was read can produce
a clean `contested: 0` that means *nobody looked*, which is this record's own
ABSENT/DECLINED distinction and the exact failure mode of the page this check
was written for — before `run_staged` forwarded `pdf_path`,
`adjudicate_instrument` abstained on 75 of 75 staves on every staged run this
repo had made. The arm prints reach first and **exits 2 declaring itself
DEAD** where nothing was named.

    python3 check_arm.py <record.json> --control
    python3 check_arm.py <record.json> --tag litolff-beethoven5-p1-p4
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate                          # noqa: E402
from tools.omr.staged import adjudicators                        # noqa: E402,F401
from tools.omr.staged.record import Log, Subject                 # noqa: E402

HERE = Path(__file__).resolve().parent


def rebuild(rec: dict) -> Log:
    """One Log holding exactly the saved record's GATHER rows, in order.

    Lifted unchanged from `omr-staged-duration-beams-2026-09/readjudicate.py`
    rather than re-derived: two spellings of the rebuild is two things that
    can disagree about what a record IS.
    """
    log = Log()
    rows = [(r, "obs") for r in rec["observations"]]
    rows += [(r, "abs") for r in rec.get("abstentions", [])]
    rows.sort(key=lambda t: t[0]["id"])
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                        frame=r["frame"], score=r.get("score"), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"],
                        frame=r["frame"], reason=r["reason"], **detail)
    return log


def _partition(verdicts) -> dict | None:
    for v in verdicts:
        if v["quantity"] == "part_partition":
            return v
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--control", action="store_true",
                    help="assert the check moved NOTHING about the join")
    ap.add_argument("--tag", default=None)
    a = ap.parse_args()

    rec = json.load(open(a.record))["record"]
    log = rebuild(rec)
    adjudicate.run(log)
    got = _partition(log.to_json()["verdicts"])
    want = _partition(rec["verdicts"])

    if got is None:
        print("DEAD: the rebuild produced no part_partition verdict at all")
        return 2

    # ── CONTROL ─────────────────────────────────────────────────────────────
    if a.control:
        if want is None:
            print("DEAD: the record carries no part_partition to compare to")
            return 2
        moved = []
        if got["outcome"] != want["outcome"]:
            moved.append(f"outcome {want['outcome']} -> {got['outcome']}")
        if got["reason"] != want["reason"]:
            moved.append(f"reason {want['reason']} -> {got['reason']}")
        if got.get("value") != want.get("value"):
            moved.append(f"value {want.get('value')} -> {got.get('value')}")
        print(f"CONTROL: join {want.get('value')} reason={want['reason']}")
        if moved:
            print("  ⚠️ THE CHECK MOVED THE JOIN — every number below is void:")
            for m in moved:
                print("   ", m)
            return 1
        print("  the join is UNMOVED: same outcome, reason and value.")
        # POSITIVE control: the detail the check writes must actually be there,
        # or "nothing moved" is also what a check that never ran looks like.
        if "instrument_consistency" not in (got.get("detail") or {}):
            print("  ⚠️ and the check wrote NO detail — it did not run.")
            return 1
        print("  and the check DID run (detail present).")
        return 0

    # ── REACH, before anything is read ──────────────────────────────────────
    check = (got.get("detail") or {}).get("instrument_consistency") or {}
    print(f"RECORD  {Path(a.record).name}")
    print(f"JOIN    {got.get('value')}  reason={got['reason']}")
    if not check.get("checked"):
        print(f"DEAD: the check could not speak — {check.get('why_not')} "
              f"(staves named {check.get('staves_named', 0)})")
        return 2
    print(f"REACH   {check['staves_named']} staves carry a named instrument; "
          f"{check['parts_named']} parts; "
          f"{check['parts_with_two_or_more_named_staves']} of them are named "
          f"on two or more systems and are the only ones that CAN disagree; "
          f"{check['staves_unkeyed']} staves belong to no part under this join")
    print(f"RESULT  parts contested: {check['parts_contested']}")
    for part, names in check.get("contested", {}).items():
        print(f"          part {part}: {names}")

    if a.tag:
        out = HERE / "out" / f"{a.tag}.json"
        out.write_text(json.dumps(
            {"record": Path(a.record).name,
             "join": got.get("value"), "reason": got["reason"],
             "instrument_consistency": check}, indent=1, default=str))
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
