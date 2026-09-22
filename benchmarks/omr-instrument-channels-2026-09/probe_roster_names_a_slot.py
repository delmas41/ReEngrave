"""Can the INSTRUMENTATION LIST name a reference SLOT the page never labelled?

The population is §2 of FINDINGS.md: on Breitkopf **10 of 38 placed staves land
on reference slots 0, 5 and 13**, which the reader itself could not name, so
they are placed and nameless.

THE RULE UNDER TEST, stated before it is scored:

  A score lists its instruments in a fixed family order (`[C82]`), so an
  unnamed reference slot is bounded by its NAMED neighbours' positions in a
  canonical layout. Align the named slots monotonically against each layout;
  an unnamed slot may only be a layout position strictly between its
  neighbours'. Where exactly ONE such position exists, the slot is forced.

  The ROSTER then CORROBORATES, and may only VETO AT FAMILY LEVEL -- never at
  instrument level.

⚠️⚠️ THE FAMILY-ONLY VETO IS NOT A SOFTENING, IT IS THE ONLY SAFE FORM HERE,
and this document proves it: **both catalog rosters name NO STRING INSTRUMENT
AT ALL** -- Brahms 1 holds `Bassoon, Clarinet, Contrabassoon, Flute, Horn,
Oboe, Timpani, Trombone, Trumpet` and carries `string` only in its FAMILIES
list, because the IMSLP page says "strings" collectively. An instrument-level
membership test would therefore veto the Kontrabass, which is certainly right.
`work_roster.decide` already vetoes on family for exactly this reason ("a
parsed roster routinely lacks an instrument the page prints"); that rule is
inherited rather than re-decided.

⚠️ THE PRIOR ART SAYS THIS SHAPE CAN GRAFT, and the difference is the subject.
`benchmarks/omr-slot-index-2026-09` measured that placing unnamed STAVES by
position scores more correct and **grafts 9**. This does not place a staff: the
staff is already placed, by names on either side of it. It asks what a SLOT
between two named slots can be. ⚠️ And `[C82]`'s own recorded exception is a
real ordering deviation (the canonical layout puts Timpani after the
Trombones; Litolff prints it between Trumpets and Trombones), so a layout that
cannot host the named slots monotonically must not vote at all.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

import channels                                                   # noqa: E402
from tools.omr import score_layouts as SL                          # noqa: E402


def monotone_fit(named: Dict[int, str],
                 layout: Sequence[str]) -> Optional[Dict[int, int]]:
    """`{slot -> layout index}` for the named slots, or None if none exists.

    ⚠️ STRICTLY INCREASING, and an EXACT name match -- this is the same claim
    `[C62]` makes about staves, applied to the lineup: a score may omit an
    instrument it is not scored for, it may never reorder the families.
    """
    slots = sorted(named)
    best: Optional[Dict[int, int]] = None

    def walk(i: int, lo: int, acc: Dict[int, int]) -> bool:
        nonlocal best
        if i == len(slots):
            best = dict(acc)
            return True
        for j in range(lo, len(layout)):
            if layout[j] != named[slots[i]]:
                continue
            acc[slots[i]] = j
            if walk(i + 1, j + 1, acc):
                return True
            acc.pop(slots[i])
        return False

    return best if walk(0, 0, {}) else None


def candidates_for(slot: int, named: Dict[int, str], fit: Dict[int, int],
                   layout: Sequence[str]) -> List[str]:
    """Every layout position strictly between this slot's named neighbours.

    ⚠️ A REPEAT OF A NEIGHBOUR IS NOT OFFERED. Two adjacent staves of ONE
    instrument -- Brahms's four horns on two staves -- is a real and common
    engraving, and the canonical layout names each instrument ONCE, so it
    cannot express one. Offering the neighbour's own name here would be this
    rule inventing a doubling the layout never claimed; the slot abstains and
    the count says so.
    """
    above = [s for s in named if s < slot]
    below = [s for s in named if s > slot]
    lo = fit[max(above)] + 1 if above else 0
    hi = fit[min(below)] if below else len(layout)
    return sorted({layout[j] for j in range(lo, hi)})


def main() -> int:
    record = sys.argv[1] if len(sys.argv) > 1 else "breitkopf"
    staves, counts, raw = channels.load(record)
    ref_sys, ref_names, _ = channels.reference(staves, counts)
    roster = next((o["value"] for o in raw["observations"]
                   if o["quantity"] == "roster_entry"), None) or {}
    instruments = set(roster.get("instruments") or ())
    families = set(roster.get("families") or ())

    named = {i: n for i, n in enumerate(ref_names) if n}
    unnamed = [i for i, n in enumerate(ref_names) if not n]
    print("=" * 78)
    print("CAN THE ROSTER NAME A SLOT?   record %s  md5 %s"
          % (record, raw["_record_md5"]))
    print("=" * 78)
    print("  reference p%d/s%d: %s" % (ref_sys[0], ref_sys[1],
                                       [n or "?" for n in ref_names]))
    print("  roster instruments: %s" % sorted(instruments))
    print("  roster families   : %s" % sorted(families))
    print("  UNNAMED reference slots: %s" % unnamed)
    if not unnamed:
        print("DEAD: this record's reference names every slot; no population.",
              file=sys.stderr)
        return 3

    staves_on = {i: sum(1 for s in staves if s.slot == i and not s.named)
                 for i in unnamed}
    print("  staves standing on them (unnamed instrument): %s" % staves_on)

    ballots: Dict[int, Dict[str, int]] = {i: {} for i in unnamed}
    voters: List[str] = []
    print()
    for layout in SL.LAYOUTS:
        fit = monotone_fit(named, layout.parts)
        if fit is None:
            continue
        voters.append(layout.name)
        print("  layout %-22s hosts every named slot" % layout.name)
        for slot in unnamed:
            for c in candidates_for(slot, named, fit, layout.parts):
                ballots[slot][c] = ballots[slot].get(c, 0) + 1

    if not voters:
        print("\n  NO LAYOUT hosts this lineup monotonically -- the rule "
              "abstains on every slot, which is `[C82]`'s own exception "
              "working.")
        return 0

    print()
    print("  RESULT (a slot is FORCED where every voting layout offers exactly "
          "one name, and they agree):")
    forced, refused = {}, {}
    for slot in unnamed:
        names = ballots[slot]
        unanimous = [n for n, v in names.items() if v == len(voters)]
        if len(names) == 1 and unanimous:
            name = unanimous[0]
            fam = SL and None
            from tools.omr.instruments import lookup
            hit = lookup(name)
            fam = hit.instrument.family if hit else None
            vetoed = bool(families) and fam is not None and fam not in families
            if vetoed:
                refused[slot] = (name, "family %r not in the roster" % fam)
                print("    slot %2d  %-14s VETOED: family %r not in roster"
                      % (slot, name, fam))
            else:
                forced[slot] = name
                print("    slot %2d  %-14s FORCED   (family %s, roster names "
                      "the instrument: %s)"
                      % (slot, name, fam, name in instruments))
        else:
            refused[slot] = (None, "candidates %s" % sorted(names))
            print("    slot %2d  abstains -- candidates %s"
                  % (slot, sorted(names) or "none"))

    reached = sum(staves_on[s] for s in forced)
    print()
    print("  SLOTS named %d of %d;  STAVES they would name: %d of %d"
          % (len(forced), len(unnamed), reached, sum(staves_on.values())))
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / ("roster-slot-%s.json" % record)).write_text(json.dumps(
        {"record_md5": raw["_record_md5"], "reference": ref_names,
         "voters": voters, "ballots": {str(k): v for k, v in ballots.items()},
         "forced": {str(k): v for k, v in forced.items()},
         "refused": {str(k): list(v) for k, v in refused.items()},
         "staves_on_slot": {str(k): v for k, v in staves_on.items()},
         "staves_named": reached}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
