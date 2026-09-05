"""Build the OMR_ARC_RECLASS=1 arm of the scan A/B from the OFF arm's fixtures.

The flag lives entirely at export time, so the ON arm re-exports the OFF
arm's stored transcriptions instead of re-reading ten scan pages on a CPU a
training run owns. For each pooled row:

  1. assert the flag-off re-export is BYTE-EQUAL to `{rid}.arcoff.omr.musicxml`
     — the no-op proof, and what makes the OFF score describe this tree;
  2. export with the flag on, recording every veto firing by rule;
  3. write `{rid}.arcon.omr.{json,musicxml}` so `scan_eval.py --score-only
     --tag arcon` scores the arm through the SAME harness as the baseline;
  4. count tie and slur starts in truth / off / on, the element movement the
     veto is answerable for.

Usage:

    python3 benchmarks/omr-export-gaps-2026-09/ab_scan.py
    OMRNED_PYTHON=... python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py \
        --score-only --tag arcon --rows <the ten> \
        --out benchmarks/omr-export-gaps-2026-09/scan-arc-on.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import export as export_mod  # noqa: E402

SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"
FIXTURES = SCAN / "fixtures"

_TIE_START = re.compile(r'<tie type="start"/>')
_SLUR_START = re.compile(r'<slur number="\d+" type="start"/>')


def _counts(xml: str) -> dict[str, int]:
    return {"ties": len(_TIE_START.findall(xml)),
            "slurs": len(_SLUR_START.findall(xml))}


def main() -> int:
    doc = json.loads((SCAN / "works.json").read_text())
    rows = doc["rows"] if isinstance(doc, dict) and "rows" in doc else doc
    pooled = [r["row_id"] for r in rows if r.get("pooled", True)]

    report = []
    totals = {"truth": {"ties": 0, "slurs": 0},
              "off": {"ties": 0, "slurs": 0},
              "on": {"ties": 0, "slurs": 0}}
    for rid in pooled:
        raw = FIXTURES / f"{rid}.arcoff.omr.json"
        stored = FIXTURES / f"{rid}.arcoff.omr.musicxml"
        truth = FIXTURES / f"{rid}.truth.musicxml"
        if not (raw.is_file() and stored.is_file()):
            print(f"{rid}: OFF-arm fixtures missing — run scan_eval "
                  "--tag arcoff first")
            return 1
        result = json.loads(raw.read_text())

        os.environ["OMR_ARC_RECLASS"] = "0"
        off_xml = export_mod.to_musicxml(result)
        identical = off_xml == stored.read_text()
        if not identical:
            print(f"{rid}: FLAG-OFF EXPORT != the OFF arm's stored musicxml")

        os.environ["OMR_ARC_RECLASS"] = "1"
        export_mod.reset_arc_reclass_stats()
        on_xml = export_mod.to_musicxml(result)
        firings = dict(export_mod.ARC_RECLASS_STATS)
        os.environ["OMR_ARC_RECLASS"] = "0"

        (FIXTURES / f"{rid}.arcon.omr.musicxml").write_text(on_xml)
        (FIXTURES / f"{rid}.arcon.omr.json").write_text(raw.read_text())

        entry = {"row_id": rid, "off_identical": identical,
                 "firings": firings,
                 "truth": _counts(truth.read_text()) if truth.is_file() else None,
                 "off": _counts(off_xml), "on": _counts(on_xml)}
        report.append(entry)
        for arm in ("truth", "off", "on"):
            if entry[arm]:
                for k in ("ties", "slurs"):
                    totals[arm][k] += entry[arm][k]
        print(f"{rid}: identical_off={identical} firings={firings or '{}'} "
              f"ties truth/off/on = {entry['truth']['ties']}/"
              f"{entry['off']['ties']}/{entry['on']['ties']}  "
              f"slurs = {entry['truth']['slurs']}/{entry['off']['slurs']}/"
              f"{entry['on']['slurs']}")

    print("totals:", json.dumps(totals))
    (BENCH / "ab_scan_elements.json").write_text(
        json.dumps({"totals": totals, "rows": report}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
