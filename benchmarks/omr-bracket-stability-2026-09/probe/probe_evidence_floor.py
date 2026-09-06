"""How much evidence does a system actually carry about its bracket groups?

The bracket-group rule's premise is that interior barlines STOP at a group
edge. That premise is only testable where interior barlines cross gaps at all.
This dumps, per system, the MEDIAN number of informative (non-spanning,
recurring) crossing columns at its gaps — the quantity the ratio is taken
against — so a floor can be placed on a measured gap rather than guessed.

Usage: probe_evidence_floor.py --label scan  PDF... --pages=0-23
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
from tools.omr import system_grouping as sg              # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--pages", default="0")
    ap.add_argument("--label", default="corpus")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out")
    args = ap.parse_args()

    pages: list[int] = []
    for tok in args.pages.split(","):
        if "-" in tok:
            a, b = tok.split("-")
            pages.extend(range(int(a), int(b) + 1))
        else:
            pages.append(int(tok))

    rows = []
    for pdf in args.pdfs:
        for p in pages:
            try:
                pi = render_page(pdf, p, dpi=args.dpi)
            except Exception:                             # noqa: BLE001
                continue
            pws = detect_staves(pi)
            staves = sorted(pws.staves, key=lambda s: s.top_y)
            if len(staves) < 2:
                continue
            runs = sg.gap_crossing_runs(pi.binary, staves)
            by_system: dict[int, list[int]] = {}
            for i, s in enumerate(staves):
                by_system.setdefault(s.system_index, []).append(i)
            for sys_idx, members in sorted(by_system.items()):
                if len(members) < 3:
                    continue
                gaps = members[:-1]
                spacing = statistics.median(
                    [staves[i].line_spacing_px for i in members]) or 1.0
                local = sg.systemic_column_counts([runs[i] for i in gaps], spacing)
                live = [n for n in local if n >= 0]
                px = [sum(w for _c, w in runs[i]) if runs[i] else 0 for i in gaps]
                rows.append({
                    "pdf": Path(pdf).name, "page": p, "system": sys_idx,
                    "n_staves": len(members),
                    "median_columns": statistics.median(live) if live else 0,
                    "median_px": statistics.median(px) if px else 0,
                    "columns": local,
                })
    meds = sorted(r["median_columns"] for r in rows)
    print(f"\n[{args.label}] {len(rows)} systems")
    print("  median informative columns per system, sorted:")
    print("   ", meds)
    from collections import Counter
    print("  histogram:", dict(sorted(Counter(meds).items())))
    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
