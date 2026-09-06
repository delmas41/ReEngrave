"""A/B the `group_index` vectors of a set of PDFs, flag off vs flag on.

`group_index` is not serialised into any benchmark artifact, so a downstream
A/B cannot see whether it moved.  This asks the question directly, in ONE
process (the flag is read per call, so both arms share the render and the staff
detection — no caching trap, and no chance of the two arms seeing different
staves).

Usage: ab_group_vectors.py --pages=0 PDF...
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.preprocessing import render_page          # noqa: E402
from tools.omr.staff_detector import detect_staves       # noqa: E402
from tools.omr import system_grouping as sg              # noqa: E402


def vectors(pi, flag: str) -> list[list[int]]:
    os.environ["OMR_BRACKET_COLUMNS"] = flag
    pws = detect_staves(pi)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    by_system: dict[int, list[int]] = {}
    for s in staves:
        by_system.setdefault(s.system_index, []).append(s.group_index)
    return [by_system[k] for k in sorted(by_system)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--pages", default="0")
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

    rows, n_same, n_diff = [], 0, 0
    for pdf in args.pdfs:
        for p in pages:
            try:
                pi = render_page(pdf, p, dpi=args.dpi)
            except Exception as exc:                      # noqa: BLE001
                print(f"  !! {Path(pdf).name} p{p}: {exc}")
                continue
            off = vectors(pi, "0")
            on = vectors(pi, "1")
            same = off == on
            n_same += same
            n_diff += not same
            rows.append({"pdf": Path(pdf).name, "page": p,
                         "off": off, "on": on, "same": same})
            mark = "  same" if same else "  DIFF"
            print(f"{mark}  {Path(pdf).name} p{p}")
            if not same:
                for a, b in zip(off, on):
                    if a != b:
                        print(f"        off {''.join(map(str, a))}")
                        print(f"        on  {''.join(map(str, b))}")
    print(f"\n{n_same} identical, {n_diff} changed")
    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
