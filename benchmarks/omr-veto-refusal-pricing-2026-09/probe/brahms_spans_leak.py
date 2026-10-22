"""⚠️ On the SECOND work, spans do not fix what they stop the veto refusing.

Six staves are vetoed with spans off and not with spans on. On Beethoven 5 that
transition was the good one — spans re-NAMED all 91, correctly. Here it is not:
this prints, for every pre-finale staff that carries no label of its own, the
name each arm gives it and the label on the staff directly above, which is what
identifies the second-horn position.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINALE_FIRST_PAGE = 45
#: Trombone and Tuba enter in the finale; a pre-finale staff carrying either
#: name is categorically wrong. Trumpet is not impossible — Brahms 1 has
#: trumpets throughout — so it is reported separately.
FINALE_ONLY = {"Trombone", "Tuba"}


def load(tag):
    return json.loads((ROOT / "out" / "brahms1" / f"{tag}.json").read_text()
                      )["contextual"]["absent_instrument_veto"]


def arm(blob):
    return (
        {(s["page_index"], s["system_index"], s["staff_index"]): s["slot"]
         for s in blob["staff_slots"]},
        {s["slot"]: s["instrument"] for s in blob["slot_instruments"]},
        {(v["page_index"], v["system_index"], v["staff_index"])
         for v in blob["vetoes"]},
    )


def main() -> None:
    on, off = load("spans-on"), load("spans-off")
    ev = collections.defaultdict(dict)
    for e in on["label_evidence"]:
        ev[e["page_index"]][e["staff_index"]] = e["instrument"]
    on_slot, on_name, on_vet = arm(on)
    off_slot, off_name, off_vet = arm(off)
    by_system = collections.defaultdict(list)
    for (p, sy, st) in on_slot:
        by_system[(p, sy)].append(st)

    def emitted(slot_map, name_map, vet, key):
        if key in vet:
            return None
        slot = slot_map.get(key)
        return name_map.get(slot) if slot is not None and slot >= 0 else None

    src = {b["slot"]: b["source"] for b in on["slot_instruments"]}
    off_src = {b["slot"]: b["source"] for b in off["slot_instruments"]}
    print("pre-finale staves named a FINALE-ONLY instrument, per 2x2 cell")
    print("(⚠️ Brahms 1 has NO tuba at all — `Tuba` is the score-order prior's "
          "name for the second trombone staff, and is outside VETOABLE_SOURCES "
          "everywhere, so it is broken out.)")
    for veto_on in (False, True):
        for tag, (sm, nm, vt, sr) in (
                ("spans-off", (off_slot, off_name, off_vet, off_src)),
                ("spans-on", (on_slot, on_name, on_vet, src))):
            per = collections.Counter()
            for key in sm:
                if key[0] >= FINALE_FIRST_PAGE:
                    continue
                got = emitted(sm, nm, vt if veto_on else set(), key)
                if got in FINALE_ONLY:
                    per[(got, sr.get(sm[key]))] += 1
            print(f"  {tag:<10} veto {'on ' if veto_on else 'off'} : "
                  f"{sum(per.values()):3d}   " +
                  ", ".join(f"{n}x {k[0]}({k[1]})"
                            for k, n in sorted(per.items())))

    print()
    print("the six the veto stops refusing once spans are on:")
    for key in sorted(off_vet - on_vet):
        p, sy, st = key
        order = sorted(by_system[(p, sy)])
        above = ev[p].get(order[order.index(st) - 1])
        print(f"  p{p:02d} sy{sy} st{st:2d}  spans-off {off_name.get(off_slot[key])!r}"
              f" -> spans-on {on_name.get(on_slot[key])!r}"
              f"   (staff above is labelled {above!r})")
    print()
    print("⚠️ Trumpet is not impossible in Brahms 1 — the work has trumpets "
          "throughout — so the rename is invisible to an `impossible` count. "
          "The staff-above label is what says it is still wrong.")


if __name__ == "__main__":
    main()
