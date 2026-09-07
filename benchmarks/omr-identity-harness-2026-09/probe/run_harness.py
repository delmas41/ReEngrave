#!/usr/bin/env python3
"""The identity harness — run it.

    python3 probe/run_harness.py                 # the default report
    python3 probe/run_harness.py --arms 'beet5/*' --detail
    python3 probe/run_harness.py --records out/records.json

MEASUREMENT ONLY.  Nothing here imports `tools.omr`, changes a default or runs
the pipeline; every arm is a committed artefact of an earlier session and the
whole report takes about a second.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import arms as arms_mod          # noqa: E402
import load as load_mod          # noqa: E402
import score as score_mod        # noqa: E402


def select(patterns):
    if not patterns:
        return sorted(arms_mod.ARMS)
    out = []
    for name in sorted(arms_mod.ARMS):
        if any(fnmatch.fnmatch(name, p) for p in patterns):
            out.append(name)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="*", default=None,
                    help="glob(s) over arm names; default all")
    ap.add_argument("--detail", action="store_true")
    ap.add_argument("--veto", action="store_true",
                    help="also derive the absent-instrument-veto-ON arm")
    ap.add_argument("--records", help="write every graded staff record to JSON")
    ap.add_argument("--pool", action="store_true",
                    help="pool the two works within each regime")
    ap.add_argument("--pool-selected", action="store_true",
                    help="pool exactly the selected arms into one row; "
                         "REFUSES if their regimes are not the same kind, "
                         "because a pooled figure across page-set regimes is "
                         "not a measurement of anything")
    args = ap.parse_args()

    names = select(args.arms)
    missing = [n for n in names
               if not (load_mod.MAIN / arms_mod.ARMS[n][1]).is_file()]
    for n in missing:
        print(f"MISSING ARTEFACT (skipped): {n} -> {arms_mod.ARMS[n][1]}")
    names = [n for n in names if n not in missing]
    if not names:
        print("REFUSING: no arm resolved to a committed artefact")
        return 1

    reports = []
    for n in names:
        work, path, regime, _note = arms_mod.ARMS[n]
        doc = load_mod.load(path, work, n)
        reports.append(score_mod.score(doc, regime))
        if args.veto:
            reports.append(score_mod.score(load_mod.apply_veto(doc), regime))

    by_regime: dict[str, list] = {}
    for r in reports:
        by_regime.setdefault(r.regime, []).append(r)

    for regime in sorted(by_regime):
        rs = by_regime[regime]
        print(f"\n############ REGIME: {regime}")
        print("  IDENTITY is over JUDGEABLE records (full systems only); "
              "HUMAN is over ALL staff records.")
        print(score_mod.HEAD)
        for r in sorted(rs, key=lambda r: (r.work, r.arm)):
            print(score_mod.line(r))
        if args.pool:
            byarm: dict[str, list] = {}
            for r in rs:
                byarm.setdefault(r.arm.split("/", 1)[1], []).append(r)
            print("  -- pooled over works, per arm (only where both works ran):")
            for a, group in sorted(byarm.items()):
                if len(group) < 2:
                    continue
                print(score_mod.line(score_mod.pooled(group, "POOL " + a)))

    if args.pool_selected:
        kinds = {r.regime.split("[")[0].split()[0] for r in reports}
        print()
        if len(kinds) > 1:
            print("REFUSING to pool: the selected arms span page-set regimes "
                  f"{sorted(kinds)}.  Identity moves more with the page set "
                  "than with any flag measured here; a pooled figure across "
                  "regimes is not a measurement of anything.")
        else:
            p = score_mod.pooled(reports, "POOLED-SELECTED")
            print(score_mod.HEAD)
            print(score_mod.line(p))
            print(score_mod.detail(p))

    if args.detail:
        print()
        for r in reports:
            print(score_mod.detail(r))
            print()

    if args.records:
        rows = [x for r in reports for x in r.records]
        Path(args.records).write_text(json.dumps(
            {"n": len(rows), "arms": names, "records": rows}, indent=1))
        print(f"\nwrote {len(rows)} graded staff records -> {args.records}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
