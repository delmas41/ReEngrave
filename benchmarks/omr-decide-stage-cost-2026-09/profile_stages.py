"""Roadmap 1.2 — per-decision cost profile of ADJUDICATE / GROUPS / EVALUATE / INFER.

Rebuilds a `Log` from a saved staged record's GATHER rows (same technique as
`benchmarks/omr-staged-duration-beams-2026-09/readjudicate.py`) and re-runs the
three post-GATHER stages, timing and cProfile-ing each DECISION / RULE
separately rather than the stage as a whole -- the report tonight's
whole-movement log cannot give, because it only prints a running verdict
count per decision, not a time.

    python3 -u benchmarks/omr-adjudicate-cost-2026-09/profile_stages.py \
        <record.json> --out-dir benchmarks/omr-adjudicate-cost-2026-09/out

Writes, to --out-dir:
    timings.json         -- one row per (stage, decision): n_subjects, seconds
    adjudicate_<q>.prof   -- a cProfile pstats dump for that decision
    evaluate_<c>.prof
    infer_<r>.prof

⚠️ ONE cProfile.Profile() PER DECISION, not one for the whole stage: cProfile
cannot hand back "stats since the last snapshot" mid-run, and creating a fresh
profiler per decision is cheap, so this is the only way to get a
function-level breakdown that can be attributed to ONE decision rather than to
the whole stage.

⚠️ WHAT THIS DOES NOT MEASURE: cProfile's own instrumentation overhead is not
subtracted, so an absolute second count here is not the same second count an
unprofiled run would show -- only the RELATIVE ranking across decisions, and
the identity of the dominant functions, are the claims this makes.
"""
from __future__ import annotations

import argparse
import cProfile
import json
import pstats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate, evaluate, groups, infer  # noqa: E402
from tools.omr.staged import adjudicators, consequences, inferences  # noqa: E402,F401
from tools.omr.staged.record import Log, Subject                 # noqa: E402
from tools.omr.staged.record_io import load_record                # noqa: E402


def rebuild(rec: dict) -> Log:
    """One Log holding exactly the saved record's GATHER rows, in order.

    Identical in shape to `omr-staged-duration-beams-2026-09/readjudicate.py`
    `rebuild()` -- kept as its own copy rather than imported, because that
    module lives under a sibling benchmark directory this lane must not edit,
    and a one-screen function is cheaper to duplicate than to import across a
    benchmark boundary.
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


def _record_of(data: dict) -> dict:
    return data["record"] if "record" in data else data


def profile_adjudicate(log: Log, out_dir: Path, rows: list) -> None:
    adjudicate._ensure_decisions()
    if not log.frozen:
        log.freeze()
    for quantity in adjudicate.ORDER:
        spec = adjudicate.REGISTRY.get(quantity)
        if spec is None:
            continue
        subjects = adjudicate.subjects_for(log, spec)
        n = len(subjects)
        pr = cProfile.Profile()
        t0 = time.perf_counter()
        pr.enable()
        for subject in subjects:
            adjudicate.adjudicate_one(log, spec, subject)
        pr.disable()
        dt = time.perf_counter() - t0
        pr.dump_stats(str(out_dir / f"adjudicate_{quantity}.prof"))
        rows.append({"stage": "adjudicate", "name": quantity,
                     "n": n, "seconds": dt,
                     "seconds_per": (dt / n) if n else None})
        print(f"  [adjudicate] {quantity}: n={n} t={dt:.3f}s", flush=True)


def profile_groups(log: Log, out_dir: Path, rows: list) -> None:
    """`groups.run` has no per-redundancy hook exposed, so this profiles the
    WHOLE stage as one entry -- named because tonight's log shows most of the
    12+ hours sitting in GATHER-then-ADJUDICATE-then-groups-then-EVALUATE, and
    a table that skips it would understate where the time goes even though
    the brief's per-decision ask was scoped to ADJUDICATE/EVALUATE/INFER."""
    pr = cProfile.Profile()
    t0 = time.perf_counter()
    pr.enable()
    report = groups.run(log)
    pr.disable()
    dt = time.perf_counter() - t0
    pr.dump_stats(str(out_dir / "groups_all.prof"))
    n = len(getattr(report, "readings", []) or [])
    rows.append({"stage": "groups", "name": "(whole stage)",
                 "n": n, "seconds": dt, "seconds_per": None})
    print(f"  [groups] whole stage: t={dt:.3f}s", flush=True)


