#!/usr/bin/env python3
"""REACH FIRST: how many CANDIDATE COLUMNS does a document actually carry?

The design this probe exists to size is *"one staff's detection names the
COLUMN; the template reader is then asked of every staff of that system at
that same bar"*. Its whole cost, and its whole false-positive surface, is

    sum over candidate columns of (staves on that column's system)

so that number has to be known before a line of the search is written. If it
is close to *every* bar of the page the design is wrong as briefed, and this
probe is what says so.

⚠️ IT READS COMMITTED LEGACY TRANSCRIPTIONS, NOT A FRESH GATHER. A cloud
container has no weights and no library, so the only real detector output
available is what is already on disk under `benchmarks/`. That is a real
limit and it is stated in FINDINGS rather than worked around: these are the
detections a past run made, with past weights, on those pages.

`--check` exits non-zero when the probe assessed NOTHING — a dead instrument
must never read as a clean result. It never fails on a threshold: a candidate
count is a property of the document, not a score to drive down.

    python3 benchmarks/omr-meter-template-changes-2026-09/probe/candidate_columns.py
    python3 .../candidate_columns.py --check
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[3]

#: Committed legacy transcriptions holding real detector output. Each is
#: (label, path, what it is) — the third field so a reader knows which
#: publisher and which weights era a row belongs to.
SOURCES = [
    ("brahms1-breitkopf-p1-3",
     "benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json",
     "Brahms 1 / Breitkopf, 3 pages, 83 staves — the scan gate's own row"),
    ("beet5-litolff-p1",
     "benchmarks/omr-clef-demo/beet5_p1_production.omr.json",
     "Beethoven 5 / Litolff p.1 — a MOVEMENT OPENING (meter in the header)"),
    ("mahler5-peters-p11",
     "benchmarks/omr-clef-demo/mahler_p11_production.omr.json",
     "Mahler 5 / Peters p.11 — a continuation page"),
]


def _is_meter_shaped(det: dict) -> bool:
    return str(det.get("class", "")).startswith("timeSig")


def survey(path: pathlib.Path) -> dict:
    doc = json.loads(path.read_text())
    staves_of: dict[tuple, set] = defaultdict(set)
    #: column -> set of staves carrying >=1 meter-shaped detection there
    hit_staves: dict[tuple, set] = defaultdict(set)
    #: column -> set of staves carrying >=2 of them (a digit PAIR is possible)
    hit_staves_2: dict[tuple, set] = defaultdict(set)
    all_columns: set = set()
    n_cells = 0
    n_noncells = 0

    for page in doc.get("pages") or []:
        p = page.get("page_index", 0)
        for si, system in enumerate(page.get("systems") or []):
            for staff in system.get("staves") or []:
                st = staff.get("staff_index")
                staves_of[(p, si)].add(st)
                for measure in staff.get("measures") or []:
                    mi = measure.get("measure_index")
                    n_cells += 1
                    all_columns.add((p, si, mi))
                    if mi == 0:
                        continue          # cell 0 states the staff's OPENING
                    n_noncells += 1
                    marks = [d for d in (measure.get("detections") or [])
                             if _is_meter_shaped(d)]
                    if marks:
                        hit_staves[(p, si, mi)].add(st)
                        if len(marks) >= 2:
                            hit_staves_2[(p, si, mi)].add(st)

    n_staff_systems = sum(len(v) for v in staves_of.values())

    def probes(columns) -> int:
        return sum(len(staves_of[(p, s)]) for (p, s, _m) in columns)

    gates = {}
    for k in (1, 2, 3, 4, 5):
        cols = [c for c, v in hit_staves.items() if len(v) >= k]
        gates[f">= {k} staff/staves carry a meter-shaped detection"] = {
            "columns": len(cols), "probes": probes(cols)}
    for k in (1, 2, 3):
        cols = [c for c, v in hit_staves_2.items() if len(v) >= k]
        gates[f">= {k} staff/staves carry TWO of them"] = {
            "columns": len(cols), "probes": probes(cols)}

    return {
        "cells": n_cells,
        "non_opening_cells": n_noncells,
        "columns_total": len(all_columns),
        "columns_non_opening": len(all_columns) - len(
            {(p, s, m) for (p, s, m) in all_columns if m == 0}),
        "staff_systems": n_staff_systems,
        "header_probes_today": n_staff_systems,
        "gates": gates,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if the probe assessed nothing")
    ap.add_argument("--json", type=pathlib.Path, default=None)
    args = ap.parse_args(argv)

    out: dict[str, dict] = {}
    assessed = 0
    for label, rel, what in SOURCES:
        path = ROOT / rel
        if not path.is_file():
            print(f"{label}: MISSING {rel}")
            continue
        res = survey(path)
        res["what"] = what
        out[label] = res
        assessed += 1
        print(f"\n{label}  —  {what}")
        print(f"  cells {res['cells']}  non-opening {res['non_opening_cells']}"
              f"  staff-systems {res['staff_systems']}")
        print(f"  columns on the page: {res['columns_total']}")
        print(f"  header probes today: {res['header_probes_today']}")
        for gate, v in res["gates"].items():
            share = (v["columns"] / res["columns_total"]
                     if res["columns_total"] else 0.0)
            print(f"    {gate:<52} columns {v['columns']:>3}"
                  f" ({share:5.1%})   probes {v['probes']:>4}")

    if args.json:
        args.json.write_text(json.dumps(out, indent=1))
        print(f"\nwrote {args.json}")

    if args.check and assessed == 0:
        print("\nDEAD: no committed transcription was read. "
              "This is not a clean result.", file=sys.stderr)
        return 2
    print(f"\nassessed {assessed} documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
