"""Prototype: segment a document into LINEUP SPANS from system sizes alone.

The axiom is the same one the roster rests on: a system may OMIT the staves of
tacet parts but can never INVENT one. So a page whose largest system is larger
than every page before it has proved that the lineup GREW there -- a new
movement's orchestra, not a tacet accident. Nothing else in the size series is
evidence of a boundary: a dip is suppression, and equality is silence.

Reports the spans each candidate rule produces, against the staff profiles the
whole-work session already measured.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path


def peaks(rows, *, merge_cap_ratio=2.0):
    """`peak[page] = largest system on the page`, merged systems refused.

    `slots.build_reference` already refuses a system more than 2x the median as
    a probable concatenation (`REFERENCE_MAX_SIZE_RATIO`); the same refusal has
    to apply here, or one merged system on one page invents a lineup boundary.
    """
    sizes = [s for r in rows for s in r["systems"]]
    if not sizes:
        return {}
    ordered = sorted(sizes)
    median = ordered[len(ordered) // 2]
    cap = median * merge_cap_ratio
    out = {}
    for r in rows:
        keep = [s for s in r["systems"] if s <= cap]
        if keep:
            out[r["page"]] = max(keep)
    return out


def spans_running_max(peak, *, require_recurrence=True):
    """Boundary at every page that sets a NEW running maximum.

    With `require_recurrence`, the new level must be seen on more than one page
    of the document -- a lineup is the orchestra, and the orchestra recurs; a
    size seen exactly once is a segmentation wobble. This is the same
    "recurring" test `build_reference` applies to its own candidates.
    """
    counts = collections.Counter(peak.values())
    pages = sorted(peak)
    bounds, running = [], 0
    for p in pages:
        v = peak[p]
        if v > running:
            if require_recurrence and counts[v] < 2:
                continue
            bounds.append(p)
            running = v
    if not bounds:
        bounds = [pages[0]]
    out = []
    for i, b in enumerate(bounds):
        end = bounds[i + 1] - 1 if i + 1 < len(bounds) else pages[-1]
        out.append((b, end))
    return out


def main(paths):
    for path in paths:
        d = json.load(open(path))
        rows = d["rows"]
        peak = peaks(rows)
        print(f"\n=== {Path(path).name}  ({len(rows)} pages) ===")
        print("  sizes:", dict(sorted(collections.Counter(peak.values()).items())))
        for tag, kw in (("recurrence", {}), ("raw", {"require_recurrence": False})):
            sp = spans_running_max(peak, **kw)
            desc = ", ".join(
                f"p{a}-{b} peak={max(peak[q] for q in peak if a <= q <= b)}"
                f" ({sum(1 for q in peak if a <= q <= b)}pp)" for a, b in sp)
            print(f"  {tag:11s} {len(sp)} spans: {desc}")


if __name__ == "__main__":
    main(sys.argv[1:] or sorted(
        str(p) for p in Path(
            "benchmarks/omr-movement-reference-2026-09/out").glob(
                "*.staffprofile.json")))
