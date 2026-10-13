#!/usr/bin/env python3
"""l281p2_reinfer: ROADMAP 2.81 PHASE 2 -- run INFER again over a saved quick record, with the
bare-stem bar rule ON, and say what happened to the bars. An iteration instrument, nothing else.

It rebuilds a `Log` from the record's rows (GATHER, ADJUDICATE, EVALUATE) WITHOUT the verdicts INFER
wrote (and without anything that rests on one), runs `infer.run` over it, and writes
`{"record": ...}` -- the shape `l281_extract.py` streams -- so `l281p2_score.sh` scores the arm on
Sean's hand truth with the Phase 1 scorer, unchanged.

⚠️ BLIND TO ADJUDICATE AND GATHER by construction (like `reinfer.py`): the quarter-first RANKING is
an ADJUDICATE change and only a re-gather shows it. This shows what the bar's arithmetic does to the
narrowings the saved record holds. `--control` rebuilds with the infer verdicts KEPT and checks every
verdict reproduces (a rebuild that does not reproduce the record is not a control).

    python3 l281p2_reinfer.py RECORD --out arm.json [--flag 1|0] [--census census.json]
"""
import argparse
import collections
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "benchmarks" / "omr-infer-stage-2026-09"))

import reinfer  # noqa: E402  (the sanctioned rebuild; we reuse its row replay)
from tools.omr.staged import evaluate, infer, inferences  # noqa: E402
from tools.omr.staged.record import (Candidate, Kind, Log, Outcome, Subject,  # noqa: E402
                                     UphillConsequence, Verdict)


def rebuild_without_infer(rec):
    """`reinfer.rebuild`, dropping INFER's verdicts and anything whose basis/supersedes reaches one."""
    dropped = {v["id"] for v in rec["verdicts"] if str(v.get("decider", "")).startswith("infer:")}
    changed = True
    while changed:
        changed = False
        for v in rec["verdicts"]:
            if v["id"] in dropped:
                continue
            if v.get("supersedes") in dropped or any(b in dropped for b in (v.get("basis") or ())):
                dropped.add(v["id"])
                changed = True
    kept = dict(rec, verdicts=[v for v in rec["verdicts"] if v["id"] not in dropped])
    return reinfer.rebuild(kept), dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", default=None)
    ap.add_argument("--flag", default="1")
    ap.add_argument("--census", default=None)
    ap.add_argument("--control", action="store_true")
    a = ap.parse_args()
    from tools.omr.staged.record_io import load_record
    doc = load_record(a.record)
    rec = doc["record"] if "record" in doc else doc
    if a.control:
        return reinfer.control(rec, reinfer.rebuild(rec))
    log, dropped = rebuild_without_infer(rec)
    print(f"rebuilt without {len(dropped)} verdicts INFER wrote or that rest on them")
    # the census FIRST: every bar that holds a bare-stem narrowing, and what the arithmetic says of it
    per = collections.Counter()
    landings = collections.Counter()
    for cell in log.subjects(Kind.CELL):
        out = inferences.solve_bare_stem_bar(log, cell)
        if not out.members:
            continue
        per["members"] += out.members
        if out.decline:
            per["declined:" + out.decline] += out.members
        else:
            per["forced"] += out.forced
            per["ambiguous"] += out.ambiguous
            landings[min(out.landings, 9)] += 1
    print("BARS holding a bare-stem narrowing, member counts:", dict(sorted(per.items())))
    print("  landings per solved bar (9 = 9+):", dict(sorted(landings.items())))
    os.environ[infer.BARE_STEM_BAR_ENV] = a.flag
    report = infer.run(log, evaluate.Report(fired=[], skipped=[], stubs=[]))
    by_rule = collections.Counter(i[0] for i in report.inferred)
    print("inferred by rule:", dict(by_rule))
    print("reach:", report.reach)
    per_decline = per
    if a.census:
        Path(a.census).write_text(json.dumps({"by_rule": by_rule, "left": per_decline, "reach": report.reach},
                                             indent=1, default=str))
    if a.out:
        Path(a.out).write_text(json.dumps({"record": log.to_json(), "inference": report.to_json()},
                                          separators=(",", ":"), default=str))
        print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
