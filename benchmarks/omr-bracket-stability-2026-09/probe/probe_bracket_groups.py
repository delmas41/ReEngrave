"""Dump the bracket-group decision for every system on every page given.

`_assign_groups` is MODEL-FREE — it needs only the binarized page and the
staves, so this probe runs the whole decision without loading YOLO. That is
what makes a corpus-wide rate measurable at all.

For each system it prints the per-gap bridging counts, the median the threshold
is derived from, the threshold itself, and the resulting `group_index` vector,
plus each gap's RATIO to the median (the quantity `_assign_groups` actually
tests against 0.5).

Usage:
    probe_bracket_groups.py PDF --pages=23,31,38 [--dpi=600] [--json OUT.json]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.preprocessing import render_page          # noqa: E402
from tools.omr.staff_detector import detect_staves       # noqa: E402
from tools.omr.system_grouping import gap_bridging_counts, GROUP_BOUNDARY_RATIO  # noqa: E402


def page_report(pdf: str, page_index: int, dpi: int) -> dict:
    pi = render_page(pdf, page_index, dpi=dpi)
    pws = detect_staves(pi)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    bridging = gap_bridging_counts(pi.binary, staves)

    by_system: dict[int, list[int]] = {}
    for i, s in enumerate(staves):
        by_system.setdefault(s.system_index, []).append(i)

    systems = []
    for sys_idx in sorted(by_system):
        members = by_system[sys_idx]
        inner = [bridging[i] for i in members[:-1] if bridging[i] >= 0]
        median = statistics.median(inner) if inner else None
        thr = median * GROUP_BOUNDARY_RATIO if median is not None else None
        systems.append({
            "system_index": sys_idx,
            "n_staves": len(members),
            "inner_bridging": [bridging[i] for i in members[:-1]],
            "median": median,
            "threshold": thr,
            "ratios": ([round(bridging[i] / median, 3) if median else None
                        for i in members[:-1]] if median else None),
            "groups": [staves[i].group_index for i in members],
            "n_groups": len(set(staves[i].group_index for i in members)),
        })
    return {"page_index": page_index, "n_staves": len(staves), "systems": systems}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--pages", required=True,
                    help="comma list and/or a-b ranges, 0-based PDF page indices")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--json")
    args = ap.parse_args()

    pages: list[int] = []
    for tok in args.pages.split(","):
        if "-" in tok:
            a, b = tok.split("-")
            pages.extend(range(int(a), int(b) + 1))
        else:
            pages.append(int(tok))

    out = []
    for p in pages:
        rep = page_report(args.pdf, p, args.dpi)
        out.append(rep)
        print(f"\n=== page {p}  ({rep['n_staves']} staves) ===")
        for s in rep["systems"]:
            print(f"  system {s['system_index']}  {s['n_staves']} staves"
                  f"  median={s['median']}  thr={s['threshold']}")
            print(f"    bridging {s['inner_bridging']}")
            print(f"    ratios   {s['ratios']}")
            print(f"    groups   {s['groups']}   ({s['n_groups']} groups)")

    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
