#!/usr/bin/env python3
"""Replay reference-selection rules over the cached system views.

Probing is the expensive half (`probe_system_views.py`); the rules are free, so
they are evaluated here, offline, over the SAME recorded views — no rule can
win by having read a margin differently.

THE QUESTION, and it is a publisher one before it is a scoring one: is the
most-labelled system reliably the FULLEST one?  Litolff labels winds and brass
on every system and strings never; Breitkopf labels everything; Simrock labels a
movement's first page only.  A rule that means "the full lineup" under one
convention can mean "an arbitrary system" under another, and the rate at which
each rule lands on the run's largest system is what separates those.

⚠️ THE LARGEST SYSTEM IS A PROXY, NOT GROUND TRUTH.  It is what
`build_reference`'s own docstring aims at ("a system can omit tacet parts but
never invent one"), and a reference SHORTER than the fullest system cannot name
every staff of it — `align` leaves the overflow at slot -1.  But it is not a
reading of the print, and where system grouping merged two systems the largest
is wrong.  So the merge guards are applied first, and a document whose run holds
one usable system is excluded (every rule agrees there and it measures nothing).

    python3 .../analyse_rules.py [--cache DIR] [--json OUT.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr.slots import SystemView, build_reference  # noqa: E402


class _St:
    """The two `Staff` fields `build_reference` reads, and nothing else."""

    def __init__(self, staff_index, group_index):
        self.staff_index = staff_index
        self.group_index = group_index


def views_of(rec):
    out = []
    for v in rec["views"]:
        if "staves" not in v:
            continue
        staves = [_St(s["staff_index"], s["group_index"]) for s in v["staves"]]
        labels = {s["staff_index"]: s["name"] for s in v["staves"]
                  if s["name"] and s["confidence"] in ("high", "medium")}
        out.append((v["page"], v["system"], SystemView(staves=staves,
                                                       labels=labels)))
    return out


def pick(views, most_labelled):
    """Which system `build_reference` chose, as (page, system, size, labels)."""
    ref = build_reference([v for _p, _s, v in views],
                          most_labelled=most_labelled)
    if not ref:
        return None
    idx = {s.index for s in ref}
    for p, s, v in views:
        if v.size == len(ref) and {i for i in range(v.size)} == idx:
            # `Slot.index` is the ordinal within the chosen system, so identity
            # is by size plus the labels the reference carries.
            got = {sl.index: sl.instrument for sl in ref}
            mine = {i: v.labels.get(st.staff_index)
                    for i, st in enumerate(v.staves)}
            if got == mine:
                return (p, s, v.size, len(v.labels))
    return (None, None, len(ref), sum(1 for s in ref if s.instrument))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(HERE.parent / "views-cache" / "w0-4"))
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    files = sorted(Path(args.cache).glob("*.json"))
    rows = []
    for f in files:
        rec = json.loads(f.read_text())
        vs = views_of(rec)
        if len(vs) < 2:
            continue                      # nothing for a rule to decide
        sizes = [v.size for _p, _s, v in vs]
        labs = [len(v.labels) for _p, _s, v in vs]
        rows.append({
            "key": rec["key"], "house": rec["house"],
            "composer": rec["composer"], "systems": len(vs),
            "sizes": sizes, "labels": labs,
            "max_size": max(sizes), "any_label": any(labs),
            "old": pick(vs, most_labelled="off"),
            "new": pick(vs, most_labelled="on"),
            "pure": pick(vs, most_labelled="pure"),
        })

    print(f"documents with >=2 usable systems in the window: {len(rows)}"
          f"  (cache holds {len(files)})")
    if not rows:
        return 0

    def summarise(tag, rs):
        if not rs:
            print(f"  {tag:22s}  (none)")
            return
        n = len(rs)
        cells = []
        for arm in ("old", "new", "pure"):
            full = sum(1 for r in rs if r[arm] and r[arm][2] == r["max_size"])
            named = sum(r[arm][3] for r in rs if r[arm])
            cells.append(f"{arm} {full:4d}/{n} = {full/n:.3f} (names {named:5d})")
        differ = sum(1 for r in rs if r["old"] != r["new"])
        print(f"  {tag:22s} n={n:4d}  " + "  ".join(cells) +
              f"  new≠old {differ:4d}")

    labelled = [r for r in rows if r["any_label"]]
    silent = [r for r in rows if not r["any_label"]]
    print("\n== overall")
    summarise("all", rows)
    summarise("names something", labelled)
    summarise("names NOTHING", silent)
    assert all(r["old"] == r["new"] for r in silent), \
        "the new rule must abstain where nothing is labelled"
    print("  ⭑ silent documents: every pick identical (abstention verified)")

    print("\n== by house — the convention axis (labelled documents only)")
    byh = defaultdict(list)
    for r in labelled:
        byh[r["house"]].append(r)
    for h, rs in sorted(byh.items(), key=lambda kv: -len(kv[1])):
        summarise(h, rs)

    print("\n== where the two rules disagree, and which way")
    better = worse = same = 0
    for r in labelled:
        if r["old"] == r["new"]:
            continue
        o = r["old"][2] if r["old"] else 0
        nn = r["new"][2] if r["new"] else 0
        if nn > o:
            better += 1
        elif nn < o:
            worse += 1
        else:
            same += 1
    print(f"  new reference LARGER  {better}")
    print(f"  new reference SMALLER {worse}   <- the risk: staves past the "
          f"reference get slot -1")
    print(f"  same size, different system {same}")

    shrink_new = [r for r in labelled
                  if r["old"] and r["new"] and r["new"][2] < r["old"][2]]
    shrink_pure = [r for r in labelled
                   if r["old"] and r["pure"] and r["pure"][2] < r["old"][2]]
    print(f"\n== documents where the reference SHRINKS vs the old rule "
          f"(staves past it get slot -1)")
    print(f"  new (never-shrink guard on)  {len(shrink_new)}")
    print(f"  pure (guard off)             {len(shrink_pure)}")
    for r in shrink_pure:
        print(f"    {r['house']:12s} {r['key']:44s} sizes={r['sizes']} "
              f"labels={r['labels']} old={r['old']} pure={r['pure']}")

    print("\n== documents where the new rule picks a LARGER reference")
    for r in labelled:
        if r["old"] and r["new"] and r["new"][2] > r["old"][2]:
            print(f"  {r['house']:12s} {r['key']:44s} sizes={r['sizes']} "
                  f"labels={r['labels']} old={r['old']} new={r['new']}")

    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
