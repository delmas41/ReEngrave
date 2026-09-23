"""The identical-verdict control for roadmap 1.2.

Dump (subject, quantity, outcome, value, reason, sorted basis, sorted
considered, sorted CORRELATED) for every decision `ORDER` puts at or before
`arc_kind`, restricted to one system. Run once against the BASE tree's
`record.py` + `adjudicate.py` and once against the ARM's, over the SAME saved
record, and diff.

⚠️ `correlated` IS IN THE PAYLOAD AND THE LANE'S OWN DRAFT LEFT IT OUT.
Roadmap 1.2 rewrote `Evidence.correlated_groups()` -- the function that
COMPUTES `Verdict.correlated` -- so a control that dumps only `basis` and
`considered` is blind to the one field the change can move. That draft's
docstring even said so ("the control ... checks `basis` and `considered`
sorted, never `correlated`"), which makes it a control that cannot fail on
its own subject.

⚠️ The control also PRINTS how many dumped verdicts carry a non-empty
`correlated`. If that count is 0 the comparison is vacuous no matter how
clean the diff looks, and the run says so rather than reporting a pass.
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
from tools.omr.staged.record_io import load_record               # noqa: E402

LAST = "arc_kind"


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

    system0 = log.subjects(Kind.SYSTEM)[0]

    # ⚠️ THE WORK IS RESTRICTED TO ONE SYSTEM, NOT JUST THE DUMP. An earlier
    # draft adjudicated all 7 systems and filtered afterwards, which is why
    # the BASE side could not finish: the point of the control is a subset
    # the OLD code can complete, so both sides compute the same thing and
    # the diff means something. A subject above SYSTEM (document/page scope)
    # is kept -- those decisions are cheap and their verdicts are part of
    # what system 0's decisions rest on.
    def in_scope(subject) -> bool:
        sys_of = subject.at(Kind.SYSTEM)
        return sys_of is None or sys_of == system0

    upto = adjudicate.ORDER[: adjudicate.ORDER.index(LAST) + 1]
    t0 = time.perf_counter()
    for quantity in upto:
        spec = adjudicate.REGISTRY.get(quantity)
        if spec is None:
            continue
        for subject in adjudicate.subjects_for(log, spec):
            if not in_scope(subject):
                continue
            adjudicate.adjudicate_one(log, spec, subject)
    dt = time.perf_counter() - t0
    print(f"decisions through {LAST}, system {system0.to_key()} only: {dt:.3f}s",
          flush=True)
    out = []
    with_correlated = 0
    for v in log.all_verdicts():
        if v.subject.at(Kind.SYSTEM) != system0:
            continue
        correlated = sorted(sorted(g) for g in (v.correlated or ()))
        if correlated:
            with_correlated += 1
        out.append({
            "subject": v.subject.to_key(),
            "quantity": v.quantity,
            "outcome": v.outcome.value,
            "value": v.value,
            "reason": v.reason,
            "basis": sorted(v.basis),
            "considered": sorted(v.considered),
            "correlated": correlated,
        })
    out.sort(key=lambda d: (d["subject"], d["quantity"]))
    Path(out_path).write_text(json.dumps(out, indent=2, default=str))
    print(f"wrote {len(out)} verdicts (system {system0.to_key()}) to {out_path}",
          flush=True)
    print(f"verdicts carrying a NON-EMPTY correlated: {with_correlated}", flush=True)
    if with_correlated == 0:
        print("⚠️ CONTROL IS VACUOUS ON ITS OWN SUBJECT: no dumped verdict "
              "carries a correlated group, so an identical diff says nothing "
              "about the rewrite.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
