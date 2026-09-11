#!/usr/bin/env python3
"""What a human cleaning the file up would see, before and after.

    python3 benchmarks/omr-keysig-truth-2026-09/file_grade.py

⚠️ THE FILE CANNOT SAY "I COULD NOT TELL". A staff whose key abstained is
exported with no `<key>` element, and a missing key is no accidentals to any
reader — so an abstention is RIGHT IN THE FILE on the horns, trumpets and
timpani, which genuinely print none, and WRONG on everyone else. Grading the
reading and grading the file are therefore different sums, and only the second
one is the cleanup count's unit.
"""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def right(v, truth) -> bool:
    return (0 if v is None else v) == truth


def main() -> int:
    rows = json.loads((HERE / "readers-read.json").read_text())
    before = sum(right(r["loc_fifths"], r["truth_fifths"]) for r in rows)
    after = sum(
        right(r["loc_fifths"] if r["loc_fifths"] is not None
              else r["tpl_fifths"], r["truth_fifths"]) for r in rows)
    print(f"FILE right — locator alone (what shipped) : {before} of {len(rows)}")
    print(f"FILE right — locator else template        : {after} of {len(rows)}")
    print()
    gained = lost = 0
    for r in rows:
        old = r["loc_fifths"]
        new = old if old is not None else r["tpl_fifths"]
        if right(old, r["truth_fifths"]) == right(new, r["truth_fifths"]):
            continue
        good = right(new, r["truth_fifths"])
        gained += good
        lost += not good
        print(f"  {'+' if good else '-'} p{r['page']}/s{r['system']} staff "
              f"{r['staff']:>2} {r['instrument']:<20} truth "
              f"{r['truth_fifths']:>3}  was {str(old):>5}  now {str(new):>5}")
    print(f"\n{gained} staff-systems become right in the file, {lost} become "
          f"wrong.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
