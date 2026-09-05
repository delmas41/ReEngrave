"""What does the REFERENCE encode for a staff the print condenses?

Before designing a split, read the convention. For every printed staff that
`works.json` maps to more than one reference part, this dumps the parts' note
content over the row's measure window and classifies each measure:

  unison    the parts sound the SAME pitches at the same onsets
  divisi    both sound, and they differ (the page prints a chord or two voices)
  solo      exactly one part sounds, the other is silent  (`a 1` / `1.` / `2.`)
  silent    neither sounds

The engraving prints ONE staff in every one of those cases. A split rule has to
produce whichever the reference holds, so the shares here decide the rule.

    python3 benchmarks/omr-condensed-parts-2026-09/probe_truth_convention.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.library.score_library import library_root  # noqa: E402
from tools.omr.training.musicxml_truth import load_truth  # noqa: E402


def measure_signature(part, m):
    """(onset, pitch) multiset for one measure of one part; None if absent."""
    for mm in part.measures:
        if mm.number == m:
            out = []
            for n in mm.notes:
                if n.rest or n.grace:
                    continue
                out.append((round(float(n.onset_ql), 4), n.pitch))
            return sorted(out)
    return None


def classify(sigs):
    if any(s is None for s in sigs):
        return "absent"
    sounding = [s for s in sigs if s]
    if not sounding:
        return "silent"
    if len(sounding) < len(sigs):
        return "solo"
    first = sigs[0]
    if all(s == first for s in sigs[1:]):
        return "unison"
    return "divisi"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", default=str(
        ROOT / "benchmarks/omr-scan-e2e-2026-09/works.json"))
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    works = json.loads(Path(args.works).read_text())
    lib = library_root()
    rows_by_id = {r["row_id"]: r for r in works["rows"]}
    report = []
    pooled = Counter()
    cache = {}

    for row in works["rows"]:
        staves = row.get("staves")
        if isinstance(staves, str):
            ref_row = staves.split(":", 1)[-1].strip()
            staves = rows_by_id.get(ref_row, {}).get("staves")
        if not staves or isinstance(staves, str):
            continue
        ref = row["reference"]
        path = lib / ref["catalog_path"]
        if not path.exists():
            print(f"  !! missing {path}")
            continue
        if str(path) not in cache:
            cache[str(path)] = load_truth(path)
        truth = cache[str(path)]
        win = row["window"]
        lo, hi = win["first_ref_measure"], win["last_ref_measure"]

        rowrep = {"row_id": row["row_id"], "groups": []}
        for si, st in enumerate(staves):
            pidx = st.get("parts") or []
            if len(pidx) < 2:
                continue
            group = [truth.parts[p] for p in pidx]
            counts = Counter()
            examples = {}
            for m in range(lo, hi + 1):
                k = classify([measure_signature(p, m) for p in group])
                counts[k] += 1
                pooled[k] += 1
                examples.setdefault(k, m)
            rowrep["groups"].append({
                "staff": si, "name": st.get("name"), "parts": pidx,
                "part_names": [p.name for p in group],
                "counts": dict(counts), "first_example": examples,
            })
        report.append(rowrep)

    for r in report:
        if not r["groups"]:
            continue
        print(f"\n=== {r['row_id']}")
        for g in r["groups"]:
            c = g["counts"]
            print(f"  staff {g['staff']:2d} {str(g['name'])[:22]:22s} "
                  f"parts={g['parts']} "
                  f"unison={c.get('unison',0):3d} divisi={c.get('divisi',0):3d} "
                  f"solo={c.get('solo',0):3d} silent={c.get('silent',0):3d} "
                  f"absent={c.get('absent',0):3d}")
    print("\nPOOLED over every condensed staff-measure:")
    tot = sum(pooled.values()) or 1
    for k, v in pooled.most_common():
        print(f"   {k:8s} {v:5d}  {100*v/tot:5.1f}%")

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"rows": report, "pooled": dict(pooled)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
