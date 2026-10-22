"""Adjudicate the second work's 16 residual refusals — categorically, then by hand.

Two independent readings, and they agree:

CATEGORICAL.  Brahms 1's trombones enter in the FINALE.  This edition's finale
opens on PDF page 45 (`out/brahms1/page045_full.png`: the Adagio, full
instrument names down the margin, `3 Posaunen` labelled — and page 44 is the
last page of the third movement, in four flats).  It is also the first page in
the whole document on which the run reads a Trombone label.  So a staff named
`Trombone` on a page BEFORE 45 cannot be right whatever it is — the same
categorical argument `score_2x2.FINALE_ONLY` makes for Beethoven.  All 16
refusals are on pages 6-44.

BY HAND.  Every refusal lands on the staff DIRECTLY BELOW a staff the reader
labelled Horn — the second horn staff, whose only margin text is a crook
(`(C)`, `(Es)`, `(H)`, `(E)`), all four of which the run reports as read and
NOT matched by the lexicon.  Unlabelled, it takes slot 8 (Trombone).  Verified
on the print for p22 (both systems) and p44.

This asserts the positional claim over all 16 rather than trusting the sample.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINALE_FIRST_PAGE = 45


def load(tag):
    return json.loads((ROOT / "out" / "brahms1" / f"{tag}.json").read_text()
                      )["contextual"]["absent_instrument_veto"]


def main() -> int:
    on, off = load("spans-on"), load("spans-off")
    ev = collections.defaultdict(dict)
    for e in on["label_evidence"]:
        ev[e["page_index"]][e["staff_index"]] = e["instrument"]
    name_by_slot = {s["slot"]: s["instrument"] for s in on["slot_instruments"]}
    slot_by_staff = {(s["page_index"], s["system_index"], s["staff_index"]):
                     s["slot"] for s in on["staff_slots"]}
    by_system = collections.defaultdict(list)
    for (p, sy, st) in slot_by_staff:
        by_system[(p, sy)].append(st)

    rows = sorted(on["vetoes"], key=lambda r: (r["page_index"],
                                               r["system_index"],
                                               r["staff_index"]))
    bad = 0
    print("| page | sys | staff | refused | staff above (label) | verdict |")
    print("|---|---|---|---|---|---|")
    for v in rows:
        p, sy, st = v["page_index"], v["system_index"], v["staff_index"]
        order = sorted(by_system[(p, sy)])
        pos = order.index(st)
        above = ev[p].get(order[pos - 1]) if pos else None
        if p >= FINALE_FIRST_PAGE:
            bad += 1
            verdict = "**NOT CATEGORICAL — in the finale**"
        elif above != "Horn":
            bad += 1
            verdict = f"**position unconfirmed (above = {above})**"
        else:
            verdict = "**benefit**"
        print(f"| {p} | {sy} | {st} | {v['instrument']} | "
              f"{above or '-'} | {verdict} |")

    print()
    print(f"refusals: {len(rows)}   all before the finale (p{FINALE_FIRST_PAGE}): "
          f"{all(v['page_index'] < FINALE_FIRST_PAGE for v in rows)}")
    print(f"rows failing either reading: {bad}")

    # What spans alone did to the 6 the veto no longer has to refuse.
    okeys = {(v["page_index"], v["system_index"], v["staff_index"])
             for v in off["vetoes"]}
    nkeys = {(v["page_index"], v["system_index"], v["staff_index"])
             for v in rows}
    off_slots = {(s["page_index"], s["system_index"], s["staff_index"]):
                 s["slot"] for s in off["staff_slots"]}
    off_names = {s["slot"]: s["instrument"] for s in off["slot_instruments"]}
    print()
    print(f"vetoed with spans OFF but not ON: {len(okeys - nkeys)} — what spans "
          f"renamed them to:")
    for k in sorted(okeys - nkeys):
        print(f"  p{k[0]:02d} sy{k[1]} st{k[2]:2d}  "
              f"{off_names.get(off_slots.get(k), '?')} -> "
              f"{name_by_slot.get(slot_by_staff.get(k), '<unnamed>')}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
