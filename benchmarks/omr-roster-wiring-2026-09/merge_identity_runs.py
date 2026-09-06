#!/usr/bin/env python3
"""Pool the two identity runs, and CHECK that the OFF arm reproduced.

The 20-row sweep was run twice: once with the roster search walking the front of
the PDF (which missed the two Simrock rows entirely), then once over just those
two rows with the search walking BACKWARD from the run. Pooling them is only
legitimate if the arm that did NOT change reproduces, so that is asserted rather
than assumed — the two Dvořák rows appear in both runs and their OFF arm must
agree record for record.

    python3 benchmarks/omr-roster-wiring-2026-09/merge_identity_runs.py \
        --base /tmp/roster-identity-frontwindow.json \
        --patch benchmarks/omr-roster-wiring-2026-09/roster-identity.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def key(r):
    return (r["row_id"], r["system_index"], r["ordinal"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--patch", required=True)
    args = ap.parse_args()

    base = json.loads(Path(args.base).read_text())
    patch = json.loads(Path(args.patch).read_text())
    by = {key(r): r for r in base["records"]}

    # ── the control: the unchanged arm must reproduce ───────────────────────
    checked = disagreed = 0
    for r in patch["records"]:
        old = by.get(key(r))
        if old is None:
            continue
        checked += 1
        if old["OFF"] != r["OFF"]:
            disagreed += 1
            print(f"  ⚠️ OFF differs at {key(r)}: {old['OFF']} vs {r['OFF']}")
    print(f"CONTROL: OFF arm reproduced on {checked - disagreed}/{checked} "
          f"overlapping records")
    if disagreed:
        raise SystemExit("the OFF arm did not reproduce — the two runs are not "
                         "poolable and no merged figure may be quoted")

    for r in patch["records"]:
        by[key(r)] = r
    records = list(by.values())

    def score(arm, subset=None):
        rs = [r for r in records if r["TRUTH"]]
        if subset:
            rs = [r for r in rs if subset(r)]
        named = [r for r in rs if r[arm]]
        right = [r for r in named if r[arm] == r["TRUTH"]]
        return (len(rs), len(named), len(named) / len(rs) if rs else 0,
                len(right), len(right) / len(named) if named else 0,
                len(right) / len(rs) if rs else 0)

    print(f"\nPOOLED over {len([r for r in records if r['TRUTH']])} "
          f"truth-bearing staff records")
    print(f"  {'arm':5s} {'n':>4s} {'named':>6s} {'cov':>7s} {'right':>6s} "
          f"{'prec':>7s} {'right/all':>10s}")
    for arm in ("OFF", "ON"):
        n, named, cov, right, prec, acc = score(arm)
        print(f"  {arm:5s} {n:4d} {named:6d} {cov:7.3f} {right:6d} {prec:7.3f}"
              f" {acc:10.3f}")

    print(f"\n  by publisher:")
    for pub in sorted({r["publisher"] for r in records}):
        for arm in ("OFF", "ON"):
            n, named, cov, right, prec, acc = score(
                arm, lambda r, p=pub: r["publisher"] == p)
            print(f"  {pub:12s} {arm:4s} n {n:4d} named {named:4d} "
                  f"cov {cov:.3f} right {right:4d} prec {prec:.3f} "
                  f"right/all {acc:.3f}")

    changed = [r for r in records if r["OFF"] != r["ON"] and r["TRUTH"]]
    tally = Counter()
    for r in changed:
        was, now = r["OFF"] == r["TRUTH"], r["ON"] == r["TRUTH"]
        tally["fixed" if now and not was else
              "BROKEN" if was and not now else
              "still right" if now else "still wrong"] += 1
    print(f"\n  changed: {len(changed)}   {dict(tally)}")

    src = {a: Counter(r[f"{a}_source"] for r in records) for a in ("OFF", "ON")}
    print(f"\n  provenance over all {len(records)} records:")
    for k in sorted(set(src['OFF']) | set(src['ON']), key=str):
        print(f"    {str(k):22s} OFF {src['OFF'].get(k, 0):4d}   "
              f"ON {src['ON'].get(k, 0):4d}")

    (HERE / "roster-identity-pooled.json").write_text(json.dumps(
        {"meta": {"base": args.base, "patch": args.patch,
                  "control_records_checked": checked},
         "records": records}, indent=1))
    print(f"\n  wrote {HERE/'roster-identity-pooled.json'}")


if __name__ == "__main__":
    main()
