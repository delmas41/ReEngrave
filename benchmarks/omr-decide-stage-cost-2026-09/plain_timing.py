"""No cProfile at all -- the number that matters for the budget, since
per-decision cProfile instrumentation inflates every call by a constant
factor and the SLOWEST.md / timings.json table is deliberately profiled
throughout to get function-level attribution everywhere, not just on the
top 3."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate, evaluate, groups, infer  # noqa: E402
from tools.omr.staged import adjudicators, consequences, inferences  # noqa: E402,F401
from tools.omr.staged.record import Log, Subject                 # noqa: E402
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
    path = sys.argv[1]
    data = load_record(path)
    rec = data["record"] if "record" in data else data

    t0 = time.perf_counter()
    log = rebuild(rec)
    t_rebuild = time.perf_counter() - t0

    t0 = time.perf_counter()
    adjudicate.run(log, progress=True)
    t_adj = time.perf_counter() - t0

    t0 = time.perf_counter()
    groups.run(log)
    t_grp = time.perf_counter() - t0

    t0 = time.perf_counter()
    report = evaluate.run(log, progress=True)
    t_eval = time.perf_counter() - t0

    t0 = time.perf_counter()
    if infer.stage_should_run():
        infer.run(log, report, progress=True)
    t_infer = time.perf_counter() - t0

    total = t_rebuild + t_adj + t_grp + t_eval + t_infer
    print(f"\nrebuild={t_rebuild:.3f}s adjudicate={t_adj:.3f}s "
          f"groups={t_grp:.3f}s evaluate={t_eval:.3f}s infer={t_infer:.3f}s "
          f"TOTAL(post-load)={total:.3f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
