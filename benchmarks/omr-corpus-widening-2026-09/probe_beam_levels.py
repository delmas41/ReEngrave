"""What the beam counter saw, per notehead, in a cell the durations went wrong in.

`probe_duration_ratios.py` names a fault by its RATIO. This one opens the cell
behind a ratio and prints the evidence the count was made from: the CV stems,
the CV and YOLO beams with their canonical y centres, the gaps between those
centres, and the clustering tolerance those gaps are compared against.

    python3 benchmarks/omr-corpus-widening-2026-09/probe_beam_levels.py \
        --work mozart-sym41-mvt1 --staff 1 --measure 0

Reads the .omr.json only — no re-detection — so it reports what the shipped
run actually did.

Host Python; needs nothing but the standard library.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def cells(doc):
    for p in doc["pages"]:
        for sy in p["systems"]:
            for st in sy["staves"]:
                for m in st["measures"]:
                    yield st, m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--fixtures", type=Path, default=FIXTURES)
    ap.add_argument("--staff", type=int)
    ap.add_argument("--measure", type=int)
    args = ap.parse_args()

    doc = json.load(open(args.fixtures / f"{args.work}.omr.json"))

    for st, m in cells(doc):
        if args.staff is not None and st["staff_index"] != args.staff:
            continue
        if args.measure is not None and m["measure_index"] != args.measure:
            continue
        nhs = [d for d in m["detections"] if d.get("category") == "notehead"]
        beams = [d for d in m["detections"]
                 if d.get("category") == "structural"
                 and "beam" in d.get("class", "").lower()]
        stems = [d for d in m["detections"]
                 if d.get("category") == "structural"
                 and "stem" in d.get("class", "").lower()]
        lines = m.get("staff_line_ys_canonical") or []
        spacing = ((max(lines) - min(lines)) / 4.0) if len(lines) >= 2 else 0.0
        print(f"\n=== staff {st['staff_index']} ({st.get('instrument')}) "
              f"m{m['measure_index']}  spacing={spacing:.1f}  "
              f"tol=0.35*sp={spacing * 0.35:.1f}")
        print(f"  {len(nhs)} noteheads, {len(beams)} beams, {len(stems)} stems")
        for d in sorted(beams, key=lambda d: d["bbox"][0]):
            x, y, w, h = d["bbox"]
            print(f"    BEAM  x={x:5.0f}..{x + w:5.0f}  yc={y + h / 2:7.1f}  "
                  f"h={h:4.0f}  {d.get('class')}  conf={d.get('confidence', 0):.2f}")
        for d in sorted(nhs, key=lambda d: d["bbox"][0]):
            x, y, w, h = d["bbox"]
            print(f"    NH    x={x:5.0f} yc={y + h / 2:7.1f} "
                  f"lvl={d.get('beam_levels')} dur={d.get('duration_beats')} "
                  f"{d.get('duration_type')} tup={d.get('tuplet')} "
                  f"pitch={d.get('pitch')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
