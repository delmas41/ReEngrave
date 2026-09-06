"""PAGE vs OURS vs MXL, side by side, on one real scanned page.

Sean: *"Can you verify our headline matches a PDF, and then run the PDF through
it to see what it captures?"*

Three columns, three substrates, none derived from another:

  PAGE   `works.json`'s hand-read `staves` list, corroborated for this run by
         reading a 130 dpi render of the page with a vision model — the staff
         labels are printed in the margin and are legible (`render_page.py`).

  OURS   the fresh transcription from `run_one_page.py` — this session's own
         run of the PDF, not a stored fixture.

  MXL    the reference encoding trimmed to the page's measures,
         `fixtures/<row>.truth.musicxml`, parsed with ElementTree.

    python3 benchmarks/omr-headline-validity-2026-09/probe_three_ways.py \
        --row beethoven-sym5-mvt1-984073-p1
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"
FIXTURES = SCAN / "fixtures"
LIVE = BENCH / "live-run"


def score_parts(xml: Path) -> list[str]:
    root = ET.parse(xml).getroot()
    out = []
    for sp in root.iter("score-part"):
        el = sp.find("part-name")
        out.append((el.text or "").strip() if el is not None else "")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", default="beethoven-sym5-mvt1-984073-p1")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    doc = json.loads((SCAN / "works.json").read_text())
    by_id = {r["row_id"]: r for r in doc["rows"]}
    row = by_id[args.row]
    staves = row.get("staves")
    if isinstance(staves, str) and staves.startswith("same-as:"):
        staves = by_id[staves.split(":", 1)[1]]["staves"]

    truth_xml = FIXTURES / f"{args.row}.truth.musicxml"
    live_xml = LIVE / f"{args.row}.live.omr.musicxml"
    mxl_parts = score_parts(truth_xml)
    our_parts = score_parts(live_xml) if live_xml.is_file() else []

    print(f"ROW {args.row}")
    print(f"  edition   {row['edition']['catalog_path']}")
    print(f"  page      pdf index {row['page']['pdf_page_index']}, "
          f"printed page {row['page'].get('printed_page')}, "
          f"{row['page']['n_systems']} system(s), "
          f"{row['page']['n_staves']} staves on the page")
    print(f"  window    reference measures "
          f"{row['window']['first_ref_measure']}-{row['window']['last_ref_measure']}")
    print()
    print(f"  PAGE prints {len(staves)} staves per system  |  "
          f"MXL encodes {len(mxl_parts)} parts  |  "
          f"WE emit {len(our_parts)} parts")
    print()
    print(f"{'#':>3} {'PAGE (hand-read staff)':30s} {'MXL parts it carries':44s} "
          f"{'OURS (part name)':28s}")
    print("-" * 108)
    for i, spec in enumerate(staves):
        carried = ", ".join(f"[{p}] {mxl_parts[p]}" if p < len(mxl_parts)
                            else f"[{p}] ??" for p in spec["parts"])
        ours = our_parts[i] if i < len(our_parts) else "—"
        flag = "  <-- CONDENSED" if len(spec["parts"]) > 1 else ""
        print(f"{i:>3} {spec['name']:30s} {carried:44s} {ours:28s}{flag}")

    orphan = sorted(set(range(len(mxl_parts)))
                    - {p for s in staves for p in s["parts"]})
    print()
    print(f"MXL parts with NO printed staff of their own: {len(orphan)}")
    n_cond = sum(1 for s in staves if len(s["parts"]) > 1)
    surplus = len(mxl_parts) - len(staves)
    print(f"condensed staves: {n_cond};  surplus parts (encoded − printed): "
          f"{surplus}")
    print()
    print("Every surplus part is a SECOND player on a staff the page already "
          "prints, so musicdiff has no staff to pair it with and charges it "
          "`entire staff insert/delete` whether or not the page was read "
          "correctly.")

    if args.out:
        Path(args.out).write_text(json.dumps({
            "row_id": args.row,
            "page_staves": [s["name"] for s in staves],
            "mxl_parts": mxl_parts,
            "our_parts": our_parts,
            "condensed": [{"staff": s["name"], "parts": s["parts"]}
                          for s in staves if len(s["parts"]) > 1],
            "orphan_parts": orphan,
            "surplus_parts": surplus,
        }, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
