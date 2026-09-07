#!/usr/bin/env python3
"""Assert a recording-only change added KEYS and changed no VERDICT.

The audit's first item — "record the refusals" — is a change whose whole
correctness claim is that the pipeline decides exactly what it decided before.
Asserting that is not evidence; this measures it.

    python3 benchmarks/omr-pipeline-audit-2026-09/probe/compare_transcriptions.py \
        BEFORE.json AFTER.json

Walks both result JSONs together and reports three populations:

    changed   a key present in BOTH whose value differs  → FAILURE
    removed   a key present in BEFORE and gone in AFTER   → FAILURE
    added     a key present only in AFTER                 → the point

Exits non-zero if `changed` or `removed` is non-empty.

⚠️ **A control ran first, and it is what defines `IGNORED_LEAVES`.** Two runs
of ONE tree on the same page are not byte-identical: the wall-clock fields
(`runtime/*`, `weight_routing/classification/ms`) differ every run, and nothing
else does — measured 2026-09-06 on an engraved fixture (brahms-sym1-mvt1 p0)
and a scan (Litolff Beethoven 5 / imslp984073 p1), 6 differing leaves each,
all of them clocks. So those leaves are excluded by NAME, and a difference
anywhere else is a real difference. Run the control yourself before trusting a
green result here: transcribe one page twice on an unmodified tree and pass the
two outputs to this script — it must report 0 changed, 0 added.

⚠️ This is the SECONDARY gate. The primary one is the exported MusicXML being
byte-identical (`python3 -m tools.omr.export <json> --format musicxml`, then
`diff`), because that is what a reader of this project actually receives; a
JSON key nothing exports could in principle move without the file moving, and
the reverse is not true.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

#: Leaves whose value legitimately differs between two runs of ONE tree.
#: Wall clocks only — see the control described in the module docstring.
IGNORED_LEAVES = (
    re.compile(r"^/runtime/"),
    re.compile(r"^/weight_routing/classification/ms$"),
    re.compile(r"/_s$"),
)


def _ignored(path: str) -> bool:
    return any(p.search(path) for p in IGNORED_LEAVES)


def walk(before, after, path: str = ""):
    """Yield (kind, path, before, after) for every leaf that is not identical."""
    if _ignored(path):
        return
    if isinstance(before, dict) and isinstance(after, dict):
        for key in before:
            sub = f"{path}/{key}"
            if key not in after:
                yield ("removed", sub, before[key], None)
            else:
                yield from walk(before[key], after[key], sub)
        for key in after:
            if key not in before:
                yield ("added", f"{path}/{key}", None, after[key])
        return
    if isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            yield ("changed", f"{path}[len]", len(before), len(after))
            return
        for i, (b, a) in enumerate(zip(before, after)):
            yield from walk(b, a, f"{path}[{i}]")
        return
    if type(before) is not type(after) or before != after:
        yield ("changed", path, before, after)


def _generalise(path: str) -> str:
    return re.sub(r"\[\d+\]", "[]", path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("before", type=Path)
    ap.add_argument("after", type=Path)
    ap.add_argument("--show", type=int, default=8,
                    help="How many example paths to print per population")
    args = ap.parse_args()

    before = json.loads(args.before.read_text())
    after = json.loads(args.after.read_text())

    buckets: dict[str, list] = {"changed": [], "removed": [], "added": []}
    for kind, path, b, a in walk(before, after):
        buckets[kind].append((path, b, a))

    for kind in ("changed", "removed", "added"):
        rows = buckets[kind]
        print(f"{kind}: {len(rows)}")
        shapes = Counter(_generalise(p) for p, _, _ in rows)
        for shape, n in shapes.most_common(args.show):
            print(f"    {n:6d}  {shape}")
        if kind != "added":
            for path, b, a in rows[: args.show]:
                print(f"      e.g. {path}: {b!r} -> {a!r}")

    bad = len(buckets["changed"]) + len(buckets["removed"])
    if bad:
        print(f"\nFAIL: {bad} pre-existing leaves changed or disappeared.")
        return 1
    print(f"\nOK: no pre-existing leaf moved; {len(buckets['added'])} new leaves.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
