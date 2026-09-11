#!/usr/bin/env python3
"""Grade the two readers together, under the ONE precedence ASSUMPTIONS.md D20
already measured and prescribed: the template answers GAPS ONLY.

    python3 benchmarks/omr-keysig-truth-2026-09/combine.py

⚠️ THE PRECEDENCE IS INHERITED, NOT CHOSEN HERE. D20: *"port the template
reader as a SECOND witness with its own `reader=`, and express gaps only as a
declared precedence ... It may not simply win: it is the one source here that
can OVER-count, and letting the fuller reading take it gains 1 staff on
Beethoven 5 p.2 and 2 on the Pastoral and costs a WRONG reading on WTC I
p.17."* Letting the template win outright is therefore already priced and
already refused, on documents this run does not have; re-deciding it from four
pages of one edition would be exactly the corpus-of-one tuning this repo
forbids. So only gaps-only is scored.
"""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def grade(rows, get):
    t = {"correct": 0, "wrong": 0, "abstained": 0}
    wrong = []
    for r in rows:
        v = get(r)
        if v is None:
            t["abstained"] += 1
        elif v == r["truth_fifths"]:
            t["correct"] += 1
        else:
            t["wrong"] += 1
            wrong.append((r["page"], r["system"], r["staff"],
                          r["instrument"], r["truth_fifths"], v))
    return t, wrong


def main() -> int:
    res = json.loads((HERE / "window-repair.json").read_text())
    readers = (
        ("locator", lambda r: r["loc_fifths"]),
        ("template", lambda r: r["tpl_fifths"]),
        ("loc-else-tpl", lambda r: r["loc_fifths"] if r["loc_fifths"]
         is not None else r["tpl_fifths"]),
    )
    print(f"{'arm':<6} {'reader':<13} {'correct':>7} {'wrong':>6} "
          f"{'abstain':>8}")
    for arm in ("base", "A", "B"):
        for name, get in readers:
            t, _ = grade(res[arm], get)
            print(f"{arm:<6} {name:<13} {t['correct']:>7} {t['wrong']:>6} "
                  f"{t['abstained']:>8}")
        print()
    t, wrong = grade(res["A"], lambda r: r["loc_fifths"]
                     if r["loc_fifths"] is not None else r["tpl_fifths"])
    print(f"ARM A, locator-else-template — the {len(wrong)} WRONG rows:")
    for w in wrong:
        print(f"  p{w[0]}/s{w[1]} staff {w[2]:>2} {w[3]:<20} "
              f"truth {w[4]:>3}  read {w[5]:>3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
