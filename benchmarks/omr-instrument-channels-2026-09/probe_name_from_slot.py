"""A staff takes the name of its SLOT — two tiers, measured apart.

Sean: *"do the roster naming for those 10 staves."* Opening the plate first
(`out/print/brahms-system-head.png`) changed what the job is: **all three
unnamed reference slots ARE labelled on the page** — `Flöten`, `Hörner in C
1. 2.`, `Kontrabaß` — and the reader lost them to OCR damage, not to a missing
channel. So the rule is measured against a print truth that is now known.

TWO TIERS, and they are different claims:

  A. SIBLING   the slot is DECIDED and some OTHER staff on it has a decided
               instrument. Pure entailment: the slot IS the part, so the two
               staves are the same instrument by the definition of a slot.
  B. LINEUP    no staff on the slot is named anywhere. The canonical layouts
               (`[C82]`) are aligned monotonically against the slots that ARE
               named, and the slot takes the one instrument every voting
               layout offers there -- with the ROSTER narrowing the offer and
               vetoing only at FAMILY level.

⚠️ THE ROSTER MAY NOT VETO AT INSTRUMENT LEVEL, and this document is the proof:
both catalog rosters name **no string instrument at all** while carrying
`string` in their FAMILIES list, because the IMSLP page says "strings"
collectively -- and both are marked `complete: true`. An instrument-level test
would veto the Kontrabaß, which the plate prints.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

import channels                                                    # noqa: E402
from probe_roster_names_a_slot import monotone_fit, candidates_for  # noqa: E402
from tools.omr import score_layouts as SL                           # noqa: E402
from tools.omr.instruments import lookup                            # noqa: E402

#: What the PLATE prints at the reference slots each record could not name.
#: ⚠️ HAND-READ FROM THE 600-DPI RENDER, and committed as a crop beside this
#: file so a later reader can check it rather than trust it.
PRINT_TRUTH = {
    "breitkopf": {0: "Flute", 5: "Horn", 13: "Contrabass"},
    "litolff": {},        # its reference names every slot
}


def main() -> int:
    record = sys.argv[1] if len(sys.argv) > 1 else "breitkopf"
    staves, counts, raw = channels.load(record)
    ref_sys, ref_names, _ = channels.reference(staves, counts)
    roster = next((o["value"] for o in raw["observations"]
                   if o["quantity"] == "roster_entry"), None) or {}
    families = set(roster.get("families") or ())
    instruments = set(roster.get("instruments") or ())

    named_on_slot: Dict[int, set] = collections.defaultdict(set)
    for s in staves:
        if s.slot_outcome == "decided" and s.slot is not None and s.named:
            named_on_slot[int(s.slot)].add(s.instrument)

    population = [s for s in staves
                  if not s.named and s.slot_outcome == "decided"
                  and s.slot is not None]
    print("=" * 78)
    print("A STAFF TAKES THE NAME OF ITS SLOT — record %s  md5 %s"
          % (record, raw["_record_md5"]))
    print("=" * 78)
    print("  staves with a DECIDED slot and NO instrument: %d" % len(population))

    # ── tier A ──────────────────────────────────────────────────────────────
    a = [s for s in population if len(named_on_slot.get(int(s.slot), ())) == 1]
    conflicted = [s for s in population
                  if len(named_on_slot.get(int(s.slot), ())) > 1]
    print()
    print("  TIER A — the slot already has a name from a SIBLING staff")
    print("    reach                         %d" % len(a))
    print("    refused, siblings DISAGREE    %d" % len(conflicted))
    print("    by instrument: %s"
          % dict(collections.Counter(
              sorted(named_on_slot[int(s.slot)])[0] for s in a)))

    # ── tier B ──────────────────────────────────────────────────────────────
    rest = [s for s in population if not named_on_slot.get(int(s.slot))]
    slots = sorted({int(s.slot) for s in rest})
    print()
    print("  TIER B — no staff anywhere names this slot: slots %s (%d staves)"
          % (slots, len(rest)))
    named_ref = {i: n for i, n in enumerate(ref_names) if n}
    ballots: Dict[int, Dict[str, int]] = {i: {} for i in slots}
    voters = []
    for layout in SL.LAYOUTS:
        fit = monotone_fit(named_ref, layout.parts)
        if fit is None:
            continue
        voters.append(layout.name)
        for slot in slots:
            for c in candidates_for(slot, named_ref, fit, layout.parts):
                ballots[slot][c] = ballots[slot].get(c, 0) + 1
    print("    layouts that host this lineup: %s" % (voters or "NONE"))

    forced: Dict[int, str] = {}
    for slot in slots:
        offered = sorted(n for n, v in ballots[slot].items() if v == len(voters))
        # ⚠️ THE ROSTER NARROWS THE LAYOUT'S OFFER. It is a POSITIVE list of
        # what the work is scored for, so an instrument it does not hold is
        # not a candidate -- but only where the roster ENUMERATES that family
        # at all, which is what keeps the string-less roster from vetoing the
        # Kontrabass.
        fams = {n: (lookup(n).instrument.family if lookup(n) else None)
                for n in offered}
        enumerated = {f for n, f in
                      ((i, lookup(i).instrument.family if lookup(i) else None)
                       for i in instruments)}
        kept = [n for n in offered
                if n in instruments or fams[n] not in enumerated]
        # family veto, last
        kept = [n for n in kept
                if not families or fams[n] is None or fams[n] in families]
        truth = PRINT_TRUTH.get(record, {}).get(slot)
        mark = ""
        if len(kept) == 1:
            forced[slot] = kept[0]
            mark = ("  PRINT: %s  %s" % (truth, "OK" if truth == kept[0]
                                         else "** WRONG **")) if truth else ""
            print("    slot %2d  layout offers %-24s roster keeps %-14s FORCED%s"
                  % (slot, offered, kept[0], mark))
        else:
            if truth:
                mark = "  PRINT: %s (missed)" % truth
            print("    slot %2d  layout offers %-24s roster keeps %-14s abstains%s"
                  % (slot, offered, kept or "-", mark))

    reached_b = sum(1 for s in rest if int(s.slot) in forced)
    right = sum(1 for slot, n in forced.items()
                if PRINT_TRUTH.get(record, {}).get(slot) == n)
    wrong = sum(1 for slot, n in forced.items()
                if PRINT_TRUTH.get(record, {}).get(slot) not in (None, n))
    print()
    print("  TIER B reach: %d slots, %d staves   (against the print: %d right, "
          "%d WRONG, %d unscored)"
          % (len(forced), reached_b, right, wrong, len(forced) - right - wrong))
    print()
    print("  TOTAL staves a name would reach: %d of %d"
          % (len(a) + reached_b, len(population)))
    (HERE / "out" / ("name-from-slot-%s.json" % record)).write_text(json.dumps(
        {"record_md5": raw["_record_md5"], "population": len(population),
         "tier_a": len(a), "tier_a_conflicted": len(conflicted),
         "tier_b_slots": {str(k): v for k, v in forced.items()},
         "tier_b_staves": reached_b, "tier_b_right": right,
         "tier_b_wrong": wrong, "voters": voters,
         "ballots": {str(k): v for k, v in ballots.items()}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