def profile_evaluate(log: Log, out_dir: Path, rows: list) -> evaluate.Report:
    evaluate._ensure_rules()
    ordered = sorted(evaluate.RULES, key=lambda r: evaluate.DOWNHILL.index(r.cause))
    report = evaluate.Report(fired=[], skipped=[], stubs=[])
    for r in ordered:
        name = r.consequence.value
        if r.stub:
            report.stubs.append(f"{name}({r.cause}->{r.effect})")
            continue
        subjects = log.subjects(r.scope)
        n = len(subjects)
        pr = cProfile.Profile()
        t0 = time.perf_counter()
        pr.enable()
        for subject in subjects:
            cause = evaluate._cause_for(log, r.cause, subject)
            if cause is None:
                report.skipped.append((name, subject.to_key(), "cause_absent"))
                continue
            if cause.outcome.value == "abstained":
                report.skipped.append((name, subject.to_key(), "cause_abstained"))
                continue
            if cause.outcome.value == "narrowed":
                report.skipped.append((name, subject.to_key(), "cause_narrowed"))
                continue
            produced = r.fn(log, subject, cause)
            for v in produced:
                report.fired.append((name, subject.to_key(), v.quantity))
        pr.disable()
        dt = time.perf_counter() - t0
        pr.dump_stats(str(out_dir / f"evaluate_{name}.prof"))
        rows.append({"stage": "evaluate", "name": name, "n": n,
                     "seconds": dt, "seconds_per": (dt / n) if n else None})
        print(f"  [evaluate] {name}: n={n} t={dt:.3f}s", flush=True)
    return report


