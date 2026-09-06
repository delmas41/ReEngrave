"""The whole-work sweep, from an identity-only run.

`identity_only.py` produces no staff dicts, so the emitted name of each staff is
not in the file — but every slot's name and provenance IS, and a staff's name is
its slot's name. That covers every instrument this bug is about: on Beethoven 5
fifteen of seventeen slots are `label`-sourced, including all three trombones,
the piccolo and the contrabassoon.

Reported per window, for both rules:

  IMPOSSIBLE   staves before the finale named Piccolo / Contrabassoon /
               Trombone. The reference encodings' part lists say movements 1-3
               contain none of the three, so any such name is categorically
               wrong whatever the page prints. This is the BENEFIT.
  OTHER        vetoes on any other name. Not all of these are wrong — a veto is
               a refusal to assert, and on an unanchored staff whose instrument
               is genuinely absent from the region it is right — but every one
               of them is a name the run used to give and now does not, so it is
               the honest upper bound on the COST.

Usage:  sweep_identity.py IDENTITY.json [--max-window=45]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.omr.absent_instrument import (DEFAULT_WINDOW,      # noqa: E402
                                         find_vetoes)

FINALE_ONLY = {"Piccolo", "Contrabassoon", "Trombone"}
FINALE_FIRST_PAGE = 44


def load(path):
    r = json.load(open(path))
    b = (r.get("contextual") or {}).get("absent_instrument_veto")
    if not b:
        raise SystemExit("REFUSING: no report block")
    ev = {}
    for e in b["label_evidence"]:
        ev.setdefault(e["page_index"], {})[e["staff_index"]] = e["instrument"]
    sbs = {(s["page_index"], s["system_index"], s["staff_index"]): s["slot"]
           for s in b["staff_slots"]}
    nm = {s["slot"]: s["instrument"] for s in b["slot_instruments"]}
    src = {s["slot"]: s["source"] for s in b["slot_instruments"]}
    return r, ev, sbs, nm, src, len((r.get("contextual") or {}).get("reference") or [])


def main(path, max_window=45):
    r, ev, sbs, nm, src, refn = load(path)
    pages = {p for p, _, _ in sbs}
    print(f"=== {Path(path).name}")
    print(f"INPUT ASSERTION: pages={len(pages)} staff-records={len(sbs)} "
          f"labelled-staves={sum(len(v) for v in ev.values())} "
          f"slots={len(nm)} reference_size={refn}")
    if not sbs:
        raise SystemExit("REFUSING: no staff records")

    named = [(p, s, i, nm.get(sbs[(p, s, i)])) for (p, s, i) in sbs]
    base_bad = [t for t in named
                if t[0] < FINALE_FIRST_PAGE and t[3] in FINALE_ONLY]
    before = [t for t in named if t[0] < FINALE_FIRST_PAGE]
    print(f"staves before the finale (page < {FINALE_FIRST_PAGE}): {len(before)}")
    print(f"BASELINE named a finale-only instrument   : {len(base_bad)} "
          f"({len(base_bad) / len(before):.4f})")
    for k, v in collections.Counter(t[3] for t in base_bad).most_common():
        print(f"    {v:4d}  {k}")
    print(f"  on pages: {sorted({t[0] for t in base_bad})}")

    att = collections.defaultdict(set)
    for p, by in ev.items():
        for x in by.values():
            att[x].add(p)
    print()
    print("attestation span per instrument:")
    for x in sorted(att):
        ps = sorted(att[x])
        gaps = [b - a for a, b in zip(ps, ps[1:])] or [0]
        print(f"  {x:16s} n={len(ps):3d}  span=[{ps[0]:3d},{ps[-1]:3d}]  "
              f"biggest internal gap={max(gaps):3d}")

    for rule in ("window", "span"):
        print()
        print(f"--- rule = {rule}")
        print(f"{'W':>4} {'vetoes':>7} {'impossible-left':>16} "
              f"{'impossible-cut':>15} {'other-cut':>10}")
        prev = None
        for w in range(0, max_window + 1):
            vs = find_vetoes(staff_keys=list(sbs), slot_by_staff=sbs,
                             instrument_name_by_slot=nm, instrument_source=src,
                             evidence=ev, window=w, rule=rule,
                             reference_size=refn)
            killed = {(v["page_index"], v["system_index"], v["staff_index"])
                      for v in vs}
            left = sum(1 for t in base_bad if (t[0], t[1], t[2]) not in killed)
            cut_bad = len(base_bad) - left
            row = (len(vs), left, cut_bad, len(vs) - cut_bad)
            mark = "" if row == prev else "  <-"
            print(f"{w:4d} {row[0]:7d} {row[1]:16d} {row[2]:15d} "
                  f"{row[3]:10d}{mark}")
            prev = row

    print()
    print(f"--- at the shipped default (span, W={DEFAULT_WINDOW}): "
          "what the OTHER vetoes are")
    vs = find_vetoes(staff_keys=list(sbs), slot_by_staff=sbs,
                     instrument_name_by_slot=nm, instrument_source=src,
                     evidence=ev, window=DEFAULT_WINDOW, rule="span",
                     reference_size=refn)
    other = [v for v in vs if not (v["page_index"] < FINALE_FIRST_PAGE
                                   and v["instrument"] in FINALE_ONLY)]
    for k, v in collections.Counter(
            (x["instrument"],
             "before finale" if x["page_index"] < FINALE_FIRST_PAGE
             else "finale") for x in other).most_common():
        print(f"  {v:5d}  {k[0]:16s} {k[1]}")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mw = 45
    for a in sys.argv[1:]:
        if a.startswith("--max-window="):
            mw = int(a.split("=", 1)[1])
    raise SystemExit(main(args[0], mw))
