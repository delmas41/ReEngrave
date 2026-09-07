"""What is the BEST a span rule could do, given the names the reference holds?

A slot carries one name for the whole document (`slot_instruments`), and a
system of N staves aligned into an N-slot reference has exactly ONE
order-preserving placement — the identity. So for every FULL system the score
is fixed the moment the reference is chosen, and no arrangement of spans can
move it: spans decide which slot a staff takes, never what that slot is called.

This prints, per region, the ceiling under

  * the reference the run actually built (read out of the arm's own blob), and
  * the counterfactual where each OTHER region's lineup had been the reference,

so "the segmentation has nothing left to give" is a number rather than a claim.

    ceiling.py ARM.json --lineups LINEUPS.json
"""
from __future__ import annotations

import argparse
import json


def score(staff_names, slot_names):
    """Correct names for one full system placed into an equal-size reference.

    ⚠️ Equal sizes force the identity placement, which is the whole point: the
    ceiling is a property of the reference's VOCABULARY, not of the aligner.
    """
    return sum(1 for a, b in zip(staff_names, slot_names) if a == b)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arm")
    ap.add_argument("--lineups", required=True)
    args = ap.parse_args()

    b = json.load(open(args.arm))["contextual"]["absent_instrument_veto"]
    ref = [s["instrument"] for s in sorted(b["slot_instruments"],
                                           key=lambda s: s["slot"])]
    lineups = json.load(open(args.lineups))

    counts = {}
    per_page: dict[int, dict[int, int]] = {}
    for s in b["staff_slots"]:
        per_page.setdefault(s["page_index"], {}).setdefault(
            s["system_index"], 0)
        per_page[s["page_index"]][s["system_index"]] += 1
    for row in lineups:
        counts[id(row)] = sum(
            1 for p, sys_ in per_page.items() if row["first"] <= p <= row["last"]
            for n in sys_.values() if n == row["size"])

    print(f"reference the run built: {len(ref)} slots\n  {ref}\n")
    print(f"{'region':16s}{'systems':>8s}{'size':>6s}"
          f"{'ceiling/sys':>13s}{'ceiling':>10s}"
          "   counterfactual ceilings (reference = each other region)")
    for row in lineups:
        n = counts[id(row)]
        cap = (score(row["lineup"], ref)
               if len(ref) == row["size"] else None)
        alt = []
        for other in lineups:
            if other is row or len(other["lineup"]) != row["size"]:
                continue
            alt.append(f"{other['first']}-{other['last']}:"
                       f"{score(row['lineup'], other['lineup'])}")
        capstr = f"{cap}" if cap is not None else "n/a"
        total = f"{cap * n}" if cap is not None else "n/a"
        print(f"{str(row['first']) + '-' + str(row['last']):16s}{n:8d}"
              f"{row['size']:6d}{capstr:>13s}{total:>10s}   "
              + ", ".join(alt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
