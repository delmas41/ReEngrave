"""Does the bracket-column change REACH the pipeline's output at all?

`Staff.group_index` has exactly two consumers:

  1. `measure_extractor._is_grouped_system` — cue C of `OMR_CHOIR_GROUPING`,
     which can flip a system out of open-score mode and therefore change its
     BARLINES. This is the one that moves OMR-NED, and it is the one that
     falsified an earlier bracket-group rule on the engraved benchmark.
  2. `slots.py` — part naming, measured elsewhere in this repo to change the
     score by exactly nothing.

So cue C is the reachable risk, and it is exactly checkable without running
the detector: `_is_grouped_system` and `_window_blind_systems` are both
model-free. This dumps both, per system, under each arm — an EXACT control,
where a full benchmark A/B on the 20-row scan gate would carry a ±6-edit noise
floor and hours of wall time.

Usage: probe_cue_c_reach.py --corpus scan [--pages-per-edition 24]
       probe_cue_c_reach.py PDF... --pages=0
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.preprocessing import render_page                      # noqa: E402
from tools.omr.staff_detector import detect_staves                   # noqa: E402
from tools.omr.measure_extractor import (                            # noqa: E402
    _is_grouped_system, _window_blind_systems)

WORKS = Path("/Users/seanjohnson/Desktop/ReEngrave/benchmarks/"
             "omr-scan-e2e-2026-09/works.json")
LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")


def arm(pi, flag: str) -> dict:
    os.environ["OMR_BRACKET_COLUMNS"] = flag
    pws = detect_staves(pi)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    blind = _window_blind_systems(pi.binary, pws.staves)
    by_system: dict[int, list] = {}
    for s in staves:
        by_system.setdefault(s.system_index, []).append(s)
    return {
        "grouped": {k: _is_grouped_system(v) for k, v in sorted(by_system.items())},
        "blind": sorted(blind),
        "groups": {k: [s.group_index for s in v] for k, v in sorted(by_system.items())},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="*")
    ap.add_argument("--corpus", choices=["scan", "gate"], default=None)
    ap.add_argument("--pages", default="0")
    ap.add_argument("--pages-per-edition", type=int, default=24)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out")
    args = ap.parse_args()

    targets: list[tuple[str, Path, list[int]]] = []
    if args.corpus == "gate":
        # exactly the 20 hand-verified rows of the scan benchmark
        for r in json.loads(WORKS.read_text())["rows"]:
            targets.append((r["row_id"], LIB / r["edition"]["catalog_path"],
                            [r["page"]["pdf_page_index"]]))
    elif args.corpus == "scan":
        import fitz
        seen: dict[str, Path] = {}
        for r in json.loads(WORKS.read_text())["rows"]:
            seen.setdefault(r["edition"]["catalog_path"],
                            LIB / r["edition"]["catalog_path"])
        for name, path in sorted(seen.items()):
            n = fitz.open(path).page_count
            targets.append((name, path, list(range(min(n, args.pages_per_edition)))))
    for p in args.pdfs:
        pages = []
        for tok in args.pages.split(","):
            if "-" in tok:
                a, b = tok.split("-")
                pages.extend(range(int(a), int(b) + 1))
            else:
                pages.append(int(tok))
        targets.append((Path(p).name, Path(p), pages))

    rows, n_diff, n_same = [], 0, 0
    for name, path, pages in targets:
        for p in pages:
            try:
                pi = render_page(str(path), p, dpi=args.dpi)
            except Exception as exc:                                 # noqa: BLE001
                print(f"  !! {name} p{p}: {exc}")
                continue
            off, on = arm(pi, "0"), arm(pi, "1")
            same = off["grouped"] == on["grouped"]
            n_same += same
            n_diff += not same
            rows.append({"name": name, "page": p, "off": off, "on": on,
                         "cue_c_same": same})
            print(f"{'  same' if same else '  CUE-C DIFF'}  {name} p{p}  "
                  f"blind={off['blind']}  "
                  f"grouped off={list(off['grouped'].values())} "
                  f"on={list(on['grouped'].values())}", flush=True)
    print(f"\ncue C input identical on {n_same} pages, different on {n_diff}")
    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
