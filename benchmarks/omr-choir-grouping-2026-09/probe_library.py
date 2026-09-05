#!/usr/bin/env python3
"""Guard 5: cue B across the library page population.

Re-uses the (pdf_rel, page, dpi) population of the left-edge work's 977-row
sweep (benchmarks/omr-system-grouping-2026-09/sweep.jsonl — the '964-page
probe' plus its error rows), renders each page the same way, detects staves
once, and records the grouping partition with OMR_CHOIR_GROUPING off and on,
plus cue B's per-gap evidence (pair-anchored left-band count at every gap the
wide rule broke). Grouping-only — no YOLO, no weights.

What it prices:
  * how often cue B fires at all, and on which pages (the family size);
  * the count distribution at gaps it examines — the population the
    CHOIR_MERGE_MIN_CROSS floor must be read off;
  * candidate false merges: pages where flag-on yields FEWER systems than the
    flag-off partition at gaps that are plausibly true breaks (adjudicated by
    crops afterwards, make_crops-style).

Cue C (barline-stage) is out of scope here by construction: this probe stops
at grouping. Its pricing comes from the scan rows and the engraved benchmark.

Usage:
    python3 probe_library.py                 # full population, resumable
    python3 probe_library.py --limit 50      # cap this invocation
Output: probe_library.jsonl (one row per page).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKTREE_ROOT = HERE.parents[1]
sys.path.insert(0, str(WORKTREE_ROOT))

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr import system_grouping as sg  # noqa: E402

LIBRARY_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave/library/editions")
SWEEP = WORKTREE_ROOT / "benchmarks/omr-system-grouping-2026-09/sweep.jsonl"
OUT = HERE / "probe_library.jsonl"


def population() -> list[dict]:
    rows = []
    for line in SWEEP.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("error"):
            continue
        rows.append({"pdf_rel": r["pdf_rel"], "page": r["page"], "dpi": r["dpi"]})
    return rows


def partition(staves) -> list[int]:
    from collections import Counter
    c = Counter(s.system_index for s in staves)
    return [c[k] for k in sorted(c)]


def probe_page(pdf: Path, page_idx: int, dpi: int) -> dict:
    page = render_page(pdf, page_idx, dpi=dpi)
    # detect_staves applies grouping internally with ambient env; grouping
    # only mutates system/group indices, so run it once and then re-run
    # assign_systems on the same staves for each arm.
    pws = detect_staves(page)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    if len(staves) < 2:
        return {"n_staves": len(staves), "skipped": "under 2 staves"}

    off, used_off = sg.assign_systems(page.binary, list(staves),
                                      left_edge_split=True, choir_grouping=False)
    part_off = partition(off)
    sizes_off = [s.system_index for s in off]

    bridging = sg.gap_bridging_counts(page.binary, staves)
    gaps = []
    for i, (u, l) in enumerate(zip(staves, staves[1:])):
        overlap = sg._x_overlap_frac(u, l)
        entry = {"i": i, "bridging": bridging[i],
                 "overlap": round(overlap, 3),
                 "gap_px": l.top_y - u.bottom_y}
        if bridging[i] == 0 and overlap > sg.MIN_X_OVERLAP_FRAC:
            entry["pair_left"] = sg.pair_left_edge_count(page.binary, u, l)
            entry["x_starts"] = [u.x_start, l.x_start]
        gaps.append(entry)

    on, used_on = sg.assign_systems(page.binary, list(staves),
                                    left_edge_split=True, choir_grouping=True)
    part_on = partition(on)

    fired = [g["i"] for g in gaps
             if g.get("pair_left", 0) >= sg.CHOIR_MERGE_MIN_CROSS]
    return {
        "n_staves": len(staves),
        "used_bridging": bool(used_off),
        "partition_off": part_off,
        "partition_on": part_on,
        "changed": part_off != part_on,
        "cue_b_examined": [g for g in gaps if "pair_left" in g],
        "cue_b_fired_gaps": fired,
        "x_starts": [s.x_start for s in staves],
        "tops": [s.top_y for s in staves],
        "bottoms": [s.bottom_y for s in staves],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    done = set()
    if args.out.exists():
        for line in args.out.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done.add((r["pdf_rel"], r["page"]))

    rows = [r for r in population() if (r["pdf_rel"], r["page"]) not in done]
    if args.limit:
        rows = rows[: args.limit]
    print(f"{len(rows)} pages to probe ({len(done)} already done)", flush=True)

    n = 0
    with args.out.open("a") as fh:
        for r in rows:
            pdf = LIBRARY_ROOT / r["pdf_rel"]
            out = {"pdf_rel": r["pdf_rel"], "page": r["page"], "dpi": r["dpi"]}
            try:
                if not pdf.exists():
                    out["error"] = "missing pdf"
                else:
                    out.update(probe_page(pdf, r["page"], r["dpi"]))
                    out["error"] = None
            except Exception as exc:  # noqa: BLE001
                out["error"] = f"{type(exc).__name__}: {exc}"
            fh.write(json.dumps(out) + "\n")
            fh.flush()
            n += 1
            if out.get("changed"):
                print(f"CHANGED {r['pdf_rel']} p{r['page']}: "
                      f"{out['partition_off']} -> {out['partition_on']}", flush=True)
            if n % 50 == 0:
                print(f"  … {n}/{len(rows)}", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
