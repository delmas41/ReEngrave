#!/usr/bin/env python3
"""Read-only: how often does the PAGE's own bracket grouping disagree with the
exporter's `len(staves) == 2` brace rule?

Step 1 of docs/target-architecture-2026-09-07.md asks for this BEFORE any code:

    over every stored transcription, count staves where `group_index` is present
    and disagrees with `len(staves) == 2`, and how many systems carry no block
    at all.

⚠️ "Present" is not "not None". `system_grouping._assign_groups` writes
`group_index = 0` for EVERY staff of a system it declined to partition — a
system with fewer than 3 staves, or with too little column evidence. So a
single-block system is an ABSTENTION wearing the same clothes as a read
one-family system, and this probe counts it as ABSENT. That is the whole point
of the step: 22/22 precise, 22/39 recalled, so the absent case is common.

Writes nothing. Exits 2 when it found no transcription to read.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def _blocks(staves: list[dict]) -> list[list[int]] | None:
    """The system's bracket blocks as index runs, or None when absent."""
    gi = [s.get("group_index") for s in staves]
    if any(g is None for g in gi):
        return None
    if len(set(gi)) < 2:
        return None            # abstention — indistinguishable from one family
    out: list[list[int]] = []
    for i, g in enumerate(gi):
        if i and g == gi[i - 1]:
            out[-1].append(i)
        else:
            out.append([i])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="+", type=Path)
    ap.add_argument("--glob", default="*.omr.json")
    args = ap.parse_args()

    files: list[Path] = []
    for r in args.roots:
        files += sorted(r.rglob(args.glob)) if r.is_dir() else [r]
    files = [f for f in files if f.is_file()]
    if not files:
        print("no transcriptions found", file=sys.stderr)
        return 2

    tot = Counter()
    reasons = Counter()
    changed_rows: list[str] = []
    for f in files:
        try:
            res = json.loads(f.read_text())
        except Exception as exc:                       # noqa: BLE001
            print(f"SKIP {f.name}: {exc}", file=sys.stderr)
            continue
        tot["files"] += 1
        for page in res.get("pages", []):
            for si, sys_ in enumerate(page.get("systems", [])):
                staves = sys_.get("staves", [])
                if not staves:
                    continue
                tot["systems"] += 1
                tot["staves"] += len(staves)
                gi = [s.get("group_index") for s in staves]
                tot["staves_group_index_null"] += sum(g is None for g in gi)
                blocks = _blocks(staves)
                if blocks is None:
                    tot["systems_fact_absent"] += 1
                    reasons["null_group_index" if any(g is None for g in gi)
                            else "single_block"] += 1
                    continue
                tot["systems_fact_present"] += 1
                old = [list(range(len(staves)))] if len(staves) == 2 else []
                new = [b for b in blocks if len(b) == 2]
                if [b for b in old] != new:
                    tot["systems_disagree"] += 1
                    tot["staves_in_new_braces"] += sum(len(b) for b in new)
                    changed_rows.append(
                        f"    {f.name} p{page.get('page_index')} sys{si}: "
                        f"{len(staves)} staves, blocks={[len(b) for b in blocks]}, "
                        f"len2-rule braces {len(old)} -> measurement braces {len(new)}")

    print(f"files            {tot['files']}")
    print(f"systems          {tot['systems']}   staves {tot['staves']}")
    print(f"  fact PRESENT   {tot['systems_fact_present']}")
    print(f"  fact ABSENT    {tot['systems_fact_absent']}   {dict(reasons)}")
    print(f"  staves with group_index == null   {tot['staves_group_index_null']}")
    print(f"DISAGREE with len(staves)==2        {tot['systems_disagree']} systems, "
          f"{tot['staves_in_new_braces']} staves newly braced")
    for row in changed_rows[:60]:
        print(row)
    if len(changed_rows) > 60:
        print(f"    ... {len(changed_rows) - 60} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
