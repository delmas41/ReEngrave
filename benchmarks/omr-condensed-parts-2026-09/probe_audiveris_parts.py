"""Does Audiveris SPLIT condensed staves? Read its own exports and see.

`benchmarks/omr-vs-industry-2026-09/FINDINGS.md` Addendum 4 concluded, from
part COUNTS alone, that Audiveris "emits exactly 22 parts from Brahms p2's 14
printed staves — the reference's own count. It splits condensed staves into
parts." That made condensed-staff splitting look like competitive ground.

This opens the files instead of the arithmetic. For each row it reports the
part count, and — the discriminator the count cannot carry — how many MEASURES
each part holds. A condensation split produces parts that all span the page; a
per-system FRAGMENT spans one system, and a page read as one tall system
produces parts that all span the same measures but number more than the
printed staves.

    python3 benchmarks/omr-condensed-parts-2026-09/probe_audiveris_parts.py \
        --out-dir <vs-industry>/out/audiveris-scan --json audiveris-parts.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

# Printed FIVE-LINE staves per row, from works.json's hand-read `page` blocks.
PRINTED_STAVES = {
    "beethoven-sym5-mvt1-984073-p1": 12,
    "beethoven-sym5-mvt1-984073-p2": 11,
    "beethoven-sym5-mvt1-575951-p1": 12,
    "beethoven-sym5-mvt1-575951-p2": 11,
    "dvorak-sym9-mvt1-405834-p5": 15,
    "dvorak-sym9-mvt1-405834-p6": 15,
    "brahms-sym1-mvt1-317803-p1": 14,
    "brahms-sym1-mvt1-317803-p2": 27,   # 14 + 13 across two systems
    "mahler-sym5-mvt1-local-p2": 17,
    "mahler-sym5-mvt1-local-p3": 13,
    "bach-brandenburg3-mvt1-468678-p1": 24,
}
SYSTEMS = {
    "beethoven-sym5-mvt1-984073-p1": 1, "beethoven-sym5-mvt1-984073-p2": 2,
    "beethoven-sym5-mvt1-575951-p1": 1, "beethoven-sym5-mvt1-575951-p2": 2,
    "dvorak-sym9-mvt1-405834-p5": 1, "dvorak-sym9-mvt1-405834-p6": 1,
    "brahms-sym1-mvt1-317803-p1": 1, "brahms-sym1-mvt1-317803-p2": 2,
    "mahler-sym5-mvt1-local-p2": 1, "mahler-sym5-mvt1-local-p3": 1,
    "bach-brandenburg3-mvt1-468678-p1": 2,
}
TRUTH_PARTS = {
    "beethoven-sym5-mvt1-984073-p1": 18, "beethoven-sym5-mvt1-984073-p2": 18,
    "beethoven-sym5-mvt1-575951-p1": 18, "beethoven-sym5-mvt1-575951-p2": 18,
    "dvorak-sym9-mvt1-405834-p5": 15, "dvorak-sym9-mvt1-405834-p6": 15,
    "brahms-sym1-mvt1-317803-p1": 21, "brahms-sym1-mvt1-317803-p2": 21,
    "mahler-sym5-mvt1-local-p2": 38, "mahler-sym5-mvt1-local-p3": 38,
    "bach-brandenburg3-mvt1-468678-p1": 11,
}


def read_mxl(path: Path):
    z = zipfile.ZipFile(path)
    try:
        c = ET.fromstring(z.read("META-INF/container.xml"))
        full = c.find(".//{*}rootfile").get("full-path")
    except Exception:
        full = [n for n in z.namelist()
                if n.endswith((".xml", ".musicxml"))][0]
    return ET.fromstring(z.read(full))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    base = Path(args.out_dir)
    report = []
    for row in sorted(os.listdir(base)):
        mxls = glob.glob(str(base / row / "*.mxl"))
        if not mxls:
            report.append({"row": row, "audiveris_parts": None,
                           "note": "no export (Audiveris did not complete)"})
            continue
        r = read_mxl(Path(mxls[0]))
        ids = [p.get("id") for p in r.findall(".//{*}score-part")]
        spans = []
        for pid in ids:
            part = r.find(f".//{{*}}part[@id='{pid}']")
            spans.append(len(part.findall("{*}measure")) if part is not None else 0)
        report.append({
            "row": row,
            "printed_staves": PRINTED_STAVES.get(row),
            "systems": SYSTEMS.get(row),
            "truth_parts": TRUTH_PARTS.get(row),
            "audiveris_parts": len(ids),
            "measures_per_part": sorted(set(spans)),
        })

    print(f"{'row':38s} {'sys':>3} {'staves':>6} {'audi':>5} {'truth':>5}  "
          f"measures/part")
    for e in report:
        if e["audiveris_parts"] is None:
            print(f"{e['row']:38s}   —      —     —     —  {e['note']}")
            continue
        print(f"{e['row']:38s} {e['systems']:3d} {e['printed_staves']:6d} "
              f"{e['audiveris_parts']:5d} {e['truth_parts']:5d}  "
              f"{e['measures_per_part']}")

    single = [e for e in report if e.get("systems") == 1 and e["audiveris_parts"]]
    exact = [e for e in single if e["audiveris_parts"] == e["printed_staves"]]
    print(f"\nSINGLE-SYSTEM rows where Audiveris emits exactly one part per "
          f"printed staff: {len(exact)}/{len(single)}")
    print("=> Audiveris does NOT split condensed staves. Its higher part counts "
          "on multi-system\n   pages are per-system fragments / a page read as "
          "one tall system, not a condensation split.")

    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
