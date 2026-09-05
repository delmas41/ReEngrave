#!/usr/bin/env python3
"""Relational context nothing reads yet — measured for COVERAGE first.

MEASUREMENT ONLY.

Three page-derived, relational signals. None is a prior: each is read off THIS
page's own staves, not from a population tendency about what pages usually hold.

  A. BRACKET CO-MEMBERSHIP -- `Staff.group_index`.
  B. KEY SIGNATURE AS A COMPARISON -- not "what key does this staff print" but
     "does it print a DIFFERENT key from its neighbour".
  C. REST/ENTRY CO-BEHAVIOUR -- which staves are silent together in a measure.

⚠️ COVERAGE BEFORE PRECISION, because coverage is what killed the last attempt.
S3 (key-signature transposition as an ABSOLUTE identity signal) was refused for
speaking on 2 of 36 brass staves: natural horns and trumpets print NO key
signature, so an absolute reading has nothing to read. A COMPARISON has
different coverage from a reading — it needs the NEIGHBOURS to print, not the
staff itself, and a transposing staff beside a concert-pitch neighbour is a
DIFFERENCE. Whether that actually buys coverage is an empirical question and
this probe answers it rather than assuming it in either direction.

⚠️ `group_index` IS NOT SERIALISED into the transcription fixtures — it lives
on the `Staff` dataclass, not the staff dict. This probe reports its
availability as measured (expected: absent) rather than silently scoring zero,
because "the signal is absent from the fixture" and "the signal is uninformative"
are different findings and only one of them is about music.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_relational_context.py

── COVERAGE RESULT 2026-09-05 ────────────────────────────────────────────────
31 systems, 396 staves, 20-row `.reconciliation` gate.

A. BRACKET CO-MEMBERSHIP    0 / 396 = 0.000 — ABSENT FROM THE FIXTURES.
   A serialisation gap, not a fact about music. No bracket tier can be measured
   on the committed gate until `group_index` is emitted into the staff dict.

B. KEY SIGNATURE AS A COMPARISON — THE COVERAGE REALLY IS DIFFERENT, AND BETTER
       staves printing their OWN signature (the S3 reading)   194/396 = 0.490
       staves with >=1 NEIGHBOUR printing one (comparison)    263/396 = 0.664
     ⭑ printing NOTHING but with a printing neighbour          98/396 = 0.247
       adjacent pairs where both print                         108
       ...of which they DIFFER                                  48   (0.444)

   The comparison reaches 1.36x the staves the reading does, and the 98-staff
   gap between them IS the population that starved S3: a natural horn or
   trumpet prints no signature, so an absolute reading has nothing to read
   there, while a comparison only needs the NEIGHBOUR to print. A quarter of
   every staff on the gate falls in that gap.

   ⚠️ BUT THE INFORMATIVE CEILING IS THE 48 DIFFERING PAIRS (48/396 = 0.121),
   not the 263. A difference says something only where it occurs; two staves
   agreeing on 2 flats separates nothing. So this is a real but modest signal —
   materially better than S3's 2-of-36 brass, and not a general-purpose namer.
   Precision is UNMEASURED and is the next question if it is pursued.

C. REST CO-BEHAVIOUR   1597 staff-measures carry no notehead — ample raw
   material for "who rests together"; no structure extracted yet.

⚠️ The 194/396 own-signature figure independently reproduces the coverage a
previous session in this area missed by reading a `fifths` key the fixtures do
not carry (they hold `sharps`/`flats`/`alterations`) and reporting a clean
negative from an empty input.
"""
from __future__ import annotations

import glob
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

FIXTURES = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
            "reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures")
TAG = ".reconciliation"


def keysig_of(staff):
    """The staff's OWN printed key signature, as (sharps, flats), or None.

    ⚠️ The fixtures carry `sharps`/`flats`/`alterations` — NOT `fifths`. A
    previous session in this area read a `fifths` key the fixtures do not have,
    got an empty result, and reported a clean negative from an empty input.
    Asserted here by counting what was actually found.
    """
    ks = staff.get("key_signature")
    if not isinstance(ks, dict):
        return None
    if not staff.get("key_signature_read"):
        return None
    s, f = ks.get("sharps"), ks.get("flats")
    if s is None and f is None:
        return None
    return (s or 0, f or 0)


