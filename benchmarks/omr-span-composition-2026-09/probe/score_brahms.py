"""Brahms 1 / Breitkopf: pre-finale staves named an instrument the work has not
got yet, per 2x2 cell, for as many `OMR_SPAN_REFERENCE_FIT` arms as you pass.

The counting rule is copied verbatim from the veto-pricing session's
`brahms_spans_leak.py` so the numbers are comparable to the 36 / 14 / 149 / 133
it recorded — `Trombone` and `Tuba` before page 45, `Tuba` broken out because
Brahms 1 has no tuba at all and the name comes from the score-order prior, which
is outside `VETOABLE_SOURCES` everywhere.

It also counts the SELF-CONTRADICTION the same session reported and did not
build: a staff whose own margin label was read, and which is exported as
something else. That is free evidence, it needs no truth file, and on this work
it is the sharper number — 132 of the 149.

Usage: score_brahms.py TAG=DIR/prefix ...   (prefix minus `-spans-{off,on}.json`)
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

FINALE_FIRST_PAGE = 45
FINALE_ONLY = {"Trombone", "Tuba"}


def load(prefix, which):
    p = Path(f"{prefix}-spans-{which}.json")
    if not p.exists():
        raise SystemExit(f"REFUSING: {p} does not exist")
    return json.loads(p.read_text())["contextual"]["absent_instrument_veto"]


def arm(blob):
    slot = {(s["page_index"], s["system_index"], s["staff_index"]): s["slot"]
            for s in blob["staff_slots"]}
    name = {s["slot"]: s["instrument"] for s in blob["slot_instruments"]}
    src = {s["slot"]: s["source"] for s in blob["slot_instruments"]}
    vet = {(v["page_index"], v["system_index"], v["staff_index"])
           for v in blob["vetoes"]}
    ev = collections.defaultdict(dict)
    for e in blob["label_evidence"]:
        ev[e["page_index"]][e["staff_index"]] = e["instrument"]
    return slot, name, src, vet, ev


def emitted(slot, name, vet, key, veto_on):
    if veto_on and key in vet:
        return None
    s = slot.get(key)
    return name.get(s) if s is not None and s >= 0 else None


def cell(blob, veto_on):
    slot, name, src, vet, ev = arm(blob)
    bad = collections.Counter()
    contra = collections.Counter()
    n_bad = n_contra = 0
    for key in slot:
        p, _sy, st = key
        nm = emitted(slot, name, vet, key, veto_on)
        if p < FINALE_FIRST_PAGE and nm in FINALE_ONLY:
            n_bad += 1
            bad[f"{nm}({src.get(slot[key])})"] += 1
        own = ev.get(p, {}).get(st)
        if own and nm and own != nm:
            n_contra += 1
            contra[f"{own}->{nm}"] += 1
    return n_bad, bad, n_contra, contra, len(slot)


def main():
    args = [a.split("=", 1) for a in sys.argv[1:]]
    if not args:
        raise SystemExit(__doc__)
    print(f"{'arm':22s} {'spans':6s} {'veto':5s} {'IMPOSSIBLE':>11s} "
          f"{'self-contradicting':>19s}   detail")
    keys_seen = None
    for tag, prefix in args:
        for which in ("off", "on"):
            blob = load(prefix, which)
            for veto_on in (False, True):
                nb, bad, nc, contra, total = cell(blob, veto_on)
                if keys_seen is None:
                    keys_seen = total
                elif total != keys_seen:
                    print(f"  ⚠️ staff-record count {total} != {keys_seen} — "
                          f"the arms did not share a read pass")
                print(f"{tag:22s} {which:6s} {'on' if veto_on else 'off':5s} "
                      f"{nb:11d} {nc:19d}   "
                      f"{', '.join(f'{v}x {k}' for k, v in bad.most_common())}")
        print()
    print(f"staff records per arm: {keys_seen}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