def profile_infer(log: Log, evaluated, out_dir: Path, rows: list) -> None:
    if not infer.stage_should_run():
        print("  [infer] no rule enabled by default; skipping", flush=True)
        return
    infer._ensure_rules()
    report = infer.Report()
    for r in infer.RULES:
        name = r.inference.value
        if r.stub:
            report.stubs.append(f"{name}({r.target})")
            continue
        if not r.switch():
            report.disabled.append((name, r.switch.env))
            print(f"  [infer] {name}: disabled by {r.switch.env}", flush=True)
            continue
        subjects = log.subjects(r.scope)
        n = len(subjects)
        pr = cProfile.Profile()
        t0 = time.perf_counter()
        pr.enable()
        produced = 0
        for subject in subjects:
            for p in r.fn(log, subject):
                if infer._admit(log, r, p, report) is not None:
                    produced += 1
        pr.disable()
        dt = time.perf_counter() - t0
        pr.dump_stats(str(out_dir / f"infer_{name}.prof"))
        rows.append({"stage": "infer", "name": name, "n": n,
                     "seconds": dt, "seconds_per": (dt / n) if n else None})
        print(f"  [infer] {name}: n={n} produced={produced} t={dt:.3f}s",
              flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--skip-groups", action="store_true",
                     help="groups.run is not part of the brief's ask; skip "
                          "it if it is the long pole and time is short")
    a = ap.parse_args()
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list = []

    t0 = time.perf_counter()
    data = load_record(a.record)
    rec = _record_of(data)
    t_load = time.perf_counter() - t0
    print(f"load_record: {t_load:.3f}s "
          f"({len(rec.get('observations', []))} obs, "
          f"{len(rec.get('abstentions', []))} abs, "
          f"{len(rec.get('verdicts', []))} verdicts already in the file)",
          flush=True)

    t0 = time.perf_counter()
    log = rebuild(rec)
    t_rebuild = time.perf_counter() - t0
    print(f"rebuild: {t_rebuild:.3f}s", flush=True)

    rows.append({"stage": "load", "name": "load_record", "n": None,
                 "seconds": t_load, "seconds_per": None})
    rows.append({"stage": "load", "name": "rebuild_log", "n": None,
                 "seconds": t_rebuild, "seconds_per": None})

    print("=== ADJUDICATE ===", flush=True)
    t0 = time.perf_counter()
    profile_adjudicate(log, out_dir, rows)
    t_adj = time.perf_counter() - t0
    print(f"ADJUDICATE total: {t_adj:.3f}s", flush=True)
    rows.append({"stage": "adjudicate", "name": "(TOTAL)", "n": None,
                 "seconds": t_adj, "seconds_per": None})

    if not a.skip_groups:
        print("=== GROUPS ===", flush=True)
        t0 = time.perf_counter()
        profile_groups(log, out_dir, rows)
        t_grp = time.perf_counter() - t0
        print(f"GROUPS total: {t_grp:.3f}s", flush=True)

    print("=== EVALUATE ===", flush=True)
    t0 = time.perf_counter()
    report = profile_evaluate(log, out_dir, rows)
    t_eval = time.perf_counter() - t0
    print(f"EVALUATE total: {t_eval:.3f}s", flush=True)
    rows.append({"stage": "evaluate", "name": "(TOTAL)", "n": None,
                 "seconds": t_eval, "seconds_per": None})

    print("=== INFER ===", flush=True)
    t0 = time.perf_counter()
    profile_infer(log, report, out_dir, rows)
    t_infer = time.perf_counter() - t0
    print(f"INFER total: {t_infer:.3f}s", flush=True)
    rows.append({"stage": "infer", "name": "(TOTAL)", "n": None,
                 "seconds": t_infer, "seconds_per": None})

    (out_dir / "timings.json").write_text(json.dumps(rows, indent=2))

    # ── top functions for the slowest decisions ────────────────────────────
    named = [r for r in rows if r["name"] not in ("(TOTAL)", "(whole stage)")
             and r["stage"] in ("adjudicate", "evaluate", "infer")]
    named.sort(key=lambda r: r["seconds"], reverse=True)
    print("\n=== SLOWEST DECISIONS/RULES ===", flush=True)
    for r in named[:8]:
        print(f"{r['stage']:>10} {r['name']:<30} n={r['n']!s:<8} "
              f"{r['seconds']:.3f}s", flush=True)

    report_lines = ["# Slowest decisions -- top functions by cumulative time\n"]
    for r in named[:3]:
        prof_path = out_dir / f"{r['stage']}_{r['name']}.prof"
        if not prof_path.exists():
            continue
        report_lines.append(f"\n## {r['stage']} / {r['name']} "
                             f"(n={r['n']}, {r['seconds']:.3f}s)\n")
        buf_path = out_dir / f"{r['stage']}_{r['name']}.pstats.txt"
        import io
        buf = io.StringIO()
        st = pstats.Stats(str(prof_path), stream=buf)
        st.sort_stats("cumulative")
        st.print_stats(20)
        st.print_callers(10)
        buf_path.write_text(buf.getvalue())
        report_lines.append(f"(full listing: {buf_path.name})\n")
        # inline the top 12 lines of the stats table for the report itself
        text = buf.getvalue().splitlines()
        header_idx = next((i for i, l in enumerate(text)
                            if "ncalls" in l and "tottime" in l), 0)
        report_lines.append("```\n" + "\n".join(
            text[header_idx:header_idx + 15]) + "\n```\n")

    (out_dir / "SLOWEST.md").write_text("\n".join(report_lines))
    print(f"\nWrote {out_dir / 'timings.json'} and {out_dir / 'SLOWEST.md'}",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
