#!/usr/bin/env python3
"""Is "no music anywhere in this column" a rule, or a threshold in disguise?

RESULTS.md §1 found system furniture read as a measure at both ends of a
system — a 56-px cell on Dvorak whose only detection is a `brace`, a 113-px cell
on Brahms holding one `timeSig9` — and it checked WIDTH before proposing it:
genuine measures run 4.2 to 28.7 staff spaces against 2.2 and 3.5 for the two
spurious ones, a 0.7-space gap on a five-page corpus. That is a threshold to
tune, not a cliff to sit on. It proposed CONTENT instead.

This is the check that has to come before implementing that, and it asks the
question at the level the answer lives at. **A barline spans the system**, so a
measure column is furniture for every staff of a system or for none of them —
per-staff emptiness says nothing (any staff may be tacet), while a column where
not one staff of fifteen carries a notehead or a rest is a different object.

    python3 benchmarks/omr-scan-e2e-2026-09/probe_furniture_columns.py

Reads committed `*.omr.json` transcriptions only — no rendering, no detector, no
CPU window. "Has music" is `voicing.group_chords_in_measure`, which is the
EXPORTER's own definition of a non-empty measure, so the rule and the thing it
protects cannot drift apart.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.voicing import group_chords_in_measure  # noqa: E402

#: Every transcription in the repo that is a real page of a real edition.
#: The `.w20` / `.dpi321` scan arms are side experiments on pages already here
#: and would double-count them.
SOURCES = (
    "benchmarks/omr-corpus-widening-2026-09/fixtures",
    "benchmarks/omr-orchestral-e2e/fixtures",
    "benchmarks/omr-scan-e2e-2026-09/fixtures",
    "benchmarks/omr-keysig-from-music-2026-09/artifacts",
)
SKIP_SUFFIXES = (".w20.omr.json", ".dpi321.omr.json")


def columns(result: dict):
    """One row per (file, page, system, measure index) column."""
    for page in result.get("pages", []):
        for sys_idx, system in enumerate(page.get("systems", [])):
            staves = system.get("staves", [])
            if not staves:
                continue
            width = max(len(s.get("measures", [])) for s in staves)
            spacing = None
            for s in staves:
                geo = s.get("staff_geometry") or {}
                sp = geo.get("line_spacing_px") or s.get("line_spacing_px")
                if sp:
                    spacing = float(sp)
                    break
            for m in range(width):
                cells = [s["measures"][m] for s in staves
                         if m < len(s.get("measures", []))]
                if not cells:
                    continue
                music = sum(1 for c in cells
                            if group_chords_in_measure(c.get("detections") or []))
                cats: Counter = Counter()
                for c in cells:
                    for d in c.get("detections") or []:
                        cats[d.get("category")] += 1
                boxes = [c.get("bbox_page_px") for c in cells
                         if c.get("bbox_page_px")]
                px = max((b[2] - b[0]) for b in boxes) if boxes else 0
                yield {
                    "page": page.get("page_index"), "system": sys_idx,
                    "m": m, "of": width, "n_staves": len(cells),
                    "music_staves": music, "cats": dict(cats),
                    "width_px": px,
                    "width_spaces": round(px / spacing, 2) if spacing else None,
                }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    rows, silent = [], []
    for src in SOURCES:
        for path in sorted((ROOT / src).glob("*.omr.json")):
            if any(path.name.endswith(s) for s in SKIP_SUFFIXES):
                continue
            result = json.loads(path.read_text())
            for col in columns(result):
                col["file"] = path.name
                rows.append(col)
                if col["music_staves"] == 0:
                    silent.append(col)

    files = len({r["file"] for r in rows})
    systems = len({(r["file"], r["page"], r["system"]) for r in rows})
    print(f"{len(rows)} measure columns over {systems} systems in {files} "
          f"transcriptions\n")

    print(f"columns where NOT ONE staff carries a notehead or a rest: "
          f"{len(silent)} of {len(rows)} ({100.0 * len(silent) / max(1, len(rows)):.2f}%)\n")
    print(f"  {'file':44s} {'sys':>3s} {'m':>3s}/{'of':<3s} {'staves':>6s} "
          f"{'px':>6s} {'spaces':>7s}  categories present")
    for c in sorted(silent, key=lambda c: (c["file"], c["system"], c["m"])):
        cats = ", ".join(f"{k}×{v}" for k, v in sorted(c["cats"].items())) or "(nothing)"
        sp = f"{c['width_spaces']:.2f}" if c["width_spaces"] else "?"
        print(f"  {c['file'][:44]:44s} {c['system']:>3d} {c['m']:>3d}/{c['of']:<3d} "
              f"{c['n_staves']:>6d} {c['width_px']:>6d} {sp:>7s}  {cats}")

    # The counter-population: what the rule must NOT touch.
    voiced = [r for r in rows if r["music_staves"] > 0]
    thin = sorted(voiced, key=lambda r: r["music_staves"])[:8]
    print(f"\n  the genuine columns with the FEWEST playing staves — the ones a "
          f"content rule\n  comes closest to deleting:")
    for c in thin:
        print(f"  {c['file'][:44]:44s} {c['system']:>3d} {c['m']:>3d}/{c['of']:<3d} "
              f"{c['music_staves']:>3d} of {c['n_staves']:<3d} staves play")

    if args.out:
        args.out.write_text(json.dumps(rows, indent=1) + "\n")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
