"""Re-export a saved ARM record through this tree's exporter and print the
`accidental_reading` census (EXPORT-only changes need no re-decision).

    python3 benchmarks/omr-accidental-2026-09/probe/reexport.py <arm.record.json> [--out <json>]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402


def main() -> int:
    doc = load_record(sys.argv[1])
    xml, report = E.to_musicxml(doc)
    out = {"record": sys.argv[1], "accidental_elements": xml.count("<accidental"),
           "notes": xml.count("<note"),
           "accidental_reading": report["accidental_reading"],
           "status_census_balanced": report["status_census"]["balanced"]}
    if "--out" in sys.argv:
        Path(sys.argv[sys.argv.index("--out") + 1]).write_text(
            json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
