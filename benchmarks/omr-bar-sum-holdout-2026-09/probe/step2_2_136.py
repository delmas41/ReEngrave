"""ROADMAP 2.136 step 2 -- what INFER's `collapse_narrowed_by_bar` settles with
`OMR_INFER_CARRIED_METER_FIX` ON versus OFF, on a saved record, in process.

PATH: STAGED INFER (tools/omr/staged/inferences.py, rule collapse_narrowed_by_bar).
No gather, no whole-movement re-run. The record is loaded once via record_io.load_record, its GATHER
rows rebuilt and its OWN verdicts inserted as written (step 1's way, `reconcile_gates_2_136.py`), the
log frozen. Then, for every CELL, the rule's own function is called with the flag OFF and with it ON
(DRY: proposals only, nothing admitted). The ON proposals are then admitted through INFER's own
`_admit` guard, and the new verdicts are written to <out>.new_verdicts.json (for the judged overlay).

    python3 step2_2_136.py RECORD --label lit|brah --out OUT.json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
T0 = time.time()


def say(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    from tools.omr.staged import consequences as C
    from tools.omr.staged import infer as INF
    from tools.omr.staged import inferences as INFS
    from tools.omr.staged.record import (Candidate, Kind, Outcome, Q, Subject,
                                         Verdict)
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun as RR

    doc = load_record(a.record)
    rec = doc["record"] if "record" in doc else doc
    log, _ = RR.rebuild_gather(rec)
    n_v = 0
    for v in rec.get("verdicts") or ():
        cands = tuple(Candidate(value=c["value"], support=c.get("support", 0.0))
                      for c in v.get("candidates") or ())
        vv = Verdict(
            id=v["id"], subject=Subject.from_key(v["subject"]),
            quantity=v["quantity"], outcome=Outcome(v["outcome"]),
            value=v.get("value"), decider=v["decider"], reason=v["reason"],
            considered=tuple(v.get("considered") or ()),
            used=tuple(v.get("used") or ()),
            missing=tuple(v.get("missing") or ()),
            declined=tuple(v.get("declined") or ()),
            excluded=tuple(tuple(e) for e in v.get("excluded") or ()),
            correlated=tuple(frozenset(g) for g in v.get("correlated") or ()),
            basis=tuple(v.get("basis") or ()), candidates=cands,
            margin=v.get("margin"), supersedes=v.get("supersedes"),
            detail=dict(v.get("detail") or {}))
        log._vrd[vv.id] = vv
        log._index(vv.quantity, vv.subject, vv.id)
        n_v += 1
    del doc, rec
    log.freeze()
    say(f"log built: {n_v} verdicts as written, frozen")

    INF._ensure_rules()
    rule = next(r for r in INF.RULES
                if r.inference is INF.Inference.COLLAPSE_NARROWED_BY_BAR)

    def narrowed_of(cell):
        return {v.subject.to_key() for v in C._standing(log, cell, Q.DURATION)
                if v.outcome is Outcome.NARROWED and not C._is_rest(v)
                and C._left_the_bar(log, v.subject) is None}

    cells = [s for s in log.subjects(Kind.CELL)]
    say(f"{len(cells)} cells")
    rows = []
    for state in ("0", "1"):
        os.environ[INF.CARRIED_METER_FIX_ENV] = state
        for i, cell in enumerate(cells):
            nar = narrowed_of(cell)
            if not nar:
                continue
            o = INFS.solve_bare_stem_bar(log, cell, any_reason=True)
            props = {p.subject.to_key(): p for p in (o.proposals or [])}
            rows.append({
                "flag": state, "cell": [cell.page, cell.system, cell.staff, cell.cell],
                "narrowed": sorted(nar), "decline": o.decline, "forced": o.forced,
                "ambiguous": o.ambiguous, "tip_not_clean": o.tip_not_clean,
                "lengthening_unwitnessed": o.lengthening_unwitnessed,
                "settled": {k: [(p.value or {}).get("beats"),
                                (p.value or {}).get("beam_levels")]
                            for k, p in props.items()},
                "fully_released": bool(nar) and set(props) >= nar})
        say(f"flag={state}: done")

    def summ(state):
        rs = [r for r in rows if r["flag"] == state]
        return {"cells_with_a_narrowed_head": len(rs),
                "bars_with_a_settled_head": sum(1 for r in rs if r["settled"]),
                "bars_fully_released": sum(1 for r in rs if r["fully_released"]),
                "notes_settled": sum(len(r["settled"]) for r in rs),
                "declines": dict(collections.Counter(r["decline"] for r in rs))}

    off, on = summ("0"), summ("1")
    say(f"OFF {off}")
    say(f"ON  {on}")
    # what ON adds over OFF, by (cell)
    off_by = {tuple(r["cell"]): r for r in rows if r["flag"] == "0"}
    added = []
    for r in rows:
        if r["flag"] != "1":
            continue
        base = off_by[tuple(r["cell"])]
        new = {k: v for k, v in r["settled"].items() if k not in base["settled"]}
        if new:
            added.append({"cell": r["cell"], "new": new,
                          "fully_released": r["fully_released"],
                          "was_declined": base["decline"],
                          "n_narrowed": len(r["narrowed"])})
        for k, v in base["settled"].items():     # the fix must never CHANGE an OFF settlement
            if r["settled"].get(k) != v:
                added.append({"cell": r["cell"], "CHANGED": k, "off": v,
                              "on": r["settled"].get(k)})
    say(f"ON adds {sum(len(x.get('new', {})) for x in added)} notes in "
        f"{sum(1 for x in added if 'new' in x)} bars; "
        f"changed-from-OFF: {sum(1 for x in added if 'CHANGED' in x)}")

    # admit the ON proposals through INFER's own guard (what the rule would write)
    os.environ[INF.CARRIED_METER_FIX_ENV] = "1"
    report = INF.Report()
    new_v = []
    for cell in cells:
        if not narrowed_of(cell):
            continue
        for p in rule.fn(log, cell):
            v = INF._admit(log, rule, p, report)
            if v is not None:
                new_v.append({
                    "id": v.id, "subject": v.subject.to_key(), "quantity": v.quantity,
                    "outcome": v.outcome.value, "value": v.value, "decider": v.decider,
                    "reason": v.reason, "margin": v.margin, "supersedes": v.supersedes,
                    "candidates": [{"value": c.value, "support": c.support}
                                   for c in v.candidates],
                    "detail": v.detail})
    say(f"admitted {len(new_v)} verdicts (skipped {len(report.skipped)})")
    Path(a.out).write_text(json.dumps(
        {"label": a.label, "record": a.record, "off": off, "on": on,
         "added": added, "rows": rows}, indent=1, default=str))
    Path(a.out).with_suffix(".new_verdicts.json").write_text(
        json.dumps(new_v, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
