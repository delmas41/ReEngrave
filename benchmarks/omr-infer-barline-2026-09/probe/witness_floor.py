"""What `COLUMN_MIN_INDEPENDENT_WITNESSES` COSTS — the stage's one unmeasured
constant, priced in reach.

⚠️⚠️ THIS PRICES ONE HALF OF THE QUESTION AND SAYS SO. The constant's own
docstring asks for exactly this — *"Do not raise this to buy precision without
measuring what it costs in reach"* — and reach is the half a machine can
answer. **The other half is whether the extra inferences are RIGHT, and that
needs crops and a human.** A survivor count at floor 1 is not an argument for
floor 1.

⚠️ AND THE DIRECTION IS NOT SYMMETRIC. Raising the floor costs reach and buys
nothing this probe can see. LOWERING it to 1 abolishes corroboration
altogether — a single staff's reading becomes an inference about another
staff's note — which is the one thing the stage's whole design rests on not
doing. This probe will happily print that column; printing it is not proposing
it.

What it reports, per rule and per document:

  * survivors at floor 1, 2 (shipped) and 3;
  * the DISTRIBUTION of independent-group counts over the cases that reached
    the floor at all, which is the informative artefact — a mass at exactly 1
    means the refused cases are single-witness and no floor change reaches
    them, while a mass at 2 means the shipped floor is doing the deciding.

    python3 benchmarks/omr-infer-barline-2026-09/probe/witness_floor.py <rec>
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged import inferences as I                     # noqa: E402
from tools.omr.staged.record import Kind                         # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]
                       / "omr-infer-stage-2026-09"))
from reinfer import rebuild                                       # noqa: E402

FLOORS = (1, 2, 3)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json")
    a = ap.parse_args()

    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc
    print(f"record provenance: {doc.get('provenance')}")
    log = rebuild(rec)

    # rule -> floor -> survivors   and   rule -> Counter(n_independent_groups)
    survivors = {"by_column": collections.Counter(),
                 "to_barline": collections.Counter()}
    groups_seen = {"by_column": collections.Counter(),
                   "to_barline": collections.Counter()}

    for system in log.subjects(Kind.SYSTEM):
        for s in I._walk(log, system):
            if s.endpoint_is_unknown:
                continue
            barline = s.runs_to_barline
            name = "to_barline" if barline else "by_column"

            votes, ids = {}, []
            for st2 in s.at_col.get(s.k, {}):
                if st2 == s.staff:
                    continue
                if s.endpoints.get((st2, s.k)) != s.endpoint:
                    continue
                beats, vids = I._event_beats(
                    log, st2, s.cell, system, s.at_col[s.k][st2]["glyphs"])
                if beats is None:
                    continue
                # the meter guard applies to the barline rule only
                if barline and I._witness_is_meter_derived(log, vids):
                    continue
                votes.setdefault(beats, []).extend(vids)
                ids.extend(vids)

            if not votes or len(votes) > 1:
                continue            # unanimity is upstream of the floor
            n = len(I.independent_groups(log, tuple(ids)))
            groups_seen[name][n] += 1

            beats = next(iter(votes))
            match = [c for c in (s.prior.candidates or ())
                     if isinstance(c.value, dict)
                     and c.value.get("beats") is not None
                     and abs(float(c.value["beats"]) - beats) < 1e-9]
            if len(match) != 1:
                continue            # the candidate test is downstream
            for f in FLOORS:
                if n >= f:
                    survivors[name][f] += 1

    print(f"\nshipped floor: COLUMN_MIN_INDEPENDENT_WITNESSES = "
          f"{I.COLUMN_MIN_INDEPENDENT_WITNESSES}")
    print("\n── SURVIVORS BY FLOOR ────────────────────────────────────────")
    print(f"  {'rule':<14}" + "".join(f"{('floor ' + str(f)):>12}"
                                      for f in FLOORS))
    for name in ("by_column", "to_barline"):
        row = "".join(f"{survivors[name][f]:>12d}" for f in FLOORS)
        print(f"  {name:<14}{row}")

    print("\n── INDEPENDENT-GROUP COUNTS, over cases that REACHED the floor ─")
    print("  (unanimous, with at least one witness -- the floor's own domain)")
    for name in ("by_column", "to_barline"):
        d = groups_seen[name]
        tot = sum(d.values())
        line = "  ".join(f"{k}:{v}" for k, v in sorted(d.items()))
        print(f"  {name:<14} n={tot:<5} {line}")

    print("\n⚠️ REACH ONLY. Whether the extra inferences at a lower floor are "
          "RIGHT is not measured here and needs crops.")
    print("⚠️ Floor 1 abolishes corroboration. The column is printed, not "
          "proposed.")

    if a.json:
        Path(a.json).write_text(json.dumps(
            {"shipped_floor": I.COLUMN_MIN_INDEPENDENT_WITNESSES,
             "survivors": {k: dict(v) for k, v in survivors.items()},
             "independent_group_counts":
                 {k: dict(v) for k, v in groups_seen.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
