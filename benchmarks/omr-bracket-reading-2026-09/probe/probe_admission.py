"""Can the reader tell when it is wrong?

The reader's raw within-page self-consistency is poor.  That is only fatal if
the bad readings are indistinguishable from the good ones — so this asks
whether a STRUCTURAL admission gate, using nothing but the reading's own shape,
separates them.  Same question `benchmarks/omr-prefill-admission-2026-09` asked
of the MusicXML pre-fill, and the same standard: a gate is worth having only if
what it admits is right *and* it still admits enough to matter.

Runs offline over `probe_vs_incumbent.py`'s dump — no rendering.

Gates, each stated before it is scored:

  TILES       the stated blocks form ONE contiguous run of staves (no
              unbracketed staff between two blocks).  A section bracket level
              tiles a stretch of the score; a level of braces over instrument
              PAIRS does not, because the pairs are separated by staves that
              carry no brace.
  FROM_TOP    that run starts at the system's first staff.
  HALF        the blocks account for at least half the system's staves.

    probe_admission.py out/vs-incumbent.json
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def tiles(blocks: list[list[int]]) -> bool:
    if not blocks:
        return False
    flat: list[int] = []
    for b in sorted(blocks, key=lambda c: c[0]):
        flat.extend(b)
    return flat == list(range(flat[0], flat[0] + len(flat)))


def gates(r: dict) -> dict:
    b = r["blocks"] or []
    covered = sorted({i for blk in b for i in blk})
    return {
        "TILES": tiles(b),
        "FROM_TOP": bool(covered) and covered[0] == 0,
        "HALF": len(covered) >= 0.5 * r["n_staves"],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    args = ap.parse_args()
    rows = json.loads(Path(args.dump).read_text())
    stated = [r for r in rows if r["verdict"] == "partial"]

    combos = [
        ("(none)", lambda g: True),
        ("TILES", lambda g: g["TILES"]),
        ("TILES+HALF", lambda g: g["TILES"] and g["HALF"]),
        ("TILES+FROM_TOP", lambda g: g["TILES"] and g["FROM_TOP"]),
        ("TILES+FROM_TOP+HALF",
         lambda g: g["TILES"] and g["FROM_TOP"] and g["HALF"]),
    ]

    print(f"{len(stated)} systems where the reader states blocks\n")
    print(f"{'gate':<22} {'admitted':>9} {'agree w/ inc':>13} "
          f"{'brkt only':>10} {'inc only':>9} {'self-consist':>13}")
    for name, fn in combos:
        adm = [r for r in stated if fn(gates(r))]
        both = bonly = ionly = 0
        for r in adm:
            bb, ii = set(r["bracket_boundaries"]), set(r["incumbent_cols"])
            both += len(bb & ii)
            bonly += len(bb - ii)
            ionly += len(ii - bb)
        # within-page self-consistency over the admitted set
        bykey: dict[tuple, list[dict]] = defaultdict(list)
        for r in adm:
            bykey[(r["tag"], r["page"], r["n_staves"])].append(r)
        pairs = agree = 0
        for group in bykey.values():
            for a, b in zip(group, group[1:]):
                pairs += 1
                agree += a["bracket_boundaries"] == b["bracket_boundaries"]
        sc = f"{agree}/{pairs}" + (f" {agree/pairs:.2f}" if pairs else "")
        print(f"{name:<22} {len(adm):>9} {both:>13} {bonly:>10} "
              f"{ionly:>9} {sc:>13}")

    print("\nper publisher, gate TILES+FROM_TOP+HALF:")
    per: dict[str, list[dict]] = defaultdict(list)
    for r in stated:
        per[r["tag"]].append(r)
    for pub in sorted(per):
        adm = [r for r in per[pub]
               if all(gates(r)[k] for k in ("TILES", "FROM_TOP", "HALF"))]
        both = bonly = ionly = 0
        for r in adm:
            bb, ii = set(r["bracket_boundaries"]), set(r["incumbent_cols"])
            both += len(bb & ii); bonly += len(bb - ii); ionly += len(ii - bb)
        print(f"  {pub:<11} {len(adm):>3}/{len(per[pub]):<3} admitted   "
              f"agree {both:>3}  bracket-only {bonly:>3}  incumbent-only {ionly:>3}")
        for r in adm:
            print(f"      p{r['page']} s{r['system']} n={r['n_staves']:2d} "
                  f"blocks={r['blocks']} "
                  f"bracket={r['bracket_boundaries']} "
                  f"inc={r['incumbent_cols']}")


if __name__ == "__main__":
    main()
