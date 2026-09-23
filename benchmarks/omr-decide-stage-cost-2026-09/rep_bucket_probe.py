"""§4's counter-example: a (reader, frame, quantity) bucket does NOT fix
`derived_from`, so one bucket representative cannot answer for the bucket.

The first draft of roadmap 1.2's `correlated_groups()` rewrite tested ONE
representative per observation bucket against each Verdict/Abstention,
reasoning that "`_one_signal` does not special-case which specific bucket
member it is comparing against". It does, through `closure(b)`:

    shared = log.closure(a.id) & log.closure(b.id)

`record.Observation`'s own docstring records that the empty-basis invariant
was found TOO STRONG on 2026-09-07 -- "a modelling error with a live
consequence" -- and that `derived_from` is how an external fact's descendants
carry it. Two rows can therefore share a bucket and have DISJOINT closures.

Run: python3 benchmarks/omr-decide-stage-cost-2026-09/rep_bucket_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged.adjudicate import _one_signal            # noqa: E402
from tools.omr.staged.record import (Log, Outcome, Q, READERS,  # noqa: E402
                                     Verdict)
from tools.omr.staged import record as R                        # noqa: E402


def main() -> int:
    log = Log()
    sub = R.staff(0, 0, 0)

    dossier = log.observe(R.DOCUMENT, Q.DOSSIER_FACT, {"clef": "alto"},
                          reader=READERS.DOSSIER, frame="page", tier="dossier")
    roster = log.observe(R.DOCUMENT, Q.ROSTER_ENTRY, {"n": 1},
                         reader=READERS.CATALOG, frame="page", tier="catalog")

    # SAME (reader, frame, quantity) bucket, DIFFERENT derived_from.
    seed_b = log.observe(sub, Q.CLEF_SEED, "bass", reader=READERS.DOSSIER,
                         frame="page", tier="dossier",
                         derived_from=(roster.id,))
    seed_a = log.observe(sub, Q.CLEF_SEED, "alto", reader=READERS.DOSSIER,
                         frame="page", tier="dossier",
                         derived_from=(dossier.id,))

    key_b = (seed_b.reader, seed_b.frame, seed_b.quantity)
    key_a = (seed_a.reader, seed_a.frame, seed_a.quantity)
    print(f"bucket key seed_b : {key_b}")
    print(f"bucket key seed_a : {key_a}")
    print(f"SAME BUCKET       : {key_a == key_b}")
    print(f"closure(seed_b)   : {sorted(log.closure(seed_b.id))}")
    print(f"closure(seed_a)   : {sorted(log.closure(seed_a.id))}")

    verdict = log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=Q.INSTRUMENT,
        outcome=Outcome.DECIDED, value={"name": "Viola"}, decider="identity",
        reason="r", considered=(dossier.id,), basis=(dossier.id,)))

    one_a = _one_signal(log, verdict, seed_a)
    one_b = _one_signal(log, verdict, seed_b)
    print()
    print(f"_one_signal(verdict, seed_a) = {one_a}   "
          f"(both rest on the dossier row)")
    print(f"_one_signal(verdict, seed_b) = {one_b}   "
          f"(seed_b rests on the roster row instead)")
    print()
    if one_a != one_b:
        print(">>> THE BUCKET MEMBERS DISAGREE. `seed_b` was filed FIRST, so it")
        print(">>> is bucket[0]; a representative-only test asks it, gets False,")
        print(">>> and leaves the verdict out of a group it demonstrably belongs")
        print(">>> in. The answer would turn on INSERTION ORDER, not evidence.")
        return 0
    print(">>> members agree -- the counter-example did not reproduce")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
