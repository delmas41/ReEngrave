#!/usr/bin/env python3
"""Measure every staff's HEADER WINDOW, and what decided its right edge.

    python3 benchmarks/omr-keysig-truth-2026-09/probe_windows.py

Both key-signature readers see only this window, so a window that stops before
the signature makes the locator abstain (it finds no run) and the template
answer a confident `0` (it finds a clean window) — one cause, two
different-looking failures, and neither reader is at fault for either.

Prints the window's width in STAFF SPACES rather than pixels, because that is
the unit the constants are written in and the unit a clef-plus-signature is
measured in: a clef is about 4 spaces wide and each accidental about 1, so a
3-flat header needs roughly 8 and cannot possibly fit in 5.
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

PDF = ("library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--"
       "imslp984073.pdf")
PAGES = [1, 2, 3, 4]


def main(argv: list[str]) -> int:
    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staged.gather import _system_local
    from tools.omr.staff_header import (DEFAULT_CONFIG, header_windows_for_page,
                                        system_left_edge)

    cfg = DEFAULT_CONFIG
    print(f"config: min_width_spaces={cfg.min_width_spaces} "
          f"max_width_spaces={cfg.max_width_spaces} "
          f"left_margin_spaces={cfg.left_margin_spaces}\n")

    rows = []
    for pws, _cells in prepare_pages(str(ROOT / PDF), PAGES):
        p = pws.page.page_index
        local = _system_local(pws.staves)
        wins = header_windows_for_page(pws)
        for sysi in sorted({s.system_index for s in pws.staves}):
            left = system_left_edge(pws, sysi, cfg)
            bls = sorted(bl.x for bl in pws.barlines if bl.system_index == sysi)
            print(f"-- page {p} system {sysi}: left_edge={left} "
                  f"first barlines {bls[:4]}")
            for st in sorted((s for s in pws.staves if s.system_index == sysi),
                             key=lambda x: x.top_y):
                _, i = local[st.staff_index]
                w = wins.get(st.staff_index)
                sp = max(1.0, st.line_spacing_px)
                if w is None:
                    print(f"   {i:>2}  NO WINDOW")
                    continue
                width_sp = (w.x1 - w.x0) / sp
                rows.append({"page": p, "system": sysi, "staff": i,
                             "x0": w.x0, "x1": w.x1,
                             "right_from": w.right_from,
                             "spacing": round(sp, 1),
                             "width_spaces": round(width_sp, 2)})
                flag = "  <-- TOO NARROW FOR A CLEF" if width_sp < 5 else ""
                print(f"   {i:>2}  x0={w.x0:>5} x1={w.x1:>5} "
                      f"spacing={sp:>5.1f}  width={width_sp:>5.2f} spaces "
                      f"({w.right_from}){flag}")

    narrow = [r for r in rows if r["width_spaces"] < 5]
    print(f"\nWINDOWS NARROWER THAN 5 STAFF SPACES: {len(narrow)} of "
          f"{len(rows)}  (a clef alone is about 4)")
    bysys: dict[tuple, int] = {}
    for r in narrow:
        bysys[(r["page"], r["system"])] = bysys.get((r["page"], r["system"]), 0) + 1
    for k, v in sorted(bysys.items()):
        print(f"  page {k[0]} system {k[1]}: {v}")
    print("\nright_from tally:",
          {k: sum(1 for r in rows if r["right_from"] == k)
           for k in sorted({r["right_from"] for r in rows})})
    json.dump(rows, (HERE / "windows.json").open("w"), indent=1)
    print(f"wrote {HERE / 'windows.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
