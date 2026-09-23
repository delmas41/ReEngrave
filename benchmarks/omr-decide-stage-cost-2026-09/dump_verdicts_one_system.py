"""Dump (subject, quantity, outcome, value, reason, sorted basis, sorted
considered) for every decision ORDER puts at or before arc_owner, restricted
to system 0 -- the control payload for roadmap 1.2's base-vs-arm comparison.
Run once against origin/main's record.py+adjudicate.py and once against this
branch's, over the SAME saved record, and diff the two JSON files.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate                          # noqa: E402
from tools.omr.staged import adjudicators, consequences          # noqa: E402,F401
from tools.omr.staged.record import Log, Subject, Kind           # noqa: E402
from tools.omr.staged.record_io import load_record                # noqa: E402


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


def main() -> int:
    path, out_path = sys.argv[1], sys.argv[2]
    data = load_record(path)
    rec = data["record"] if "record" in data else data
    log = rebuild(rec)

    adjudicate._ensure_decisions()
    log.freeze()

    upto = adjudicate.ORDER[: adjudicate.ORDER.index("arc_owner") + 1]
    t0 = time.perf_counter()
    for quantity in upto:
        spec = adjudicate.REGISTRY.get(quantity)
        if spec is None:
            continue
        for subject in adjudicate.subjects_for(log, spec):
            adjudicate.adjudicate_one(log, spec, subject)
    dt = time.perf_counter() - t0
    print(f"decisions through arc_owner: {dt:.3f}s", flush=True)

    system0 = log.subjects(Kind.SYSTEM)[0]
    out = []
    for v in log.all_verdicts():
        sub_sys = v.subject.at(Kind.SYSTEM)
        if sub_sys != system0:
            continue
        out.append({
            "subject": v.subject.to_key(),
            "quantity": v.quantity,
            "outcome": v.outcome.value,
            "value": v.value,
            "reason": v.reason,
            "basis": sorted(v.basis),
            "considered": sorted(v.considered),
        })
    out.sort(key=lambda d: (d["subject"], d["quantity"]))
    Path(out_path).write_text(json.dumps(out, indent=2, default=str))
    print(f"wrote {len(out)} verdicts (system {system0.to_key()}) to {out_path}",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
