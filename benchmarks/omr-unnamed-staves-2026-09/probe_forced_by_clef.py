"""Can ORDER + CLEF force a slot for a staff the margin never named?

THE RULE UNDER TEST, stated before it is scored:

  A short system's staves map to the reference lineup's slots in strictly
  increasing order -- a printed score may omit a tacet part, it may never
  reorder one. The staves the margin DID name are already pinned by
  `_forced_pairing`. So every unnamed staff's slot is constrained by its
  named neighbours above and below; and where the record has read its CLEF,
  it is constrained again, because a slot whose own staff on the REFERENCE
  system reads a different clef cannot be this staff.

  Enumerate every assignment satisfying both. A staff takes a slot only where
  EVERY surviving assignment gives it that same slot -- "place only what is
  forced", which is `_forced_pairing`'s own discipline, extended with one
  more constraint rather than replaced by a score.

⚠️ THE CLEF OF A SLOT COMES FROM THE DOCUMENT'S OWN REFERENCE SYSTEM, never
from a table of what instruments are conventionally written in. That makes
this CONTINUITY -- the page answering a question about itself -- and it is
also why the scoring below may not use the same source: `table.PRINTED_CLEF`
is used ONLY to score, never as rule input, or the rule would be graded
against its own evidence.

⚠️ SCORING USES THE ESTABLISHED CLASSIFIER, not a new one. A printed staff
CONDENSES the slot it is given iff the slot's name is one of the ` e `
-separated parts the staff prints (`Violoncello e Basso` given slot
`Violoncello`). That test is `slot_arm.classify`'s, reproduced here because
importing it would drag a record loader in; the 2026-09-15 findings record
what a looser test cost -- `Violino II`.startswith(`Violino I`) read a graft
as a condensation.
"""
import itertools
import json
import sys
from typing import Dict, List, Optional, Sequence, Tuple

import table

MAX_ENUM = 200000  # a system this ambiguous is a "cannot tell", not a slow one


def classify(printed: Optional[str], slot_name: Optional[str]) -> str:
    """`ok` | `condensation` | `graft`, the 2026-09-15 membership test."""
    if printed is None or slot_name is None:
        return "unknown"
    if printed == slot_name:
        return "ok"
    parts = [p.strip() for p in printed.split(" e ")]
    if len(parts) > 1 and slot_name in parts:
        return "condensation"
    return "graft"


def assignments(n_staves: int, pinned: Dict[int, int], n_slots: int,
                allowed: Dict[int, Optional[set]]) -> List[Tuple[int, ...]]:
    """Every strictly-increasing staff->slot map honouring pins and clefs.

    `allowed[ordinal]` is the set of slots the clef permits, or None where the
    clef abstained -- and None means "every slot", never "no slot": an absent
    reading must widen the candidate set, not empty it.
    """
    out: List[Tuple[int, ...]] = []

    def walk(ordinal: int, lo: int, acc: List[int]) -> None:
        if len(out) > MAX_ENUM:
            return
        if ordinal == n_staves:
            out.append(tuple(acc))
            return
        # the suffix must still fit: leave room for the staves after this one
        hi = n_slots - (n_staves - ordinal)
        for slot in range(lo, hi + 1):
            if ordinal in pinned and pinned[ordinal] != slot:
                continue
            ok = allowed.get(ordinal)
            if ok is not None and slot not in ok:
                continue
            acc.append(slot)
            walk(ordinal + 1, slot + 1, acc)
            acc.pop()

    walk(0, 0, [])
    return out


def main() -> int:
    staves, printed_lineups, _ = table.load()
    ref_names = table.reference_lineup()
    n_slots = len(ref_names)

    # ── the reference system's OWN clef readings: the rule's only clef input
    ref = sorted([s for s in staves if s.sys_key == (1, 0)],
                 key=lambda s: s.ordinal)
    slot_clef: Dict[int, Optional[str]] = {s.ordinal: s.clef for s in ref}
    print("=" * 74)
    print("THE RULE'S CLEF INPUT -- the reference system's own readings")
    print("=" * 74)
    for i, name in enumerate(ref_names):
        print("   slot %2d  %-22s clef read as %s" % (i, name, slot_clef.get(i)))
    if all(v is None for v in slot_clef.values()):
        print("DEAD: the reference read no clef at all", file=sys.stderr)
        return 2

    totals = {"forced": 0, "ambiguous": 0, "no_solution": 0}
    verdict = {"ok": 0, "condensation": 0, "graft": 0, "unknown": 0}
    rows = []

    print()
    print("=" * 74)
    print("PER SYSTEM")
    print("=" * 74)
    for key in sorted(printed_lineups):
        grp = sorted([s for s in staves if s.sys_key == key],
                     key=lambda s: s.ordinal)
        unnamed = [s for s in grp if not s.named]
        if not unnamed:
            continue
        pinned = {s.ordinal: s.slot for s in grp if s.slot is not None}
        allowed: Dict[int, Optional[set]] = {}
        for s in grp:
            if s.named or s.clef is None:
                allowed[s.ordinal] = None
            else:
                allowed[s.ordinal] = {i for i, c in slot_clef.items()
                                      if c == s.clef}
        sols = assignments(len(grp), pinned, n_slots, allowed)
        print()
        print("--- p%d/s%d  %d staves, %d named, %d unnamed  -> %d assignment(s)"
              % (key[0], key[1], len(grp), len(grp) - len(unnamed),
                 len(unnamed), len(sols)))
        if not sols:
            totals["no_solution"] += len(unnamed)
            print("    NO SOLUTION -- the constraints are unsatisfiable here")
            for s in unnamed:
                rows.append((s, None, "no_solution"))
            continue
        for s in unnamed:
            got = {sol[s.ordinal] for sol in sols}
            if len(got) == 1:
                slot = got.pop()
                name = ref_names[slot]
                cls = classify(s.printed, name)
                totals["forced"] += 1
                verdict[cls] += 1
                rows.append((s, slot, cls))
                flag = "  <-- GRAFT" if cls == "graft" else ""
                print("    FORCED   st%-2d printed=%-20s clef=%-7s -> slot %2d "
                      "%-14s [%s]%s"
                      % (s.ordinal, s.printed, s.clef, slot, name, cls, flag))
            else:
                totals["ambiguous"] += 1
                rows.append((s, None, "ambiguous"))
                cands = sorted(got)
                print("    abstain  st%-2d printed=%-20s clef=%-7s -> %s"
                      % (s.ordinal, s.printed, s.clef,
                         [(i, ref_names[i]) for i in cands]))

    print()
    print("=" * 74)
    print("RESULT on the 25 unnamed staves")
    print("=" * 74)
    print("   FORCED (a slot is named)   %d" % totals["forced"])
    print("   abstained (ambiguous)      %d" % totals["ambiguous"])
    print("   abstained (no solution)    %d" % totals["no_solution"])
    print()
    print("   of the forced:")
    print("      correct                 %d" % verdict["ok"])
    print("      condensation            %d" % verdict["condensation"])
    print("      ** GRAFTS **            %d" % verdict["graft"])
    print("      unknown                 %d" % verdict["unknown"])

    out = table.HERE / "out" / "forced-by-clef.json"
    out.write_text(json.dumps(
        {"totals": totals, "verdict": verdict,
         "rows": [{"subject": s.subject, "printed": s.printed,
                   "clef": s.clef, "slot": slot, "class": cls}
                  for s, slot, cls in rows]}, indent=1))
    print()
    print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