def main():
    paths = sorted(glob.glob(f"{FIXTURES}/*{TAG}.omr.json"))
    print(f"FIXTURES {FIXTURES}\nTAG {TAG!r}  rows {len(paths)}")
    if len(paths) != 20:
        raise SystemExit(f"expected the 20-row gate, found {len(paths)}")

    n_staves = 0
    have_group = 0
    have_ks = 0
    ks_pairs = 0            # adjacent pairs where BOTH print a signature
    ks_diff = 0             # ...and they DIFFER
    ks_any_neighbour = 0    # staves with >=1 adjacent staff printing a signature
    rest_measures = 0
    systems = 0
    for p in paths:
        for page in json.loads(Path(p).read_text()).get("pages", []):
            for sysd in page.get("systems", []):
                systems += 1
                staves = sorted(
                    sysd.get("staves", []),
                    key=lambda s: (s.get("staff_geometry") or {})
                    .get("line_ys_page", [0])[0])
                n = len(staves)
                n_staves += n
                have_group += sum(1 for s in staves
                                  if s.get("group_index") is not None)
                ks = [keysig_of(s) for s in staves]
                have_ks += sum(1 for k in ks if k is not None)
                for i in range(n - 1):
                    if ks[i] is not None and ks[i + 1] is not None:
                        ks_pairs += 1
                        if ks[i] != ks[i + 1]:
                            ks_diff += 1
                for i in range(n):
                    nb = [ks[j] for j in (i - 1, i + 1) if 0 <= j < n]
                    if any(x is not None for x in nb):
                        ks_any_neighbour += 1
                        # THE S3 RESCUE POPULATION: this staff prints NO
                        # signature of its own -- the natural horn / trumpet
                        # case that starved the absolute reading -- but a
                        # neighbour does, so a COMPARISON has something to say
                        # where a READING has nothing.
                        if ks[i] is None:
                            globals()["ks_silent_with_speaking_nb"] = \
                                globals().get("ks_silent_with_speaking_nb", 0) + 1
                for s in staves:
                    rest_measures += sum(
                        1 for m in s.get("measures", [])
                        if not any(d.get("category") == "notehead"
                                   for d in m.get("detections", [])))

    print(f"\nINPUT AUDIT   systems {systems}   staves {n_staves}")
    if not n_staves:
        raise SystemExit("REFUSING to report: no staves read.")

    print(f"\nA. BRACKET CO-MEMBERSHIP (`group_index`)")
    print(f"   staves carrying it in the fixture: {have_group} / {n_staves}"
          f"  = {have_group/n_staves:.3f}")
    if not have_group:
        print("   ⚠️ ABSENT FROM THE FIXTURES, as predicted. This is a"
              " SERIALISATION gap, not a\n      measurement about music:"
              " `group_index` is on the Staff dataclass and never"
              "\n      reaches the staff dict. Emitting it is the named"
              " prerequisite for any\n      bracket-based tier, and no"
              " coverage or precision figure for bracket\n      co-membership"
              " can be produced on the committed gate until it is.")

    print(f"\nB. KEY SIGNATURE AS A COMPARISON  (what starved S3 was COVERAGE)")
    print(f"   staves printing their OWN signature (the S3 reading): "
          f"{have_ks} / {n_staves} = {have_ks/n_staves:.3f}")
    print(f"   staves with >=1 NEIGHBOUR printing one (the comparison): "
          f"{ks_any_neighbour} / {n_staves} = {ks_any_neighbour/n_staves:.3f}")
    rescue = globals().get("ks_silent_with_speaking_nb", 0)
    print(f"   ⭑ staves printing NOTHING themselves but with a printing "
          f"neighbour:\n     {rescue} / {n_staves} = {rescue/n_staves:.3f}"
          f"   — THE S3 RESCUE POPULATION (natural horns and\n     trumpets"
          f" print no signature; an absolute reading has nothing to read there,"
          f"\n     a comparison has a neighbour to read)")
    print(f"   adjacent pairs where BOTH print: {ks_pairs}"
          f"   of which they DIFFER: {ks_diff}"
          f"  ({ks_diff/ks_pairs if ks_pairs else 0:.3f})")
    print(f"\n   A difference is only informative where it OCCURS, so the"
          f" ceiling on this\n   signal is the {ks_diff} differing pairs, not"
          f" the {ks_pairs} readable ones.")

    print(f"\nC. REST CO-BEHAVIOUR")
    print(f"   staff-measures with no notehead: {rest_measures}"
          f"   (the raw material for 'who rests together')")
    print(f"\n⚠️ COVERAGE ONLY. Nothing here is scored against identity truth;"
          f" a signal that\n   cannot reach most staves cannot be worth"
          f" precision-testing, and that is the\n   question this probe"
          f" exists to settle first.")


if __name__ == "__main__":
    main()
