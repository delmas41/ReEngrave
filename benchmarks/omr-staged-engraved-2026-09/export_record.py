"""Export a staged record with the REAL exporter, and print what it wrote.

    python3 benchmarks/omr-staged-engraved-2026-09/export_record.py \
        --record out/engraved-p0.record.json --out out/engraved-p0.musicxml

⚠️ SEPARATE FROM THE GATHER, DELIBERATELY. `staged/__main__.py` imports the
exporter AFTER the gather finishes, so an edit to `export.py` during a long run
reaches it and can kill a completed gather with a `NameError`. CLAUDE.md
records that costing two gathers; the recipe is to gather without `--musicxml`
and export afterwards, which is what this file is for.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.staged import export as X  # noqa: E402

_KEYS = ("notes", "rests", "measure_rests_read", "beams", "beamed_events",
         "pitches_altered_by_the_key", "parts", "ties", "slurs", "fermatas",
         "dynamics", "articulations", "ornaments", "divisions",
         "empty_bars_padded_without_meter", "tacet_bars_padded")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    result = json.loads(args.record.read_text())
    xml, report = X.to_musicxml(result)
    args.out.write_text(xml)
    cov = Path(str(args.out) + ".coverage.json")
    cov.write_text(json.dumps(report, indent=2, default=str))

    w = report.get("written", {})
    print(f"{args.record.name}: {len(xml)} bytes -> {args.out}")
    print("  written: " + ", ".join(f"{k}={w[k]}" for k in _KEYS if k in w))
    print(f"  balance: {report.get('balance')}")
    print(f"  part join: {report.get('part_join', {}).get('join_used')}  "
          f"staves/system {report.get('part_join', {}).get('staves_per_system')}")
    nr = report.get("notes_not_written") or report.get("not_written")
    if nr:
        print(f"  not written: {nr}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
