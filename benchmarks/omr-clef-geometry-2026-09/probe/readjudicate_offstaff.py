#!/usr/bin/env python3
"""ROADMAP 2.11b measurement — GATHER ONCE, ADJUDICATE TWICE, for the
off-staff clef discount.

    python3 .../readjudicate_offstaff.py <record.json> --off  --out base.json
    python3 .../readjudicate_offstaff.py <record.json>        --out arm.json

BASE = `clef._off_staff_discount_applies` monkeypatched to
`lambda row, on_staff: False` — 2.11b's rule DISABLED by an explicit
parameter, not a new env flag (CLAUDE.md rule 9). ARM = the unpatched tree's
own function. Same idiom `omr-key-majority-2026-09/readjudicate.py` used for
roadmap 2.9 (`H._marker_run = lambda ...`), reused rather than restated.

ADJUDICATE, then EVALUATE, then INFER, then the bounded second EVALUATE pass
over what INFER wrote — `pipeline.py`'s own shape, inherited from the
key-majority harness's own hard-won note (2.10's cross-system clef fill is
otherwise invisible to a re-adjudicate-only harness). GATHER is NOT re-run:
this is a Q.CLEF ADJUDICATE-only change (reads `Q.CLEF_GLYPH` /
`Q.CLEF_POSITION`, both already gathered), so re-adjudicating a saved record
is valid measurement, per CLAUDE.md §4d's own "three blind spots" note; this
cannot price a GATHER change and is not asked to.

⚠️ MEMORY: `rebuild()` reconstructs the WHOLE document's observations and
abstentions into one in-process `Log` — for the two 300-480 MB acceptance
records this is the same cost `omr-key-majority-2026-09` and
`omr-clef-geometry-2026-09`'s own 2.9c/2.11 measurements already paid on
this machine; there is no cheaper valid path (2.10's cross-system fill needs
every staff of the document, not just the one under test).

Usage:
    python3 benchmarks/omr-clef-geometry-2026-09/probe/readjudicate_offstaff.py \
        <record.json> --off --out /tmp/base.json
    python3 benchmarks/omr-clef-geometry-2026-09/probe/readjudicate_offstaff.py \
        <record.json>       --out /tmp/arm.json
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from tools.omr.staged import adjudicate, evaluate, infer            # noqa: E402
from tools.omr.staged import adjudicators, consequences, inferences  # noqa: E402,F401
from tools.omr.staged.record import Log, Subject                    # noqa: E402
from tools.omr.staged.record_io import load_record                  # noqa: E402
from tools.omr.staged.adjudicators import clef as C                 # noqa: E402


def rebuild(rec: dict) -> Log:
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


def verdicts_of(log: Log, quantity: str) -> dict:
    return {v["subject"]: v for v in log.to_json()["verdicts"]
            if v["quantity"] == quantity}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--off", action="store_true",
                     help="disable the 2.11b discount -- the BASE arm")
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.off:
        C._off_staff_discount_applies = lambda row, on_staff: False

    rec = load_record(a.record)["record"]
    log = rebuild(rec)
    adjudicate.run(log)
    evaluated = evaluate.run(log)
    infer.run(log, evaluated)
    evaluate.run_over(log, infer.inferred_verdicts(log))

    clefs = verdicts_of(log, "clef")
    print("arm:", "BASE (2.11b OFF)" if a.off else "ARM (2.11b ON)")
    print("clef outcomes:",
          collections.Counter(v["outcome"] for v in clefs.values()).most_common())
    print("clef reasons:",
          collections.Counter(v.get("reason") for v in clefs.values()).most_common())
    discounted_n = sum(1 for v in clefs.values()
                        if v.get("detail", {}).get(C.OFF_STAFF_REASON))
    print("clef verdicts carrying a discount in detail:", discounted_n)

    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(
            json.dumps({"record": log.to_json()}, default=str))
        print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
