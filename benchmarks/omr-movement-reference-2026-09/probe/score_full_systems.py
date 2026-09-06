"""Score staff identity on FULL systems of a whole-work run.

A system that carries every staff the movement has is the one case where the
truth needs no page-by-page reading: nothing can be added to a full lineup, so a
system of exactly N staves in a region whose maximum is N IS that lineup, in
printed order.  The lineups below were read off the print
(`crops/p1-margin.png`, `crops/p44-margin.png`, `crops/p4-margin.png`) and the
instrument names are the canonical `instruments.Instrument.name` values a
musician would give, NOT what the lexicon returns -- so a lexicon fault shows as
an error rather than being scored as correct against itself.

Reduced systems (tacet staves suppressed) are NOT scored: which parts were
dropped is a fact about the page and this harness does not know it.

Usage:  score_full_systems.py WORK OUT.json [OUT2.json ...]
        WORK in {beet5, dvorak9}
"""
from __future__ import annotations

import json
import sys
import collections
from pathlib import Path

# (first_page, last_page, size) -> lineup, top to bottom
LINEUPS = {
    "beet5": [
        # movements 1-3, twelve staves: crops/p1-margin.png
        (0, 43, 12, ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Trumpet",
                     "Timpani", "Violin", "Violin", "Viola", "Cello",
                     "Contrabass"]),
        # finale, seventeen staves: crops/p44-margin.png
        (44, 200, 17, ["Piccolo", "Flute", "Oboe", "Clarinet", "Bassoon",
                       "Contrabassoon", "Horn", "Trumpet", "Timpani",
                       "Trombone", "Trombone", "Trombone", "Violin", "Violin",
                       "Viola", "Cello", "Contrabass"]),
    ],
    "dvorak9": [
        # whole work, fifteen staves: crops/p4-margin.png
        (0, 200, 15, ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Horn",
                      "Trumpet", "Trombone", "Trombone", "Timpani", "Violin",
                      "Violin", "Viola", "Cello", "Contrabass"]),
    ],
}


def systems(r):
    for page in r.get("pages", []):
        for sy in page.get("systems", []):
            sts = sorted(sy.get("staves", []),
                         key=lambda s: s.get("staff_geometry", {})
                         .get("line_ys_page", [0])[0])
            yield page.get("page_index"), sy.get("system_index"), sts


def truth_for(work, page, size):
    for lo, hi, n, names in LINEUPS[work]:
        if lo <= page <= hi and size == n:
            return names
    return None


def main(work, path):
    r = json.load(open(path))
    rows = list(systems(r))
    scored = [(p, s, st, truth_for(work, p, len(st))) for p, s, st in rows]
    scored = [t for t in scored if t[3] is not None]
    n_staff = sum(len(st) for _, _, st, _ in scored)
    print(f"=== {Path(path).name}   work={work}")
    print(f"INPUT ASSERTION: pages={len(r.get('pages', []))} "
          f"systems-in-run={len(rows)} full-systems-scored={len(scored)} "
          f"staff-records-scored={n_staff}")
    if n_staff == 0:
        print("REFUSING: no full system matched a known lineup — nothing scored")
        return
    ros = (r.get("contextual") or {}).get("roster")
    if ros:
        print(f"roster from page {ros['page_index']} sys {ros['system_index']}, "
              f"{ros['named']}/{ros['n_staves']} named, "
              f"opened={ros['pages_opened']}")
    ref = (r.get("contextual") or {}).get("reference") or []
    print(f"reference slots: {len(ref)}")

    correct = 0
    unnamed = 0
    conf = collections.Counter()
    by_size = collections.Counter()
    by_size_ok = collections.Counter()
    for p, s, st, names in scored:
        for i, x in enumerate(st):
            got = x.get("instrument")
            want = names[i]
            by_size[len(st)] += 1
            if got is None:
                unnamed += 1
                conf[(want, "(unnamed)")] += 1
            elif got == want:
                correct += 1
                by_size_ok[len(st)] += 1
            else:
                conf[(want, got)] += 1
    print()
    print(f"CORRECT {correct}/{n_staff} = {correct/n_staff:.4f}   "
          f"unnamed {unnamed}   wrong {n_staff - correct - unnamed}")
    for k in sorted(by_size):
        print(f"   size {k:3d}: {by_size_ok[k]:4d}/{by_size[k]:4d} = "
              f"{by_size_ok[k]/by_size[k]:.4f}")
    print()
    print("confusions (truth -> emitted), most common first:")
    for (want, got), n in conf.most_common(30):
        print(f"  {n:5d}  {want:16s} -> {got}")


if __name__ == "__main__":
    work = sys.argv[1]
    for a in sys.argv[2:]:
        main(work, a)
        print()
