"""Sean's hypothesis: do the FULL-HEIGHT objects define the SYSTEM?

`system_grouping` uses a column inked through a whole gap only as a VETO on a
gap-based break, and `systemic_column_counts` (the `OMR_BRACKET_COLUMNS` fix)
explicitly DISCARDS any cluster crossing every gap, because it distinguishes no
gap from any other.  The hypothesis is that the same discarded object states
something else: the extent of the system.

The test has to be honest about what it may use.  A per-system band would be
begging the question — the system assignment is the thing under test — so the
band here is anchored on the PAGE, over all staves at once, and the resulting
partition is compared against `Staff.system_index` after the fact.

Reported per page:

    incumbent   the systems `assign_systems` produced (sizes)
    read        the partition induced by the maximal left-edge strokes
    unassigned  staves no stroke covers — the honest failure mode, and the
                one a veto-only consumer never has to face

    probe_system_extent.py --corpus scan --pages-per-edition 12 --out out/sys.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import cv2                                                   # noqa: E402
import numpy as np                                           # noqa: E402
from tools.omr.preprocessing import render_page              # noqa: E402
from tools.omr.staff_detector import detect_staves           # noqa: E402
from tools.omr.bracket_reader import (                       # noqa: E402
    strokes_at_left_edge, covered_staves, is_rule)

LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")
WORKS = Path("/Users/seanjohnson/Desktop/ReEngrave/benchmarks/"
             "omr-scan-e2e-2026-09/works.json")


def scan_editions() -> list[tuple[str, Path]]:
    rows = json.loads(WORKS.read_text())["rows"]
    seen: dict[str, Path] = {}
    for r in rows:
        cp = r["edition"]["catalog_path"]
        seen.setdefault(cp.split("/")[1], LIB / cp)
    return sorted(seen.items())


class _PageAnchor:
    """A stand-in `staff` list for `strokes_at_left_edge`'s page-wide scan.

    The function anchors on `median(x_start)` and widens by BAND_*_SPACINGS.
    On a page whose systems are indented differently that median falls between
    the modes — the exact poisoning `OMR_CHOIR_GROUPING`'s cue B exists for —
    so the scan is run once per distinct x_start MODE and the strokes pooled.
    """


def _x_modes(staves: list, spacing: float) -> list[float]:
    """Cluster the page's staff x_starts; one band per mode."""
    xs = sorted(s.x_start for s in staves)
    modes: list[list[float]] = []
    for x in xs:
        if modes and x - modes[-1][-1] <= 4.0 * spacing:
            modes[-1].append(x)
        else:
            modes.append([x])
    return [statistics.median(m) for m in modes]


class _Fake:
    __slots__ = ("top_y", "bottom_y", "x_start", "x_end", "line_spacing_px")

    def __init__(self, s, x_start):
        self.top_y = s.top_y
        self.bottom_y = s.bottom_y
        self.x_start = x_start
        self.x_end = s.x_end
        self.line_spacing_px = s.line_spacing_px


def page_strokes(binary, staves: list) -> list:
    """Every rule-shaped left-edge stroke on the page, all modes pooled."""
    spacing = statistics.median([s.line_spacing_px for s in staves]) or 1.0
    out = []
    for anchor in _x_modes(staves, spacing):
        fake = [_Fake(s, anchor) for s in staves]
        strokes, _geom = strokes_at_left_edge(binary, fake)
        out.extend(s for s in strokes if is_rule(s))
    return out


def induced_partition(strokes: list, staves: list) -> tuple[list[list[int]], list[int]]:
    """Maximal strokes -> a partition of the page's staves."""
    covers = []
    for st in strokes:
        c = covered_staves(st, staves)
        if len(c) >= 2:
            covers.append(set(c))
    # keep only maximal sets
    maximal = [c for c in covers
               if not any(c < d for d in covers)]
    # merge overlapping maximal sets (two objects of one system)
    merged: list[set] = []
    for c in sorted(maximal, key=lambda s: min(s)):
        if merged and merged[-1] & c:
            merged[-1] |= c
        else:
            merged.append(set(c))
    assigned = {i for m in merged for i in m}
    unassigned = [i for i in range(len(staves)) if i not in assigned]
    return [sorted(m) for m in merged], unassigned


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages-per-edition", type=int, default=12)
    ap.add_argument("--first-page", type=int, default=2)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = []
    for tag, pdf in scan_editions():
        for pg in range(args.first_page,
                        args.first_page + args.pages_per_edition):
            try:
                pi = render_page(str(pdf), pg, dpi=args.dpi)
                staves = sorted(detect_staves(pi).staves, key=lambda s: s.top_y)
            except Exception as exc:                          # noqa: BLE001
                print(f"{tag} p{pg}: FAILED {exc}", flush=True)
                continue
            if len(staves) < 2:
                continue
            by_sys: dict[int, list[int]] = defaultdict(list)
            for i, s in enumerate(staves):
                by_sys[s.system_index].append(i)
            incumbent = [sorted(v) for _k, v in sorted(by_sys.items())]
            strokes = page_strokes(pi.binary, staves)
            read, unassigned = induced_partition(strokes, staves)
            exact = read == incumbent
            rows.append({
                "tag": tag, "page": pg, "n_staves": len(staves),
                "incumbent": incumbent, "read": read,
                "unassigned": unassigned, "exact": exact,
                "inc_sizes": [len(b) for b in incumbent],
                "read_sizes": [len(b) for b in read],
            })
            print(f"{tag} p{pg} n={len(staves):2d} inc={rows[-1]['inc_sizes']} "
                  f"read={rows[-1]['read_sizes']} "
                  f"unassigned={len(unassigned)} "
                  f"{'EXACT' if exact else ''}", flush=True)

    Path(args.out).write_text(json.dumps(rows, indent=1))

    print("\n== does the left edge define the SYSTEM? ==")
    print(f"{'publisher':<12} {'pages':>6} {'exact':>6} {'≥1 unassigned':>14} "
          f"{'over-split':>11} {'under-split':>12}")
    per: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        per[r["tag"]].append(r)
    for pub in sorted(per) + ["TOTAL"]:
        rs = rows if pub == "TOTAL" else per[pub]
        print(f"{pub:<12} {len(rs):>6} {sum(r['exact'] for r in rs):>6} "
              f"{sum(bool(r['unassigned']) for r in rs):>14} "
              f"{sum(len(r['read']) > len(r['incumbent']) for r in rs):>11} "
              f"{sum(len(r['read']) < len(r['incumbent']) for r in rs):>12}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
