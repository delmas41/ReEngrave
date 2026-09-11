#!/usr/bin/env python3
"""Test `system_left_edge`'s stated invariant, per staff, on four real pages.

    python3 benchmarks/omr-keysig-truth-2026-09/probe_left_edge.py

`system_left_edge` takes the MINIMUM of its per-staff estimates, and its own
docstring says why that is safe:

    "the estimate can only ever be too far right and never too far left ...
     the wall rule is what makes the minimum safe: nothing can under-run past
     the bracket into the instrument names, so there is no runaway value for
     the minimum to prefer."

A minimum over eleven estimates is only as good as its worst one, so this is
the load-bearing claim in the module and it is worth a direct test. The
system's own OPENING RULE is a full-height vertical line at the head of the
system — the leftmost thing any staff of it can legitimately reach — so
`min(barline x)` for the system is an upper bound on the truth, and an
estimate materially LEFT of it has under-run into the margin.

⚠️ The comparison is one-sided on purpose. An estimate right of the rule is
the documented, harmless case (the staff stopped at a later barline and the
minimum discards it); only an estimate LEFT of the rule falsifies the
invariant, and only that is reported as a violation.
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
    from tools.omr.staff_header import (DEFAULT_CONFIG, _staff_left_candidate,
                                        system_left_edge)

    cfg = DEFAULT_CONFIG
    rows = []
    for pws, _cells in prepare_pages(str(ROOT / PDF), PAGES):
        p = pws.page.page_index
        for sysi in sorted({s.system_index for s in pws.staves}):
            staves = sorted((s for s in pws.staves if s.system_index == sysi),
                            key=lambda x: x.top_y)
            cands = [_staff_left_candidate(pws, s, cfg) for s in staves]
            bls = sorted(bl.x for bl in pws.barlines if bl.system_index == sysi)
            rule = bls[0] if bls else None
            got = system_left_edge(pws, sysi, cfg)
            sp = max(1.0, staves[0].line_spacing_px)
            under = [c for c in cands
                     if c is not None and rule is not None and c < rule - sp]
            rows.append({"page": p, "system": sysi, "opening_rule": rule,
                         "left_edge": got, "candidates": cands,
                         "under_running": len(under),
                         "shortfall_spaces": (round((rule - got) / sp, 2)
                                              if rule and got else None)})
            mark = "   <-- UNDER-RUNS THE OPENING RULE" if under else ""
            print(f"page {p} system {sysi}: opening rule x={rule}  "
                  f"left_edge={got}  shortfall="
                  f"{rows[-1]['shortfall_spaces']} spaces{mark}")
            print(f"    candidates: {cands}")

    bad = [r for r in rows if r["under_running"]]
    print(f"\nSYSTEMS WITH AT LEAST ONE UNDER-RUNNING ESTIMATE: "
          f"{len(bad)} of {len(rows)}")
    for r in bad:
        print(f"  page {r['page']} system {r['system']}: "
              f"{r['under_running']} of {len(r['candidates'])} estimates "
              f"land left of the opening rule; the minimum takes one of them "
              f"and the whole system's header window follows it")
    if not bad:
        print("  none — the invariant holds on every system measured here.")
    json.dump(rows, (HERE / "left-edge.json").open("w"), indent=1)
    print(f"\nwrote {HERE / 'left-edge.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
