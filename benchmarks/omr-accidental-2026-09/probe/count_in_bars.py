"""Count `<accidental>` (and `<note>`) elements in a MusicXML file, per
measure-number range — the gate's reach figure read off the FILE itself.

    python3 benchmarks/omr-accidental-2026-09/probe/count_in_bars.py <file.musicxml> <first> <last>
"""
from __future__ import annotations

import collections
import json
import sys
import xml.etree.ElementTree as ET


def main() -> int:
    path, lo, hi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    root = ET.parse(path).getroot()
    acc = collections.Counter()
    notes = 0
    nums = set()
    for part in root.findall("part"):
        name = part.get("id")
        for m in part.findall("measure"):
            try:
                n = int(m.get("number"))
            except (TypeError, ValueError):
                continue
            nums.add(n)
            if not lo <= n <= hi:
                continue
            for note in m.findall("note"):
                notes += 1
                a = note.findtext("accidental")
                if a:
                    acc[name] += 1
    print(json.dumps({"file": path, "bars": [lo, hi],
                      "measure_numbers_in_file": [min(nums), max(nums)],
                      "notes": notes,
                      "accidental_elements": sum(acc.values()),
                      "by_part": dict(acc)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
