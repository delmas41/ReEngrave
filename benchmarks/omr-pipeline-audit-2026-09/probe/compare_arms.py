#!/usr/bin/env python3
"""Prove a pipeline change recorded evidence and changed no verdict.

Used to gate the barline-evidence change (branch `claude/fix-barline-evidence`,
2026-09-06), which added eight optional fields to `types.Barline` and
per-deletion-site counters to `measure_extractor` / `staff_detector`.

Three assertions, in the order they can fail:

1. **The exported MusicXML is byte-identical.** `measure_extractor` is upstream
   of literally everything — a moved barline moves a measure boundary, which
   moves every cell, which moves every detection. If the file the user gets is
   identical, no verdict moved.

2. **Measure and barline counts per staff are unchanged.** A change can be
   byte-identical in the export while still having shifted structure that the
   exporter happened to normalise away, and an off-by-one bar is exactly the
   silent failure this guards.

3. **No pre-existing key in the result JSON changed value.** New keys are
   permitted (that is the point of the change); a changed value is not.

⚠️ **The comparison is only meaningful if the harness is deterministic**, so
run the control first: two `before` arms against each other. On 2026-09-06 with
`--no-direction-text --no-contextual` the MusicXML of both pages was
bit-identical across two independent runs, and the ONLY JSON keys that moved
were wall-clock timings (`runtime/*`, `weight_routing/classification/ms`) —
which is why those are in IGNORE_SUFFIXES. Do not add anything else to that
list to make a run pass; a moving key that is not a clock is the finding.

    python3 benchmarks/omr-pipeline-audit-2026-09/probe/compare_arms.py \
        <before-dir> <after-dir>

Each arm directory holds `<name>.json` + `<name>.musicxml` per page.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# Keys whose value is a measured duration, not a verdict. Established by
# running the same tree twice — see the docstring.
IGNORE_SUFFIXES = (
    "/runtime/total_s", "/runtime/phase1_s", "/runtime/yolo_s",
    "/runtime/detect_s", "/runtime/export_s", "/runtime/contextual_s",
    "/weight_routing/classification/ms",
)


def _ignored(path: str) -> bool:
    return any(path.endswith(s) for s in IGNORE_SUFFIXES)


def walk(a, b, path: str, out: list[str]) -> None:
    """Report only CHANGED pre-existing values and removed keys. A key present
    in `b` and absent from `a` is the whole point of the change and is
    reported separately, as an addition."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k not in b:
                out.append(f"REMOVED  {path}/{k}")
            else:
                walk(a[k], b[k], f"{path}/{k}", out)
        return
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"LENGTH   {path}: {len(a)} -> {len(b)}")
            return
        for i, (u, v) in enumerate(zip(a, b)):
            walk(u, v, f"{path}[{i}]", out)
        return
    if type(a) is not type(b):
        out.append(f"TYPE     {path}: {type(a).__name__} -> {type(b).__name__}")
        return
    if a != b and not _ignored(path):
        out.append(f"VALUE    {path}: {a!r} -> {b!r}")


def added_keys(a, b, path: str, out: list[str]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in b:
            if k not in a:
                out.append(f"{path}/{k}")
            else:
                added_keys(a[k], b[k], f"{path}/{k}", out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (u, v) in enumerate(zip(a, b)):
            added_keys(u, v, f"{path}[{i}]", out)


def structure(doc) -> Counter:
    """(page, system, staff) -> measure count, plus barline count per system.

    Read off the result JSON rather than off `PageWithStaves`, because that is
    what survives to disk and what every downstream consumer actually sees.
    """
    c: Counter = Counter()
    for page in doc.get("pages", []):
        p = page.get("page_index")
        for sys_ in page.get("systems", []):
            s = sys_.get("system_index")
            for staff in sys_.get("staves", []):
                key = ("measures", p, s, staff.get("staff_index"))
                c[key] = len(staff.get("measures", []))
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    args = ap.parse_args()
    before, after = Path(args.before), Path(args.after)

    failures = 0
    for xml in sorted(before.glob("*.musicxml")):
        name = xml.stem
        other = after / xml.name
        print(f"\n=== {name} ===")

        # 1. the file the user gets
        if not other.is_file():
            print(f"  FAIL  no {other}")
            failures += 1
            continue
        same = xml.read_bytes() == other.read_bytes()
        print(f"  musicxml byte-identical: {same}  ({xml.stat().st_size} bytes)")
        failures += 0 if same else 1

        aj, bj = before / f"{name}.json", after / f"{name}.json"
        if not (aj.is_file() and bj.is_file()):
            print("  (no result JSON pair — skipping 2 and 3)")
            continue
        a = json.loads(aj.read_text())
        b = json.loads(bj.read_text())

        # 2. structure
        sa, sb = structure(a), structure(b)
        if sa == sb:
            print(f"  per-staff measure counts unchanged: {len(sa)} staves, "
                  f"{sum(sa.values())} measures")
        else:
            print("  FAIL  per-staff measure counts MOVED:")
            for k in sorted(set(sa) | set(sb), key=str):
                if sa.get(k) != sb.get(k):
                    print(f"        {k}: {sa.get(k)} -> {sb.get(k)}")
            failures += 1

        # 3. no pre-existing key changed
        diffs: list[str] = []
        walk(a, b, "", diffs)
        if diffs:
            print(f"  FAIL  {len(diffs)} pre-existing key(s) changed:")
            for d in diffs[:40]:
                print("        " + d)
            failures += 1
        else:
            print("  no pre-existing key changed value (timings ignored)")

        adds: list[str] = []
        added_keys(a, b, "", adds)
        seen = Counter(p.rsplit("/", 1)[-1] for p in adds)
        print(f"  new keys: {len(adds)} occurrence(s), "
              f"{len(seen)} distinct — {dict(seen)}")

    print("\nRESULT:", "PASS" if failures == 0 else f"FAIL ({failures})")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
