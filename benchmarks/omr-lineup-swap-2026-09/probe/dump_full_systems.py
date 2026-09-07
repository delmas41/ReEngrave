"""Print every FULL system's per-ordinal label sequence, one row per system.

Forensics for `ordinal_agreement.py` — a disagreement rate is a number; this is
what it is made of.

    dump_full_systems.py LABELS.json --lineups LINEUPS.json [--text]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from ordinal_agreement import full_systems  # noqa: E402

ABBR = {
    "Flute": "Fl", "Piccolo": "Picc", "Oboe": "Ob", "Clarinet": "Cl",
    "Bassoon": "Fag", "Contrabassoon": "Kfag", "Horn": "Hn",
    "Trumpet": "Tpt", "Trombone": "Tbn", "Tuba": "Tuba", "Timpani": "Timp",
    "Percussion": "Perc", "Violin": "Vln", "Viola": "Vla", "Cello": "Vc",
    "Contrabass": "Cb", "Harp": "Hp", "Bass voice": "Bass",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("labels")
    ap.add_argument("--lineups", required=True)
    ap.add_argument("--text", action="store_true",
                    help="print the OCR text instead of the resolved name")
    args = ap.parse_args()

    rows = json.load(open(args.labels))
    lineups = json.load(open(args.lineups))
    by_page = {r["page"]: r for r in rows}

    for row in lineups:
        print(f"\n=== pages {row['first']}-{row['last']}, size {row['size']} "
              f"— hand-read lineup ===")
        print("  TRUTH  " + " ".join(
            f"{ABBR.get(n, n[:4]):>5s}" for n in row["lineup"]))
        for page, si, seq in full_systems(
                rows, row["first"], row["last"], row["size"]):
            cells = [f"{ABBR.get(n, n[:4]):>5s}" if n else "    ." for n in seq]
            print(f"  p{page:3d}s{si} " + " ".join(cells))
            if args.text:
                r = by_page[page]
                offset = sum(r["systems"][:si])
                txt = {l["staff_index"]: l["text"] for l in r["labels"]}
                for k in range(row["size"]):
                    t = txt.get(offset + k)
                    if t:
                        print(f"          [{k:2d}] {t!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
