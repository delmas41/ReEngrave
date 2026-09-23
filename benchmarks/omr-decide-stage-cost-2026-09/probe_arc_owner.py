"""Isolate WHY `arc_owner` is still slow after the SELF_AND_DESCENDANTS fix.

Runs the decisions that must precede arc_owner in ORDER (cheap -- all under
3s each per the full-run log), then times/cProfiles `adjudicate_arc_owner`
restricted to ONE system's arcs, both with and without
`Evidence.correlated_groups()` -- the O(n^2) pairwise walk over everything a
decision read, flagged unaddressed in roadmap 1.1b FINDINGS.md #12.6.

    python3 -u benchmarks/omr-decide-stage-cost-2026-09/probe_arc_owner.py \
        <record.json> --system-index 0
"""
from __future__ import annotations

import argparse
import cProfile
import pstats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate                          # noqa: E402
from tools.omr.staged import adjudicators, consequences          # noqa: E402,F401
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
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--system-index", type=int, default=0,
                     help="which of log.subjects(Kind.SYSTEM) to isolate")
    ap.add_argument("--no-correlated", action="store_true",
                     help="monkeypatch correlated_groups() to a no-op, to "
                          "isolate its cost from the rest of the decision")
    a = ap.parse_args()

    data = load_record(a.record)
    rec = data["record"] if "record" in data else data
    log = rebuild(rec)

    adjudicate._ensure_decisions()
    log.freeze()

    # Run every decision ORDER puts before arc_owner -- cheap, and arc_owner
    # legitimately depends on some of them (glyph_owner, notehead precision).
    pre = adjudicate.ORDER[: adjudicate.ORDER.index("arc_owner")]
    t0 = time.perf_counter()
    for quantity in pre:
        spec = adjudicate.REGISTRY.get(quantity)
        if spec is None:
            continue
        for subject in adjudicate.subjects_for(log, spec):
            adjudicate.adjudicate_one(log, spec, subject)
    print(f"prerequisite decisions ({len(pre)}): {time.perf_counter() - t0:.3f}s",
          flush=True)

    spec = adjudicate.REGISTRY["arc_owner"]
    all_subjects = adjudicate.subjects_for(log, spec)
    from tools.omr.staged.record import Kind
    systems = log.subjects(Kind.SYSTEM)
    target_system = systems[a.system_index]
    subjects = tuple(s for s in all_subjects if s.at(Kind.SYSTEM) == target_system)
    print(f"system {target_system.to_key()}: {len(subjects)} arcs of "
          f"{len(all_subjects)} total", flush=True)

    if a.no_correlated:
        from tools.omr.staged.adjudicate import Evidence
        Evidence.correlated_groups = lambda self: ()  # type: ignore[assignment]
        print("(correlated_groups() DISABLED for this run)", flush=True)

    seen_sizes = []
    orig_note = adjudicate.Evidence._note
    def spy_note(self, quantity, kept, sub, scope):
        orig_note(self, quantity, kept, sub, scope)
    adjudicate.Evidence._note = spy_note  # unchanged; hook point kept simple

    pr = cProfile.Profile()
    t0 = time.perf_counter()
    pr.enable()
    verdicts = []
    for subject in subjects:
        v = adjudicate.adjudicate_one(log, spec, subject)
        verdicts.append(v)
        seen_sizes.append(len(v.considered))
    pr.disable()
    dt = time.perf_counter() - t0

    print(f"arc_owner over {len(subjects)} arcs of one system: {dt:.3f}s "
          f"({dt / len(subjects):.4f}s/arc)", flush=True)
    if seen_sizes:
        print(f"considered-set size per arc: min={min(seen_sizes)} "
              f"median={sorted(seen_sizes)[len(seen_sizes)//2]} "
              f"max={max(seen_sizes)}", flush=True)

    suffix = "no_correlated" if a.no_correlated else "with_correlated"
    out = Path(a.record).parent / f"arc_owner_system{a.system_index}_{suffix}.prof"
    out_path = Path("benchmarks/omr-decide-stage-cost-2026-09/out") / out.name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pr.dump_stats(str(out_path))
    st = pstats.Stats(str(out_path))
    st.sort_stats("cumulative")
    st.print_stats(15)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
