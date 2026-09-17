"""BYTE-IDENTITY CONTROL — does declaring a claim kind change what a record IS?

⚠️⚠️ THE BLAST RADIUS IS THE QUESTION THIS JOB WAS MOST AT RISK OF WAVING
THROUGH. A claim kind stored as a FIELD would change every record this repo
has ever written; CLAUDE.md records that exact hazard being paid for once
already (`Verdict.single_pass_revision` is SET, READ by the fixpoint guard,
and deliberately ABSENT from `Verdict.to_json`, because adding a key there
"changes every record in the tree"). So the claim is DERIVED and not stored,
and this control is what turns that from a design intention into a measurement.

It writes one `Log` exercising EVERY quantity in the vocabulary — observations
and verdicts — and prints the md5 of `log.to_json()`. Run it on this tree and
on the merge base; the two hashes must agree.

    git stash list            # (do not: see CLAUDE.md on the shared stash)
    python3 benchmarks/omr-claim-kind-2026-09/probe/record_bytes_control.py

⚠️ THE POSITIVE CONTROL IS BUILT IN. `--positive-control` serialises the claim
into every row, which is what a stored field would have done, and prints a
DIFFERENT hash. Without it, a hash that matches because the script serialised
nothing at all would be indistinguishable from a hash that matches because the
change is inert — the "control that computes the wrong thing" family.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged.record import (            # noqa: E402
    CLAIMS, Log, Outcome, Q, Verdict, claim_of, glyph, staff)


def build() -> Log:
    """One row per quantity, so no quantity can slip the comparison."""
    log = Log()
    names = {k: v for k, v in vars(Q).items()
             if not k.startswith("_") and isinstance(v, str)}
    for i, (name, q) in enumerate(sorted(names.items())):
        # Observations for everything the vocabulary holds. The point is the
        # SHAPE of the serialised row, not whether a real gatherer would emit
        # this quantity here.
        log.observe(glyph(0, 0, 0, 0, i), q, [i, i + 1],
                    reader="detector", frame="cell:0",
                    score=(0.5 if i % 2 else None), note=f"row-{i}")
    for i, (name, q) in enumerate(sorted(names.items())):
        log.record(Verdict(f"vrd{i}", staff(0, 0, i), q, Outcome.DECIDED,
                           i, "probe", "read"))
    return log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--positive-control", action="store_true",
                    help="serialise the claim, as a stored field would have")
    args = ap.parse_args()

    log = build()
    blob = log.to_json()
    if args.positive_control:
        for row in blob["observations"]:
            row["claim"] = claim_of(row["quantity"])
        for row in blob["verdicts"]:
            row["claim"] = claim_of(row["quantity"])

    text = json.dumps(blob, sort_keys=True, default=str)
    digest = hashlib.md5(text.encode()).hexdigest()

    print(f"quantities declared      {len(CLAIMS)}")
    print(f"observations serialised  {len(blob['observations'])}")
    print(f"verdicts serialised      {len(blob['verdicts'])}")
    print(f"observation row keys     "
          f"{sorted(blob['observations'][0])}")
    print(f"arm                      "
          f"{'POSITIVE CONTROL (claim stored)' if args.positive_control else 'as shipped (claim derived)'}")
    print(f"md5                      {digest}")

    if not blob["observations"] or not blob["verdicts"]:
        print("⚠️ the control serialised nothing — a matching hash would be "
              "meaningless", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
