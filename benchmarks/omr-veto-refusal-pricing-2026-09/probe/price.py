"""Join the hand-read adjudication to the composition harness's veto records.

Refuses to report if the two disagree about WHICH staves were refused: the
adjudication is worth nothing if it is not about the same 18 rows the shipping
default produces. Prints the per-refusal table and the bottom line.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOB = (ROOT.parent / "omr-spans-veto-composition-2026-09" / "out" /
        "whole-spans-on.json")


def main() -> int:
    blob = json.loads(BLOB.read_text())["contextual"]["absent_instrument_veto"]
    adj = json.loads((ROOT / "adjudication.json").read_text())
    live = {(v["page_index"], v["system_index"], v["staff_index"]): v
            for v in blob["vetoes"]}
    mine = {(r["page"], r["system"], r["staff"]): r for r in adj["rows"]}

    if set(live) != set(mine):
        print("REFUSING: the adjudication is not about the shipping refusals")
        print("  only in the run :", sorted(set(live) - set(mine)))
        print("  only in the file:", sorted(set(mine) - set(live)))
        return 1
    for key, row in mine.items():
        if live[key]["instrument"] != row["refused"]:
            print(f"REFUSING: {key} refused {live[key]['instrument']!r} in the "
                  f"run, {row['refused']!r} in the adjudication")
            return 1

    print(f"{len(live)} refusals, mode={blob['mode']} rule={blob['rule']} "
          f"window={blob['window']} reference_size={blob['reference_size']}")
    print()
    hdr = ("page", "sys", "staff", "slot", "refused name", "printed",
           "verdict")
    print("| %s |" % " | ".join(hdr))
    print("|" + "|".join("---" for _ in hdr) + "|")
    for key in sorted(mine):
        r = mine[key]
        print(f"| {r['page']} | {r['system']} | {r['staff']} | {r['slot']} | "
              f"{r['refused']} | {r['printed']} | **{r['verdict']}** |")

    tally = collections.Counter(r["verdict"] for r in mine.values())
    print()
    print(f"COST    (a name that would have been RIGHT) : {tally['cost']}")
    print(f"BENEFIT (a name that would have been WRONG) : {tally['benefit']}")
    print(f"UNKNOWN                                     : {tally['unknown']}")
    print()
    by_page = collections.defaultdict(collections.Counter)
    for k, r in mine.items():
        by_page[k[0]][r["verdict"]] += 1
    for page in sorted(by_page):
        c = by_page[page]
        print(f"  page {page}: {c['cost']} cost, {c['benefit']} benefit, "
              f"{c['unknown']} unknown")

    # The scale to read the 18 at: on the SAME pages, names the veto passes.
    extra = adj.get("same_pages_unvetoed", {}).get("rows", [])
    if extra:
        print()
        print(f"on the same four pages, unlabelled staves given a name from a "
              f"DIFFERENT FAMILY and NOT refused: {len(extra)}")
        for r in extra:
            key = (r["page"], r["system"], r["staff"])
            assert key not in live, f"{key} is refused; it is not an example"
            print(f"  p{r['page']} sy{r['system']} st{r['staff']:2d}  "
                  f"{r['given']:<9} on a {r['printed']} staff")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
