"""Export ONE record twice -- one tree before the change, one after -- and ask
whether the MUSIC is unmoved while the measure NUMBERS move.

    python3 benchmarks/omr-measure-numbering-2026-09/numbering_arm.py \
        --record library/_shared-records/beethoven5-p1-p4.record.json \
        --tag before

⚠️ THIS IS AN EXPORT-STAGE CHANGE, so a re-export of a saved record is the
RIGHT instrument (`reexport_arm.py`'s family). `readjudicate.py` is blind to
an export change by construction, and a GATHER re-run is unnecessary: nothing
about which ink is read changes.

⚠️ Run it from a tree whose `tools/` is not being edited -- a source-level
test reads from disk using import-time line numbers.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import export as sx          # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def measures_per_part(xml):
    """{part_id: [measure numbers]} straight out of the emitted text."""
    out = collections.OrderedDict()
    for chunk in re.split(r'(?=<part id=")', xml):
        m = re.match(r'<part id="([^"]+)"', chunk)
        if not m:
            continue
        out[m.group(1)] = [int(x) for x in
                           re.findall(r'<measure number="(\d+)"', chunk)]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--tag", required=True)
    args = ap.parse_args(argv)

    OUT.mkdir(parents=True, exist_ok=True)
    result = json.loads(Path(args.record).read_text())
    xml, report = sx.to_musicxml(result)

    (OUT / f"{args.tag}.musicxml").write_text(xml)
    (OUT / f"coverage-{args.tag}.json").write_text(json.dumps(report, indent=1))

    per_part = measures_per_part(xml)
    (OUT / f"numbers-{args.tag}.json").write_text(json.dumps(per_part, indent=1))

    print("%s: parts=%s measures=%d"
          % (args.tag, report["written"].get("parts"),
             sum(len(v) for v in per_part.values())))
    for pid, nums in per_part.items():
        print("  %-4s n=%-5d first=%-4s last=%-4s"
              % (pid, len(nums), nums[0] if nums else "-",
                 nums[-1] if nums else "-"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
